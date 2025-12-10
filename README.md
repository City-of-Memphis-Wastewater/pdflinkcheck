# pdflinkcheck
A purpose-built tool for comprehensive analysis of hyperlinks and link remnants within PDF documents, primarily using the PyMuPDF library.
Use the CLI or the GUI.

---

### Graphical User Interface (GUI)

The tool can be run using a simple cross-platform graphical interface (Tkinter):

![Screenshot of the pdflinkcheck GUI](https://raw.githubusercontent.com/City-of-Memphis-Wastewater/pdflinkcheck/main/assets/pdflinkcheck_gui.png)

To launch the GUI:
A. Install from pipx using `pipx install pdflinkcheck`, and then use the command: `pdflinkcheck-gui`
or
B. Download and double-click the latest PYZ, EXE, or ELF binary from https://github/com/City-of-Memphis-Wastewater/pdflinkcheck/releases/
---

### ✨ Features

* **Active Link Extraction:** Identifies and categorizes all programmed links (External URIs, Internal GoTo/Destinations, Remote Jumps).
* **Anchor Text Retrieval:** Extracts the visible text corresponding to each link's bounding box.
* **Remnant Detection:** Scans the document's text layer for unlinked URIs and email addresses that should potentially be converted into active links.
* **Structural TOC:** Extracts the PDF's internal Table of Contents (bookmarks/outline).

---

### 📥 Installation (Recommended via `pipx`)

The recommended way to install `pdflinkcheck` is using `pipx`, which installs Python applications in isolated environments, preventing dependency conflicts.

```bash
# Ensure you have pipx installed first (if not, run: pip install pipx)
pipx install pdflinkcheck
```


**Note for Developers:** If you prefer a traditional virtual environment or are developing locally, use `pip`:
```bash
# From the root of the project
pip install .
```

---

### 🚀 Usage

The main command is `pdflinkcheck analyze`.


```bash
# Basic usage: Analyze a PDF and check for remnants (default behavior)
pdflinkcheck analyze "path/to/my/document.pdf"
```

#### Command Options

|**Option**|**Description**|**Default**|
|---|---|---|
|`<PDF_PATH>`|**Required.** The path to the PDF file to analyze.|N/A|
|`--check-remnants / --no-check-remnants`|Toggle scanning the text layer for unlinked URLs/Emails.|`--check-remnants`|
|`--max-links INTEGER`|Maximum number of links/remnants to display in the detailed report sections.|`50`|
|`--help`|Show command help and exit.|N/A|

#### Example Run

```bash
pdflinkcheck analyze "TE Maxson WWTF O&M Manual.pdf" --max-links 10
```

# Run from source
```
git clone http://github.com/city-of-memphis-wastewater/pdflinkcheck.git
cd pdflinkcheck
uv sync
python src/pdflinkcheck/analyze.py
```

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
