import xml.etree.ElementTree as ET
from pathlib import Path
from pdflinkcheck.version_info import get_version_from_pyproject

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Register all namespaces to use proper prefixes
ET.register_namespace('', "http://schemas.microsoft.com/appx/manifest/foundation/windows10")
ET.register_namespace('uap', "http://schemas.microsoft.com/appx/manifest/uap/windows10")
ET.register_namespace('rescap', "http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities")

def update_appxmanifest_version(manifest_path: Path, new_version: str):
    # Pad version to 4 parts: 1.1.90 -> 1.1.90.0
    parts = new_version.split(".")
    if len(parts) == 2:
        parts += ["0", "0"]
    elif len(parts) == 3:
        parts.append("0")
    elif len(parts) > 4:
        raise ValueError(f"Version has too many parts: {new_version}")
    
    msix_version = ".".join(parts[:4])

    # Parse the file
    tree = ET.parse(manifest_path)
    root = tree.getroot()

    # Find the Identity element using the default namespace
    identity = root.find("./{http://schemas.microsoft.com/appx/manifest/foundation/windows10}Identity")
    if identity is None:
        raise ValueError("No <Identity> element found in manifest")

    # Update the Version attribute
    identity.set("Version", msix_version)
    print(f"Updated AppxManifest.xml version to {msix_version}")

    # Write back with proper XML declaration and UTF-8 encoding
    tree.write(
        manifest_path,
        encoding="utf-8",
        xml_declaration=True,
        default_namespace="http://schemas.microsoft.com/appx/manifest/foundation/windows10",  # This keeps <Package>, not <ns0:Package>
        method="xml"
    )

if __name__ == "__main__":
    manifest_path = PROJECT_ROOT / "msix" / "AppxManifest.xml"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found at {manifest_path}")
    
    version = get_version_from_pyproject()
    update_appxmanifest_version(manifest_path, version)
