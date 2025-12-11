# src/bug_record/cli_typer_no_args_no_gui_silent (defunct, kept as a bug record, associated with FastAPI/Typer issue # x)
import typer
from rich.console import Console
from pathlib import Path
from pdflinkcheck.analyze import run_analysis # Assuming core logic moves here
from typing import Dict
import logging
import pyhabitat
import sys
import os

console = Console() # to be above the tkinter check, in case of console.print

if pyhabitat.tkinter_is_available():
    from pdflinkcheck.gui import start_gui
else:
    start_gui = None
    console.print("Tkinter is not available on this system.")


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
    If no subcommand is provided, launch the GUI <- Is the idea. However.
    This is not functioning today.
    Work around: non-typer-app _launch_default_gui() called in __main__ block if len(sys.argv) <= 1.
    """

    if ctx.invoked_subcommand is None:

        # No subcommand → launch GUI
        if not start_gui:
            _gui_failure_msg()
            raise typer.Exit(code=1)
        
        start_gui()

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
    check_remnants: bool = typer.Option(
        True,
        "--check-remnants/--no-check-remnants",
        help="Toggle checking for unlinked URLs/Emails in the text layer."
    ),
    max_links: int = typer.Option(
        50,
        "--max-links",
        min=0,
        help="Maximum number of links/remnants to display in the report. Use 0 to show all."
    )
):
    """
    Analyzes the specified PDF file for all internal, external, and unlinked URI/Email references.
    """
    # The actual heavy lifting (analysis and printing) is now in run_analysis
    run_analysis(
        pdf_path=str(pdf_path), 
        check_remnants=check_remnants,
        max_links=max_links
    )

@app.command(name="gui") 
def gui_command()->None:
    """
    Launch tkinter-based GUI.
    """
    if not start_gui:
        _gui_failure_msg()
        return
    start_gui()

        
def _launch_default_gui():
    """
    Logic to launch GUI and handle failure, used in __main__.
    This should not be necessary, but when no args are provided the gui does not launch without it.
    """
    # 1. Ensure that gui is available
    if not start_gui:
        _gui_failure_msg()
        sys.exit(1)
    
    # 2. Call the core function which blocks
    start_gui()
    
    # 3. Exit cleanly after the GUI window is closed
    sys.exit(0)
        

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