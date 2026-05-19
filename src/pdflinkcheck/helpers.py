# src/pdflinkcheck/helpers.py
from __future__ import annotations
from pprint import pprint
from typing import Any, Dict
from pathlib import Path
from enum import Flag, auto
import functools
import operator
from typing import Optional, Iterable, Any, Set

from pdflinkcheck.io import PDFLINKCHECK_HOME
from pdflinkcheck.environment import pymupdf_is_available, pdfium_is_available

"""
Helper functions
"""

def get_source_pdf_path(report: Dict) -> Path:
    return Path(report["metadata"]["file_overview"]["source_path"])

def debug_head(label: str, data: Any, n: int = 3):
    """Helper to cleanly print the first N items of a list or dict."""
    print(f"\n--- [DEBUG: {label}] ---")
    if isinstance(data, list):
        pprint(data[:n], indent=2, compact=True, width=100)
    elif isinstance(data, dict):
        # Print first N keys
        head_dict = {k: data[k] for k in list(data.keys())[:n]}
        pprint(head_dict, indent=2, compact=True, width=100)
    else:
        print(data)


class PageRef:
    """
    A simple translator to handle the 0-to-1 index conversion 
    without the 'Double Bump' risk.
    """
    def __init__(self, index: int):
        self.index = index  # The 0-based physical index

    @property
    def human(self) -> int:
        """The 1-based page number for humans."""
        return self.index + 1

    @property
    def machine(self) -> int:
        """Alias for index. The 0-based page number for machines."""
        return self.index

    
    @classmethod
    def corrected_down(cls, human_num: int) -> "PageRef":
        """Explicitly compensates for 1-based data (e.g., PyMuPDF TOC)."""
        return cls.from_human(human_num)
    
    @classmethod
    def from_pymupdf_total_page_count(cls, total_pages: int) -> "PageRef":
        """
        Converts PyMuPDF's doc.page_count into a PageRef 
        representing the final valid machine-facing index.
        """
        return cls.from_human(total_pages)
    
    @classmethod
    def from_human(cls, human_num: int) -> "PageRef":
        """Creates a PageRef from a 1-based human page number (e.g., from TOC)."""
        return cls(human_num - 1)

    @classmethod
    def from_index(cls, physical_index: int) -> "PageRef":
        """Creates a PageRef from a 0-based physical index (e.g., from links)."""
        return cls(physical_index)
    
    def __int__(self):
        return self.index
    
    def __str__(self):
        return str(self.human)

    def __repr__(self):
        return f"PageRef(index={self.index}, human={self.human})"
    

class ExportFormat(Flag):
    NONE = 0
    JSON = auto()
    TXT = auto()
    XLSX = auto()
    # Define multi-flags (all checkboxes ticked) natively
    ALL = JSON | TXT | XLSX

    @classmethod
    def from_str(cls, value: Optional[str]) -> ExportFormat:
        """Parse comma-separated choices or 'all' safely into a single flag integer."""
        if not value or value.strip().lower() in ("none", ""):
            return cls.NONE
        
        if value.strip().lower() == "all":
            return cls.ALL
            
        result = cls.NONE
        # Leverage the enum's native mapping to check membership directly
        for token in value.split(","):
            try:
                result |= cls[token.strip().upper()]
            except KeyError:
                continue # Ignore garbage options gracefully
        return result
    @classmethod
    def from_iterable(cls, formats: Optional[Iterable[Any]]) -> ExportFormat:
        """
        Reduces an iterable of flags (like Typer's List[ExportFormat]) 
        into a single consolidated bitmask flag choice.
        """
        if not formats or cls.NONE in formats:
            return cls.NONE
        return functools.reduce(operator.or_, formats, cls.NONE)


class PdfEngine(Flag):
    PYPDF = auto()    # 1
    PYMUPDF = auto()  # 2
    PDFIUM = auto()   # 4
    AUTO = auto()     # 8
    
    # Combined option for running differential matrix checks
    ALL = PYPDF | PYMUPDF | PDFIUM

    @classmethod
    def from_str(cls, value: Optional[str]) -> "PdfEngine":
        """Parses a raw string engine request into an explicit flag choice."""
        # Since NONE is removed, fallback cleanly to AUTO if string is dead or empty
        if not value or value.strip().lower() in ("none", ""):
            return cls.AUTO
        
        normalized = value.strip().lower()
        if normalized == "auto":
            return cls.AUTO
        if normalized == "all":
            return cls.ALL

        # Start with an empty combined mask state
        result = cls(0)
        for token in normalized.split(","):
            token_clean = token.strip()
            if token_clean == "pypdf":
                result |= cls.PYPDF
            elif token_clean in ("pymupdf", "fitz"):
                result |= cls.PYMUPDF
            elif token_clean in ("pdfium", "pypdfium2"):
                result |= cls.PDFIUM
                
        # If string was invalid tokens and result flag remains 0, fallback to AUTO
        return result if result.value != 0 else cls.AUTO

    @classmethod
    def resolve_auto_flag(cls) -> "PdfEngine":
        """Fallbacks cleanly based on physical package availability."""
        from pdflinkcheck.environment import pymupdf_is_available, pdfium_is_available
        if pymupdf_is_available():
            return cls.PYMUPDF
        if pdfium_is_available():
            return cls.PDFIUM
        return cls.PYPDF

    def resolve(self) -> "PdfEngine":
        """
        Evaluates the instance flag. If the AUTO bit is present, it scrubs it 
        and blends in the dynamic system fallback engine.
        """
        if not (self & PdfEngine.AUTO):
            return self
        
        # Strip AUTO out and merge with dynamic system availability fallback
        remaining = self.value & ~PdfEngine.AUTO.value
        if remaining == 0:
            return self.resolve_auto_flag()
        return PdfEngine(remaining)
    
"""
## Using the PageRef class
### Indexing Map: Physical (0) vs. Logical (1)

| **File**              | **Context**      | **Index Rule**      | **Reasoning**                                                                                          |
| --------------------- | ---------------- | ------------------- | ------------------------------------------------------------------------------------------------------ |
| `analysis_pypdf.py`   | Data Extraction  | **0-indexing only** | `pypdf` is 0-indexed. Your previous `+ 1` hacks have been removed.                                     |
| `analysis_pymupdf.py` | Data Extraction  | **Mixed**           | **Internal:** 0-indexed. **TOC:** `get_toc()` is natively 1-indexed. Needs normalization.              |
| `validate.py`         | Logic/Validation | **Mixed**           | **Logic:** Uses `START_INDEX=0` for boundary checks. **Strings:** Formats error messages as 1-indexed. |
| `report.py`           | Output/Reporting | **Mixed**           | **Data:** Keeps dictionary values at 0. **Display:** Formats CLI tables as 1-indexed.                  |
| `helpers.py`          | Translation      | **Mixed**           | The `PageRef` class acts as the "Border Control" between 0 and 1.                                      |
| `__init__.py`         | API Surface      | **0-indexing only** | If exposing a library, users expect 0-indexed lists of pages/links.                                    |
"""

# ---

def get_export_path() -> Path:
    """
    Determines the directory where reports are stored.
    Uses the centralized PDFLINKCHECK_HOME defined in io.py.
    """
    # Ensure the directory exists before returning/using it
    if not PDFLINKCHECK_HOME.exists():
        PDFLINKCHECK_HOME.mkdir(parents=True, exist_ok=True)
    return PDFLINKCHECK_HOME

# --- Exceptions --- 

class PDFLinkCheckError(Exception):
    """Base exception for all pdflinkcheck errors."""

class AnalysisError(PDFLinkCheckError):
    """Raised when a specific PDF engine fails to process a file."""

class ExportError(PDFLinkCheckError):
    """Raised when writing the final report (JSON/TXT/XLSX) fails."""