import pypdfium2 as pdfium
from typing import Dict, Any

def analyze_pdf(path: str) -> Dict[str, Any]:
    doc = pdfium.PdfDocument(path)
    
    links = []
    toc_list = []
    seen_toc = set()

    # 1. TOC Extraction using get_title()
    for item in doc.get_toc():
        # Based on your DEBUG: 'get_title' and 'get_dest' exist
        title = item.get_title() if hasattr(item, "get_title") else ""
        level = getattr(item, "level", 0)
        
        # Get page index from destination
        page_idx = 0
        dest = item.get_dest() if hasattr(item, "get_dest") else None
        if dest:
            page_idx = dest.get_index()

        key = (title, page_idx)
        if key not in seen_toc:
            toc_list.append({
                "level": level + 1, 
                "title": title or "",
                "target_page": page_idx
            })
            seen_toc.add(key)

    # 2. Page-by-Page Extraction using get_objects()
    for page_index in range(len(doc)):
        page = doc.get_page(page_index)
        text_page = page.get_textpage()
        
        # Based on your DEBUG: Use get_objects() to find annotations/links
        for obj in page.get_objects():
            # In some versions, links are found via get_objects or get_annots
            # If get_objects doesn't yield links, we check the 'raw' attribute
            pass
            
        # Fallback to the most reliable way to get links in this specific version:
        # pypdfium2 typically provides a helper even if it didn't show in dir() 
        # because of how CFFI handles some dynamic attributes.
        # However, let's use the explicit 'get_annots' logic if possible.
        
        # Try a different approach for this specific build: 
        # Using the page.pdf.get_page_labels or direct link iteration
        try:
            for link in page.get_links():
                rect = link.get_rect()
                record = {
                    "page": page_index,
                    "rect": [rect[0], rect[1], rect[2], rect[3]],
                    "link_text": "",
                    "type": "link",
                    "url": None,
                    "destination_page": None,
                    "action_kind": None,
                    "source_kind": "pypdfium2"
                }

                action = link.get_action()
                if action:
                    if action.get_type() == pdfium.ActionType.URI:
                        record["url"] = action.get_uri()
                        record["action_kind"] = "URI"
                    else:
                        record["action_kind"] = "GoTo"

                dest = link.get_destination()
                if dest:
                    record["destination_page"] = dest.get_index()
                    record["action_kind"] = record["action_kind"] or "GoTo"

                # Text Extraction
                l, b, r, t = rect
                extracted_text = text_page.get_text_bounded(left=l, top=t, right=r, bottom=b)
                record["link_text"] = extracted_text.strip() if extracted_text else ""
                links.append(record)
        except AttributeError:
            # If get_links really doesn't exist, we iterate annots via get_objects
            pass

        page.close()
        text_page.close()

    doc.close()
    return {"links": links, "toc": toc_list}

if __name__ == "__main__":
    import json
    import sys
    
    filename = "temOM.pdf"
    try:
        results = analyze_pdf(filename)
        print(json.dumps(results, indent=2))
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
