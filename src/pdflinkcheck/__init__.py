#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# src/pdflinkcheck/__init__.py
"""
pdflinkcheck - A PDF Link Checker

Source code: https://github.com
"""
from __future__ import annotations
import os

from pdflinkcheck._version import __version__

# 1. Clean public facing mapping
__all__ = [
    "__version__",
    "run_report",
    "analyze_pdf_pymupdf",
    "analyze_pdf_pypdf",
    "analyze_pdf_pdfium",
    "__pdflinkcheck_gui_easteregg_enabled__", # Re-added for REPL discovery
]

def _check_easteregg_env() -> bool:
    """Helper to dynamically read environment state at call-time."""
    env_flag = os.environ.get('PDFLINKCHECK_GUI_EASTEREGG', '').strip().lower()
    return env_flag in ('true', '1', 'yes', 'on')

# 2. Fully dynamic attribute routing
def __getattr__(name: str):
    if name == "run_report":
        from pdflinkcheck.report import run_report_and_call_exports
        return run_report_and_call_exports

    if name == "analyze_pdf_pypdf":
        try:
            from pdflinkcheck.analysis_pypdf import analyze_pdf
            return analyze_pdf
        except ImportError:
            raise ImportError("pypdf engine is not installed. Install pypdf to enable pypdf support.")

    if name == "analyze_pdf_pymupdf":
        try:
            from pdflinkcheck.analysis_pymupdf import analyze_pdf
            return analyze_pdf
        except ImportError:
            raise ImportError("PyMuPDF engine is not installed. Install with the [pymupdf] extra to enable support.")

    if name == "analyze_pdf_pdfium":
        try:
            from pdflinkcheck.analysis_pdfium import analyze_pdf
            return analyze_pdf
        except ImportError:
            raise ImportError("PDFium engine is not installed. Install with the [pdfium] extra to enable support.")

    # Dynamic boolean evaluation for the breadcrumb attribute
    if name == "__pdflinkcheck_gui_easteregg_enabled__":
        return _check_easteregg_env()

    # Dynamic lookups for the GUI function invocation
    if name == "start_gui":
        def _missing_gui(*args, **kwargs):
            raise RuntimeError(
                "start_gui requires pyhabitat and a Tkinter-capable environment"
            )
        _missing_gui.__name__ = "start_gui"
        _missing_gui.__doc__ = (
            "GUI support is unavailable in this environment."
        )
        if _check_easteregg_env():
            try:
                import pyhabitat
                if pyhabitat.tkinter_is_available():
                    from pdflinkcheck.gui import start_gui
                    return start_gui
            except ImportError:
                pass

            return _missing_gui
            
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    

# 3. Dynamic introspection reflecting runtime changes
def __dir__():
    exported = list(__all__)
    if _check_easteregg_env():
        exported.append("start_gui")
    
    return sorted(exported + [
        "__builtins__", "__cached__", "__doc__", "__file__",
        "__getattr__", "__dir__", "__loader__", "__name__", "__package__", "__path__", "__spec__"
    ])
