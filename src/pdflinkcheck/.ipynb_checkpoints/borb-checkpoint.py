# src/pdflinkcheck/borb.py 

from borb.pdf import Document
from borb.pdf import PDF
from borb.io.read.types import Name
import re
from pathlib import Path

URI_PATTERN = re.compile(r'(?:https?|ftp|mhtml|file)://\S+|www\.\S+', re.IGNORECASE)
EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', re.IGNORECASE)

def extract_with_borb(pdf_path):
    doc = Document()
    with open(pdf_path, "rb") as fh:
        PDF.loads(fh, doc)

    external = []
    internal = []
    remnants = set()

    for page in doc.get_pages():
        page_num = page.get_page_info().get_page_number() + 1

        # External links
        if "Annots" in page:
            for annot in page["Annots"]:
                obj = annot.get_object()
                if obj.get("/Subtype") == "/Link" and "/A" in obj and "/URI" in obj["/A"]:
                    uri = str(obj["/A"]["/URI"])
                    rect = obj.get("/Rect", [0,0,0,0])
                    text = "N/A"
                    external.append({
                        "page": page_num,
                        "text": text,
                        "url": uri,
                        "rect": rect
                    })

        # Internal GoTo (this is what you need!)
        content = page.get_content_string()
        # Look for BT ... /Dest (Name) ... ET patterns
        import re
        goto_matches = re.finditer(r'/Dest\s*\(([^)]+)\)', content)
        for m in goto_matches:
            dest_name = m.group(1)
            internal.append({
                "page": page_num,
                "dest": dest_name,
                "type": "Named Destination"
            })

        # Text remnants
        text = page.get_text_string()
        for match in URI_PATTERN.finditer(text):
            remnants.add((page_num, "URI", match.group(0)))
        for match in EMAIL_PATTERN.finditer(text):
            remnants.add((page_num, "Email", match.group(0)))

    return external, internal, remnants

def main():
    pdf = "TE Maxson WWTF O&M Manual.pdf"
    ext, int_links, rem = extract_with_borb(pdf)

    print(f"External links: {len(ext)}")
    print(f"Internal named destinations (GoTo): {len(int_links)}")
    print(f"Unlinked remnants: {len(rem)}")

    print("\nFirst 10 internal GoTo targets:")
    for i, link in enumerate(int_links[:10]):
        print(f"  {i+1}. Page {link['page']} → Destination: {link['dest']}")

if __name__ == "__main__":
    main()