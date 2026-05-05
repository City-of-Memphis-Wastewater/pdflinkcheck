from __future__ import annotations
import sys
import tomllib # or tomli for older python
import tomli_w
from pathlib import Path

def prepare(mode):
    path = Path("pyproject.toml")
    data = tomllib.loads(path.read_text())
    
    if mode == "mit":
        data["project"]["name"] = "pdflinkcheck-mit"
        data["project"]["license"] = {"text": "MIT"}
        # Remove AGPL dependencies entirely
        if "optional-dependencies" in data["project"]:
            data["project"]["optional-dependencies"].pop("pymupdf", None)
            data["project"]["optional-dependencies"].pop("full", None)
        # Update entry point
        data["project"]["scripts"]["pdflinkcheck-mit"] = "pdflinkcheck.cli:app"

    elif mode == "agpl":
        data["project"]["name"] = "pdflinkcheck-agpl"
        data["project"]["license"] = {"text": "AGPL-3.0-or-later"}
        # Force PyMuPDF into core dependencies
        data["project"]["dependencies"].append("pymupdf>=1.24.0,<2.0.0")
        data["project"]["scripts"]["pdflinkcheck-agpl"] = "pdflinkcheck.cli:app"

    path.write_text(tomli_w.dumps(data))

if __name__ == "__main__":
    prepare(sys.argv[1])
