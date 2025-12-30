# src/pdflinkcheck/ffi.py
from functools import cache
import ctypes
import json
from pathlib import Path
import pyhabitat 
import os

# This is always the directory containing ffi.py
HERE = Path(__file__).resolve().parent

PACKAGE_ROOT = Path(__file__).parents[2]


def _should_attempt_rust():
    # Termux: never load Rust/pdfium
    if pyhabitat.on_termux():
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

    # 1. Check the 'data' sibling directory (Installed/Production)
    candidate = HERE / "data" / target
    if candidate.exists():
        return str(candidate)
        
    # 2. Check the current directory (Local Dev copy)
    candidate = HERE / target
    if candidate.exists():
        return str(candidate)

    # 3. Check the Rust target directory (Development/Cargo layout)
    # This goes up 3 levels from src/pdflinkcheck/ffi.py to root, 
    # then into the rust project folder
    root_candidate = HERE.parents[2] / "rust_pdflinkcheck" / "target" / "release" / target
    if root_candidate.exists():
        return str(root_candidate)

    return None


@cache
def _load_rust():
    path = _find_rust_lib()
    if not path:
        return None

    # On Linux, we can try to pre-load libpdfium or 
    # tell ctypes where to look if it's in the same folder
    if os.name == "posix":
        # This helps the Rust lib find its sibling libpdfium.so
        lib_dir = os.path.dirname(path)
        os.environ["LD_LIBRARY_PATH"] = f"{lib_dir}:{os.environ.get('LD_LIBRARY_PATH', '')}"

    try:
        lib = ctypes.CDLL(path)
        # return lib
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

def extract_links_rust(pdf_path: str):
    """Returns only the links list from the Rust engine, for consistent naming with the pypdf and pymupdf functions"""
    data = _run_rust_analysis(pdf_path)
    return data.get("links", [])

def extract_toc_rust(pdf_path: str):
    """Returns only the TOC list from the Rust engine, for consistent naming with the pypdf and pymupdf functions"""
    data = _run_rust_analysis(pdf_path)
    return data.get("toc", [])

def analyze_pdf_rust(pdf_path: str):
    return _run_rust_analysis(pdf_path)

def _run_rust_analysis_(pdf_path: str):
    """Internal helper to call the shared library and handle JSON/Memory."""
    lib = _load_rust()
    if lib is None:
        raise RuntimeError("Rust engine not available")

    # Get the raw pointer address
    ptr = lib.pdflinkcheck_analyze_pdf(pdf_path.encode("utf-8"))
    if not ptr:
        raise RuntimeError(f"Rust engine failed to analyze: {pdf_path}")

    try:
        # Manually extract the string from the pointer address
        json_str = ctypes.string_at(ptr).decode("utf-8")
        return json.loads(json_str)
    finally:
        # Now we can safely free the pointer address
        lib.pdflinkcheck_free_string(ptr)

def _run_rust_analysis(pdf_path: str):
    """
    Internal helper to call the shared library and handle JSON/Memory.
    
    This function acts as the bridge between Rust 0-based indexing and 
    and user-facing PDF page numbers (1-based).
    """
    lib = _load_rust()
    if lib is None:
        raise RuntimeError("Rust engine not available")

    # Get the raw pointer address from the C-FFI call
    ptr = lib.pdflinkcheck_analyze_pdf(pdf_path.encode("utf-8"))
    if not ptr:
        return {"links": [], "toc": []} # Return empty instead of crashing
        #raise RuntimeError(f"Rust engine failed to analyze: {pdf_path}")

    try:
        # Manually extract the string from the pointer address
        json_str = ctypes.string_at(ptr).decode("utf-8")
        raw_data = json.loads(json_str)
        return raw_data # this was missing
        
    finally:
        # Free the memory allocated by Rust
        lib.pdflinkcheck_free_string(ptr)

