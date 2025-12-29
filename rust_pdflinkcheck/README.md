# Rust PDF Link Check Core

This is the high-performance core for PDF analysis.

## Prerequisites
This project requires the Pdfium shared library.

### Setup (Linux x64)
To download the required library binaries:
```bash
wget [https://github.com/bblanchon/pdfium-binaries/releases/latest/download/pdfium-linux-x64.tgz](https://github.com/bblanchon/pdfium-binaries/releases/latest/download/pdfium-linux-x64.tgz)
tar -xvf pdfium-linux-x64.tgz
cp lib/libpdfium.so .
