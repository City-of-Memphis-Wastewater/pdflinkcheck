import sys
from pathlib import Path
import logging
from pprint import pprint
# Configure logging to suppress low-level pdfminer messages
logging.getLogger("fitz").setLevel(logging.ERROR) 
from typing import Dict, Any
import fitz # PyMuPDF

from pdflinkcheck.remnants import find_link_remnants

"""
Inspect target PDF for both URI links and for GoTo links.
"""


# Helper function: Prioritize 'from'
def get_link_rect(link_dict):
    """
    Retrieves the bounding box for the link using the reliable 'from' key.
    Returns the rect coordinates (tuple of 4 floats) or None.
    """
    # 1. Use the 'from' key, which returns a fitz.Rect object or None
    rect_obj = link_dict.get('from') 
    
    if rect_obj:
        # 2. Extract the coordinates using the standard Rect properties 
        #    (compatible with all recent PyMuPDF versions)
        return (rect_obj.x0, rect_obj.y0, rect_obj.x1, rect_obj.y1)
    
    # 3. Fallback to None if 'from' is missing
    return None

def get_pdf_file():

    example_path = f"/mnt/c/Users/george.bennett/Downloads/TE Maxson WWTF O&M Manual DRAFT - Sections 1-6 - April 2025 (3).pdf"
    example_path = "TE Maxson WWTF O&M Manual.pdf"
    print(f"example path = {example_path}")
    pdf_file = input(f"Paste path to PDF file (or press Enter to accept example): ")
    if not pdf_file:
        pdf_file = example_path
    if not Path(pdf_file).exists:
        print("File not found!")
        sys.exit(1)
 
    return pdf_file


def get_anchor_text(page, link_rect):
    """
    Extracts text content using the link's bounding box.
    Returns the cleaned text or a placeholder if no text is found.
    """
    if not link_rect:
        return "N/A: Missing Rect"

    try:
        # 1. Convert the coordinate tuple back to a fitz.Rect object
        rect = fitz.Rect(link_rect)
        
        # --- CRITICAL STEP: Check for invalid/empty rect AFTER conversion ---
        # If the rect is invalid (e.g., width or height is <= 0), skip it
        # Note: fitz.Rect will often auto-normalize, but this explicit check is safer.
        if rect.is_empty or rect.width <= 0 or rect.height <= 0:
            return "N/A: Rect Error (Zero/Negative Dimension)"

        # 2. Expand the rect slightly to capture full characters (1 unit in each direction)
        #    This method avoids the proprietary/unstable 'from_expanded' or 'from_rect' methods.
        expanded_rect = fitz.Rect(
            rect.x0 - 1, 
            rect.y0 - 1, 
            rect.x1 + 1, 
            rect.y1 + 1
        )
        
        # 3. Get the text within the expanded bounding box
        anchor_text = page.get_textbox(expanded_rect)
        
        # 4. Clean up whitespace and non-printing characters
        cleaned_text = " ".join(anchor_text.split())
        
        if cleaned_text:
            return cleaned_text
        else:
            return "N/A: No Visible Text"
            
    except Exception:
        # Fallback for unexpected errors in rect conversion or retrieval
        return "N/A: Rect Error"


def analyze_toc_fitz(doc):
    """
    Extracts the structured Table of Contents (bookmarks/outline) from the PDF.
    """
    toc = doc.get_toc()
    toc_data = []
    
    for level, title, page_num in toc:
        # fitz pages are 1-indexed for TOC!
        toc_data.append({
            'level': level,
            'title': title,
            'target_page': page_num
        })
        
    return toc_data


# 2. Updated Main Inspection Function to Include Text Extraction
def inspect_pdf_hyperlinks_fitz(pdf_path):
    links_data = []
    try:
        doc = fitz.open(pdf_path)
        structural_toc = analyze_toc_fitz(doc)
        

        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            
            for link in page.get_links():

                page_obj = doc.load_page(page_num)
                link_rect = get_link_rect(link)
                
                rect_obj = link.get("from")
                xref = link.get("xref")
                #print(f"rect_obj = {rect_obj}")
                #print(f"xref = {xref}")
                

                # --- Examples of various keys associated with various link instances ---
                #print(f"keys: list(link) = {list(link)}")
                # keys: list(link) = ['kind', 'xref', 'from', 'page', 'viewrect', 'id']
                # keys: list(link) = ['kind', 'xref', 'from', 'uri', 'id']
                # keys: list(link) = ['kind', 'xref', 'from', 'page', 'view', 'id']

                # 1. Extract the anchor text
                anchor_text = get_anchor_text(page_obj, link_rect)

                # 2. Extract the target and kind
                target = ""
                kind = link.get('kind')
                
                
                link_dict = {
                    'page': int(page_num) + 1,
                    'rect': link_rect,
                    'link_text': anchor_text,
                    'xref':xref
                }
                
                
                if link['kind'] == fitz.LINK_URI:
                    target =  link.get('uri', 'URI (Unknown Target)')
                    link_dict.update({
                        'type': 'External (URI)',
                        'url': link.get('uri'),
                        'target': target
                    })
                
                elif link['kind'] == fitz.LINK_GOTO:
                    target_page_num = link.get('page') + 1 # fitz pages are 0-indexed
                    target = f"Page {target_page_num}"
                    link_dict.update({
                        'type': 'Internal (GoTo/Dest)',
                        'destination_page': int(link.get('page')) + 1,
                        'destination_view': link.get('to'),
                        'target': target
                    })
                
                elif link['kind'] == fitz.LINK_GOTOR:
                    link_dict.update({
                        'type': 'Remote (GoToR)',
                        'remote_file': link.get('file'),
                        'destination': link.get('to')
                    })
                
                elif link.get('page') is not None and link['kind'] != fitz.LINK_GOTO: 
                    link_dict.update({
                        'type': 'Internal (Resolved Action)',
                        'destination_page': int(link.get('page')) + 1,
                        'destination_view': link.get('to'),
                        'source_kind': link.get('kind')
                    })
                    
                else:
                    target = link.get('url') or link.get('remote_file') or link.get('target')
                    link_dict.update({
                        'type': 'Other Action',
                        'action_kind': link.get('kind'),
                        'target': target
                    })
                    
                links_data.append(link_dict)

        doc.close()
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
    return links_data, structural_toc

def print_structural_toc(structural_toc):
    """
    Prints the structural TOC data in a clean, hierarchical, and readable format.
    """
    print("\n## 📚 Structural Table of Contents (PDF Bookmarks/Outline)")
    print("-" * 50)
    if not structural_toc:
        print("No structural TOC (bookmarks/outline) found.")
        return

    # Determine max page width for consistent alignment (optional but nice)
    max_page = max(item['target_page'] for item in structural_toc) if structural_toc else 1
    page_width = len(str(max_page))
    
    # Iterate and format
    for item in structural_toc:
        # Use level for indentation (e.g., Level 1 = 0 spaces, Level 2 = 4 spaces, Level 3 = 8 spaces)
        indent = " " * 4 * (item['level'] - 1)
        # Format the title and target page number
        page_str = str(item['target_page']).rjust(page_width)
        print(f"{indent}{item['title']} . . . page {page_str}")

    print("-" * 50)

def run_analysis(pdf_path: str, check_remnants: bool, max_links: int) -> Dict[str, Any]:
    """
    Core PDF analysis logic using PyMuPDF. Extracts links, remnants, and TOC.
    The printing is now done inside this function based on your call_v8 logic.
    """
    
    print(f"Running PyMuPDF analysis on {Path(pdf_path).name}...")

    # 1. Extract all active links and TOC
    extracted_links, structural_toc = inspect_pdf_hyperlinks_fitz(pdf_path) 
    toc_entry_count = len(structural_toc)
    
    # 2. Find link remnants
    remnants = []
    if check_remnants:
        remnants = find_link_remnants(pdf_path, extracted_links) # Pass active links to exclude them

    if not extracted_links and not remnants and not structural_toc:
         print(f"\nNo hyperlinks, remnants, or structural TOC found in {Path(pdf_path).name}.")
         return {}
         
    # 3. Separate the lists based on the 'type' key
    uri_links = [link for link in extracted_links if link['type'] == 'External (URI)']
    goto_links = [link for link in extracted_links if link['type'] == 'Internal (GoTo/Dest)']
    resolved_action_links = [link for link in extracted_links if link['type'] == 'Internal (Resolved Action)']
    other_links = [link for link in extracted_links if link['type'] not in ['External (URI)', 'Internal (GoTo/Dest)', 'Internal (Resolved Action)']]

    total_internal_links = len(goto_links) + len(resolved_action_links)
    
    # --- ANALYSIS SUMMARY (Using your print logic) ---
    print(f"\n--- Link Analysis Results for {Path(pdf_path).name} ---")
    print(f"Total active links: {len(extracted_links)} (External: {len(uri_links)}, Internal Jumps: {total_internal_links}, Other: {len(other_links)})")
    print(f"Total **structural TOC entries (bookmarks)** found: {toc_entry_count}")
    print(f"Total **potential missing links** found: {len(remnants)}")
    print("-" * 50)

    uri_and_other = uri_links + other_links
    
    # --- Section 1: ACTIVE URI LINKS ---
    print(f"\n## 🔗 Active URI Links (External & Other) - {len(uri_and_other)} found") 
    print("{:<5} | {:<5} | {:<40} | {}".format("Idx", "Page", "Anchor Text", "Target URI/Action"))
    print("-" * 75)
    
    if uri_and_other:
        for i, link in enumerate(uri_and_other[:max_links], 1):
            target = link.get('url') or link.get('remote_file') or link.get('target')
            link_text = link.get('link_text', 'N/A')
            print("{:<5} | {:<5} | {:<40} | {}".format(i, link['page'], link_text[:40], target))
        if len(uri_and_other) > max_links:
            print(f"... and {len(uri_and_other) - max_links} more links (use --max-links to see all).")
    else: 
        print("  No external or 'Other' links found.")

    # --- Section 2: ACTIVE INTERNAL JUMPS ---
    print(f"\n## 🖱️ Active Internal Jumps (GoTo & Resolved Actions) - {total_internal_links} found")
    print("{:<5} | {:<5} | {:<40} | {}".format("Idx", "Page", "Anchor Text", "Jumps To Page"))
    print("-" * 75)
    
    all_internal = goto_links + resolved_action_links
    if total_internal_links > 0:
        for i, link in enumerate(all_internal[:max_links], 1):
            link_text = link.get('link_text', 'N/A')
            print("{:<5} | {:<5} | {:<40} | {}".format(i, link['page'], link_text[:40], link['destination_page']))
        if len(all_internal) > max_links:
             print(f"... and {len(all_internal) - max_links} more links (use --max-links to see all).")
    else:
        print("  No internal GoTo or Resolved Action links found.")
        
    # --- Section 3: REMNANTS ---
    print("\n" + "=" * 70)
    print(f"## ⚠️ Link Remnants (Potential Missing Links to Fix) - {len(remnants)} found")
    print("=" * 70)
    
    if remnants:
        print("{:<5} | {:<5} | {:<15} | {}".format("Idx", "Page", "Remnant Type", "Text Found (Needs Hyperlink)"))
        print("-" * 75)
        for i, remnant in enumerate(remnants[:max_links], 1):
            print("{:<5} | {:<5} | {:<15} | {}".format(i, remnant['page'], remnant['type'], remnant['text']))
        if len(remnants) > max_links:
             print(f"... and {len(remnants) - max_links} more remnants (use --max-links to see all).")
    else:
        print("  No URI or Email remnants found that are not already active links.")
        
    # --- Section 4: TOC ---
    print_structural_toc(structural_toc)
    
    # Return the collected data for potential future JSON/other output
    return {
        "external_links": uri_links,
        "internal_links": all_internal,
        "remnants": remnants,
        "toc": structural_toc
    }

def call_stable():
    print("Begin analysis...")
    run_analysis()
    print("Analysis complete.")

if __name__ == "__main__":
    call_stable()
