# src/bug_record/cli.py
import typer
from rich.console import Console
from pathlib import Path
from pdflinkcheck.analyze import run_analysis # Assuming core logic moves here
from typing import Dict
import pyhabitat
import sys

console = Console() # to be above the tkinter check, in case of console.print

app = typer.Typer(
    name="pdflinkcheck",
    help="A command-line tool for comprehensive PDF link analysis and reporting.",
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
    export_format: str = typer.Option("JSON", "--export-format","-e", help="Set the export format for the report. Currently supported: json. When None, the report wll be printed but not exported. "
    ),
    max_links: int = typer.Option(
        0,
        "--max-links",
        min=0,
        help="Maximum number of links/remnants to display in the report, if an overwhelming amount is expected. Use 0 to show all."
    ),
    check_remnants: bool = typer.Option(
        True,
        "--check-remnants/--no-check-remnants",
        help="Toggle checking for unlinked URLs/Emails in the text layer."
    )
):
    """
    Analyzes the specified PDF file for all internal, external, and unlinked URI/Email references.
    """
    # The actual heavy lifting (analysis and printing) is now in run_analysis
    run_analysis(
        pdf_path=str(pdf_path), 
        check_remnants=check_remnants,
        max_links=max_links,
        export_format = export_format
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

    if not pyhabitat.tkinter_is_available():
        _gui_failure_msg()
        return
    from pdflinkcheck.gui import start_gui
    start_gui(time_auto_close = auto_close)


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