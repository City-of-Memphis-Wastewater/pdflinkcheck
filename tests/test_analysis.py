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
        #export_format="JSON,TXT,XLSX",       # Force generation of json, txt, and xlsx formats
        export_format= ExportFormat.ALL,
        pdf_library=PdfEngine.AUTO,       # Use standard pure-Python parser
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

    # 2. Physical File Export Verification Asserts
    # Extract the base name stem without the .pdf extension to predict the exported filenames
    base_stem = pdf_path.stem
    
    generated_files = list(TEST_OUTPUT_DIR.glob(f"*{base_stem}*"))
    
    assert len(generated_files) > 0, f"Engine failed to write physical export artifacts for {pdf_path.name} to disk."
    
    # Verify the specific key report types are physically present in the folder
    extensions_found = {f.suffix for f in generated_files}
    assert ".json" in extensions_found, f"Missing JSON export artifact for {pdf_path.name}"
    assert ".txt" in extensions_found, f"Missing TXT data summary for {pdf_path.name}"
