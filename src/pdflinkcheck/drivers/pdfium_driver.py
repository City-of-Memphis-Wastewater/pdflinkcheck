# src/pdflinkcheck/drivers/pdfium_driver.py
from __future__ import annotations
import logging
from typing import Dict, Any, List, Optional
import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c

from ..page import PageRef
from ..taxonomy import (
    PDFIUM_KIND_LOOKUP,
    SourceKindPdfium,
    create_link_dict,
)

logger = logging.getLogger(__name__)

def extract_links_pdfium(doc: pdfium.PdfDocument) -> List[Dict[str, Any]]:
    """
    Iterates through a PDF document using pypdfium2, evaluating annotation and 
    action structures natively via the central taxonomy integer registry.
    """
    all_links: List[Dict[str, Any]] = []
    
    for page_idx, page in enumerate(doc):
        page_source = PageRef.from_index(page_idx)
        
        # Load PDFium page architecture and capture boundaries
        for annot in page.get_annotations():
            # Filter strictly on interactive link elements
            if annot.get_type() != pdfium_c.FPDF_ANNOT_LINK:
                continue
                
            # Extract raw link action bound to the annotation object
            raw_annot = annot.raw
            action = pdfium_c.FPDFLink_GetAction(raw_annot)
            
            raw_kind = None
            if action:
                # Resolve action signature type integer (GOTO=1, URI=2, GOTOR=3, LAUNCH=4)
                raw_kind = pdfium_c.FPDFAction_GetType(action)
                
            # --- Centralized Routing Core ---
            # If no action exists but there is a direct layout mapping destination,
            # raw_kind remains None, mapping cleanly to ANNOT_DIRECT_DEST via our matrix fallback.
            taxonomy = PDFIUM_KIND_LOOKUP.get(raw_kind)
            if taxonomy is None:
                target_source = (
                    SourceKindPdfium.ANNOT_DIRECT_DEST 
                    if not action 
                    else SourceKindPdfium.ANNOT_OTHER
                )
                for t in PDFIUM_KIND_LOOKUP.values():
                    if t.pdfium_source == target_source:
                        taxonomy = t
                        break

            # Data Extraction payloads
            url: Optional[str] = None
            destination_page: Optional[int] = None
            remote_file: Optional[str] = None
            file: Optional[str] = None
            
            # --- Pure Data-Extraction Phase ---
            if taxonomy.pdfium_source == SourceKindPdfium.ANNOT_URI:
                # Extract text buffer directly out of PDFium memory structure allocation
                buflen = pdfium_c.FPDFAction_GetURIPath(doc.raw, action, None, 0)
                if buflen > 0:
                    buffer = bytearray(buflen)
                    # Create explicit raw type pointer mapping for safe retrieval
                    ffi_buffer = pdfium_c.ffi.from_buffer(buffer)
                    pdfium_c.FPDFAction_GetURIPath(doc.raw, action, ffi_buffer, buflen)
                    url = buffer.decode("utf-8").strip("\x00")
                    
            elif taxonomy.pdfium_source in (SourceKindPdfium.ANNOT_GOTO, SourceKindPdfium.ANNOT_DIRECT_DEST):
                # Handle target calculations via direct action or absolute layout map destination
                dest = (
                    pdfium_c.FPDFLink_GetDest(doc.raw, raw_annot) 
                    if taxonomy.pdfium_source == SourceKindPdfium.ANNOT_DIRECT_DEST 
                    else pdfium_c.FPDFAction_GetDest(doc.raw, action)
                )
                if dest:
                    target_idx = pdfium_c.FPDFDest_GetDestPageIndex(doc.raw, dest)
                    if target_idx >= 0:
                        destination_page = PageRef.from_index(target_idx).machine
                        
            elif taxonomy.pdfium_source == SourceKindPdfium.ANNOT_GOTOR:
                # PDFium tracks remote file routes via action filepath allocations
                buflen = pdfium_c.FPDFAction_GetFilePath(action, None, 0)
                if buflen > 0:
                    buffer = bytearray(buflen)
                    ffi_buffer = pdfium_c.ffi.from_buffer(buffer)
                    pdfium_c.FPDFAction_GetFilePath(action, ffi_buffer, buflen)
                    remote_file = buffer.decode("utf-8").strip("\x00")
                    
            elif taxonomy.pdfium_source == SourceKindPdfium.ANNOT_LAUNCH:
                buflen = pdfium_c.FPDFAction_GetFilePath(action, None, 0)
                if buflen > 0:
                    buffer = bytearray(buflen)
                    ffi_buffer = pdfium_c.ffi.from_buffer(buffer)
                    pdfium_c.FPDFAction_GetFilePath(action, ffi_buffer, buflen)
                    file = buffer.decode("utf-8").strip("\x00")

            # Extract normalized rectangle coordinates from PDFium bounding boxes
            rect_norm = None
            fs_rect = pdfium_c.FS_RECTF()
            if pdfium_c.FPDFAnnot_GetRect(raw_annot, fs_rect):
                rect_norm = [fs_rect.left, fs_rect.bottom, fs_rect.right, fs_rect.top]

            # Look up overlapping text strings localized on the page canvas layer
            anchor_text = ""
            if rect_norm:
                try:
                    # PDFium standard text search bounds check mapping snippet
                    text_page = pdfium_c.FPDFText_LoadPage(page.raw)
                    # Convert bounding rect float mappings to character index ranges
                    char_count = pdfium_c.FPDFText_CountChars(text_page)
                    # Simple text fallback capture; can be constrained cleanly by location clipping
                    anchor_text = page.get_text_bounded(
                        left=fs_rect.left, 
                        bottom=fs_rect.bottom, 
                        right=fs_rect.right, 
                        top=fs_rect.top
                    ).strip()[:50]
                    pdfium_c.FPDFText_ClosePage(text_page)
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
                source_kind=taxonomy.pdfium_source.value,
                destination_page=destination_page,
                url=url,
                remote_file=remote_file,
                file=file,
                xref=None  # PDFium relies heavily on transient memory pointer references over raw table xrefs
            )
            all_links.append(link_record)
            
    return all_links
