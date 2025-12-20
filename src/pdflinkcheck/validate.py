# src/pdflinkcheck/validate.py

import sys
from pathlib import Path
from typing import Dict, Any

from pdflinkcheck.report import run_report

def run_validation(
    report_result: Dict[str, Any],
    pdf_path: str,
    pdf_library: str = "pypdf",
    check_external: bool = False,
    print_bool: bool = True
) -> Dict[str, Any]:
    """
    Validates links using the output from run_report().

    Args:
        report_result: The dict returned by run_report()
        pdf_path: Path to the original PDF (needed for relative file checks and page count)
        pdf_library: Engine used ("pypdf" or "pymupdf")
        check_external: Whether to validate HTTP URLs (requires network + requests)
        print_bool: Whether to print results to console

    Returns:
        Validation summary with valid/broken counts and detailed issues
    """
    data = report_result.get("data", {})
    metadata = report_result.get("metadata", {})

    all_links = data.get("external_links", []) + data.get("internal_links", [])
    toc = data.get("toc", [])

    if not all_links and not toc:
        if print_bool:
            print("No links or TOC to validate.")
        return {"summary": {"valid": 0, "broken": 0}, "issues": []}

    # Get total page count (critical for internal validation)
    try:
        if pdf_library == "pymupdf":
            import fitz
            doc = fitz.open(pdf_path)
            total_pages = doc.page_count
            doc.close()
        else:
            from pypdf import PdfReader
            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages)
    except Exception as e:
        if print_bool:
            print(f"Could not determine page count: {e}")
        total_pages = None

    pdf_dir = Path(pdf_path).parent

    issues = []
    valid_count = 0
    broken_file_count = 0
    broken_page_count = 0
    file_found_count = 0
    unknown_web_count = 0
    unknown_reasonableness_count = 0
    unknown_link_count = 0

    # Validate active links
    for i, link in enumerate(all_links):
        link_type = link.get("type")
        status = "valid"
        reason = None
        if link_type in ("Internal (GoTo/Dest)", "Internal (Resolved Action)"):
            target_page = int(link.get("destination_page"))
            print(f"{i}, {link_type}, target = {target_page}")
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
            print(f"\tstatus = {status}, reason = {reason}")

        elif link_type == "Remote (GoToR)":
            remote_file = link.get("remote_file")
            print(f"{i}, {link_type}, remote_file = {remote_file}")
            if not remote_file:
                status = "broken"
                reason = "Missing remote file name"
            else:
                target_path = (pdf_dir / remote_file).resolve()
                if target_path.exists() and target_path.is_file():
                    status = "file-found"
                    reason = f"Found: {target_path.name}"
                else:
                    status = "broken"
                    reason = f"File not found: {remote_file}"
            print(f"\tstatus = {status}, reason = {reason}")

        elif link_type == "External (URI)":
            url = link.get("url")
            print(f"{i}, {link_type}, url = {url}")
            if url and url.startswith(("http://", "https://")) and check_external:
                # Optional: add requests-based check later
                status = "unknown-web"
                reason = "External URL validation not enabled"
            else:
                status = "unknown-web"
                reason = "External link (no network check)"
            print(f"\tstatus = {status}, reason = {reason}")

        else:
            print(f"{i}")
            status = "unknown-link"
            reason = "Other/unsupported link type"
            print(f"\tstatus = {status}, reason = {reason}")

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
        elif status == "broken":
            broken_count += 1
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
                status = "broken"
                broken_count += 1
                reason = f"TOC targets negative page: {target_page}."
            elif 1 <= target_page <= total_pages:
                valid_count += 1
                continue
            else:
                status = "broken"
                reason = f"TOC targets page {page} (out of 1–{total_pages})"
                broken_count += 1
        else:
            status = "broken"
            reason = f"Invalid page: {target_page}"
            broken_count += 1

        issues.append({
            "type": "TOC Entry",
            "title": entry["title"],
            "level": entry["level"],
            "target_page": target_page,
            "validation": {"status": status, "reason": reason}
        })

    summary = {
        "total_checked": len(all_links) + len(toc),
        "valid": valid_count,
        "file-found": file_found_count,
        "broken-page": broken_page_count,
        "broken-file": broken_file_count,
        "unknown-web": unknown_web_count,
        "unknown-reasonableness": unknown_reasonableness_count,
        "unknown-link": unknown_link_count,
        #"unknown": len(all_links) + len(toc) - valid_count - broken_count # nah this is not granuar enough 
    }

    result = {
        "summary": summary,
        "issues": issues,
        "total_pages": total_pages
    }

    if print_bool:
        print("\n" + "=" * 70)
        print("## Validation Results")
        print("=" * 70)
        print(f"Total items checked: {summary['total_checked']}")
        print(f"✅ Valid:   {summary['valid']}")
        print(f"🌐 Web Addresses (Not Checked): {summary['unknown-web']}")
        print(f"⚠️ Unknown Page Reasonableness (Mising Total Page Count): {summary['unknown-reasonableness']}")
        print(f"⚠️ Unsupported PDF Links: {summary['unknown-link']}")
        print(f"❌ Broken Page Reference:  {summary['broken-page']}")
        print(f"❌ Broken File Reference:  {summary['broken-file']}")
        print("=" * 70)

        if issues:
            print("\n## Issues Found")
            print("{:<5} | {:<12} | {:<30} | {}".format("Idx", "Type", "Text", "Problem"))
            print("-" * 70)
            for i, issue in enumerate(issues[:25], 1):
                link_type = issue.get("type", "Link")
                text = issue.get("link_text", "") or issue.get("title", "") or "N/A"
                text = text[:30]
                reason = issue["validation"]["reason"]
                print("{:<5} | {:<12} | {:<30} | {}".format(i, link_type, text, reason))
            if len(issues) > 25:
                print(f"... and {len(issues) - 25} more issues")
        else:
            print("No issues found — all links and TOC entries are valid!")

    return result

if __name__ == "__main__":

    from pdflinkcheck.io import get_first_pdf_in_cwd
    pdf_path = get_first_pdf_in_cwd()
    # Run analysis first
    report = run_report(
        pdf_path=pdf_path,
        max_links=0,
        export_format="",
        pdf_library="pypdf",
        print_bool=False  # We handle printing in validation
    )

    if not report or not report.get("data"):
        print("No data extracted — nothing to validate.")
        sys.exit(1)

    # Then validate
    validation_result = run_validation(
        report_result=report,
        pdf_path=pdf_path,
        pdf_library="pypdf",
        print_bool=True
    )