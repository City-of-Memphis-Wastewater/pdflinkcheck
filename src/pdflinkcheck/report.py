#!/usr/bin/env python3 
# SPDX-License-Identifier: MIT
# pdflinkcheck/report.py
from __future__ import annotations
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
import copy
import unicodedata
import logging
logger = logging.getLogger(__name__)

from pyhabitat import check_executable_path

from .logging_setup import error_logger    
from .paths import LOG_FILE_PATH

from pdflinkcheck.io import (
    export_report_json, 
    export_report_txt, 
    get_first_pdf_in_cwd, 
    get_friendly_path, 
)
from pdflinkcheck.validate import run_validation
from pdflinkcheck.security import compute_risk
from pdflinkcheck.helpers import PageRef, ExportFormat, PdfEngine, ReportRequest, LinkType
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


def run_report_request(request: ReportRequest) -> dict:
    return run_report_and_call_exports(
        request.pdf_path, 
        request.export_format, 
        request.pdf_library, 
        request.print_bool,
        request.concise_print,
        request.output_dir,
        request.check_external)
     
def run_report_and_call_exports(
    pdf_path: str | Path | None = None, 
    export_format: ExportFormat | None = ExportFormat.JSON, 
    pdf_library: PdfEngine | None = None, 
    print_bool: bool=True,
    concise_print: bool = False,
    output_dir: Optional[str] = None,
    check_external:bool=False
) -> Dict[str, Any]:
    """
    Public entry point. Orchestrates extraction, validation, and file exports.
    """

    logger.debug(f"{check_external=}")
    if pdf_library is None:
        pdf_library = PdfEngine.resolve_auto_flag()

    if not pdf_path:
        raise ValueError("pdf_path is required")
    pdf_path = Path(pdf_path)

    
    selected_formats = export_format
        
    #  The meat and potatoes
    report_results = run_report_core(
        pdf_path=pdf_path, 
        pdf_library = pdf_library,
        print_bool = print_bool,
        concise_print = concise_print,
        check_external=check_external
        
    )
    # 2. Initialize file path tracking
    output_path_json = None
    output_path_txt = None
    output_path_xlsx = None

    if export_format:
        report_data_dict = report_results["data"]
        report_buffer_str = report_results["text-lines"]
        if selected_formats & ExportFormat.JSON:
            output_path_json = export_report_json(report_data_dict, pdf_path, pdf_library_name = pdf_library.name.lower(),output_dir=output_dir)
        if selected_formats & ExportFormat.TXT:
            output_path_txt = export_report_txt(report_buffer_str, pdf_path, pdf_library_name = pdf_library.name.lower(),output_dir=output_dir)
        if selected_formats & ExportFormat.XLSX:
            output_path_xlsx = export_report_links_to_xlsx(report_results,pdf_path, pdf_library_name = pdf_library.name.lower(),output_dir=output_dir)

    # 4. Inject the file info into the results dictionary
    report_results["files"] = {
        "export_path_json": str(output_path_json) if output_path_json else None, 
        "export_path_txt": str(output_path_txt) if output_path_txt else None,
        "export_path_xlsx": str(output_path_xlsx) if output_path_xlsx else None
    }
    
    return report_results

def run_report_core(
    pdf_path: Path | None = None, 
    pdf_library: PdfEngine = PdfEngine.resolve_auto_flag(), 
    print_bool: bool = True,
    concise_print: bool = False,
    check_external:bool =False
) -> Dict[str, Any]:
    """Core high-level PDF link analysis logic coordinator."""
    report_buffer: List[str] = []
    report_buffer_overview: List[str] = []

    def log(msg: str, overview: bool = False):
        report_buffer.append(msg)
        if overview:
            report_buffer_overview.append(msg)

    if isinstance(pdf_library, str):
        pdf_library = PdfEngine.from_str(pdf_library)

    resolved_engine = pdf_library.resolve_if_auto()
    resolved_name = resolved_engine.name.lower()

    log("\n--- Analysis ---\n")
    if pdf_path is None:
        log("pdf_path is None", overview=True)
        log("Tip: Drop a PDF in the current folder or pass in a path arg.")
        _print_report_algorithm(report_buffer, report_buffer_overview, print_bool, concise_print)
        return _build_empty_report_dict("null", 0, "null", resolved_name, report_buffer)

    pdf_path = Path(pdf_path)
    pdf_name = pdf_path.name
    resolved_path = str(pdf_path.resolve())

    # Dynamically resolve engine targeting matrix
    try:
        if resolved_engine == PdfEngine.PDFIUM:
            from pdflinkcheck.analysis_pdfium import analyze_pdf
        elif resolved_engine == PdfEngine.PYMUPDF:
            from pdflinkcheck.analysis_pymupdf import analyze_pdf
        elif resolved_engine == PdfEngine.PYPDF:
            from pdflinkcheck.analysis_pypdf import analyze_pdf
        else:
            raise RuntimeError(f"Unsupported engine definition: {resolved_engine}")
    except ImportError as e:
        error_logger.error(f"Failed to load backend engine {resolved_name}: {e}", exc_info=True)
        log(f"FATAL: Back-end engine '{resolved_name}' could not be loaded.", overview=True)
        _print_report_algorithm(report_buffer, report_buffer_overview, print_bool, concise_print)
        return _build_empty_report_dict(pdf_name, 0, resolved_path, resolved_name, report_buffer)

    try:
        data = analyze_pdf(pdf_path) or {"links": [], "toc": [], "file_ov": []}
        
        extracted_links = data.get("links", [])
        print("delete me")
        print(extracted_links)
        structural_toc = data.get("toc", [])
        total_pages = data.get("file_ov", {}).get("total_pages", 0)

        log(f"Target file: {get_friendly_path(pdf_path)}", overview=True)
        log(f"PDF Engine: {resolved_name}", overview=True)

        if not extracted_links and not structural_toc:
            log(f"\nNo hyperlinks or structural TOC found in {pdf_name}.", overview=True)
            _print_report_algorithm(report_buffer, report_buffer_overview, print_bool, concise_print)
            return _build_empty_report_dict(pdf_name, total_pages, resolved_path, resolved_name, report_buffer)

        # Build categorized list segments and render text logs
        link_counts = _generate_report_text_layers(extracted_links, structural_toc, pdf_name, log)
        link_counts["toc_entry_count"] = len(structural_toc)

        # each of these needs a GUID and to be nested in a step further, with a details section, a validation section, and a risk section
        base_data_dict = {
            "external_links": [k for k in extracted_links if k.get('type') == LinkType.EXTERNAL.value], 
            "internal_links": [k for k in extracted_links if k.get('type') in [LinkType.INTERNAL_GOTO.value, LinkType.INTERNAL_RESOLVED.value]], 
            "toc": structural_toc,
            "validation": EMPTY_VALIDATION.copy()
        }

        intermediate_results = {
            "data": base_data_dict,
            "text-lines": "",
            "metadata": {
                "file_overview": {
                    "pdf_name": pdf_name, "total_pages": total_pages,
                    "source_path": resolved_path, "processing_path": resolved_path
                },
                "library_used": resolved_name,
                "link_counts": link_counts
            }
        }

        log("\n--- Analysis Complete ---")

        # Execute validation pipeline on defensive deep copy
        report_results = copy.deepcopy(intermediate_results)
        validation_results = run_validation(report_results=report_results, pdf_path=pdf_path, check_external=check_external)

        for line in validation_results.get("summary-lines", []):
            log(line, overview=True)

        # Assemble finalized payload architecture
        report_results["data"]["risk"] = compute_risk(report_results)
        report_results["data"]["validation"].update(validation_results)
        report_results["text-lines"] = report_buffer

        _print_report_algorithm(report_buffer, report_buffer_overview, print_bool, concise_print)
        return report_results

    except Exception as e:
        error_logger.error(f"Critical failure during run_report processing for {pdf_path}: {e}", exc_info=True)
        print(f"FATAL: Analysis failed: {str(e)}. Check logs at {LOG_FILE_PATH}", file=sys.stderr)
        
        log(f"\nWarning: Processing interrupted due to an internal parsing anomaly.")
        _print_report_algorithm(report_buffer, report_buffer_overview, print_bool, concise_print)
        return _build_empty_report_dict(pdf_name if 'pdf_name' in locals() else "Unknown", 0, resolved_path, resolved_name, report_buffer)


def _generate_report_text_layers(extracted_links: list, structural_toc: list, pdf_name: str, log_fn: Any) -> Dict[str, int]:
    """Generates the console logs and splits the raw metrics safely."""
    external_uri = [l for l in extracted_links if l.get('type') == LinkType.EXTERNAL.value]
    goto_links = [l for l in extracted_links if l.get('type') ==  LinkType.INTERNAL_GOTO.value]
    resolved_action = [l for l in extracted_links if l.get('type') == LinkType.INTERNAL_RESOLVED.value]
    other_links = [l for l in extracted_links if l.get('type') not in [LinkType.EXTERNAL.value, LinkType.INTERNAL_GOTO.value, LinkType.INTERNAL_RESOLVED.value]]

    total_internal = len(goto_links) + len(resolved_action)

    log_fn("\n" + "=" * SEP_COUNT, overview=True)
    log_fn(f"--- Link Analysis Results for {pdf_name} ---", overview=True)
    log_fn(f"Total active links: {len(extracted_links)} (External: {len(external_uri)}, Internal Jumps: {total_internal}, Other: {len(other_links)})", overview=True)
    log_fn(f"Total **structural TOC entries (bookmarks)** found: {len(structural_toc)}", overview=True)
    log_fn("=" * SEP_COUNT, overview=True)

    log_fn(get_structural_toc(structural_toc))

    # Internal Jumps Block
    log_fn(f"\n" + "=" * SEP_COUNT + f"\n## Active Internal Jumps (GoTo & Resolved Actions) - {total_internal} found\n" + "=" * SEP_COUNT)
    log_fn("{:<5} | {:<5} | {:<40} | {}".format("Idx", "Page", "Anchor Text", "Jumps To Page"))
    log_fn("-" * SEP_COUNT)
    for i, link in enumerate(goto_links + resolved_action, 1):
        log_fn("{:<5} | {:<5} | {:<40} | {}".format(
            i, PageRef.from_index(link['page']).human, link.get('link_text', 'N/A')[:40], PageRef.from_index(link['destination_page']).human
        ))

    # External URI Block
    log_fn(f"\n" + "=" * SEP_COUNT + f"\n## Active URI Links (External) - {len(external_uri)} found\n" + "{:<5} | {:<5} | {:<40} | {}\n".format("Idx", "Page", "Anchor Text", "Target URI/Action") + "=" * SEP_COUNT)
    for i, link in enumerate(external_uri, 1):
        log_fn("{:<5} | {:<5} | {:<40} | {}".format(i, link['page'], link.get('link_text', 'N/A')[:40], link.get('url') or link.get('remote_file')))

    # Fallback Other Category Block
    log_fn(f"\n" + "=" * SEP_COUNT + f"\n## Other Links  - {len(other_links)} found\n" + "{:<5} | {:<5} | {:<40} | {}\n".format("Idx", "Page", "Anchor Text", "Target Action") + "=" * SEP_COUNT)
    for i, link in enumerate(other_links, 1):
        log_fn("{:<5} | {:<5} | {:<40} | {}".format(i, link['page'], link.get('link_text', 'N/A')[:40], link.get('url') or link.get('remote_file')))

    return {
        "internal_goto_links_count": len(goto_links),
        "interal_resolve_action_links_count": len(resolved_action),
        "total_internal_links_count": total_internal,
        "external_uri_links_count": len(external_uri),
        "other_links_count": len(other_links),
        "total_links_count": len(extracted_links)
    }
    
# Final aggregation and printing of the buffer into one string, after the last call to log()
def _print_report_algorithm(report_buffer: list, report_buffer_overview: list, print_bool: bool, concise_print: bool):
    if print_bool:
        print("\n".join(report_buffer_overview if concise_print else report_buffer))

def _build_empty_report_dict(name: str, pages: int, path: str, engine_name: str, buffer: list) -> dict:
    """Factory helper providing fully structured empty states safely."""
    return {
        "data": {"external_links": [], "internal_links": [], "toc": [], "validation": EMPTY_VALIDATION.copy()},
        "text-lines": buffer,
        "metadata": {
            "file_overview": {"pdf_name": name, "total_pages": pages, "source_path": path, "processing_path": path},
            "library_used": engine_name,
            "link_counts": {
                "toc_entry_count": 0, "internal_goto_links_count": 0, "interal_resolve_action_links_count": 0,
                "total_internal_links_count": 0, "external_uri_links_count": 0, "other_links_count": 0, "total_links_count": 0
            }
        }
    }

        
def get_structural_toc(structural_toc: list) -> str:
    """
    Formats the structural TOC data into a hierarchical string.

    Args:
        structural_toc: A list of TOC dictionaries.

    Returns:
        A formatted string of the structural TOC.
    """
    toc_buffer = []
    def log_toc(msg: str):
        toc_buffer.append(msg)
    
    # Rename this list variable to avoid overwriting the function 'log_toc'
    header_list = ["\n" + "=" * SEP_COUNT, "## Structural Table of Contents (PDF Bookmarks/Outline)", "=" * SEP_COUNT]
    toc_buffer.extend(header_list)

    if not structural_toc:
        msg = "No structural TOC (bookmarks/outline) found."
        log_toc(msg)
        return "\n".join(toc_buffer)

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
        display_val = PageRef.from_index(target_page).human if isinstance(target_page, int) else str(target_page)
        page_str = str(display_val).rjust(page_width)
        log_toc(f"{indent}{item['title']} . . . page {page_str}")

    log_toc("-" * SEP_COUNT)
    
    # Final aggregation
    return "\n".join(toc_buffer)

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



def demo():
    from pdflinkcheck.io import get_first_pdf_in_cwd
    pdf_path = get_first_pdf_in_cwd()    # Run analysis first

    report = run_report_and_call_exports(
        pdf_path=pdf_path,
        export_format=ExportFormat.NONE,
        pdf_library=PdfEngine.AUTO,
        print_bool=True,  # We handle printing in validation
        concise_print=False
    )

    if not report or not report.get("data"):
        print("No data extracted — nothing to validate.")
        sys.exit(1)

    else:
        print("Success!")
        print(f"list(report['data']) = {list(report['data'])}")

if __name__ == "__main__":
    demo()