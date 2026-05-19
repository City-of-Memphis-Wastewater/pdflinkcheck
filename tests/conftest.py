import os
import pathlib
import pytest
import urllib.request

@pytest.fixture(scope="session")
def pdf_test_dir():
    # Look for local sibling directory first
    local_path = pathlib.Path(__file__).resolve().parents[2] / "public-documents" / "assets" / "pdf"
    
    if local_path.exists() and local_path.is_dir():
        return local_path
        
    # Fallback to a temporary cache directory for downloaded remote test assets
    cache_dir = pathlib.Path(__file__).resolve().parent / ".test_pdf_cache"
    cache_dir.mkdir(exist_ok=True)
    return cache_dir

@pytest.fixture
def get_test_pdf(pdf_test_dir):
    def _get_pdf(filename):
        target_file = pdf_test_dir / filename
        if target_file.exists():
            return target_file
            
        # Remote fallback URL
        remote_url = f"https://raw.githubusercontent.com/City-of-Memphis-Wastewater/public-documents/main/assets/pdf/{filename}"
        try:
            urllib.request.urlretrieve(remote_url, target_file)
            return target_file
        except Exception as e:
            pytest.fail(f"Could not retrieve test asset {filename} from local or remote: {e}")
            
    return _get_pdf
