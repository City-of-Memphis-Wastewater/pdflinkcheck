# tests/test_analysis_engine_matrix.py
import pathlib
import pytest
from pdflinkcheck.report import run_report_and_call_exports
from pdflinkcheck.helpers import ExportFormat, PdfEngine
from pdflinkcheck.environment import pdfium_is_available, pymupdf_is_available

TEST_OUTPUT_DIR = pathlib.Path(__file__).resolve().parent / "test_outputs"

def test_pdf_differential_engine_parity(pdf_path):
    """
    Differential Matrix Test: Keeps production code linear by handling the 
    multi-engine execution verification loop entirely within the test runner.
    """
    assert pdf_path.exists(), f"Target test asset missing: {pdf_path}"
    TEST_OUTPUT_DIR.mkdir(exist_ok=True)

    engine_telemetry = {}
    concrete_backends = [PdfEngine.PYPDF, PdfEngine.PYMUPDF, PdfEngine.PDFIUM]

    # Explicitly loop over the backends under test
    for backend in concrete_backends:

        if backend == PdfEngine.PYMUPDF and not pymupdf_is_available():
            continue

        if backend == PdfEngine.PDFIUM and not pdfium_is_available():
            continue
        report_results = run_report_and_call_exports(
            pdf_path=str(pdf_path),
            export_format=ExportFormat.NONE,  # Don't pollute disk
            pdf_library=backend,
            print_bool=False,
            concise_print=True
        )
        
        stats = report_results["data"]["validation"]["summary-stats"]
        engine_telemetry[backend.name] = stats.get("total_checked", 0)

    # Verify structural integrity across all backends
    pypdf_count = engine_telemetry["PYPDF"]
    pymupdf_count = engine_telemetry["PYMUPDF"]
    pdfium_count = engine_telemetry["PDFIUM"]

    assert pypdf_count == pymupdf_count, f"PYPDF found {pypdf_count} links, but PYMUPDF found {pymupdf_count}."
    assert pypdf_count == pdfium_count, f"PYPDF found {pypdf_count} links, but PDFIUM found {pdfium_count}."
