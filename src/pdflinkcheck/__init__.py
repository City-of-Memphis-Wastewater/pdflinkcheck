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
import os

# Library functions
from pdflinkcheck.analyze import run_analysis, extract_links_pymupdf, extract_toc_pymupdf, extract_links_pypdf, extract_toc_pypdf
from pdflinkcheck.analyze import extract_links_pymupdf as extract_links # to expose functions referred to in README
from pdflinkcheck.analyze import extract_toc_pymupdf as extract_toc # to expose functions referred to in README


# For the kids. This is what I wanted when learning Python in a mysterious new REPL.
# Is this Pythonic? No. Oh well. PEP 8, PEP 20.
gui_easteregg_env_flag = os.environ.get('PDFLINKCHECK_GUI_EASTEREGG', '')
pdflibkcheck_gui_lib_func_load = str(gui_easteregg_env_flag).strip().lower() in ('true', '1', 'yes', 'on')
if pdflibkcheck_gui_lib_func_load:
    try:
        import pyhabitat # pyhabitat is a dependency of this package already
        if pyhabitat.tkinter_is_available():
            from pdflinkcheck.gui import start_gui
    except ImportError:
        # Optional: log or ignore silently
        pass

# Breadcrumbs, for stumbling upon.
if pdflibkcheck_gui_lib_func_load:
    __pdflinkcheck_gui_easteregg_enabled__ = True
else:
    __pdflinkcheck_gui_easteregg_enabled__ = False

# Define __all__ such that the library functions are self documenting.
__all__ = [
    "run_analysis",
    "extract_links",
    "extract_toc",
    #"extract_links_pymupdf", # redundant
    #"extract_toc_pymupdf", # redundant
    #"extract_links_pypdf", # not mature yet 
    #"extract_toc_pypdf", # not mature yet
    "start_gui" if pdflibkcheck_gui_lib_func_load else None,
]
