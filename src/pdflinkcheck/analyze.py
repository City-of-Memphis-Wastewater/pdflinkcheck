import sys
from pathlib import Path
import logging
from typing import Dict, Any, Optional, List

logging.getLogger("fitz").setLevel(logging.ERROR) 

import fitz # PyMuPDF
from pypdf import PdfReader
from pypdf.generic import Destination, NameObject, ArrayObject, IndirectObject

from pdflinkcheck.remnants import find_link_remnants
from pdflinkcheck.io import error_logger, export_report_data, LOG_FILE_PATH

"""
Inspect target PDF for both URI links and for GoTo links.
"""

# Helper function: Prioritize 'from'
def get_link_rect(link_dict):
    """
    Retrieves the bounding box for the link using the reliable 'from' key
    provided by PyMuPDF's link dictionary.

    Args:
        link_dict: A dictionary representing a single link/annotation 
                   returned by `page.get_links()`.

    Returns:
        A tuple of four floats (x0, y0, x1, y1) representing the 
        rectangular coordinates of the link on the page, or None if the 
        bounding box data is missing.
    """
    # 1. Use the 'from' key, which returns a fitz.Rect object or None
    rect_obj = link_dict.get('from') 
    
    if rect_obj:
        # 2. Extract the coordinates using the standard Rect properties 
        #    (compatible with all recent PyMuPDF versions)
        return (rect_obj.x0, rect_obj.y0, rect_obj.x1, rect_obj.y1)
    
    # 3. Fallback to None if 'from' is missing
    return None

def get_anchor_text(page, link_rect):
    """
    Extracts text content using the link's bounding box coordinates.
    The bounding box is slightly expanded to ensure full characters are captured.

    Args:
        page: The fitz.Page object where the link is located.
        link_rect: A tuple of four floats (x0, y0, x1, y1) representing the 
                   link's bounding box.

    Returns:
        The cleaned, extracted text string, or a placeholder message 
        if no text is found or if an error occurs.
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

def get_anchor_text_pypdf(page, rect) -> str:
    """
    Alternative to get_anchor_text().
    Status: Not ready yet.
    Extracts text within (or overlapping) the link's bounding box.
    Slightly expands the rect to capture full characters.
    """
    if rect is None:
        return "N/A: Missing Rect"
    
    try:
        # pypdf Rect: [x0, y0, x1, y1] (bottom-left origin)
        x0, y0, x1, y1 = rect
        if x0 >= x1 or y0 >= y1:
            return "N/A: Invalid Rect"
        
        # Expand slightly
        expand = 2
        expanded = (x0 - expand, y0 - expand, x1 + expand, y1 + expand)
        
        text = page.extract_text(
            x0=expanded[0], y0=expanded[1],
            x1=expanded[2], y1=expanded[3]
        )
        
        cleaned = " ".join(text.split()) if text else "N/A: No Visible Text"
        return cleaned
    except Exception:
        return "N/A: Extraction Error"
    

def analyze_toc_fitz(doc):
    """
    Extracts the structural Table of Contents (PDF Bookmarks/Outline) 
    from the PDF document using PyMuPDF's built-in functionality.

    Args:
        doc: The open fitz.Document object.

    Returns:
        A list of dictionaries, where each dictionary represents a TOC entry 
        with 'level', 'title', and 'target_page' (1-indexed).
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
#def inspect_pdf_hyperlinks_fitz(pdf_path):
def extract_toc(pdf_path):
    """
    Opens a PDF, iterates through all pages and extracts the structural table of contents (TOC/bookmarks).

    Args:
        pdf_path: The file system path (str) to the target PDF document.

    Returns:
        A list of dictionaries representing the structural TOC/bookmarks.
    """
    try:
        doc = fitz.open(pdf_path)
        structural_toc = analyze_toc_fitz(doc)
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
    return structural_toc


def serialize_fitz_object(obj):
    """Converts a fitz object (Point, Rect, Matrix) to a serializable type."""
    # Meant to avoid known Point errors like: '[ERROR] An unexpected error occurred during analysis: Report export failed due to an I/O error: Object of type Point is not JSON serializable'
    if obj is None:
        return None
    
    # 1. Handle fitz.Point (has x, y)
    if hasattr(obj, 'x') and hasattr(obj, 'y') and not hasattr(obj, 'x0'):
        return (obj.x, obj.y)
        
    # 2. Handle fitz.Rect and fitz.IRect (has x0, y0)
    if hasattr(obj, 'x0') and hasattr(obj, 'y0'):
        return (obj.x0, obj.y0, obj.x1, obj.y1)
        
    # 3. Handle fitz.Matrix (has a, b, c, d, e, f)
    if hasattr(obj, 'a') and hasattr(obj, 'b') and hasattr(obj, 'c'):
        return (obj.a, obj.b, obj.c, obj.d, obj.e, obj.f)
        
    # 4. Fallback: If it's still not a primitive type, convert it to a string
    if not isinstance(obj, (str, int, float, bool, list, tuple, dict)):
        # Examples: hasattr(value, 'rect') and hasattr(value, 'point'):
        # This handles Rect and Point objects that may slip through
        return str(obj)
        
    # Otherwise, return the object as is (it's already primitive)
    return obj

def extract_links(pdf_path):
    """
    Opens a PDF, iterates through all pages and extracts all link annotations. 
    It categorizes the links into External, Internal, or Other actions, and extracts the anchor text.
    
    Args:
        pdf_path: The file system path (str) to the target PDF document.

    Returns:
        A list of dictionaries, where each dictionary is a comprehensive 
           representation of an active hyperlink found in the PDF.
        
    """
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
                    'page': int(page_num) + 1, # accurate for link location, add 1
                    'rect': link_rect,
                    'link_text': anchor_text,
                    'xref':xref
                }
                
                # A. Clean Geom. Objects: Use the helper function on 'to' / 'destination'
                # Use the clean serialize_fitz_object() helper function on all keys that might contain objects
                destination_view = serialize_fitz_object(link.get('to'))

                # B. Correct Internal Link Page Numbering (The -1 correction hack)
                # This will be skipped by URI, which is not expected to have a page key
                target_page_num_reported = "N/A"
                if link.get('page') is not None:
                    target_page_num_reported = int(link.get('page'))+1 # accurate for link target, don't add 1 (weird)

                if link['kind'] == fitz.LINK_URI:
                    target =  link.get('uri', 'URI (Unknown Target)')
                    link_dict.update({
                        'type': 'External (URI)',
                        'url': link.get('uri'),
                        'target': target
                    })
                
                elif link['kind'] == fitz.LINK_GOTO:
                    target = f"Page {target_page_num_reported}"
                    link_dict.update({
                        'type': 'Internal (GoTo/Dest)',
                        'destination_page': target_page_num_reported,
                        'destination_view': destination_view,
                        'target': target
                    })
                
                elif link['kind'] == fitz.LINK_GOTOR:
                    link_dict.update({
                        'type': 'Remote (GoToR)',
                        'remote_file': link.get('file'),
                        'destination': destination_view
                    })
                
                elif link.get('page') is not None and link['kind'] != fitz.LINK_GOTO: 
                    target = f"Page {target_page_num_reported}"
                    link_dict.update({
                        'type': 'Internal (Resolved Action)',
                        'destination_page': target_page_num_reported,
                        'destination_view': destination_view,
                        'source_kind': link.get('kind'),
                        'target': target
                    })
                    
                else:
                    target = link.get('url') or link.get('remote_file') or link.get('target')
                    link_dict.update({
                        'type': 'Other Action',
                        'action_kind': link.get('kind'),
                        'target': target
                    })

                ## --- General Serialization Cleaner ---
                #for key, value in link_dict.items():
                #    if hasattr(value, 'rect') and hasattr(value, 'point'):
                #        # This handles Rect and Point objects that may slip through
                #        link_dict[key] = str(value)
                ## --- End Cleaner ---
                    
                links_data.append(link_dict)

        doc.close()
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
    return links_data

def print_structural_toc(structural_toc):
    """
    Prints the structural TOC data (bookmarks/outline) in a clean, 
    hierarchical, and readable console format.

    Args:
        structural_toc: A list of TOC dictionaries returned by `analyze_toc_fitz`.
    """
    print("\n" + "=" * 70)
    print("## Structural Table of Contents (PDF Bookmarks/Outline)")
    print("=" * 70)
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

    print("-" * 70)


def get_first_pdf_in_cwd() -> Optional[str]:
    """
    Scans the current working directory (CWD) for the first file ending 
    with a '.pdf' extension (case-insensitive).

    This is intended as a convenience function for running the tool 
    without explicitly specifying a path.

    Returns:
        The absolute path (as a string) to the first PDF file found, 
        or None if no PDF files are present in the CWD.
    """
    # 1. Get the current working directory (CWD)
    cwd = Path.cwd()
    
    # 2. Use Path.glob to find files matching the pattern. 
    #    We use '**/*.pdf' to also search nested directories if desired, 
    #    but typically for a single PDF in CWD, '*.pdf' is enough. 
    #    Let's stick to files directly in the CWD for simplicity.
    
    # We use list comprehension with next() for efficiency, or a simple loop.
    # Using Path.glob('*.pdf') to search the CWD for files ending in .pdf
    # We make it case-insensitive by checking both '*.pdf' and '*.PDF'
    
    # Note: On Unix systems, glob is case-sensitive by default.
    # The most cross-platform safe way is to iterate and check the suffix.
    
    try:
        # Check for files in the current directory only
        # Iterating over the generator stops as soon as the first match is found.
        first_pdf_path = next(
            p.resolve() for p in cwd.iterdir() 
            if p.is_file() and p.suffix.lower() == '.pdf'
        )
        return str(first_pdf_path)
    except StopIteration:
        # If the generator runs out of items, no PDF was found
        return None
    except Exception as e:
        # Handle potential permissions errors or other issues
        print(f"Error while searching for PDF in CWD: {e}", file=sys.stderr)
        return None

def run_analysis(pdf_path: str = None, check_remnants: bool = True, max_links: int = 0, export_format: Optional[str] = "JSON") -> Dict[str, Any]:
    """
    Core high-level PDF link analysis logic. 
    
    This function orchestrates the extraction of active links and TOC 
    using PyMuPDF, finds link remnants (plain text URLs/emails), and 
    prints a comprehensive, user-friendly report to the console.

    Args:
        pdf_path: The file system path (str) to the target PDF document.
        check_remnants: Boolean flag to enable/disable scanning for plain text 
                        links that are not active hyperlinks.
        max_links: Maximum number of links/remnants to display in each console 
                   section. If <= 0, all links will be displayed.

    Returns:
        A dictionary containing the structured results of the analysis:
        'external_links', 'internal_links', 'remnants', and 'toc'.
    """

    if pdf_path is None:
        pdf_path = get_first_pdf_in_cwd()
    if pdf_path is None:
        print("pdf_path is None")
        print("Tip: Drop a PDF in the current folder or pass in a path arg.")
        return
    try:
        print(f"Running PyMuPDF analysis on {Path(pdf_path).name}...")

        # 1. Extract all active links and TOC
        extracted_links = extract_links(pdf_path)
        structural_toc = extract_toc(pdf_path) 
        #extracted_links = extract_links_pypdf(pdf_path)
        #structural_toc = extract_toc_pypdf(pdf_path) 
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
        print("\n" + "✪" * 70)
        print(f"--- Link Analysis Results for {Path(pdf_path).name} ---")
        print(f"Total active links: {len(extracted_links)} (External: {len(uri_links)}, Internal Jumps: {total_internal_links}, Other: {len(other_links)})")
        print(f"Total **structural TOC entries (bookmarks)** found: {toc_entry_count}")
        print(f"Total **potential missing links** found: {len(remnants)}")
        print("✪" * 70)

        limit = max_links if max_links > 0 else None

        uri_and_other = uri_links + other_links
        
        # --- Section 1: ACTIVE URI LINKS ---
        print("\n" + "=" * 70)
        print(f"## Active URI Links (External & Other) - {len(uri_and_other)} found") 
        print("{:<5} | {:<5} | {:<40} | {}".format("Idx", "Page", "Anchor Text", "Target URI/Action"))
        print("=" * 70)
        
        if uri_and_other:
            for i, link in enumerate(uri_and_other[:limit], 1):
                target = link.get('url') or link.get('remote_file') or link.get('target')
                link_text = link.get('link_text', 'N/A')
                print("{:<5} | {:<5} | {:<40} | {}".format(i, link['page'], link_text[:40], target))
            if limit is not None and len(uri_and_other) > limit:
                print(f"... and {len(uri_and_other) - limit} more links (use --max-links to see all or --max-links 0 to show all).")

        else: 
            print(" No external or 'Other' links found.")

        # --- Section 2: ACTIVE INTERNAL JUMPS ---
        print("\n" + "=" * 70)
        print(f"## Active Internal Jumps (GoTo & Resolved Actions) - {total_internal_links} found")
        print("=" * 70)
        print("{:<5} | {:<5} | {:<40} | {}".format("Idx", "Page", "Anchor Text", "Jumps To Page"))
        print("-" * 70)
        
        all_internal = goto_links + resolved_action_links
        if total_internal_links > 0:
            for i, link in enumerate(all_internal[:limit], 1):
                link_text = link.get('link_text', 'N/A')
                print("{:<5} | {:<5} | {:<40} | {}".format(i, link['page'], link_text[:40], link['destination_page']))

            if limit is not None and len(all_internal) > limit:
                print(f"... and {len(all_internal) - limit} more links (use --max-links to see all or --max-links 0 to show all).")
        else:
            print(" No internal GoTo or Resolved Action links found.")
            
        # --- Section 3: REMNANTS ---
        print("\n" + "=" * 70)
        print(f"## ⚠️ Link Remnants (Potential Missing Links to Fix) - {len(remnants)} found")
        print("=" * 70)
        
        if remnants:
            print("{:<5} | {:<5} | {:<15} | {}".format("Idx", "Page", "Remnant Type", "Text Found (Needs Hyperlink)"))
            print("-" * 70)
            for i, remnant in enumerate(remnants[:limit], 1):
                print("{:<5} | {:<5} | {:<15} | {}".format(i, remnant['page'], remnant['type'], remnant['text']))
            if max_links!=0 and len(remnants) > max_links:
                print(f"... and {len(remnants) - max_links} more remnants (use --max-links to see all).")
        else:
            print(" No URI or Email remnants found that are not already active links.")
            
        # --- Section 4: TOC ---
        print_structural_toc(structural_toc)
        
        # Return the collected data for potential future JSON/other output
        final_report_data =  {
            "external_links": uri_links,
            "internal_links": all_internal,
            "remnants": remnants,
            "toc": structural_toc
        }

        # 5. Export Report 
        if export_format:
            # Assuming export_to will hold the output format string (e.g., "JSON")
            export_report_data(final_report_data, Path(pdf_path).name, export_format)

        return final_report_data
    except Exception as e:
        # Log the critical failure
        error_logger.error(f"Critical failure during run_analysis for {pdf_path}: {e}", exc_info=True)
        print(f"FATAL: Analysis failed. Check logs at {LOG_FILE_PATH}", file=sys.stderr)
        raise # Allow the exception to propagate or handle gracefully

def resolve_destination(reader: PdfReader, dest) -> Optional[int]:
    """
    Necessary for pypdf alternative functions to run.
    Resolve destination to page number (1-based).
    Handles direct page references, named dests via /Dests, and array forms.
    """
    if isinstance(dest, Destination):
        return dest.page_number + 1 if dest.page_number is not None else "N/A"
    
    if isinstance(dest, int) or isinstance(dest, IndirectObject):
        # Direct page reference
        page_num = reader.get_destination_page_number(dest)
        return page_num + 1
    
    if isinstance(dest, str):
        # Named destination
        root = reader.trailer["/Root"]
        if "/Dests" in root:
            dests = root["/Dests"]
            if "/Names" in dests and dest in dests["/Names"]:
                target = dests["/Names"][dest]
                if isinstance(target, ArrayObject):
                    return reader.get_destination_page_number(target[0]) + 1
        return "Named (Unresolved)"
    
    if isinstance(dest, ArrayObject) and len(dest) > 0:
        return reader.get_destination_page_number(dest[0]) + 1
    
    return "N/A"

def extract_toc_pypdf(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Alternative to extract_toc().
    Status: Not ready yet.
    Extract structural TOC (bookmarks/outline).
    """
    try:
        reader = PdfReader(pdf_path)
        toc = reader.outline  # List of Destination objects or nested lists
        toc_data = []
        
        def flatten_outline(outline_items, level=1):
            for item in outline_items:
                if isinstance(item, Destination):
                    page_num = resolve_destination(reader, item)
                    toc_data.append({
                        "level": level,
                        "title": item.title,
                        "target_page": page_num
                    })
                # Nested outlines
                if hasattr(item, "items") or isinstance(item, list):
                    sub_items = item.items if hasattr(item, "items") else item
                    flatten_outline(sub_items, level + 1)
        
        flatten_outline(toc)
        return toc_data
    except Exception as e:
        print(f"TOC error: {e}", file=sys.stderr)
        return []

def extract_links_pypdf(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Alternative to extract_links().
    Status: Not ready yet.
    Extract all link annotations with details.
    """
    links_data = []
    try:
        reader = PdfReader(pdf_path)
        
        for page_num, page in enumerate(reader.pages, start=1):
            if "/Annots" not in page:
                continue
            
            for annot_ref in page["/Annots"]:
                annot = annot_ref.get_object()
                if annot.get("/Subtype") != "/Link":
                    continue
                
                rect = annot.get("/Rect")  # [x0, y0, x1, y1]
                anchor_text = get_anchor_text_pypdf(page, rect)
                
                link_dict = {
                    "page": page_num,
                    "rect": rect,
                    "link_text": anchor_text,
                }
                
                # Action or Dest
                if "/A" in annot:
                    action = annot["/A"]
                    if "/URI" in action:
                        link_dict.update({
                            "type": "External (URI)",
                            "url": action["/URI"],
                            "target": action["/URI"]
                        })
                    elif "/S" in action and action["/S"] == "/GoToR":
                        link_dict.update({
                            "type": "Remote (GoToR)",
                            "remote_file": action.get("/F"),
                            "target": "Remote File"
                        })
                    else:
                        link_dict.update({
                            "type": "Other Action",
                            "target": str(action)
                        })
                elif "/Dest" in annot:
                    dest = annot["/Dest"]
                    target_page = resolve_destination(reader, dest)
                    link_dict.update({
                        "type": "Internal (GoTo/Dest)",
                        "destination_page": target_page,
                        "target": f"Page {target_page}"
                    })
                else:
                    link_dict.update({
                        "type": "Other Link",
                        "target": "Unknown"
                    })
                
                links_data.append(link_dict)
        
    except Exception as e:
        print(f"Links error: {e}", file=sys.stderr)
    
    return links_data

# Rest of your functions (print_structural_toc, get_first_pdf_in_cwd, run_analysis) remain almost identical
# Just replace calls to extract_toc/extract_links with the new versions above.

# Example adjustment in run_analysis:
# extracted_links = extract_links(pdf_path)
# structural_toc = extract_toc(pdf_path)

# The reporting logic can stay the same – it uses the same dict keys.



def call_stable():
    """
    Placeholder function for command-line execution (e.g., in __main__).
    Note: This requires defining PROJECT_NAME, CLI_MAIN_FILE, etc., or 
    passing them as arguments to run_analysis.
    """
    print("Begin analysis...")
    run_analysis()
    print("Analysis complete.")

if __name__ == "__main__":
    call_stable()
