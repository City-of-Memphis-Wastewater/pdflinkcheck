#!/usr/bin/env python3 
# SPDX-License-Identifier: MIT
# src/pdflinkcheck/cli.py
from __future__ import annotations
import typer
from typing import Literal, List
from typer.models import OptionInfo
from rich.console import Console
from pathlib import Path
from typing import Dict, Optional, Union, List
import pyhabitat
import sys
import os
from importlib.resources import files
from typer_helptree import add_typer_helptree

from pdflinkcheck.report import run_report_and_call_exports 
from pdflinkcheck._version import __version__
from pdflinkcheck.io import get_first_pdf_in_cwd
from pdflinkcheck.environment import (
    is_in_dev_environment,
    pymupdf_is_available, 
    pdfium_is_available
)
from pdflinkcheck.helpers import ExportFormat, ExportFormatChoice, PdfEngine, PdfEngineChoice

console = Console() # to be above the tkinter check, in case of console.print

# Force Rich to always enable colors, even when running from a .pyz bundle
os.environ["FORCE_COLOR"] = "1"
# Optional but helpful for full terminal feature detection
os.environ["TERM"] = "xterm-256color"

from enum import Enum
import typer
from typing import List, Optional
from pathlib import Path

app = typer.Typer(
    name="pdflinkcheck",
    help=f"A command-line tool for comprehensive PDF link analysis and reporting. (v{__version__})",
    add_completion=False,
    invoke_without_command = True, 
    no_args_is_help = False,
    context_settings={"ignore_unknown_options": True,
                      "allow_extra_args": True,
                      "help_option_names": ["-h", "--help"]},
)


def debug_callback(value: bool):
    if value:
        # This runs IMMEDIATELY when --debug is parsed, even before --help
         # 1. Access the list of all command-line arguments
        full_command_list = sys.argv
        # 2. Join the list into a single string to recreate the command
        command_string = " ".join(full_command_list)
        # 3. Print the command
        typer.echo(f"command:\n{command_string}\n")
    return value

if "--show-command" in sys.argv or "--debug" in sys.argv: # requires that --show-command flag be used before the sub command
    debug_callback(True)

    
@app.callback()
def main(ctx: typer.Context,
    version: Optional[bool] = typer.Option(
    None, "--version", is_flag=True, help="Show the version."
    ),
    debug: bool = typer.Option(
        False, "--debug", is_flag=True, help="Enable verbose debug logging and echo the full command string."
    ),
    show_command: bool = typer.Option(
        False, "--show-command", is_flag=True, help="Echo the full command string to the console before execution."
    )
    ):
    """
    If no subcommand is provided, launch the GUI.
    """
    if version:
        typer.echo(__version__)
        raise typer.Exit(code=0)
        
    if ctx.invoked_subcommand is None:
        gui_command()
        raise typer.Exit(code=0)


add_typer_helptree(app = app, console = console, version = __version__, hidden = False)

@app.command(name="docs", help="Show the docs for this software.")
def docs_command(
    license: Optional[bool] = typer.Option(
        None, "--license", "-l", help="Show the LICENSE text."
    ),
    readme: Optional[bool] = typer.Option(
        None, "--readme", "-r", help="Show the README.md content."
    ),
):
    """
    Handles the pdflinkcheck docs command, either with flags or by showing help.
    """
    if not license and not readme:
        # If no flags are provided, show the help message for the docs subcommand.
        # Use ctx.invoke(ctx.command.get_help, ctx) if you want to print help immediately.
        # Otherwise, the default behavior (showing help) works fine, but we'll add a message.
        console.print("[yellow]Please use either the --license or --readme flag.[/yellow]")
        return # Typer will automatically show the help message.

    # --- Development Sync Check ---
    # We use your new check to see if we are in a dev context.
    # If so, we trigger the data copy to ensure we aren't viewing stale docs.
    if is_in_dev_environment():
        from pdflinkcheck.datacopy import ensure_data_files_for_build
        ensure_data_files_for_build()
        console.print("[dim italic]Dev mode detected: Synced data files.[/dim italic]")

    # --- Handle --license flag ---
    if license:
        try:
            license_path = files("pdflinkcheck.data") / "LICENSE"
            license_text = license_path.read_text(encoding="utf-8")
            console.print(f"\n[bold green]=== LICENSE ===[/bold green]")
            console.print(license_text, highlight=False)
            
        except FileNotFoundError:
            console.print("[bold red]Error:[/bold red] The embedded license file could not be found.")
            raise typer.Exit(code=1)

    # --- Handle --readme flag ---
    if readme:
        try:
            readme_path = files("pdflinkcheck.data") / "README.md"
            readme_text = readme_path.read_text(encoding="utf-8")
            
            # Using rich's Panel can frame the readme text nicely
            console.print(f"\n[bold green]=== pdflinkcheck README ===[/bold green]")
            console.print(readme_text, highlight=False)
            
        except FileNotFoundError:
            console.print("[bold red]Error:[/bold red] The embedded README.md file could not be found.")
            raise typer.Exit(code=1)
    
    # Exit successfully if any flag was processed
    raise typer.Exit(code=0)

# Create tools sub-group
tools_app = typer.Typer(help="Additional utility features and maintenance tools.")
app.add_typer(tools_app, name="tools")

@tools_app.command(
        name="check-libs",
        help = "Recheck the PDF library availability and cache the results."
        ) 
def tools_clear_cache():
    """Recheck the PDF library availability."""
    from pdflinkcheck.environment import clear_pdf_library_caches
    clear_pdf_library_caches()
    console.print("[green]PDF library availabilty rechecked.[/green]")
    console.print(f"pymupdf_is_available: {pymupdf_is_available()}")
    console.print(f"pdfium_is_available: {pdfium_is_available()}")
    

@tools_app.command(name="browse-exports")
def tools_browse_exports():
    """Open the system file explorer at the report output directory."""
    from pdflinkcheck.helpers import get_export_path
    
    target_dir = get_export_path()
    console.print(f"Opening: [bold cyan]{target_dir}[/bold cyan]")
    
    try:
        pyhabitat.show_system_explorer(path = target_dir)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)

@app.command(name="analyze") # Added a command name 'analyze' for clarity
def analyze_pdf( # Renamed function for clarity
    pdf_path: Optional[Path] = typer.Argument(
        None, 
        exists=True, 
        file_okay=True, 
        dir_okay=False, 
        readable=True,
        resolve_path=True,
        help="Path to the PDF file to analyze. If omitted, searches current directory."
    ), 
    export_format: List[ExportFormatChoice] = typer.Option(
        [ExportFormat.JSON.name.lower(), ExportFormat.TXT.name.lower(), ExportFormat.XLSX.name.lower()],
        "--format", "-f",
        case_sensitive=False,
        help="Export formats (repeatable). Use '--format none' to suppress all exports."
    ),

    pdf_library: List[PdfEngineChoice] = typer.Option(
        [PdfEngine.resolve_auto_flag().name.lower()],
        "--engine","-e",
        envvar="PDF_ENGINE",
        #help="PDF parsing library. pypdf (pure Python), pymupdf (fast, AGPL3+ licensed), pdfium (fast, BSD-3 licensed).",
        #help=f"PDF parsing library backend choices: {', '.join([k.lower() for k in PdfEngine.__members__ ])}",
        help=f"PDF parsing library backend choice.",
    ),
    print_bool: bool = typer.Option(
        True,
        "--print/--quiet",
        help="Print or do not print the analysis and validation report to console."
    )
):
    """
    Analyzes the specified PDF file for all internal, external, and unlinked references.

    Checks:
    • Internal GoTo links point to valid pages
    • Remote GoToR links point to existing files
    • TOC bookmarks target valid pages

    Validates:
    • Are referenced files available?
    • Are the page numbers referenced by GoTo links within the length of the document?

    """

    """
    Fun Typer fact:
    Overriding Order
    Environment variables sit in the middle of the "priority" hierarchy:

    CLI Flag: (Highest priority) analyze -e pypdf will always win.
    Env Var: If no flag is present, it checks PDF_ENGINE.
    Code Default: (Lowest priority) It falls back to "pypdf" as defined in typer.Option.
    """

    if pdf_path is None:
        pdf_path = get_first_pdf_in_cwd()
        if pdf_path is None:
            console.print("[red]Error: No PDF file provided and none found in current directory.[/red]")
            raise typer.Exit(code=1)
        console.print(f"[dim]No file specified — using: {Path(pdf_path).name}[/dim]")

    
    # Single Source of Truth validation: Check against the enum names + virtual keywords
    for engine in pdf_library:
        cleaned = engine.strip().lower()
        if cleaned not in ("all", "none") and cleaned.upper() not in PdfEngine.__members__:
            # Reconstruct the allowed list on the fly for the error message
            allowed_tokens = [k.lower() for k in PdfEngine.__members__ if k not in ("NONE", "ALL")] + ["all", "none"]
            console.print(f"[red]Error: '{engine}' is not a valid engine choice.[/red]")
            console.print(f"[dim]Choose from: {', '.join(allowed_tokens)}[/dim]")
            raise typer.Exit(code=1)

    # 1. Resolve export formats from the Typer choice enum to your internal Flag
    resolved_format = ExportFormat.NONE
    
    # Handle the virtual keywords first
    if any(f == ExportFormatChoice.NONE for f in export_format):
        resolved_format = ExportFormat.NONE
    elif any(f == ExportFormatChoice.ALL for f in export_format):
        # Assuming your ExportFormat flag has an ALL mask (or combine them)
        resolved_format = ExportFormat.JSON | ExportFormat.TXT | ExportFormat.XLSX
    else:
        # Map the incoming string values directly to your internal Flag enum names
        for f in export_format:
            resolved_format |= ExportFormat[f.name]

    # 2. Resolve PDF engines from the Typer choice enum to your internal Flag
    resolved_engine = PdfEngine(0)
    # The mapping loop reduces down to a clean dictionary lookup
    for choice in pdf_library:
        resolved_engine |= PdfEngine[choice.name]

    # The meat and potatoes
    report_results = run_report_and_call_exports(
        pdf_path=str(pdf_path), 
        export_format = resolved_format,
        pdf_library = resolved_engine,
        print_bool = print_bool,
        concise_print = True # ideal for CLI, to not overwhelm the terminal.
    )

    if not report_results or not report_results.get("data"):
        console.print("[yellow]No links or TOC found — nothing to validate.[/yellow]")
        raise typer.Exit(code=0)

@app.command(name="serve")
def serve(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host to bind (use 0.0.0.0 for network access)"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to listen on"),
    reload: bool = typer.Option(False, "--reload", is_flag=True, help="Auto-reload on code changes (dev only)"),
):
    """
    Start the built-in web server for uploading and analyzing PDFs in the browser.

    Pure stdlib — no extra dependencies. Works great on Termux!
    """
    console.print(f"[bold green]Starting pdflinkcheck web server[/bold green]")
    console.print(f"   → Open your browser at: [bold blue]http://{host}:{port}[/bold blue]")
    console.print(f"   → Upload a PDF to analyze links and TOC")
    if reload:
        console.print("   → [yellow]Reload mode enabled[/yellow]")

    # Import here to avoid slow imports on other commands
    from pdflinkcheck.stdlib_server import main as stdlib_server_main# ThreadedHTTPServer, PDFLinkCheckHandler
    import socketserver

    try:
        stdlib_server_main()
        #with ThreadedTCPServer((host, port), PDFLinkCheckHandler) as httpd:
        #    console.print(f"[green]Server running — press Ctrl+C to stop[/green]\n")
        #    httpd.serve_forever()
    except OSError as e:
        if "Address already in use" in str(e):
            console.print(f"[red]Error: Port {port} is already in use.[/red]")
            console.print("Try a different port with --port 8080")
        else:
            console.print(f"[red]Server error: {e}[/red]")
        raise typer.Exit(code=1)
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Server stopped.[/bold yellow]")
        raise typer.Exit(code=0)

        
@app.command(name="gui") 
def gui_command(
    auto_close: int = typer.Option(0, 
                                   "--auto-close", "-c", 
                                   help = "Delay in milliseconds after which the GUI window will close (for automated testing). Use 0 to disable auto-closing.",
                                   min=0)
    )->None:
    """
    Launch tkinter-based GUI.
    """
    assured_auto_close_value = 0
    
    if isinstance(auto_close, OptionInfo):
        # Case 1: Called implicitly from main() (pdflinkcheck with no args)
        # We received the metadata object, so use the function's default value (0).
        # We don't need to do anything here since final_auto_close_value is already 0.
        pass 
    else:
        # Case 2: Called explicitly by Typer (pdflinkcheck gui -c 3000)
        # Typer has successfully converted the command line argument, and auto_close is an int.
        assured_auto_close_value = int(auto_close)

    if not pyhabitat.tkinter_is_available():
        _gui_failure_msg()
        return
    
    from pdflinkcheck.gui import start_gui
    start_gui(time_auto_close = assured_auto_close_value)

def parse_engine_flags(values: Optional[List[str]]) -> PdfEngine:
    """
    Callback that converts incoming repeatable CLI engine strings 
    into a unified type-safe PdfEngine bitmask.
    """
    if not values:
        return PdfEngine.AUTO

    combined_mask = PdfEngine.NONE
    for val in values:
        # Match against our robust internal parser logic
        parsed = PdfEngine.from_str(val)
        if parsed == PdfEngine.NONE and val.strip().lower() != "none":
            raise typer.BadParameter(
                f"'{val}' is not a valid engine choice. Choose from: auto, pypdf, pymupdf, pdfium, all."
            )
        combined_mask |= parsed
    return combined_mask

# --- Helper, consistent gui failure message. --- 
def _gui_failure_msg():
    console.print("[bold red]GUI failed to launch[/bold red]")
    console.print("Use 'pdflinkcheck analyze CLI' instead.")
    console.print(f"pyhabitat.tkinter_is_available() = {pyhabitat.tkinter_is_available()}")
    console.print(f"pyhabitat.on_termux() = {pyhabitat.on_termux()}")


if __name__ == "__main__":
    app()
    
