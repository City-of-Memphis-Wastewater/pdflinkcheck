#!/usr/bin/env python3
import os
os.environ["FORCE_COLOR"] = "1"
os.environ["TERM"] = "xterm-256color"

# Now run the real entry point
from pdflinkcheck.cli import app
import sys
from typer import run

if __name__ == "__main__":
    run(app)
