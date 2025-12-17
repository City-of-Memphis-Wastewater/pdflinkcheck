# src/pdflinkcheck/analyze_pypdf.py
import sys
from pathlib import Path
import logging
from typing import Dict, Any, Optional, List

from pypdf import PdfReader
from pypdf.generic import Destination, NameObject, ArrayObject, IndirectObject


from pdflinkcheck.io import error_logger, export_report_data, get_first_pdf_in_cwd, LOG_FILE_PATH
from pdflinkcheck.report import run_report

"""
Inspect target PDF for both URI links and for GoTo links, using only pypdf, not Fitz
"""

def get_anchor_text_pypdf(page, rect) -> str:
    """
    Extracts text within the link's bounding box using a visitor function.
    Reliable for finding text associated with a link without PyMuPDF.
    """
    if not rect:
        return "N/A: Missing Rect"
    
    # Standardize rect orientation (pypdf Rects are [x0, y0, x1, y1])
    # Note: PDF coordinates use bottom-left as (0,0)
    x_min, y_min = min(rect[0], rect[2]), min(rect[1], rect[3])
    x_max, y_max = max(rect[0], rect[2]), max(rect[1], rect[3])
    
    parts = []

    def visitor_body(text, cm, tm, font_dict, font_size):
        # tm[4], tm[5] are the current text insertion point coordinates (x, y)
        x, y = tm[4], tm[5]
        # Using a 3pt threshold to account for font metrics/descenders
        if (x_min - 3) <= x <= (x_max + 3) and (y_min - 3) <= y <= (y_max + 3):
            parts.append(text)

    page.extract_text(visitor_text=visitor_body)
    
    raw_extracted = "".join(parts)
    cleaned = " ".join(raw_extracted.split()).strip()
    
    return cleaned if cleaned else "Graphic/Empty Link"

def resolve_pypdf_destination(reader: PdfReader, dest, obj_id_to_page: dict) -> str:
    """
    Resolves a Destination object or IndirectObject to a 1-based page number string.
    """
    try:
        if isinstance(dest, Destination):
            return str(dest.page_number + 1)
        
        if isinstance(dest, IndirectObject):
            return str(obj_id_to_page.get(dest.idnum, "Unknown"))
        
        if isinstance(dest, ArrayObject) and len(dest) > 0:
            if isinstance(dest[0], IndirectObject):
                return str(obj_id_to_page.get(dest[0].idnum, "Unknown"))
            
        return "Unknown"
    except Exception:
        return "Error Resolving"

def extract_links_pypdf(pdf_path):
    """
    Termux-compatible link extraction using pure-Python pypdf.
    Matches the reporting schema of the PyMuPDF version.
    """
    reader = PdfReader(pdf_path)
    
    # Pre-map Object IDs to Page Numbers for fast internal link resolution
    obj_id_to_page = {
        page.indirect_reference.idnum: i + 1 
        for i, page in enumerate(reader.pages)
    }

    all_links = []
    
    for i, page in enumerate(reader.pages):
        page_num = i + 1
        if "/Annots" not in page:
            continue
            
        for annot in page["/Annots"]:
            obj = annot.get_object()
            if obj.get("/Subtype") != "/Link":
                continue

            rect = obj.get("/Rect")
            anchor_text = get_anchor_text_pypdf(page, rect)
            
            link_dict = {
                'page': page_num,
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
                target_page = resolve_pypdf_destination(reader, dest, obj_id_to_page)
                link_dict.update({
                    'type': 'Internal (GoTo/Dest)',
                    'destination_page': target_page,
                    'target': f"Page {target_page}"
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


def extract_toc_pypdf(pdf_path: str) -> List[Dict[str, Any]]:
    try:
        reader = PdfReader(pdf_path)
        # Note: outline is a property, not a method.
        toc_tree = reader.outline 
        toc_data = []
        
        def flatten_outline(outline_items, level=1):
            for item in outline_items:
                if isinstance(item, Destination):
                    # Using the reader directly is the only way to avoid 
                    # the 'Destination' object has no attribute error
                    try:
                        page_num = reader.get_destination_page_number(item) + 1
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
    print("Begin analysis...")
    run_report(library_pdf = "pypdf")
    print("Analysis complete.")

if __name__ == "__main__":
    call_stable()
