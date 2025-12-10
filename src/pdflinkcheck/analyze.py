import sys
from pathlib import Path
import logging
# Configure logging to suppress low-level pdfminer messages
logging.getLogger("fitz").setLevel(logging.ERROR) 

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
    
    pdf_file = example_path
    if not pdf_file:
        print(fr"If running in WSL, use a Linux path like: {example_path}")
        pdf_file = str(Path(input('Paste a PDF file path: ')))
    return pdf_file

import fitz # PyMuPDF

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

def get_text_from_rect(page, rect):
    """
    Extracts the text content from the PDF page that lies within the given PyMuPDF Rect.
    This is the link's anchor text.
    """
    if not rect or rect.is_empty:
        return 'N/A: Rect Empty'
    
    # Use 'text' output mode and clip the text extraction to the link rectangle.
    # The 'sort' parameter can help if text runs across multiple lines.
    text = page.get_text('text', clip=rect, sort=True).strip()
    
    # Clean up common PDF extraction artifacts (like multiple spaces or newlines)
    text = ' '.join(text.split()) 
    
    return text if text else 'N/A: Text Not Found'


# 2. Updated Main Inspection Function to Include Text Extraction
def inspect_pdf_hyperlinks_fitz(pdf_path):
    links_data = []
    try:
        doc = fitz.open(pdf_path)

        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            
            
            for link in page.get_links():

                page_obj = doc.load_page(page_num)
                link_rect = get_link_rect(link)
                
                rect_obj = link.get("from")
                xref = link.get("xref")
                #print(f"rect_obj = {rect_obj}")
                #print(f"xref = {xref}")
                
                # try to see all possible keys for link

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
    return links_data

def inspect_pdf_hyperlinks_fitz_stable(pdf_path):
    links_data = []
    try:
        doc = fitz.open(pdf_path)

        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            
            for link in page.get_links():
                # Rect is a fitz.Rect object. We will pass it as is.
                link_dict = {
                    'page': int(page_num) + 1,
                    'rect': link.get('rect')
                }

                if link['kind'] == fitz.LINK_URI:
                    link_dict.update({
                        'type': 'External (URI)',
                        'url': link.get('uri')
                    })
                
                elif link['kind'] == fitz.LINK_GOTO:
                    link_dict.update({
                        'type': 'Internal (GoTo/Dest)',
                        'destination_page': int(link.get('page')) + 1,
                        'destination_view': link.get('to')
                    })
                
                elif link['kind'] == fitz.LINK_GOTOR:
                    link_dict.update({
                        'type': 'Remote (GoToR)',
                        'remote_file': link.get('file'),
                        'destination': link.get('to')
                    })
                
                elif link.get('page') is not None and link['kind'] != fitz.LINK_GOTO: 
                    # Internal Jumps that are not LINK_GOTO (e.g., Named Actions resolved by fitz)
                    link_dict.update({
                        'type': 'Internal (Resolved Action)',
                        'destination_page': int(link.get('page')) + 1,
                        'destination_view': link.get('to'),
                        'source_kind': link.get('kind')
                    })
                    
                else:
                    # Handle everything else (mailto, launch, generic actions)
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
    return links_data

def inspect_pdf_hyperlinks_fitz_0(pdf_path):
    links_data = []
    try:
        doc = fitz.open(pdf_path)

        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            
            for link in page.get_links():
                link_dict = {
                    'page': int(page_num) + 1,
                    'rect': link.get('rect')
                }

                if link['kind'] == fitz.LINK_URI:
                    link_dict.update({
                        'type': 'External (URI)',
                        'url': link.get('uri')
                    })
                
                elif link['kind'] == fitz.LINK_GOTO:
                    link_dict.update({
                        'type': 'Internal (GoTo/Dest)',
                        'destination_page': int(link.get('page')) + 1,
                        'destination_view': link.get('to')
                    })
                
                elif link['kind'] == fitz.LINK_GOTOR:
                    link_dict.update({
                        'type': 'Remote (GoToR)',
                        'remote_file': link.get('file'),
                        'destination': link.get('to')
                    })
                
                # --- NEW/UPDATED LOGIC: Catching the Internal Jumps that are not LINK_GOTO ---
                elif link.get('page') is not None and link['kind'] != fitz.LINK_GOTO: 
                    # If it has a target page index but wasn't caught as LINK_GOTO (kind 2), 
                    # it must be a Named/Action-based internal jump that fitz resolved partially.
                    link_dict.update({
                        'type': 'Internal (Resolved Action)',
                        'destination_page': int(link.get('page')) + 1,
                        'destination_view': link.get('to'),
                        'source_kind': link.get('kind') # Keep original kind for debugging
                    })
                    
                else:
                    # Handle everything else (mailto, launch, generic actions)
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
    return links_data

def call_v4_stable():

    pdf_file = get_pdf_file()
    extracted_links = inspect_pdf_hyperlinks_fitz(pdf_file)

    if extracted_links:
        # Separate the lists based on the new 'type' key
        uri_links = [link for link in extracted_links if link['type'] == 'External (URI)']
        goto_links = [link for link in extracted_links if link['type'] == 'Internal (GoTo/Dest)']
        resolved_action_links = [link for link in extracted_links if link['type'] == 'Internal (Resolved Action)'] # <-- NEW RESOLVED LIST
        other_links = [link for link in extracted_links if link['type'] not in ['External (URI)', 'Internal (GoTo/Dest)', 'Internal (Resolved Action)']]

        
        total_internal_links = len(goto_links) + len(resolved_action_links)
        
        print(f"\n--- Link Analysis Results for {pdf_file} ---")
        print(f"Total links found: {len(extracted_links)} (External: {len(uri_links)}, Internal Jumps: {total_internal_links}, Other: {len(other_links)})")

        print("\n## External URI Links (Checkable)")
        if uri_links:
            for link in uri_links:
                print(f"  Page {link['page']}: {link['url']}")
        else:
            print("  No external URI links found.")

        print("\n## Internal Jumps (GoTo & Resolved Actions)")
        if total_internal_links > 0:
            count = 1
            # Report simple GoTo links
            for link in goto_links:
                print(f" {count}. Page {link['page']}: Jumps directly to Page {link['destination_page']}")
                count+=1
            # Report resolved action links (the 247 links)
            for link in resolved_action_links:
                print(f" {count}. Page {link['page']}: Jumps via Action/Dest to Page {link['destination_page']}")
                count+=1
        else:
            print("  No internal GoTo or Resolved Action links found.")
            
        print("\n## Other Links (mailto, tel, GoToR)")
        if other_links:
            for link in other_links:
                target = link.get('url') or link.get('remote_file') or link.get('target')
                print(f"  Page {link['page']}: {link['type']} -> {target}")
        else:
            print("  No other link types found.")

    else:
        print(f"\nNo hyperlinks of any type were found in {pdf_file}.")


def call_v5():

    pdf_file = get_pdf_file()
    extracted_links = inspect_pdf_hyperlinks_fitz(pdf_file)

    if extracted_links:
        # Separate the lists based on the new 'type' key
        uri_links = [link for link in extracted_links if link['type'] == 'External (URI)']
        goto_links = [link for link in extracted_links if link['type'] == 'Internal (GoTo/Dest)']
        resolved_action_links = [link for link in extracted_links if link['type'] == 'Internal (Resolved Action)'] # <-- NEW RESOLVED LIST
        other_links = [link for link in extracted_links if link['type'] not in ['External (URI)', 'Internal (GoTo/Dest)', 'Internal (Resolved Action)']]


        total_internal_links = len(goto_links) + len(resolved_action_links)

        print(f"\n--- Link Analysis Results for {pdf_file} ---")
        print(f"Total links found: {len(extracted_links)} (External: {len(uri_links)}, Internal Jumps: {total_internal_links}, Other: {len(other_links)})")

        print("\n## External URI Links (Checkable)")
        if uri_links:
            for link in uri_links:
                print(f" Page {link['page']}: {link['url']}")
        else:
            print(" No external URI links found.")

        print("\n## Internal Jumps (GoTo & Resolved Actions)")
        if total_internal_links > 0:
            count = 1
            
            # Helper function to print the detailed line
            def print_internal_link(link, is_goto=False):
                type_str = "GoTo" if is_goto else "Action/Dest"
                # PyMuPDF Rect object format: (x0, y0, x1, y1)
                rect_str = f"({int(link['rect'][0])}, {int(link['rect'][1])}) to ({int(link['rect'][2])}, {int(link['rect'][3])})" if link['rect'] else 'N/A'
                
                print(f" {count}. Page {link['page']} (Rect: {rect_str}): Jumps via {type_str} to Page {link['destination_page']}")
                # Only show destination view if it's not the default (often None or empty list)
                if link['destination_view']:
                    print(f"     -> View: {link['destination_view']}")


            # Report simple GoTo links
            for link in goto_links:
                print_internal_link(link, is_goto=True)
                count+=1
            
            # Report resolved action links (the 247 links)
            for link in resolved_action_links:
                print_internal_link(link, is_goto=False)
                count+=1
        else:
            print(" No internal GoTo or Resolved Action links found.")

        print("\n## Other Links (mailto, tel, GoToR)")
        if other_links:
            for link in other_links:
                target = link.get('url') or link.get('remote_file') or link.get('target')
                print(f" Page {link['page']}: {link['type']} -> {target}")
        else:
            print(" No other link types found.")

    else:
        print(f"\nNo hyperlinks of any type were found in {pdf_file}.")

def call_v6(): # <--- ITERATED TO V6

    pdf_file = get_pdf_file()
    extracted_links = inspect_pdf_hyperlinks_fitz(pdf_file)

    if extracted_links:
        # Separate the lists based on the 'type' key
        uri_links = [link for link in extracted_links if link['type'] == 'External (URI)']
        goto_links = [link for link in extracted_links if link['type'] == 'Internal (GoTo/Dest)']
        resolved_action_links = [link for link in extracted_links if link['type'] == 'Internal (Resolved Action)']
        other_links = [link for link in extracted_links if link['type'] not in ['External (URI)', 'Internal (GoTo/Dest)', 'Internal (Resolved Action)']]

        
        total_internal_links = len(goto_links) + len(resolved_action_links)
        
        print(f"\n--- Link Analysis Results for {pdf_file} ---")
        print(f"Total links found: {len(extracted_links)} (External: {len(uri_links)}, Internal Jumps: {total_internal_links}, Other: {len(other_links)})")

        print("\n## External URI Links (Checkable)")
        if uri_links:
            for link in uri_links:
                print(f"  Page {link['page']}: {link['url']}")
        else:
            print("  No external URI links found.")

        print("\n## Internal Jumps (GoTo & Resolved Actions)")
        if total_internal_links > 0:
            count = 1
            
            # Helper function to print the detailed line - UPDATED TO HANDLE fitz.Rect
            def print_internal_link(link, is_goto=False):
                type_str = "GoTo" if is_goto else "Action/Dest"
                
                # Access the fitz.Rect object attributes directly
                rect = link['rect']
                if rect and not rect.is_empty:
                    # Use integer coordinates for a cleaner look
                    rect_str = f"({int(rect.x0)}, {int(rect.y0)}) to ({int(rect.x1)}, {int(rect.y1)})"
                else:
                    rect_str = 'N/A'
                
                # Print the main link line
                print(f" {count}. Page {link['page']} (Rect: {rect_str}): Jumps via {type_str} to Page {link['destination_page']}")
                
                # Only show destination view if it's not the default
                if link['destination_view'] and link['destination_view'] != [fitz.PDF_ANY_DEST]:
                    print(f"     -> View: {link['destination_view']}")


            # Report simple GoTo links
            for link in goto_links:
                print_internal_link(link, is_goto=True)
                count+=1
            
            # Report resolved action links
            for link in resolved_action_links:
                print_internal_link(link, is_goto=False)
                count+=1
        else:
            print("  No internal GoTo or Resolved Action links found.")

        print("\n## Other Links (mailto, tel, GoToR)")
        if other_links:
            for link in other_links:
                target = link.get('url') or link.get('remote_file') or link.get('target')
                print(f"  Page {link['page']}: {link['type']} -> {target}")
        else:
            print("  No other link types found.")

    else:
        print(f"\nNo hyperlinks of any type were found in {pdf_file}.")


def call_v7(): 

    pdf_file = get_pdf_file()
    # 1. Extract all active links (now with link_text)
    extracted_links = inspect_pdf_hyperlinks_fitz(pdf_file) 
    
    # 2. Find link remnants
    remnants = find_link_remnants(pdf_file, extracted_links) # Pass active links to exclude them

    if extracted_links or remnants:
        # Separate the lists based on the 'type' key
        uri_links = [link for link in extracted_links if link['type'] == 'External (URI)']
        goto_links = [link for link in extracted_links if link['type'] == 'Internal (GoTo/Dest)']
        resolved_action_links = [link for link in extracted_links if link['type'] == 'Internal (Resolved Action)']
        other_links = [link for link in extracted_links if link['type'] not in ['External (URI)', 'Internal (GoTo/Dest)', 'Internal (Resolved Action)']]

        total_internal_links = len(goto_links) + len(resolved_action_links)
        
        print(f"\n--- Link Analysis Results for {Path(pdf_file).name} ---")
        print(f"Total active links: {len(extracted_links)} (External: {len(uri_links)}, Internal Jumps: {total_internal_links}, Other: {len(other_links)})")
        print(f"Total **potential missing links** found: {len(remnants)}")
        print("-" * 50)

        # ------------------- Section 1: ACTIVE LINKS (With Anchor Text) -------------------
        print("\n## 🔗 Active URI Links (External & Other)")
        print("{:<5} | {:<40} | {}".format("Page", "Anchor Text", "Target URI/Action"))
        print("-" * 70)
        
        uri_and_other = uri_links + other_links
        for link in uri_and_other:
            target = link.get('url') or link.get('remote_file') or link.get('target')
            link_text = link.get('link_text', 'N/A')
            print("{:<5} | {:<40} | {}".format(link['page'], link_text[:40], target))
        if not uri_and_other: print("  No external or 'Other' links found.")


        print("\n## 🖱️ Active Internal Jumps (GoTo & Resolved Actions)")
        print("{:<5} | {:<40} | {}".format("Page", "Anchor Text", "Jumps To Page"))
        print("-" * 70)
        
        if total_internal_links > 0:
            all_internal = goto_links + resolved_action_links
            for link in all_internal:
                link_text = link.get('link_text', 'N/A')
                print("{:<5} | {:<40} | {}".format(link['page'], link_text[:40], link['destination_page']))
        else:
            print("  No internal GoTo or Resolved Action links found.")
            
        # ------------------- Section 2: REMNANTS (Missing Links) -------------------
        print("\n" + "=" * 70)
        print("## ⚠️ Link Remnants (Potential Missing Links to Fix)")
        print("=" * 70)
        
        if remnants:
            print("{:<5} | {:<15} | {}".format("Page", "Remnant Type", "Text Found (Needs Hyperlink)"))
            print("-" * 70)
            for remnant in remnants:
                print("{:<5} | {:<15} | {}".format(remnant['page'], remnant['type'], remnant['text']))
        else:
            print("  No URI or Email remnants found that are not already active links.")
            

    else:
        print(f"\nNo hyperlinks or link remnants of any type were found in {pdf_file}.")

def call_stable():
    call_v7()

if __name__ == "__main__":
    call_stable()