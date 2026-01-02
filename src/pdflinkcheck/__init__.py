#!/usr/bin/env python3 
# SPDX-License-Identifier: MIT
# src/pdflinkcheck/__init__.py
"""
pdflinkcheck - A PDF Link Checker

Source code: https://github.com/City-of-Memphis-Wastewater/pdflinkcheck/

"""
import os as _os

# Library functions
#from pdflinkcheck import dev

# lazy loaded  library functions
def run_report_and_call_exports(*args, **kwargs):
    from pdflinkcheck.report import run_report_and_call_exports as _run
    return _run(*args, **kwargs)

# --- pypdf ---
def extract_links_pypdf(*args, **kwargs):
    from pdflinkcheck.analysis_pypdf import extract_links_pypdf as _extract
    return _extract(*args, **kwargs)

def extract_toc_pypdf(*args, **kwargs):
    from pdflinkcheck.analysis_pypdf import extract_toc_pypdf as _extract
    return _extract(*args, **kwargs)

# --- PyMuPDF ---
def extract_links_pymupdf(*args, **kwargs):
    try:
        from pdflinkcheck.analysis_pymupdf import extract_links_pymupdf as _extract
    except ImportError:
        raise ImportError(
            "PyMuPDF engine is not installed. "
            "Install pdflinkcheck with the `[full]` extra to enable PyMuPDF support:\n"
            "    pip install pdflinkcheck[full]"
        )
    return _extract(*args, **kwargs)


def extract_toc_pymupdf(*args, **kwargs):
    try:
        from pdflinkcheck.analysis_pymupdf import extract_toc_pymupdf as _extract
    except ImportError:
        raise ImportError(
            "PyMuPDF engine is not installed. "
            "Install pdflinkcheck with the `[full]` extra to enable PyMuPDF support:\n"
            "    pip install pdflinkcheck[full]"
        )
    return _extract(*args, **kwargs)



# --- Rust ---

def analyze_pdf_rust(*args, **kwargs):
    try:
        from pdflinkcheck_rust import analyze_pdf as _analyze
    except ImportError:
        raise ImportError(
            "Rust engine is not installed. "
            "Install pdflinkcheck-rust to enable Rust support."
        )
    return _analyze(*args, **kwargs)
analyze_pdf_rust.__doc__ = (
    "Analyze a PDF using the Rust engine and return a normalized dictionary.\n\n"
    "See pdflinkcheck.ffi.analyze_pdf_rust for full details."
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
        import pyhabitat as _pyhabitat # pyhabitat is a dependency of this package already
        if _pyhabitat.tkinter_is_available():
            #from pdflinkcheck.gui import start_gui
            from pdflinkcheck.gui_alt import start_gui
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
    "run_report_and_call_exports",
    "extract_links_pymupdf", 
    "extract_toc_pymupdf", 
    "extract_links_pypdf", 
    "extract_toc_pypdf", 
    "analyze_pdf_rust",     
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
