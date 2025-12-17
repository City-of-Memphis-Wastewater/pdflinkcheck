# src/pdflinkcheck/cli.py
import typer
from typer.models import OptionInfo
from rich.console import Console
from pathlib import Path
from pdflinkcheck.report import run_report # Assuming core logic moves here
from typing import Dict, Optional
import pyhabitat
import sys
import os
from importlib.resources import files

from pdflinkcheck.version_info import get_version_from_pyproject


console = Console() # to be above the tkinter check, in case of console.print

app = typer.Typer(
    name="pdflinkcheck",
    help=f"A command-line tool for comprehensive PDF link analysis and reporting. (v{get_version_from_pyproject()})",
    add_completion=False,
    invoke_without_command = True, 
    no_args_is_help = False,
)


@app.callback()
def main(ctx: typer.Context):
    """
    If no subcommand is provided, launch the GUI.
    """
    
    if ctx.invoked_subcommand is None:
        gui_command()
        raise typer.Exit(code=0)
    
    # 1. Access the list of all command-line arguments
    full_command_list = sys.argv
    # 2. Join the list into a single string to recreate the command
    command_string = " ".join(full_command_list)
    # 3. Print the command
    typer.echo(f"command:\n{command_string}\n")


# help-tree() command: fragile, experimental, defaults to not being included.
if os.environ.get('DEV_TYPER_HELP_TREE',0) in ('true','1'):
    from pdflinkcheck.dev import add_typer_help_tree
    add_typer_help_tree(
        app = app,
        console = console)

@app.command(name="docs", help="Show the docs for this software.")
def docs_command(
    license: Optional[bool] = typer.Option(
        None, "--license", "-l", help="Show the full AGPLv3 license text."
    ),
    readme: Optional[bool] = typer.Option(
        None, "--readme", "-r", help="Show the full README.md content."
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

@app.command(name="analyze") # Added a command name 'analyze' for clarity
def analyze_pdf( # Renamed function for clarity
    pdf_path: Path = typer.Argument(
        ..., 
        exists=True, 
        file_okay=True, 
        dir_okay=False, 
        readable=True,
        resolve_path=True,
        help="The path to the PDF file to analyze."
    ),
    export_format: str = typer.Option("JSON", "--export-format","-e", help="Set the export format for the report. Currently supported: JSON. To suppress file export, use the empty string: --export-format \"\""
    ),
    max_links: int = typer.Option(
        0,
        "--max-links", "-m",
        min=0,
        help="Maximum number of links/remnants to display in the report, if an overwhelming amount is expected. Use 0 to show all."
    ),
    pdf_library: str = typer.Option(
        "pypdf",#"pymupdf",
        "--pdf-library","-p",
        help="select the PDF parsing library to use, pymupdf or pypdf."
    )
):
    """
    Analyzes the specified PDF file for all internal, external, and unlinked references.
    """

    VALID_FORMATS = ("JSON") # extend later

    final_export_format = export_format.upper().strip()
    export_format_for_analysis = None

    # The actual heavy lifting (analysis and printing) is now in run_report
    if not final_export_format:
        export_format_for_analysis = None
    elif final_export_format == "" or final_export_format == "NONE" or final_export_format == "0":
        export_format_for_analysis = None
    elif final_export_format not in VALID_FORMATS:
        typer.echo(f"An unexpected --export-format was provided: {final_export_format}")
        typer.echo(f"No export will be made.")
        export_format_for_analysis = None
    else:
        # User passed "JSON" or other valid format
        export_format_for_analysis = final_export_format

    run_report(
        pdf_path=str(pdf_path), 
        max_links=max_links,
        export_format = export_format_for_analysis,
        pdf_library = pdf_library,
    )

@app.command(name="gui") 
def gui_command(
    auto_close: int = typer.Option(0, 
                                   "--auto-close", "-c", 
                                   help = "Delay in milliseconds after which the GUI window will close (for automated testing). Use 0 (default) to disable auto-closing.",
                                   min=0)
    )->None:
    """
    Launch tkinter-based GUI.
    """

    # --- START FIX ---
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
    # --- END FIX ---

    if not pyhabitat.tkinter_is_available():
        _gui_failure_msg()
        return
    from pdflinkcheck.gui import start_gui
    start_gui(time_auto_close = assured_auto_close_value)

# --- Helper, consistent gui failure message. --- 
def _gui_failure_msg():
    console.print("[bold red]GUI failed to launch[/bold red]")
    console.print("Ensure pdflinkcheck dependecies are installed and the venv is activated (the dependecies are managed by uv).")
    console.print("The dependecies for pdflinkcheck are managed by uv.")
    console.print("Ensure tkinter is available, especially if using WSLg.")
    console.print(f"pyhabitat.tkinter_is_available() = {pyhabitat.tkinter_is_available()}")
    pass

if __name__ == "__main__":
    app()
    