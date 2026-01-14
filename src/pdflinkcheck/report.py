#!/usr/bin/env python3 
# SPDX-License-Identifier: MIT
# pdflinkcheck/report.py
from __future__ import annotations
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import pyhabitat
import copy

from pdflinkcheck.io import error_logger, export_report_json, export_report_txt, get_first_pdf_in_cwd, get_friendly_path, LOG_FILE_PATH
from pdflinkcheck.environment import pymupdf_is_available, pdfium_is_available
from pdflinkcheck.validate import run_validation
from pdflinkcheck.security import compute_risk
from pdflinkcheck.helpers import debug_head, PageRef
from pdflinkcheck.spreadsheet import export_report_links_to_xlsx

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
        #"summary-txt": "Analysis failed: No validation performed.",
        "summary-lines": ["Analysis failed: No validation performed."],
        "total_pages": 0
    }


def run_report_and_call_exports(
    pdf_path: str = None, 
    export_format: str = "JSON", 
    pdf_library: str = "auto", 
    print_bool: bool=True,
    concise_print: bool = False
) -> Dict[str, Any]:
    """
    Public entry point. Orchestrates extraction, validation, and file exports.
    """
    #  The meat and potatoes
    report_results = run_report_meat(
        pdf_path=str(pdf_path), 
        pdf_library = pdf_library,
        print_bool = print_bool,
        concise_print = concise_print,
    )
    # 2. Initialize file path tracking
    output_path_json = None
    output_path_txt = None
    output_path_xlsx = None
    
    if export_format:
        report_data_dict = report_results["data"]
        report_buffer_str = report_results["text-lines"]
        if "JSON" in export_format.upper():
            output_path_json = export_report_json(report_data_dict, pdf_path, pdf_library)
        if "TXT" in export_format.upper():
            output_path_txt = export_report_txt(report_buffer_str, pdf_path, pdf_library)
        if "XLSX" in export_format.upper():
            output_path_xlsx = export_report_links_to_xlsx(report_results)

    # 4. Inject the file info into the results dictionary
    report_results["files"] = {
        "export_path_json": output_path_json, 
        "export_path_txt": output_path_txt,
        "export_path_xlsx": output_path_xlsx
    }
    
    return report_results

# -----  Stable version: See "report copy.py" for refactor (failing) ----
def run_report_meat(
        pdf_path: str = None, 
        pdf_library: str = "auto", 
        print_bool: bool=True,
        concise_print: bool=False
        ) -> Dict[str, Any]:
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
    report_buffer_overview = []

    # Helper to handle conditional printing and mandatory buffering
    def log(msg: str, overview: bool = False):
        report_buffer.append(msg)
        if overview:
            report_buffer_overview.append(msg)
    
    allowed_libraries = ("pypdf", "pymupdf", "pdfium", "auto")
    pdf_library = pdf_library.lower()

    log("\n")
    log("--- Starting Analysis ... ---")
    log("\n")
    if pdf_path is None:
        log("pdf_path is None", overview=True)
        log("Tip: Drop a PDF in the current folder or pass in a path arg.")
        _return_empty_report(report_buffer)
    else:
        pdf_name = Path(pdf_path).name
    resolved_path = str(Path(pdf_path).resolve())
        
    # AUTO MODE
    if pdf_library == "auto":
        if pdfium_is_available():
            pdf_library = "pdfium"
        elif pymupdf_is_available():
            pdf_library = "pymupdf"
        else:
            pdf_library = "pypdf"



    # PDFium ENGINE
    if pdf_library in allowed_libraries and pdf_library == "pdfium":
        from pdflinkcheck.analysis_pdfium import analyze_pdf as analyze_pdf_pdfium
        data = analyze_pdf_pdfium(pdf_path) or {"links": [], "toc": [], "file_ov": []}
        extracted_links = data.get("links", [])
        structural_toc = data.get("toc", [])
        file_ov = data.get("file_ov", [])
        
    # pypdf ENGINE
    elif pdf_library in allowed_libraries and pdf_library == "pypdf":
        from pdflinkcheck.analysis_pdfium import analyze_pdf as analyze_pdf_pypdf
        #extracted_links = extract_links(pdf_path)
        #structural_toc = extract_toc(pdf_path) 
        data = analyze_pdf_pypdf(pdf_path) or {"links": [], "toc": [], "file_ov": []}
        extracted_links = data.get("links", [])
        structural_toc = data.get("toc", [])
        file_ov = data.get("file_ov", [])

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

        from pdflinkcheck.analysis_pdfium import analyze_pdf as analyze_pdf_pymupdf
        data = analyze_pdf_pymupdf(pdf_path) or {"links": [], "toc": [], "file_ov": []}
        extracted_links = data.get("links", [])
        structural_toc = data.get("toc", [])
        file_ov = data.get("file_ov", [])
    
    total_pages = file_ov.get("total_pages",0)
    

        
    try:
        log(f"Target file: {get_friendly_path(pdf_path)}", overview=True)
        log(f"PDF Engine: {pdf_library}", overview=True)

        toc_entry_count = len(structural_toc)
        str_structural_toc = get_structural_toc(structural_toc)
        
        if not extracted_links and not structural_toc:
            log("\n")
            log(f"No hyperlinks or structural TOC found in {pdf_name}.", overview=True)
            log("(This is common for scanned/image-only PDFs.)", overview=True)
            
            empty_result = {
                "data": {
                    "external_links": [],
                    "internal_links": [],
                    "toc": [],
                    "validation": EMPTY_VALIDATION.copy()
                },
                "text-lines": report_buffer,
                "metadata": {
                    "file_overview": {
                        "pdf_name": pdf_name,
                        "total_pages": total_pages,
                        "source_path": resolved_path,        # user-facing, stable
                        "processing_path": resolved_path,    # internal only
                    },
                    "library_used": pdf_library,
                    "link_counts": {
                        "toc_entry_count": 0,
                        "internal_goto_links_count": 0,
                        "interal_resolve_action_links_count": 0,
                        "total_internal_links_count": 0,
                        "external_uri_links_count": 0,
                        "other_links_count": 0,
                        "total_links_count": 0
                    }
                }
            }
            _print_report_algorithm(report_buffer,report_buffer_overview, print_bool, concise_print)
            return empty_result
            
        # 3. Separate the lists based on the 'type' key
        external_uri_links = [link for link in extracted_links if link['type'] == 'External (URI)']
        goto_links = [link for link in extracted_links if link['type'] == 'Internal (GoTo/Dest)']
        resolved_action_links = [link for link in extracted_links if link['type'] == 'Internal (Resolved Action)']
        other_links = [link for link in extracted_links if link['type'] not in ['External (URI)', 'Internal (GoTo/Dest)', 'Internal (Resolved Action)']]

        interal_resolve_action_links_count = len(resolved_action_links)
        internal_goto_links_count = len(goto_links) 
        total_internal_links_count = internal_goto_links_count + interal_resolve_action_links_count

        external_uri_links_count = len(external_uri_links)
        other_links_count = len(other_links)

        total_links_count = len(extracted_links)

        # --- ANALYSIS SUMMARY (Using your print logic) ---
        log("\n")
        log("=" * SEP_COUNT, overview = True)
        log(f"--- Link Analysis Results for {pdf_name} ---", overview = True)
        log(f"Total active links: {total_links_count} (External: {external_uri_links_count}, Internal Jumps: {total_internal_links_count}, Other: {other_links_count})",overview = True)
        log(f"Total **structural TOC entries (bookmarks)** found: {toc_entry_count}",overview = True)
        log("=" * SEP_COUNT,overview = True)

        # --- Section 1: TOC ---
        log(str_structural_toc)

        # --- Section 2: ACTIVE INTERNAL JUMPS ---
        log("\n")
        log("=" * SEP_COUNT)
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
        log("\n")
        log("=" * SEP_COUNT)
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
        log("\n")
        log("=" * SEP_COUNT)
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
            "validation": EMPTY_VALIDATION.copy()
        }

        
        intermediate_report_results = {
            "data": report_data_dict, # The structured JSON-ready dict
            "text-lines": "",
            "metadata": {                  # Helpful for the GUI/Logs
                "file_overview": {
                        "pdf_name": pdf_name,
                        "total_pages": total_pages,
                        "source_path": resolved_path,
                        "processing_path": resolved_path,    # internal only
                    },
                "library_used": pdf_library,
                "link_counts": {
                    "toc_entry_count": toc_entry_count,
                    "internal_goto_links_count": internal_goto_links_count,
                    "interal_resolve_action_links_count": interal_resolve_action_links_count,
                    "total_internal_links_count": total_internal_links_count,
                    "external_uri_links_count": external_uri_links_count,
                    "other_links_count": other_links_count,
                    "total_links_count": total_links_count
                }
            }
        }

        log("\n")
        log("--- Analysis Complete ---")

        validation_results = run_validation(report_results=intermediate_report_results,
                                            pdf_path=pdf_path)
        #log(validation_results.get("summary-txt",""), overview = True)

        summary_lines = validation_results.get("summary-lines", [])
        for line in summary_lines:
            log(line, overview=True)

        # CRITICAL: Re-assign to report_results so it's available for the final return
        report_results = copy.deepcopy(intermediate_report_results)

        # --- Offline Risk Analysis (Security Layer) ---
        risk_results = compute_risk(report_results)
        report_results["data"]["risk"] = risk_results
        report_results["data"]["validation"].update(validation_results)
        report_results["text-lines"] = report_buffer


        # Final aggregation and printing of the buffer into one string, after the last call to log()
        _print_report_algorithm(report_buffer,report_buffer_overview, print_bool, concise_print)
        return report_results

    except Exception as e:
        # Specific handling for common read failures
        if True:#"invalid pdf header" in str(e).lower() or "EOF marker not found" in str(e) or "stream has ended unexpectedly" in str(e):
            log("\n")
            log(f"Warning: Could not parse PDF structure — likely an image-only or malformed PDF.")
            log("No hyperlinks or TOC can exist in this file.")
            log("Result: No links found.")
            _print_report_algorithm(report_buffer,report_buffer_overview, print_bool, concise_print)
            return {
                "data": {"external_links": [], "internal_links": [], "toc": [], "validation": EMPTY_VALIDATION.copy()},
                "text-lines": report_buffer + [
                    "\n",
                    "Warning: PDF appears to be image-only or malformed.",
                    "No hyperlinks or structural TOC found."
                ],
                "metadata": {
                    "file_overview": {
                        "pdf_name": pdf_name,
                        "total_pages": total_pages,
                        "source_path": resolved_path,        # user-facing, stable
                        "processing_path": resolved_path,    # internal only
                    },
                    "library_used": pdf_library,
                    "link_counts": {
                        "toc_entry_count": 0,
                        "internal_goto_links_count": 0,
                        "interal_resolve_action_links_count": 0,
                        "total_internal_links_count": 0,
                        "external_uri_links_count": 0,
                        "other_links_count": 0,
                        "total_links_count": 0
                    }
                }
            }
    except Exception as e:
        error_logger.error(f"Critical failure during run_report for {pdf_path}: {e}", exc_info=True)
        log(f"FATAL: Analysis failed: {str(e)}. Check logs at {LOG_FILE_PATH}", file=sys.stderr)

        # Always return a safe empty result on error
        _print_report_algorithm(report_buffer,report_buffer_overview, print_bool, concise_print)
        return {
            "data": {
                "external_links": [],
                "internal_links": [],
                "toc": [],
                "validation": EMPTY_VALIDATION.copy()
            },
            "text-lines": report_buffer + [
                "\n",
                "--- Analysis failed ---",
                f"Error: {str(e)}",
                "No links or TOC extracted."
            ],
            "metadata": {
                "file_overview": {
                        "pdf_name": pdf_name,
                        "total_pages": total_pages,
                        "source_path": resolved_path,        # user-facing, stable
                        "processing_path": resolved_path,    # internal only
                    },
                "library_used": pdf_library,
                "link_counts": {
                        "toc_entry_count": 0,
                        "internal_goto_links_count": 0,
                        "interal_resolve_action_links_count": 0,
                        "total_internal_links_count": 0,
                        "external_uri_links_count": 0,
                        "other_links_count": 0,
                        "total_links_count": 0
                    }
            }
        }
    
# Final aggregation and printing of the buffer into one string, after the last call to log()
def _print_report_algorithm(report_buffer,report_buffer_overview, print_bool, concise_print):
    report_buffer_str = "\n".join(report_buffer)
    report_buffer_overview_str = "\n".join(report_buffer_overview)
    
    if print_bool:
        if concise_print:
            print(report_buffer_overview_str)
        else:
            print(report_buffer_str)
    
def _return_empty_report(report_buffer: str, pdf_library: str)-> dict:
    
    empty_report = {
            "data": {
                "external_links": [],
                "internal_links": [],
                "toc": [],
                "validation": EMPTY_VALIDATION.copy()
            },
            "text-lines": report_buffer,
            "metadata": {
                "file_overview": {
                    "pdf_name": "null",
                    "total_pages": 0,
                    "source_path": "null",        # user-facing, stable
                    "processing_path": "null",    # internal only
                },
                "library_used": pdf_library,
                "link_counts": {
                    "toc_entry_count": 0,
                    "internal_goto_links_count": 0,
                    "interal_resolve_action_links_count": 0,
                    "total_internal_links_count": 0,
                    "external_uri_links_count": 0,
                    "other_links_count": 0,
                    "total_links_count": 0
                }
            }
        }

    return empty_report

        
def get_structural_toc(structural_toc: list) -> str:
    """
    Formats the structural TOC data into a hierarchical string and optionally prints it.

    Args:
        structural_toc: A list of TOC dictionaries.

    Returns:
        A formatted string of the structural TOC.
    """
    toc_buffer = []
    def log_toc(msg: str):
        toc_buffer.append(msg)
        
    log_toc("\n")
    log_toc("=" * SEP_COUNT)
    log_toc("## Structural Table of Contents (PDF Bookmarks/Outline)")
    log_toc("=" * SEP_COUNT)

    if not structural_toc:
        msg = "No structural TOC (bookmarks/outline) found."
        log_toc(msg)
        output = "\n".join(toc_buffer)
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

        log_toc(f"{indent}{item['title']} . . . page {page_str}")

    log_toc("-" * SEP_COUNT)
    
    # Final aggregation
    str_structural_toc = "\n".join(toc_buffer)
        
    return str_structural_toc

import unicodedata

def sanitize_glyphs_for_compatibility(text: str) -> str:
    """Replaces emojis with ASCII tags to prevent rendering bugs in gedit/WSL2."""
    glyph_mapping = {
        '✅': '[PASS]',
        '🌐': '[WEB]',
        '⚠️': '[WARN]',
        '❌': '[FAIL]',
        'ℹ️': '[INFO]'
    }
    for glyph, replacement in glyph_mapping.items():
        text = text.replace(glyph, replacement)
    
    # Standard library only - no unidecode dependency
    normalized = unicodedata.normalize('NFKD', text)
    return normalized.encode('ascii', 'ignore').decode('utf-8').replace('  ', ' ')



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
        print_bool=True,  # We handle printing in validation
        concise_print=False
    )

    if not report or not report.get("data"):
        print("No data extracted — nothing to validate.")
        sys.exit(1)

    else:
        print("Success!")
        print(f"list(report['data']) = {list(report['data'])}")

