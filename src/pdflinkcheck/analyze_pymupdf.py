import sys
from pathlib import Path
import logging
from typing import Dict, Any, Optional, List

logging.getLogger("fitz").setLevel(logging.ERROR) 

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

from pdflinkcheck.report import run_report
from pdflinkcheck.validate import run_validation

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
        toc_data.append({
            'level': level,
            'title': title,
            'target_page': page_num
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
    """
    Opens a PDF, iterates through all pages and extracts all link annotations. 
    It categorizes the links into External, Internal, or Other actions, and extracts the anchor text.
    
    Args:
        pdf_path: The file system path (str) to the target PDF document.

    Returns:
        A list of dictionaries, where each dictionary is a comprehensive 
           representation of an active hyperlink found in the PDF.
        
    """
    links_data = []
    try:
        doc = fitz.open(pdf_path)        

        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            
            for link in page.get_links():

                page_obj = doc.load_page(page_num)
                link_rect = get_link_rect(link)
                
                rect_obj = link.get("from")
                xref = link.get("xref")
                #print(f"rect_obj = {rect_obj}")
                #print(f"xref = {xref}")
                

                # --- Examples of various keys associated with various link instances ---
                #print(f"keys: list(link) = {list(link)}")
                # keys: list(link) = ['kind', 'xref', 'from', 'page', 'viewrect', 'id']
                # keys: list(link) = ['kind', 'xref', 'from', 'uri', 'id']
                # keys: list(link) = ['kind', 'xref', 'from', 'page', 'view', 'id']

                # 1. Extract the anchor text
                anchor_text = get_anchor_text(page_obj, link_rect)

                # 2. Extract the target and kind
                target = ""
                kind = link.get('kind')
                
                
                link_dict = {
                    'page': int(page_num) + 1, # accurate for link location, add 1
                    'rect': link_rect,
                    'link_text': anchor_text,
                    'xref':xref
                }
                
                # A. Clean Geom. Objects: Use the helper function on 'to' / 'destination'
                # Use the clean serialize_fitz_object() helper function on all keys that might contain objects
                destination_view = serialize_fitz_object(link.get('to'))

                # B. Correct Internal Link Page Numbering (The -1 correction hack)
                # This will be skipped by URI, which is not expected to have a page key
                target_page_num_reported = "N/A"
                if link.get('page') is not None:
                    target_page_num_reported = int(link.get('page'))+1 # accurate for link target, don't add 1 (weird)

                if link['kind'] == fitz.LINK_URI:
                    target =  link.get('uri', 'URI (Unknown Target)')
                    link_dict.update({
                        'type': 'External (URI)',
                        'url': link.get('uri'),
                        'target': target
                    })
                
                elif link['kind'] == fitz.LINK_GOTO:
                    target = f"Page {target_page_num_reported}"
                    link_dict.update({
                        'type': 'Internal (GoTo/Dest)',
                        'destination_page': target_page_num_reported,
                        'destination_view': destination_view,
                        'target': target
                    })
                
                elif link['kind'] == fitz.LINK_GOTOR:
                    link_dict.update({
                        'type': 'Remote (GoToR)',
                        'remote_file': link.get('file'),
                        'destination': destination_view
                    })
                
                elif link.get('page') is not None and link['kind'] != fitz.LINK_GOTO: 
                    target = f"Page {target_page_num_reported}"
                    link_dict.update({
                        'type': 'Internal (Resolved Action)',
                        'destination_page': target_page_num_reported,
                        'destination_view': destination_view,
                        'source_kind': link.get('kind'),
                        'target': target
                    })
                    
                else:
                    target = link.get('url') or link.get('remote_file') or link.get('target')
                    link_dict.update({
                        'type': 'Other Action',
                        'action_kind': link.get('kind'),
                        'target': target
                    })

                ## --- General Serialization Cleaner ---
                #for key, value in link_dict.items():
                #    if hasattr(value, 'rect') and hasattr(value, 'point'):
                #        # This handles Rect and Point objects that may slip through
                #        link_dict[key] = str(value)
                ## --- End Cleaner ---
                    
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
    run_report(pdf_library = "pymupdf")
    #run_validation(pdf_library = "pymupdf")

if __name__ == "__main__":
    call_stable()
