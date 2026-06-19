#!/usr/bin/env python3 
# SPDX-License-Identifier: MIT
# src/pdflinkcheck/validate.py
from __future__ import annotations
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple, NamedTuple
import re
from enum import Enum


from pdflinkcheck.io import get_friendly_path
from pdflinkcheck.helpers import PageRef, LinkType, PageValidationResult
from .ping import is_valid_web_url, ping_url


logger = logging.getLogger(__name__)

SEP_COUNT = 28
START_INDEX = 0  
ISSUES_SHOWN = 25

# Standard RFC 5322 compliant lightweight email pattern
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

class LinkValidationResult(NamedTuple):
    status: MetricKey
    reason: str

class ValidationStatus(Enum):
    VALID = 'valid'
    BROKEN = 'broken'
    UNKNOWN = 'unknown' 
    REASONABLE = 'reasonable'
    FORBIDDEN = 'forbidden'
    MISSING = 'missing'

#class LinkSource(Enum):
#    redundant for the helpers.LinkType class

class MetricKey(str, Enum):
    # Valid categories
    TOTAL_FOUND = 'total-found'
    INTERNAL_PAGE_JUMP_VALID = 'internal-page-jump-valid'
    TOC_JUMP_VALID = 'toc-jump-valid'
    FILE_TARGET_VALID = 'file-target-valid'
    WEB_PING_VALID = 'web-ping-valid'
    LAUNCH_TARGET_VALID = 'launch-target-valid'
    
    # Unknowns/Warnings
    UNKNOWN_WEB_NOT_PINGED = 'unknown-web-not-pinged'
    INTERNAL_JUMP_UNKNOWN_REASONABLENESS = 'internal-jump-unknown-reasonableness'
    TOC_JUMP_UNKNOWN_REASONABLENESS = 'toc-jump-unknown-reasonableness'
    EMAIL_ADDRESS_REASONABLE = 'email-address-reasonable'
    LAUNCH_TARGET_EXECUTABLE = 'launch-target-executable'
    EXTERNAL_URI_FORBIDDEN = 'external-uri-forbidden'
    TELEPHONE_NUMBER = 'telephone-number'
    UNKNOWN_LINK = 'unknown-link'
    
    # Broken categories
    INTERNAL_PAGE_JUMP_BROKEN = 'internal-page-jump-broken'
    FILE_TARGET_BROKEN = 'file-target-broken'
    LAUNCH_TARGET_BROKEN = 'launch-target-broken'
    TOC_JUMP_BROKEN = 'toc-jump-broken'
    TOC_JUMP_NO_DESTINATION_PAGE = 'toc-jump-no-destination-page'
    INTERNAL_JUMP_NO_DESTINATION_PAGE = 'internal-jump-no-destination-page'
    WEB_PING_FAIL = 'web-ping-fail'
    UNKNOWN_WEB_URL_MISSING = 'unknown-web-url-missing'
    EMAIL_ADDRESS_BROKEN = 'email-address-broken'

# A simple, centralized set of all Enum members that constitute structural failures
ISSUE_METRICS = {
    MetricKey.INTERNAL_PAGE_JUMP_BROKEN, 
    MetricKey.FILE_TARGET_BROKEN,
    MetricKey.INTERNAL_JUMP_NO_DESTINATION_PAGE, 
    MetricKey.WEB_PING_FAIL,
    MetricKey.TOC_JUMP_BROKEN, 
    MetricKey.TOC_JUMP_NO_DESTINATION_PAGE,
    MetricKey.TOC_JUMP_UNKNOWN_REASONABLENESS, 
    MetricKey.EMAIL_ADDRESS_BROKEN,
    MetricKey.UNKNOWN_WEB_URL_MISSING, 
    MetricKey.INTERNAL_JUMP_UNKNOWN_REASONABLENESS,
    MetricKey.UNKNOWN_LINK, 
    MetricKey.EXTERNAL_URI_FORBIDDEN,
    MetricKey.LAUNCH_TARGET_BROKEN, 
    MetricKey.LAUNCH_TARGET_EXECUTABLE
}

def make_fresh_stats(total_found):
    # do i want these to use value or the raw LinkValidationResult?
    stats_fresh = {
        MetricKey.TOTAL_FOUND: total_found,
        MetricKey.INTERNAL_PAGE_JUMP_VALID: 0,
        MetricKey.TOC_JUMP_VALID: 0,
        MetricKey.TOC_JUMP_BROKEN: 0,
        MetricKey.TOC_JUMP_NO_DESTINATION_PAGE: 0,
        MetricKey.TOC_JUMP_UNKNOWN_REASONABLENESS: 0,
        MetricKey.FILE_TARGET_VALID: 0,
        MetricKey.WEB_PING_VALID: 0,
        MetricKey.EMAIL_ADDRESS_REASONABLE: 0,
        MetricKey.EMAIL_ADDRESS_BROKEN: 0,
        MetricKey.UNKNOWN_WEB_URL_MISSING: 0,
        MetricKey.UNKNOWN_WEB_NOT_PINGED: 0,
        MetricKey.INTERNAL_JUMP_UNKNOWN_REASONABLENESS: 0,
        MetricKey.UNKNOWN_LINK: 0,
        MetricKey.INTERNAL_PAGE_JUMP_BROKEN: 0,
        MetricKey.FILE_TARGET_BROKEN: 0,
        MetricKey.EXTERNAL_URI_FORBIDDEN: 0,
        MetricKey.INTERNAL_JUMP_NO_DESTINATION_PAGE: 0,
        MetricKey.WEB_PING_FAIL: 0,
        MetricKey.TELEPHONE_NUMBER: 0,
        MetricKey.LAUNCH_TARGET_VALID: 0,
        MetricKey.LAUNCH_TARGET_BROKEN: 0,
        MetricKey.LAUNCH_TARGET_EXECUTABLE: 0
    }
    return stats_fresh

class ValidationCounter:
    """Manages validation metric accumulation and categorization safely."""
    def __init__(self, total_found: int):
        self.stats = make_fresh_stats(total_found) # ultimately plain text, does get passed into generate_validation_summary_txt_buffer()
        self.issues: List[Dict[str, Any]] = []

    def record(self, linkvalres: LinkValidationResult, link_payload: Dict[str, Any]):
        """Increments stats and tracks failures in the issues registry."""
        status = linkvalres.status
        if status in self.stats:
            self.stats[status] += 1
            
        if status in ISSUE_METRICS:
            self.issues.append(link_payload)


# =====================================================================
# Validation Sub-Engines, with LinkValidationResult returns
# =====================================================================

def _check_internal_jump(dest_page: Any, total_pages: int | None) -> LinkValidationResult:
    """Evaluates index targeting against document thresholds using PageRef translation."""
    if dest_page is None:
        return LinkValidationResult(
            status=MetricKey.INTERNAL_JUMP_NO_DESTINATION_PAGE, 
            reason="No destination page resolved"
        )

    # 1. Determine the structural classification
    try:
        page_ref = PageRef.from_index(int(dest_page))
        if page_ref.machine < START_INDEX:
            result_status = PageValidationResult.NEGATIVE
        elif total_pages is None:
            result_status = PageValidationResult.UNKNOWN
        elif page_ref.machine >= total_pages:
            result_status = PageValidationResult.HIGH
        else:
            result_status = PageValidationResult.VALID
    except (ValueError, TypeError):
        result_status = PageValidationResult.INVALID

    # 2. Map structural state cleanly to the reporting payload
    if result_status == PageValidationResult.NEGATIVE:
        return LinkValidationResult(
            status=MetricKey.INTERNAL_PAGE_JUMP_BROKEN, 
            reason=f"Target page {page_ref.human} is invalid (negative index)."
        )
    elif result_status == PageValidationResult.UNKNOWN:
        return LinkValidationResult(
            status=MetricKey.INTERNAL_JUMP_UNKNOWN_REASONABLENESS, 
            reason=f"Page {page_ref.human} seems reasonable, but total page count is unavailable."
        )
    elif result_status == PageValidationResult.HIGH:
        return LinkValidationResult(
            status=MetricKey.INTERNAL_PAGE_JUMP_BROKEN, 
            reason=f"Page {page_ref.human} out of range (1–{total_pages})"
        )
    elif result_status == PageValidationResult.INVALID:
        return LinkValidationResult(
            status=MetricKey.INTERNAL_PAGE_JUMP_BROKEN, 
            reason=f"Invalid page value: {dest_page}"
        )
    
    return LinkValidationResult(
        status=MetricKey.INTERNAL_PAGE_JUMP_VALID, 
        reason=f"Page {page_ref.human} within range (1–{total_pages})"
    )

def _check_toc_jump(dest_page: Any, total_pages: int | None) -> LinkValidationResult:
    """Evaluates index targeting against document thresholds using PageRef translation."""
    if dest_page is None:
        return LinkValidationResult(
            status = MetricKey.TOC_JUMP_NO_DESTINATION_PAGE, 
            reason = "No destination page resolved"
        )

    # 1. Determine the structural classification
    try:
        page_ref = PageRef.from_index(int(dest_page))
        if page_ref.machine < START_INDEX:
            result_status = PageValidationResult.NEGATIVE
        elif total_pages is None:
            result_status = PageValidationResult.UNKNOWN
        elif page_ref.machine >= total_pages:
            result_status = PageValidationResult.HIGH
        else:
            result_status = PageValidationResult.VALID
    except (ValueError, TypeError):
        result_status = PageValidationResult.INVALID

    # 2. Map structural state cleanly to the reporting payload
    if result_status == PageValidationResult.NEGATIVE:
        return LinkValidationResult(
            status = MetricKey.TOC_JUMP_BROKEN, 
            reason = f"Target page {page_ref.human} is invalid (negative index)."
        )
    elif result_status == PageValidationResult.UNKNOWN:
        return LinkValidationResult(
            status = MetricKey.TOC_JUMP_UNKNOWN_REASONABLENESS, 
            reason = f"Page {page_ref.human} seems reasonable, but total page count is unavailable."
        )
    elif result_status == PageValidationResult.HIGH:
        human_label = page_ref.human
        reason = f"TOC targets page {human_label} (out of 1–{total_pages if total_pages else 'Unknown'})"
        return LinkValidationResult(
            status = MetricKey.TOC_JUMP_BROKEN, 
            reason = reason
        )
    elif result_status == PageValidationResult.INVALID:
        return LinkValidationResult(
            status = MetricKey.TOC_JUMP_BROKEN, 
            reason = f"Invalid page value: {dest_page}"
        )

    return LinkValidationResult(
        status = MetricKey.TOC_JUMP_VALID, 
        reason = f"Page {page_ref.human} within range (1–{total_pages})"
    )


def _check_remote_file(remote_file: str | None, pdf_dir: Path) -> LinkValidationResult:
    """Evaluates OS filesystem presence for local cross-document references."""
    if not remote_file:
        return LinkValidationResult(
            status = MetricKey.FILE_TARGET_BROKEN, 
            reason = "Missing remote file name"
        )
    
    target_path = (pdf_dir / remote_file).resolve() # assumes that the remote files has a relative path
    # we should possibly address the case where the remote_file is deemde to be a complete full filepath, if this is within the bounds of expectation. 
    if target_path.exists() and target_path.is_file():
        return LinkValidationResult(
            status = MetricKey.FILE_TARGET_VALID, 
            reason = f"Found: {target_path.name}"
        )
    
    return LinkValidationResult(
        status = MetricKey.FILE_TARGET_BROKEN, 
        reason = f"File not found: {remote_file}"
    )


def _check_email_protocol(url_str: str) -> LinkValidationResult:
    """
    Parses and validates mailto protocol strings for syntax correctness.
    
    Extracts the core address by stripping the protocol prefix and any 
    trailing query parameters (e.g., ?subject=, ?body=).
    """
    # Strip the 'mailto:' prefix (case-insensitive slice)
    email_part = url_str[7:].split('?')[0].strip()
    
    if not email_part:
        return LinkValidationResult(
            status = MetricKey.EMAIL_ADDRESS_BROKEN, 
            reason = "Malformed mailto link: Missing email address"
        )
        
    if EMAIL_REGEX.match(email_part):
        return LinkValidationResult(
            status = MetricKey.EMAIL_ADDRESS_REASONABLE, 
            reason = "Valid email address syntax"
        )
        
    return LinkValidationResult(
        status = MetricKey.EMAIL_ADDRESS_BROKEN, 
        reason = f"Invalid email address formatting: '{email_part}'"
    )

def _check_external_uri(url: str | None, check_external: bool) -> LinkValidationResult:
    """Evaluates network URI structure and processes pings if allowed."""
    if not url:
        return LinkValidationResult(
            status = MetricKey.UNKNOWN_WEB_URL_MISSING, 
            reason = "External link (no URL provided)"
        )
        
    url_stripped = url.strip()
    url_lower = url_stripped.lower()
    
    # Handle known local/application protocols natively, probably in a nested way, rather than this flat way
    if url_lower.startswith("mailto:"):
        return _check_email_protocol(url_stripped)

    if url_lower.startswith("tel:"):
        return LinkValidationResult(
            status = MetricKey.TELEPHONE_NUMBER, 
            reason = f"Phone number not checked."
        )
        
    if url_lower.startswith(("file:", "mhtml:")):
        #return MetricKey.FILE_TARGET_BROKEN, f"Forbidden local hardcoded reference: {url}"
        reason = f"Forbidden local hardcoded reference."
        return LinkValidationResult(
            status = MetricKey.EXTERNAL_URI_FORBIDDEN,
            reason = reason
        )
        
    # Proceed to web link verification
    if not is_valid_web_url(url):
        return LinkValidationResult(
            status = MetricKey.WEB_PING_FAIL, 
            reason = "Malformed or unparseable URL syntax"
        )

    if not check_external:
        return LinkValidationResult(
            status = MetricKey.UNKNOWN_WEB_NOT_PINGED, 
            reason = "External link (no network check)"
        )

    ping_res = ping_url(url)
    logger.debug(f"Ping result: {ping_res}")
    
    if ping_res.success:
        return LinkValidationResult(
            status = MetricKey.WEB_PING_VALID, 
            reason = f"HTTP {ping_res.status_code}: {ping_res.reason}"
        )
    
    reason = f"HTTP {ping_res.status_code}: {ping_res.reason}" if ping_res.status_code else ping_res.reason
    return LinkValidationResult(
        status = MetricKey.WEB_PING_FAIL, 
        reason = reason
    )

def _check_launch_link(launch_target: str | None) -> LinkValidationResult:
    """
    Evaluates PDF Launch actions for structural safety and path validity.
    
    """
    if not launch_target:
        return LinkValidationResult(
            status = MetricKey.LAUNCH_TARGET_BROKEN, 
            reason = "Malformed Launch link: Missing executable or file target"
        )

    target_clean = launch_target.strip()
    target_lower = target_clean.lower()

    # 1. Guard against high-risk executable or script types immediately
    dangerous_extensions = (
        ".exe", ".bat", ".cmd", ".sh", ".bash", ".vbs", 
        ".js", ".scr", ".pif", ".msi", ".com", ".ps1"
    )
    if target_lower.endswith(dangerous_extensions) or any(f" {ext}" in target_lower for ext in dangerous_extensions):
        return LinkValidationResult(
            status = MetricKey.LAUNCH_TARGET_EXECUTABLE, 
            reason = f"High-risk executable Launch path blocked: {target_clean}"
        )

    # 3. Path verification (Treating the target as an explicit local file asset dependency)
    try:
        target_path = Path(target_clean)
        # Note: Launch paths can be absolute or relative. Adjust base resolution as required by engine context
        if target_path.exists() and target_path.is_file():
            return LinkValidationResult(
                status = MetricKey.LAUNCH_TARGET_VALID, 
                reason = f"Verified local target: {target_path.name}"
            )
        return LinkValidationResult(
            status = MetricKey.LAUNCH_TARGET_BROKEN, 
            reason = f"Launch target file not found: {target_clean}"
        )
    except Exception as e:
        return LinkValidationResult(
            status = MetricKey.LAUNCH_TARGET_BROKEN, 
            reason = f"Unparseable Launch path sequence: {str(e)}"
        )

def _check_unknown_link() -> LinkValidationResult:
    return LinkValidationResult(
        status = MetricKey.UNKNOWN_LINK, 
        reason = "Other/unsupported link type"
    )
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
    metadata = report_results.get("summary_metadata", {})
    
    external_links = data.get("external_links", [])
    internal_links = data.get("internal_links", [])
    all_links = external_links + internal_links
    
    toc = data.get("toc", [])

    total_pages = metadata.get("file_overview", {}).get("total_pages", None)

    total_found = (
        metadata.get("link_counts", {}).get("total_links_count", 0) + 
        metadata.get("link_counts", {}).get("toc_entry_count", 0)
    )

    if not all_links and not toc:
        return {
            "pdf_path": pdf_path,
            "summary-stats": {MetricKey.TOTAL_FOUND.value: 0}, 
            "issues": [], 
            "summary-lines": [],
            "total_pages": total_pages
        }

    pdf_dir = Path(pdf_path).parent
    tracker = ValidationCounter(total_found)

    # Dispatch Pass 1: Standard Document Annotations
    for link in all_links:
        details =  link.get('details',{})
        link_type = details.get('link_type')
        if link_type in (LinkType.INTERNAL_GOTO.value, LinkType.INTERNAL_RESOLVED.value): 
            linkvalres = _check_internal_jump(details.get("destination_page"), total_pages)
        elif link_type == LinkType.REMOTE_GOTOR.value:
            linkvalres = _check_remote_file(details.get("remote_file"), pdf_dir) 
        elif link_type == LinkType.EXTERNAL.value:
            linkvalres = _check_external_uri(details.get("url"), check_external) 
        elif link_type == LinkType.LAUNCH.value:
            linkvalres = _check_launch_link(details.get("file"))
        else:
            linkvalres = _check_unknown_link()
        
        # Update the original dict context in place for JSON reporting
        #print(f"{linkvalres=}")
        #print(f"{linkvalres.status=}")
        #link = link.copy()
        link["target_validation"] = {"status": linkvalres.status.value, "reason": linkvalres.reason}

        # Construct a clean, normalized payload flat at the top level
        issue_payload = {
            "GUID": link.get("GUID"),
            "link_type": link_type or "Link",
            "anchor_text": details.get("anchor_text") or link.get("anchor_text") or "—",
            "target": (
                details.get("url") or 
                details.get("remote_file") or 
                (f"Page {details.get('destination_page')}" if details.get('destination_page') is not None else None) or
                "N/A"
            ),
            "target_validation": link["target_validation"]
        }
        tracker.record(linkvalres, issue_payload) # NOTDONE

    # Dispatch Pass 2: Table of Contents Bookmarks
    for entry in toc:
        raw_page = entry.get("target_page", -1)

        linkvalres = _check_toc_jump(raw_page, total_pages) # NOTDONE

        entry["target_validation"] = {"status": linkvalres.status.value, "reason": linkvalres.reason}

        issue_payload = {
            "GUID": entry.get("GUID"),
            "link_type": "TOC Entry",
            "anchor_text": entry.get("title", "Untitled"),
            "target": f"Page {raw_page}" if raw_page != -1 else "N/A",
            "target_validation": entry["target_validation"]
        }
        tracker.record(linkvalres, issue_payload) # NOTDONE

    '''
    # ---
        # Update the original dict context in place for JSON reporting
        #link = link.copy()
        link["target_validation"] = {"status": linkvalres.status.value, "reason": linkvalres.reason}

        # Construct a clean, normalized payload flat at the top level
        if True:
            issue_payload = {
                "GUID": link.get("GUID"),
                "link_type": link_type or "Link",
                "anchor_text": details.get("anchor_text") or link.get("anchor_text") or "—",
                "validation_issue": link["target_validation"] 
            }
        else:
            issue_payload = {
                "GUID": link.get("GUID")
            }
        tracker.record(linkvalres, issue_payload) # NOTDONE

    # Dispatch Pass 2: Table of Contents Bookmarks
    for entry in toc:
        raw_page = entry.get("target_page", -1)

        linkvalres = _check_toc_jump(raw_page, total_pages) # NOTDONE

        # Update the original dict context in place for JSON reporting
        entry["target_validation"] = {"status": linkvalres.status.value, "reason": linkvalres.reason}

        if True:
            issue_payload = {
                "GUID": entry.get("GUID"),
                "link_type": "TOC Entry",
                "anchor_text": entry.get("title", "Untitled"),
                "target": f"Page {raw_page}" if raw_page != -1 else "N/A",
                "validation_issue": entry["target_validation"] 
            }
        else:
            issue_payload = {
                "GUID": entry.get("GUID"),
            }
        tracker.record(linkvalres, issue_payload) # NOTDONE
    # ---'''

    report_buffer = generate_validation_summary_txt_buffer(data,tracker.stats, tracker.issues, pdf_path, check_external)
    # you actually don't want to pass self.issues here.

    return {
        "pdf_path": pdf_path,
        #"summary-stats": tracker.stats,
        "summary-stats": {k.value: v for k, v in tracker.stats.items()},
        "issues": tracker.issues,
        "summary-lines": report_buffer["validation_summary_lines"],
        "total_pages": total_pages
    }

def build_flat_guid_registry(data):
    # Build a flat, O(1) lookup map of the nested data structures by GUID
    guid_registry = {}
    
    for item in data.get("external_links", []):
        if "GUID" in item:
            guid_registry[item["GUID"]] = item
            
    for item in data.get("internal_links", []):
        if "GUID" in item:
            guid_registry[item["GUID"]] = item
            
    for item in data.get("toc", []):
        if "GUID" in item:
            guid_registry[item["GUID"]] = item
    return guid_registry

def generate_validation_summary_txt_buffer(data,summary_stats, issues, pdf_path, check_external):
    """Generates structural text layers from state engine snapshots."""
    buf = []
    
    buf.append("\n" + "=" * SEP_COUNT)
    buf.append("## Validation Results")
    buf.append("=" * SEP_COUNT)
    buf.append(f"PDF Path = {get_friendly_path(pdf_path)}")
    buf.append(f"Ping: {check_external}")
    buf.append(f"Total items found: {summary_stats[MetricKey.TOTAL_FOUND]}")
    buf.append(f"✅ TOC Page Jumps Valid: {summary_stats[MetricKey.TOC_JUMP_VALID]}")
    buf.append(f"✅ Internal Page Jumps Valid: {summary_stats[MetricKey.INTERNAL_PAGE_JUMP_VALID]}")
    buf.append(f"✅ File Targets Valid: {summary_stats[MetricKey.FILE_TARGET_VALID]}")
    buf.append(f"✅ Launch Targets Valid: {summary_stats[MetricKey.LAUNCH_TARGET_VALID]}")
    buf.append(f"✅ Web Addresses Valid: {summary_stats[MetricKey.WEB_PING_VALID]}")
    buf.append(f"🌐 Web Addresses Not Checked: {summary_stats[MetricKey.UNKNOWN_WEB_NOT_PINGED]}")
    buf.append(f"⚠️ Unknown Page Reasonableness: {summary_stats[MetricKey.INTERNAL_JUMP_UNKNOWN_REASONABLENESS]}")
    buf.append(f"⚠️ TOC Unknown Reasonableness: {summary_stats[MetricKey.TOC_JUMP_UNKNOWN_REASONABLENESS]}")
    buf.append(f"⚠️ Email Addresses Reasonable But Not Checked: {summary_stats[MetricKey.EMAIL_ADDRESS_REASONABLE]}")
    buf.append(f"⚠️ Forbidden Local Executable Launches: {summary_stats[MetricKey.LAUNCH_TARGET_EXECUTABLE]}")
    buf.append(f"⚠️ Unsupported URL File Links: {summary_stats[MetricKey.EXTERNAL_URI_FORBIDDEN]}")
    buf.append(f"⚠️ Unsupported Telephone Numbers: {summary_stats[MetricKey.TELEPHONE_NUMBER]}")
    buf.append(f"⚠️ Unsupported Other PDF Links: {summary_stats[MetricKey.UNKNOWN_LINK]}")
    buf.append(f"❌ Broken Page Reference: {summary_stats[MetricKey.INTERNAL_PAGE_JUMP_BROKEN]}")
    buf.append(f"❌ Broken File Targets: {summary_stats[MetricKey.FILE_TARGET_BROKEN]}")
    buf.append(f"❌ Broken Launch Targets: {summary_stats[MetricKey.LAUNCH_TARGET_BROKEN]}")
    buf.append(f"❌ TOC Page Jumps Broken: {summary_stats[MetricKey.TOC_JUMP_BROKEN]}")
    buf.append(f"❌ TOC Page Jumps Not Resolved: {summary_stats[MetricKey.TOC_JUMP_NO_DESTINATION_PAGE]}")
    buf.append(f"❌ Internal Page Jumps Not Resolved: {summary_stats[MetricKey.INTERNAL_JUMP_NO_DESTINATION_PAGE]}")
    buf.append(f"❌ Web Address Pings Failed: {summary_stats[MetricKey.WEB_PING_FAIL]}")
    buf.append(f"❌ Web Addresses Missing: {summary_stats[MetricKey.UNKNOWN_WEB_URL_MISSING]}")
    buf.append(f"❌ Email Addresses Broken: {summary_stats[MetricKey.EMAIL_ADDRESS_BROKEN]}")
    
    buf.append("=" * SEP_COUNT)

    if issues:

        guid_registry = build_flat_guid_registry(data)

        buf.append("\n## Issues Found")
        # Added explicit "Target/URL" column asset header
        buf.append("{:<5} | {:<12} | {:<25} | {:<30} | {}".format("Idx", "Type", "Anchor Text", "Target / URL", "Problem"))
        buf.append("-" * (SEP_COUNT + 50)) # Extended divider line for width matching
            
        for i, issue in enumerate(issues[:ISSUES_SHOWN], 1):
            
            guid = issue.get("GUID")
            itype = issue.get("link_type", "Link")
            
            # Resolve the original reference object from our flat map
            source_item = guid_registry.get(guid, {})
            details = source_item.get("details", {})
            
            #referenced_link_or_toc = cross_reference_guid_to_get_instance(data,issue) # what if instead we just feed inthe complete data structure into this function. it is currenly unknown to this function
            # the reference problem with checking the GUID is you also have to use the linktype to check the nested 'toc' or the 'external_links' or the 'internal_links' structures.
            itype = issue.get('link_type', "Link") # check the GUID, i think, not the issue dict, so that the issue doesn't need to carry redundant information
            
            # Extract anchor visual text or fallback onto title
            itext = issue.get("anchor_text", "—") # check the GUID, i think, not the issue dict
            itext = (itext[:22] + "...") if len(itext) > 25 else itext
            
            # Extract actual underlying execution target string
            #itarget = (issue.get("url") or issue.get("remote_file") or f"Page {issue.get('target_page', 'N/A')}")
            itarget = issue.get("target", "N/A") # check the GUID, i think, not the issue dict
            itarget = (itarget[:27] + "...") if len(itarget) > 30 else itarget
            
            #ireason = issue["target_validation"]["reason"]
            ireason = issue.get("target_validation", {}).get("reason", "Unknown issue") # check the GUID, i think, not the issue dict
            ireason = ireason.encode('utf-8').decode('utf-8')
            buf.append("{:<5} | {:<12} | {:<25} | {:<30} | {}".format(i, itype, itext, itarget, ireason))
            
        if len(issues) > ISSUES_SHOWN:
            buf.append(f"... and {len(issues) - ISSUES_SHOWN} more issues")
    elif summary_stats.get(MetricKey.TOTAL_FOUND, 0) == 0:
        buf.append("\nStatus: No items were discovered to evaluate.")
    else:
        buf.append("\nSuccess: Document structural references verified perfectly!")

    return {
        "validation_summary_str": "\n".join(buf),
        "validation_summary_lines": buf
    }

