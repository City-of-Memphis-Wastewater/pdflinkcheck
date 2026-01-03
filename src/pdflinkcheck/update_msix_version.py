# src/pdflinkcheck/update_msix_version.py
from __future__ import annotations
from pathlib import Path
from pdflinkcheck.version_info import get_version_from_pyproject

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

UNVERSIONED_MANIFEST = PROJECT_ROOT / "msix" / "AppxManifest_unversioned.xml"
OUTPUT_MANIFEST = PROJECT_ROOT / "msix" / "AppxManifest.xml"


PLACEHOLDER = "@@VERSION_PLACEHOLDER@@"


def generate_versioned_manifest(version):

    # Pad to four parts: 1.1 -> 1.1.0.0, 1.1.92 -> 1.1.92.0
    parts = version.split(".")
    if len(parts) == 2:
        parts += ["0", "0"]
    elif len(parts) == 3:
        parts.append("0")
    elif len(parts) > 4:
        raise ValueError(f"Version has too many parts: {version}")

    msix_version = ".".join(parts[:4])

    if not UNVERSIONED_MANIFEST.exists():
        raise FileNotFoundError(f"Unversioned manifest not found: {UNVERSIONED_MANIFEST}")

    text = UNVERSIONED_MANIFEST.read_text(encoding="utf-8")

    placeholder_full = f'Version="{PLACEHOLDER}"'

    if placeholder_full not in text:
        raise ValueError(f"Placeholder {placeholder_full} not found in the unversioned manifest!")

    updated_text = text.replace(placeholder_full, f'Version="{msix_version}"')

    # Ensure the directory exists and write the new manifest
    OUTPUT_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MANIFEST.write_text(updated_text, encoding="utf-8")

    print(f"Successfully generated AppxManifest.xml with version {msix_version}")


if __name__ == "__main__":
    version = get_version_from_pyproject()
    generate_versioned_manifest(version)
