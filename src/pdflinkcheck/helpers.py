# src/pdflinkcheck/helpers.py
from __future__ import annotations
from pprint import pprint
from typing import Any

"""
Helper functions
"""

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
    

"""
### Indexing Map: Physical (0) vs. Logical (1)

| **File**              | **Context**      | **Index Rule**      | **Reasoning**                                                                                          |
| --------------------- | ---------------- | ------------------- | ------------------------------------------------------------------------------------------------------ |
| `ffi.py` (Rust bridge)| Data Extraction  | **0-indexing only** | Rust's `pdf-extract` and `lopdf` crates are 0-indexed. Data should stay raw.                           |
| `analysis_pypdf.py`   | Data Extraction  | **0-indexing only** | `pypdf` is 0-indexed. Your previous `+ 1` hacks have been removed.                                     |
| `analysis_pymupdf.py` | Data Extraction  | **Mixed**           | **Internal:** 0-indexed. **TOC:** `get_toc()` is natively 1-indexed. Needs normalization.              |
| `validate.py`         | Logic/Validation | **Mixed**           | **Logic:** Uses `START_INDEX=0` for boundary checks. **Strings:** Formats error messages as 1-indexed. |
| `report.py`           | Output/Reporting | **Mixed**           | **Data:** Keeps dictionary values at 0. **Display:** Formats CLI tables as 1-indexed.                  |
| `helpers.py`          | Translation      | **Mixed**           | The `PageRef` class acts as the "Border Control" between 0 and 1.                                      |
| `__init__.py`         | API Surface      | **0-indexing only** | If exposing a library, users expect 0-indexed lists of pages/links.                                    |

"""
