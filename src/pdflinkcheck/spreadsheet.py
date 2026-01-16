#!/usr/bin/env python3
# SPDX-License-Identifier: MIT

from __future__ import annotations
import sys
import re
from pathlib import Path
from typing import Dict, List

from openpyxl import Workbook
from openpyxl.styles import Font

from pdflinkcheck.io import PDFLINKCHECK_HOME, get_friendly_path, get_unique_unix_time
from pdflinkcheck.helpers import PageRef

# ----------------- Helper Functions -----------------

def is_temp_pdf(pdf_name: str) -> bool:
    """Detect likely temp or unstable PDF filenames."""
    temp_patterns = [r'^tmp', r'^~', r'^[0-9a-fA-F]{8,}-', r'^temp']
    return any(re.match(pat, pdf_name, re.IGNORECASE) for pat in temp_patterns)

def sanitize_excel_text(text: str) -> str:
    """Remove characters illegal for Excel cells."""
    if not isinstance(text, str):
        text = str(text)
    return ''.join(c for c in text if c.isprintable() or c in '\t')

def convert_goto_link(link: Dict, pdf_path: str) -> str:
    """
    Convert internal GoTo link into a clickable file:// URL.
    Excel will recognize this as a hyperlink.
    """
    page_index = link.get('destination_page')
    if page_index is None:
        return f'file://{Path(pdf_path).resolve()}'

    human_page = page_index + 1
    full_path = Path(pdf_path).resolve()
    return f'file://{full_path}#page={human_page}'

def prepare_links_by_type(report: Dict) -> Dict[str, List[Dict]]:
    from pdflinkcheck.helpers import PageRef
    
    # Initialize the four requested sheets
    grouped_links = {
        'Table of Contents': [],
        'Internal Links': [],
        'External Links': [],
        'Other': []
    }

    # 1. Process Table of Contents (TOC) - Pulled from report['toc']
    for item in report.get('toc', []):
        raw_target = item.get('target_page')
        # Use PageRef to ensure human-readable numbers (1-based)
        pg_human = PageRef.from_index(int(raw_target)).human if isinstance(raw_target, (int, float)) else "N/A"
        
        grouped_links['Table of Contents'].append({
            'level': item.get('level', 1),
            'title': sanitize_excel_text(item.get('title', 'Untitled')),
            'target_page': pg_human
        })

    # 2. Process All Links - Pulled from report['links']
    for link in report.get('links', []):
        link_type = link.get('type', 'Unknown')
        anchor_text = sanitize_excel_text(link.get('link_text', 'Link (No Text)'))
        
        raw_src = link.get('page')
        pg_num = PageRef.from_index(int(raw_src)).human if isinstance(raw_src, (int, float)) else "N/A"

        # Handle Internal
        if "Internal" in link_type or "GoTo" in link_type and "Remote" not in link_type:
            raw_dest = link.get('destination_page')
            pg_dest = PageRef.from_index(int(raw_dest)).human if isinstance(raw_dest, (int, float)) else "N/A"
            
            grouped_links['Internal Links'].append({
                'source': pg_num,
                'dest': pg_dest,
                'anchor_text': anchor_text,
                'hyperlink': f"Page {pg_dest}" 
            })

        # Handle External
        elif "External" in link_type or "URI" in link_type:
            url = link.get('url') or ''
            grouped_links['External Links'].append({
                'page': pg_num,
                'anchor_text': anchor_text,
                'hyperlink': url
            })

        # Handle Other (Remote Files, GoToR, etc.)
        else:
            other_target = link.get('remote_file') or link.get('url') or 'N/A'
            grouped_links['Other'].append({
                'page': pg_num,
                'anchor_text': anchor_text,
                'hyperlink': other_target
            })

    return grouped_links

def _export_links_to_xlsx(grouped_links: Dict[str, List[Dict]], output_file: Path):
    wb = Workbook()
    sheets_created = 0

    # Ensure sheets appear in a logical order
    order = ['Table of Contents', 'Internal Links', 'External Links', 'Other']
    
    for sheet_name in order:
        rows = grouped_links.get(sheet_name, [])
        if not rows:
            continue
            
        ws = wb.create_sheet(sheet_name)
        sheets_created += 1

        # --- Define Dynamic Headers ---
        if sheet_name == 'Table of Contents':
            headers = ['Level', 'Title', 'Target Page']
        elif sheet_name == 'Internal Links':
            headers = ['Source Page', 'Dest Page', 'Anchor Text', 'Jump to Page']
        else:
            headers = ['Source Page', 'Anchor Text', 'Hyperlink / Path']
        
        ws.append(headers)
        for cell in ws[1]:
            cell.font = Font(bold=True)

        # --- Fill Rows ---
        for entry in rows:
            if sheet_name == 'Table of Contents':
                row_data = [entry['level'], entry['title'], entry['target_page']]
            elif sheet_name == 'Internal Links':
                row_data = [entry['source'], entry['dest'], entry['anchor_text'], entry['hyperlink']]
            else:
                row_data = [entry['page'], entry['anchor_text'], entry['hyperlink']]

            ws.append(row_data)
            
            # Apply Hyperlink style to the last column (unless it's TOC which is just text)
            if sheet_name != 'Table of Contents':
                last_cell = ws.cell(row=ws.max_row, column=len(row_data))
                hlink = entry.get('hyperlink')
                if hlink and hlink != 'N/A':
                    last_cell.hyperlink = hlink
                    last_cell.style = 'Hyperlink'

        # Auto-size columns
        for col in ws.columns:
            max_length = max(len(str(cell.value)) if cell.value else 0 for cell in col)
            ws.column_dimensions[col[0].column_letter].width = min(max_length + 2, 80)

    if sheets_created == 0:
        return None

    if 'Sheet' in wb.sheetnames:
        wb.remove(wb['Sheet'])

    wb.save(output_file)
    print(f"XLSX exported successfully to {get_friendly_path(output_file)}")
    return True

def export_report_links_to_xlsx(report: Dict, output_dir: Path = None) -> Path:
    """
    Takes a report dictionary (from run_report_meat) and exports
    grouped clickable links to XLSX. Returns the XLSX path.
    """
    output_dir = output_dir or PDFLINKCHECK_HOME

    # 1. Group and process links
    grouped_links = prepare_links_by_type(report)

    # CHECK: If all groups are empty, don't bother creating the file
    if not any(grouped_links.values()):
        print("No links found. Skipping XLSX export.")
        return None
    
    # 2. Extract metadata safely
    metadata = report.get("metadata", {})
    file_overview = metadata.get("file_overview", {})

    # Fallback to "report" if pdf_name is missing
    pdf_name = file_overview.get("pdf_name", "file")
    pdf_stem = Path(pdf_name).stem

    # Only add the underscore if the library name exists
    lib = metadata.get("library_used")
    lib_suffix = f"_{lib}" if lib else ""

    timestamp = get_unique_unix_time()
    output_file = output_dir / f"{pdf_stem}{lib_suffix}_{timestamp}_report.xlsx"
    # 3. Write XLSX
    success = _export_links_to_xlsx(grouped_links, output_file)
    if success:
        return output_file
    else:
        return None
# ----------------- Main / Proof-of-Concept -----------------

def main(pdf_path: str = None):
    from pdflinkcheck.report import run_report_meat, get_first_pdf_in_cwd
    if pdf_path is None:
        pdf_path = get_first_pdf_in_cwd()
        if not pdf_path:
            print("No PDF found in current directory.")
            sys.exit(1)

    report = run_report_meat(pdf_path=pdf_path, pdf_library = "auto", print_bool=True, concise_print=True)

    export_report_links_to_xlsx(report)

if __name__ == "__main__":
    main()
