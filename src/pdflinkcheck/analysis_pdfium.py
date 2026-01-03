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

    else:
        pdfium = None
        pdfium_c = None
except ImportError:
    pdfium = None
    pdfium_c = None

def analyze_pdf(path: str) -> Dict[str, Any]:
    # 1. Guard the entry point
    if not pdfium_is_available() or pdfium is None:
        raise ImportError(
            "pypdfium2 is not installed. "
            "Install it with: pip install pdflinkcheck[pdfium]"
        )
    doc = pdfium.PdfDocument(path)
    links = []
    toc_list = []
    seen_toc = set()

    # 1. TOC Extraction (Matches PyMuPDF logic)
    for item in doc.get_toc():
        title = item.get_title() if hasattr(item, "get_title") else ""
        dest = item.get_dest()
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
                    'target': url,
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
            
            subtype = pdfium_c.FPDFAnnot_GetSubtype(annot_raw)
            if subtype == pdfium_c.FPDF_ANNOT_LINK:
                # Get Rect
                fs_rect = pdfium_c.FS_RECTF()
                pdfium_c.FPDFAnnot_GetRect(annot_raw, fs_rect)
                
                # Try to get Destination
                link_annot = pdfium_c.FPDFAnnot_GetLink(annot_raw)
                dest = pdfium_c.FPDFLink_GetDest(doc.raw, link_annot)
                
                if dest:
                    dest_idx = pdfium_c.FPDFDest_GetDestPageIndex(doc.raw, dest)
                    dest_ref = PageRef.from_index(dest_idx)
                    
                    links.append({
                        'page': source_ref.machine,
                        'rect': [fs_rect.left, fs_rect.bottom, fs_rect.right, fs_rect.top],
                        'link_text': text_page.get_text_bounded(left=fs_rect.left, top=fs_rect.top, right=fs_rect.right, bottom=fs_rect.bottom).strip(),
                        'type': 'Internal (GoTo/Dest)',
                        'destination_page': dest_ref.machine,
                        'target': dest_ref.machine,
                        'source_kind': 'pypdfium2_annot'
                    })
            
            # Note: We don't close annot here if we are just enumerating by index 
            # in some builds, but standard practice is to increment pos
            pos += 1

        page.close()
        text_page.close()

    doc.close()
    return {"links": links, "toc": toc_list}

if __name__ == "__main__":
    import json
    import sys
    filename = "temOM.pdf"
    results = analyze_pdf(filename)
    print(json.dumps(results, indent=2))
