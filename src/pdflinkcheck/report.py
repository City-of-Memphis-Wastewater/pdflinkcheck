#!/usr/bin/env python3 
# SPDX-License-Identifier: MIT
# pdflinkcheck/report.py

import sys
from pathlib import Path
from typing import Optional, Dict, Any
import pyhabitat

from pdflinkcheck.io import error_logger, export_report_json, export_report_txt, get_first_pdf_in_cwd, get_friendly_path, LOG_FILE_PATH
from pdflinkcheck.environment import pymupdf_is_available
from pdflinkcheck.validate import run_validation
from pdflinkcheck.security import compute_risk
from pdflinkcheck.helpers import debug_head, PageRef


SEP_COUNT=28
# Define a safe "empty" validation state
EMPTY_VALIDATION = {
        "summary-stats": {
            "total_checked": 0,
            "valid": 0,
            "file-found": 0,
            "broken-page": 0,
            "broken-file": 0,
            "no_destination_page_count": 0,
            "unknown-web": 0,
            "unknown-reasonableness": 0,
            "unknown-link": 0 
        },
        "issues": [],
        "summary-txt": "Analysis failed: No validation performed.",
        "total_pages": 0
    }


def run_report_and_call_exports(pdf_path: str = None, export_format: str = "JSON", pdf_library: str = "pypdf", print_bool:bool=True) -> Dict[str, Any]:
    # The meat and potatoes
    report_results = run_report(
        pdf_path=str(pdf_path), 
        pdf_library = pdf_library,
        print_bool=print_bool,
    )
    # 2. Initialize file path tracking
    output_path_json = None
    output_path_txt = None
    
    if export_format:
        report_data_dict = report_results["data"]
        report_buffer_str = report_results["text"]
        
        if "JSON" in export_format.upper():
            output_path_json = export_report_json(report_data_dict, pdf_path, pdf_library)
        
        if "TXT" in export_format.upper():
            output_path_txt = export_report_txt(report_buffer_str, pdf_path, pdf_library)

    # 4. Inject the file info into the results dictionary
    report_results["files"] = {
        "export_path_json": output_path_json, 
        "export_path_txt": output_path_txt
    }
    return report_results
    

def run_report(pdf_path: str = None, pdf_library: str = "pypdf", print_bool:bool=True) -> Dict[str, Any]:
    """
    Core high-level PDF link analysis logic. 
    
    This function orchestrates the extraction of active links and TOC 
    using pdflinkcheck analysis, and 
    prints a comprehensive, user-friendly report to the console.

    Args:
        pdf_path: The file system path (str) to the target PDF document.

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
        report_buffer.append(msg)

    # Expected: "pypdf" or "PyMuPDF" pr "rust"
    allowed_libraries = ("pypdf", "pymupdf", "rust", "auto")
    pdf_library = pdf_library.lower()

    # AUTO MODE
    if pdf_library == "auto":
        from pdflinkcheck.ffi import rust_available
        if rust_available():
            pdf_library = "rust"
        elif pymupdf_is_available():
            pdf_library = "pymupdf"
        else:
            pdf_library = "pypdf"

    # RUST ENGINE
    if pdf_library == "rust":
        from pdflinkcheck.ffi import rust_available, analyze_pdf_rust
        # overkill, encourages redundancy: from pdflinkcheck.ffi import (rust_available, extract_links_pypdf as extract_links, extract_toc_pypdf as extract_toc)

        if not rust_available():
            raise ImportError("Rust engine requested but Rust library not available.")
        
        # Rust returns a dict: {"links": [...], "toc": [...]}
        rust_data = analyze_pdf_rust(pdf_path)
        # Normalize Rust types to match Python expectations
        for link in rust_data.get("links", []):
            if link.get("action_kind") == "GoTo":
                link['type'] = 'Internal (GoTo/Dest)'
            elif link.get("action_kind") == "URI":
                link['type'] = 'External (URI)'
        
        extracted_links = rust_data.get("links", [])
        structural_toc = rust_data.get("toc", [])
        
    # pypdf ENGINE
    elif pdf_library in allowed_libraries and pdf_library == "pypdf":
        from pdflinkcheck.analysis_pypdf import (extract_links_pypdf as extract_links, extract_toc_pypdf as extract_toc)

    # PyMuPDF Engine
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
            raise ImportError("The 'fitz' module (PyMuPDF) is required but not installed.")
        from pdflinkcheck.analysis_pymupdf import (extract_links_pymupdf as extract_links, extract_toc_pymupdf as extract_toc)
    
    log("\n--- Starting Analysis ... ---\n")
    if pdf_path is None:
        log("pdf_path is None")
        log("Tip: Drop a PDF in the current folder or pass in a path arg.")
        empty_report = {
                "data": {
                    "external_links": [],
                    "internal_links": [],
                    "toc": []
                },
                "text": "\n".join(report_buffer),
                "metadata": {
                    "pdf_name": Path(pdf_path).name,
                    "library_used": pdf_library,
                    "link_counts": {
                        "toc_entry_count": 0,
                        "interal_goto_links_count": 0,
                        "interal_resolve_action_links_count": 0,
                        "total_internal_links_count": 0,
                        "external_uri_links_count": 0,
                        "other_links_count": 0,
                        "total_links_count": 0
                    }
                }
            }

        return empty_report
        
    if True: #try:
        log(f"Target file: {get_friendly_path(pdf_path)}")
        log(f"PDF Engine: {pdf_library}")

        # 1. Extract all active links and TOC
        if pdf_library != "rust": 
            extracted_links = extract_links(pdf_path)
            structural_toc = extract_toc(pdf_path) 

        toc_entry_count = len(structural_toc)
        str_structural_toc = get_structural_toc(structural_toc)
        
        # check the structure, that it matches
        if False:
            print(f"pdf_library={pdf_library}")
            debug_head("TOC", structural_toc, n=1)
            debug_head("Links", list(extracted_links), n=1)
        
        # THIS HITS

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
                    "link_counts": {
                        "toc_entry_count": 0,
                        "interal_goto_links_count": 0,
                        "interal_resolve_action_links_count": 0,
                        "total_internal_links_count": 0,
                        "external_uri_links_count": 0,
                        "other_links_count": 0,
                        "total_links_count": 0
                    }
                }
            }
            return empty_result
            
        # 3. Separate the lists based on the 'type' key
        external_uri_links = [link for link in extracted_links if link['type'] == 'External (URI)']
        goto_links = [link for link in extracted_links if link['type'] == 'Internal (GoTo/Dest)']
        resolved_action_links = [link for link in extracted_links if link['type'] == 'Internal (Resolved Action)']
        other_links = [link for link in extracted_links if link['type'] not in ['External (URI)', 'Internal (GoTo/Dest)', 'Internal (Resolved Action)']]

        interal_resolve_action_links_count = len(resolved_action_links)
        interal_goto_links_count = len(goto_links) 
        total_internal_links_count = interal_goto_links_count + interal_resolve_action_links_count

        external_uri_links_count = len(external_uri_links)
        other_links_count = len(other_links)

        total_links_count = len(extracted_links)

        # --- ANALYSIS SUMMARY (Using your print logic) ---
        log("\n" + "=" * SEP_COUNT)
        log(f"--- Link Analysis Results for {Path(pdf_path).name} ---")
        log(f"Total active links: {total_links_count} (External: {external_uri_links_count}, Internal Jumps: {total_internal_links_count}, Other: {other_links_count})")
        log(f"Total **structural TOC entries (bookmarks)** found: {toc_entry_count}")
        log("=" * SEP_COUNT)

        # --- Section 1: TOC ---
        log(str_structural_toc)

        # --- Section 2: ACTIVE INTERNAL JUMPS ---
        log("\n" + "=" * SEP_COUNT)
        log(f"## Active Internal Jumps (GoTo & Resolved Actions) - {total_internal_links_count} found")
        log("=" * SEP_COUNT)
        log("{:<5} | {:<5} | {:<40} | {}".format("Idx", "Page", "Anchor Text", "Jumps To Page"))
        log("-" * SEP_COUNT)
        
        all_internal = goto_links + resolved_action_links
        #If links were found: all_internal is a list with dictionaries. It evaluates to True.
        # If NO links were found: all_internal is an empty list []. It evaluates to False.
        if all_internal:
            for i, link in enumerate(all_internal, 1):
                link_text = link.get('link_text', 'N/A')

                # Convert source and destination indices to human strings
                src_page = PageRef.from_index(link['page']).human
                dest_page = PageRef.from_index(link['destination_page']).human

                log("{:<5} | {:<5} | {:<40} | {}".format(
                    i, 
                    src_page, 
                    link_text[:40], 
                    dest_page
                ))


        else:
            log(" No internal GoTo or Resolved Action links found.")
        log("-" * SEP_COUNT)
        
        # --- Section 3: ACTIVE URI LINKS ---
        log("\n" + "=" * SEP_COUNT)
        log(f"## Active URI Links (External) - {len(external_uri_links)} found") 
        log("{:<5} | {:<5} | {:<40} | {}".format("Idx", "Page", "Anchor Text", "Target URI/Action"))
        log("=" * SEP_COUNT)
        
        if external_uri_links:
            for i, link in enumerate(external_uri_links, 1):
                target = link.get('url') or link.get('remote_file') or link.get('target')
                link_text = link.get('link_text', 'N/A')
                log("{:<5} | {:<5} | {:<40} | {}".format(i, link['page'], link_text[:40], target))

        else: 
            log(" No external links found.")
        log("-" * SEP_COUNT)

        # --- Section 4: OTHER LINKS ---
        log("\n" + "=" * SEP_COUNT)
        log(f"## Other Links  - {len(other_links)} found") 
        log("{:<5} | {:<5} | {:<40} | {}".format("Idx", "Page", "Anchor Text", "Target Action"))
        log("=" * SEP_COUNT)
        
        if other_links:
            for i, link in enumerate(other_links, 1):
                target = link.get('url') or link.get('remote_file') or link.get('target')
                link_text = link.get('link_text', 'N/A')
                log("{:<5} | {:<5} | {:<40} | {}".format(i, link['page'], link_text[:40], target))

        else: 
            log(" No 'Other' links found.")
        log("-" * SEP_COUNT)
        
        # Return the collected data for potential future JSON/other output
        report_data_dict =  {
            "external_links": external_uri_links,
            "internal_links": all_internal,
            "toc": structural_toc,
            "validation": EMPTY_VALIDATION
        }

        intermediate_report_results = {
            "data": report_data_dict, # The structured JSON-ready dict
            "text": "",
            "metadata": {                  # Helpful for the GUI/Logs
                "pdf_name": Path(pdf_path).name,
                "library_used": pdf_library,
                "link_counts": {
                    "toc_entry_count": toc_entry_count,
                    "interal_goto_links_count": interal_goto_links_count,
                    "interal_resolve_action_links_count": interal_resolve_action_links_count,
                    "total_internal_links_count": total_internal_links_count,
                    "external_uri_links_count": external_uri_links_count,
                    "other_links_count": other_links_count,
                    "total_links_count": total_links_count
                }
            }
        }

        log("\n--- Analysis Complete ---")

        validation_results = run_validation(report_results=intermediate_report_results,
                                            pdf_path=pdf_path,
                                            pdf_library=pdf_library)
        log(validation_results.get("summary-txt",""))

        # CRITICAL: Re-assign to report_results so it's available for the final return
        report_results = intermediate_report_results

        # --- Offline Risk Analysis (Security Layer) ---
        risk_results = compute_risk(report_results)
        report_results["data"]["risk"] = risk_results
        
        # Final aggregation of the buffer into one string, after the last call to log()
        report_buffer_str = "\n".join(report_buffer)

        report_results["data"]["validation"].update(validation_results)
        #report_results["text"].update(report_buffer_str)      # The human-readable string
        report_results["text"] = report_buffer_str

        # 5. Export Report 
        #if export_format:
        #    # Assuming export_to will hold the output format string (e.g., "JSON")
        #    export_report_data(report_data_dict, Path(pdf_path).name, export_format, pdf_library)
        
        if print_bool:
            print(report_buffer_str)
            
        return report_results
        """except Exception as e:
        error_logger.error(f"Critical failure during run_report for {pdf_path}: {e}", exc_info=True)
        # Ensure we always return a valid structure even in total failure
        return {
            "data": {"external_links": [], "internal_links": [], "toc": [], "validation": EMPTY_VALIDATION},
            "text": f"FATAL Error: {str(e)}",
            "metadata": {"pdf_name": Path(pdf_path).name, "library_used": pdf_library}
        }"""
    if False:#except Exception as e:
        # Specific handling for common read failures
        if True:#"invalid pdf header" in str(e).lower() or "EOF marker not found" in str(e) or "stream has ended unexpectedly" in str(e):
            log(f"\nWarning: Could not parse PDF structure — likely an image-only or malformed PDF.")
            log("No hyperlinks or TOC can exist in this file.")
            log("Result: No links found.")
            return {
                "data": {"external_links": [], "internal_links": [], "toc": [], "validation": EMPTY_VALIDATION},
                "text": "\n".join(report_buffer + [
                    "\nWarning: PDF appears to be image-only or malformed.",
                    "No hyperlinks or structural TOC found."
                ]),
                "metadata": {
                    "pdf_name": Path(pdf_path).name,
                    "library_used": pdf_library,
                    "link_counts": {
                        "toc_entry_count": 0,
                        "interal_goto_links_count": 0,
                        "interal_resolve_action_links_count": 0,
                        "total_internal_links_count": 0,
                        "external_uri_links_count": 0,
                        "other_links_count": 0,
                        "total_links_count": 0
                    }
                }
            }

    #except Exception as e:
    #    # Log the critical failure
    #    error_logger.error(f"Critical failure during run_report for {pdf_path}: {e}", exc_info=True)
    #    log(f"FATAL: Analysis failed. Check logs at {LOG_FILE_PATH}", file=sys.stderr)
    #    raise # Allow the exception to propagate or handle gracefully
    if False:#except Exception as e:
        error_logger.error(f"Critical failure during run_report for {pdf_path}: {e}", exc_info=True)
        log(f"FATAL: Analysis failed: {str(e)}. Check logs at {LOG_FILE_PATH}", file=sys.stderr)

        # Always return a safe empty result on error
        return {
            "data": {
                "external_links": [],
                "internal_links": [],
                "toc": [],
                "validation": EMPTY_VALIDATION
            },
            "text": "\n".join(report_buffer + [
                "\n--- Analysis failed ---",
                f"Error: {str(e)}",
                "No links or TOC extracted."
            ]),
            "metadata": {
                "pdf_name": Path(pdf_path).name,
                "library_used": pdf_library,
                "link_counts": {
                        "toc_entry_count": 0,
                        "interal_goto_links_count": 0,
                        "interal_resolve_action_links_count": 0,
                        "total_internal_links_count": 0,
                        "external_uri_links_count": 0,
                        "other_links_count": 0,
                        "total_links_count": 0
                    }
            }
        }
        
def get_structural_toc(structural_toc: list) -> str:
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
        
        # Determine the human-facing string
        if isinstance(target_page, int):
            # Convert 0-index back to human (1-index) for the report
            display_val = PageRef.from_index(target_page).human
        else:
            display_val = str(target_page)

        page_str = str(display_val).rjust(page_width)

        lines.append(f"{indent}{item['title']} . . . page {page_str}")

    lines.append("-" * SEP_COUNT)
    
    # Final aggregation
    str_structural_toc = "\n".join(lines)
        
    return str_structural_toc

if __name__ == "__main__":

    from pdflinkcheck.io import get_first_pdf_in_cwd
    pdf_path = get_first_pdf_in_cwd()
    # Run analysis first

    if pymupdf_is_available():
        pdf_library = "pymupdf"
    else:
        pdf_library = "pypdf"
    report = run_report_and_call_exports(
        pdf_path=pdf_path,
        export_format="",
        pdf_library=pdf_library,
        print_bool=True  # We handle printing in validation
    )

    if not report or not report.get("data"):
        print("No data extracted — nothing to validate.")
        sys.exit(1)

    else:
        print("Success!")
        print(f"list(report['data']) = {list(report['data'])}")

