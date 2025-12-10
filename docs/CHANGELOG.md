# Changelog
All notable changes to this project will be documented in this file.
The format is (read: strives to be) based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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