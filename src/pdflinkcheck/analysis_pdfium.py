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
from typing import Optional, Dict, Any, Tuple, List

from pdflinkcheck.helpers import PageRef
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

def analyze_pdf(pdf_path: str) -> Dict[str, Any]:
    # 1. Guard the entry point
    if not pdfium_is_available() or pdfium is None:
        print(f"pdfium_is_available() = {pdfium_is_available()}")
        print(f"pdfium = {pdfium}")
        
        raise ImportError(
            "\n\npypdfium2 is not installed. \nInstall it with: \n\n\tpip install pdflinkcheck[pdfium] \n\t\tOR \n\tuv sync --extra pdfium \n"
        )
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
        #logger.debug(f"page_index = {page_index}")
        #logger.debug(f"params = {params}")
        #logger.debug(help(pdfium_c.FPDFDest_GetView))
        #destination_view = pdfium_c.FPDFDest_GetView(dest)
        page_idx = PageRef.from_index(dest.get_index()).machine if dest else 0
        if title or page_idx > 0:
            key = (item.level, title, page_idx)
            if key not in seen_toc:
                toc_list.append({"level": item.level + 1, "title": title, "target_page": page_idx})
                seen_toc.add(key)

    # 2. Link Enumeration
    for page_index in range(len(doc)):
        
        page = doc.get_page(page_index)

        try:
            text_page = page.get_textpage()
            try:
            source_ref = PageRef.from_index(page_index)
            # --- LINKS (Standard Annotations) Internal & External ---
            # We iterate through standard link annotations for GoTo actions
            assess_action(doc,page,links, page_index, text_page, source_ref)
            finally:
                text_page.close()
        finally:
            page.close()
        
    doc.close()
    return {"links": links, "toc": toc_list, "file_ov": file_ov}


def normalize_rect_floats_defunct(fs_rect: pdfium_c.FS_RECTF) -> List[float]:
    """
    Normalize FS_RECTF to consistent [x0, y0, x1, y1] order.
    PDF uses bottom-left origin; we keep that but ensure x0 < x1, y0 < y1.
    Returns list of 4 floats or [0,0,0,0] if invalid.
    """
    if not fs_rect:
        return [0.0, 0.0, 0.0, 0.0]

    x0 = min(fs_rect.left, fs_rect.right)
    x1 = max(fs_rect.left, fs_rect.right)
    y0 = min(fs_rect.bottom, fs_rect.top)
    y1 = max(fs_rect.bottom, fs_rect.top)

    # Protect against degenerate/empty rects
    if x1 <= x0 or y1 <= y0:
        return [0.0, 0.0, 0.0, 0.0]

    return [float(x0), float(y0), float(x1), float(y1)]

def normalize_rect(fs_rect: pdfium_c.FS_RECTF, precision: int = 2) -> List[float]:
    """
    Normalize FS_RECTF to consistent [x0, y0, x1, y1] order with standardized decimal precision.
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

        # Optional debug (comment out later)
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


def create_link_dict(
    source_ref: PageRef,
    rect_norm: List[float],
    anchor_text: str,
    link_type: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Factory for consistent link dictionary structure.
    Matches PyMuPDF style as closely as possible.
    """
    base = {
        'page': source_ref.machine,
        'rect': rect_norm,
        'link_text': anchor_text.strip() or "Link (No Text)",
        'type': link_type,
    }
    base.update(kwargs)
    return base

def get_pdfium_text_safe(text_page, fs_rect, tolerance=2.0):
    # Ensure min/max logic so we don't pass an inverted rect to PDFium
    l = min(fs_rect.left, fs_rect.right) - tolerance
    r = max(fs_rect.left, fs_rect.right) + tolerance
    t = max(fs_rect.top, fs_rect.bottom) + tolerance
    b = min(fs_rect.top, fs_rect.bottom) - tolerance
    
    return text_page.get_text_bounded(left=l, top=t, right=r, bottom=b).strip()


def get_link_text_precise(text_page, link_handle):
    """
    Extracts text from a link using its QuadPoints (for multi-line links) 
    or its Annotation Rect.
    """
    all_text_segments = []
    quad_count = pdfium_c.FPDFLink_CountQuadPoints(link_handle)
    
    if quad_count > 0:
        # Handle multi-line links by checking each quad (box) individually
        for i in range(quad_count):
            quad = pdfium_c.FS_QUADPOINTSF()
            pdfium_c.FPDFLink_GetQuadPoints(link_handle, i, ctypes.byref(quad))
            
            # PDF coordinates: x1,y1 is bottom-left; x3,y3 is top-right
            l = min(quad.x1, quad.x2, quad.x3, quad.x4)
            r = max(quad.x1, quad.x2, quad.x3, quad.x4)
            b = min(quad.y1, quad.y2, quad.y3, quad.y4)
            t = max(quad.y1, quad.y2, quad.y3, quad.y4)
            
            segment = text_page.get_text_bounded(left=l-1, bottom=b-1, right=r+1, top=t+1)
            if segment:
                all_text_segments.append(segment)
        
        return " ".join(all_text_segments).strip()

    else:
        # Fallback to the standard bounding box
        r = pdfium_c.FS_RECTF()
        pdfium_c.FPDFLink_GetAnnotRect(link_handle, ctypes.byref(r))
        
        anchor_text = text_page.get_text_bounded(
            left=r.left-1, 
            bottom=r.bottom-1, 
            right=r.right+1, 
            top=r.top+1
        )
        return anchor_text.strip() if anchor_text else ""
    

def get_pdfium_text_smart(page, text_page, fs_rect):
    """
    Finds characters inside the rect, then expands to grab full words 
    without necessarily grabbing the entire line.
    """
    # 1. Get all character indices within the link rectangle
    # count_rects and get_rects identify which characters are physically 'hit'
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

    # 2. Expand Left: look back for a 'boundary'
    # We look back up to 60 chars (roughly a few words)
    lookback = max(0, start_idx - 60)
    prefix_text = text_page.get_text_range(index=lookback, count=start_idx - lookback)
    
    # Simple heuristic: Split by spaces and take the last 3 'words'
    # This prevents grabbing the whole line if the line is long.
    prefix_words = prefix_text.split()
    refined_prefix = " ".join(prefix_words[-3:]) if prefix_words else ""

    # 3. Expand Right: look ahead
    lookahead_limit = 60
    suffix_text = text_page.get_text_range(index=end_idx + 1, count=lookahead_limit)
    
    suffix_words = suffix_text.split()
    refined_suffix = " ".join(suffix_words[:3]) if suffix_words else ""

    # 4. Get the actual link text
    link_text = text_page.get_text_range(index=start_idx, count=(end_idx - start_idx) + 1)

    # Combine: [3 words before] + [Link Text] + [3 words after]
    full_context = f"{refined_prefix} {link_text} {refined_suffix}"
    
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

def assess_action(doc, page, links, page_index, text_page, source_ref):
    pos = 0
    while True:
        annot_raw = pdfium_c.FPDFPage_GetAnnot(page.raw, pos)
        if not annot_raw:
            break

        try:
            subtype = pdfium_c.FPDFAnnot_GetSubtype(annot_raw)
            if subtype != pdfium_c.FPDF_ANNOT_LINK:
                pos += 1
                continue
            
            link_handle = pdfium_c.FPDFAnnot_GetLink(annot_raw)
            anchor_text = get_link_text_precise(text_page, link_handle)
            
            fs_rect = pdfium_c.FS_RECTF()
            pdfium_c.FPDFAnnot_GetRect(annot_raw, fs_rect)
            rect_norm = normalize_rect(fs_rect)

            action = pdfium_c.FPDFLink_GetAction(link_handle)
            dest = pdfium_c.FPDFLink_GetDest(doc.raw, link_handle)

            # --- CASE 1: ACTION EXISTS ---
            if action:
                action_type = pdfium_c.FPDFAction_GetType(action)

                if action_type == 1:  # GOTO
                    # Reuse existing dest if present, or try to get from action
                    target_dest = dest or pdfium_c.FPDFAction_GetDest(doc.raw, action)
                    if target_dest:
                        dest_idx = pdfium_c.FPDFDest_GetDestPageIndex(doc.raw, target_dest)
                        links.append(create_link_dict(
                            source_ref=source_ref, rect_norm=rect_norm, anchor_text=anchor_text,
                            link_type='Internal (GoTo/Dest)',
                            destination_page=PageRef.from_index(dest_idx).machine,
                            destination_view=extract_destination_view(target_dest),
                            source_kind='pypdfium2_annot_goto'
                        ))
                
                elif action_type == 3:  # URI
                    uri = get_uri_from_action(action, doc.raw)
                    if uri:
                        links.append(create_link_dict(
                            source_ref=source_ref, rect_norm=rect_norm, anchor_text=anchor_text,
                            link_type='External (URI)', url=uri, source_kind='pypdfium2_annot_uri'
                        ))

                elif action_type == 2:  # GOTOR (Remote)
                    remote_file = get_remote_file_from_action(action, doc.raw)
                    r_dest = pdfium_c.FPDFAction_GetDest(doc.raw, action)
                    links.append(create_link_dict(
                        source_ref=source_ref, rect_norm=rect_norm, anchor_text=anchor_text,
                        link_type='Remote (GoToR)', remote_file=remote_file,
                        destination_page=pdfium_c.FPDFDest_GetDestPageIndex(doc.raw, r_dest) if r_dest else None,
                        source_kind='pypdfium2_annot_gotor'
                    ))
                # ... handle other types (4, etc) as you had them ...

            # --- CASE 2: NO ACTION, BUT DIRECT DESTINATION ---
            elif dest:
                dest_idx = pdfium_c.FPDFDest_GetDestPageIndex(doc.raw, dest)
                links.append(create_link_dict(
                    source_ref=source_ref, rect_norm=rect_norm, anchor_text=anchor_text,
                    link_type='Internal (GoTo/Dest)',
                    destination_page=PageRef.from_index(dest_idx).machine,
                    destination_view=extract_destination_view(dest),
                    source_kind='pypdfium2_annot_direct_dest'
                ))

        finally:
            if annot_raw:
                pdfium_c.FPDFPage_CloseAnnot(annot_raw)
        pos += 1

def assess_action_(doc,page,links, page_index, text_page, source_ref):
    """
    # Standard annotation action types will help to  include external files
    #- **1** = `FPDFACTION_GOTO` → Internal GoTo
    #- **3** = `FPDFACTION_URI` → URI action (http, https, mailto, file:, tel:, etc.).  
    #- **2** = `FPDFACTION_GOTOR` → GoTo Remote (external file/PDF reference — this is your main missing GoToR case)
    #- **4** = `FPDFACTION_LAUNCH` → Launch action (open external file/application)
    #- **5** = `FPDFACTION_NAMED` → Named action (e.g., predefined like "NextPage", "Print")
    #- **6** = `FPDFACTION_JAVASCRIPT` → Execute JavaScript
    #- **7** = `FPDFACTION_SUBMIT` → Form submit
    #- **8** = `FPDFACTION_RESET` → Form reset
    #- **9** = `FPDFACTION_IMPORTDATA` → Import form data
    
    """
    pos = 0
        
    while True:
        annot_raw = pdfium_c.FPDFPage_GetAnnot(page.raw, pos)
        if not annot_raw:
            break

        try:
            subtype = pdfium_c.FPDFAnnot_GetSubtype(annot_raw)
            if subtype != pdfium_c.FPDF_ANNOT_LINK:
                pos += 1
                continue
            link_handle = pdfium_c.FPDFAnnot_GetLink(annot_raw)
        
            # 2. Extract precise text (Pass the HANDLE, not the rect)
            anchor_text = get_link_text_precise(text_page, link_handle)

            # 3. Keep your rect logic exactly as is for the dictionary
            fs_rect = pdfium_c.FS_RECTF()
            pdfium_c.FPDFAnnot_GetRect(annot_raw, fs_rect)
            rect_norm = normalize_rect(fs_rect)

            # 4. Use the handle for the action (instead of the rect)
            action = pdfium_c.FPDFLink_GetAction(link_handle)

           
            #anchor_text = get_pdfium_text_safe(text_page, fs_rect)


            if action:
                action_type = pdfium_c.FPDFAction_GetType(action)

                if action_type == 1:  # GOTO
                    dest = pdfium_c.FPDFLink_GetDest(doc.raw, link_handle)
                    if dest:
                        dest_idx = pdfium_c.FPDFDest_GetDestPageIndex(doc.raw, dest)
                        dest_ref = PageRef.from_index(dest_idx)
                        view_dict = extract_destination_view(dest)

                        links.append(create_link_dict(
                            source_ref=source_ref,
                            rect_norm=rect_norm,
                            anchor_text=anchor_text,
                            link_type='Internal (GoTo/Dest)',
                            destination_page=dest_ref.machine,
                            destination_view=view_dict,
                            source_kind='pypdfium2_annot_goto'
                        ))
                elif action_type == 3:  # URI
                    uri = get_uri_from_action(action, doc.raw)  # ← pass doc.raw here!
                    #print(f"Type 3 URI attempt at pos {pos}: {uri}")

                    if uri:
                        links.append(create_link_dict(
                            source_ref=source_ref,
                            rect_norm=rect_norm,
                            anchor_text=anchor_text,
                            link_type='External (URI)',
                            url=uri,
                            source_kind='pypdfium2_annot_uri'
                        ))
                    else:
                        print(f"Type 3 at pos {pos} — no URI found")
                        
                    """
                    # --- A. EXTERNAL WEB LINKS --- (a known duplicate approach)
                    pagelink_raw = pdfium_c.FPDFLink_LoadWebLinks(text_page.raw)
                    if pagelink_raw:
                        # This is buiilt for only web links - we entirely miss file links
                        count = pdfium_c.FPDFLink_CountWebLinks(pagelink_raw)
                        for i in range(count):
                            buflen = pdfium_c.FPDFLink_GetURL(pagelink_raw, i, None, 0)
                            url = ""
                            if buflen > 0:
                                buffer = (pdfium_c.c_uint16 * buflen)() 
                                pdfium_c.FPDFLink_GetURL(pagelink_raw, i, buffer, buflen)
                                url = ctypes.string_at(buffer, (buflen-1)*2).decode('utf-16le')

                            l, t, r, b = (ctypes.c_double() for _ in range(4))
                            pdfium_c.FPDFLink_GetRect(pagelink_raw, i, 0, ctypes.byref(l), ctypes.byref(t), ctypes.byref(r), ctypes.byref(b))
                            
                            rect = [l.value, b.value, r.value, t.value]
                            links.append({
                                'page': source_ref.machine,
                                'rect': rect,
                                'link_text': text_page.get_text_bounded(left=l.value, top=t.value, right=r.value, bottom=b.value).strip() or url,
                                'type': 'External (URI)',
                                'url': url,
                                'source_kind': 'pypdfium2_weblink'
                            })
                        pdfium_c.FPDFLink_CloseWebLinks(pagelink_raw)
                    """

                elif action_type == 2:  # GOTOR
                    remote_file = get_remote_file_from_action(action, doc.raw)
                    dest = pdfium_c.FPDFAction_GetDest(action)
                    dest_page = None
                    view_dict = None
                    if dest:
                        dest_page = pdfium_c.FPDFDest_GetDestPageIndex(doc.raw, dest)
                        view_dict = extract_destination_view(dest)

                    links.append(create_link_dict(
                        source_ref=source_ref,
                        rect_norm=rect_norm,
                        anchor_text=anchor_text,
                        link_type='Remote (GoToR)',
                        remote_file=remote_file,
                        destination_page=dest_page,
                        destination_view=view_dict,
                        source_kind='pypdfium2_annot_gotor'
                    ))

                elif action_type == 4:  # LAUNCH
                    remote_file = get_remote_file_from_action(action, doc.raw)
                    links.append(create_link_dict(
                        source_ref=source_ref,
                        rect_norm=rect_norm,
                        anchor_text=anchor_text,
                        link_type='Launch',
                        remote_file=remote_file,
                        source_kind='pypdfium2_annot_launch'
                    ))

                else:
                    links.append(create_link_dict(
                        source_ref=source_ref,
                        rect_norm=rect_norm,
                        anchor_text=anchor_text,
                        link_type='Other Action',
                        action_kind=action_type,
                        source_kind='pypdfium2_annot_other'
                    ))

        finally:
            if annot_raw:
                #print(f"Closing annot at pos {pos}")
                pdfium_c.FPDFPage_CloseAnnot(annot_raw)

        pos += 1
    

def demo():
    """
    Demostrate the pypdfium2-informed analyze_pdf().
    """
    from pdflinkcheck.io import get_first_pdf_in_cwd

    data = analyze_pdf(pdf_path = get_first_pdf_in_cwd())
    print(f"list(data) = {list(data)}")
    print("pypdfium2-based analysis complete.")
    print("Use the pdflinkcheck CLI, GUI, or web server to generate export files.")

if __name__ == "__main__":
    demo()
