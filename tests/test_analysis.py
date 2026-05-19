# tests/test_analysis.py
import pathlib
import pytest
from pdflinkcheck.report import run_report_and_call_exports
from pdflinkcheck.helpers import ExportFormat, PdfEngine

# Define a clean local test artifact directory inside the repo workspace
TEST_OUTPUT_DIR = pathlib.Path(__file__).resolve().parent / "test_outputs"

def test_pdf_link_and_structure_integrity(pdf_path):
    """Iteratively analyze all discovered PDFs and verify physical report export generation."""
    assert pdf_path.exists(), f"Target test asset missing: {pdf_path}"

    # Ensure our localized test output folder exists cleanly before running
    TEST_OUTPUT_DIR.mkdir(exist_ok=True)

    # Run core orchestration engine with file exports turned ON
    report_results = run_report_and_call_exports(
        pdf_path=str(pdf_path),
        export_format= ExportFormat.NONE,
        pdf_library=PdfEngine.AUTO,       
        print_bool=False,
        concise_print=True,
        output_dir=str(TEST_OUTPUT_DIR) # Pin the destination to our isolated workspace folder
    )
    
    # 1. Structural Engine Asserts
    assert report_results is not None, f"Analysis failed to produce report dictionary for {pdf_path.name}"
    assert "data" in report_results
    assert "validation" in report_results["data"]
    
    stats = report_results["data"]["validation"]["summary-stats"]
    assert stats["total_checked"] >= 0
    assert stats["broken-page"] == 0, f"Found broken page jumps in {pdf_path.name}"
    assert stats["broken-file"] == 0, f"Found broken file references in {pdf_path.name}"

