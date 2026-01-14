#!/usr/bin/env python3 
# SPDX-License-Identifier: MIT
# src/pdflinkcheck/validate.py
from __future__ import annotations
import sys
from pathlib import Path
from typing import Dict, Any

from pdflinkcheck.io import get_friendly_path
from pdflinkcheck.helpers import PageRef  # Importing the established helper

SEP_COUNT=28

START_INDEX = 0  
# Internal 0-based start
# Define the offset. 
# The PDF engines are 0-based.
# We will add +1 only for the HUMAN REASON strings.


def run_validation(
    report_results: Dict[str, Any],
    pdf_path: str,
    check_external: bool = False
) -> Dict[str, Any]:
    """
    Validates links during run_report_*() using a partial completion of the data dict.

    Args:
        report_results: The dict returned by run_report_and_call_exports()
        pdf_path: Path to the original PDF (needed for relative file checks and page count)
        check_external: Whether to validate HTTP URLs (requires network + requests)

    Returns:
        Validation summary stats with valid/broken counts and detailed issues
    """
    data = report_results.get("data", {})
    metadata = report_results.get("metadata", {})

    all_links = data.get("external_links", []) + data.get("internal_links", [])
    toc = data.get("toc", [])
    total_pages = metadata.get("file_overview", {}).get("total_pages",None)

    if not all_links and not toc:
        print("No links or TOC to validate.")
        return {"summary-stats": {"valid": 0, "broken": 0}, "issues": []}


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
    for link in all_links:
        link_type = link.get("type")
        status = "valid"
        reason = None

        if link_type in ("Internal (GoTo/Dest)", "Internal (Resolved Action)"):
            dest_page_raw = link.get("destination_page")

            if dest_page_raw is not None:

                try:
                    # Use PageRef to handle translation
                    target_page_ref = PageRef.from_index(int(dest_page_raw))
                    #target_page = int(dest_page_raw)
                    
                    # 1. Immediate Failure: Below 0
                    if target_page_ref.machine < START_INDEX:
                        status = "broken-page"
                        # We use target_page + 1 to show the user what they "saw"
                        reason = f"Target page {target_page_ref.human} is invalid (negative index)."

                    # 2. Case: We don't know the max page count
                    elif total_pages is None:
                        # If it's 0 or higher, we assume it might be okay but can't be sure
                        status = "unknown-reasonableness"
                        reason = f"Page {target_page_ref.human} seems reasonable, but total page count is unavailable."

                    # 3. Case: Out of Upper Bounds
                    elif target_page_ref.machine >= total_pages:
                        status = "broken-page"
                        # User sees 1-based, e.g., "Page 101 out of range (1-100)"
                        reason = f"Page {target_page_ref.human} out of range (1–{total_pages})"

                    # 4. Case: Perfect Match
                    else:
                        status = "valid"
                        reason = f"Page {target_page_ref.human} within range (1–{total_pages})"

                except (ValueError, TypeError):
                    status = "broken-page"
                    reason = f"Invalid page value: {dest_page_raw}"

                except (ValueError, TypeError):
                    status = "broken-page"
                    reason = f"Invalid page value: {dest_page_raw}"

            elif dest_page_raw is None:
                status = "no-destinstion-page"
                reason = "No destination page resolved"

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
        try:
            # Coerce to int; we expect 0-based index from the engine
            # In the context of the ing Map, -1 acts as a "Sentinel Value." It represents a state that is strictly outside the "Machine" range
            target_page_raw = int(entry.get("target_page", -1))
            target_page_ref = PageRef.from_index(int(target_page_raw))

            status = "valid"
            reason = ""

            # 1. Check for negative indices (anything below our START_INDEX)
            if target_page_ref.machine < START_INDEX:
                status = "broken-page"
                broken_page_count += 1
                # User sees Page 0 or lower as the problem
                reason = f"TOC targets invalid page number: {target_page_ref.human}"

            # 2. Case: total_pages is unknown
            elif total_pages is None:
                status = "unknown-reasonableness"
                unknown_reasonableness_count += 1
                reason = f"Page {target_page_ref.human} unknown (could not verify total pages)"

            # 3. Case: Out of range (Upper Bound)
            # Index 100 in a 100-page doc (total_pages=100) is out of bounds
            elif target_page_ref.machine >= total_pages:
                status = "broken-page"
                broken_page_count += 1
                reason = f"TOC targets page {target_page_ref.human} (out of 1–{total_pages})"

            # 4. Valid Case
            else:
                status = "valid"
                valid_count += 1
                # We skip issues.append for valid TOC entries to keep the issues list clean
                continue

        except (ValueError, TypeError):
            status = "broken-page"
            broken_page_count += 1
            reason = f"Invalid page reference: {entry.get('target_page')}"

        # Only reaches here if status is not "valid" (because of 'continue' above)
        issues.append({
            "type": "TOC Entry",
            "title": entry.get("title", "Untitled"),
            "level": entry.get("level", 0),
            "target_page": target_page_ref.machine, # Stored as 0-indexed for data consistency
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

        log("\n")
        log("=" * SEP_COUNT)
        log("## Validation Results")
        log("=" * SEP_COUNT)
        log(f"PDF Path = {get_friendly_path(pdf_path)}")
        log(f"Total items checked: {summary_stats['total_checked']}")
        log(f"✅ Valid: {summary_stats['valid']}")
        #log(f"✅ Valid: {summary_stats['valid']}")
        #log(f"✅ Valid: {summary_stats['valid']}")
        log(f"🌐 Web Addresses (Ping: OFF): {summary_stats['unknown-web']}")
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
        
        results = dict()
        results["validation_summary_str"] = validation_buffer_str
        results["validation_summary_lines"] = validation_buffer
        return results
    
    results_validation = generate_validation_summary_txt_buffer(summary_stats, issues, pdf_path)

    validation_results = {
        "pdf_path" : pdf_path,
        "summary-stats": summary_stats,
        "issues": issues,
        #"summary-txt": results_validation["validation_summary_str"],
        "summary-lines": results_validation["validation_summary_lines"],
        "total_pages": total_pages
    }

    return validation_results
