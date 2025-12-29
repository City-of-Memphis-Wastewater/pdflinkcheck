from functools import cache
import ctypes
import json
from pathlib import Path

try:
    import pyhabitat as habitat
except Exception:
    habitat = None


def _should_attempt_rust():
    # Termux: never load Rust/pdfium
    if habitat and habitat.platform.is_termux():
        return False

    # Android: same story
    if habitat and habitat.platform.is_android():
        return False

    # Headless CI: skip Rust/pdfium
    if habitat and habitat.is_headless():
        return False

    return True


def _find_rust_lib():
    if not _should_attempt_rust():
        return None

    lib_names = {
        "linux": "librust_pdflinkcheck.so",
        "darwin": "librust_pdflinkcheck.dylib",
        "win32": "rust_pdflinkcheck.dll",
    }

    import sys
    platform = sys.platform

    if platform.startswith("linux"):
        target = lib_names["linux"]
    elif platform == "darwin":
        target = lib_names["darwin"]
    elif platform == "win32":
        target = lib_names["win32"]
    else:
        return None

    here = Path(__file__).resolve().parent
    data_dir = here / "data"

    # Check data dir first (for distributed packages)
    candidate = data_dir / target
    if candidate.exists():
        return str(candidate)
        
    candidate = here / target
    if candidate.exists():
        return str(candidate)

    root_candidate = (
        Path(__file__).resolve().parents[2]
        / "rust_pdflinkcheck"
        / "target"
        / "release"
        / target
    )
    if root_candidate.exists():
        return str(root_candidate)

    return None


@cache
def _load_rust():
    path = _find_rust_lib()
    if not path:
        return None

    try:
        lib = ctypes.CDLL(path)
        lib.pdflinkcheck_analyze_pdf.argtypes = [ctypes.c_char_p]
        # Use void_p so we keep the raw address for freeing later
        lib.pdflinkcheck_analyze_pdf.restype = ctypes.c_void_p 
        
        lib.pdflinkcheck_free_string.argtypes = [ctypes.c_void_p]
        lib.pdflinkcheck_free_string.restype = None
        return lib
    except OSError:
        return None

def rust_available():
    return _load_rust() is not None


def analyze_pdf_rust(path: str):
    lib = _load_rust()
    if lib is None:
        raise RuntimeError("Rust engine not available")

    # Get the raw pointer address
    ptr = lib.pdflinkcheck_analyze_pdf(path.encode("utf-8"))
    if not ptr:
        raise RuntimeError("Rust returned NULL")

    try:
        # Manually extract the string from the pointer address
        json_str = ctypes.string_at(ptr).decode("utf-8")
        return json.loads(json_str)
    finally:
        # Now we can safely free the pointer address
        lib.pdflinkcheck_free_string(ptr)
        
