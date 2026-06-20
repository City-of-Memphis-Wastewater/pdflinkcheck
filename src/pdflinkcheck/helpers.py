# src/pdflinkcheck/helpers.py
from __future__ import annotations
from pprint import pprint
from typing import Any, Dict, List
from pathlib import Path
from enum import Flag, auto, Enum
import functools
import operator
from typing import Optional, Iterable, Any, Set, NamedTuple
from dataclasses import dataclass, field

from .paths import PDFLINKCHECK_HOME


def get_source_pdf_path(report: Dict) -> Path:
    return Path(report["summary_metadata"]["file_overview"]["source_path"])

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
    def from_iterable(cls, formats: Optional[Iterable[ExportFormat]]) -> ExportFormat:
        """
        Reduces an iterable of flags (like Typer's List[ExportFormat]) 
        into a single consolidated bitmask flag choice.
        """
        if not formats or cls.NONE in formats:
            return cls.NONE
        return functools.reduce(operator.or_, formats, cls.NONE)

    @classmethod
    def from_choices(
        cls,
        choices: Optional[Iterable["ExportFormatChoice"]]
    ) -> "ExportFormat":

        if not choices:
            return cls.NONE

        if ExportFormatChoice.NONE in choices:
            return cls.NONE

        if ExportFormatChoice.ALL in choices:
            return cls.ALL

        result = cls.NONE

        for choice in choices:
            result |= cls[choice.name]

        return result

class PdfEngine(Flag):
    PYPDF = auto()    # 1
    PYMUPDF = auto()  # 2
    PDFIUM = auto()   # 4
    AUTO = auto()     # 8
    
    @classmethod
    def from_str(cls, value: Optional[str]) -> "PdfEngine":
        """Parses a raw string engine request into an explicit flag choice."""
        if not value or value.strip().lower() in ("none", "", "auto"):
            return cls.AUTO
        
        token_clean = value.strip().lower()
        if token_clean == "pypdf":
            return cls.PYPDF
        elif token_clean in ("pymupdf", "fitz"):
            return cls.PYMUPDF
        elif token_clean in ("pdfium", "pypdfium2"):
            return cls.PDFIUM
                
        return cls.AUTO

    @classmethod
    def resolve_auto_flag(cls) -> "PdfEngine":
        """Fallbacks cleanly based on physical package availability."""
        from pdflinkcheck.environment import pymupdf_is_available, pdfium_is_available
        if pymupdf_is_available():
            return cls.PYMUPDF
        if pdfium_is_available():
            return cls.PDFIUM
        return cls.PYPDF

    def resolve_if_auto(self) -> "PdfEngine":
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

    @classmethod
    def from_gui(cls, value: str) -> "PdfEngine":
        return cls.from_str(value)

# ==========================================
# TYPE-SAFE TYPER PRESENTATION LAYERS (Derived Natively)
# ==========================================

class ExportFormatChoice(str, Enum):
    """Presentation layer choices for Typer derived from ExportFormat flags."""
    NONE = "none"
    JSON = "json"
    TXT = "txt"
    XLSX = "xlsx"
    ALL = "all"


class PdfEngineChoice(str, Enum):
    """Presentation layer choices for Typer derived from PdfEngine flags."""
    PYPDF = "pypdf"
    PYMUPDF = "pymupdf"
    PDFIUM = "pdfium"
    AUTO = "auto"

# =================
# Formalized request structure
# =================

@dataclass(slots=True)
class ReportRequest:
    pdf_path: Path
    export_format: ExportFormat = ExportFormat.JSON
    pdf_library: PdfEngine = PdfEngine.AUTO
    print_bool: bool = True
    concise_print: bool = False
    output_dir: Optional[Path] = None
    check_external: bool = False

    def normalize(self) -> "ReportRequest":
        self.pdf_path = Path(self.pdf_path)

        if isinstance(self.pdf_library, str):
            self.pdf_library = PdfEngine.from_str(self.pdf_library)

        if isinstance(self.export_format, str):
            self.export_format = ExportFormat.from_str(self.export_format)

        return self
    
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
