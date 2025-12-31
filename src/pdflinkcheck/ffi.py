# src/pdflinkcheck/ffi.py
from functools import cache
import ctypes
import json
from pathlib import Path
import pyhabitat 
import os

from pdflinkcheck.helpers import PageRef

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

def _load_rust():
    print("[!] Rust engine is disabled in pdflinkcheck v1.2.2. "
          "Install `pdflinkcheck-rust` in v1.2.3+ to enable Rust support.")
    return None

@cache
def _load_rust_onhold():
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
    """
    Temporarily disable Rust engine for v1.2.2.
    Users will get a friendly message if they try to use it.
    """
    return False
    
def rust_available_onhold():
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
    """
    Analyze a PDF using the Rust engine (via FFI) and return a normalized
    Python dictionary containing links and table-of-contents (TOC) data.

    The returned dictionary has the structure:
        {
            "links": [...],  # List of link dicts, fully normalized
            "toc": [...]     # List of TOC entries, fully normalized
        }

    Normalization includes:
      - Page numbers start as 0-based Rust indexing and continue to be Pythonically 0-based.
      - Internal GoTo destinations resolved to PageRef.machine values.
      - External URI links classified and structured consistently.
      - TOC entries with numeric target pages and proper levels.

    This function abstracts away all raw Rust indexing and JSON quirks, 
    providing a ready-to-use Python-friendly data structure.

    Parameters:
        pdf_path (str): Path to the PDF file to analyze.

    Returns:
        dict: Normalized analysis data containing 'links' and 'toc'.
    
    Raises:
        RuntimeError: If the Rust engine is unavailable or fails to analyze.
    """
    rust_data = _run_rust_analysis(pdf_path) or {"links": [], "toc": []}

    extracted_links = rust_data.get("links", [])
    structural_toc = rust_data.get("toc", [])
    extracted_links = rust_normalize_extracted_links(extracted_links)
    structural_toc = rust_normalize_structural_toc(structural_toc)
    
    # Put humoty dumpty back together again
    rust_data["links"] = extracted_links
    rust_data["toc"] = structural_toc

    return rust_data

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

def rust_normalize_structural_toc(structural_toc):

    # TOC: Rust already provides flat list with correct level and 0-indexed target_page (as json value)
    # Unwrap the json value to int
    for entry in structural_toc:
        if isinstance(entry['target_page'], dict) and '$serde_json::private::Number' in entry['target_page']:
            # If it serialized as raw number object (rare), handle it
            entry['target_page'] = int(list(entry['target_page'].values())[0])
        elif isinstance(entry['target_page'], (int, float)):
            entry['target_page'] = int(entry['target_page'])
        # Ensure it's int for PageRef later

    return structural_toc

def rust_normalize_extracted_links(extracted_links):
    # RUST ENGINE NORMALIZATION
    external_uri_links = []
    goto_links = []  # Unresolved or resolved GoTo

    for link in extracted_links:
        kind = link.get("action_kind")
        # Source page: Rust uses 0-indexed 'page'
        raw_src = link.get("page", 0)
        src_ref = PageRef.from_index(raw_src)
        link['page'] = src_ref.machine  # Keep machine (0-indexed) for internal use

        if kind == "URI":
            link['type'] = 'External (URI)'
            link['target'] = link.get("url") or "Unknown URI"
            external_uri_links.append(link)

        elif kind == "GoTo" or kind == "Other":  # Treat Other as potential internal if dest exists
            link['type'] = 'Internal (GoTo/Dest)'
            raw_target = link.get("destination_page")
            if raw_target is not None:
                ref = PageRef.from_index(int(raw_target))
                link['destination_page'] = ref.machine
                link['target'] = ref.machine
            else:
                link['destination_page'] = None
                link['target'] = "Unresolved"
            goto_links.append(link)

        else:
            # Fallback for unexpected kinds
            link['type'] = 'Other'
            goto_links.append(link)  # Conservative

    # Rebuild extracted_links for consistency (though not strictly needed)
    extracted_links = external_uri_links + goto_links
    return extracted_links
