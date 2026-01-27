#!/usr/bin/env python3 
# SPDX-License-Identifier: MIT
# pdflinkcheck/environment.py
from __future__ import annotations
from functools import cache
import subprocess
import os
import pyhabitat
"""
Environment checks.

Functions:

Examples:
- is_in_dev_environment() is used when deciding to force load src/pdflinkcheck/data/ files, when CLI docs is called, and if they are not found when called in the GUI,
- Default to pypdf at load if not pymupdf_is_available(). pymupdf_is_available() is useful for caching a common check in this codebase and setting up explicit logic rather than relying on try/except blocks in each instance. 
"""

def clear_pdf_library_caches()->None:
    """Clear every @cache used in pdflinkcheck. Future work: Call from CLI using --clear-cache"""
    pymupdf_is_available.cache_clear()
    pdfium_is_available.cache_clear()

    
@cache
def pymupdf_is_available() -> bool:
    """Check if pymupdf is available in the current local version of pdflinkcheck."""
    try:
        import fitz
        return True
    except Exception as e:
        # Fails if: the [full] group from [project.optional-dependencies] in pyrpoject.toml was not used when installing pdflink check. Like 
        # Use: `pipx install pdflinkcheck[full]` or alternative.
        #print(f"DEBUG: pymupdf check failed with error: {e}")
        return False


@cache
def pdfium_is_available() -> bool:
    """Check if pdfium2 is available in the current local version of pdflinkcheck."""
    try:
        import pypdfium2
        return True
    except Exception as e:
        # Fails if: the [full] group from [project.optional-dependencies] in pyrpoject.toml was not used when installing pdflink check. Like 
        # Use: `pipx install pdflinkcheck[pdfium]` or alternative.
        #print(f"DEBUG: pdfium check failed with error: {e}")
        return False


@cache
def is_in_dev_environment() -> bool:
    """
    Determines if the code is running in a local development context.
    Returns False if the execution is bundled, sandboxed, or lacks dev markers.
    """
    # 1. Check for 'Artifact' states. 
    # If it's a binary or managed package, it's not a dev environment.
    if any([
        pyhabitat.as_frozen(),
        pyhabitat.is_msix(),
        pyhabitat.is_pipx(),
        pyhabitat.is_pyz(),
        pyhabitat.is_elf(),
        pyhabitat.is_windows_portable_executable(),
        pyhabitat.is_macos_executable()
    ]):
        return False

    # 2. Check for the source of truth: Git.
    # Use the directory of the file calling this function, or pyhabitat's location
    # as a proxy for the source tree.
    try:
        # We look relative to the module file to find the repo root
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        if pyhabitat.is_in_git_repo(current_file_dir):
            return True
    except Exception:
        pass

    # 3. Explicit Developer Overrides
    if os.getenv('PYTHON_ENV') == 'development' or os.getenv('DEV_MODE') == '1':
        return True

    return False


def assess_default_pdf_library():
    if pymupdf_is_available():
        return "pymupdf"
    elif pdfium_is_available():
        return "pdfium"
    return "pypdf"
