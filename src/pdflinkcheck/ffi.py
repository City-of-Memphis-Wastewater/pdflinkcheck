import ctypes
import json
import os
import sys
from pathlib import Path

# ------------------------------------------------------------
# Locate the Rust shared library
# ------------------------------------------------------------

def _find_rust_lib():
    """
    Search for the compiled Rust shared library in common locations.
    """
    lib_names = {
        "linux": "librust_pdflinkcheck.so",
        "darwin": "librust_pdflinkcheck.dylib",
        "win32": "rust_pdflinkcheck.dll",
    }

    platform = sys.platform
    if platform.startswith("linux"):
        target = lib_names["linux"]
    elif platform == "darwin":
        target = lib_names["darwin"]
    elif platform == "win32":
        target = lib_names["win32"]
    else:
        return None

    # Search in package directory
    here = Path(__file__).resolve().parent
    candidate = here / target
    if candidate.exists():
        return str(candidate)

    # Search in project root (editable installs)
    root_candidate = Path(__file__).resolve().parents[2] / "rust_pdflinkcheck" / "target" / "release" / target
    if root_candidate.exists():
        return str(root_candidate)

    return None


# ------------------------------------------------------------
# Load the Rust library (if available)
# ------------------------------------------------------------

_rust_lib_path = _find_rust_lib()
_rust = None

if _rust_lib_path:
    try:
        _rust = ctypes.CDLL(_rust_lib_path)
        _rust.pdflinkcheck_analyze_pdf.argtypes = [ctypes.c_char_p]
        _rust.pdflinkcheck_analyze_pdf.restype = ctypes.c_char_p

        _rust.pdflinkcheck_free_string.argtypes = [ctypes.c_char_p]
        _rust.pdflinkcheck_free_string.restype = None

    except OSError:
        _rust = None


# ------------------------------------------------------------
# Public API
# ------------------------------------------------------------

def rust_available() -> bool:
    """Return True if the Rust engine is available."""
    return _rust is not None


def analyze_pdf_rust(path: str):
    """
    Call the Rust engine. Returns a Python dict.
    Raises RuntimeError if Rust is unavailable.
    """
    if _rust is None:
        raise RuntimeError("Rust engine not available")

    path_bytes = path.encode("utf-8")
    raw = _rust.pdflinkcheck_analyze_pdf(path_bytes)

    if not raw:
        raise RuntimeError("Rust returned NULL")

    try:
        json_str = ctypes.cast(raw, ctypes.c_char_p).value.decode("utf-8")
    finally:
        _rust.pdflinkcheck_free_string(raw)

    return json.loads(json_str)
