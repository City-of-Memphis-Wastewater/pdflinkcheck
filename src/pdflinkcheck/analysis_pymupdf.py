#!/usr/bin/env python3 
# SPDX-License-Identifier: MIT
# pdflinkcheck/analysis_pymupdf.py
from __future__ import annotations
import sys
from pathlib import Path
import logging
from typing import Dict, Any, Optional, List

logging.getLogger("fitz").setLevel(logging.ERROR) 

from pdflinkcheck.environment import pymupdf_is_available
from pdflinkcheck.helpers import PageRef

try:
    if pymupdf_is_available():
        import fitz  # PyMuPDF
    else:
        fitz = None
except ImportError:
    fitz = None

"""
Inspect target PDF for both URI links and for GoTo links.
"""

# Helper function: Prioritize 'from'
def get_link_rect(link_dict):
    """
    Retrieves the bounding box for the link using the reliable 'from' key
    provided by PyMuPDF's link dictionary.

    Args:
        link_dict: A dictionary representing a single link/annotation 
                   returned by `page.get_links()`.

    Returns:
        A tuple of four floats (x0, y0, x1, y1) representing the 
        rectangular coordinates of the link on the page, or None if the 
        bounding box data is missing.
    """
    # 1. Use the 'from' key, which returns a fitz.Rect object or None
    rect_obj = link_dict.get('from') 
    
    if rect_obj:
        # 2. Extract the coordinates using the standard Rect properties 
        #    (compatible with all recent PyMuPDF versions)
        return (rect_obj.x0, rect_obj.y0, rect_obj.x1, rect_obj.y1)
    
    # 3. Fallback to None if 'from' is missing
    return None

def get_anchor_text(page, link_rect):
    if not link_rect:
        return "N/A: Missing Rect"

    try:
        # 1. Convert to fitz.Rect and normalize
        rect = fitz.Rect(link_rect)
        if rect.is_empty:
            return "N/A: Rect Error"

        # 2. Use asymmetric expansion (similar to the pypdf logic)
        # 10 points horizontal to catch wide characters/kerning
        # 3 points vertical to stay within the line
        search_rect = fitz.Rect(
            rect.x0 - 10, 
            rect.y0 - 3, 
            rect.x1 + 10, 
            rect.y1 + 3
        )

        # 3. Extract all words on the page
        # Each word is: (x0, y0, x1, y1, "text", block_no, line_no, word_no)
        words = page.get_text("words")
        
        anchor_parts = []
        for w in words:
            word_rect = fitz.Rect(w[:4])
            # Check if the word intersects our expanded link rectangle
            if word_rect.intersects(search_rect):
                anchor_parts.append(w[4])

        cleaned_text = " ".join(anchor_parts).strip()
        
        return cleaned_text if cleaned_text else "N/A: No Visible Text"
            
    except Exception:
        return "N/A: Rect Error"
    
def get_anchor_text_stable(page, link_rect):
    """
    Extracts text content using the link's bounding box coordinates.
    The bounding box is slightly expanded to ensure full characters are captured.

    Args:
        page: The fitz.Page object where the link is located.
        link_rect: A tuple of four floats (x0, y0, x1, y1) representing the 
                   link's bounding box.

    Returns:
        The cleaned, extracted text string, or a placeholder message 
        if no text is found or if an error occurs.
    """
    if not link_rect:
        return "N/A: Missing Rect"

    try:
        # 1. Convert the coordinate tuple back to a fitz.Rect object
        rect = fitz.Rect(link_rect)
        
        # --- CRITICAL STEP: Check for invalid/empty rect AFTER conversion ---
        # If the rect is invalid (e.g., width or height is <= 0), skip it
        # Note: fitz.Rect will often auto-normalize, but this explicit check is safer.
        if rect.is_empty or rect.width <= 0 or rect.height <= 0:
            return "N/A: Rect Error (Zero/Negative Dimension)"

        # 2. Expand the rect slightly to capture full characters (1 unit in each direction)
        #    This method avoids the proprietary/unstable 'from_expanded' or 'from_rect' methods.
        expanded_rect = fitz.Rect(
            rect.x0 - 1, 
            rect.y0 - 1, 
            rect.x1 + 1, 
            rect.y1 + 1
        )
        
        # 3. Get the text within the expanded bounding box
        anchor_text = page.get_textbox(expanded_rect)
        
        # 4. Clean up whitespace and non-printing characters
        cleaned_text = " ".join(anchor_text.split())
        
        if cleaned_text:
            return cleaned_text
        else:
            return "N/A: No Visible Text"
            
    except Exception:
        # Fallback for unexpected errors in rect conversion or retrieval
        return "N/A: Rect Error"

def analyze_toc_fitz(doc):
    """
    Extracts the structural Table of Contents (PDF Bookmarks/Outline) 
    from the PDF document using PyMuPDF's built-in functionality.

    Args:
        doc: The open fitz.Document object.

    Returns:
        A list of dictionaries, where each dictionary represents a TOC entry 
        with 'level', 'title', and 'target_page' (1-indexed).
    """
    toc = doc.get_toc()
    toc_data = []
    
    for level, title, page_num in toc:
        # fitz pages are 1-indexed for TOC!
        # We know fitz gives us a human number. 
        # We convert it to a physical index for our internal storage.
        # page_num is 1 (Human). We normalize to 0 (Physical).
        ref = PageRef.from_human(page_num)
        toc_data.append({
            'level': level,
            'title': title,
            #'target_page': ref.index
            'target_page': ref.machine
        })
        
    return toc_data


# 2. Updated Main Inspection Function to Include Text Extraction
#def inspect_pdf_hyperlinks_fitz(pdf_path):
def extract_toc_pymupdf(pdf_path):
    """
    Opens a PDF, iterates through all pages and extracts the structural table of contents (TOC/bookmarks).

    Args:
        pdf_path: The file system path (str) to the target PDF document.

    Returns:
        A list of dictionaries representing the structural TOC/bookmarks.
    """
    try:
        doc = fitz.open(pdf_path)
        structural_toc = analyze_toc_fitz(doc)
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
    return structural_toc


def serialize_fitz_object(obj):
    """Converts a fitz object (Point, Rect, Matrix) to a serializable type."""
    # Meant to avoid known Point errors like: '[ERROR] An unexpected error occurred during analysis: Report export failed due to an I/O error: Object of type Point is not JSON serializable'
    if obj is None:
        return None
    
    # 1. Handle fitz.Point (has x, y)
    if hasattr(obj, 'x') and hasattr(obj, 'y') and not hasattr(obj, 'x0'):
        return (obj.x, obj.y)
        
    # 2. Handle fitz.Rect and fitz.IRect (has x0, y0)
    if hasattr(obj, 'x0') and hasattr(obj, 'y0'):
        return (obj.x0, obj.y0, obj.x1, obj.y1)
        
    # 3. Handle fitz.Matrix (has a, b, c, d, e, f)
    if hasattr(obj, 'a') and hasattr(obj, 'b') and hasattr(obj, 'c'):
        return (obj.a, obj.b, obj.c, obj.d, obj.e, obj.f)
        
    # 4. Fallback: If it's still not a primitive type, convert it to a string
    if not isinstance(obj, (str, int, float, bool, list, tuple, dict)):
        # Examples: hasattr(value, 'rect') and hasattr(value, 'point'):
        # This handles Rect and Point objects that may slip through
        return str(obj)
        
    # Otherwise, return the object as is (it's already primitive)
    return obj


def extract_links_pymupdf(pdf_path):
    links_data = []
    try:
        doc = fitz.open(pdf_path)        
        # This represents the maximum valid 0-index in the doc
        last_page_ref = PageRef.from_pymupdf_total_page_count(doc.page_count)

        #print(last_page_ref)       # Output: "358" (Because of __str__)
        #print(int(last_page_ref))  # Output: 357   (Because of __int__)

        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            source_ref = PageRef.from_index(page_num)

            for link in page.get_links():
                link_rect = get_link_rect(link)
                anchor_text = get_anchor_text(page, link_rect)
                
                link_dict = {
                    'page': source_ref.machine,
                    'rect': link_rect,
                    'link_text': anchor_text,
                    'xref': link.get("xref")
                }
                
                kind = link.get('kind')
                destination_view = serialize_fitz_object(link.get('to'))
                p_index = link.get('page') # excpeted to be human facing, per PyMuPDF's known quirks
                
                # --- CASE 1: INTERNAL JUMPS (GoTo) ---
                if p_index is not None:

                    # Ensure we are working with an integer
                    raw_pymupdf_idx = int(p_index)
                    corrected_machine_idx = PageRef.corrected_down(raw_pymupdf_idx).index
                    
                    # Logic: Normalize to 0-index and store as int
                    idx = min(corrected_machine_idx, int(last_page_ref))
                    #print(f"DEBUG: Link Text: {anchor_text} | Raw p_index: {p_index}")
                    #print(f"[DEBUG] idx: {idx}")
                    dest_ref = PageRef.from_index(idx) # does not impact the value

                    link_dict.update({
                        'destination_page': dest_ref.machine,
                        'destination_view': destination_view,
                        'target': dest_ref.machine,          # INT (MACHINE INDEX)
                    })

                    if kind == fitz.LINK_GOTO:
                        link_dict['type'] = 'Internal (GoTo/Dest)'
                    else:
                        link_dict['type'] = 'Internal (Resolved Action)'
                        link_dict['source_kind'] = kind
                
                # --- CASE 2: EXTERNAL URIs ---
                elif kind == fitz.LINK_URI:
                    uri = link.get('uri', 'URI (Unknown Target)')
                    link_dict.update({
                        'type': 'External (URI)',
                        'url': uri,
                        'target': uri # STRING (URL)
                    })
                
                # --- CASE 3: REMOTE PDF REFERENCES ---
                elif kind == fitz.LINK_GOTOR:
                    remote_file = link.get('file', 'Remote File')
                    link_dict.update({
                        'type': 'Remote (GoToR)',
                        'remote_file': link.get('file'),
                        'target': remote_file  # STRING (File Path)
                    })
                
                # --- CASE 4: OTHERS ---
                else:
                    link_dict.update({
                        'type': 'Other Action',
                        'action_kind': kind,
                        'target': 'Unknown'  # STRING
                    })

                links_data.append(link_dict)
        doc.close()
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
    return links_data

def call_stable():
    """
    Placeholder function for command-line execution (e.g., in __main__).
    Note: This requires defining PROJECT_NAME, CLI_MAIN_FILE, etc., or 
    passing them as arguments to run_report.
    """
    from pdflinkcheck.report import run_report_and_call_exports
    
    run_report_and_call_exports(pdf_library = "pymupdf")

if __name__ == "__main__":
    call_stable()
