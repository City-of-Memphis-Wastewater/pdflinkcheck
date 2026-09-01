# src/pdflinkcheck/context.py
from __future__ import annotations

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
SRC_DIR = PACKAGE_DIR.parent            
PROJECT_ROOT = SRC_DIR.parent

def get_app_dir(app_name:str) -> Path:
    path = Path.home() / f".{app_name}"
    path.mkdir(parents=True, exist_ok=True)
    return path

APP_NAME = "pdflinkcheck"
APP_NAME_PRETTY = "PDFLinkCheck"
APP_DIR = get_app_dir(APP_NAME)
IMPORT_NAME = "pdflinkcheck"

LOG_FILE_PATH = APP_DIR / f"{APP_NAME}.log"
SRC_FOLDER_NAME = IMPORT_NAME
SERVICE = APP_NAME

CONFIG_PATH = APP_DIR / "config.json"
SECRET_PATH = APP_DIR / "vault.db"
ENV_PATH = PROJECT_ROOT / ".env"