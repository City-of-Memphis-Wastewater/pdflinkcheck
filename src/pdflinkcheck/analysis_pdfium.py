# src/pdflinkcheck/analysis_pdfium.py

"""
A performant PDF analysis backend, built on pypdfium2, that challenges the PyMuPDF engine, with a bit of parsing.
References:
- https://pypdfium2.readthedocs.io/en/stable/python_api.html
- https://pypdfium2.readthedocs.io/en/stable/python_api/raw.html
- https://pdfium.googlesource.com/pdfium/+/refs/heads/main/public/fpdf_doc.h
"""

from __future__ import annotations
import ctypes
from enum import Enum, IntEnum
from typing import Optional, Dict, Any, List

from pdflinkcheck.environment import pdfium_is_available
from pdflinkcheck.helpers import PageRef

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


class LinkType(str, Enum):
    """Normalized categories of extracted document elements for reporting/filtering."""
    INTERNAL = "Internal (GoTo/Dest)"
    EXTERNAL = "External (URI)"
    REMOTE = "Remote (GoToR)"
    LAUNCH = "Launch"
    OTHER = "Other Action"


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
    """Coordinates the high-level workflow for document link and TOC analysis."""
    _guard_pdfium_availability()
    
    doc = pdfium.PdfDocument(pdf_path)
    try:
        total_pages = len(doc)
        toc_list = extract_toc(doc)
        links = extract_all_links(doc)
        
        file_ov = {"total_pages": total_pages}
        return {"links": links, "toc": toc_list, "file_ov": file_ov}
    finally:
        doc.close()


def extract_toc(doc: pdfium.PdfDocument) -> List[Dict[str, Any]]:
    """Extracts the Table of Contents (TOC) structure from the document."""
    toc_list = []
    seen_toc = set()

    for item in doc.get_toc():
        title = item.get_title() if hasattr(item, "get_title") else ""
        dest = item.get_dest()
        page_idx = PageRef.from_index(dest.get_index()).machine if dest else 0
        
        if title or page_idx > 0:
            key = (item.level, title, page_idx)
            if key not in seen_toc:
                toc_list.append({
                    "level": item.level + 1, 
                    "title": title, 
                    "target_page": page_idx
                })
                seen_toc.add(key)
    return toc_list


def extract_all_links(doc: pdfium.PdfDocument) -> List[Dict[str, Any]]:
    """Iterates through all pages in the document to look for link entries."""
    links = []
    for page_index in range(len(doc)):
        page = doc.get_page(page_index)
        try:
            text_page = page.get_textpage()
            try:
                source_ref = PageRef.from_index(page_index)
                page_links = extract_page_links(doc, page, text_page, source_ref)
                links.extend(page_links)
            finally:
                text_page.close()
        finally:
            page.close()
    return links

def extract_page_links(
    doc: pdfium.PdfDocument, 
    page: Any, 
    text_page: Any, 
    source_ref: PageRef
) -> List[Dict[str, Any]]:
    """
    Scans links directly from the page using pypdfium2's built-in link 
    enumeration wrapper instead of raw annotation pointer queries.
    """
    page_links = []
    
    # The original working version iterates over links directly via the page object
    for link in page.get_links():
        # Extracted geometry and page targets directly through the high-level API
        rect_norm = [round(float(coord), 2) for coord in link.rect]
        dest_idx = link.page_index
        
        # Pull exact text bounds matching the link coordinates
        anchor_text = text_page.get_text_bounded(
            left=link.rect[0]-1, 
            bottom=link.rect[1]-1, 
            right=link.rect[2]+1, 
            top=link.rect[3]+1
        )
        
        context = {
            "source_ref": source_ref,
            "rect_norm": rect_norm,
            "anchor_text": anchor_text.strip() if anchor_text else "",
        }
        
        # Route to appropriate LinkType categories
        if link.uri:
            link_dict = create_link_dict(
                link_type=LinkType.EXTERNAL,
                url=link.uri,
                source_kind=SourceKindPdfium.ANNOT_URI,
                **context
            )
        elif dest_idx is not None and dest_idx >= 0:
            link_dict = create_link_dict(
                link_type=LinkType.INTERNAL,
                destination_page=PageRef.from_index(dest_idx).machine,
                source_kind=SourceKindPdfium.ANNOT_DIRECT_DEST,
                **context
            )
        else:
            continue
            
        page_links.append(link_dict)
        
    return page_links

def extract_page_links_defunct(
    doc: pdfium.PdfDocument, 
    page: Any, 
    text_page: Any, 
    source_ref: PageRef
) -> List[Dict[str, Any]]:
    """Scans structural page annotations using deterministic length bounds."""
    page_links = []
    annot_count = pdfium_c.FPDFPage_CountAnnots(page.raw)
    
    for pos in range(annot_count):
        annot_raw = pdfium_c.FPDFPage_GetAnnot(page.raw, pos)
        if not annot_raw:
            continue

        try:
            subtype = pdfium_c.FPDFAnnot_GetSubtype(annot_raw)
            if subtype == pdfium_c.FPDF_ANNOT_LINK:
                link_dict = extract_link_annotation(doc, annot_raw, text_page, source_ref)
                if link_dict:
                    page_links.append(link_dict)
        finally:
            pdfium_c.FPDFPage_CloseAnnot(annot_raw)
        
    return page_links


def extract_link_annotation(
    doc: pdfium.PdfDocument, 
    annot_raw: Any, 
    text_page: Any, 
    source_ref: PageRef
) -> Optional[Dict[str, Any]]:
    """Inspects a single link annotation object to build its metadata payload."""
    link_handle = pdfium_c.FPDFAnnot_GetLink(annot_raw)
    if not link_handle:
        return None

    anchor_text = get_link_text_precise(text_page, link_handle)
    
    fs_rect = pdfium_c.FS_RECTF()
    pdfium_c.FPDFAnnot_GetRect(annot_raw, fs_rect)
    rect_norm = normalize_rect(fs_rect)

    action = pdfium_c.FPDFLink_GetAction(link_handle)
    dest = pdfium_c.FPDFLink_GetDest(doc.raw, link_handle)

    context = {
        "source_ref": source_ref,
        "rect_norm": rect_norm,
        "anchor_text": anchor_text,
    }

    if action:
        raw_type = pdfium_c.FPDFAction_GetType(action)
        try:
            action_type = PdfActionType(raw_type)
        except ValueError:
            action_type = PdfActionType.UNSUPPORTED

        return parse_action_by_type(doc, action, action_type, dest, context)
        
    elif dest:
        dest_idx = pdfium_c.FPDFDest_GetDestPageIndex(doc.raw, dest)
        return create_link_dict(
            link_type=LinkType.INTERNAL,
            destination_page=PageRef.from_index(dest_idx).machine,
            destination_view=extract_destination_view(dest),
            source_kind=SourceKindPdfium.ANNOT_DIRECT_DEST,
            **context
        )
    return None


def parse_action_by_type(
    doc: pdfium.PdfDocument, 
    action: Any, 
    action_type: PdfActionType, 
    fallback_dest: Any, 
    ctx: dict
) -> Optional[Dict[str, Any]]:
    """Routes specific actionable behaviors to normalized link configurations based on the enum definition."""
    
    if action_type == PdfActionType.GOTO:
        # REPAIR: FPDFAction_GetDest only accepts the action handle, not doc.raw
        target_dest = fallback_dest or pdfium_c.FPDFAction_GetDest(action)
        if target_dest:
            dest_idx = pdfium_c.FPDFDest_GetDestPageIndex(doc.raw, target_dest)
            return create_link_dict(
                link_type=LinkType.INTERNAL,
                destination_page=PageRef.from_index(dest_idx).machine,
                destination_view=extract_destination_view(target_dest),
                source_kind=SourceKindPdfium.ANNOT_GOTO,
                **ctx
            )
            
    elif action_type == PdfActionType.URI:
        uri = get_uri_from_action(action, doc.raw)
        if uri:
            return create_link_dict(
                link_type=LinkType.EXTERNAL, 
                url=uri, 
                source_kind=SourceKindPdfium.ANNOT_URI,
                **ctx
            )
            
    elif action_type == PdfActionType.GOTOR:
        remote_file = get_remote_file_from_action(action, doc.raw)
        # REPAIR: FPDFAction_GetDest only accepts the action handle, not doc.raw
        r_dest = pdfium_c.FPDFAction_GetDest(action)
        dest_page = pdfium_c.FPDFDest_GetDestPageIndex(doc.raw, r_dest) if r_dest else None
        return create_link_dict(
            link_type=LinkType.REMOTE, 
            remote_file=remote_file,
            destination_page=dest_page,
            source_kind=SourceKindPdfium.ANNOT_GOTOR,
            **ctx
        )
        
    elif action_type == PdfActionType.LAUNCH:
        remote_file = get_remote_file_from_action(action, doc.raw)
        return create_link_dict(
            link_type=LinkType.LAUNCH,
            remote_file=remote_file,
            source_kind=SourceKindPdfium.ANNOT_LAUNCH,
            **ctx
        )

    if fallback_dest:
        dest_idx = pdfium_c.FPDFDest_GetDestPageIndex(doc.raw, fallback_dest)
        return create_link_dict(
            link_type=LinkType.INTERNAL,
            destination_page=PageRef.from_index(dest_idx).machine,
            destination_view=extract_destination_view(fallback_dest),
            source_kind=SourceKindPdfium.ANNOT_DIRECT_DEST,
            **ctx
        )
        
    return create_link_dict(
        link_type=LinkType.OTHER,
        action_kind=int(action_type),
        source_kind=SourceKindPdfium.ANNOT_OTHER,
        **ctx
    )


def normalize_rect(fs_rect: pdfium_c.FS_RECTF, precision: int = 2) -> List[float]:
    """Normalize FS_RECTF to consistent [x0, y0, x1, y1] order with standardized decimal precision."""
    if not fs_rect:
        return [0.0, 0.0, 0.0, 0.0]

    x0 = min(fs_rect.left, fs_rect.right)
    x1 = max(fs_rect.left, fs_rect.right)
    y0 = min(fs_rect.bottom, fs_rect.top)
    y1 = max(fs_rect.bottom, fs_rect.top)

    if x1 <= x0 or y1 <= y0:
        return [0.0, 0.0, 0.0, 0.0]

    return [
        round(float(x0), precision), round(float(y0), precision), 
        round(float(x1), precision), round(float(y1), precision)
    ]


def extract_destination_view(dest: Any) -> Optional[Dict[str, Any]]:
    """Extract view parameters from a destination object."""
    if not dest:
        return None

    try:
        view = dest.get_view() if hasattr(dest, 'get_view') else pdfium_c.FPDFDest_GetView(dest)
        if not view or len(view) < 2:
            return None

        view_mode = view[1]
        params = view[2] if len(view) > 2 else []
        result = {"fit": str(view_mode)}

        if view_mode in (pdfium_c.PDFDEST_VIEW_XYZ, pdfium_c.PDFDEST_VIEW_FITH,
                         pdfium_c.PDFDEST_VIEW_FITV, pdfium_c.PDFDEST_VIEW_FITR):
            if len(params) >= 3:
                result.update({
                    "zoom": float(params[0]) if params[0] is not None else None,
                    "left": float(params[1]) if params[1] is not None else None,
                    "top": float(params[2]) if params[2] is not None else None,
                })
        return result if len(result) > 1 else None
    except Exception:
        return None


def get_uri_from_action(action: Any, doc_raw: Any) -> Optional[str]:
    """Extract URI path string safely out of low-level string buffer fragments."""
    if not action or not doc_raw:
        return None
    try:
        buflen = pdfium_c.FPDFAction_GetURIPath(doc_raw, action, None, 0)
        if buflen <= 1:
            return None

        buffer = ctypes.create_string_buffer(buflen)
        pdfium_c.FPDFAction_GetURIPath(doc_raw, action, buffer, buflen)

        uri_bytes = buffer.value
        try:
            return uri_bytes.decode('utf-8', errors='strict').rstrip('\x00').strip()
        except UnicodeDecodeError:
            return uri_bytes.decode('utf-8', errors='replace').rstrip('\x00').strip()
    except Exception:
        return None


def get_remote_file_from_action(action: Any, doc_raw: Any) -> Optional[str]:
    """Extract remote file path from GoToR or Launch action."""
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


def create_link_dict(
    source_ref: PageRef,
    rect_norm: List[float],
    anchor_text: str,
    link_type: LinkType,
    source_kind: SourceKindPdfium,
    **kwargs
) -> Dict[str, Any]:
    """Factory for consistent link dictionary structure."""
    base = {
        'page': source_ref.machine,
        'rect': rect_norm,
        'link_text': anchor_text.strip() or "Link (No Text)",
        'type': link_type.value,
        'source_kind': source_kind.value,
    }
    base.update(kwargs)
    return base


def get_link_text_precise(text_page: Any, link_handle: Any) -> str:
    """Extracts text from a link using its QuadPoints or Annotation Rect fallback."""
    quad_count = pdfium_c.FPDFLink_CountQuadPoints(link_handle)
    
    if quad_count > 0:
        all_text_segments = []
        for i in range(quad_count):
            quad = pdfium_c.FS_QUADPOINTSF()
            pdfium_c.FPDFLink_GetQuadPoints(link_handle, i, ctypes.byref(quad))
            
            l = min(quad.x1, quad.x2, quad.x3, quad.x4)
            r = max(quad.x1, quad.x2, quad.x3, quad.x4)
            b = min(quad.y1, quad.y2, quad.y3, quad.y4)
            t = max(quad.y1, quad.y2, quad.y3, quad.y4)
            
            segment = text_page.get_text_bounded(left=l-1, bottom=b-1, right=r+1, top=t+1)
            if segment:
                cleaned = " ".join(segment.split())
                # REPAIR: Deduplicate overlapping bounding boxes across lines
                if cleaned and cleaned not in all_text_segments:
                    all_text_segments.append(cleaned)
        return " ".join(all_text_segments).strip()
    else:
        r = pdfium_c.FS_RECTF()
        pdfium_c.FPDFLink_GetAnnotRect(link_handle, ctypes.byref(r))
        anchor_text = text_page.get_text_bounded(
            left=r.left-1, bottom=r.bottom-1, right=r.right+1, top=r.top+1
        )
        return anchor_text.strip() if anchor_text else ""


def demo():
    """Runs a quick local integration check on the first PDF discovered in the working directory."""
    from pdflinkcheck.io import get_first_pdf_in_cwd
    pdf = get_first_pdf_in_cwd()
    if pdf:
        data = analyze_pdf(pdf_path=pdf)
        print(f"Analysis complete. Extracted {len(data.get('links', []))} links.")


if __name__ == "__main__":
    demo()