#!/usr/bin/env python3 
# SPDX-License-Identifier: MIT
# src/pdflinkcheck/io.py
from __future__ import annotations
import logging
import json
import sys
from pathlib import Path
from typing import Dict, Any, Union, List, Optional
import datetime
import time
import pyhabitat
import os
from enum import Enum
import logging

logger = logging.getLogger(__name__)

from .logging_setup import error_logger
from .paths import PDFLINKCHECK_HOME, LOG_FILE_PATH

# --- Export Functionality ---

def export_report_json(
    report_data: Dict[str, Any], 
    pdf_filename: str, 
    pdf_library_name: str,
    output_dir: Optional[Union[str, Path]] = None
) -> Path:
    """
    Exports the structured analysis report data to a file in the 
    PDFLINKCHECK_HOME directory.

    Args:
        report_data: The dictionary containing the results from run_report.
        pdf_filename: The base filename of the PDF being analyzed (used for the output file name).
    
    Returns:
        The path object pointing to the successfully created report file.
        
    Raises:
        ValueError: If the export_format is not supported.

    Exports structured dictionary results to a .json file.
    """
    # Resolve the destination target folder dynamically
    target_dir = Path(output_dir) if output_dir else PDFLINKCHECK_HOME
    target_dir.mkdir(parents=True, exist_ok=True)

    base_name = Path(pdf_filename).stem
    output_path = target_dir / f"{base_name}_{pdf_library_name}_{get_unique_human_time()}_report.json"
    
    print("For more details, explore the exported file(s).")
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            safe_payload = make_json_safe(report_data)
            json.dump(safe_payload, f, indent=4, ensure_ascii=False)
            #json.dump(safe_payload, f, indent=4)
        print(f"JSON report exported: {get_friendly_path(output_path)}")
        return output_path
    except Exception as e:
        error_logger.error(f"JSON export failed: {e}", exc_info=True)
        raise RuntimeError(f"JSON export failed: {e}")

def export_report_txt(
    report_text: str, 
    pdf_filename: str, 
    pdf_library_name: str,
    output_dir: Optional[Union[str, Path]] = None
) -> Path:
    """Exports the formatted string buffer to a .txt file."""
    target_dir = Path(output_dir) if output_dir else PDFLINKCHECK_HOME
    target_dir.mkdir(parents=True, exist_ok=True)

    base_name = Path(pdf_filename).stem
    output_path = target_dir / f"{base_name}_{pdf_library_name}_{get_unique_human_time()}_report.txt"
 
    report_text_str = "\n".join(report_text)
    
    try:
        output_path.write_text(report_text_str, encoding='utf-8')
        print(f"TXT report exported: {get_friendly_path(output_path)}")
        return output_path
    except Exception as e:
        error_logger.error(f"TXT export failed: {e}", exc_info=True)
        raise RuntimeError(f"TXT export failed: {e}")

def make_json_safe(obj):
    """
    Recursively convert non-JSON-safe objects into serializable primitives.
    """

    if isinstance(obj, Path):
        return str(obj)

    if isinstance(obj, Enum):
        return obj.name.lower()

    if isinstance(obj, dict):
        return {
            str(k): make_json_safe(v)
            for k, v in obj.items()
        }

    if isinstance(obj, (list, tuple, set)):
        return [make_json_safe(v) for v in obj]

    return obj


# --- helpers ---
def get_friendly_path(full_path: str) -> str:
    """
    
    Returns an absolute path on Windows, or a tilde-shortened path on Linux.
    Ensures system calls don't break on Windows while maintaining Linux UX.
    
    """
    try:
        p = Path(full_path).resolve()
    except Exception:
        # If resolution fails (e.g. permission error), use the raw path
        p = Path(full_path)

    if pyhabitat.on_windows():
        return str(p)
    
    # Linux/macOS: Try to provide the friendly tilde shortcut
    try:
        home = Path.home()
        # is_relative_to was added in Python 3.9
        if hasattr(p, "is_relative_to") and p.is_relative_to(home):
            return f"~{os.sep}{p.relative_to(home)}"
        elif str(p).startswith(str(home)):
            # Fallback for Python < 3.9
            return str(p).replace(str(home), "~", 1)
    except Exception:
        # If home directory can't be determined, return absolute path
        pass
        
    return str(p)
    
def get_unique_human_time()->str:
    return str(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S"))
    
def get_unique_unix_time()->str:
    """
    Get the unix time for right now.
    Purpose: When added to a filename, this ensures a unique filename, to avoid overwrites for otherwise identical filenames. 
    Pros:
    - cheap, easy, no reason to check for collision

    Cons:
    - Longer than YYYYMMDDalpha
    - not human readable
    """
    return str(int(time.time()))
    #return str(int(time.mktime(datetime.datetime.now().timetuple())))

    
def get_first_pdf_in_cwd() -> Optional[str]:
    """
    Scans the current working directory (CWD) for the first file ending 
    with a '.pdf' extension (case-insensitive).

    This is intended as a convenience function for running the tool 
    without explicitly specifying a path.

    Returns:
        The absolute path (as a string) to the first PDF file found, 
        or None if no PDF files are present in the CWD.
    """
    # 1. Get the current working directory (CWD)
    cwd = Path.cwd()
    
    # 2. Use Path.glob to find files matching the pattern. 
    #    We use '**/*.pdf' to also search nested directories if desired, 
    #    but typically for a single PDF in CWD, '*.pdf' is enough. 
    #    Let's stick to files directly in the CWD for simplicity.
    
    # We use list comprehension with next() for efficiency, or a simple loop.
    # Using Path.glob('*.pdf') to search the CWD for files ending in .pdf
    # We make it case-insensitive by checking both '*.pdf' and '*.PDF'
    
    # Note: On Unix systems, glob is case-sensitive by default.
    # The most cross-platform safe way is to iterate and check the suffix.
    print("No PDF argument was provide. Falling back to using the first PDF available at the current path.")
    try:
        # Check for files in the current directory only
        # Iterating over the generator stops as soon as the first match is found.
        first_pdf_path = next(
            (p.resolve() for p in cwd.iterdir() 
            if p.is_file() and p.suffix.lower() == '.pdf'),
        )
        if first_pdf_path is None:
            logger.debug("No PDF files found in the current working directory.")
            return None
        logger.info(f"Fallback PDF found: {first_pdf_path.name}")
        return str(first_pdf_path)
    
    except Exception as e:
        logger.error(f"Error while searching for PDF in CWD: {e}")
        # Handle potential permissions errors or other issues
        return None
