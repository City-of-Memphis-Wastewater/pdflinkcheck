# src/pdflinkcheck/analysis_pdfium.py
"""
A performant PDF analysis backend, built on pypdfium2, that challenges the PyMuPDF engine, with a bit of parsing.
References:
- https://pypdfium2.readthedocs.io/en/stable/python_api.html
- https://pypdfium2.readthedocs.io/en/stable/python_api/raw.html
- https://pdfium.googlesource.com/pdfium/+/refs/heads/main/public/fpdf_doc.h#1100
- https://pdfium.googlesource.com/pdfium/+/refs/heads/main/public/fpdfview.h#141-147
- https://pdfium.googlesource.com/pdfium/+/refs/heads/main/public/fpdfview.h#119-128
"""
from __future__ import annotations
import ctypes
from enum import IntEnum, Enum
from typing import Optional, Dict, Any, Tuple, List

from pdflinkcheck.helpers import PageRef, LinkType, create_link_dict, create_toc_dict, ItemCategory
from pdflinkcheck.environment import pdfium_is_available

try:
    if pdfium_is_available():
        import pypdfium2 as pdfium
        import pypdfium2.raw as pdfium_c
    else:
        pdfium = None
        pdfium_c = None
except ImportError:
    pdfium = None
    pdfium_c = None

class PdfActionType(IntEnum):
    """
    Standard PDF structural action types mapped to PDFium specifications.
    Reference: fpdf_doc.h action type macros
    """
    UNSUPPORTED = 0
    GOTO = 1         # Internal destination
    GOTOR = 2        # Remote destination (external PDF file reference)
    URI = 3          # External web / application resource locator
    LAUNCH = 4       # Launch external application or open arbitrary files
    NAMED = 5        # Predefined structural names (e.g., NextPage, Print)
    VJS = 6          # Embedded JavaScript execution engine blocks
    SUBMIT = 7       # Form field submission data pipelines
    RESET = 8        # Form tracking component control reset actions
    IMPORTDATA = 9   # Interactive external form initialization values

class SourceKindPdfium(str, Enum):
    """Tracks exactly which internal PDF pipeline or object type exposed the target link."""
    ANNOT_DIRECT_DEST = "pypdfium2_annot_direct_dest"
    ANNOT_GOTO = "pypdfium2_annot_goto"
    ANNOT_URI = "pypdfium2_annot_uri"
    ANNOT_GOTOR = "pypdfium2_annot_gotor"
    ANNOT_LAUNCH = "pypdfium2_annot_launch"
    ANNOT_OTHER = "pypdfium2_annot_other"

def _guard_pdfium_availability() -> None:
    """Ensures pypdfium2 components are properly installed and available."""
    if not pdfium_is_available() or pdfium is None:
        raise ImportError(
            "\n\npypdfium2 is not installed. \n"
            "Install it with: \n\n"
            "\tpip install pdflinkcheck[pdfium] \n"
            "\t\tOR \n"
            "\tuv sync --extra pdfium \n"
        )

def analyze_pdf(pdf_path: str) -> Dict[str, Any]:
    # 1. Guard the entry point
    _guard_pdfium_availability()
    doc = pdfium.PdfDocument(pdf_path)

    total_pages = len(doc) # or doc.page_count

    links = []
    toc_list = []
    file_ov = {}
    seen_toc = set()

    file_ov["total_pages"] = total_pages

    # 1. TOC Extraction (Matches PyMuPDF logic)
    for item in doc.get_toc():
        title = item.get_title() if hasattr(item, "get_title") else ""
        dest = item.get_dest()
        #view = dest.get_view()
        page_index, view_type, params = parse_view(dest)
        #destination_view = pdfium_c.FPDFDest_GetView(dest)
        page_idx = PageRef.from_index(dest.get_index()).machine if dest else 0
        if title or page_idx > 0:
            key = (item.level, title, page_idx)
            if key not in seen_toc:
                toc_item_dict = create_toc_dict(
                    level = item.level + 1, 
                    title = title, 
                    target_page =  page_idx
                    )
                toc_list.append(toc_item_dict)
                seen_toc.add(key)

    # 2. Link Enumeration
    for page_index in range(len(doc)):
        page = doc.get_page(page_index)
        try:
            text_page = page.get_textpage()
            try:
                source_page_ref = PageRef.from_index(page_index)
                # --- LINKS (Standard Annotations) Internal & External ---
                # We iterate through standard link annotations for GoTo actions
                assess_action(doc, page, links, page_index, text_page, source_page_ref)
                
            finally:
                text_page.close()
        finally:
            page.close()
    doc.close()
    return {"links": links, "toc": toc_list, "file_ov": file_ov}

def normalize_rect(fs_rect: pdfium_c.FS_RECTF, precision: int = 2) -> List[float]:
    """
    Normalize FS_RECTF to consistent [x0, y0, x1, y1] order 
    with standardized decimal precision.
    PDF uses bottom-left origin; we keep that but ensure x0 < x1, y0 < y1.
    Returns list of 4 rounded values or [0,0,0,0] if invalid.
    """
    if not fs_rect:
        return [0.0, 0.0, 0.0, 0.0]

    x0 = min(fs_rect.left, fs_rect.right)
    x1 = max(fs_rect.left, fs_rect.right)
    y0 = min(fs_rect.bottom, fs_rect.top)
    y1 = max(fs_rect.bottom, fs_rect.top)

    if x1 <= x0 or y1 <= y0:
        return [0.0, 0.0, 0.0, 0.0]

    # Enforce standard rounding precision here
    return [round(float(x0), precision), round(float(y0), precision), 
            round(float(x1), precision), round(float(y1), precision)]

def extract_destination_view(dest: Any) -> Optional[Dict[str, Any]]:
    """
    Extract view parameters from a destination object.
    Returns dict like {'fit': 'XYZ', 'zoom': 1.5, 'left': 100, 'top': 200, 'bottom': None} or None.
    """
    if not dest:
        return None

    try:
        # FPDFDest_GetView returns a tuple: (page_index, view_mode, params_list)
        # But in pypdfium2 helpers it may vary — fall back to raw if needed
        view = dest.get_view() if hasattr(dest, 'get_view') else pdfium_c.FPDFDest_GetView(dest)

        if not view or len(view) < 2:
            return None

        view_mode = view[1]  # e.g. PDFDEST_VIEW_FIT, PDFDEST_VIEW_XYZ, etc.
        params = view[2] if len(view) > 2 else []

        result = {"fit": str(view_mode)}

        if view_mode in (pdfium_c.PDFDEST_VIEW_XYZ, pdfium_c.PDFDEST_VIEW_FITH,
                         pdfium_c.PDFDEST_VIEW_FITV, pdfium_c.PDFDEST_VIEW_FITR):
            # params usually [zoom, left, top] or similar
            if len(params) >= 3:
                result.update({
                    "zoom": float(params[0]) if params[0] is not None else None,
                    "left": float(params[1]) if params[1] is not None else None,
                    "top": float(params[2]) if params[2] is not None else None,
                })
        return result if len(result) > 1 else None  # don't return empty dict

    except Exception:
        return None

def get_uri_from_action(action: Any, doc_raw: Any) -> Optional[str]:
    """
    Extract URI path from action.
    Your PDFium build returns null-terminated UTF-8, not UTF-16.
    """
    if not action or not doc_raw:
        return None
    uri_bytes = b"" # Initialize to avoid UnboundLocalError
    try:
        # Probe length
        buflen = pdfium_c.FPDFAction_GetURIPath(doc_raw, action, None, 0)
        if buflen <= 1:
            return None

        # Allocate buffer as char* (for UTF-8)
        buffer = ctypes.create_string_buffer(buflen)

        # Fill buffer
        pdfium_c.FPDFAction_GetURIPath(doc_raw, action, buffer, buflen)

        # buffer.value is bytes up to first null; decode as UTF-8
        uri_bytes = buffer.value
        uri = uri_bytes.decode('utf-8', errors='strict').rstrip('\x00').strip()
        #logger.debug(f"Clean repr URI: {repr(uri)}")
        #logger.debug(f"Clean display URI: {uri}")

        return uri if uri else None

    except UnicodeDecodeError as ude:
        print(f"UTF-8 decode error: {ude}")
        # Fallback: replace invalid sequences
        uri = uri_bytes.decode('utf-8', errors='replace').rstrip('\x00').strip()
        #print(f"Fallback repr: {repr(uri)}")
        return uri if uri else None

    except Exception as e:
        #print(f"URI extraction failed: {str(e)}")
        return None

def get_remote_file_from_action(action: Any, doc_raw: Any) -> Optional[str]:
    """
    Extract remote file path from GoToR or Launch action.
    Returns string (file path) or None.
    """
    if not action or not doc_raw:
        return None

    try:
        filespec = pdfium_c.FPDFAction_GetFileSpec(action)
        if not filespec:
            return None
        
        path_len = pdfium_c.FPDFDoc_GetFileSpecFileName(filespec, None, 0)
        if path_len <= 0:
            return None

        path_buf = (pdfium_c.c_ushort * path_len)()
        pdfium_c.FPDFDoc_GetFileSpecFileName(filespec, path_buf, path_len)
        path = ctypes.string_at(path_buf, (path_len - 1) * 2).decode('utf-16le', errors='replace')
        return path.strip()
    except Exception:
        return None

def get_pdfium_text_safe(text_page, fs_rect, tolerance=2.0):
    # Ensure min/max logic so we don't pass an inverted rect to PDFium
    l = min(fs_rect.left, fs_rect.right) - tolerance
    r = max(fs_rect.left, fs_rect.right) + tolerance
    t = max(fs_rect.top, fs_rect.bottom) + tolerance
    b = min(fs_rect.top, fs_rect.bottom) - tolerance
    
    return text_page.get_text_bounded(left=l, top=t, right=r, bottom=b).strip()

    
def get_link_text_precise(text_page: Any, link_handle: Any) -> str:
    """
    Extracts text from a link using its QuadPoints (for multi-line links) 
    or falls back to its standard Annotation Rectangle.
    """
    all_text_segments = []
    quad_count = pdfium_c.FPDFLink_CountQuadPoints(link_handle)
    
    if quad_count > 0:
        for i in range(quad_count):
            quad = pdfium_c.FS_QUADPOINTSF()
            pdfium_c.FPDFLink_GetQuadPoints(link_handle, i, ctypes.byref(quad))
            
            # Extract standard bounding bounds from QuadPoints coordinates
            l = min(quad.x1, quad.x2, quad.x3, quad.x4)
            r = max(quad.x1, quad.x2, quad.x3, quad.x4)
            b = min(quad.y1, quad.y2, quad.y3, quad.y4)
            t = max(quad.y1, quad.y2, quad.y3, quad.y4)
            
            segment = text_page.get_text_bounded(left=l-1, bottom=b-1, right=r+1, top=t+1)
            if segment:
                all_text_segments.append(segment)
        
        return " ".join(all_text_segments).strip()

    # Fallback to the standard bounding box if no quadpoints exist
    r = pdfium_c.FS_RECTF()
    pdfium_c.FPDFLink_GetAnnotRect(link_handle, ctypes.byref(r))
    
    anchor_text = text_page.get_text_bounded(
        left=r.left-1, 
        bottom=r.bottom-1, 
        right=r.right+1, 
        top=r.top+1
    )
    return anchor_text.strip() if anchor_text else ""
    

def get_pdfium_text_smart(page: Any, text_page: Any, fs_rect: pdfium_c.FS_RECTF) -> str:
    """
    Finds characters inside the rect, then expands outwards to grab full 
    words for context without pulling in the entire line.
    """
    char_indices = text_page.get_chars_bounded(
        left=fs_rect.left - 1, 
        top=fs_rect.top + 1, 
        right=fs_rect.right + 1, 
        bottom=fs_rect.bottom - 1
    )
    
    if not char_indices:
        return ""

    start_idx = min(char_indices)
    end_idx = max(char_indices)

    # Expand Left: grab context up to 60 characters back
    lookback = max(0, start_idx - 60)
    prefix_text = text_page.get_text_range(index=lookback, count=start_idx - lookback)
    prefix_words = prefix_text.split()
    refined_prefix = " ".join(prefix_words[-3:]) if prefix_words else ""

    # Expand Right: grab context up to 60 characters ahead
    suffix_text = text_page.get_text_range(index=end_idx + 1, count=60)
    suffix_words = suffix_text.split()
    refined_suffix = " ".join(suffix_words[:3]) if suffix_words else ""

    # Pull the baseline link text and combine
    anchor_text = text_page.get_text_range(index=start_idx, count=(end_idx - start_idx) + 1)
    full_context = f"{refined_prefix} {anchor_text} {refined_suffix}"
    
    return " ".join(full_context.split()).strip()

def parse_view(dest):
    view = dest.get_view()

    if len(view) == 3:
        page_index, view_type, params = view
    elif len(view) == 2:
        page_index, params = view
        view_type = None
    else:
        raise RuntimeError(f"Unexpected view tuple: {view}")

    return page_index, view_type, params

def assess_action(doc, page, links, page_index, text_page, source_page_ref):
    pos = 0
    while True:
        annot_raw = pdfium_c.FPDFPage_GetAnnot(page.raw, pos)
        if not annot_raw:
            break
        try:
            subtype = pdfium_c.FPDFAnnot_GetSubtype(annot_raw)
            if subtype == pdfium_c.FPDF_ANNOT_LINK:
                _process_link_annotation(doc, page, annot_raw, text_page, source_page_ref, links)
        finally:
            if annot_raw:
                pdfium_c.FPDFPage_CloseAnnot(annot_raw)
        
        pos += 1

def _process_link_annotation(
    doc: Any,
    page: Any,
    annot_raw: Any,
    text_page: Any,
    source_page_ref: PageRef,
    links: List[Dict[str, Any]]
) -> None:
    """Extracts bounding box, anchor text, and targets for a single link annotation."""
    link_handle = pdfium_c.FPDFAnnot_GetLink(annot_raw)
    if not link_handle:
        return

    anchor_text = get_link_text_precise(text_page, link_handle)
    
    fs_rect = pdfium_c.FS_RECTF()
    pdfium_c.FPDFAnnot_GetRect(annot_raw, fs_rect)
    rect_norm = normalize_rect(fs_rect)

    action = pdfium_c.FPDFLink_GetAction(link_handle)
    dest = pdfium_c.FPDFLink_GetDest(doc.raw, link_handle)

    if action:
        # --- CASE 1: ACTION EXISTS ---
        _dispatch_action(doc, action, dest, source_page_ref, rect_norm, anchor_text, links)
    elif dest:
        # --- CASE 2: NO ACTION, BUT DIRECT DESTINATION ---
        _dispatch_direct_dest(doc, dest, source_page_ref, rect_norm, anchor_text, links)
    else:
        # Fail-safe catch for unhandled, blank, or broken structural link markers
        link_dict = create_link_dict(
            source_page_ref=source_page_ref, 
            rect_norm=rect_norm, 
            anchor_text=anchor_text,
            link_type=LinkType.OTHER.value,
            item_category=ItemCategory.OTHER.value,
            source_kind=SourceKindPdfium.ANNOT_OTHER.value
        )
        links.append(link_dict)

def _dispatch_action(
    doc: Any,
    action: Any,
    dest: Any,
    source_page_ref: PageRef,
    rect_norm: List[float],
    anchor_text: str,
    links: List[Dict[str, Any]]
) -> None:
    """Routes an action object to its specific LinkType classification."""
    action_type = pdfium_c.FPDFAction_GetType(action)

    destination_page = None
    destination_view = None
    file = None
    url = None
    action_kind = None

    if action_type == PdfActionType.GOTO:
        # Reuse existing dest if present, or try to get from action
        target_dest = dest or pdfium_c.FPDFAction_GetDest(doc.raw, action)
        if target_dest:
            dest_idx = pdfium_c.FPDFDest_GetDestPageIndex(doc.raw, target_dest)
            link_type=LinkType.INTERNAL_GOTO.value,
            item_category=ItemCategory.INTERNAL.value,
            source_kind=SourceKindPdfium.ANNOT_GOTO.value,
            destination_page = PageRef.from_index(dest_idx).machine,
            destination_view = extract_destination_view(target_dest)        
    
    elif action_type == PdfActionType.URI:
        uri = get_uri_from_action(action, doc.raw)
        if uri:
            link_type=LinkType.EXTERNAL.value
            item_category=ItemCategory.EXTERNAL.value
            url=uri
            source_kind=SourceKindPdfium.ANNOT_URI.value
            
        else:
            link_type=LinkType.OTHER.value, 
            # item_category=ItemCategory.EXTERNAL.value # tempting, but we should remain consistent with the assertion in PyMuPDF that 
            item_category=ItemCategory.OTHER.value
            source_kind=SourceKindPdfium.ANNOT_URI.value
            
    elif action_type == PdfActionType.GOTOR:
        remote_file = get_remote_file_from_action(action, doc.raw)
        r_dest = pdfium_c.FPDFAction_GetDest(doc.raw, action)
        
        link_type=LinkType.REMOTE_GOTOR.value, 
        item_category=ItemCategory.INTERNAL.value,
        remote_file=remote_file,
        source_kind=SourceKindPdfium.ANNOT_GOTOR.value,
        destination_page=pdfium_c.FPDFDest_GetDestPageIndex(doc.raw, r_dest) if r_dest else None
        

    elif action_type == PdfActionType.LAUNCH:
        # Extract underlying target path string from the Launch action spec
        launch_file = get_remote_file_from_action(action, doc.raw) or ""
        link_type=LinkType.LAUNCH.value
        item_category=ItemCategory.EXTERNAL.value
        file=launch_file
        source_kind=SourceKindPdfium.ANNOT_LAUNCH.value
        
    else:
        # Captures exotic macros (VJS, SUBMIT, NAMED) cleanly into the unknown dictionary structure
        link_type=LinkType.OTHER.value
        item_category=ItemCategory.OTHER.value
        action_kind=int(action_type)
        source_kind=SourceKindPdfium.ANNOT_OTHER.value
        
    link_dict = create_link_dict(
        source_page_ref=source_page_ref, 
        rect_norm=rect_norm, 
        anchor_text=anchor_text,
        link_type=link_type, 
        item_category=item_category,
        url=url,
        file=file,
        source_kind=source_kind,
        destination_page = destination_page,
        destination_view = destination_view,
        action_kind=action_kind,
    )
    links.append(link_dict)

def _dispatch_direct_dest(
    doc: Any,
    dest: Any,
    source_page_ref: PageRef,
    rect_norm: List[float],
    anchor_text: str,
    links: List[Dict[str, Any]]
) -> None:
    """Handles direct layout map links that lack an explicit action wrapper."""
    dest_idx = pdfium_c.FPDFDest_GetDestPageIndex(doc.raw, dest)
    link_dict = create_link_dict(
        source_page_ref=source_page_ref, 
        rect_norm=rect_norm, 
        anchor_text=anchor_text,
        link_type=LinkType.INTERNAL_RESOLVED.value,
        item_category=ItemCategory.INTERNAL.value,
        source_kind=SourceKindPdfium.ANNOT_DIRECT_DEST.value,
        destination_page = PageRef.from_index(dest_idx).machine,
        destination_view = extract_destination_view(dest)
    )
    links.append(link_dict)

def demo():
    """
    Demostrate the pypdfium2-informed analyze_pdf().
    """
    from pdflinkcheck.io import get_first_pdf_in_cwd

    pdf_path = get_first_pdf_in_cwd()
    if not pdf_path:
        print(" [!] No PDF found in the current working directory to run testing.")
        print("     Drop a dummy PDF into ~/dev/pdflinkcheck or pass an explicit path to test.")
        return
    
    data = analyze_pdf(pdf_path = pdf_path)
    print(f"list(data) = {list(data)}")
    print("pypdfium2-based analysis complete.")
    print("Use the pdflinkcheck CLI, GUI, or web server to generate export files.")

if __name__ == "__main__":
    demo()