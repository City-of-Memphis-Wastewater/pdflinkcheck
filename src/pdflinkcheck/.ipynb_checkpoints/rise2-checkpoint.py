# src/pdflinkcheck/rise_final.py  ←  FINAL VERSION (Dec 2025, Termux-ready)

import sys
from pathlib import Path
import re
import pdfplumber
import logging

# ──────────────────────────────────────────────────────────────
# 1. Kill the color warnings (they are harmless PDF junk)
# ──────────────────────────────────────────────────────────────
logging.getLogger("pdfplumber").setLevel(logging.ERROR)
logging.getLogger("pdfminer").setLevel(logging.ERROR)

# ──────────────────────────────────────────────────────────────
# 2. Regex patterns
# ──────────────────────────────────────────────────────────────
URI_PATTERN = re.compile(r'(?:https?|ftp|mhtml|file)://\S+|www\.\S+', re.IGNORECASE)
EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', re.IGNORECASE)

def get_pdf_file():
    default = "TE Maxson WWTF O&M Manual.pdf"
    pdf_file = input(f"Paste PDF path (or press Enter for default):\n  {default}\n> ").strip()
    if not pdf_file:
        pdf_file = default
    if not Path(pdf_file).exists():
        print("File not found!")
        sys.exit(1)
    return pdf_file

def extract_active_links(pdf_path):
    active = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            # ── External URI links (pdfplumber puts them in "uri") ──
            for annot in page.annots or []:
                uri = annot.get("uri")
                if uri:
                    rect = (annot["x0"], annot["top"], annot["x1"], annot["bottom"])
                    text = page.crop(rect).extract_text() or "N/A"
                    text = " ".join(text.split())[:60]
                    active.append({
                        "page": page_num,
                        "rect": rect,
                        "link_text": text,
                        "type": "External (URI)",
                        "url": uri,
                    })

            # ── Internal GoTo links (they have "dest" or are resolved via actions) ──
            for annot in page.annots or []:
                if annot.get("uri"):  # already handled
                    continue

                action = annot.get("A") or {}
                dest_name = action.get("D")
                if not dest_name:
                    continue

                rect = (annot["x0"], annot["top"], annot["x1"], annot["bottom"])
                text = page.crop(rect).extract_text() or "N/A"
                text = " ".join(text.split())[:60]

                # Resolve destination page number
                dest_page = "Unknown"
                try:
                    resolved = pdf.doc.resolve_dest(dest_name)
                    if resolved and resolved[0]:
                        dest_page = pdf.pages.index(resolved[0]) + 1
                except:
                    pass

                active.append({
                    "page": page_num,
                    "rect": rect,
                    "link_text": text,
                    "type": "Internal (GoTo/Dest)",
                    "destination_page": dest_page,
                })

    return active

def find_link_remnants(pdf_path, active_links):
    active_rects = {tuple(round(x, 2) for x in l["rect"]) for l in active_links}
    remnants = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            for match, kind in [(m, "URI") for m in URI_PATTERN.finditer(text)] + \
                               [(m, "Email") for m in EMAIL_PATTERN.finditer(text)]:
                remnant_text = match.group(0)
                for inst in page.search(remnant_text, regex=True):
                    rect = (inst["x0"], inst["top"], inst["x1"], inst["bottom"])
                    if tuple(round(x, 2) for x in rect) not in active_rects:
                        remnants.append({
                            "page": page_num,
                            "type": f"{kind} Remnant",
                            "text": remnant_text,
                        })
                        active_rects.add(tuple(round(x, 2) for x in rect))
                        break  # avoid duplicates
    return remnants

def call_stable():
    pdf_file = get_pdf_file()
    print(f"\nAnalyzing: {Path(pdf_file).name}\n{'='*80}")

    active_links = extract_active_links(pdf_file)
    remnants = find_link_remnants(pdf_file, active_links)

    external = [l for l in active_links if l["type"] == "External (URI)"]
    internal = [l for l in active_links if l["type"] == "Internal (GoTo/Dest)"]

    print(f"Active links: {len(active_links)} (External: {len(external)}, Internal GoTo: {len(internal)})")
    print(f"Potential missing links: {len(remnants)}")
    print("="*80)

    # External
    print("\nActive External Links")
    print("{:<5} | {:<50} | {}".format("Page", "Anchor Text", "URL"))
    print("-"*100)
    for l in external:
        print("{:<5} | {:<50} | {}".format(l["page"], l["link_text"], l["url"]))
    if not external:
        print("  None")

    # Internal GoTo
    print("\nActive Internal GoTo Links (Table of Contents, etc.)")
    print("{:<5} | {:<50} | {}".format("Page", "Anchor Text", "→ Page"))
    print("-"*100)
    for l in internal:
        print("{:<5} | {:<50} | → {}".format(l["page"], l["link_text"], l["destination_page"]))
    if not internal:
        print("  None")

    # Remnants
    print("\n" + "Link Remnants (Unlinked URLs/Emails)".center(100))
    print("="*100)
    if remnants:
        print("{:<5} | {:<15} | {}".format("Page", "Type", "Unlinked Text"))
        print("-"*100)
        for r in remnants:
            print("{:<5} | {:<15} | {}".format(r["page"], r["type"], r["text"]))
    else:
        print("  Perfect — no unlinked URLs or emails!")

if __name__ == "__main__":
    call_stable()