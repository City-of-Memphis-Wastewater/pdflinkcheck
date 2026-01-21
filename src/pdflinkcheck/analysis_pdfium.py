# src/pdflinkcheck/analysis_pdfium.py
from __future__ import annotations
import ctypes
from typing import List, Dict, Any
from pdflinkcheck.helpers import PageRef

from pdflinkcheck.environment import pdfium_is_available
from pdflinkcheck.helpers import PageRef

try:
    if pdfium_is_available():
        import pypdfium2 as pdfium
        import pypdfium2.raw as pdfium_c
        print(dir(pdfium_c))
        #from pypdfium2._helpers.misc import PdfiumBase # you dont want to do this, it overrides pdfium

                    
    else:
        pdfium = None
        pdfium_c = None
except ImportError:
    pdfium = None
    pdfium_c = None

def analyze_pdf(path: str) -> Dict[str, Any]:
    # 1. Guard the entry point
    if not pdfium_is_available() or pdfium is None:
        print(f"pdfium_is_available() = {pdfium_is_available()}")
        print(f"pdfium = {pdfium}")
        
        raise ImportError(
            "pypdfium2 is not installed. "
            "\nInstall it with: \n\tpip install pdflinkcheck[pdfium] \n\t OR \n\t uv sync --extra pdfium"
        )
    doc = pdfium.PdfDocument(path)

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
        #print(f"page_index = {page_index}")
        #print(f"params = {params}")
        #print(help(pdfium_c.FPDFDest_GetView))
        #destination_view = pdfium_c.FPDFDest_GetView(dest)
        page_idx = PageRef.from_index(dest.get_index()).machine if dest else 0
        if title or page_idx > 0:
            key = (title, page_idx)
            if key not in seen_toc:
                toc_list.append({"level": item.level + 1, "title": title, "target_page": page_idx})
                seen_toc.add(key)

    # 2. Link Enumeration
    for page_index in range(len(doc)):
        page = doc.get_page(page_index)
        text_page = page.get_textpage()
        source_ref = PageRef.from_index(page_index)

        # --- A. EXTERNAL WEB LINKS ---
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

        # --- B. INTERNAL GOTO LINKS (Standard Annotations) ---
        # We iterate through standard link annotations for GoTo actions
        pos = 0
        while True:
            annot_raw = pdfium_c.FPDFPage_GetAnnot(page.raw, pos)
            if not annot_raw:
                break
            try:
                subtype = pdfium_c.FPDFAnnot_GetSubtype(annot_raw)
                if subtype == pdfium_c.FPDF_ANNOT_LINK:
                    # Get Rect
                    fs_rect = pdfium_c.FS_RECTF()
                    pdfium_c.FPDFAnnot_GetRect(annot_raw, fs_rect)
                                    
                    anchor_text = get_pdfium_text_safe(text_page, fs_rect)
                    
                    # Try to get Destination
                    link_annot = pdfium_c.FPDFAnnot_GetLink(annot_raw)
                    
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
                    action = pdfium_c.FPDFLink_GetAction(link_annot)
                    action_type = pdfium_c.FPDFAction_GetType(action)
                    if False: # worth keeping around
                        print(f"action_type = {action_type}")
                    # doc_raw does not exist yet?
                    result = get_action_info(doc, action, fs_rect, anchor_text, source_ref, link_annot)
                    # pdfium_c.FPDFAction_CloseAction(action)
                    dest = pdfium_c.FPDFLink_GetDest(doc.raw, link_annot)
                    
                    if dest:
                        dest_idx = pdfium_c.FPDFDest_GetDestPageIndex(doc.raw, dest)
                        dest_ref = PageRef.from_index(dest_idx)
                        
                        links.append({
                            'page': source_ref.machine,
                            'rect': [fs_rect.left, fs_rect.bottom, fs_rect.right, fs_rect.top],
                            'link_text': anchor_text or "Link (No Text)",
                            'type': 'Internal (GoTo/Dest)',
                            'destination_page': dest_ref.machine,
                            'source_kind': 'pypdfium2_annot'
                        })

            finally:
                pass
                # pdfium_c.FPDF_CloseAnnot(annot_raw) # does not exist
            # Note: We don't close annot here if we are just enumerating by index 
            # in some builds, but standard practice is to increment pos
            pos += 1

        page.close()
        text_page.close()

    doc.close()
    return {"links": links, "toc": toc_list, "file_ov": file_ov}

def get_pdfium_text_safe(text_page, fs_rect, tolerance=2.0):
    # Ensure min/max logic so we don't pass an inverted rect to PDFium
    l = min(fs_rect.left, fs_rect.right) - tolerance
    r = max(fs_rect.left, fs_rect.right) + tolerance
    t = max(fs_rect.top, fs_rect.bottom) + tolerance
    b = min(fs_rect.top, fs_rect.bottom) - tolerance
    
    return text_page.get_text_bounded(left=l, top=t, right=r, bottom=b).strip()

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


def get_action_info(doc, action, fs_rect, anchor_text, source_ref, link_annot):
    if not action:
        return None
    # ... fill in url / remote_file / dest_page / type / etc.
    doc_raw = doc.raw
    action_type = pdfium_c.FPDFAction_GetType(action)
    result = {'action_type': action_type}
    
    if action_type == 1:  # FPDFACTION_GOTO
        # Your existing dest handling
        dest = pdfium_c.FPDFLink_GetDest(doc.raw, link_annot)
        if dest:
            dest_idx = pdfium_c.FPDFDest_GetDestPageIndex(doc.raw, dest)
            # ... add as Internal (GoTo/Dest)

    elif action_type == 3:  # FPDFACTION_URI
        # Extract URI string (very similar to your web-link buffer code)
        if hasattr(action, "get_uri"):
            uri = action.get_uri()
        else:
            uri = None
            
        result["uri"] = uri
        """print(help(pdfium_c.FPDFAction_GetURIPath))
        buflen = pdfium_c.FPDFAction_GetURIPath(action, None, 0)
        if buflen > 0:
            buffer = (pdfium_c.c_ushort * buflen)()
            pdfium_c.FPDFAction_GetURIPath(action, buffer, buflen)
            uri = ctypes.string_at(buffer, (buflen-1)*2).decode('utf-16le')
            links.append({
                'page': source_ref.machine,
                'rect': [fs_rect.left, fs_rect.bottom, fs_rect.right, fs_rect.top],
                'link_text': anchor_text or uri,
                'type': 'External (URI)',
                'url': uri,
                'source_kind': 'pypdfium2_annot_uri'
            })"""

    elif action_type == 2:  # FPDFACTION_GOTOR
        # Extract remote file
        filespec = pdfium_c.FPDFAction_GetFileSpec(action)
        if filespec:
            path_len = pdfium_c.FPDFDoc_GetFileSpecFileName(filespec, None, 0)
            if path_len > 0:
                path_buf = (pdfium_c.c_ushort * path_len)()
                pdfium_c.FPDFDoc_GetFileSpecFileName(filespec, path_buf, path_len)
                remote_path = ctypes.string_at(path_buf, (path_len-1)*2).decode('utf-16le')
                # Optional: also get dest if present
                dest = pdfium_c.FPDFAction_GetDest(action)  # may be null
                dest_page = None
                if dest:
                    dest_page = pdfium_c.FPDFDest_GetDestPageIndex(doc.raw, dest)
                links.append({
                    'page': source_ref.machine,
                    'rect': [fs_rect.left, fs_rect.bottom, fs_rect.right, fs_rect.top],
                    'link_text': anchor_text or remote_path,
                    'type': 'Remote (GoToR)',
                    'remote_file': remote_path,
                    'destination_page': dest_page if dest_page is not None else None,
                    'source_kind': 'pypdfium2_annot_gotor'
                })

    elif action_type == 4:  # FPDFACTION_LAUNCH
        # Similar to GoToR — often overlaps
        # Use same FPDFAction_GetFileSpec(...)
        # type: 'Launch'
        pass

    else:
        # Catch-all for named, JS, etc.
        links.append({
            'page': source_ref.machine,
            'rect': [fs_rect.left, fs_rect.bottom, fs_rect.right, fs_rect.top],
            'link_text': anchor_text or f"Unsupported action {action_type}",
            'type': 'Other Action',
            'action_kind': action_type,
            'source_kind': 'pypdfium2_annot_other'
        })
    return result

def is_high_level(obj):
    return isinstance(obj, PdfiumBase)


if __name__ == "__main__":
    import json
    import sys
    filename = "temOM.pdf"
    results = analyze_pdf(filename)
    print(json.dumps(results, indent=2))
