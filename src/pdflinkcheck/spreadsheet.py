#!/usr/bin/env python3
# SPDX-License-Identifier: MIT

from __future__ import annotations
import re
from pathlib import Path
from typing import Dict, List

from openpyxl import Workbook
from openpyxl.styles import Font

from pdflinkcheck.io import PDFLINKCHECK_HOME, get_friendly_path, get_unique_human_time
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
    Convert internal GoTo link into a clickable file:// URI.
    Uses .as_uri() for robust cross-platform path encoding.
    """
    page_index = link.get('destination_page')
    
    # Path.as_uri() handles file:/// and character escaping automatically
    # This ensures it works on WSL and Windows without manual slashing
    base_uri = Path(pdf_path).absolute().as_uri()
    
    if page_index is None:
        return base_uri

    # Use PageRef with .human to ensure 1-based numbering in the URI fragment
    human_page = PageRef.from_index(int(page_index)).human
    filepath = f"{base_uri}#page={human_page}"
    
    return filepath

def prepare_links_by_type(results: Dict, pdf_path: str = "") -> Dict[str, List[Dict]]:
    """
    Groups links and TOC items into four categories.
    Watches keys closely to ensure data extraction.
    """
    payload = results.get("data", {})
    
    # WATCHING THE KEYS - Crucial for debugging payload mismatches
    #print(f"DEBUG: payload.keys() = {list(payload.keys())}")
    
    ext_links = payload.get('external_links', [])
    int_links = payload.get('internal_links', [])
    all_toc = payload.get('toc', [])

    # DEBUG COUNTS - Verifies if the loops will actually execute
    #print(f"DEBUG: len(int_links) = {len(int_links)}")
    #print(f"DEBUG: len(ext_links) = {len(ext_links)}")

    grouped = {
        'Table of Contents': [],
        'Internal Links': [],
        'External Links': [],
        'Other': []
    }

    # 1. Process TOC
    for item in all_toc:
        raw_target = item.get('target_page')
        pg_human = PageRef.from_index(int(raw_target)).human if isinstance(raw_target, (int, float)) else "N/A"
        grouped['Table of Contents'].append({
            'col1': item.get('level', 1),
            'col2': sanitize_excel_text(item.get('title', 'Untitled')),
            'col3': pg_human
        })

    # 2. Process Internal Links
    for link in int_links:
        anchor = sanitize_excel_text(link.get('link_text', 'Link (No Text)'))
        raw_src = link.get('page')
        pg_src = PageRef.from_index(int(raw_src)).human if isinstance(raw_src, (int, float)) else "N/A"
        
        raw_dst = link.get('destination_page')
        pg_dst = PageRef.from_index(int(raw_dst)).human if isinstance(raw_dst, (int, float)) else "N/A"
        
        # Calls convert_goto_link (contains the filepath print)
        jump_url = convert_goto_link(link, pdf_path) if pdf_path else f"Page {pg_dst}"

        grouped['Internal Links'].append({
            'col1': pg_src, 
            'col2': pg_dst, 
            'col3': anchor, 
            'hyperlink': jump_url 
        })

    # 3. Process External Links
    for link in ext_links:
        anchor = sanitize_excel_text(link.get('link_text', 'Link (No Text)'))
        raw_src = link.get('page')
        pg_src = PageRef.from_index(int(raw_src)).human if isinstance(raw_src, (int, float)) else "N/A"
        
        url = link.get('url') or ''
        l_type = str(link.get('type', '')).lower()
        
        if "external" in l_type or "uri" in l_type:
            grouped['External Links'].append({
                'col1': pg_src, 'col2': anchor, 'col3': url, 'hyperlink': url
            })
        else:
            grouped['Other'].append({
                'col1': pg_src, 'col2': anchor, 'col3': url, 'hyperlink': url
            })

    return grouped

def _export_links_to_xlsx(grouped_links: Dict[str, List[Dict]], output_file: Path) -> bool:
    """
    Physical writer. Uses optimized sampling for column widths.
    """
    wb = Workbook()
    wb.properties.creator = "pdflinkcheck"  # optional
    wb.properties.title = "PDF Link Report"

    # Add this to force UTF-8 BOM on save (helps Excel with Unicode)
    from openpyxl.utils import quote_sheetname  # not needed, but for completeness
    # No extra code needed — openpyxl saves UTF-8 by default, but BOM helps Excel
    
    sheet_configs = [
        ('Table of Contents', ['Level', 'Title', 'Target Page']),
        ('Internal Links',   ['Source Page', 'Dest Page', 'Anchor Text', 'Jump Link']),
        ('External Links',   ['Source Page', 'Anchor Text', 'URL', 'External Link']),
        ('Other',            ['Source Page', 'Anchor Text', 'Reference', 'Link'])
    ]

    sheets_actually_written = 0

    for sheet_name, headers in sheet_configs:
        rows = grouped_links.get(sheet_name, [])
        if not rows:
            continue
            
        ws = wb.create_sheet(sheet_name)
        sheets_actually_written += 1
        ws.append(headers)
        
        # Bold headers
        for cell in ws[1]:
            cell.font = Font(bold=True)

        for item in rows:
            row_data = [item['col1'], item['col2'], item['col3']]
            if 'hyperlink' in item:
                row_data.append(item['hyperlink'])
            
            ws.append(row_data)
            
            if 'hyperlink' in item and item['hyperlink'] != 'N/A':
                last_cell = ws.cell(row=ws.max_row, column=len(row_data))
                last_cell.hyperlink = item['hyperlink']
                last_cell.style = 'Hyperlink'
        try:
            # Force UTF-8 BOM for Excel compatibility with Unicode paths
            for row_idx, item in enumerate(rows, start=2):
                for col_idx, value in enumerate([item['col1'], item['col2'], item['col3']], start=1):
                    cell = ws.cell(row=row_idx, column=col_idx, value=str(value))
                    # Ensure Excel treats as text
                    if isinstance(value, str) and (value.startswith('http') or value.startswith('mhtml') or value.startswith('mailto')):
                        cell.number_format = '@'  # text format
        except:
            print("this block is in the wrong spot or it otherwose problematic")
        # COLUMN AUTO-FIT: Sample first 100 rows for speed on large PDFs
        sample_rows = list(ws.iter_rows(min_row=1, max_row=100, values_only=True))
        if sample_rows:
            for i, column_cells in enumerate(zip(*sample_rows)):
                column_letter = ws.cell(row=1, column=i+1).column_letter
                max_len = 0
                for val in column_cells:
                    if val:
                        max_len = max(max_len, len(str(val)))
                ws.column_dimensions[column_letter].width = min(max_len + 2, 70)

    # Remove the default empty sheet created by Workbook()
    if 'Sheet' in wb.sheetnames:
        wb.remove(wb['Sheet'])

    if sheets_actually_written == 0:
        return False

    wb.save(output_file)
    print(f"sheets_actually_written = {sheets_actually_written}")
    print(f"XLSX exported successfully to {get_friendly_path(output_file)}")
    return True

def export_report_links_to_xlsx(results: Dict, output_dir: Path = None) -> Path:
    """
    Main entry point for spreadsheet generation.
    Prioritizes 'source_path' to handle server-side uploads correctly.
    """
    output_dir = output_dir or PDFLINKCHECK_HOME
    
    metadata = results.get("metadata", {})
    file_ov = metadata.get("file_overview", {})
    
    # 1. Prioritize source_path (Original filename from server upload)
    # 2. Fallback to pdf_path (Local CLI path)
    # 3. Fallback to processing_path (The actual temp file used)
    pdf_path = (
        file_ov.get("source_path") or 
        file_ov.get("pdf_path") or 
        file_ov.get("processing_path") or 
        ""
    )
    
    # DEBUG: Crucial to see which path we finally settled on
    #print(f"DEBUG: XLSX Path Resolution: '{pdf_path}'")

    grouped_links = prepare_links_by_type(results, pdf_path=pdf_path)

    total_entries = sum(len(v) for v in grouped_links.values())
    if total_entries == 0:
        return None
    
    pdf_name = file_ov.get("pdf_name") or file_ov.get("source_path") or "file"
    pdf_stem = Path(pdf_name).stem
    lib_suffix = f"_{metadata.get('library_used')}" if metadata.get('library_used') else ""

    timestamp = get_unique_human_time()
    output_file = output_dir / f"{pdf_stem}{lib_suffix}_{timestamp}_report.xlsx"

    if _export_links_to_xlsx(grouped_links, output_file):
        return output_file
    return None
