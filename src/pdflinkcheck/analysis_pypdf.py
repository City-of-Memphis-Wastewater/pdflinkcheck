#!/usr/bin/env python3 
# SPDX-License-Identifier: MIT
# src/pdflinkcheck/analysis_pypdf.py
from __future__ import annotations
import sys
from pathlib import Path
import logging
from typing import Dict, Any, Optional, List

from pypdf import PdfReader
from pypdf.generic import Destination, NameObject, ArrayObject, IndirectObject
from pdflinkcheck.helpers import PageRef


from pdflinkcheck.io import error_logger, export_report_data, get_first_pdf_in_cwd, LOG_FILE_PATH

"""
Inspect target PDF for both URI links and for GoTo links, using only pypdf, not Fitz
"""

def analyze_pdf(pdf_path: str):
    data = {}
    data["links"] = []
    data["toc"] = []
    data["file_ov"] = {}

    try:
        reader = PdfReader(pdf_path)
    except Exception as e:
        print(f"pypdf.PdfReader() failed: {e}")
        return data
    
    extracted_links = _extract_links_pypdf(reader)
    structural_toc = _extract_toc_pypdf(reader)
    page_count = len(reader.pages)
    data["links"] = extracted_links
    data["toc"] = structural_toc
    data["file_ov"]["total_pages"] = page_count
    return data


def _get_anchor_text_pypdf(page, rect) -> str:
    """
    Extracts text within the link's bounding box using a visitor function.
    Reliable for finding text associated with a link without PyMuPDF.
    """
    if not rect:
        return "N/A: Missing Rect"
    
    # Standardize rect orientation (pypdf Rects are [x0, y0, x1, y1])
    # Note: PDF coordinates use bottom-left as (0,0)
    x_min = min(rect[0], rect[2])
    y_min = min(rect[1], rect[3])
    x_max = max(rect[0], rect[2])
    y_max = max(rect[1], rect[3])
    
    parts: List[str] = []

    def _visitor_body(text, cm, tm, font_dict, font_size):
        # tm[4], tm[5] are the current text insertion point coordinates (x, y)
        x, y = tm[4], tm[5]

        # Using a threshold to account for font metrics/descenders
        # Generous tolerance (±10 pt) to catch descenders, ascenders, kerning, and minor misalignments
        tolerance = 10
        if (x_min - tolerance) <= x <= (x_max + tolerance) and (y_min - tolerance) <= y <= (y_max + tolerance):
            if text.strip():
                parts.append(text)

    page.extract_text(visitor_text=_visitor_body)
    
    raw_extracted = "".join(parts)
    cleaned = " ".join(raw_extracted.split()).strip()
    
    return cleaned if cleaned else "Graphic/Empty Link"

def _resolve_pypdf_destination(reader: PdfReader, dest, obj_id_to_page: dict) -> Optional[int]:
    try:
        if isinstance(dest, Destination):
            # .page_number in pypdf is already 0-indexed
            return dest.page_number 

        if isinstance(dest, IndirectObject):
            return obj_id_to_page.get(dest.idnum)

        if isinstance(dest, ArrayObject) and len(dest) > 0:
            if isinstance(dest[0], IndirectObject):
                return obj_id_to_page.get(dest[0].idnum)

        return None  # Unresolved → None
    except Exception:
        return None
        

def _extract_links_pypdf(reader: PdfReader) -> List[Dict[str, Any]]:
    """
    Termux-compatible link extraction using pure-Python pypdf.
    Matches the reporting schema of the PyMuPDF version.
    """
    
    # Pre-map Object IDs to Page Numbers for fast internal link resolution
    obj_id_to_page = {
        page.indirect_reference.idnum: i
        for i, page in enumerate(reader.pages)
    }

    all_links = []
    
    for i, page in enumerate(reader.pages):
        #page_num = i 
        # Use PageRef to stay consistent
        page_source = PageRef.from_index(i)
        if "/Annots" not in page:
            continue
            
        for annot in page["/Annots"]:
            obj = annot.get_object()
            if obj.get("/Subtype") != "/Link":
                continue

            rect = obj.get("/Rect")
            anchor_text = _get_anchor_text_pypdf(page, rect)
            
            link_dict = {
                'page': page_source.machine,
                'rect': list(rect) if rect else None,
                'link_text': anchor_text,
                'type': 'Other Action',
                'target': 'Unknown'
            }
            
            # Handle URI (External)
            if "/A" in obj and "/URI" in obj["/A"]:
                uri = obj["/A"]["/URI"]
                link_dict.update({
                    'type': 'External (URI)',
                    'url': uri,
                    'target': uri
                })
            
            # Handle GoTo (Internal)
            elif "/Dest" in obj or ("/A" in obj and "/D" in obj["/A"]):
                dest = obj.get("/Dest") or obj["/A"].get("/D")
                target_page = _resolve_pypdf_destination(reader, dest, obj_id_to_page)
                # print(f"DEBUG: resolved target_page = {target_page} (type: {type(target_page)})")
                if target_page is not None:
                    dest_page = PageRef.from_index(target_page)
                    link_dict.update({
                        'type': 'Internal (GoTo/Dest)',
                        'destination_page': dest_page.machine,
                        #'target': f"Page {target_page}"
                        'target': dest_page.machine
                    })
            
            # Handle Remote GoTo (GoToR)
            elif "/A" in obj and obj["/A"].get("/S") == "/GoToR":
                remote_file = obj["/A"].get("/F")
                link_dict.update({
                    'type': 'Remote (GoToR)',
                    'remote_file': str(remote_file),
                    'target': f"File: {remote_file}"
                })

            all_links.append(link_dict)
                        
    return all_links


def _extract_toc_pypdf(reader: PdfReader) -> List[Dict[str, Any]]:
    try:
        # Note: outline is a property, not a method.
        toc_tree = reader.outline 
        toc_data = []
        
        def flatten_outline(outline_items, level=1):
            for item in outline_items:
                if isinstance(item, Destination):
                    # Using the reader directly is the only way to avoid 
                    # the 'Destination' object has no attribute error
                    try:
                        page_num_raw = reader.get_destination_page_number(item)
                        # page_num_raw is 0-indexed. Use PageRef to store it.
                        ref = PageRef.from_index(page_num_raw)
                        page_num = ref.machine
                    except:
                        page_num = "N/A"

                    toc_data.append({
                        "level": level,
                        "title": item.title,
                        "target_page": page_num
                    })
                elif isinstance(item, list):
                    # pypdf nests children in a list immediately following the parent
                    flatten_outline(item, level + 1)
        
        flatten_outline(toc_tree)
        return toc_data
    except Exception as e:
        print(f"TOC error: {e}", file=sys.stderr)
        return []

def call_stable():
    """
    Placeholder function for command-line execution (e.g., in __main__).
    Note: This requires defining PROJECT_NAME, CLI_MAIN_FILE, etc., or 
    passing them as arguments to run_report.
    """
    from pdflinkcheck.report import run_report_and_call_exports

    run_report_and_call_exports(pdf_library = "pypdf")

if __name__ == "__main__":
    call_stable()
