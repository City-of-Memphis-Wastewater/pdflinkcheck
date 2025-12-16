# Library functions
from pdflinkcheck.analyze import run_analysis, extract_links, extract_toc

# For the kids. This is what I wanted when learning Python in a mysterious new REPL.

import os
flag = os.environ.get('PDFLINKCHECK_GUI_EASTEREGG', '')
pdflibkcheck_gui_lib_func_load = str(flag).strip().lower() in ('true', '1', 'yes', 'on')

if pdflibkcheck_gui_lib_func_load:
    try:
        import pyhabitat
        if pyhabitat.tkinter_is_available():
            from pdflinkcheck.gui import start_gui
    except ImportError:
        # Optional: log or ignore silently
        pass

__all__ = [
    "run_analysis",
    "extract_links",
    "extract_toc",
    "start_gui" if pdflibkcheck_gui_lib_func_load else None,
]

if pdflibkcheck_gui_lib_func_load:
    __pdflinkcheck_gui_enabled__ = True


