# src/pdflinkcheck/_version.py
from pathlib import Path

def get_version() -> str:
    
    # Try local VERSION file (Source/Dev)
    try:
        # __file__ is src/pdflinkcheck/_version.py
        # VERSION is src/pdflinkcheck/VERSION
        version_file = Path(__file__).parent / "VERSION"
        if version_file.exists():
            return version_file.read_text(encoding="utf-8").strip()
    except Exception:
        pass
    
    # Try metadata (Installed)
    try:
        from importlib.metadata import version, PackageNotFoundError
        return version("pdflinkcheck")
    except (ImportError, PackageNotFoundError):
        pass


    return "0.0.0-unknown"

__version__ = get_version()