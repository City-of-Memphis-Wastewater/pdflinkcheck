# src/pdflinkcheck/datacopy.py
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# --- COPY LICENSE FILE TO PACKAGE DATA ---
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

# --- COPY README FILE TO PACKAGE DATA ---
def ensure_package_readme(source_root_path: Path, package_data_path: Path):
    """Copies the root README.md file into the expected package data path."""
    source = source_root_path / "README.md"
    destination = package_data_path / "src" / "pdflinkcheck" / "data" / "README.md"

    if not source.exists():
        print(f"FATAL: Root README file not found at {source}!", file=sys.stderr)
        sys.exit(1)

    print(f"Ensuring package README is copied to: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True) # Ensure data dir exists
    shutil.copy2(source, destination) # copy2 preserves metadata


def ensure_data_files_for_build():
    print(f"PROJECT_ROOT = {PROJECT_ROOT}")
    ensure_package_license(PROJECT_ROOT, PROJECT_ROOT)
    ensure_package_readme(PROJECT_ROOT, PROJECT_ROOT)

if __name__ == "__main__":
    ensure_data_files_for_build()