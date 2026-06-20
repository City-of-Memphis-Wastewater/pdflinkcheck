# src/pdflinkcheck/drivers/pymupdf_driver.py
from __future__ import annotations
import logging
from typing import Dict, Any, List, Optional
import fitz  # PyMuPDF

from ..page import PageRef
from ..taxonomy import (
    PYMUPDF_KIND_LOOKUP,
    SourceKindPyMuPDF,
    create_link_dict,
)

logger = logging.getLogger(__name__)

def extract_links_pymupdf(doc: fitz.Document) -> List[Dict[str, Any]]:
    """
    Iterates through a PDF document using PyMuPDF, mapping raw engine integer kinds 
    directly against the centralized taxonomy matrix lookup accelerator.
    """
    all_links: List[Dict[str, Any]] = []
    
    for page_idx, page in enumerate(doc):
        page_source = PageRef.from_index(page_idx)
        
        # Load interactive links collection surfaced by PyMuPDF's layout tree
        links = page.get_links()
        
        for link_dict in links:
            # Extract raw engine integer pattern matching (e.g., fitz.LINK_GOTO = 1)
            raw_kind = link_dict.get("kind")
            if raw_kind is None:
                continue
                
            # --- Centralized Routing Core ---
            # Fallback to the OTHER definition if the engine encounters an out-of-bounds type
            taxonomy = PYMUPDF_KIND_LOOKUP.get(raw_kind)
            if taxonomy is None:
                fallback_kind = None  # Maps straight to SourceKindPyMuPDF.LINK_OTHER
                for t in PYMUPDF_KIND_LOOKUP.values():
                    if t.pymupdf_source == SourceKindPyMuPDF.LINK_OTHER:
                        taxonomy = t
                        break
            
            # Data Extraction payloads
            url: Optional[str] = None
            destination_page: Optional[int] = None
            remote_file: Optional[str] = None
            file: Optional[str] = None
            
            # --- Pure Data-Extraction Phase ---
            # Evaluated securely via structural source enums determined by taxonomy matrix
            if taxonomy.pymupdf_source == SourceKindPyMuPDF.LINK_URI:
                url = link_dict.get("uri")
                
            elif taxonomy.pymupdf_source in (SourceKindPyMuPDF.LINK_GOTO, SourceKindPyMuPDF.LINK_NONE):
                # PyMuPDF normalizes internal targets down to a 0-indexed integer destination page
                page_target = link_dict.get("page")
                if page_target is not None and page_target >= 0:
                    destination_page = PageRef.from_index(page_target).machine
                    
            elif taxonomy.pymupdf_source == SourceKindPyMuPDF.LINK_GOTOR:
                remote_file = link_dict.get("file")
                # PyMuPDF bundles sub-target tracking information inside the payload dictionary
                # inside the 'page' or 'dest' keys for cross-file navigation
                
            elif taxonomy.pymupdf_source == SourceKindPyMuPDF.LINK_LAUNCH:
                file = link_dict.get("file")

            # Extract normalized rectangle coordinates [x0, y0, x1, y1]
            rect_obj = link_dict.get("from")
            rect_norm = [rect_obj.x0, rect_obj.y0, rect_obj.x1, rect_obj.y1] if rect_obj else None

            # Look up localized overlap string within interactive bounds
            anchor_text = ""
            if rect_obj:
                try:
                    anchor_text = page.get_text("text", clip=rect_obj).strip()[:50]
                except Exception:
                    pass

            # Dispatch structured record to global reporting factory
            link_record = create_link_dict(
                source_page_ref=page_source,
                rect_norm=rect_norm,
                anchor_text=anchor_text,
                link_type=taxonomy.link_type.value,
                item_category=taxonomy.item_category.value,
                target_type=taxonomy.target_type,
                source_kind=taxonomy.pymupdf_source.value,
                destination_page=destination_page,
                url=url,
                remote_file=remote_file,
                file=file,
                xref=link_dict.get("xref")  # Surfaces true low-level PDF table cross-reference IDs
            )
            all_links.append(link_record)
            
    return all_links
