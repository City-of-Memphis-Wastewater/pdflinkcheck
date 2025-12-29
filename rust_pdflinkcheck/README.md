# Rust PDF Link Check Core

This crate is a high-performance native core for **PDF link and table-of-contents analysis**.
It is one of the analysis engines used by the PDF Link Check project, which include:

- **pypdf-based engine** — maximizes portability (including Termux)
- **PyMuPDF-based engine** — exposes a rich, high-level PDF object model
- **PDFium-based Rust engine (this crate)** — prioritizes performance, while avoiding
  PyMuPDF's AGPLv3+ licensing restrictions, on supported platforms

Source repository:
https://github.com/City-of-Memphis-Wastewater/pdflinkcheck

---

## Why PDFium?

PDFium was selected for this Rust implementation after evaluating multiple
approaches to reliable link and anchor-text extraction.

- PDFium provides accurate, low-level access to link annotations and their
  associated geometry.
- It reliably associates link annotations with visible anchor text, which
  proved difficult using several pure-Rust PDF libraries.
- It is battle-tested at scale and widely used in production environments.

### Trade-offs and platform considerations

PDFium does not build on Termux, which limits its portability. For this reason,
Termux compatibility is provided by the project’s `pypdf`-based Python engine,
implemented in `src/pdflinkcheck/analyze_pypdf.py`.

Several Rust-native PDF libraries (`lopdf`, `pdf`) were evaluated but were unable
to consistently identify anchor text associated with link annotations. As a
result, PDFium was chosen for this Rust core despite its platform constraints.

---

## Design notes

This crate is intentionally focused on **PDF analysis**, not general-purpose
PDF manipulation.

Internally, it uses PDFium via the `pdfium-render` crate, but PDFium types are
treated strictly as implementation details. The public API exposes only the crate-defined,
stable Rust data structures (`AnalysisResult`, `LinkRecord`, `TocEntry`) and
JSON output via an FFI boundary.

This design minimizes API surface area while preserving performance and
long-term maintainability.

---

## Raw PDFium access (advanced)

For advanced users who need direct access to PDFium APIs, this crate re-exports
the low-level `pdfium_sys` bindings behind a feature flag:

```bash
cargo build --features pdfium-raw
```

**Note**: 
These bindings are unsafe and are not considered part of the stable public API. 
They may change without notice.

## What is *not* exposed
This crate does not expose PDF document, page, or annotation objects as part of its public API. 
All PDFium interaction is encapsulated within the analysis engine.

---

## Prerequisites

This crate requires the **PDFium** shared library at runtime.

## Setup (Linux x64)
```bash
wget https://github.com/bblanchon/pdfium-binaries/releases/latest/download/pdfium-linux-x64.tgz
tar -xvf pdfium-linux-x64.tgz
cp lib/libpdfium.so .
```
