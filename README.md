# pdflinkcheck

A purpose-built tool for comprehensive analysis of hyperlinks and link remnants within PDF documents, primarily using the PyMuPDF library. Use the CLI or the GUI.

-----

![Screenshot of the pdflinkcheck GUI](https://raw.githubusercontent.com/City-of-Memphis-Wastewater/pdflinkcheck/main/assets/pdflinkcheck_gui_v1.1.32.png)

-----

## 📥 Access and Installation

The recommended way to use `pdflinkcheck` is to either install the CLI with `pipx` or to download the appropriate latest binary for your system from [Releases](https://github.com/City-of-Memphis-Wastewater/pdflinkcheck/releases/).

### 🚀 Recommended Access (Binary Files)

For the most user-typical experience, download the single-file binary matching your OS.

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

## 🚀 CLI Usage

The core functionality is accessed via the `analyze` command. All commands include the built-in `--help` flag for quick reference.

### Available Commands

|**Command**|**Description**|
|---|---|
|`pdflinkcheck analyze`|Analyzes a PDF file for links and remnants.|
|`pdflinkcheck gui`|Explicitly launch the Graphical User Interface.|
|`pdflinkcheck license`|**Displays the full AGPLv3+ license text in the terminal.**|

### `analyze` Command Options

|**Option**|**Description**|**Default**|
|---|---|---|
|`<PDF_PATH>`|**Required.** The path to the PDF file to analyze.|N/A|
|`--check-remnants / --no-check-remnants`|Toggle scanning the text layer for unlinked URLs/Emails.|`--check-remnants`|
|`--max-links INTEGER`|Maximum number of links/remnants to display in the detailed report sections. Use `0` to show all.|`0` (Show All)|
|`--export-format FORMAT`|Format for the exported report. If specified, the report is saved to a file named after the PDF. Currently supported: `JSON`.|`JSON`|
|`--help`|Show command help and exit.|N/A|

### `gui` Command Options

| **Option**             | **Description**                                                                                               | **Default**    |
| ---------------------- | ------------------------------------------------------------------------------------------------------------- | -------------- |
| `--auto-close INTEGER` | **(For testing/automation only).** Delay in milliseconds after which the GUI window will automatically close. | `0` (Disabled) |
#### Example Runs



```bash 
# Analyze a document, show all links/remnants, and save the report as JSON
pdflinkcheck analyze "TE Maxson WWTF O&M Manual.pdf" --export-format JSON

# Analyze a document but skip the time-consuming remnant check
pdflinkcheck analyze "another_doc.pdf" --no-check-remnants 

# Analyze a document but keep the print block short, showing only the first 10 links for each type
pdflinkcheck analyze "TE Maxson WWTF O&M Manual.pdf" --max-links 10

# Show the GUI for only a moment, like in a build check
pdflinkcheck gui --auto-close 3000 
```


-----

### 📦 Library Access (Advanced)

For developers importing `pdflinkcheck` into other Python projects, the core analysis functions are exposed directly in the root namespace:

|**Function**|**Description**|
|---|---|
|`run_analysis()`|**(Primary function)** Performs the full analysis, prints to console, and handles file export.|
|`extract_links()`|Low-level function to retrieve all explicit links (URIs, GoTo, etc.) from a PDF path.|
|`extract_toc()`|Low-level function to extract the PDF's internal Table of Contents (bookmarks/outline).|

Python

```
from pdflinkcheck.analyze import run_analysis, extract_links, extract_toc
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

#### Platform Compatibility: 

This tool relies on the `PyMuPDF` library. 
All testing has failed to run in a **Termux (Android)** environment due to underlying C/C++ library compilation issues with PyMuPDF. 
It is recommended for use on standard Linux, macOS, or Windows operating systems.

A key goal of City-of-Memphis-Wastewater is to release all software as Termux-compatible. Unfortunately, that simply isn't possible with PyMuPDF as a dependency. 
We tried alternative PDF libaries like `pdfminer`, `pdfplumber`, and `borb`, but none of these offered the level of detail concerning GoTo links.
Due to Termux compatibility goals, we do not generally make Tkinter-based interfaces, so that was a fun, minimalist opportunity on this project. 

Termux compatibility is important in the modern age as Android devices are common among technicians, field engineers, and maintenace staff. 
Android is the most common operating system in the Global South. 
We aim to produce stable software that can do the most possible good. 

We love web-stack GUIs served locally as a final product.
All that packaged up into a Termux-compatible ELF or PYZ - What could be better!

In the future we may find a work-around and be able to drop the PyMuPDF dependency. 
This would have lots of implications:
- Reduced artifact size.
- Alpine-compatible Docker image.
- Web-stack GUI rather than tkinter, to be compatible with Termux.
- A different license from the AGPL3, if we choose at that time.

In the meantime, the standalone binaries and pipx installation provide excellent cross-platform support on Windows, macOS, and standard Linux desktops/laptops.

#### Document Compatibility: 
While `pdflinkcheck` uses the robust PyMuPDF library, not all PDF files can be processed successfully. This tool is designed primarily for digitally generated (vector-based) PDFs.

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
