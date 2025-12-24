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
