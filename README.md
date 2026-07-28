# PDFLinkCheck

PDFLinkCheck validates hyperlinks and navigation destinations inside PDF documents. It is available as a Python library, command-line tool, and desktop GUI.

## Metadata

**Type:** Python library + CLI + GUI

**Primary purpose:** Validate hyperlinks and navigation inside PDF documents.

**Input:** PDF files

**Output:** Link validation reports, in JSON, XLSX, and TXT.

**Platforms:** Windows, Linux, macOS

**Python:** 3.9+

## Features

PDFLinkCheck analyzes PDF files for:

- External web links (`http`, `https`)
- Internal PDF destinations (`GoTo`)
- External PDF destinations (`GoToR`)
- Broken and unresolved references
- Link inventory and reporting

Designed for documentation QA, publishing pipelines, engineering document control, and automated validation.


## Install

CLI application:

```bash
pipx install "pdflinkcheck[pdfium]"
```

Python library:

```bash
pip install "pdflinkcheck[pdfium]"
```

## Quick Start

GUI

```bash
pdflinkcheck gui
```

CLI

```bash
pdflinkcheck analyze document.pdf
```

Web App

```bash
pdflinkcheck --debug serve
```

Library usage

```python
import pdflinkcheck

# Script pdf analysis and export handling ...
```

## Documentation

Documentation:

https://city-of-memphis-wastewater.github.io/pdflinkcheck/

## CLI

```bash
pdflinkcheck helptree
```

<p align="center">
  <img src="https://raw.githubusercontent.com/City-of-Memphis-Wastewater/pdflinkcheck/main/assets/pdflinkcheck_v1.5.14_helptree.svg" width="100%" alt="SVG of the pdflinkcheck CLI helptree">
</p>

## Screenshot

<p align="center">
<img src="https://raw.githubusercontent.com/City-of-Memphis-Wastewater/pdflinkcheck/main/assets/pdflinkcheck_gui_v1.3.3.png" width="900">
</p>

## License

MIT
