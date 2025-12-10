# Run from source
```
git clone http://github.com/city-of-memphis-wastewater/pdflinkcheck.git
cd pdflinkcheck
uv sync
python src/pdflinkcheck/analyze.py
```

When prompted, paste the path to your PDF.

---

### ⚠️ Platform Compatibility Note

This tool relies on the `PyMuPDF` library, which requires specific native dependencies (like MuPDF) that may not be available on all platforms.

**Known Incompatibility:** This tool is **not officially supported** and may fail to run on environments like **Termux (Android)** due to underlying C/C++ library compilation issues with PyMuPDF. It is recommended for use on standard Linux, macOS, or Windows operating systems.

---

### Document Compatibility

While `pdflinkcheck` uses the robust PyMuPDF library, not all PDF files can be processed successfully. This tool is designed primarily for digitally generated (vector-based) PDFs.

Processing may fail or yield incomplete results for:
* **Scanned PDFs** (images of text) that lack an accessible text layer.
* **Encrypted or Password-Protected** documents.
* **Malformed or non-standard** PDF files.
