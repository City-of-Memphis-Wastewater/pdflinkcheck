#!/usr/bin/env python3 
# SPDX-License-Identifier: MIT
# src/pdflinkcheck/validate.py

import sys
from pathlib import Path
from typing import Dict, Any

from pdflinkcheck.io import get_friendly_path
from pdflinkcheck.environment import pymupdf_is_available

SEP_COUNT=28

def run_validation(
    report_results: Dict[str, Any],
    pdf_path: str,
    pdf_library: str = "pypdf",
    check_external: bool = False
) -> Dict[str, Any]:
    """
    Validates links during run_report() using a partial completion of the data dict.

    Args:
        report_results: The dict returned by run_report_and_call_exports()
        pdf_path: Path to the original PDF (needed for relative file checks and page count)
        pdf_library: Engine used ("pypdf" or "pymupdf")
        check_external: Whether to validate HTTP URLs (requires network + requests)

    Returns:
        Validation summary stats with valid/broken counts and detailed issues
    """
    data = report_results.get("data", {})
    metadata = report_results.get("metadata", {})

    all_links = data.get("external_links", []) + data.get("internal_links", [])
    toc = data.get("toc", [])

    if not all_links and not toc:
        print("No links or TOC to validate.")
        return {"summary-stats": {"valid": 0, "broken": 0}, "issues": []}

    # Get total page count (critical for internal validation)
    try:
        if pymupdf_is_available() and pdf_library == "pymupdf":
            import fitz
            doc = fitz.open(pdf_path)
            total_pages = doc.page_count
            doc.close()
        else:
            from pypdf import PdfReader
            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages)
    except Exception as e:
        print(f"Could not determine page count: {e}")
        total_pages = None

    pdf_dir = Path(pdf_path).parent

    issues = []
    valid_count = 0 # add more granulaity for types of valid links
    file_found_count = 0
    broken_file_count = 0
    broken_page_count = 0
    no_destination_page_count = 0
    unknown_web_count = 0
    unknown_reasonableness_count = 0
    unknown_link_count = 0

    # Validate active links
    #print("DEBUG validate: entering loop with", len(all_links), "links")
    for i, link in enumerate(all_links):
        link_type = link.get("type")
        status = "valid"
        reason = None
        if link_type in ("Internal (GoTo/Dest)", "Internal (Resolved Action)"):
            dest_page_raw = link.get("destination_page")
            if dest_page_raw is None:
                status = "no-destinstion-page"
                reason = "No destination page resolved"
            else:
                try:
                    target_page = int(dest_page_raw)
                    #target_page = int(link.get("destination_page"))
                    if not isinstance(target_page, int):
                        status = "broken-page"
                        reason = f"Target page not a number: {target_page}"
                    elif (1 <= target_page) and total_pages is None:
                        status = "unknown-reasonableness"
                        reason = "Total page count unavailable, but the page number is reasonable"
                    elif (1 <= target_page <= total_pages):
                        status = "valid"
                        reason = f"Page {target_page} within range (1–{total_pages})"
                    elif target_page < 1:
                        status = "broken-page"
                        reason = f"TOC targets page negative {target_page}."
                    elif not (1 <= target_page <= total_pages):
                        status = "broken-page"
                        reason = f"Page {target_page} out of range (1–{total_pages})"
                except (ValueError, TypeError):
                    status = "broken-page"
                    reason = f"Invalid page value: {dest_page_raw}"
        elif link_type == "Remote (GoToR)":
            remote_file = link.get("remote_file")
            if not remote_file:
                status = "broken-file"
                reason = "Missing remote file name"
            else:
                target_path = (pdf_dir / remote_file).resolve()
                if target_path.exists() and target_path.is_file():
                    status = "file-found"
                    reason = f"Found: {target_path.name}"
                else:
                    status = "broken-file"
                    reason = f"File not found: {remote_file}"
            
        elif link_type == "External (URI)":
            url = link.get("url")
            if url and url.startswith(("http://", "https://")) and check_external:
                # Optional: add requests-based check later
                status = "unknown-web"
                reason = "External URL validation not enabled"
            else:
                status = "unknown-web"
                reason = "External link (no network check)"
            
        else:
            status = "unknown-link"
            reason = "Other/unsupported link type"
            
        link_with_val = link.copy()
        link_with_val["validation"] = {"status": status, "reason": reason}

        if status == "valid":
            valid_count += 1
        elif status =="file-found":
            file_found_count += 1
        elif status == "unknown-web":
            unknown_web_count += 1
        elif status == "unknown-reasonableness":
            unknown_reasonableness_count += 1
        elif status == "unknown-link":
            unknown_link_count += 1
        elif status == "broken-page":
            broken_page_count += 1
            issues.append(link_with_val)
        elif status == "broken-file":
            broken_file_count += 1
            issues.append(link_with_val)
        elif status == "no-destinstion-page":
            no_destination_page_count += 1
            issues.append(link_with_val)
    # Validate TOC entries
    for entry in toc:
        target_page = int(entry.get("target_page"))
        if isinstance(target_page, int):
            if (1 <= target_page) and total_pages is None:
                reason = "Page count unknown"
                status = "unknown-reasonableness"
                unknown_reasonableness_count += 1
            elif target_page < 1:
                status = "broken-page"
                broken_page_count += 1
                reason = f"TOC targets negative page: {target_page}."
            elif 1 <= target_page <= total_pages:
                valid_count += 1
                continue
            else:
                status = "broken-page"
                reason = f"TOC targets page {target_page} (out of 1–{total_pages})"
                broken_page_count += 1
        else:
            status = "broken-page"
            reason = f"Invalid page: {target_page}"
            broken_page_count += 1

        issues.append({
            "type": "TOC Entry",
            "title": entry["title"],
            "level": entry["level"],
            "target_page": target_page,
            "validation": {"status": status, "reason": reason}
        })
    
    total_checked = metadata.get("link_counts",{}).get("total_links_count",0) + metadata.get("link_counts",{}).get("toc_entry_count",0)
    summary_stats = {
        "total_checked": total_checked,
        "valid": valid_count,
        "file-found": file_found_count,
        "broken-page": broken_page_count,
        "broken-file": broken_file_count,
        "no_destination_page_count": no_destination_page_count,
        "unknown-web": unknown_web_count,
        "unknown-reasonableness": unknown_reasonableness_count,
        "unknown-link": unknown_link_count 
    }

    
    def generate_validation_summary_txt_buffer(summary_stats, issues, pdf_path):
        """
        Prepare the validation overview for modular reuse
        """
        validation_buffer = []

        # Helper to handle conditional printing and mandatory buffering
        def log(msg: str):
            validation_buffer.append(msg)
    
        log("\n" + "=" * SEP_COUNT)
        log("## Validation Results")
        log("=" * SEP_COUNT)
        log(f"PDF Path = {get_friendly_path(pdf_path)}")
        log(f"Total items checked: {summary_stats['total_checked']}")
        log(f"✅ Valid: {summary_stats['valid']}")
        #log(f"✅ Valid: {summary_stats['valid']}")
        #log(f"✅ Valid: {summary_stats['valid']}")
        log(f"🌐 Web Addresses (Not Checked): {summary_stats['unknown-web']}")
        log(f"⚠️ Unknown Page Reasonableness (Due to Missing Total Page Count): {summary_stats['unknown-reasonableness']}")
        log(f"⚠️ Unsupported PDF Links: {summary_stats['unknown-link']}")
        log(f"❌ Broken Page Reference (Page number beyond scope of availability): {summary_stats['broken-page']}")
        log(f"❌ Broken File Reference (File not available): {summary_stats['broken-file']}")
        log("=" * SEP_COUNT)

        if issues:
            log("\n## Issues Found")
            log("{:<5} | {:<12} | {:<30} | {}".format("Idx", "Type", "Text", "Problem"))
            log("-" * SEP_COUNT)
            for i, issue in enumerate(issues[:25], 1):
                link_type = issue.get("type", "Link")
                text = issue.get("link_text", "") or issue.get("title", "") or "N/A"
                text = text[:30]
                reason = issue["validation"]["reason"]
                log("{:<5} | {:<12} | {:<30} | {}".format(i, link_type, text, reason))
            if len(issues) > 25:
                log(f"... and {len(issues) - 25} more issues")

        elif summary_stats.get('total_checked', 0) == 0:
            # Check if this was a total crash or just an empty PDF
            if summary_stats.get('is_error_fallback'): 
                 log("\nStatus: Validation could not be performed due to a processing error.")
            else:
                 log("\nStatus: No links or TOC entries were found to validate.")

        else:
            log("Success: No broken links or TOC issues!")

        # Final aggregation of the buffer into one string
        validation_buffer_str = "\n".join(validation_buffer)
        
        return validation_buffer_str
    
    summary_txt = generate_validation_summary_txt_buffer(summary_stats, issues, pdf_path)

    validation_results = {
        "pdf_path" : pdf_path,
        "summary-stats": summary_stats,
        "issues": issues,
        "summary-txt": summary_txt,
        "total_pages": total_pages
    }

    return validation_results


def run_validation_more_readable_slop(pdf_path: str = None, pdf_library: str = "pypdf", check_external_links:bool = False) -> Dict[str, Any]:
    """
    Experimental. Ignore for now.

    Extends the report logic by programmatically testing every extracted link.
    Validates Internal Jumps (page bounds), External URIs (HTTP status), 
    and Launch actions (file existence).
    """
    if check_external_links:
        import requests

    # 1. Setup Library Engine (Reuse logic)
    pdf_library = pdf_library.lower()
    if pdf_library == "pypdf":
        from pdflinkcheck.analysis_pypdf import extract_links_pypdf as extract_links
    else:
        from pdflinkcheck.analysis_pymupdf import extract_links_pymupdf as extract_links

    if pdf_path is None:
        pdf_path = get_first_pdf_in_cwd()
    
    if not pdf_path:
        print("Error: No PDF found for validation.")
        return {}

    print(f"\nValidating links in {Path(pdf_path).name}...")

    # 2. Extract links and initialize validation counters
    links = extract_links(pdf_path)
    total_links_count = len(links)
    results = {"valid": [], "broken": [], "error": []}

    # 3. Validation Loop
    for i, link in enumerate(links, 1):
        # Progress indicator for long manuals
        sys.stdout.write(f"\rChecking link {i}/{total_links_count}...")
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

    print("\n" + "=" * SEP_COUNT)
    print(f"--- Validation Summary Stats for {Path(pdf_path).name} ---")
    print(f"Total Checked: {total_links_count}")
    print(f"✅ Valid:  {len(results['valid'])}")
    print(f"❌ Broken: {len(results['broken'])}")
    print("=" * SEP_COUNT)

    # 4. Print Detail Report for Broken Links
    if results['broken']:
        print("\n## ❌ Broken Links Found:")
        print("{:<5} | {:<5} | {:<30} | {}".format("Idx", "Page", "Reason", "Target"))
        print("-" * SEP_COUNT)
        for i, link in enumerate(results['broken'], 1):
            target = link.get('url') or link.get('destination_page') or link.get('remote_file')
            print("{:<5} | {:<5} | {:<30} | {}".format(
                i, link['page'], link['validation']['reason'], str(target)[:30]
            ))
    
    return results
