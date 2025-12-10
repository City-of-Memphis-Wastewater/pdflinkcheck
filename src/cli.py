# src/cli.py
from __future__ import annotations 
import typer
from rich.console import Console
from pathlib import Path

from pdflinkcheck.analyze import call_stable


### Pipeline CLI

app = typer.Typer(
    help="CLI utility for analyzing PDF hyperlinks and finding missing remnants.",
    no_args_is_help=False
)
console = Console()

@app.command(name="analyze", help="Show the stable analysis command")
def analyze():
    call_stable()