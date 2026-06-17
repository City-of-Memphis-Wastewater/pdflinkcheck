#!/usr/bin/env python3 
# SPDX-License-Identifier: MIT
# src/pdflinkcheck/validate.py
from __future__ import annotations
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple
import re

from pdflinkcheck.io import get_friendly_path
from pdflinkcheck.helpers import PageRef 
from .ping import is_valid_web_url, ping_url

logger = logging.getLogger(__name__)

SEP_COUNT = 28
START_INDEX = 0  

# Standard RFC 5322 compliant lightweight email pattern
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

def make_fresh_stats(total_found):
    stats_fresh = {
        "total-found": total_found,
        "internal-page-jump-valid": 0,
        "toc-jump-valid": 0,
        "file-target-valid": 0,
        "web-ping-valid": 0,
        "unknown-web": 0,
        "internal-jump-unknown-reasonableness": 0,
        "unknown-link": 0,
        "internal-page-jump-broken": 0,
        "file-target-broken": 0,
        "internal-jump-no-destination-page": 0,
        "web-ping-fail": 0
    }
    return stats_fresh

class ValidationCounter:
    """Manages validation metric accumulation and categorization safely."""
    def __init__(self, total_found: int):
        self.stats = make_fresh_stats(total_found)
        self.issues: List[Dict[str, Any]] = []

    def record(self, status: str, link_payload: Dict[str, Any]):
        """Increments stats and tracks failures in the issues registry."""
        if status in self.stats:
            self.stats[status] += 1
            
        if status in ("internal-page-jump-broken", "file-target-broken", "internal-jump-no-destination-page", "web-ping-fail"):
            self.issues.append(link_payload)


# =====================================================================
# Pure Validation Sub-Engines
# =====================================================================

def _check_internal_jump(dest_page: Any, total_pages: int | None) -> Tuple[str, str]:
    """Evaluates index targeting against document thresholds using PageRef translation."""
    if dest_page is None:
        return "internal-jump-no-destination-page", "No destination page resolved"
    try:
        page_ref = PageRef.from_index(int(dest_page))
        
        if page_ref.machine < START_INDEX:
            return "internal-page-jump-broken", f"Target page {page_ref.human} is invalid (negative index)."
            
        if total_pages is None:
            return "internal-jump-unknown-reasonableness", f"Page {page_ref.human} seems reasonable, but total page count is unavailable."
            
        if page_ref.machine >= total_pages:
            return "internal-page-jump-broken", f"Page {page_ref.human} out of range (1–{total_pages})"
            
        return "internal-page-jump-valid", f"Page {page_ref.human} within range (1–{total_pages})"
    except (ValueError, TypeError):
        return "internal-page-jump-broken", f"Invalid page value: {dest_page}"


def _check_remote_file(remote_file: str | None, pdf_dir: Path) -> Tuple[str, str]:
    """Evaluates OS filesystem presence for local cross-document references."""
    if not remote_file:
        return "file-target-broken", "Missing remote file name"
    
    target_path = (pdf_dir / remote_file).resolve()
    if target_path.exists() and target_path.is_file():
        return "file-target-valid", f"Found: {target_path.name}"
    return "file-target-broken", f"File not found: {remote_file}"


def _check_email_protocol(url_str: str) -> Tuple[str, str]:
    """
    Parses and validates mailto protocol strings for syntax correctness.
    
    Extracts the core address by stripping the protocol prefix and any 
    trailing query parameters (e.g., ?subject=, ?body=).
    """
    # Strip the 'mailto:' prefix (case-insensitive slice)
    email_part = url_str[7:].split('?')[0].strip()
    
    if not email_part:
        return "web-ping-fail", "Malformed mailto link: Missing email address"
        
    if EMAIL_REGEX.match(email_part):
        return "web-ping-valid", "Valid email address syntax"
        
    return "web-ping-fail", f"Invalid email address formatting: '{email_part}'"

def _check_external_uri(url: str | None, check_external: bool) -> Tuple[str, str]:
    """Evaluates network URI structure and processes pings if allowed."""
    if not url:
        return "unknown-web", "External link (no URL provided)"
        
    url_stripped = url.strip()
    url_lower = url_stripped.lower()
    
    # Handle known local/application protocols natively
    if url_lower.startswith("mailto:"):
        return _check_email_protocol(url_stripped)
    
    if url_lower.startswith(("file:", "mhtml:")):
        return "file-target-broken", f"Forbidden local hardcoded reference: {url}"

    # Proceed to web link verification
    if not is_valid_web_url(url):
        return "web-ping-fail", "Malformed or unparseable URL syntax"

    if not check_external:
        return "unknown-web", "External link (no network check)"

    ping_res = ping_url(url)
    logger.debug(f"Ping result: {ping_res}")
    
    if ping_res.success:
        return "web-ping-valid", f"HTTP {ping_res.status_code}: {ping_res.reason}"
    
    reason = f"HTTP {ping_res.status_code}: {ping_res.reason}" if ping_res.status_code else ping_res.reason
    return "web-ping-fail", reason


# =====================================================================
# Main Coordinator & Orchestration Boundary
# =====================================================================

def run_validation(
    report_results: Dict[str, Any],
    pdf_path: str,
    check_external: bool = False
) -> Dict[str, Any]:
    """Coordinates deep asset testing across document boundaries."""
    data = report_results.get("data", {})
    metadata = report_results.get("metadata", {})
    all_links = data.get("external_links", []) + data.get("internal_links", [])
    toc = data.get("toc", [])
    total_pages = metadata.get("file_overview", {}).get("total_pages", None)

    total_found = (
        metadata.get("link_counts", {}).get("total_links_count", 0) + 
        metadata.get("link_counts", {}).get("toc_entry_count", 0)
    )

    if not all_links and not toc:
        return {
            "pdf_path": pdf_path,
            "summary-stats": {"total-found": 0}, 
            "issues": [], 
            "summary-lines": [],
            "total_pages": total_pages
        }

    pdf_dir = Path(pdf_path).parent
    tracker = ValidationCounter(total_found)

    # Dispatch Pass 1: Standard Document Annotations
    for link in all_links:
        link_type = link.get("type")
        
        if link_type in ("Internal (GoTo/Dest)", "Internal (Resolved Action)"):
            status, reason = _check_internal_jump(link.get("destination_page"), total_pages)
        elif link_type == "Remote (GoToR)":
            status, reason = _check_remote_file(link.get("remote_file"), pdf_dir)
        elif link_type == "External (URI)":
            status, reason = _check_external_uri(link.get("url"), check_external)
        else:
            status, reason = "unknown-link", "Other/unsupported link type"

        validated_link = link.copy()
        validated_link["validation"] = {"status": status, "reason": reason}
        tracker.record(status, validated_link)

    # Dispatch Pass 2: Table of Contents Bookmarks
    for entry in toc:
        raw_page = entry.get("target_page", -1)
        status, reason = _check_internal_jump(raw_page, total_pages)
        
        if status == "internal-page-jump-valid":
            status = "toc-jump-valid"
        elif status == "internal-page-jump-broken":
            try:
                human_label = PageRef.from_index(int(raw_page)).human
            except (ValueError, TypeError):
                human_label = str(raw_page)
            reason = f"TOC targets page {human_label} (out of 1–{total_pages if total_pages else 'Unknown'})"

        validated_toc = {
            "type": "TOC Entry",
            "title": entry.get("title", "Untitled"),
            "level": entry.get("level", 0),
            "target_page": raw_page,
            "validation": {"status": status, "reason": reason}
        }
        tracker.record(status, validated_toc)

    report_buffer = generate_validation_summary_txt_buffer(tracker.stats, tracker.issues, pdf_path, check_external)

    return {
        "pdf_path": pdf_path,
        "summary-stats": tracker.stats,
        "issues": tracker.issues,
        "summary-lines": report_buffer["validation_summary_lines"],
        "total_pages": total_pages
    }


def generate_validation_summary_txt_buffer(summary_stats, issues, pdf_path, check_external):
    """Generates structural text layers from state engine snapshots."""
    buf = []
    
    buf.append("\n" + "=" * SEP_COUNT)
    buf.append("## Validation Results")
    buf.append("=" * SEP_COUNT)
    buf.append(f"PDF Path = {get_friendly_path(pdf_path)}")
    buf.append(f"Total items found: {summary_stats['total-found']}")
    buf.append(f"✅ TOC Page Jumps Valid: {summary_stats['toc-jump-valid']}")
    buf.append(f"✅ Internal Page Jumps Valid: {summary_stats['internal-page-jump-valid']}")
    buf.append(f"✅ File Targets Valid: {summary_stats['file-target-valid']}")
    buf.append(f"✅ Web Addresses Valid: {summary_stats['web-ping-valid']}")
    buf.append(f"🌐 Web Addresses Not Checked (Ping: {check_external}): {summary_stats['unknown-web']}")
    buf.append(f"⚠️ Unknown Page Reasonableness: {summary_stats['internal-jump-unknown-reasonableness']}")
    buf.append(f"⚠️ Unsupported PDF Links: {summary_stats['unknown-link']}")
    buf.append(f"❌ Broken Page Reference: {summary_stats['internal-page-jump-broken']}")
    buf.append(f"❌ Broken File Targets: {summary_stats['file-target-broken']}")
    buf.append(f"❌ No Destination Resolved: {summary_stats['internal-jump-no-destination-page']}")
    buf.append(f"❌ Web Addresses Broken: {summary_stats['web-ping-fail']}")
    buf.append("=" * SEP_COUNT)

    if issues:
        buf.append("\n## Issues Found")
        # Added explicit "Target/URL" column asset header
        buf.append("{:<5} | {:<12} | {:<25} | {:<30} | {}".format("Idx", "Type", "Anchor Text", "Target / URL", "Problem"))
        buf.append("-" * (SEP_COUNT + 50)) # Extended divider line for width matching
        
        for i, issue in enumerate(issues[:25], 1):
            itype = issue.get("type", "Link")
            
            # Extract anchor visual text or fallback onto title
            itext = (issue.get("link_text") or issue.get("title") or "—")
            itext = (itext[:22] + "...") if len(itext) > 25 else itext
            
            # Extract actual underlying execution target string
            itarget = (issue.get("url") or issue.get("remote_file") or f"Page {issue.get('target_page', 'N/A')}")
            itarget = (itarget[:27] + "...") if len(itarget) > 30 else itarget
            
            ireason = issue["validation"]["reason"]
            buf.append("{:<5} | {:<12} | {:<25} | {:<30} | {}".format(i, itype, itext, itarget, ireason))
            
        if len(issues) > 25:
            buf.append(f"... and {len(issues) - 25} more issues")
    elif summary_stats.get('total-found', 0) == 0:
        buf.append("\nStatus: No items were discovered to evaluate.")
    else:
        buf.append("\nSuccess: Document structural references verified perfectly!")

    return {
        "validation_summary_str": "\n".join(buf),
        "validation_summary_lines": buf
    }
