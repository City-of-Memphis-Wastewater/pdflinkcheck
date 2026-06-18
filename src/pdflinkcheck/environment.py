#!/usr/bin/env python3 
# SPDX-License-Identifier: MIT
# pdflinkcheck/environment.py
from __future__ import annotations
from functools import cache
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
        # Fails if: the [pdfium,pymupdf] group from [project.optional-dependencies] in pyproject.toml was not used when installing pdflink check. Like 
        # Use: `pipx install pdflinkcheck[pdfium,pymupdf]` or alternative.
        #print(f"DEBUG: pymupdf check failed with error: {e}")
        return False


@cache
def pdfium_is_available() -> bool:
    """Check if pdfium2 is available in the current local version of pdflinkcheck."""
    try:
        import pypdfium2
        return True
    except Exception as e:
        # Fails if: the [pdfium,pymupdf] group from [project.optional-dependencies] in pyproject.toml was not used when installing pdflink check. Like 
        # Use: `pipx install pdflinkcheck[pdfium]` or alternative.
        #print(f"DEBUG: pdfium check failed with error: {e}")
        return False


@cache
def is_in_dev_environment() -> bool:
    """
    Determines if the code is running in a local development context.

    Determines if the code is running in a local development context.
    
    NOTE: This logic is only appropriate for the 'highest consuming project' 
    (the Application). If placed in a library, it will detect the library's 
    dev-state, not the state of the app using it. This is due to the use of `os.path.abspath(__file__)`.
    """

    # --- Explicit Developer Overrides ---
    # Allows a dev to force dev-behavior even in a bundled/installed artifact.
    if os.getenv('PYTHON_ENV') == 'development' or os.getenv('DEV_MODE') == '1':
        return True
    
    # --- Check for 'Artifact' states. ---
    # If the app is packaged, frozen, or managed by a tool like pipx, 
    # we treat it as "Production" regardless of the file system layout.
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

    # --- Check for .git dir ---
    # Use the directory of the file calling this function, or pyhabitat's location
    # as a proxy for the source tree.
    try:
        
        current_file_path = os.path.abspath(__file__)


        # Look relative to this module file to find the repo root.
        # Since this is part of the 'highest consuming project', this path
        # is a reliable proxy for the application's installation state.
        # Quick exit: If we are inside site-packages, we are 'installed', not 'in dev'.
        if "site-packages" in current_file_path or "dist-packages" in current_file_path:
            return False
        
        # We look relative to the module file to find the repo root
        if pyhabitat.is_in_git_repo(os.path.dirname(current_file_path)):
            return True
            
    except Exception:
        # If path detection fails, we default to the safer 'False' (Production)
        pass

    return False
    