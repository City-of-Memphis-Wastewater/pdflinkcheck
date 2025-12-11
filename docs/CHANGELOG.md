# Changelog
All notable changes to this project will be documented in this file.
The format is (read: strives to be) based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [1.1.6] – 2025-12-10
### Changed:
- In build_executable.py, change form_dynamic_binary_name() to form_dynamic_name().
- Import form_dynamic_name() from build_executable.py into build_pyz.py, so that the PYZ filename can be associated with it's OS and processir architecture. This is important because the pymupdf package has a corw which is not pure Python, ergo PYZ builds of pdflinkcheck are not cross platform. 

---

## [1.1.5] – 2025-12-10
### Fixed:
- Improve arch and os tagging in build_executable.py by leveraging pyhabitat.SystemInfo().

### Added:
- Add pyhabitat>=1.0.52 to the pyproject.toml as a dependency. This isnthe firsr version which exposes the SystemInfo class in pyhabitat/__init__.py.

---

## [1.1.4] – 2025-12-10
### Added: 
- build_executable.py.
- ci.yml

---

## [1.1.3] – 2025-12-10
### Fixed:
- Reference to GUI screenshot now uses `raw.githubusercontent` format to enable image content on PyPI.

---

## [1.1.1] – 2025-12-10
### Added:
- Add detail to gui command in CLI.
- Add and stabilize build_pyz.py.

Hooray, 1.1.1 indicates a stable public release.

---

## [0.1.5] – 2025-12-10
### Added:
- gui.py, for tkinter gui. Ensure you have `sudo apt install python3-tk tk-dev if using wslg`

---

## [0.1.1] – 2025-12-09
### Added:
- **Initial release** of the `pdflinkcheck` utility for comprehensive PDF link analysis.
- Core functionality to analyze PDF documents using PyMuPDF (Fitz).
- Ability to scan and categorize all links into: **External URIs**, **Mailto Emails**, and **Internal Jumps** (GoTo actions).
- Implemented robust **Anchor Text Extraction** by querying the text within the link's bounding box.
- Introduced a **Link Remnants** section to identify plain text URLs and email addresses that are not currently hyperlinked, flagging them for manual correction.

### Changed:
- Migrated link extraction and `fitz.Rect` manipulation logic to use **explicit coordinate arithmetic** (`rect.x0 - 1`, etc.) instead of version-dependent methods like `rect.from_expanded()`. This ensures maximum compatibility across different PyMuPDF versions.
- Switched Git repository origin from HTTPS to **SSH** for secure, key-based authentication.

### Fixed:
- Resolved coordinate handling errors stemming from non-normalized link rect tuples returned by PyMuPDF.
- Corrected issue where link extraction methods were failing due to missing `fitz.Rect` utility functions in the target environment (e.g., `'Rect' object has no attribute 'from_expanded'`).

### Removed:
- Eliminated reliance on potentially unstable or version-specific PyMuPDF methods for rect expansion.

---
