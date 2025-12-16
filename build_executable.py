#!/usr/bin/env python3
"""
build_executable.py for pdflinkcheck
Builds the pdflinkcheck standalone binary (EXE/ELF) using PyInstaller.
"""
import shutil
import subprocess
import sys
import os
from pathlib import Path
import re
import pyhabitat

# --- Configuration ---
PROJECT_NAME = "pdflinkcheck"
CLI_MAIN_FILE = Path(f'src/{PROJECT_NAME}/cli.py')
DIST_DIR = Path("dist")
BUILD_DIR = Path("build/pyinstaller_work")
RC_TEMPLATE = Path('version.rc.template') # Assume this template exists for Windows
RC_FILE = Path('version.rc')
IS_WINDOWS_BUILD = pyhabitat.on_windows()
PROJECT_ROOT = Path(__file__).resolve().parent
HOOKS_DIR_ABS = PROJECT_ROOT / "pyinstaller_hooks"

# --- Version Info Helper (From successful build_pyz.py) ---
def find_pyproject(start: Path) -> Path | None:
    """Find the pyproject.toml file by walking up the directory tree."""
    for p in start.resolve().parents:
        candidate = p / "pyproject.toml"
        if candidate.exists():
            return candidate
    return None

def get_version_for_build() -> str:
    """Reads the version from pyproject.toml."""
    pyproject = find_pyproject(Path(__file__))
    if not pyproject: return "0.0.0"
    text = pyproject.read_text(encoding="utf-8")
    
    match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', text, re.DOTALL | re.IGNORECASE)
    return match.group(1) if match else "0.0.0"

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

def clean_artifacts(exe_name: str):
    """Clean specific output and build folders."""
    output_file = DIST_DIR / (exe_name + ('.exe' if IS_WINDOWS_BUILD else ''))

    if output_file.exists():
        print(f"Removing old executable: {output_file.resolve()}")
        output_file.unlink()
    
    if BUILD_DIR.parent.exists():
        print(f"Removing build folder: {BUILD_DIR.parent.resolve()}")
        shutil.rmtree(BUILD_DIR.parent)
    
    if IS_WINDOWS_BUILD and RC_FILE.exists():
        RC_FILE.unlink()

# --- Main PyInstaller Execution ---

def run_pyinstaller(dynamic_exe_name: str, main_script_path: Path):
    """Run PyInstaller to build the executable."""
    
    print(f"--- {PROJECT_NAME} Executable Builder ---")

    # 1. Clean and Setup
    clean_artifacts(exe_name=dynamic_exe_name)
    setup_dirs()

    
    # 2. PyInstaller Command Construction
    base_command = [
        'pyinstaller',
        '--noconfirm',
        '--clean',
        '--onefile',
        '--noconsole', # Worth it for GUI launch experience. Typer CLI might not work or show help. Encourage users who want the CLI to use the PYZ.
        f'--name={dynamic_exe_name}',
        
        # Output paths
        f'--distpath={DIST_DIR}',
        f'--workpath={BUILD_DIR / "work"}',
        f'--specpath={BUILD_DIR}',

        # --- Add the Hooks Directory ---
        f'--additional-hooks-dir={HOOKS_DIR_ABS}', # 

        # Crucial for Typer/Click based apps
        "--hidden-import", "pkg_resources.py2_warn", 
        "--hidden-import", "typer.models", 
        
        # PyMuPDF is a native library, ensure its dependencies are included if necessary
        # PyInstaller often handles this automatically, but if it fails, 'collect-all' is needed.
        
    ]

    # 3. Add Windows resource file if applicable
    if IS_WINDOWS_BUILD and RC_FILE.exists():
        base_command.append(f'--version-file={RC_FILE.name}')

    # 4. Add the main script
    base_command.append(str(main_script_path.resolve()))
    
    # 5. Determine execution path (Run PyInstaller directly, assuming it's in PATH/venv)
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
    ext = '.exe' if IS_WINDOWS_BUILD else ''
    final_path = DIST_DIR / f"{dynamic_exe_name}{ext}"
    print(f"Executable is located at: {final_path.resolve()}")
    return final_path.resolve()


if __name__ == "__main__":
    try:
        package_version = get_version_for_build()
        if package_version == "0.0.0":
            print("FATAL: Cannot find package version in pyproject.toml.", file=sys.stderr)
            sys.exit(1)
            
        # 1. Ensure PyInstaller is installed (if you haven't done it manually)
        # uv run python -m pip install pyinstaller 
        
        # 2. Generate RC file (conditionally)
        generate_rc_file(package_version)

        # 3. Determine the executable name (without the extension)
        executable_descriptor = form_dynamic_name(PROJECT_NAME, package_version)

        # 4. Run the installer
        path = run_pyinstaller(executable_descriptor, CLI_MAIN_FILE)
        
    except SystemExit:
        pass
    except Exception as e:
        print(f"An unhandled error occurred: {e}", file=sys.stderr)
        sys.exit(1)

    # 5. Test for success
    try:
        print("Testing the PyInstaller artifact...")
        subprocess.run([str(path), "--help"])
        if pyhabitat.tkinter_is_available():
            print(f"Testing GUI for {str(path)}...")
            subprocess.run([str(path), "gui", "--auto-close", "1000"])
        print("Testing complete.")
    except Exception as e:
        print(f"\n ERROR during PyInstaller post-build test: {e}", file=sys.stderr)
        sys.exit(1)