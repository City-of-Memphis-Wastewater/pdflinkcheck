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
    report_results = run_report_extraction_and_assessment_and_recording(
        pdf_path=str(pdf_path), 
        pdf_library = pdf_library,
        print_bool = print_bool,
        concise_print = concise_print,
    )
    # 2. Initialize file path tracking
    output_path_json = None
    output_path_txt = None
    
    if export_format:
        report_data_dict = report_results["data"]
        report_buffer_str = report_results["text-lines"]
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

def _get_engine_data(pdf_path: str, pdf_library: str) -> tuple[Dict, str]:
    """Handles the dirty work of switching engines and importing them."""
    # Resolve 'auto' mode
    if pdf_library == "auto":
        if pdfium_is_available(): pdf_library = "pdfium"
        elif pymupdf_is_available(): pdf_library = "pymupdf"
        else: pdf_library = "pypdf"

    # Map engine names to their respective modules
    engines = {
        "pdfium": "pdflinkcheck.analysis_pdfium",
        "pypdf": "pdflinkcheck.analysis_pypdf", # Assuming this exists
        "pymupdf": "pdflinkcheck.analysis_pymupdf"
    }

    if pdf_library not in engines:
        raise ValueError(f"Unsupported library: {pdf_library}")

    # Dynamic import to keep __init__ lean
    import importlib
    module = importlib.import_module(engines[pdf_library])
    data = module.analyze_pdf(pdf_path) or {"links": [], "toc": [], "file_ov": {}}
    
    return data, pdf_library

# ----- Refactored version, failing ----
def run_report_extraction_and_assessment_and_recording_(
    pdf_path: str = None, 
    pdf_library: str = "auto", 
    print_bool: bool = True,
    concise_print: bool = False
) -> Dict[str, Any]:
    """
    Orchestrates extraction, categorization, and validation.
    FULLY RECONCILED with legacy logic to ensure no features are lost.
    """
    if pdf_path is None:
        return _return_empty_report(["pdf_path is None"], pdf_library)

    try:
        # 1. Extraction
        raw_data, resolved_library = _get_engine_data(pdf_path, pdf_library)
        
        extracted_links = raw_data.get("links", [])
        structural_toc = raw_data.get("toc", [])
        file_ov = raw_data.get("file_ov", {})
        total_pages = file_ov.get("total_pages", 0)
        pdf_name = Path(pdf_path).name

        # 2. Categorization (Restored exactly from original logic)
        external_uri_links = [link for link in extracted_links if link['type'] == 'External (URI)']
        goto_links = [link for link in extracted_links if link['type'] == 'Internal (GoTo/Dest)']
        resolved_action_links = [link for link in extracted_links if link['type'] == 'Internal (Resolved Action)']
        other_links = [link for link in extracted_links if link['type'] not in 
                       ['External (URI)', 'Internal (GoTo/Dest)', 'Internal (Resolved Action)']]

        all_internal = goto_links + resolved_action_links

        # 3. Generate the Text Report (Using get_friendly_path as required)
        # We pass the separate lists to maintain Section 2, 3, and 4 formatting
        report_text_base = _generate_text_report(
            pdf_path=pdf_path,
            library=resolved_library, 
            ext_links=external_uri_links, 
            goto_links=goto_links,
            resolve_links=resolved_action_links,
            other_links=other_links, 
            toc=structural_toc
        )

        # 4. Initial Result Assembly
        report_results = {
            "data": {
                "external_links": external_uri_links,
                "internal_links": goto_links + resolved_action_links,
                "toc": structural_toc,
                "validation": EMPTY_VALIDATION.copy()
            },
            "text-lines": report_text_base,
            "metadata": _build_metadata(
                pdf_name=pdf_name, 
                total_pages=total_pages, 
                library_used=resolved_library, 
                toc_entry_count=len(structural_toc), 
                internal_goto_links_count=len(goto_links), 
                interal_resolve_action_links_count=len(resolved_action_links),
                external_uri_links_count=len(external_uri_links), 
                other_links_count=len(other_links)
            )
        }

        # 5. Validation & Risk Analysis
        validation_results = run_validation(report_results=report_results, pdf_path=pdf_path)
        report_results["data"]["validation"].update(validation_results)
        report_results["data"]["risk"] = compute_risk(report_results)

        # --- Inside run_report_extraction_and_assessment_and_recording ---
        # 6. Finalizing Text Buffer
        #val_summary = validation_results.get("summary-txt", "")
        val_summary = validation_results.get("summary-lines", "")
        raw_text = report_text_base + f"\n{val_summary}\n--- Analysis Complete ---"
        cleaned_text = sanitize_glyphs_for_compatibility(raw_text)
        # Apply sanitization before returning
        report_results["text-lines"] = cleaned_text
        #report_results["text-lines"] = raw_text

        if print_bool:
            # Matches your original logic: print the overview/validation summary to console
            print(val_summary)

        return report_results

    except Exception as e:
        error_logger.error(f"Critical failure: {e}", exc_info=True)
        return _return_empty_report([f"FATAL: {str(e)}"], pdf_library)

# ----- Revert to stable version ----
def run_report_extraction_and_assessment_and_recording(
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
    


    # Expected: "pypdf" or "PyMuPDF" pr "rust"
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
        
        # check the structure, that it matches
        if False:
            print(f"pdf_library={pdf_library}")
            debug_head("TOC", structural_toc, n=3)
            debug_head("Links", list(extracted_links), n=3)
        
        # THIS HITS

        if not extracted_links and not structural_toc:
            log("\n")
            log(f"No hyperlinks or structural TOC found in {pdf_name}.", overview=True)
            log("(This is common for scanned/image-only PDFs.)", overview=True)

            empty_result = {
                "data": {
                    "external_links": [],
                    "internal_links": [],
                    "toc": []
                },
                "text-lines": report_buffer,
                "metadata": {
                    "file_overview": {
                        "pdf_name": pdf_name,
                        "total_pages": total_pages,
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
        
        # Final aggregation of the buffer into one string, after the last call to log()
        report_buffer_str = "\n".join(report_buffer)
        
        report_buffer_overview_str = "\n".join(report_buffer_overview)

        report_results["data"]["validation"].update(validation_results)

        
        #report_results["text-lines"].update(report_buffer_str)      # The human-readable string
        #report_results["text-lines"] = report_buffer_str
        report_results["text-lines"] = report_buffer

        # 5. Export Report 
        #if export_format:
        #    # Assuming export_to will hold the output format string (e.g., "JSON")
        #    export_report_data(report_data_dict, pdf_name, export_format, pdf_library)
        
        if print_bool:
            if concise_print:
                print(report_buffer_overview_str)
            else:
                print(report_buffer_str)
            
        return report_results

    except Exception as e:
        # Specific handling for common read failures
        if True:#"invalid pdf header" in str(e).lower() or "EOF marker not found" in str(e) or "stream has ended unexpectedly" in str(e):
            log("\n")
            log(f"Warning: Could not parse PDF structure — likely an image-only or malformed PDF.")
            log("No hyperlinks or TOC can exist in this file.")
            log("Result: No links found.")
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

    #except Exception as e:
    #    # Log the critical failure
    #    error_logger.error(f"Critical failure during run_report for {pdf_path}: {e}", exc_info=True)
    #    log(f"FATAL: Analysis failed. Check logs at {LOG_FILE_PATH}", file=sys.stderr)
    #    raise # Allow the exception to propagate or handle gracefully
    except Exception as e:
        error_logger.error(f"Critical failure during run_report for {pdf_path}: {e}", exc_info=True)
        log(f"FATAL: Analysis failed: {str(e)}. Check logs at {LOG_FILE_PATH}", file=sys.stderr)

        # Always return a safe empty result on error
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

def _generate_text_report(
    pdf_path: str, 
    library: str, 
    ext_links: list, 
    goto_links: list, 
    resolve_links: list, 
    other_links: list, 
    toc: list
) -> str:
    """Pure helper to build the human-readable string for console/TXT export."""
    lines = []
    lines.append("\n--- Starting Analysis ... ---\n")
    lines.append(f"Target file: {get_friendly_path(pdf_path)}")
    lines.append(f"PDF Engine: {library}")
    
    total_int = len(goto_links) + len(resolve_links)
    total_links = len(ext_links) + total_int + len(other_links)

    # 1. Summary Header
    lines.append("\n" + "=" * SEP_COUNT)
    lines.append(f"--- Link Analysis Results for {get_friendly_path(pdf_path)} ---")
    lines.append(f"Total active links: {total_links} (External: {len(ext_links)}, Internal Jumps: {total_int}, Other: {len(other_links)})")
    lines.append(f"Total **structural TOC entries (bookmarks)** found: {len(toc)}")
    lines.append("=" * SEP_COUNT)

    # 2. Table of Contents
    lines.append(get_structural_toc(toc))

    # 3. Internal Jumps
    lines.append("\n" + "=" * SEP_COUNT)
    lines.append(f"## Active Internal Jumps (GoTo & Resolved Actions) - {total_int} found")
    lines.append("=" * SEP_COUNT)
    lines.append("{:<5} | {:<5} | {:<40} | {}".format("Idx", "Page", "Anchor Text", "Jumps To Page"))
    lines.append("-" * SEP_COUNT)
    
    all_internal = goto_links + resolve_links
    if all_internal:
        for i, link in enumerate(all_internal, 1):
            src = PageRef.from_index(link.get('page', 0)).human
            dest = PageRef.from_index(link.get('destination_page', 0)).human
            lines.append("{:<5} | {:<5} | {:<40} | {}".format(
                i, src, link.get('link_text', 'N/A')[:40], dest
            ))
    else:
        lines.append(" No internal GoTo or Resolved Action links found.")
    lines.append("-" * SEP_COUNT)

    # 4. External URI Links
    lines.append("\n" + "=" * SEP_COUNT)
    lines.append(f"## Active URI Links (External) - {len(ext_links)} found")
    lines.append("{:<5} | {:<5} | {:<40} | {}".format("Idx", "Page", "Anchor Text", "Target URI/Action"))
    lines.append("=" * SEP_COUNT)
    
    if ext_links:
        for i, link in enumerate(ext_links, 1):
            target = link.get('url') or link.get('remote_file') or link.get('target', 'N/A')
            lines.append("{:<5} | {:<5} | {:<40} | {}".format(
                i, link.get('page', 0), link.get('link_text', 'N/A')[:40], target
            ))
    else:
        lines.append(" No external links found.")
    lines.append("-" * SEP_COUNT)

    # 5. Other Links
    lines.append("\n" + "=" * SEP_COUNT)
    lines.append(f"## Other Links - {len(other_links)} found")
    lines.append("{:<5} | {:<5} | {:<40} | {}".format("Idx", "Page", "Anchor Text", "Target Action"))
    lines.append("=" * SEP_COUNT)
    
    if other_links:
        for i, link in enumerate(other_links, 1):
            target = link.get('url') or link.get('remote_file') or link.get('target', 'N/A')
            lines.append("{:<5} | {:<5} | {:<40} | {}".format(
                i, link.get('page', 0), link.get('link_text', 'N/A')[:40], target
            ))
    else:
        lines.append(" No 'Other' links found.")
    lines.append("-" * SEP_COUNT)

    return "\n".join(lines)

def _generate_text_report__(pdf_path, library, ext_links, int_links, other_links, toc) -> str:
    lines = []
    lines.append("\n--- Starting Analysis ... ---\n")
    lines.append(f"Target file: {get_friendly_path(pdf_path)}")
    lines.append(f"PDF Engine: {library}")
    
    # 1. Summary Header
    lines.append("\n" + "=" * SEP_COUNT)
    lines.append(f"--- Link Analysis Results for {get_friendly_path(pdf_path)} ---")
    lines.append(f"Total active links: {len(ext_links) + len(int_links) + len(other_links)}")
    lines.append(f"Total bookmarks: {len(toc)}")
    lines.append("=" * SEP_COUNT)

    # 2. Table of Contents
    lines.append(get_structural_toc(toc))

    # 3. Internal Jumps (GoTo & Resolved)
    lines.append("\n" + "=" * SEP_COUNT)
    lines.append(f"## Active Internal Jumps - {len(int_links)} found")
    lines.append("=" * SEP_COUNT)
    lines.append("{:<5} | {:<5} | {:<40} | {}".format("Idx", "Page", "Anchor Text", "Jumps To"))
    
    for i, link in enumerate(int_links, 1):
        src = PageRef.from_index(link.get('page', 0)).human
        dest = PageRef.from_index(link.get('destination_page', 0)).human
        lines.append("{:<5} | {:<5} | {:<40} | {}".format(i, src, link.get('link_text', 'N/A')[:40], dest))

    # 4. External URI Links
    lines.append("\n" + "=" * SEP_COUNT)
    lines.append(f"## External URI Links - {len(ext_links)} found")
    lines.append("=" * SEP_COUNT)
    for i, link in enumerate(ext_links, 1):
        target = link.get('url') or link.get('target', 'N/A')
        lines.append("{:<5} | {:<5} | {:<40} | {}".format(i, link.get('page', 0), link.get('link_text', 'N/A')[:40], target))

    return "\n".join(lines)

def _build_metadata(
    pdf_name: str, 
    total_pages: int, 
    library_used: str, 
    toc_entry_count: int, 
    internal_goto_links_count: int, 
    interal_resolve_action_links_count: int,
    external_uri_links_count: int, 
    other_links_count: int
) -> Dict[str, Any]:
    """
    Standardizes the metadata dictionary using the EXACT legacy variable names.
    """
    total_internal_links_count = internal_goto_links_count + interal_resolve_action_links_count
    total_links_count = total_internal_links_count + external_uri_links_count + other_links_count

    return {
        "file_overview": {
            "pdf_name": pdf_name,
            "total_pages": total_pages,
        },
        "library_used": library_used,
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

def _build_metadata_(
    pdf_name: str, 
    total_pages: int, 
    library_used: str, 
    toc_count: int, 
    goto_count: int, 
    resolve_count: int,
    ext_count: int, 
    other_count: int
) -> Dict[str, Any]:
    """Standardizes the metadata dictionary for all report types."""
    return {
        "file_overview": {
            "pdf_name": pdf_name,
            "total_pages": total_pages,
        },
        "library_used": library_used,
        "link_counts": {
            "toc_entry_count": toc_count,
            "internal_links_count": goto_count,
            "external_uri_links_count": ext_count,
            "other_links_count": other_count,
            "total_links_count": goto_count + ext_count + other_count
        }
    }
        
def get_structural_toc(structural_toc: list) -> str:
    """
    Formats the structural TOC data into a hierarchical string and optionally prints it.

    Args:
        structural_toc: A list of TOC dictionaries.

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

