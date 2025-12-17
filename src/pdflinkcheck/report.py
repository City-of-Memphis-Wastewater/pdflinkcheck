# pdflinkcheck/report.py

import sys
from pathlib import Path
from typing import Optional, Dict, Any

from pdflinkcheck.io import error_logger, export_report_data, get_first_pdf_in_cwd, LOG_FILE_PATH


def run_report(pdf_path: str = None,  max_links: int = 0, export_format: Optional[str] = "JSON", library_pdf: Optional[str] = "pypdf") -> Dict[str, Any]:
    """
    Core high-level PDF link analysis logic. 
    
    This function orchestrates the extraction of active links and TOC 
    using pdflinkcheck analysis, and 
    prints a comprehensive, user-friendly report to the console.

    Args:
        pdf_path: The file system path (str) to the target PDF document.
        max_links: Maximum number of links to display in each console 
                   section. If <= 0, all links will be displayed.

    Returns:
        A dictionary containing the structured results of the analysis:
        'external_links', 'internal_links', and 'toc'.

    To Do:
        Aggregate print strings into a str for TXT export.
        Modularize.
    """

    # Expected: "pypdf" or "PyMuPDF"
    allowed_libraries = ("pypdf","pymupdf")
    library_pdf = library_pdf.lower()
    if library_pdf in allowed_libraries and library_pdf == "pypdf":
        from pdflinkcheck.analyze_pypdf import extract_links_pypdf as extract_links
        from pdflinkcheck.analyze_pypdf import extract_toc_pypdf as extract_toc
    elif library_pdf in allowed_libraries and library_pdf == "pymupdf":
        from pdflinkcheck.analyze import extract_links_pymupdf as extract_links
        from pdflinkcheck.analyze import extract_toc_pymupdf as extract_toc
    

    if pdf_path is None:
        pdf_path = get_first_pdf_in_cwd()
    if pdf_path is None:
        print("pdf_path is None")
        print("Tip: Drop a PDF in the current folder or pass in a path arg.")
        return
    try:
        print(f"Running pdflinkcheck analysis on {Path(pdf_path).name}...")

        # 1. Extract all active links and TOC
        extracted_links = extract_links(pdf_path)
        structural_toc = extract_toc(pdf_path) 
        #structural_toc = extract_toc_pypdf(pdf_path) 
        toc_entry_count = len(structural_toc)
        

        if not extracted_links and not structural_toc:
            print(f"\nNo hyperlinks or structural TOC found in {Path(pdf_path).name}.")
            return {}
            
        # 3. Separate the lists based on the 'type' key
        uri_links = [link for link in extracted_links if link['type'] == 'External (URI)']
        goto_links = [link for link in extracted_links if link['type'] == 'Internal (GoTo/Dest)']
        resolved_action_links = [link for link in extracted_links if link['type'] == 'Internal (Resolved Action)']
        other_links = [link for link in extracted_links if link['type'] not in ['External (URI)', 'Internal (GoTo/Dest)', 'Internal (Resolved Action)']]

        total_internal_links = len(goto_links) + len(resolved_action_links)
        limit = max_links if max_links > 0 else None
        uri_and_other = uri_links + other_links
        
        # --- ANALYSIS SUMMARY (Using your print logic) ---
        print("\n" + "=" * 70)
        print(f"--- Link Analysis Results for {Path(pdf_path).name} ---")
        print(f"Total active links: {len(extracted_links)} (External: {len(uri_links)}, Internal Jumps: {total_internal_links}, Other: {len(other_links)})")
        print(f"Total **structural TOC entries (bookmarks)** found: {toc_entry_count}")
        print("=" * 70)

        # --- Section 1: TOC ---
        print_structural_toc(structural_toc)

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
        
        # --- Section 3: ACTIVE URI LINKS ---
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

        
        # Return the collected data for potential future JSON/other output
        final_report_data =  {
            "external_links": uri_links,
            "internal_links": all_internal,
            "toc": structural_toc
        }

        # 5. Export Report 
        if export_format:
            # Assuming export_to will hold the output format string (e.g., "JSON")
            export_report_data(final_report_data, Path(pdf_path).name, export_format)

        return final_report_data
    except Exception as e:
        # Log the critical failure
        error_logger.error(f"Critical failure during run_report for {pdf_path}: {e}", exc_info=True)
        print(f"FATAL: Analysis failed. Check logs at {LOG_FILE_PATH}", file=sys.stderr)
        raise # Allow the exception to propagate or handle gracefully


def print_structural_toc(structural_toc):
    """
    Prints the structural TOC data (bookmarks/outline) in a clean, 
    hierarchical, and readable console format.

    Args:
        structural_toc: A list of TOC dictionaries.
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