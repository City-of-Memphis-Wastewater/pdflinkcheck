# src/pdflinkcheck/taxonomy.py
from __future__ import annotations
from enum import Enum
import uuid
from xmlrpc.client import INTERNAL_ERROR

from typing import Dict, Any, Optional, NamedTuple, List
import logging

logger = logging.getLogger(__name__)

from .page import PageRef

class TargetType(str,Enum):
    URL = "url"
    FILE = "file"
    REMOTE_FILE = "remote_file"
    OTHER = "other"
    PAGE = "page"
    DESTINATION_PAGE = "destination_page" # link jargon, just means PAGE
    #TARGET_PAGE = "target_page" # TOC jargon, just means PAGE
    
class LinkType(str, Enum):
    """Normalized categories of extracted document elements for reporting/filtering."""
    INTERNAL_GOTO = "Internal (GoTo/Dest)"
    INTERNAL_RESOLVED = "Internal (Resolved Action)"
    EXTERNAL = "External (URI)"
    REMOTE_GOTOR = "Remote (GoToR)"
    LAUNCH = "Launch"
    OTHER = "Other Action"

class ItemCategory(str, Enum):
    INTERNAL = "internal"
    EXTERNAL = "external"
    OTHER = "other"
    TOC = "toc"

class EngineTaxonomy(NamedTuple):
    item_category: ItemCategory
    link_type: LinkType
    target_type: TargetType
    pymupdf_kind: Optional[int]
    pypdf_kind: Optional[str]
    pdfium_kind: Optional[int]

# The Unified Single Source of Truth Table
TAXONOMY_REGISTRY: List[EngineTaxonomy] = [
    EngineTaxonomy(
        item_category=ItemCategory.INTERNAL,
        link_type=LinkType.INTERNAL_GOTO,
        target_type=TargetType.DESTINATION_PAGE,
        pymupdf_kind=1,      # fitz.LINK_GOTO
        pypdf_kind="ANNOT_ACTION_DEST",
        pdfium_kind=1,       # PdfActionType.GOTO
    ),
    EngineTaxonomy(
        item_category=ItemCategory.INTERNAL,
        link_type=LinkType.INTERNAL_RESOLVED,
        target_type=TargetType.DESTINATION_PAGE,
        pymupdf_kind=None,   # Resolved contextually via p_index presence
        pypdf_kind="ANNOT_DIRECT_DEST",
        pdfium_kind=None,
    ),
    EngineTaxonomy(
        item_category=ItemCategory.EXTERNAL,
        link_type=LinkType.EXTERNAL,
        target_type=TargetType.URL,
        pymupdf_kind=2,      # fitz.LINK_URI
        pypdf_kind="ANNOT_URI",
        pdfium_kind=2,       # PdfActionType.URI
    ),
    EngineTaxonomy(
        item_category=ItemCategory.EXTERNAL,
        link_type=LinkType.REMOTE_GOTOR,
        target_type=TargetType.REMOTE_FILE,
        pymupdf_kind=3,      # fitz.LINK_GOTOR
        pypdf_kind="ANNOT_GOTOR",
        pdfium_kind=3,       # PdfActionType.GOTOR
    ),
    EngineTaxonomy(
        item_category=ItemCategory.EXTERNAL,
        link_type=LinkType.LAUNCH,
        target_type=TargetType.FILE,
        pymupdf_kind=5,      # fitz.LINK_LAUNCH
        pypdf_kind="ANNOT_LAUNCH",
        pdfium_kind=4,       # PdfActionType.LAUNCH
    ),
    EngineTaxonomy(
        item_category=ItemCategory.OTHER,
        link_type=LinkType.OTHER,
        target_type=TargetType.OTHER,
        pymupdf_kind=None,   # Fallback capture
        pypdf_kind="ANNOT_OTHER",
        pdfium_kind=None,
    )
]

# High-Performance Compiled Lookups for Factory Optimization
PYMUPDF_LOOKUP: Dict[int, EngineTaxonomy] = {
    t.pymupdf_kind: t for t in TAXONOMY_REGISTRY if t.pymupdf_kind is not None
}
PYPDF_LOOKUP: Dict[str, EngineTaxonomy] = {
    t.pypdf_kind: t for t in TAXONOMY_REGISTRY if t.pypdf_kind is not None
}
PDFIUM_LOOKUP: Dict[int, EngineTaxonomy] = {
    t.pdfium_kind: t for t in TAXONOMY_REGISTRY if t.pdfium_kind is not None
}

# ---


def create_toc_dict(
        level,
        title:str,
        target_page
)->Dict[str,Any]:
    return {
        "GUID":str(uuid.uuid4()),
        "details":{
            "level": level, 
            "title": title, 
            "target_page": target_page,
            "item_category":ItemCategory.TOC.value,
            "target_type": TargetType.PAGE.value,
        }
    }

def create_link_dict(
    source_page_ref: PageRef,
    rect_norm: Optional[tuple],
    anchor_text: str,
    link_type: str,
    item_category: str,
    source_kind: Any,
    # Explicitly define target payload options with defaults
    target_type: Optional[Any] = None,
    destination_page: Optional[Any] = None,
    destination_view: Optional[Any] = None,
    url: Optional[str] = None,
    remote_file: Optional[str] = None,
    file: Optional[str] = None,
    params: Optional[str] = None,
    xref: Optional[int] = None,
    action_kind: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Central factory method ensuring all keys are populated with 
    standard defaults, preventing schema drift across PDF engines.
    """
    base =  {
        "page": source_page_ref.machine, # Always normalized machine index (int)
        "rect": rect_norm,
        "anchor_text": anchor_text,
        "link_type": link_type,
        "item_category": item_category, 
        "source_kind": str(source_kind) if source_kind is not None else "",
        # --- Inconsistent terms ---
        "target_type": target_type,
        "xref": xref,
        "destination_page": destination_page,
        "destination_view": destination_view,
        "url": url,
        "remote_file": remote_file,
        "action_kind": action_kind,
        "file": file,
        "params": params,
    }
    structure = {
        "GUID": str(uuid.uuid4()),
        "details": base,
        "target_validation":{
            "status":"unverified",
            "reason": None,
        },
        "security_risk":{}
    }
    #return base
    return structure


# ---- EXPERIMENTAL, DETRITIS ----

class ElementRelationship(NamedTuple):
    item_category: ItemCategory
    link_type: Optional[LinkType]
    target_type: TargetType

# The OUTDATED Dichotomous Reference Matrix, ALSO handled by TAXONOMY_REGISTRY and EngineTaxonomy
TAXONOMY_MATRIX: List[ElementRelationship] = [
    # TOC Elements
    ElementRelationship(ItemCategory.TOC, None, TargetType.PAGE),
    
    # Internal Annotations
    ElementRelationship(ItemCategory.INTERNAL, LinkType.INTERNAL_GOTO, TargetType.DESTINATION_PAGE),
    ElementRelationship(ItemCategory.INTERNAL, LinkType.INTERNAL_RESOLVED, TargetType.DESTINATION_PAGE),
    
    # External Annotations
    ElementRelationship(ItemCategory.EXTERNAL, LinkType.EXTERNAL, TargetType.URL),
    ElementRelationship(ItemCategory.EXTERNAL, LinkType.REMOTE_GOTOR, TargetType.REMOTE_FILE),
    ElementRelationship(ItemCategory.EXTERNAL, LinkType.LAUNCH, TargetType.FILE),
    
    # Fallback/Other Handlers
    ElementRelationship(ItemCategory.OTHER, LinkType.OTHER, TargetType.OTHER),
]
