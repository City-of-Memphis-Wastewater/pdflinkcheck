# src/pdflinkcheck/taxonomy.py
from __future__ import annotations

import enum
import uuid
from typing import Dict, Any, Optional, NamedTuple, List

class TargetType(str,enum.Enum):
    URL = "url"
    FILE = "file"
    REMOTE_FILE = "remote_file"
    OTHER = "other"
    PAGE = "page"
    DESTINATION_PAGE = "destination_page" # link jargon, just means PAGE
    #TARGET_PAGE = "target_page" # TOC jargon, just means PAGE
    
class LinkType(str, enum.Enum):
    """Normalized categories of extracted document elements for reporting/filtering."""
    INTERNAL_GOTO = "Internal (GoTo/Dest)"
    INTERNAL_RESOLVED = "Internal (Resolved Action)"
    EXTERNAL = "External (URI)"
    REMOTE_GOTOR = "Remote (GoToR)"
    LAUNCH = "Launch"
    OTHER = "Other Action"

class ItemCategory(str, enum.Enum):
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
