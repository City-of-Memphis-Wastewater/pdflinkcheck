import sys
from pathlib import Path
from typing import List, Dict
import re

import xlsxwriter

from pdflinkcheck.report import run_report_and_call_exports, get_first_pdf_in_cwd

# ----- Helper Functions -----

def is_temp_pdf(pdf_name: str) -> bool:
    """Detect likely temp or unstable PDF filenames."""
    temp_patterns = [r'^tmp', r'^~', r'^[0-9a-fA-F]{8,}-', r'^temp']
    return any(re.match(pat, pdf_name) for pat in temp_patterns)


def convert_goto_link(link: Dict, pdf_name: str) -> str:
    """Convert internal GoTo link into a hyperlink usable in Excel."""
    page_index = link.get('destination_page')
    if page_index is None:
        return pdf_name
    human_page = page_index + 1  # Convert 0-index page to 1-index
    return f'{pdf_name}#page={human_page}'


def prepare_links_by_type(report: Dict) -> Dict[str, List[Dict]]:
    """Prepare links grouped by type for separate Excel sheets."""
    pdf_name = report['metadata']['file_overview']['pdf_name']

    if is_temp_pdf(pdf_name):
        raise ValueError(
            f"PDF filename '{pdf_name}' looks like a temporary or unstable file. Provide a stable filename."
        )

    grouped_links = {'Internal GoTo': [], 'External URI': [], 'Other': []}

    all_links = (
        report['data'].get('internal_links', [])
        + report['data'].get('external_links', [])
        + report['data'].get('other_links', [])
    )

    for link in all_links:
        link_type = link.get('type', 'Unknown')
        anchor_text = link.get('link_text', 'N/A')

        if link_type in ('Internal (GoTo/Dest)', 'Internal (Resolved Action)'):
            url = convert_goto_link(link, pdf_name)
            grouped_links['Internal GoTo'].append({
                'page': link.get('page', 'N/A'),
                'anchor_text': anchor_text,
                'hyperlink': url
            })
        elif link_type == 'External (URI)':
            url = link.get('url') or link.get('remote_file') or link.get('target') or ''
            grouped_links['External URI'].append({
                'page': link.get('page', 'N/A'),
                'anchor_text': anchor_text,
                'hyperlink': url
            })
        else:
            url = link.get('url') or link.get('remote_file') or link.get('target') or ''
            grouped_links['Other'].append({
                'page': link.get('page', 'N/A'),
                'anchor_text': anchor_text,
                'hyperlink': url
            })

    return grouped_links


def export_links_to_xlsx(grouped_links: Dict[str, List[Dict]], output_file: str):
    """Export grouped links into separate sheets in an XLSX workbook using xlsxwriter."""
    workbook = xlsxwriter.Workbook(output_file)
    hyperlink_format = workbook.add_format({'font_color': 'blue', 'underline': 1})
    header_format = workbook.add_format({'bold': True})

    for sheet_name, links in grouped_links.items():
        worksheet = workbook.add_worksheet(sheet_name)

        # Write headers
        headers = ['Page', 'Anchor Text', 'Hyperlink']
        for col_num, header in enumerate(headers):
            worksheet.write(0, col_num, header, header_format)

        # Write data rows
        for row_num, link in enumerate(links, start=1):
            worksheet.write(row_num, 0, link['page'])
            worksheet.write(row_num, 1, link['anchor_text'])
            if link['hyperlink']:
                worksheet.write_url(
                    row_num, 2, link['hyperlink'], hyperlink_format, string=link['hyperlink']
                )

        # Auto-size columns approximately
        for col_num in range(3):
            max_len = max(
                [len(str(link.get(headers[col_num].lower().replace(' ', '_'), ''))) for link in links]
                + [len(headers[col_num])]
            )
            worksheet.set_column(col_num, col_num, max_len + 5)

    workbook.close()
    print(f"✅ XLSX exported successfully to {output_file}")


# ----- Main / Proof-of-Concept -----

def main():
    pdf_path = get_first_pdf_in_cwd()
    if not pdf_path:
        print("No PDF found in current directory.")
        sys.exit(1)

    report = run_report_and_call_exports(pdf_path=pdf_path, export_format='', print_bool=False)

    try:
        grouped_links = prepare_links_by_type(report)
    except ValueError as e:
        print(f"⚠️  {e}")
        sys.exit(1)

    output_file = Path(pdf_path).with_suffix('.links.xlsx')
    export_links_to_xlsx(grouped_links, str(output_file))


if __name__ == "__main__":
    main()
