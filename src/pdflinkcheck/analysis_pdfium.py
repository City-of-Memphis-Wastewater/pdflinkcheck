import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c
import ctypes
from typing import List, Dict, Any
from pdflinkcheck.helpers import PageRef

def analyze_pdf(path: str) -> Dict[str, Any]:
    """
    Extracts TOC and Links from a PDF using pypdfium2.
    Uses direct C-API calls to ensure compatibility with varied PDFium builds.
    """
    doc = pdfium.PdfDocument(path)
    links = []
    toc_list = []
    seen_toc = set()

    # 1. TOC Extraction
    for item in doc.get_toc():
        title = item.get_title() if hasattr(item, "get_title") else ""
        page_idx = PageRef.from_index(item.get_dest().get_index()).machine if item.get_dest() else 0
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

        # Access WebLinks interface (more robust than Annotations in some builds)
        pagelink_raw = pdfium_c.FPDFLink_LoadWebLinks(text_page.raw)
        
        if pagelink_raw:
            count = pdfium_c.FPDFLink_CountWebLinks(pagelink_raw)
            for i in range(count):
                # Extract URL (UTF-16LE decoding)
                buflen = pdfium_c.FPDFLink_GetURL(pagelink_raw, i, None, 0)
                url = ""
                if buflen > 0:
                    buffer = (pdfium_c.c_uint16 * buflen)() 
                    pdfium_c.FPDFLink_GetURL(pagelink_raw, i, buffer, buflen)
                    url = ctypes.string_at(buffer, (buflen-1)*2).decode('utf-16le')

                # Extract Bounding Box (7-argument signature for binary compatibility)
                l, t, r, b = (ctypes.c_double() for _ in range(4))
                pdfium_c.FPDFLink_GetRect(
                    pagelink_raw, i, 0, 
                    ctypes.byref(l), ctypes.byref(t), ctypes.byref(r), ctypes.byref(b)
                )
                
                link_dict = {
                    'page': source_ref.machine,
                    'rect': [l.value, b.value, r.value, t.value],
                    'link_text': url,
                    'type': 'External (URI)',
                    'url': url,
                    'target': url,
                    'source_kind': 'pypdfium2'
                }

                # Extract Text from the defined coordinates
                extracted_text = text_page.get_text_bounded(
                    left=l.value, top=t.value, right=r.value, bottom=b.value
                )
                if extracted_text:
                    link_dict['link_text'] = extracted_text.strip()
                
                links.append(link_dict)

            pdfium_c.FPDFLink_CloseWebLinks(pagelink_raw)

        page.close()
        text_page.close()

    doc.close()
    return {"links": links, "toc": toc_list}

if __name__ == "__main__":
    import json
    import sys
    if len(sys.argv) > 1:
        filename = sys.argv[1]
        results = analyze_pdf(filename)
        print(json.dumps(results, indent=2))