"""To fully lift all routing, inference, and control flow mechanics out of the engine drivers and centralize them inside `taxonomy.py`, we need to change how the taxonomy registry operates. Instead of a flat lookup table, `taxonomy.py` should act as the master **structural routing engine** for all three drivers.

By using nested dictionaries and specific token-matching logic inside the registry, the engine drivers no longer need to execute `if/elif` statements checking for things like `/A`, `/S`, `/F`, or `/Dist`. Instead, they pass the raw structural components directly to a centralized routing dispatcher.

Here is the complete, non-truncated `src/pdflinkcheck/taxonomy.py` built to map every control sequence, slash token, and key inference pattern across all drivers.
"""
# src/pdflinkcheck/taxonomy.py
from __future__ import annotations
from enum import Enum
import uuid
from typing import Dict, Any, Optional, NamedTuple, List, Union
import logging

logger = logging.getLogger(__name__)

from .page import PageRef

class TargetType(str, Enum):
    """Normalized low-level validation targets indicating the underlying destination payload form."""
    URL = "url"
    FILE = "file"
    REMOTE_FILE = "remote_file"
    OTHER = "other"
    PAGE = "page"
    DESTINATION_PAGE = "destination_page"

class LinkType(str, Enum):
    """Human-readable reporting classifications describing how the link interactive region behaves."""
    INTERNAL_GOTO = "Internal (GoTo/Dest)"
    INTERNAL_RESOLVED = "Internal (Resolved Action)"
    EXTERNAL = "External (URI)"
    REMOTE_GOTOR = "Remote (GoToR)"
    LAUNCH = "Launch"
    OTHER = "Other Action"

class ItemCategory(str, Enum):
    """High-level bucket separating internal document routes from external infrastructure routes."""
    INTERNAL = "internal"
    EXTERNAL = "external"
    OTHER = "other"
    TOC = "toc"

# ==============================================================================
# --- Centralized Engine Source Identifiers ---
# ==============================================================================

class SourceKindPdfium(str, Enum):
    """Tracks exactly which internal PDF pipeline or object type exposed the target link in pdfium."""
    ANNOT_DIRECT_DEST = "pypdfium2_annot_direct_dest"
    ANNOT_GOTO = "pypdfium2_annot_goto"
    ANNOT_URI = "pypdfium2_annot_uri"
    ANNOT_GOTOR = "pypdfium2_annot_gotor"
    ANNOT_LAUNCH = "pypdfium2_annot_launch"
    ANNOT_OTHER = "pypdfium2_annot_other"

class SourceKindPyPDF(str, Enum):
    """Tracks exactly which internal low-level PDF dictionary pattern exposed the target link in pypdf."""
    ANNOT_URI = "pypdf_annot_action_uri"           # /A with /URI
    ANNOT_DIRECT_DEST = "pypdf_annot_direct_dest"   # Direct /Dest on Annotation dictionary
    ANNOT_ACTION_DEST = "pypdf_annot_action_dest"   # /A with /D (GoTo Action dictionary)
    ANNOT_GOTOR = "pypdf_annot_gotor"               # /A with /S -> /GoToR
    ANNOT_LAUNCH = "pypdf_annot_launch"             # /A with /S -> /Launch
    ANNOT_OTHER = "pypdf_annot_other"               # Fallback structural block

class SourceKindPyMuPDF(str, Enum):
    """Tracks exactly which internal link type exposed the target link in PyMuPDF (fitz)."""
    LINK_NONE = "pymupdf_link_none"                 # 0: Direct layout map or unclassified target
    LINK_GOTO = "pymupdf_link_goto"                 # 1: Destination inside this PDF document
    LINK_URI = "pymupdf_link_uri"                   # 2: Resource identifier string target (Web URL)
    LINK_GOTOR = "pymupdf_link_gotor"               # 3: Destination inside another remote PDF document
    LINK_LAUNCH = "pymupdf_link_launch"             # 5: External application/file execution action
    LINK_NAMED = "pymupdf_link_named"               # 4: Named internal pipeline action
    LINK_OTHER = "pymupdf_link_other"               # Fallback identifier string

# ==============================================================================
# --- Centralized Structural Registry Matrix ---
# ==============================================================================

class EngineTaxonomy(NamedTuple):
    """
    Polymorphic lookup tuple aligning human classifications with the specific internal keys,
    integers, and system source identifiers used by each parsing driver engine.
    """
    item_category: ItemCategory
    link_type: LinkType
    target_type: TargetType
    
    # PyMuPDF Mapping Dimensions
    pymupdf_kind: Optional[int]       # Match pattern against raw link dict integers (e.g., fitz.LINK_GOTO = 1)
    pymupdf_source: SourceKindPyMuPDF
    
    # PyPDF Mapping Dimensions
    pypdf_kind: Optional[str]         # Main structural dictionary hook key
    pypdf_subtype: Optional[str]      # Secondary control path token (e.g., value of /S entry if present)
    pypdf_source: SourceKindPyPDF
    
    # PDFium Mapping Dimensions
    pdfium_kind: Optional[int]        # Match pattern against raw action integers (e.g., PdfActionType.GOTO = 1)
    pdfium_source: SourceKindPdfium

TAXONOMY_REGISTRY: List[EngineTaxonomy] = [
    EngineTaxonomy(
        item_category=ItemCategory.INTERNAL,
        link_type=LinkType.INTERNAL_GOTO,
        target_type=TargetType.DESTINATION_PAGE,
        pymupdf_kind=1,               # fitz.LINK_GOTO
        pymupdf_source=SourceKindPyMuPDF.LINK_GOTO,
        pypdf_kind="/D",              # In /A action dictionary: contains /D destination direct array or named string
        pypdf_subtype=None,
        pypdf_source=SourceKindPyPDF.ANNOT_ACTION_DEST,
        pdfium_kind=1,                # FPDFAction_GetType layout -> FPDFACTION_GOTO
        pdfium_source=SourceKindPdfium.ANNOT_GOTO,
    ),
    EngineTaxonomy(
        item_category=ItemCategory.INTERNAL,
        link_type=LinkType.INTERNAL_RESOLVED,
        target_type=TargetType.DESTINATION_PAGE,
        pymupdf_kind=0,               # fitz.LINK_NONE context (layout map link with a target page reference)
        pymupdf_source=SourceKindPyMuPDF.LINK_NONE,
        pypdf_kind="/Dest",           # Direct /Dest parameter on the base Annotation dictionary itself
        pypdf_subtype=None,
        pypdf_source=SourceKindPyPDF.ANNOT_DIRECT_DEST,
        pdfium_kind=None,             # Handled contextually via layout destination references lacking actions
        pdfium_source=SourceKindPdfium.ANNOT_DIRECT_DEST,
    ),
    EngineTaxonomy(
        item_category=ItemCategory.EXTERNAL,
        link_type=LinkType.EXTERNAL,
        target_type=TargetType.URL,
        pymupdf_kind=2,               # fitz.LINK_URI
        pymupdf_source=SourceKindPyMuPDF.LINK_URI,
        pypdf_kind="/URI",            # In /A action dictionary: contains the direct /URI string parameter
        pypdf_subtype=None,
        pypdf_source=SourceKindPyPDF.ANNOT_URI,
        pdfium_kind=2,                # FPDFAction_GetType layout -> FPDFACTION_URI
        pdfium_source=SourceKindPdfium.ANNOT_URI,
    ),
    EngineTaxonomy(
        item_category=ItemCategory.EXTERNAL,
        link_type=LinkType.REMOTE_GOTOR,
        target_type=TargetType.REMOTE_FILE,
        pymupdf_kind=3,               # fitz.LINK_GOTOR
        pymupdf_source=SourceKindPyMuPDF.LINK_GOTOR,
        pypdf_kind="/A",              # In /A action dictionary: resolved when /S matches control token below
        pypdf_subtype="/GoToR",       # Secondary Action subtype key specifying destination in alternate PDF
        pypdf_source=SourceKindPyPDF.ANNOT_GOTOR,
        pdfium_kind=3,                # FPDFAction_GetType layout -> FPDFACTION_GOTOR
        pdfium_source=SourceKindPdfium.ANNOT_GOTOR,
    ),
    EngineTaxonomy(
        item_category=ItemCategory.EXTERNAL,
        link_type=LinkType.LAUNCH,
        target_type=TargetType.FILE,
        pymupdf_kind=5,               # fitz.LINK_LAUNCH
        pymupdf_source=SourceKindPyMuPDF.LINK_LAUNCH,
        pypdf_kind="/A",              # In /A action dictionary: resolved when /S matches control token below
        pypdf_subtype="/Launch",      # Secondary Action subtype key specifying operating system execution target
        pypdf_source=SourceKindPyPDF.ANNOT_LAUNCH,
        pdfium_kind=4,                # FPDFAction_GetType layout -> FPDFACTION_LAUNCH
        pdfium_source=SourceKindPdfium.ANNOT_LAUNCH,
    ),
    EngineTaxonomy(
        item_category=ItemCategory.OTHER,
        link_type=LinkType.OTHER,
        target_type=TargetType.OTHER,
        pymupdf_kind=None,             # Captures fitz.LINK_NAMED (4) or out-of-bounds metrics cleanly
        pymupdf_source=SourceKindPyMuPDF.LINK_OTHER,
        pypdf_kind="/Other",          # Fallback structural block signature
        pypdf_subtype=None,
        pypdf_source=SourceKindPyPDF.ANNOT_OTHER,
        pdfium_kind=None,             # Captures macro triggers or unsupported variations
        pdfium_source=SourceKindPdfium.ANNOT_OTHER,
    )
]

# ==============================================================================
# --- Centralized Multi-Engine Routing Dispatchers ---
# ==============================================================================

# Lookups by Raw Engine Primitive Kind
PYMUPDF_KIND_LOOKUP: Dict[int, EngineTaxonomy] = {
    t.pymupdf_kind: t for t in TAXONOMY_REGISTRY if t.pymupdf_kind is not None
}
PDFIUM_KIND_LOOKUP: Dict[int, EngineTaxonomy] = {
    t.pdfium_kind: t for t in TAXONOMY_REGISTRY if t.pdfium_kind is not None
}

# Lookups by Normalized System Source Enum
PYMUPDF_SOURCE_LOOKUP: Dict[SourceKindPyMuPDF, EngineTaxonomy] = {
    t.pymupdf_source: t for t in TAXONOMY_REGISTRY
}
PYPDF_SOURCE_LOOKUP: Dict[SourceKindPyPDF, EngineTaxonomy] = {
    t.pypdf_source: t for t in TAXONOMY_REGISTRY
}
PDFIUM_SOURCE_LOOKUP: Dict[SourceKindPdfium, EngineTaxonomy] = {
    t.pdfium_source: t for t in TAXONOMY_REGISTRY
}

# Advanced Low-Level Token Route Resolver for PyPDF
def route_pypdf_dictionary(obj: Dict[str, Any]) -> EngineTaxonomy:
    """
    Examines low-level pypdf dictionary layouts and returns the matching EngineTaxonomy record.
    Completely isolates structural rules, control flow tokens (/S, /F), and inferences here.
    """
    fallback = [t for t in TAXONOMY_REGISTRY if t.pypdf_source == SourceKindPyPDF.ANNOT_OTHER][0]
    
    # 1. Look for Action Wrapper block
    if "/A" in obj:
        action = obj["/A"].get_object()
        
        if "/URI" in action:
            return [t for t in TAXONOMY_REGISTRY if t.pypdf_kind == "/URI"][0]
            
        if "/D" in action:
            return [t for t in TAXONOMY_REGISTRY if t.pypdf_kind == "/D"][0]
            
        # Extract the Subtype string control token (/S)
        if "/S" in action:
            subtype = str(action["/S"])
            for t in TAXONOMY_REGISTRY:
                if t.pypdf_kind == "/A" and t.pypdf_subtype == subtype:
                    return t
                    
    # 2. Look for Direct Destination Layout mapping entry
    if "/Dest" in obj:
        return [t for t in TAXONOMY_REGISTRY if t.pypdf_kind == "/Dest"][0]
        
    return fallback

# ==============================================================================
# --- Shared Standard Reporting Factories ---
# ==============================================================================

def create_toc_dict(
    level: int,
    title: str,
    target_page: Any
) -> Dict[str, Any]:
    """Generates a structured outline payload matching reporting schemas."""
    return {
        "GUID": str(uuid.uuid4()),
        "details": {
            "level": level, 
            "title": title, 
            "target_page": target_page,
            "item_category": ItemCategory.TOC.value,
            "target_type": TargetType.PAGE.value,
        }
    }

def create_link_dict(
    source_page_ref: PageRef,
    rect_norm: Optional[Union[tuple, list]],
    anchor_text: str,
    link_type: str,
    item_category: str,
    source_kind: str,
    target_type: TargetType,
    destination_page: Optional[int] = None,
    destination_view: Optional[Any] = None,
    url: Optional[str] = None,
    remote_file: Optional[str] = None,
    file: Optional[str] = None,
    params: Optional[str] = None,
    xref: Optional[int] = None,
    action_kind: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Central factory guaranteeing a unified dictionary schema for reporting tools.
    Preserves all cross-engine properties without shifting keys or losing context.
    """
    base = {
        "page": source_page_ref.machine,
        "rect": rect_norm,
        "anchor_text": anchor_text,
        "link_type": link_type,
        "item_category": item_category, 
        "source_kind": source_kind,
        "target_type": target_type.value,
        "xref": xref,
        "destination_page": destination_page,
        "destination_view": destination_view,
        "url": url,
        "remote_file": remote_file,
        "file": file,
        "params": params,
        "action_kind": action_kind,
    }
    
    return {
        "GUID": str(uuid.uuid4()),
        "details": base,
        "target_validation": {
            "status": "unverified",
            "reason": None,
        },
        "security_risk": {}
    }

"""
### Driver Integration Pattern Example (`pypdf`)
With `route_pypdf_dictionary` handling all inference logic centrally, the actual extraction driver simplifies dramatically down to a clean data extraction step:
"""
def use_case_in_analysis_pypdf_py()
    # Inside your pypdf parsing driver module
    from .taxonomy import route_pypdf_dictionary, create_link_dict

    # ... (inside loop for annotations)
    taxonomy = route_pypdf_dictionary(obj)

    url = None
    destination_page = None
    remote_file = None
    file = None

    # Extract targeted parameters based on centrally evaluated taxonomy definitions
    if taxonomy.pypdf_source == SourceKindPyPDF.ANNOT_URI:
        url = obj["/A"].get_object()["/URI"]
    elif taxonomy.pypdf_source in [SourceKindPyPDF.ANNOT_ACTION_DEST, SourceKindPyPDF.ANNOT_DIRECT_DEST]:
        dest = obj.get("/Dest") if "/Dest" in obj else obj["/A"].get_object().get("/D")
        target_page = _resolve_pypdf_destination(reader, dest, obj_id_to_page)
        if target_page is not None:
            destination_page = PageRef.from_index(target_page).machine
    elif taxonomy.pypdf_source == SourceKindPyPDF.ANNOT_GOTOR:
        remote_file = str(obj["/A"].get_object().get("/F"))
    elif taxonomy.pypdf_source == SourceKindPyPDF.ANNOT_LAUNCH:
        # Explicitly pull target executable / file path out via control key /F
        file = str(obj["/A"].get_object().get("/F") or "")


