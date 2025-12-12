# pdflinkcheck

A purpose-built tool for comprehensive analysis of hyperlinks and link remnants within PDF documents, primarily using the PyMuPDF library. Use the CLI or the GUI.

-----

![Screenshot of the pdflinkcheck GUI](https://raw.githubusercontent.com/City-of-Memphis-Wastewater/pdflinkcheck/main/assets/pdflinkcheck_gui.png)

-----

## 📥 Access and Installation

The recommended way to use `pdflinkcheck` is to either install with `pipx` for a managed environment or to download the appropriate latest binary for your system from [Releases](https://github.com/City-of-Memphis-Wastewater/pdflinkcheck/releases/).

### 🚀 Recommended Access (Binary Files)

For the fastest, most reliable experience, download the single-file binary matching your OS.

| **File Type** | **Primary Use Case** | **Recommended Launch Method** |
| :--- | :--- | :--- |
| **Executable (.exe, .elf, .pyz)** | **GUI (Double-Click)** | Double-click the file (use the accompanying `.bat` file on Windows). |
| **PYZ (Python Zip App)** | **CLI (Terminal)** | Run using your system's `python` command: `python pdflinkcheck-VERSION.pyz analyze ...` |

### Installation via pipx

For an isolated environment where you can access `pdflinkcheck` from any terminal:

```bash
# Ensure you have pipx installed first (if not, run: pip install pipx)
pipx install pdflinkcheck
```

-----

## 💻 Graphical User Interface (GUI)

The tool can be run as simple cross-platform graphical interface (Tkinter).

### Launching the GUI

There are three ways to launch the GUI interface:

1.  **Implicit Launch:** Run the main command with no arguments, subcommands, or flags (`pdflinkcheck`).
2.  **Explicit Command:** Use the dedicated GUI subcommand (`pdflinkcheck gui`).
3.  **Binary Double-Click:**
      * **Windows:** Double-click the `pdflinkcheck-VERSION-gui.bat` file.
      * **macOS/Linux:** Double-click the downloaded `.pyz` or `.elf` file.

### Planned GUI Updates

We are actively working on the following enhancements:

  * **Report Export:** Functionality to export the full analysis report to a plain text file.
  * **License Visibility:** A dedicated "License Info" button within the GUI to display the terms of the AGPLv3+ license.

-----

### 🚀 CLI Usage

The main command is `pdflinkcheck analyze`.

```bash
# Basic usage: Analyze a PDF and check for remnants (default behavior)
pdflinkcheck analyze "path/to/my/document.pdf"
```

#### Analyze Command Options

| **Option** | **Description** | **Default** |
| :--- | :--- | :--- |
| `<PDF_PATH>` | **Required.** The path to the PDF file to analyze. | N/A |
| `--check-remnants / --no-check-remnants` | Toggle scanning the text layer for unlinked URLs/Emails. | `--check-remnants` |
| `--max-links INTEGER` | Set the maximum number of links/remnants to display in the detailed report sections. Use 0 to show all. | `50` |
| `--help` | Show command help and exit. | N/A |

#### Example Run

```bash
pdflinkcheck analyze "TE Maxson WWTF O&M Manual.pdf" --max-links 10
```

-----

### ✨ Features

  * **Active Link Extraction:** Identifies and categorizes all programmed links (External URIs, Internal GoTo/Destinations, Remote Jumps).
  * **Anchor Text Retrieval:** Extracts the visible text corresponding to each link's bounding box.
  * **Remnant Detection:** Scans the document's text layer for unlinked URIs and email addresses that should potentially be converted into active links.
  * **Structural TOC:** Extracts the PDF's internal Table of Contents (bookmarks/outline).

-----

### 📜 License Implications (AGPLv3+)

**pdflinkcheck is licensed under the GNU Affero General Public License version 3 or later (AGPLv3+).**

This license has significant implications for **distribution and network use**, particularly for organizations:

  * **Source Code Provision:** If you distribute this tool (modified or unmodified) to anyone, you **must** provide the full source code under the same license.
  * **Network Interaction (Affero Clause):** If you modify this tool and make the modified version available to users over a computer network (e.g., as a web service or backend), you **must** also offer the source code to those network users.

> **Before deploying or modifying this tool for organizational use, especially for internal web services or distribution, please ensure compliance with the AGPLv3+ terms.**

-----

### ⚠️ Compatibility Notes

  * **Platform Compatibility:** This tool relies on the `PyMuPDF` library. All testing has failed to run in a **Termux (Android)** environment due to underlying C/C++ library compilation issues with PyMuPDF. It is recommended for use on standard Linux, macOS, or Windows operating systems.
  * **Document Compatibility:** While `pdflinkcheck` uses the robust PyMuPDF library, not all PDF files can be processed successfully. This tool is designed primarily for digitally generated (vector-based) PDFs.
    Processing may fail or yield incomplete results for:
      * **Scanned PDFs** (images of text) that lack an accessible text layer.
      * **Encrypted or Password-Protected** documents.
      * **Malformed or non-standard** PDF files.

-----

### Run from Source (Developers)

```bash
git clone http://github.com/city-of-memphis-wastewater/pdflinkcheck.git
cd pdflinkcheck
uv sync
uv run python src/pdflinkcheck/cli.py --help
```
