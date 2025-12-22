# pdflinkcheck/report.py

import sys
from pathlib import Path
from typing import Optional, Dict, Any
import pyhabitat

from pdflinkcheck.io import error_logger, export_report_json, export_report_txt, get_first_pdf_in_cwd, get_friendly_path, LOG_FILE_PATH
from pdflinkcheck.environment import pymupdf_is_available

SEP_COUNT=28

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
        if print_bool: # this should not be here
            print(msg) # this should not be here. esure elsewhere then remove
        report_buffer.append(msg)

    # Expected: "pypdf" or "PyMuPDF"
    allowed_libraries = ("pypdf","pymupdf")
    pdf_library = pdf_library.lower()
    if pdf_library in allowed_libraries and pdf_library == "pypdf":
        from pdflinkcheck.analyze_pypdf import (extract_links_pypdf as extract_links, extract_toc_pypdf as extract_toc)
    elif pdf_library in allowed_libraries and pdf_library == "pymupdf":
        if not pymupdf_is_available():
            print("PyMuPDF was explicitly requested as the PDF Engine")
            print("Switch the PDF library to 'pypdf' instead, or install PyMuPDF. ")
            print("To install PyMuPDF locally, try: `uv sync --extra full` OR `pip install .[full]`")
            if pyhabitat.on_termux():
                print(f"pyhabitat.on_termux() = {pyhabitat.on_termux()}")
                print("PyMuPDF is not expected to work on Termux. Use pypdf.")
            print("\n")
            #return    
            raise ImportError(f"The 'fitz' module is required for this functionality. Original error: {e}") from e
        from pdflinkcheck.analyze_pymupdf import (extract_links_pymupdf as extract_links, extract_toc_pymupdf as extract_toc)
    
    log("\n--- Starting Analysis ... ---\n")
    if pdf_path is None:
        log("pdf_path is None")
        log("Tip: Drop a PDF in the current folder or pass in a path arg.")
        return {
            "data": {"external_links": [], "internal_links": [], "toc": []},
            "text": "\n".join(report_buffer),
            "metadata": {
                "pdf_name": "None",
                "library_used": pdf_library,
                "total_links": 0
            }
        }
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
            log("(This is common for scanned/image-only PDFs.)")

            empty_result = {
                "data": {
                    "external_links": [],
                    "internal_links": [],
                    "toc": []
                },
                "text": "\n".join(report_buffer),
                "metadata": {
                    "pdf_name": Path(pdf_path).name,
                    "library_used": pdf_library,
                    "total_links": 0
                }
            }
            return empty_result
            
        # 3. Separate the lists based on the 'type' key
        uri_links = [link for link in extracted_links if link['type'] == 'External (URI)']
        goto_links = [link for link in extracted_links if link['type'] == 'Internal (GoTo/Dest)']
        resolved_action_links = [link for link in extracted_links if link['type'] == 'Internal (Resolved Action)']
        other_links = [link for link in extracted_links if link['type'] not in ['External (URI)', 'Internal (GoTo/Dest)', 'Internal (Resolved Action)']]

        total_internal_links = len(goto_links) + len(resolved_action_links)
        limit = max_links if max_links > 0 else None
        uri_and_other = uri_links + other_links
        
        # --- ANALYSIS SUMMARY (Using your print logic) ---
        log("\n" + "=" * SEP_COUNT)
        log(f"--- Link Analysis Results for {Path(pdf_path).name} ---")
        log(f"Total active links: {len(extracted_links)} (External: {len(uri_links)}, Internal Jumps: {total_internal_links}, Other: {len(other_links)})")
        log(f"Total **structural TOC entries (bookmarks)** found: {toc_entry_count}")
        log("=" * SEP_COUNT)

        # --- Section 1: TOC ---
        str_structural_toc = print_structural_toc(structural_toc)
        log(str_structural_toc)

        # --- Section 2: ACTIVE INTERNAL JUMPS ---
        log("\n" + "=" * SEP_COUNT)
        log(f"## Active Internal Jumps (GoTo & Resolved Actions) - {total_internal_links} found")
        log("=" * SEP_COUNT)
        log("{:<5} | {:<5} | {:<40} | {}".format("Idx", "Page", "Anchor Text", "Jumps To Page"))
        log("-" * SEP_COUNT)
        
        all_internal = goto_links + resolved_action_links
        if total_internal_links > 0:
            for i, link in enumerate(all_internal[:limit], 1):
                link_text = link.get('link_text', 'N/A')
                log("{:<5} | {:<5} | {:<40} | {}".format(i, link['page'], link_text[:40], link['destination_page']))

            if limit is not None and len(all_internal) > limit:
                log(f"... and {len(all_internal) - limit} more links (use --max-links 0 to show all).")
        else:
            log(" No internal GoTo or Resolved Action links found.")
        log("-" * SEP_COUNT)
        
        # --- Section 3: ACTIVE URI LINKS ---
        log("\n" + "=" * SEP_COUNT)
        log(f"## Active URI Links (External & Other) - {len(uri_and_other)} found") 
        log("{:<5} | {:<5} | {:<40} | {}".format("Idx", "Page", "Anchor Text", "Target URI/Action"))
        log("=" * SEP_COUNT)
        
        if uri_and_other:
            for i, link in enumerate(uri_and_other[:limit], 1):
                target = link.get('url') or link.get('remote_file') or link.get('target')
                link_text = link.get('link_text', 'N/A')
                log("{:<5} | {:<5} | {:<40} | {}".format(i, link['page'], link_text[:40], target))
            if limit is not None and len(uri_and_other) > limit:
                log(f"... and {len(uri_and_other) - limit} more links (use --max-links 0 to show all).")

        else: 
            log(" No external or 'Other' links found.")
        log("-" * SEP_COUNT)

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
        
        report_results = {
            "data": final_report_data_dict, # The structured JSON-ready dict
            "text": report_buffer_str,      # The human-readable string
            "metadata": {                  # Helpful for the GUI/Logs
                "pdf_name": Path(pdf_path).name,
                "library_used": pdf_library,
                "total_links": len(extracted_links)
            }
        }
        # Return a clean results object
        return report_results
    except Exception as e:
        # Specific handling for common read failures
        if "invalid pdf header" in str(e).lower() or "EOF marker not found" in str(e) or "stream has ended unexpectedly" in str(e):
            log(f"\nWarning: Could not parse PDF structure — likely an image-only or malformed PDF.")
            log("No hyperlinks or TOC can exist in this file.")
            log("Result: No links found.")
            return {
                "data": {"external_links": [], "internal_links": [], "toc": []},
                "text": "\n".join(report_buffer + [
                    "\nWarning: PDF appears to be image-only or malformed.",
                    "No hyperlinks or structural TOC found."
                ]),
                "metadata": {
                    "pdf_name": Path(pdf_path).name,
                    "library_used": pdf_library,
                    "total_links": 0
                }
            }

    except Exception as e:
        # Log the critical failure
        error_logger.error(f"Critical failure during run_report for {pdf_path}: {e}", exc_info=True)
        log(f"FATAL: Analysis failed. Check logs at {LOG_FILE_PATH}", file=sys.stderr)
        raise # Allow the exception to propagate or handle gracefully

def print_structural_toc(structural_toc: list, print_bool: bool = False) -> str:
    """
    Formats the structural TOC data into a hierarchical string and optionally prints it.

    Args:
        structural_toc: A list of TOC dictionaries.
        print_bool: Whether to print the output to the console.

    Returns:
        A formatted string of the structural TOC.
    """
    lines = []
    lines.append("\n" + "=" * SEP_COUNT)
    lines.append("## Structural Table of Contents (PDF Bookmarks/Outline)")
    lines.append("=" * SEP_COUNT)

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

    lines.append("-" * SEP_COUNT)
    
    # Final aggregation
    str_structural_toc = "\n".join(lines)
    
    if print_bool:
        print(str_structural_toc)
        
    return str_structural_toc
