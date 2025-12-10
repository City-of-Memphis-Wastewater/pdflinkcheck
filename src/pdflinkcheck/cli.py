# src/pdflinkcheck/cli.py
import typer
from rich.console import Console
from pathlib import Path
from .analyze import run_analysis # Assuming core logic moves here

# Initialize the rich console for output
console = Console()
app = typer.Typer(
    name="pdflinkcheck",
    help="A command-line tool for comprehensive PDF link analysis and reporting.",
    add_completion=False
)

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
        min=1,
        help="Maximum number of links/remnants to display in the report."
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

@app.command()
def check(
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
        min=1,
        help="Maximum number of links/remnants to display in the report."
    )
):
    """
    Analyzes the specified PDF file for all internal, external, and unlinked URI/Email references.
    """
    console.print(f"[bold blue]Analyzing PDF:[/bold blue] {pdf_path.name}")
    
    # Call the core logic function (which you will place in analyze.py)
    results = run_analysis(
        pdf_path=str(pdf_path), 
        check_remnants=check_remnants,
        max_links=max_links
    )

    # Display results (you will build out the rich-based reporting later)
    console.print("\n--- Analysis Summary ---")
    console.print(f"External Links: [green]{len(results.get('external_links', []))}[/green]")
    console.print(f"Internal Links: [green]{len(results.get('internal_links', []))}[/green]")
    console.print(f"Unlinked Remnants: [yellow]{len(results.get('remnants', []))}[/yellow]")
    
    # Placeholder for running the app
if __name__ == "__main__":
    app()
