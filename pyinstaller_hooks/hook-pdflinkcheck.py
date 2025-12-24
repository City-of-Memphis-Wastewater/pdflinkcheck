# pyinstaller_hooks/hook-pdflinkcheck.py
"""
When PyInstaller starts packaging, it does the following:

It sees the project is importing modules and packages (like pdflinkcheck).

It checks all hook directories (including the one specified in build_executable.py) for a file named hook-PACKAGENAME.py.
"""
# This collects all files specified as package data in the setup configuration. 
# This ensures that files force-copied to src/pdflinkcheck/data/ (like pyproject.toml) are bundled into the EXE.
# This is required for runtime resource discovery via importlib.resources.
# PyInstaller needs this explicit instruction for importlib.resources to work properly 
# within the bundled executable.

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs
#datas = collect_data_files("pymupdf")
datas = collect_data_files('pdflinkcheck')
binaries = collect_dynamic_libs("pymupdf")