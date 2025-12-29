#!/usr/bin/env python3 
# SPDX-License-Identifier: MIT
# src/pdflinkcheck/cli.py
import typer
from typing import Literal
from typer.models import OptionInfo
from rich.console import Console
from pathlib import Path
from pdflinkcheck.report import run_report_and_call_exports # Assuming core logic moves here
from typing import Dict, Optional, Union, List
import pyhabitat
import sys
import os
from importlib.resources import files

from pdflinkcheck.version_info import get_version_from_pyproject
from pdflinkcheck.validate import run_validation 
from pdflinkcheck.environment import is_in_git_repo, assess_default_pdf_library
from pdflinkcheck.io import get_first_pdf_in_cwd

console = Console() # to be above the tkinter check, in case of console.print

app = typer.Typer(
    name="pdflinkcheck",
    help=f"A command-line tool for comprehensive PDF link analysis and reporting. (v{get_version_from_pyproject()})",
    add_completion=False,
    invoke_without_command = True, 
    no_args_is_help = False,
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
)


def debug_callback(value: bool):
#def debug_callback(ctx: typer.Context, value: bool):
    if value:
        # This runs IMMEDIATELY when --debug is parsed, even before --help
         # 1. Access the list of all command-line arguments
        full_command_list = sys.argv
        # 2. Join the list into a single string to recreate the command
        command_string = " ".join(full_command_list)
        # 3. Print the command
        typer.echo(f"command:\n{command_string}\n")
    return value

if "--show-command" in sys.argv or "--debug" in sys.argv:
    debug_callback(True)
    
@app.callback()
def main(ctx: typer.Context,
    version: Optional[bool] = typer.Option(
    None, "--version", is_flag=True, help="Show the version."
    )
    ):
    """
    If no subcommand is provided, launch the GUI.
    """
    if version:
        typer.echo(get_version_from_pyproject())
        raise typer.Exit(code=0)
        
    if ctx.invoked_subcommand is None:
        gui_command()
        raise typer.Exit(code=0)


# help-tree() command: fragile, experimental, defaults to not being included.
if os.environ.get('DEV_TYPER_HELP_TREE',0) in ('true','1'):
    from pdflinkcheck.dev import add_typer_help_tree
    add_typer_help_tree(
        app = app,
        console = console)

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

    if is_in_git_repo():
        """This is too aggressive. But we don't expect it often. Probably worth it."""
        from pdflinkcheck.datacopy import ensure_data_files_for_build
        ensure_data_files_for_build()

    # --- Handle --license flag ---
    if license:
        try:
            license_path = files("pdflinkcheck.data") / "LICENSE"
            license_text = license_path.read_text(encoding="utf-8")
            console.print(f"\n[bold green]=== GNU AFFERO GENERAL PUBLIC LICENSE V3+ ===[/bold green]")
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

@app.command(name="tools", help= "Additional features, hamburger menu.")
def tools_command(
    clear_cache: bool = typer.Option(
        False,
        "--clear-cache",
        is_flag=True,
        help="Clear the environment caches. \n - pymupdf_is_available() \n - is_in_git_repo() \nMain purpose: Run after adding PyMuPDF to an existing installation where it was previously missing, because pymupdf_is_available() would have been cached as False."
    )
    ):
    from pdflinkcheck.environment import clear_all_caches
    if clear_cache:
        clear_all_caches()

"""
def validate_pdf_commands(
    pdf_path: Optional[Path] = typer.Argument(
        None,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Path to the PDF file to validate. If omitted, searches current directory."
    ),
    pdf_library: Literal["pypdf", "pymupdf"] = typer.Option(
        "pypdf",
        "--library", "-l",
        envvar="PDF_ENGINE",
        help="PDF parsing engine: pypdf (pure Python) or pymupdf (faster, if available)"
    ),
    """
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
    export_format: Optional[Literal["JSON", "TXT", "JSON,TXT", "NONE"]] = typer.Option(
        "JSON,TXT", 
        "--export-format","-e",
        case_sensitive=False, 
        help="Export format. Use 'None' to suppress file export.",
    ),

    pdf_library: Literal["auto","rust","pypdf", "pymupdf"] = typer.Option(
        assess_default_pdf_library(),
        "--pdf-library","-p",
        envvar="PDF_ENGINE",
        help="PDF parsing library. pypdf (pure Python) or pymupdf (faster, if available).",
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

    CLI Flag: (Highest priority) analyze -p pypdf will always win.

    Env Var: If no flag is present, it checks PDF_ENGINE.

    Code Default: (Lowest priority) It falls back to "pypdf" as defined in typer.Option.
    """

    if pdf_path is None:
        pdf_path = get_first_pdf_in_cwd()
        if pdf_path is None:
            console.print("[red]Error: No PDF file provided and none found in current directory.[/red]")
            raise typer.Exit(code=1)
        console.print(f"[dim]No file specified — using: {Path(pdf_path).name}[/dim]")

    pdf_path_str = str(pdf_path)

    VALID_FORMATS = ("JSON") # extend later
    requested_formats = [fmt.strip().upper() for fmt in export_format.split(",")]
    if "NONE" in requested_formats or not export_format.strip() or export_format == "0":
        export_formats = ""
    else:
        # Filter for valid ones: ("JSON", "TXT")
        # This allows "JSON,TXT" to become "JSONTXT" which run_report logic can handle
        valid = [f for f in requested_formats if f in ("JSON", "TXT")]
        export_formats = "".join(valid)

        if not valid and "NONE" not in requested_formats:
            typer.echo(f"Warning: No valid formats found in '{export_format}'. Supported: JSON, TXT.")

    # The meat and potatoes
    report_results = run_report_and_call_exports(
        pdf_path=str(pdf_path), 
        export_format = export_formats,
        pdf_library = pdf_library,
    )

    if not report_results or not report_results.get("data"):
        console.print("[yellow]No links or TOC found — nothing to validate.[/yellow]")
        raise typer.Exit(code=0)

    validation_results = report_results["data"]["validation"]
    # Optional: fail on broken links
    broken_count = validation_results["summary-stats"]["broken-page"] + validation_results["summary-stats"]["broken-file"]
    
    if broken_count > 0:
        console.print(f"\n[bold yellow]Warning:[/bold yellow] {broken_count} broken link(s) found.")
    else:
        console.print(f"\n[bold green]Success:[/bold green] No broken links or TOC issues!\n")

    raise typer.Exit(code=0 if broken_count == 0 else 1)

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
    from pdflinkcheck.stdlib_server import ThreadedTCPServer, PDFLinkCheckHandler
    import socketserver

    try:
        with ThreadedTCPServer((host, port), PDFLinkCheckHandler) as httpd:
            console.print(f"[green]Server running — press Ctrl+C to stop[/green]\n")
            httpd.serve_forever()
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
    #from pdflinkcheck.gui import start_gui
    #from pdflinkcheck.gui_alt import start_gui
    from pdflinkcheck.gui_tight import start_gui
    start_gui(time_auto_close = assured_auto_close_value)

# --- Helper, consistent gui failure message. --- 
def _gui_failure_msg():
    console.print("[bold red]GUI failed to launch[/bold red]")
    console.print("Ensure pdflinkcheck dependecies are installed and the venv is activated (the dependecies are managed by uv).")
    console.print("The dependecies for pdflinkcheck are managed by uv.")
    console.print("Ensure Tkinter is available, especially if using WSLg.")
    console.print("On Termux/Android, GUI is not supported. Use 'pdflinkcheck analyze <file.pdf>' instead.")
    console.print(f"pyhabitat.tkinter_is_available() = {pyhabitat.tkinter_is_available()}")
    pass

if __name__ == "__main__":
    app()
    
