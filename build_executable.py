#!/usr/bin/env python3 
# SPDX-License-Identifier: MIT
# ./build_executable.py
"""
build_executable.py for pdflinkcheck
Builds the pdflinkcheck standalone binary (EXE/ELF) using PyInstaller.
"""
from __future__ import annotations
import shutil
import subprocess
import sys
import os
from pathlib import Path
import argparse
import pyhabitat

from pdflinkcheck.datacopy import ensure_data_files_for_build
from pdflinkcheck._version import get_version
from pdflinkcheck.environment import pymupdf_is_available, pdfium_is_available

# --- Configuration ---
PROJECT_NAME = "pdflinkcheck"
#CLI_MAIN_FILE = Path(f'src/{PROJECT_NAME}/cli.py')
#CLI_MAIN_FILE = Path.cwd() / 'src' / PROJECT_NAME / "cli.py"
CLI_MAIN_FILE = Path.cwd() / 'src' / PROJECT_NAME / "__main__.py"
DIST_DIR = Path("dist")
DIST_DIR_ONEFILE = DIST_DIR / "onefile" 
DIST_DIR_ONEDIR = DIST_DIR / "onedir" 
BUILD_DIR = Path("build/pyinstaller_work")
RC_TEMPLATE = Path('build_assets') / 'version.rc.template' # Assume this template exists for Windows
RC_FILE = Path('build_assets') / 'version.rc'
IS_WINDOWS_BUILD = pyhabitat.on_windows()
PROJECT_ROOT = Path(__file__).resolve().parent
HOOKS_DIR_ABS = PROJECT_ROOT / "pyinstaller_hooks"

# --- Dynamic Naming Placeholder (Simplified version for this context) ---
def form_dynamic_name(pkg_name: str, version: str) -> str:
    """Creates a standardized binary name descriptor."""

    os_tag = pyhabitat.SystemInfo().get_os_tag()
    arch = pyhabitat.SystemInfo().get_arch()
    py_ver = f"py{sys.version_info.major}{sys.version_info.minor}"
    return f"{pkg_name}-{version}-{py_ver}-{os_tag}-{arch}"

# --- Windows Resource File (version.rc) ---
def generate_rc_file(package_version: str):
    """Generates the .rc file using the provided version string, only on Windows."""
    if not IS_WINDOWS_BUILD: return

    if not RC_TEMPLATE.exists():
        print(f"WARNING: RC template not found at {RC_TEMPLATE}. Skipping version info embedding.", file=sys.stderr)
        return

    # Implementation logic for reading template and writing RC_FILE...
    # (Same as in the previous pipeline script, but simplified here)
    print(f"Placeholder: Generated resource file {RC_FILE} for version {package_version}")
    RC_FILE.write_text("// Placeholder content for versioning", encoding="utf-8")


# --- Setup & Cleanup ---

def setup_dirs():
    """Ensure directories exist."""
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    DIST_DIR_ONEFILE.mkdir(parents=True, exist_ok=True)
    DIST_DIR_ONEDIR.mkdir(parents=True, exist_ok=True)


def clean_artifacts(exe_name: str, mode: str):
    """Clean specific output and build folders based on mode."""
    
    
    # Define what we are cleaning based on mode
    if mode == "onedir":
        # In onedir, PyInstaller creates a directory with the exe_name
        mode_dir = DIST_DIR_ONEDIR
        target = mode_dir / exe_name
    else:
        # In onefile, it's just the .exe (or ELF) file
        mode_dir = DIST_DIR_ONEFILE
        ext = '.exe' if IS_WINDOWS_BUILD else ''
        target = mode_dir / f"{exe_name}{ext}"

    if target.exists():
        print(f"Removing old build artifact: {target.resolve()}")
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
    
    # Clean the work directory
    if BUILD_DIR.exists():
        print(f"Removing build/pyinstaller_work folder: {BUILD_DIR.resolve()}")
        shutil.rmtree(BUILD_DIR)

    if IS_WINDOWS_BUILD and RC_FILE.exists():
        RC_FILE.unlink()

# --- Main PyInstaller Execution ---

def run_pyinstaller(
        dynamic_exe_name: str, 
        main_script_path: Path,
        mode: str = "onedir",
        ):
    """
    Run PyInstaller to build the executable.
    """
    
    print(f"--- {PROJECT_NAME} Executable Builder ---")

    
    ext = '.exe' if IS_WINDOWS_BUILD else ''
    if mode == "onefile":
        mode_dist_path = DIST_DIR_ONEFILE 
        final_path = DIST_DIR_ONEFILE/ f"{dynamic_exe_name}{ext}"
    elif mode  == "onedir":
        mode_dist_path = DIST_DIR_ONEDIR
        final_path = DIST_DIR_ONEDIR / dynamic_exe_name / f"{dynamic_exe_name}{ext}"

    mode_dist_path.mkdir(parents=True, exist_ok=True)

    print(f"Executable is located at: {final_path.resolve()}") 

    # Clean and Setup
    clean_artifacts(exe_name=dynamic_exe_name, mode=mode)
    setup_dirs()

    
    # PyInstaller Command Construction
    base_command = [
        #'pyinstaller',
        sys.executable, "-m", "PyInstaller",
        '--noconfirm',
        '--clean',
        f'--name={dynamic_exe_name}',

        # --- Crucial for resolving package structure and relative imports ---
        f'--paths={PROJECT_ROOT / "src"}',
        
        # Output paths
        f'--distpath={mode_dist_path}', # <--
        f'--workpath={BUILD_DIR / "work"}',
        f'--specpath={BUILD_DIR}',

        # --- Add the Hooks Directory ---
        f'--additional-hooks-dir={HOOKS_DIR_ABS}', # 

        # Crucial for Typer/Click based apps
        "--hidden-import", "pkg_resources.py2_warn", 
        "--hidden-import", "typer.models",
        "--hidden-import", "typer.main", 
        "--hidden-import", "typer",  
        "--hidden-import", "click",  
        "--hidden-import", "rich",

        #'--log-level=DEBUG',

        #"--add-data", "pyproject.toml:pdflinkcheck/data",
    ]


    # msix.yml and build.yml have been adjusted to expect either onefile or onedir
    if mode == "onefile": 
        onedir_or_onefile_flag = '--onefile'
        base_command.append(onedir_or_onefile_flag)
    else: # default
        onedir_or_onefile_flag = '--onedir'
        base_command.append(onedir_or_onefile_flag)
    
    # Prepare for MSIX
    if IS_WINDOWS_BUILD and (mode == "onedir") and pyhabitat.tkinter_is_available(): 
        # only use windows mode for scenario that targets MSIX
        flag = '--windowed'
        # flag = '--noconsole'
        print(f"Building with the {flag} flag, to favor GUI usage for the artifact, because GUI is avaialble.")
        base_command.append(flag)
        
    else:
        print("Building without the --noconsole or --windowed flag, to favor CLI usage for the artifact, because GUI is not available.")

    # Add Windows resource file if applicable
    if IS_WINDOWS_BUILD and RC_FILE.exists():
        #base_command.append(f'--version-file={RC_FILE.name}')
        base_command.append(f'--version-file={RC_FILE.resolve()}')

    # PyMuPDF is a native library, ensure its dependencies are included if necessary
    # PyInstaller often handles this automatically, but if it fails, 'collect-all' is needed.
    if pymupdf_is_available():
        base_command.append("--collect-all")
        base_command.append("fitz")
        base_command.append("--collect-all")
        base_command.append("pymupdf") # careful. if this line runs, your binary is subject to the AGPL3+
    
    if pdfium_is_available():
        base_command.append("--collect-all")
        base_command.append("pypdfium2")
        
    if pyhabitat.on_macos():
        base_command.append("--osx-bundle-identifier")
        base_command.append("com.georgeclaytonbennett.pdflinkcheck")
        #base_command.append("--icon=icon.icns")
        
     # Add the main script LAST
    base_command.append(str(main_script_path.resolve()))

    # Determine execution path (Run PyInstaller directly, assuming it's in PATH/venv)
    full_command = base_command
    print(f"Executing PyInstaller: {' '.join(full_command)}")

    # 6. Execute
    try:
        # Pass environment variables to ensure venv dependencies are found
        subprocess.run(full_command, check=True, env=os.environ.copy()) 
    except subprocess.CalledProcessError as e:
        print(f"PyInstaller failed with exit code {e.returncode}!", file=sys.stderr)
        raise SystemExit(e.returncode)

    print("\n--- PyInstaller Build Complete ---")

    return final_path.resolve()


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices = ("onedir","onefile"),
        default = "onedir",
        help = "PyInstaller build mode.",
        )
    args = parser.parse_args()
    try:
        package_version = get_version()
        if package_version == "0.0.0":
            print("FATAL: Cannot find package version in pyproject.toml.", file=sys.stderr)
            sys.exit(1)
        
        # 0. Ensure data files are available to build package
        ensure_data_files_for_build()

        # 1. Ensure PyInstaller is installed (if you haven't done it manually)
        # uv run python -m pip install pyinstaller 
        
        # 2. Generate RC file (conditionally)
        generate_rc_file(package_version)

        # 3. Determine the executable name (without the extension)
        executable_descriptor = form_dynamic_name(PROJECT_NAME, package_version)
        if args.mode == "onefile":
            executable_descriptor += "-onefile"

        # 4. Run the installer
        path = run_pyinstaller(
            executable_descriptor, 
            CLI_MAIN_FILE, 
            mode = args.mode,
            )

        # Only test GUI if we aren't in a headless CI environment
        # GitHub Actions sets the GITHUB_ACTIONS environment variable to 'true'
        is_ci = os.environ.get('GITHUB_ACTIONS') == 'true'

        # Only run text-based --help check if we aren't a hidden-window GUI binary
        is_windowed_build = IS_WINDOWS_BUILD and (args.mode == "onedir") and pyhabitat.tkinter_is_available()

        #if is_ci:
        #    print("[CI DETECTED] Skipping CLI help text check to prevent headless stream hangs.")
        if is_windowed_build:
            print("Skipping CLI help text check because artifact was built with --windowed.")
        else:
            print("Testing the PyInstaller artifact...")
            subprocess.run([str(path), "--help"], check=True)

        print(f"pyhabitat.tkinter_is_available() = {pyhabitat.tkinter_is_available()}")
        if pyhabitat.tkinter_is_available() and not is_ci:
            print(f"Testing GUI for {str(path)}...")
            subprocess.run([str(path), "gui", "--auto-close", "1000"])
        print("Testing complete.")
        
    except SystemExit as e:
        sys.exit(e.code)
    except Exception as e:
        print(f"An unhandled error occurred: {e}", file=sys.stderr)
        sys.exit(1)
    
