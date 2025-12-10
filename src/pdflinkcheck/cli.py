# src/pdflinkcheck/cli.py
import typer
from rich.console import Console
from pathlib import Path
from pdflinkcheck.analyze import run_analysis # Assuming core logic moves here
from typing import Dict
# Initialize the rich console for output
console = Console()
app = typer.Typer(
    name="pdflinkcheck",
    help="A command-line tool for comprehensive PDF link analysis and reporting.",
    add_completion=False,
    invoke_without_command = True,
    no_args_is_help=False,
)

app.callback()
def main(ctx: typer.Context):
    """
    If no subcommand is provided, launch the GUI.
    """
    if ctx.invoked_subcommand is None:
        # No subcommand → launch GUI
        try:
            from pdflinkcheck.gui import start_gui
            start_gui()
        except ImportError as e:
            console.print("[red]GUI dependencies not available.[/red]")
            console.print("Install with: pip install pdflinkcheck[gui]")
            console.print(f"Details: {e}")
            raise typer.Exit(code=1)
        except Exception as e:
            console.print("[bold red]GUI failed to launch[/bold red]")
            console.print("Make sure tkinter is available (especially on WSL).")
            console.print(f"Error: {e}")
            raise typer.Exit(code=1)

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
def gui():
    """
    Launch tkinter-based GUI.
    """
    from pdflinkcheck.gui import start_gui
    try:
        start_gui()
    except Exception as e:
        typer.echo("GUI failed to launch")
        typer.echo("Ensure tkinter is available, especially if using WSLg.")
        typer.echo(f"Error: {e}")

    # Placeholder for running the app
if __name__ == "__main__":
    app()
