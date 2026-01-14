#!/usr/bin/env python3 
# SPDX-License-Identifier: MIT
# src/pdflinkcheck/__init__.py
"""
pdflinkcheck - A PDF Link Checker

Source code: https://github.com/City-of-Memphis-Wastewater/pdflinkcheck/

"""
from __future__ import annotations
import os as _os

# Library functions
#from pdflinkcheck import dev

# Lazy-loaded orchestrator
def run_report(pdf_path: str, export_format: str = "JSON", pdf_library: str = "auto", print_bool: bool = True):
    """
    Run a full link check report on a PDF file.
    
    Args:
        pdf_path: Path to the PDF file.
        export_format: "JSON", "TXT", or both (e.g., "JSON,TXT").
        pdf_library: "auto", "pdfium", "pymupdf", or "pypdf".
        print_bool: If True, prints the overview to stdout.
    """
    from pdflinkcheck.report import run_report_and_call_exports as _run
    return _run(pdf_path=pdf_path, export_format=export_format, pdf_library=pdf_library, print_bool=print_bool)

# --- pypdf ---
def analyze_pdf_pypdf(path):
    try:
        from pdflinkcheck.analysis_pypdf import analyze_pdf as _analyze
    except ImportError:
        raise ImportError(
            "pypdf engine is not installed. "
            "Install pypdf to enable pypdf support."
        )
    return _analyze(path)
analyze_pdf_pypdf.__doc__ = (
    "Analyze a PDF using the lightweight pypdf engine and return a normalized dictionary.\n\n"
    "See pdflinkcheck.analyze_pypdf for full details."
)

# --- PyMuPDF ---
def analyze_pdf_pymupdf(path):
    try:
        from pdflinkcheck.analysis_pymupdf import analyze_pdf as _analyze
    except ImportError:
        raise ImportError(
            "PyMuPDF engine is not installed. "
            "Install with the [pymupdf] extra to enable PyMuPDF support."
        )
    return _analyze(path)
analyze_pdf_pymupdf.__doc__ = (
    "Analyze a PDF using the AGPL3-licensed PyMuPDF engine and return a normalized dictionary.\n\n"
    "See pdflinkcheck.analyze_pymupdf for full details."
)


# --- PDFium ---

def analyze_pdf_pdfium(path):
    try:
        from pdflinkcheck.analysis_pdfium import analyze_pdf as _analyze
    except ImportError:
        raise ImportError(
            "PDFium engine is not installed. "
            "Install with the [pdfium] extra to enable pdfium support."
        )
    return _analyze(path)
analyze_pdf_pdfium.__doc__ = (
    "Analyze a PDF using the PDFium engine and return a normalized dictionary.\n\n"
    "See pdflinkcheck.analyze_pdfium for full details."
)

# -----------------------------
# GUI easter egg
# -----------------------------
# For the kids. This is what I wanted when learning Python in a mysterious new REPL.
# Is this Pythonic? No. Oh well. PEP 8, PEP 20.
# Why is this not Pythonic? Devs expect no side effects when importing library functions.
# What is a side effect?
_gui_easteregg_env_flag = _os.environ.get('PDFLINKCHECK_GUI_EASTEREGG', '')
_load_gui_func = str(_gui_easteregg_env_flag).strip().lower() in ('true', '1', 'yes', 'on')
if _load_gui_func:
    try:
        print("Easter egg, attemping.")
        import pyhabitat as _pyhabitat # pyhabitat is a dependency of this package already
        print(f"pyhabitat.tkinter_is_available() = {_pyhabitat.tkinter_is_available()}")
        if _pyhabitat.tkinter_is_available():
            from pdflinkcheck.gui import start_gui
            print("Success: pdflinkcheck.start_gui() function loaded as top-level pmlibrary function.")
    except ImportError:
        # Optional: log or ignore silently
        print("start_gui() not imported")



# Breadcrumbs, for stumbling upon.
if _load_gui_func:
    __pdflinkcheck_gui_easteregg_enabled__ = True
else:
    __pdflinkcheck_gui_easteregg_enabled__ = False


# -----------------------------
# Public API
# -----------------------------
# Define __all__ such that the library functions are self documenting.
__all__ = [
    "run_report",
    "analyze_pdf_pymupdf",
    "analyze_pdf_pypdf", 
    "analyze_pdf_pdfium",     
]

# Handle the Easter Egg export
if _load_gui_func:
    __all__.append("start_gui")

# Handle dev module if you want it public
try:
    from pdflinkcheck import dev
    __all__.append("dev")
except ImportError:
    pass

# 4. THE CLEANUP (This removes items from dir())
del _os
del _gui_easteregg_env_flag
del _load_gui_func

# Force avoid 'io' appearing, it's likely being imported, when it is imported by another package which is imported here:
#if "io" in locals(): 
#    del io
