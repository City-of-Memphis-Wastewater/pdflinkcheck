# pdflinkcheck

A purpose-built tool for comprehensive analysis of hyperlinks and GoTo links within PDF documents. Users may leverage either the PyMuPDF or the pypdf library. Use the CLI or the GUI.

-----

![Screenshot of the pdflinkcheck GUI](https://raw.githubusercontent.com/City-of-Memphis-Wastewater/pdflinkcheck/main/assets/pdflinkcheck_gui_v1.1.56.png)

-----

## 📥 Access and Installation

The recommended way to use `pdflinkcheck` is to either install the CLI with `pipx` or to download the appropriate latest binary for your system from [Releases](https://github.com/City-of-Memphis-Wastewater/pdflinkcheck/releases/).

### 🚀 Release Artifact Files (EXE, PYZ, ELF)

For the most user-typical experience, download the single-file binary matching your OS.

| **File Type** | **Primary Use Case** | **Recommended Launch Method** |
| :--- | :--- | :--- |
| **Executable (.exe, .elf)** | **GUI** | Double-click the file. |
| **PYZ (Python Zip App)** | **CLI** or **GUI** | Run using your system's `python` command: `python pdflinkcheck-VERSION.pyz --help` |

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

![Screenshot of the pdflinkcheck CLI Tree Help](https://raw.githubusercontent.com/City-of-Memphis-Wastewater/pdflinkcheck/main/assets/pdflinkcheck_cli_v1.1.57_tree_help.png)


### Available Commands

|**Command**|**Description**|
|---|---|
|`pdflinkcheck analyze`|Analyzes a PDF file for links |
|`pdflinkcheck gui`|Explicitly launch the Graphical User Interface.|
|`pdflinkcheck license`|**Displays the full AGPLv3+ license text in the terminal.**|

### `analyze` Command Options

|**Option**|**Description**|**Default**|
|---|---|---|
|`<PDF_PATH>`|**Required.** The path to the PDF file to analyze.|N/A|
|`--max-links INTEGER`|Maximum number of links to display in the detailed report sections. Use `0` to show all.|`0` (Show All)|
|`--export-format FORMAT`|Format for the exported report. If specified, the report is saved to a file named after the PDF. Currently supported: `JSON`.|`JSON`|
|`--help`|Show command help and exit.|N/A|

### `gui` Command Options

| **Option**             | **Description**                                                                                               | **Default**    |
| ---------------------- | ------------------------------------------------------------------------------------------------------------- | -------------- |
| `--auto-close INTEGER` | **(For testing/automation only).** Delay in milliseconds after which the GUI window will automatically close. | `0` (Disabled) |
#### Example Runs



```bash 
# Analyze a document, show all links, and save the report as JSON
pdflinkcheck analyze "TE Maxson WWTF O&M Manual.pdf" --export-format JSON

# Analyze a document but keep the print block short, showing only the first 10 links for each type
pdflinkcheck analyze "TE Maxson WWTF O&M Manual.pdf" --max-links 10

# Show the GUI for only a moment, like in a build check
pdflinkcheck gui --auto-close 3000 
```


-----

## 📦 Library Access (Advanced)

For developers importing `pdflinkcheck` into other Python projects, the core analysis functions are exposed directly in the root namespace:

|**Function**|**Description**|
|---|---|
|`run_report()`|**(Primary function)** Performs the full analysis, prints to console, and handles file export.|
|`extract_links()`|Low-level function to retrieve all explicit links (URIs, GoTo, etc.) from a PDF path.|
|`extract_toc()`|Low-level function to extract the PDF's internal Table of Contents (bookmarks/outline).|

Python

```
from pdflinkcheck.report import run_report
from pdflinkcheck.analysis import extract_links, extract_toc
```

-----

## ✨ Features

  * **Active Link Extraction:** Identifies and categorizes all programmed links (External URIs, Internal GoTo/Destinations, Remote Jumps).
  * **Anchor Text Retrieval:** Extracts the visible text corresponding to each link's bounding box.
  * **Structural TOC:** Extracts the PDF's internal Table of Contents (bookmarks/outline).

-----

## 🥚 Optional REPL‑Friendly GUI Access (Easter Egg)

For users who prefer exploring tools interactively—especially those coming from MATLAB or other REPL‑first environments—`pdflinkcheck` includes an optional Easter egg that exposes the GUI launcher directly in the library namespace.

This feature is **disabled by default** and has **no effect on normal imports**.

### Enabling the Easter Egg

Set the environment variable before importing the library:

```python
import os
os.environ["PDFLINKCHECK_GUI_EASTEREGG"] = "true"

import pdflinkcheck
pdflinkcheck.start_gui()
```

Accepted values include: `true`, `1`, `yes`, `on` (case‑insensitive).

### Purpose

This opt‑in behavior is designed to make the library feel welcoming to beginners who are experimenting in a Python REPL for the first time. When enabled, the `start_gui()` function becomes available at the top level:

```python
pdflinkcheck.start_gui()
```

If the `PDFLINKCHECK_GUI_EASTEREGG` environment variable is not set—or if GUI support is unavailable—`pdflinkcheck` behaves as a normal library with no GUI functions exposed.

### Another Easter Egg

```bash
DEV_TYPER_HELP_TREE=1 pdflinkcheck help-tree
```

This `help-tree` feature has not yet been submitted for inclusion into Typer.

-----

## ⚠️ Compatibility Notes

### Platform Compatibility: 

This tool relies on the `PyMuPDF` library. 
All testing has failed to run in a **Termux (Android)** environment due to underlying C/C++ library compilation issues with PyMuPDF. 
It is recommended for use on standard Linux, macOS, or Windows operating systems.

#### Termux Compatibility as a Key Goal
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
- Web-stack GUI rather than Tkinter, to be compatible with Termux.
- A different license from the AGPL3, if we choose at that time.

In the meantime, the standalone binaries and pipx installation provide excellent cross-platform support on Windows, macOS, and standard Linux desktops/laptops.

### Document Compatibility: 
While `pdflinkcheck` uses the robust PyMuPDF library, not all PDF files can be processed successfully. This tool is designed primarily for digitally generated (vector-based) PDFs.

Processing may fail or yield incomplete results for:
* **Scanned PDFs** (images of text) that lack an accessible text layer.
* **Encrypted or Password-Protected** documents.
* **Malformed or non-standard** PDF files.

-----

## PDF Library Selection
At long last, `PyMuPDF` is an optional dependency. The default is `pypdf`. All testing has shown identical performance, but the `analyze_pymupdf.py` is more direct and robust than `analyze_pypdf.py`, which requires a lot of intentional parsing. 

Binaries and artifacts that are distibuted with both PDF librarys will include "pymupdf" in the filename. The GUI and CLI interfaces both allow selection of the library; if PyMuPDF is selected but is not available, the user will be warned.

To install the complete version use one of these options:

```bash
pip install "pdflinkcheck[full]"
pipx install "pdflinkcheck[full]"
uv tool install "pdflinkcheck[full]"
uv add "pdflinkcheck[full]"
```

-----

## Run from Source (Developers)

```bash
git clone http://github.com/city-of-memphis-wastewater/pdflinkcheck.git
cd pdflinkcheck
uv sync
uv run python src/pdflinkcheck/cli.py --help
```

-----

## 📜 License Implications (AGPLv3+)

**`pdflinkcheck` is licensed under the `GNU Affero General Public License` version 3 or later (`AGPLv3+`).**

The `AGPL3+` is required because `pdflinkcheck` uses `PyMuPDF`, which is licensed under the `AGPL3`.

This license has significant implications for **distribution and network use**, particularly for organizations:

  * **Source Code Provision:** If you distribute this tool (modified or unmodified) to anyone, you **must** provide the full source code under the same license.
  * **Network Interaction (Affero Clause):** If you modify this tool and make the modified version available to users over a computer network (e.g., as a web service or backend), you **must** also offer the source code to those network users.

> **Before deploying or modifying this tool for organizational use, especially for internal web services or distribution, please ensure compliance with the AGPLv3+ terms.**

Links:
- Source code: https://github.com/City-of-Memphis-Wastewater/pdflinkcheck/  
- Official AGPLv3 Text (FSF): https://www.gnu.org/licenses/agpl-3.0.html

Copyright © 2025 George Clayton Bennett
