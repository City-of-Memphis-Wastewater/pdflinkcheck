#!/usr/bin/env python3 
# SPDX-License-Identifier: MIT
# src/pdflinkcheck/paths.py
from __future__ import annotations
import sys
from pathlib import Path

# --- Configuration ---

# Define the base directory for pdflinkcheck data (~/.pdflinkcheck)
try:
    # Use the home directory and append the tool's name
    PDFLINKCHECK_HOME = Path.home() / ".pdflinkcheck"
except Exception:
    # Fallback if Path.home() fails in certain environments (e.g., some CI runners)
    PDFLINKCHECK_HOME = Path("/tmp/.pdflinkcheck_temp")

# Ensure the directory exists
PDFLINKCHECK_HOME.mkdir(parents=True, exist_ok=True)

# Define the log file path
LOG_FILE_PATH = PDFLINKCHECK_HOME / "pdflinkcheck_errors.log"
