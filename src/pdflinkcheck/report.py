# pdflinkcheck/report.py

import sys
from pathlib import Path
from typing import Optional, Dict, Any

from pdflinkcheck.io import error_logger, export_report_json, export_report_txt, get_first_pdf_in_cwd, get_friendly_path, LOG_FILE_PATH


def run_report(pdf_path: str = None,  max_links: int = 0, export_format: str = "JSON", pdf_library: str = "pypdf", print_bool:bool=True) -> Dict[str, Any]:
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

    report_buffer = []

    # Helper to handle conditional printing and mandatory buffering
    def log(msg: str):
        if print_bool:
            print(msg)
        report_buffer.append(msg)

    # Expected: "pypdf" or "PyMuPDF"
    allowed_libraries = ("pypdf","pymupdf")
    pdf_library = pdf_library.lower()
    if pdf_library in allowed_libraries and pdf_library == "pypdf":
        from pdflinkcheck.analyze_pypdf import (extract_links_pypdf as extract_links, extract_toc_pypdf as extract_toc)
    elif pdf_library in allowed_libraries and pdf_library == "pymupdf":
        try:
            import fitz
        except ImportError:
            print("The PyMuPDF / fitz library is not available. Install pymupdf, or select pypdf as the PDF library. See README for details.")
            return    
        from pdflinkcheck.analyze_pymupdf import (extract_links_pymupdf as extract_links, extract_toc_pymupdf as extract_toc)
    
    log("\n--- Starting Analysis ... ---\n")
    if pdf_path is None:
        pdf_path = get_first_pdf_in_cwd()
    if pdf_path is None:
        log("pdf_path is None")
        log("Tip: Drop a PDF in the current folder or pass in a path arg.")
        return
    try:
        log(f"Target file: {get_friendly_path(pdf_path)}")
        log(f"PDF Engine: {pdf_library}")

        # 1. Extract all active links and TOC
        extracted_links = extract_links(pdf_path)
        structural_toc = extract_toc(pdf_path) 
        #structural_toc = extract_toc_pypdf(pdf_path) 
        toc_entry_count = len(structural_toc)
        

        if not extracted_links and not structural_toc:
            log(f"\nNo hyperlinks or structural TOC found in {Path(pdf_path).name}.")
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
        log("\n" + "=" * 70)
        log(f"--- Link Analysis Results for {Path(pdf_path).name} ---")
        log(f"Total active links: {len(extracted_links)} (External: {len(uri_links)}, Internal Jumps: {total_internal_links}, Other: {len(other_links)})")
        log(f"Total **structural TOC entries (bookmarks)** found: {toc_entry_count}")
        log("=" * 70)

        # --- Section 1: TOC ---
        print_structural_toc(structural_toc)

        # --- Section 2: ACTIVE INTERNAL JUMPS ---
        log("\n" + "=" * 70)
        log(f"## Active Internal Jumps (GoTo & Resolved Actions) - {total_internal_links} found")
        log("=" * 70)
        log("{:<5} | {:<5} | {:<40} | {}".format("Idx", "Page", "Anchor Text", "Jumps To Page"))
        log("-" * 70)
        
        all_internal = goto_links + resolved_action_links
        if total_internal_links > 0:
            for i, link in enumerate(all_internal[:limit], 1):
                link_text = link.get('link_text', 'N/A')
                log("{:<5} | {:<5} | {:<40} | {}".format(i, link['page'], link_text[:40], link['destination_page']))

            if limit is not None and len(all_internal) > limit:
                log(f"... and {len(all_internal) - limit} more links (use --max-links 0 to show all).")
        else:
            log(" No internal GoTo or Resolved Action links found.")
        
        # --- Section 3: ACTIVE URI LINKS ---
        log("\n" + "=" * 70)
        log(f"## Active URI Links (External & Other) - {len(uri_and_other)} found") 
        log("{:<5} | {:<5} | {:<40} | {}".format("Idx", "Page", "Anchor Text", "Target URI/Action"))
        log("=" * 70)
        
        if uri_and_other:
            for i, link in enumerate(uri_and_other[:limit], 1):
                target = link.get('url') or link.get('remote_file') or link.get('target')
                link_text = link.get('link_text', 'N/A')
                log("{:<5} | {:<5} | {:<40} | {}".format(i, link['page'], link_text[:40], target))
            if limit is not None and len(uri_and_other) > limit:
                log(f"... and {len(uri_and_other) - limit} more links (use --max-links 0 to show all).")

        else: 
            log(" No external or 'Other' links found.")

        log("\n--- Analysis Complete ---\n")

        # Final aggregation of the buffer into one string
        report_buffer_str = "\n".join(report_buffer)
        
        # Return the collected data for potential future JSON/other output
        final_report_data_dict =  {
            "external_links": uri_links,
            "internal_links": all_internal,
            "toc": structural_toc
        }

        # 5. Export Report 
        #if export_format:
        #    # Assuming export_to will hold the output format string (e.g., "JSON")
        #    export_report_data(final_report_data_dict, Path(pdf_path).name, export_format, pdf_library)
        
        if export_format:
            fmt_upper = export_format.upper()
            
            if "JSON" in fmt_upper:
                export_report_json(final_report_data_dict, pdf_path, pdf_library)
            
            if "TXT" in fmt_upper:
                export_report_txt(report_buffer_str, pdf_path, pdf_library)
                
        # Return a clean results object
        return {
            "data": final_report_data_dict, # The structured JSON-ready dict
            "text": report_buffer_str,      # The human-readable string
            "metadata": {                  # Helpful for the GUI/Logs
                "pdf_name": Path(pdf_path).name,
                "library_used": pdf_library,
                "total_links": len(extracted_links)
            }
        }

    except Exception as e:
        # Log the critical failure
        error_logger.error(f"Critical failure during run_report for {pdf_path}: {e}", exc_info=True)
        log(f"FATAL: Analysis failed. Check logs at {LOG_FILE_PATH}", file=sys.stderr)
        raise # Allow the exception to propagate or handle gracefully


def print_structural_toc_print(structural_toc:dict, print_bool:bool=True)->str|None:
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


def print_structural_toc(structural_toc: list, print_bool: bool = True) -> str:
    """
    Formats the structural TOC data into a hierarchical string and optionally prints it.

    Args:
        structural_toc: A list of TOC dictionaries.
        print_bool: Whether to print the output to the console.

    Returns:
        A formatted string of the structural TOC.
    """
    lines = []
    lines.append("\n" + "=" * 70)
    lines.append("## Structural Table of Contents (PDF Bookmarks/Outline)")
    lines.append("=" * 70)

    if not structural_toc:
        msg = "No structural TOC (bookmarks/outline) found."
        lines.append(msg)
        output = "\n".join(lines)
        if print_bool:
            print(output)
        return output

    # Determine max page width for consistent alignment
    valid_pages = [item['target_page'] for item in structural_toc if isinstance(item['target_page'], int)]
    max_page = max(valid_pages) if valid_pages else 1
    page_width = len(str(max_page))
    
    # Iterate and format
    for item in structural_toc:
        indent = " " * 4 * (item['level'] - 1)
        # Handle cases where page might be N/A or None
        target_page = item.get('target_page', "N/A")
        page_str = str(target_page).rjust(page_width)
        
        lines.append(f"{indent}{item['title']} . . . page {page_str}")

    lines.append("-" * 70)
    
    # Final aggregation
    str_structural_toc = "\n".join(lines)
    
    if print_bool:
        print(str_structural_toc)
        
    return str_structural_toc


def run_validation(pdf_path: str = None, pdf_library: str = "pypdf", check_external_links:bool = False) -> Dict[str, Any]:
    """
    Experimental. Ignore for now.

    Extends the report logic by programmatically testing every extracted link.
    Validates Internal Jumps (page bounds), External URIs (HTTP status), 
    and Launch actions (file existence).
    """
    if check_external_links:
        import requests

    # 1. Setup Library Engine (Reuse your logic)
    pdf_library = pdf_library.lower()
    if pdf_library == "pypdf":
        from pdflinkcheck.analyze_pypdf import extract_links_pypdf as extract_links
    else:
        from pdflinkcheck.analyze_pymupdf import extract_links_pymupdf as extract_links

    if pdf_path is None:
        pdf_path = get_first_pdf_in_cwd()
    
    if not pdf_path:
        print("Error: No PDF found for validation.")
        return {}

    print(f"\nValidating links in {Path(pdf_path).name}...")

    # 2. Extract links and initialize validation counters
    links = extract_links(pdf_path)
    total_links = len(links)
    results = {"valid": [], "broken": [], "error": []}

    # 3. Validation Loop
    for i, link in enumerate(links, 1):
        # Progress indicator for long manuals
        sys.stdout.write(f"\rChecking link {i}/{total_links}...")
        sys.stdout.flush()

        link_type = link.get('type')
        status = {"is_valid": False, "reason": "Unknown Type"}

        # --- A. Validate Internal Jumps ---
        if "Internal" in link_type:
            target_page = link.get('destination_page')
            if isinstance(target_page, int) and target_page > 0:
                # In a real run, you'd compare against reader.pages_count
                status = {"is_valid": True, "reason": "Resolves"}
            else:
                status = {"is_valid": False, "reason": f"Invalid Page: {target_page}"}

        # --- B. Validate Web URIs ---
        elif link_type == 'External (URI)':

            url = link.get('url')
            if url and url.startswith("http") and check_external_links:
                try:
                    # Use a short timeout and HEAD request to be polite/fast
                    resp = requests.head(url, timeout=5, allow_redirects=True)
                    if resp.status_code < 400:
                        status = {"is_valid": True, "reason": f"HTTP {resp.status_code}"}
                    else:
                        status = {"is_valid": False, "reason": f"HTTP {resp.status_code}"}
                except Exception as e:
                    status = {"is_valid": False, "reason": "Connection Failed"}
            else:
                status = {"is_valid": False, "reason": "Malformed URL"}

        # --- C. Validate Local File/Launch Links ---
        elif link_type == 'Launch' or 'remote_file' in link:
            file_path = link.get('remote_file') or link.get('url')
            if file_path:
                # Clean URI formatting
                clean_path = file_path.replace("file://", "").replace("%20", " ")
                # Check relative to the PDF's location
                abs_path = Path(pdf_path).parent / clean_path
                if abs_path.exists():
                    status = {"is_valid": True, "reason": "File Exists"}
                else:
                    status = {"is_valid": False, "reason": "File Missing"}

        # Append result
        link['validation'] = status
        if status['is_valid']:
            results['valid'].append(link)
        else:
            results['broken'].append(link)

    print("\n" + "=" * 70)
    print(f"--- Validation Summary for {Path(pdf_path).name} ---")
    print(f"Total Checked: {total_links}")
    print(f"✅ Valid:  {len(results['valid'])}")
    print(f"❌ Broken: {len(results['broken'])}")
    print("=" * 70)

    # 4. Print Detail Report for Broken Links
    if results['broken']:
        print("\n## ❌ Broken Links Found:")
        print("{:<5} | {:<5} | {:<30} | {}".format("Idx", "Page", "Reason", "Target"))
        print("-" * 70)
        for i, link in enumerate(results['broken'], 1):
            target = link.get('url') or link.get('destination_page') or link.get('remote_file')
            print("{:<5} | {:<5} | {:<30} | {}".format(
                i, link['page'], link['validation']['reason'], str(target)[:30]
            ))
    
    return results