# hook-pdflinkcheck.py
from PyInstaller.utils.hooks import collect_data_files

# This collects all files specified as package data in the setup configuration 
# (e.g., pyproject.toml's [tool.setuptools.package-data]) for the package 'pdflinkcheck'.
# PyInstaller needs this explicit instruction for importlib.resources to work properly 
# within the bundled executable.

datas = collect_data_files('pdflinkcheck')