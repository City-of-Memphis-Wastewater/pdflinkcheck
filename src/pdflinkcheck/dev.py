# pdflinkcheck/dev.py
"""
Experiemental developer-facing function(s).

help_tree_command() used click and typer internals which might change version to version.

This portion of the codebase is MIT licensed. It does not rely on any AGPL-licensed code.

---

MIT License

Copyright (c) 2025 George Clayton Bennett <george.bennett@memphistn.gov>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

"""

import typer
from rich.tree import Tree 
from rich.panel import Panel
import click

from pdflinkcheck.version_info import get_version_from_pyproject

def add_help_tree(app,
                  console):
    @app.command(name="help-tree", help="Show all commands and options in a tree structure.")
    def help_tree_command(ctx: typer.Context):
        """
        Fragile developer-facing function
        Generates and prints a tree view of the CLI structure (commands and flags).
        """
        root_app_command = ctx.parent.command 
        
        # 1. Start the Rich Tree structure
        app_tree = Tree(
            f"[bold blue]{root_app_command.name}[/bold blue] (v{get_version_from_pyproject()})",
            guide_style="cyan"
        )

        # 2. Iterate through all subcommands of the main app
        for command_name in sorted(root_app_command.commands.keys()):
            command = root_app_command.commands[command_name]
            
            if command.name == "tree-help":
                continue

            help_text = command.help.splitlines()[0].strip() if command.help else "No help available."

            command_branch = app_tree.add(f"[bold white]{command.name}[/bold white] - [dim]{help_text}[/dim]")

            # 3. Add Arguments and Options (Flags)
            params_branch = command_branch.add("[yellow]Parameters[/yellow]:")
            
            if not command.params:
                params_branch.add("[dim]None[/dim]")
            
            for param in command.params:
                # New, safer check: Check if param is an Option by looking for opts attribute 
                # and ensuring it has a flag declaration (starts with '-')
                is_option = hasattr(param, 'opts') and param.opts and param.opts[0].startswith('-')
                
                if is_option:
                    # This is an Option/Flag
                    flag_names = " / ".join(param.opts)
                    
                    # Filter out the default Typer/Click flags like --help
                    if flag_names in ("-h", "--help"):
                        continue
                    
                    # Handling default value safely
                    # Check for None explicitly, as well as the Typer/Click internal sentinel value for not provided.
                    default_value = getattr(param, 'default', None)

                    # This is the sentinel value used by the Click/Typer internals
                    if default_value not in (None, click.core.UNSET):
                        default = f"[dim] (default: {default_value})[/dim]"
                    else:
                        default = ""
                    
                    params_branch.add(f"[green]{flag_names}[/green]: [dim]{param.help}[/dim]{default}")
                else:
                    # This is an Argument (Positional)
                    # Arguments have a single name property, not an opts list.
                    arg_name = param.human_readable_name.upper()
                    params_branch.add(f"[magenta]ARG: {arg_name}[/magenta]: [dim]{param.help}[/dim]")

        # 4. Print the final Panel containing the tree
        console.print(Panel(app_tree, title=f"[bold]{root_app_command.name} CLI Tree Help[/bold]", border_style="blue"))
