# src/pdflinkcheck/build.py
import shutil
import sys
from pathlib import Path
# --- COPYING LICENSE FILE TO PACKAGE DATA ---
def ensure_package_license(source_root_path: Path, package_data_path: Path):
    """Copies the root LICENSE file into the expected package data path."""
    source = source_root_path / "LICENSE"
    destination = package_data_path / "src" / "pdflinkcheck" / "data" / "LICENSE"

    if not source.exists():
        print(f"FATAL: Root license file not found at {source}!", file=sys.stderr)
        sys.exit(1)

    print(f"Ensuring package license is copied to: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True) # Ensure data dir exists
    shutil.copy2(source, destination) # copy2 preserves metadata