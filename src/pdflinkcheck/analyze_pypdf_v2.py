# src/pdflinkcheck/analyze_pypdf.py
import sys
from pathlib import Path
import logging
from typing import Dict, Any, List

from pypdf import PdfReader
from pypdf.generic import Destination, NameObject, IndirectObject

from pdflinkcheck.report import run_report
#from pdflinkcheck.validate import run_validation

"""
Inspect target PDF for both URI links and GoTo links, using only pypdf (no PyMuPDF/Fitz).
Fully fixed and improved version as of December 2025 (compatible with pypdf >= 4.0).
"""

def get_anchor_text_pypdf(page, rect) -> str:
    """
    Extracts text that falls within or near the link's bounding box using a visitor function.
    This is a reliable pure-pypdf method for associating visible text with a link annotation.
    """
    if not rect:
        return "N/A: Missing Rect"

    # PDF coordinates: bottom-left origin. Rect is [x0, y0, x1, y1]
    # Standardize Rect: [x_min, y_min, x_max, y_max]
    # Some PDF generators write Rect as [x_max, y_max, x_min, y_min]
    x_min, y_min, x_max, y_max = rect[0], rect[1], rect[2], rect[3]
    if x_min > x_max: x_min, x_max = x_max, x_min
    if y_min > y_max: y_min, y_max = y_max, y_min

    parts: List[str] = []

    def visitor_body(text: str, cm, tm, font_dict, font_size):
        # tm[4] and tm[5] are the (x, y) coordinates of the text insertion point
        x, y = tm[4], tm[5]

        # Guard against missing font_size
        actual_font_size = font_size if font_size else 10


        # Approximate Center-Alignment Check
        # Since tm[4/5] is usually the bottom-left of the character, 
        # we shift our 'check point' slightly up and to the right based 
        # on font size to approximate the center of the character.
        char_center_x = x + (actual_font_size / 4)
        char_center_y = y + (actual_font_size / 3)

        # Asymmetric Tolerance
        # We use a tighter vertical tolerance (3pt) to avoid catching lines above/below.
        # We use a wider horizontal tolerance (10pt) to catch kerning/spacing issues.
        v_tol = 3 
        h_tol = 10
        if (x_min - h_tol) <= char_center_x <= (x_max + h_tol) and \
        (y_min - v_tol) <= char_center_y <= (y_max + v_tol):
            if text.strip():
                parts.append(text)
                
    # Extract text using the visitor – this preserves drawing order
    page.extract_text(visitor_text=visitor_body)

    raw = "".join(parts)
    cleaned = " ".join(raw.split()).strip()

    return cleaned if cleaned else "Graphic/Empty Link"


def resolve_pypdf_destination(reader: PdfReader, dest) -> str:
    """
    Resolves any form of destination (/Dest or /A /D) to a human-readable page number.
    Uses the official pypdf helper when possible for maximum reliability.
    """
    try:
        if dest is None:
            return "N/A"
        
        # If it's an IndirectObject, resolve it first
        if isinstance(dest, (IndirectObject, NameObject)):
            dest = dest.get_object()
        
        # Named destinations or explicit destinations are handled correctly by this method
        if isinstance(dest, Destination):
            return str(reader.get_destination_page_number(dest) + 1)

        # Direct array or indirect reference
        page_num = reader.get_destination_page_number(dest)
        return str(page_num + 1)

    except Exception:
        return "Unknown/Error"


def extract_links_pypdf(pdf_path: Path | str) -> List[Dict[str, Any]]:
    """
    Extract all link annotations (URI, internal GoTo, remote GoToR) using pure pypdf.
    Output schema matches typical reporting needs.
    """
    reader = PdfReader(pdf_path)

    all_links: List[Dict[str, Any]] = []

    for i, page in enumerate(reader.pages):
        page_num = i + 1

        if "/Annots" not in page:
            continue

        annots = page["/Annots"]
        for annot_ref in annots:
            try:
                annot = annot_ref.get_object()
            except Exception:
                continue  # Corrupted annotation – skip

            if annot.get("/Subtype") != "/Link":
                continue

            rect = annot.get("/Rect")
            anchor_text = get_anchor_text_pypdf(page, rect)

            link_dict: Dict[str, Any] = {
                "page": page_num,
                "rect": list(rect) if rect else None,
                "link_text": anchor_text,
                "type": "Other Action",
                "target": "Unknown",
            }

            action = annot.get("/A")

            # External URI link
            if action and action.get("/URI"):
                uri = action["/URI"]
                link_dict.update({
                    "type": "External (URI)",
                    "url": str(uri),
                    "target": str(uri),
                })

            # Internal GoTo – can be /Dest directly or inside /A /D
            elif annot.get("/Dest") or (action and action.get("/D")):
                dest = annot.get("/Dest") or (action and action["/D"])
                target_page = resolve_pypdf_destination(reader, dest)
                link_dict.update({
                    "type": "Internal (GoTo/Dest)",
                    "destination_page": target_page,
                    "target": f"Page {target_page}",
                })

            # Remote GoToR (links to another PDF file)
            elif action and action.get("/S") == "/GoToR":
                file_spec = action.get("/F")
                remote_file = str(file_spec) if file_spec else "Unknown File"
                remote_dest = action.get("/D")
                remote_target = f"File: {remote_file}"
                if remote_dest:
                    remote_target += f" → Dest: {remote_dest}"
                link_dict.update({
                    "type": "Remote (GoToR)",
                    "remote_file": remote_file,
                    "target": remote_target,
                })

            all_links.append(link_dict)

    return all_links


def extract_toc_pypdf(pdf_path: Path | str) -> List[Dict[str, Any]]:
    """
    Extract the PDF outline (bookmarks / table of contents) using pypdf.
    Correctly handles nested structure and uses the official page resolution method.
    """
    try:
        reader = PdfReader(pdf_path)
        outline = reader.outline
        if not outline:
            return []

        toc_data: List[Dict[str, Any]] = []

        def flatten_outline(items: List, level: int = 1):
            for item in items:
                if isinstance(item, Destination):
                    try:
                        page_num = reader.get_destination_page_number(item) + 1
                    except Exception:
                        page_num = "N/A"

                    toc_data.append({
                        "level": level,
                        "title": item.title or "(Untitled)",
                        "target_page": page_num,
                    })
                elif isinstance(item, list):
                    # Recurse into child entries
                    flatten_outline(item, level + 1)

        flatten_outline(outline)
        return toc_data

    except Exception as e:
        print(f"TOC extraction error: {e}", file=sys.stderr)
        return []


def call_stable():
    """
    Entry point for command-line execution or integration with reporting module.
    """
    run_report(library_pdf="pypdf")
    # run_validation(library_pdf="pypdf")  # Uncomment if validation step is needed
    

if __name__ == "__main__":
    call_stable()
    # pypdf version updates