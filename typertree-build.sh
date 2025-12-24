cat << 'EOF' > ./external/typertree/pyproject.toml
[project]
name = "typertree"
version = "0.1.0"
description = "A Typer extension providing a Rich-based CLI help tree visualizer."
readme = "README.md"
requires-python = ">=3.10"
license = "MIT"
authors = [
    { name = "George Clayton Bennett" }
]

dependencies = [
    "typer>=0.20.0",
    "rich>=14.2.0",
    "click>=8.1.0"
]

[project.scripts]
typertree = "typertree.cli:app"

[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"
EOF

cat << 'EOF' > ./external/typertree/src/typertree/__init__.py
from .core import add_typer_help_tree, wiki

__all__ = [
    "add_typer_help_tree",
    "wiki",
]
EOF

cat << 'EOF' > ./external/typertree/src/typertree/core.py
#!/usr/bin/env python3
# SPDX-License-Identifier: MIT

import click
import typer
from rich.tree import Tree
from rich.panel import Panel
from rich.console import Console


def add_typer_help_tree(app: typer.Typer, console: Console):
    @app.command(name="help-tree", help="Show all commands and options in a tree structure.")
    def help_tree_command(ctx: typer.Context):
        root_app_command = ctx.parent.command

        app_tree = Tree(
            f"[bold blue]{root_app_command.name}[/bold blue]",
            guide_style="cyan"
        )

        for command_name in sorted(root_app_command.commands.keys()):
            command = root_app_command.commands[command_name]
            help_text = command.help.splitlines()[0].strip() if command.help else "No help available."

            command_branch = app_tree.add(
                f"[bold white]{command.name}[/bold white] - [dim]{help_text}[/dim]"
            )

            params_branch = command_branch.add("[yellow]Parameters[/yellow]:")

            if not command.params:
                params_branch.add("[dim]None[/dim]")

            for param in command.params:
                is_option = hasattr(param, "opts") and param.opts and param.opts[0].startswith("-")

                if is_option:
                    flag_names = " / ".join(param.opts)
                    if flag_names in ("-h", "--help"):
                        continue

                    default_value = getattr(param, "default", None)
                    if default_value not in (None, click.core.UNSET):
                        default = f"[dim] (default: {default_value})[/dim]"
                    else:
                        default = ""

                    params_branch.add(
                        f"[green]{flag_names}[/green]: [dim]{param.help}[/dim]{default}"
                    )
                else:
                    arg_name = param.human_readable_name.upper()
                    params_branch.add(
                        f"[magenta]ARG: {arg_name}[/magenta]: [dim]{param.help}[/dim]"
                    )

        console.print(
            Panel(app_tree, title="[bold]CLI Help Tree[/bold]", border_style="blue")
        )


def wiki():
    console = Console()
    console.print(Panel("""
[bold]TyperTree Developer Documentation[/bold]

TyperTree is a developer-facing CLI visualization tool for Typer apps.
It uses Rich to render a tree of commands, arguments, and options.

Features:
- help-tree command
- --tree global flag
- tree demo subcommand
- add_typer_help_tree() for integration
- wiki() for documentation

Example usage:

    from typertree import add_typer_help_tree
    add_typer_help_tree(app, console)

""", title="TyperTree Wiki", border_style="green"))
EOF

cat << 'EOF' > ./external/typertree/src/typertree/helpers.py
# SPDX-License-Identifier: MIT

def placeholder():
    return "TyperTree helper module ready."
EOF

cat << 'EOF' > ./external/typertree/src/typertree/cli.py
#!/usr/bin/env python3
# SPDX-License-Identifier: MIT

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
EOF

cat << 'EOF' > ./external/typertree/README.md
# TyperTree

TyperTree is a standalone CLI and importable library that adds a Rich-powered
help-tree visualizer to any Typer application.

## Features

- Standalone CLI:
    typertree help-tree
    typertree --tree
    typertree tree
    typertree wiki

- Importable library:
    from typertree import add_typer_help_tree

- Rich-based tree visualization of commands, arguments, and options.

## Install

    pip install ./external/typertree

## Use in another Typer app

    from typertree import add_typer_help_tree
    add_typer_help_tree(app, console)

EOF