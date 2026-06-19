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
            export_format=ExportFormat.ALL,  # Don't pollute disk
            pdf_library=backend,
            print_bool=False,
            concise_print=True,
            output_dir=str(TEST_OUTPUT_DIR), # Pin the destination to our isolated workspace folder
            check_external=False
        )
        
        stats = report_results["data"]["validation_summary"]["summary-stats"]
        engine_telemetry[backend.name] = stats.get("total_checked", 0)

    # Verify structural integrity across all backends
    # Use .get() with a default fallback to avoid KeyError when an engine is skipped
    pypdf_count = engine_telemetry.get("PYPDF")
    pymupdf_count = engine_telemetry.get("PYMUPDF")
    pdfium_count = engine_telemetry.get("PDFIUM")

    # Only run comparative assertions if both engines actually executed
    if pypdf_count is not None and pymupdf_count is not None:
        assert pypdf_count == pymupdf_count, f"PYPDF found {pypdf_count} links, but PYMUPDF found {pymupdf_count}."
        
    if pypdf_count is not None and pdfium_count is not None:
            assert pdfium_count >= pypdf_count, f"PDFIUM engine degradation: found {pdfium_count}, expected at least {pypdf_count}."