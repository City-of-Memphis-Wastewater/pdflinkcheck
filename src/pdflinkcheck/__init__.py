# src/pdflinkcheck/__init__.py
"""
# License information
pdflinkcheck - A PDF Link Checker

Copyright (C) 2025 George Clayton Bennett

Source code: https://github.com/City-of-Memphis-Wastewater/pdflinkcheck/

This program is free software: You can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.                    

The AGPL3+ is required because pdflinkcheck uses PyMuPDF, which is licensed under the AGPL3.
"""
import os as _os

# Library functions
from pdflinkcheck.analyze_pymupdf import extract_links_pymupdf, extract_toc_pymupdf
from pdflinkcheck.analyze_pypdf import extract_links_pypdf, extract_toc_pypdf
from pdflinkcheck.report import run_report_and_call_exports as run_report
#from pdflinkcheck import dev

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

# Define __all__ such that the library functions are self documenting.
__all__ = [
    "run_report",
    "extract_links_pymupdf", 
    "extract_toc_pymupdf", 
    "extract_links_pypdf", 
    "extract_toc_pypdf", 
    #"start_gui" if _load_gui_func else None,
    "dev", 
]
if _load_gui_func:
    __all__.append("start_gui")

# 4. THE CLEANUP (This removes items from dir())
del _os
del _gui_easteregg_env_flag
del _load_gui_func

# Force avoid 'io' appearing, it's likely being imported, when it is imported by another package which is imported here:
#if "io" in locals(): 
#    del io
