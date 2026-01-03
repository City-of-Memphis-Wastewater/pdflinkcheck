#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
from __future__ import annotations
import typer
from rich.console import Console

from typertree.core import add_typer_help_tree, wiki

console = Console()
app = typer.Typer(
    name="typertree",
    help="TyperTree: A Rich-powered CLI help tree visualizer for Typer apps.",
    add_completion=False,
)

add_typer_help_tree(app, console)


@app.callback()
def main(
    ctx: typer.Context,
    tree: bool = typer.Option(
        False,
        "--tree",
        help="Show the CLI help tree and exit."
    )
):
    if tree:
        ctx.invoke(app.commands["help-tree"])
        raise typer.Exit()


@app.command(name="tree", help="Demonstration subcommand that also supports --tree.")
def tree_command(
    ctx: typer.Context,
    tree: bool = typer.Option(False, "--tree", help="Show the CLI help tree for this subcommand.")
):
    if tree:
        ctx.invoke(app.commands["help-tree"])
        raise typer.Exit()

    console.print("[bold green]This is the TyperTree demo 'tree' subcommand.[/bold green]")


@app.command(name="wiki", help="Show developer documentation for TyperTree.")
def wiki_command():
    wiki()
