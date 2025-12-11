# build_pyz.py (Final with explicit 'build' installation)
#!/usr/bin/env python3
import subprocess
import sys
import re
import os 
from pathlib import Path
import site

from .build_executable import form_dynamic_name

# Get the one site-packages path where packages are installed in the venv
SITE_PACKAGES_PATH = site.getsitepackages()[0]

# --- Configuration for pdflinkcheck ---
PROJECT_NAME = "pdflinkcheck"
ENTRY_POINT = "pdflinkcheck.cli:app" 
DIST_DIR = Path("dist")

# --- TOML Parsing Helper ---
def find_pyproject(start: Path) -> Path | None:
    for p in start.resolve().parents:
        candidate = p / "pyproject.toml"
        if candidate.exists():
            return candidate
    return None

def get_version_from_pyproject() -> str:
    pyproject = find_pyproject(Path(__file__))
    if not pyproject or not pyproject.exists():
        print("ERROR: pyproject.toml missing.", file=sys.stderr)
        return "0.0.0"

    text = pyproject.read_text(encoding="utf-8")
    
    # Match PEP 621 style: [project]
    project_section = re.search(r"\[project\](.*?)(?:\n\[|$)", text, re.DOTALL | re.IGNORECASE)
    if project_section:
        match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', project_section.group(1))
        if match: return match.group(1)

    # Match Poetry style: [tool.poetry]
    poetry_section = re.search(r"\[tool\.poetry\](.*?)(?:\n\[|$)", text, re.DOTALL | re.IGNORECASE)
    if poetry_section:
        match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', poetry_section.group(1))
        if match: return match.group(1)

    return "0.0.0"

# --- Helper Functions ---

def run_command(cmd, check=True, env=None):
    """Run command with printing and clear error reporting."""
    print(f"\n$ {' '.join(cmd)}")
    
    final_env = env if env is not None else os.environ

    result = subprocess.run(cmd, text=True, check=False, capture_output=True, env=final_env) 

    if result.stdout:
        print(result.stdout.strip())

    if result.returncode != 0:
        if result.stderr:
            print(f"--- COMMAND FAILED (Exit {result.returncode}) ---", file=sys.stderr)
            print(result.stderr.strip(), file=sys.stderr)
        
        if check:
            raise subprocess.CalledProcessError(
                result.returncode, cmd, output=result.stdout, stderr=result.stderr
            )
    return result

def find_latest_wheel(dist_dir: Path, version: str) -> Path:
    """Finds the most recently built wheel file for the given version."""
    wheels = sorted(
        dist_dir.glob(f"{PROJECT_NAME}-{version}*.whl"), 
        key=lambda f: f.stat().st_mtime,
        reverse=True
    )
    if not wheels:
        raise FileNotFoundError(f"No wheel found for version {version} in {dist_dir}.")
    return wheels[0]

def build_wheel():
    """Builds the source distribution and wheel using the standard Python build module."""
    print("\n1. Building project wheel using 'python -m build'...")
    # PASS THE CURRENT ENVIRONMENT (os.environ.copy())
    run_command([
        sys.executable, "-m", "build", 
        "--wheel", 
        "--outdir", str(DIST_DIR)
    ], env=os.environ.copy()) 
    print("Wheel build complete.")



def ensure_dependencies_and_shiv():
    """Ensures 'shiv', 'build', and all runtime dependencies are installed via uv."""
    print("\n2. Ensuring 'shiv', 'build', and runtime dependencies are installed via uv...")

    # 2a. Check/Install 'build' package (using the activated python, which works in your venv)
    try:
        run_command([sys.executable, "-m", "build", "--version"], check=True)
    except subprocess.CalledProcessError:
        print("Installing 'build' using uv...")
        run_command(["uv", "pip", "install", "build"])

    # 2b. INSTALL/SYNC ALL PROJECT DEPENDENCIES (The Fix)
    print("Installing all project dependencies via uv pip install -e .")
    run_command(["uv", "pip", "install", "-e", "."]) # <-- FIX: Use -e . to get all dependencies
    
    # 2c. Ensure shiv is installed
    try:
        run_command(["shiv", "--version"], check=True) 
    except subprocess.CalledProcessError:
        print("Installing 'shiv' using uv...")
        run_command(["uv", "pip", "install", "shiv"])
    
    print("Dependencies and shiv ready.")

def build_shiv_pyz():
    """Build the portable PYZ using shiv."""
    
    version = get_version_from_pyproject()
    if version == "0.0.0":
        print("FATAL: Cannot proceed without a valid version found in pyproject.toml.", file=sys.stderr)
        sys.exit(1)
        
    DIST_DIR.mkdir(exist_ok=True)
    
    # 1. Ensure dependencies, shiv, and build are ready
    ensure_dependencies_and_shiv()
    
    # 2. Build the wheel 
    build_wheel()

    # 3. Find the resulting wheel file
    wheel_path = find_latest_wheel(DIST_DIR, version)
    dynamic_name = form_dynamic_name(PROJECT_NAME, version)
    output_filename = f"{dynamic_name}-shiv.pyz" 
    output_path = DIST_DIR / output_filename
    if output_path.exists():
        output_path.unlink()
        
    print(f"\n3. Building PYZ using shiv from Wheel: {output_filename}")

    # SHIV COMMAND
    cmd = [
        "shiv",
        str(wheel_path), 
        "-o", str(output_path),
        "-p", "/usr/bin/env python3", 
        "-e", ENTRY_POINT,
        "--compressed",
        "--no-cache", 
        "--python", sys.executable,
        "--site-packages", SITE_PACKAGES_PATH,
    ]
    
    # Pass the current, activated environment
    run_command(cmd, env=os.environ.copy())
    
    output_path.chmod(0o755)
    
    print(f"\n✅ Build successful! Portable PYZ: {output_path.resolve()}")

if __name__ == "__main__":
    try:
        # NOTE: This script is intended to be run via: uv run python build_pyz.py
        build_shiv_pyz()
    except subprocess.CalledProcessError as e:
        print(f"\nFATAL ERROR: A subprocess failed with exit code {e.returncode}.", file=sys.stderr)
        print("Review the stderr output above for details (often a dependency issue).", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nFATAL ERROR during PYZ build: {e}", file=sys.stderr)
        sys.exit(1)
