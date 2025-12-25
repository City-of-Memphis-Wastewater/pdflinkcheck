import xml.etree.ElementTree as ET
from pathlib import Path
from pdflinkcheck.version_info import get_version_from_pyproject

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

def update_appxmanifest_version(manifest_path: Path, new_version: str):
    # MSIX versions must be in Major.Minor.Build.Revision format (4 parts, each 0-65535)
    parts = new_version.split(".")
    if len(parts) == 2:
        parts += ["0", "0"]  # e.g., 1.1 -> 1.1.0.0
    elif len(parts) == 3:
        parts += ["0"]       # e.g., 1.1.90 -> 1.1.90.0
    elif len(parts) > 4:
        raise ValueError("Version has too many parts")
    
    msix_version = ".".join(parts[:4])
    
    tree = ET.parse(manifest_path)
    root = tree.getroot()
    
    # Namespaces
    ns = {"default": "http://schemas.microsoft.com/appx/manifest/foundation/windows10"}
    identity = root.find("./default:Identity", namespaces=ns)
    if identity is None:
        raise ValueError("No <Identity> element found")
    
    identity.set("Version", msix_version)
    
    tree.write(manifest_path, encoding="utf-8", xml_declaration=True)
    print(f"Updated AppxManifest.xml version to {msix_version}")

if __name__ == "__main__":
    manifest_path = PROJECT_ROOT / "msix" / "AppxManifest.xml"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found at {manifest_path}")
    
    version = get_version_from_pyproject()
    update_appxmanifest_version(manifest_path, version)