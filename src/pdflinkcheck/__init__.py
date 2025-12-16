# src/pdflinkcheck/__init__.py
# License information
"""
pdflinkcheck - A PDF Link Checker
Copyright (C) 2025 George Clayton Bennett
source code: https://github.com/City-of-Memphis-Wastewater/pdflinkcheck/

This program is free software: You can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.                    

The AGPL3+ is required because it uses PyMuPDF, which is licensed under the AGPL3.
"""
# Library functions
from pdflinkcheck.analyze import run_analysis, extract_links, extract_toc

# For the kids. This is what I wanted when learning Python in a mysterious new REPL.
# Is this Pythonic? No. Oh well. PEP 8, PEP 20.
import os
flag = os.environ.get('PDFLINKCHECK_GUI_EASTEREGG', '')
pdflibkcheck_gui_lib_func_load = str(flag).strip().lower() in ('true', '1', 'yes', 'on')

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
    "start_gui" if pdflibkcheck_gui_lib_func_load else None,
]
