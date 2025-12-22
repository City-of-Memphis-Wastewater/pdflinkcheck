# pdflinkcheck

A purpose-built tool for comprehensive analysis of hyperlinks and GoTo links within PDF documents. Users may leverage either the PyMuPDF or the pypdf library. Use the CLI or the GUI.

-----

![Screenshot of the pdflinkcheck GUI](https://raw.githubusercontent.com/City-of-Memphis-Wastewater/pdflinkcheck/main/assets/pdflinkcheck_gui_v1.1.79.png)

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
pipx install pdflinkcheck[full]

# On Termux
pipx install pdflinkcheck

```

-----

## 💻 Graphical User Interface (GUI)

The tool can be run as simple cross-platform graphical interface (Tkinter).

### Launching the GUI

Ways to launch the GUI interface:
1.  **Implicit Launch:** Run the tool or file with no arguments, subcommands, or flags. (Note: PyInstaller builds use the --noconsole flag, except for on Termux.)
2.  **Explicit Command:** Use the dedicated GUI subcommand (`pdflinkcheck gui`).

-----

## 🚀 CLI Usage

The core functionality is accessed via the `analyze` command. 

`DEV_TYPER_HELP_TREE=1 pdflinkcheck help-tree`:
![Screenshot of the pdflinkcheck CLI Tree Help](https://raw.githubusercontent.com/City-of-Memphis-Wastewater/pdflinkcheck/main/assets/pdflinkcheck_cli_v1.1.79_tree_help.png)

`pdflinkcheck --help`:
![Screenshot of the pdflinkcheck CLI Tree Help](https://raw.githubusercontent.com/City-of-Memphis-Wastewater/pdflinkcheck/main/assets/pdflinkcheck_cli_v1.1.79.png)


### Available Commands

|**Command**|**Description**|
|---|---|
|`pdflinkcheck analyze`|Analyzes a PDF file for links |
|`pdflinkcheck gui`|Explicitly launch the Graphical User Interface.|
|`pdflinkcheck docs`|Access documentation, including the README and AGPLv3+ license.|

### `analyze` Command Options

|**Option**|**Description**|**Default**|
|---|---|---|
|`<PDF_PATH>`|**Required.** The path to the PDF file to analyze.|N/A|
|`--pdf-library / -p`|Select engine: `pymupdf` or `pypdf`.|`pypdf`|
|`--export-format / -e`|Export to `JSON`, `TXT`, or `None` to suppress file output.|`JSON`|
|`--max-links / -m`|Maximum links to display per section. Use `0` for all.|`0`|

### `gui` Command Options

| **Option**             | **Description**                                                                                               | **Default**    |
| ---------------------- | ------------------------------------------------------------------------------------------------------------- | -------------- |
| `--auto-close INTEGER` | **(For testing/automation only).** Delay in milliseconds after which the GUI window will automatically close. | `0` (Disabled) |

#### Example Runs

```bash 
# Analyze a document, show all links, and save the report as JSON and TXT
pdflinkcheck analyze "TE Maxson WWTF O&M Manual.pdf" --export-format JSON,TXT

# Analyze a document but keep the print block short, showing only the first 10 links for each type
pdflinkcheck analyze "TE Maxson WWTF O&M Manual.pdf" --max-links 10

# Show the GUI for only a moment, like in a build check
pdflinkcheck gui --auto-close 3000 

# Show both the LICENSE and README.md docs
pdflinkcheck docs --license --readme 
```

-----

## 📦 Library Access (Advanced)

For developers importing `pdflinkcheck` into other Python projects, the core analysis functions are exposed directly in the root namespace:

|**Function**|**Description**|
|---|---|
|`run_report()`|**(Primary function)** Performs the full analysis, prints to console, and handles file export.|
|`extract_links_pynupdf()`|Function to retrieve all explicit links (URIs, GoTo, etc.) from a PDF path.|
|`extract_toc_pymupdf()`|Function to extract the PDF's internal Table of Contents (bookmarks/outline).|
|`extract_links_pynupdf()`|Function to retrieve all explicit links (URIs, GoTo, etc.) from a PDF path, using the pypdf library.|
|`extract_toc_pymupdf()`|Function to extract the PDF's internal Table of Contents (bookmarks/outline), using the pypdf library.|

Exanple:

```python
from pdflinkcheck.report import run_report
from pdflinkcheck.analysis_pymupdf import extract_links_pymupdf, extract_toc_pymupdf                                                                          130 from pdflinkcheck.analysis_pymupdf import extract_links_pynupdf, extract_toc_pymupdf
from pdflinkcheck.analysis_pypdf import extract_links_pypdf, extract_toc_pypdf

file = "document1.pdf"
report_data = run_report(file)
links_pymupdf = extract_links_pymupdf(file)
links_pypdf = extract_links_pypdf(file)
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

#### Termux Compatibility as a Key Goal
A key goal of City-of-Memphis-Wastewater is to release all software as Termux-compatible.

Termux compatibility is important in the modern age as Android devices are common among technicians, field engineers, and maintenace staff. 
Android is the most common operating system in the Global South. 
We aim to produce stable software that can do the most possible good. 

While using `PyMuPDF` in Python dependency resolution on Termux simply isn't possible, we are proud to have achieved a work-around by implementing a parallel solution in `pypdf`! 
Now, there is PDF Engine selection in both the CLI and the GUI. 
`pypdf` is the default in pdflinkcheck.report.run_report(); PyMuPDF can be explicitly requested in the CLI and is the default in the TKinter GUI.

Now `pdflinkcheck` can run on Termux by using the `pypdf` engine. 
Benefits:
- `pypdf`-only artifacts, to reduce size to about 6% compared to artifacts that include `PyMuPDF`.
- Web-stack GUI as an alternative to the Tkinter GUI, which can be run locally on Termux or as a web app.

Because it works, we plan to keep the `PyMuPDF` portion of the codebase.

### Document Compatibility: 
Not all PDF files can be processed successfully. This tool is designed primarily for digitally generated (vector-based) PDFs.

Processing may fail or yield incomplete results for:
* **Scanned PDFs** (images of text) that lack an accessible text layer.
* **Encrypted or Password-Protected** documents.
* **Malformed or non-standard** PDF files.

-----

## PDF Library Selection
At long last, `PyMuPDF` is an optional dependency. The default is `pypdf`. All testing has shown identical performance, though the `analyze_pymupdf.py` is faster and more direct and robust than `analyze_pypdf.py`, which requires a lot of intentional parsing. 

Binaries and artifacts are expected to contain PyMuPDF, unless they are build on Android. The GUI and CLI interfaces both allow selection of the library; if PyMuPDF is selected but is not available, the user will be warned.

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

# To include the PyMuPDF dependency in the installation:
uv sync --extras full

# On Termux, to not include PyMuPDF:
uv sync

# To include developer depedecies:
uv sync --all-extras --group dev

# Run the CLI
uv run python src/pdflinkcheck/cli.py --help

# Run a basic webapp and Termux-facing browser-based interface
uv run  python -m pdflinkcheck.stdlib_server
```

-----

## 📜 License Implications (AGPLv3+)

**`pdflinkcheck` is licensed under the `GNU Affero General Public License` version 3 or later (`AGPLv3+`).**

The `AGPL3+` is required for this codebase because `pdflinkcheck` uses `PyMuPDF`, which is licensed under the `AGPL3`.
However, (nearly) every file in thie codebase is explicitly labeled as MIT-licensed. I did not reuse any lines of PyMuPDF, and I have only referenced PyMuPDF functions.

To stay in compliance, the AGPL3 license text is readily available in the CLI and the GUI, and it is included in the build artifacts.
The `AGPL3` appears as the primary license file in the source code. While this infers that the entire project is AGPL3-licensed, this is not true - portions of the codebase are MIT-licensed.

This license has significant implications for **distribution and network use**, particularly for organizations:

  * **Source Code Provision:** If you distribute this tool (modified or unmodified) to anyone, you **must** provide the full source code under the same license.
  * **Network Interaction (Affero Clause):** If you modify this tool and make the modified version available to users over a computer network (e.g., as a web service or backend), you **must** also offer the source code to those network users.

> **Before deploying or modifying this tool for organizational use, especially for internal web services or distribution, please ensure compliance with the AGPLv3+ terms.**

Because the AGPLv3 is a strong copyleft license, any version of `pdflinkcheck` that includes AGPL‑licensed components (such as `PyMuPDF`) must be distributed as a whole under AGPLv3+. This means that for those versions, anyone who distributes the application—or makes a modified version available over a network—must also provide the complete corresponding source code under the same terms.

However, the MIT‑licensed portions of the codebase remain MIT regardless of the overall project license. They may be reused independently in other projects without triggering AGPL obligations.

If a future version of `pdflinkcheck` removes all AGPL‑licensed dependencies, that version would no longer be subject to AGPLv3+ requirements.

Links:
- Source code: https://github.com/City-of-Memphis-Wastewater/pdflinkcheck/  
- PyMuPDF source code: https://github.com/pymupdf/PyMuPDF/
- pypdf source code: https://github.com/py-pdf/pypdf/
- Official AGPLv3 Text (FSF): https://www.gnu.org/licenses/agpl-3.0.html

Copyright © 2025 George Clayton Bennett
