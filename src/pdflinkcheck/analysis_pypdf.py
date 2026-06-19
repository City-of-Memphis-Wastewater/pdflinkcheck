#!/usr/bin/env python3 
# SPDX-License-Identifier: MIT
# src/pdflinkcheck/analysis_pypdf.py
from __future__ import annotations
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
from pypdf import PdfReader
from pypdf.generic import (
    Destination,
    NameObject,
    ArrayObject,
    IndirectObject,
)
import logging

logger = logging.getLogger(__name__)

from pdflinkcheck.helpers import PageRef, LinkType, create_link_dict


"""
Inspect target PDF for both URI links and for GoTo links, using only pypdf, not Fitz
"""

from enum import Enum

class SourceKindPyPDF(str, Enum):
    """Tracks exactly which internal low-level PDF dictionary pattern exposed the target link in pypdf."""
    ANNOT_URI = "pypdf_annot_action_uri"           # /A with /URI
    ANNOT_DIRECT_DEST = "pypdf_annot_direct_dest"   # Direct /Dest on Annotation
    ANNOT_ACTION_DEST = "pypdf_annot_action_dest"   # /A with /D (GoTo Action)
    ANNOT_GOTOR = "pypdf_annot_gotor"               # /A with /S -> /GoToR
    ANNOT_LAUNCH = "pypdf_annot_launch"             # /A with /S -> /Launch
    ANNOT_OTHER = "pypdf_annot_other"               # Fallback
    
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
    
    return cleaned if cleaned else "Link (No Text)"

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
        page_source = PageRef.from_index(i)
        if "/Annots" not in page:
            continue
            
        for annot in page["/Annots"]:
            obj = annot.get_object()
            if obj.get("/Subtype") != "/Link":
                continue

            rect = obj.get("/Rect")
            anchor_text = _get_anchor_text_pypdf(page, rect)

            # Initialize local variables for conditional assignment
            determined_type = LinkType.OTHER.value
            url = None
            destination_page = None
            remote_file = None
            file = None
            source_kind = SourceKindPyPDF.ANNOT_OTHER.value

            # 1. Handle URI (External)
            if "/A" in obj and "/URI" in obj["/A"]:
                determined_type = LinkType.EXTERNAL.value
                source_kind = SourceKindPyPDF.ANNOT_URI.value
                url = obj["/A"]["/URI"]
            
            # 2. Handle GoTo (Internal)
            elif "/Dest" in obj or ("/A" in obj and "/D" in obj["/A"]):
                dest = obj.get("/Dest") or obj["/A"].get("/D")
                target_page = _resolve_pypdf_destination(reader, dest, obj_id_to_page)
                
                if target_page is not None:
                    dest_page = PageRef.from_index(target_page)
                    destination_page = dest_page.machine
                    
                    if "/Dest" in obj:
                        determined_type = LinkType.INTERNAL_RESOLVED.value
                        source_kind = SourceKindPyPDF.ANNOT_DIRECT_DEST.value
                    else:
                        determined_type = LinkType.INTERNAL_GOTO.value
                        source_kind = SourceKindPyPDF.ANNOT_ACTION_DEST.value

            # 3. Handle Remote GoTo (GoToR)
            elif "/A" in obj and obj["/A"].get("/S") == "/GoToR":
                determined_type = LinkType.REMOTE_GOTOR.value
                source_kind = SourceKindPyPDF.ANNOT_GOTOR.value
                remote_file = str(obj["/A"].get("/F"))

            # 4. Handle Launch Actions
            elif "/A" in obj and obj["/A"].get("/S") == "/Launch":
                determined_type = LinkType.LAUNCH.value
                source_kind = SourceKindPyPDF.ANNOT_LAUNCH.value
                file = str(obj["/A"].get("/F") or "")

            # Pass everything directly into the dictionary factory initialization
            link_dict = create_link_dict(
                source_page_ref=page_source, 
                rect_norm=list(rect) if rect else None,
                anchor_text=anchor_text,
                link_type=determined_type,
                source_kind=source_kind,
                destination_page=destination_page,
                url=url,
                remote_file=remote_file,
                file=file,
                xref=None # pypdf does not track direct xref metrics identical to PyMuPDF
            )

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

def demo():
    """
    Demostrate the pypdf-informed analyze_pdf().
    """
    from pdflinkcheck.io import get_first_pdf_in_cwd
    
    analyze_pdf(pdf_path = get_first_pdf_in_cwd())
    data = analyze_pdf(pdf_path = get_first_pdf_in_cwd())
    print(f"list(data) = {list(data)}")
    print("pypdf-based analysis complete.")
    print("Use the pdflinkcheck CLI, GUI, or web server to generate export files.")

if __name__ == "__main__":
    demo()
