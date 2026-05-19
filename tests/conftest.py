# tests/conftest.py
import pathlib
import pytest

def get_all_test_pdfs():
    """Locate the cloned asset repository relative to this codebase."""
    # Look for the standard sibling directory layout
    local_path = pathlib.Path(__file__).resolve().parents[2] / "public-documents" / "assets" / "pdf"
    
    if local_path.exists() and local_path.is_dir():
        return list(local_path.glob("*.pdf"))
        
    return []

def pytest_generate_tests(metafunc):
    """Dynamically parameterize tests based on files discovered on disk."""
    if "pdf_path" in metafunc.fixturenames:
        pdf_paths = get_all_test_pdfs()
        
        if not pdf_paths:
            # Provide actionable feedback to the engineer instead of hanging on a git pull
            raise FileNotFoundError(
                "\n\n[pdflinkcheck Test Suite Error]: Test assets folder not found!\n"
                "Please clone the public-documents repo as a sibling directory to this repository:\n"
                "git clone git@github.com:City-of-Memphis-Wastewater/public-documents.git ../public-documents\n"
            )
            
        ids = [p.name for p in pdf_paths]
        metafunc.parametrize("pdf_path", pdf_paths, ids=ids)
