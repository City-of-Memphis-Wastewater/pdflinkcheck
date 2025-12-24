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

## Steering

### ✔ Adds a **main Typer app**  
### ✔ Provides a **minimal demo CLI** that uses your `add_typer_help_tree()` function  
### ✔ Adds a **flag version** (`--tree`) that triggers the help‑tree output  
### ✔ Adds a **subcommand** `tree` that also accepts `--tree`  
### ✔ Adds a **wiki()** function that prints documentation for developers  

Born: Christmas Eve 2025
