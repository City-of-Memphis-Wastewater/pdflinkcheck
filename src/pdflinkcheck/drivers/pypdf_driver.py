# src/pdflinkcheck/drivers/pypdf_driver.py
from __future__ import annotations
import logging
from typing import Dict, Any, List, Optional, Union
from pypdf import PdfReader

from ..page import PageRef
from ..taxonomy import (
    PdfToken,
    SourceKindPyPDF,
    route_pypdf_dictionary,
    create_link_dict,
)

logger = logging.getLogger(__name__)

def _resolve_pypdf_destination(
    reader: PdfReader, 
    dest: Any, 
    obj_id_to_page: Dict[int, int]
) -> Optional[int]:
    """
    Resolves complex polymorphic pypdf destinations (Direct Arrays, Indirect Objects, 
    or Named Destination Strings) down to a zero-indexed machine page number.
    """
    if dest is None:
        return None

    # Handle Named Destination string lookups (/NamedDestinations)
    if isinstance(dest, str):
        try:
            named_dests = reader.named_destinations
            if dest in named_dests:
                return _resolve_pypdf_destination(reader, named_dests[dest], obj_id_to_page)
        except Exception as e:
            logger.debug(f"Failed resolving named destination string '{dest}': {e}")
        return None

    # Handle IndirectObject reference dictionaries
    if hasattr(dest, "get_object"):
        obj = dest.get_object()
        if isinstance(obj, list) and len(obj) > 0:
            return _resolve_pypdf_destination(reader, obj, obj_id_to_page)
        if hasattr(obj, "indirect_reference"):
            ref_id = obj.indirect_reference.idnum
            return obj_id_to_page.get(ref_id)

    # Handle standard Direct Arrays: [IndirectObject(PageRef), /XYZ, left, top, zoom]
    if isinstance(dest, list) and len(dest) > 0:
        page_obj = dest[0]
        if hasattr(page_obj, "indirect_reference"):
            ref_id = page_obj.indirect_reference.idnum
            return obj_id_to_page.get(ref_id)
        if hasattr(page_obj, "get_object"):
            resolved_page = page_obj.get_object()
            if hasattr(resolved_page, "indirect_reference"):
                return obj_id_to_page.get(resolved_page.indirect_reference.idnum)

    return None

def _get_anchor_text_pypdf(page: Any, rect: Optional[List[float]]) -> str:
    """Extracts overlapping string primitives within the link bounding box."""
    if not rect:
        return ""
    try:
        return page.extract_text().strip()[:50]
    except Exception:
        return ""

def extract_links_pypdf(reader: PdfReader) -> List[Dict[str, Any]]:
    """
    Iterates through a PDF document using pypdf, offloading all ISO 32000 structural 
    routing logic and classification decisions directly to the taxonomy matrix.
    """
    # High-speed index matching IndirectObject IDs to 0-indexed page indices
    obj_id_to_page = {
        page.indirect_reference.idnum: i
        for i, page in enumerate(reader.pages)
    }

    all_links: List[Dict[str, Any]] = []
    
    for i, page in enumerate(reader.pages):
        page_source = PageRef.from_index(i)
        
        if PdfToken.ANNOTS_KEY not in page:
            continue
            
        annots = page[PdfToken.ANNOTS_KEY]
        if hasattr(annots, "get_object"):
            annots = annots.get_object()

        for annot in annots:
            obj = annot.get_object()
            if obj.get(PdfToken.SUBTYPE_KEY) != PdfToken.LINK_VALUE:
                continue

            rect = obj.get(PdfToken.RECT_KEY)
            anchor_text = _get_anchor_text_pypdf(page, rect)

            # --- Centralized Routing Core ---
            taxonomy = route_pypdf_dictionary(obj)

            # Data Extraction payloads
            url: Optional[str] = None
            destination_page: Optional[int] = None
            remote_file: Optional[str] = None
            file: Optional[str] = None
            
            # --- Pure Data-Extraction Phase ---
            if taxonomy.pypdf_source == SourceKindPyPDF.ANNOT_URI:
                action = obj[PdfToken.ACTION_KEY].get_object()
                url = str(action[PdfToken.PARAM_URI])
                
            elif taxonomy.pypdf_source in (SourceKindPyPDF.ANNOT_ACTION_DEST, SourceKindPyPDF.ANNOT_DIRECT_DEST):
                if taxonomy.pypdf_source == SourceKindPyPDF.ANNOT_DIRECT_DEST:
                    dest = obj.get(PdfToken.DEST_KEY)
                else:
                    action = obj[PdfToken.ACTION_KEY].get_object()
                    dest = action.get(PdfToken.PARAM_D)
                    
                target_page_idx = _resolve_pypdf_destination(reader, dest, obj_id_to_page)
                if target_page_idx is not None:
                    destination_page = PageRef.from_index(target_page_idx).machine
                    
            elif taxonomy.pypdf_source == SourceKindPyPDF.ANNOT_GOTOR:
                action = obj[PdfToken.ACTION_KEY].get_object()
                remote_file = str(action.get(PdfToken.FILE_SPEC_KEY) or "")
                
            elif taxonomy.pypdf_source == SourceKindPyPDF.ANNOT_LAUNCH:
                action = obj[PdfToken.ACTION_KEY].get_object()
                file = str(action.get(PdfToken.FILE_SPEC_KEY) or "")

            # Dispatch structured record to the global reporting factory
            link_record = create_link_dict(
                source_page_ref=page_source, 
                rect_norm=list(rect) if rect else None,
                anchor_text=anchor_text,
                link_type=taxonomy.link_type.value,
                item_category=taxonomy.item_category.value,
                target_type=taxonomy.target_type,
                source_kind=taxonomy.pypdf_source.value,
                destination_page=destination_page,
                url=url,
                remote_file=remote_file,
                file=file,
                xref=None
            )
            all_links.append(link_record)
                        
    return all_links


