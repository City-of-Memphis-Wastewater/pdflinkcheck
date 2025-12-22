# pdflinkcheck/environment.py

from functools import cache
import subprocess
"""
Environment checks.

Functions:
- is_in_git_repo()
- pymupdf_is_available()

Examples:
- is_in_git_repo() is used when deciding to force load src/pdflinkcheck/data/ files, when CLI docs is called, and if they are not found when called in the GUI,
- Default to pypdf at load if not pymupdf_is_available(). pymupdf_is_available() is useful for caching a common check in this codebase and setting up explicit logic rather than relying on try/except blocks in each instance. 
"""

def clear_all_caches()->None:
    """Clear every @cache used in pdflinkcheck. Future work: Call from CLI using --clear-cache"""
    
@cache
def pymupdf_is_available() -> bool:
    """Check if pymupdf is available in the current local version of pdflinkcheck."""
    try:
        import fitz
        return True
    except Exception:
        # Fails if: the [full] group from [project.optional-dependencies] in pyrpoject.toml was not used when installing pdflink check. Like 
        # Use: `pipx install pdflinkcheck[full]` or alternative.
        return False


@cache
def is_in_git_repo(path='.'):
    """
    Check if the given path is inside a Git repository.
    
    Uses 'git rev-parse --is-inside-work-tree' command.

    """
    try:
        # Run the git command, suppressing output
        result = subprocess.run(
            ['git', 'rev-parse', '--is-inside-work-tree'],
            cwd=path,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return result.stdout.strip().decode('utf-8') == 'true'
    except subprocess.CalledProcessError:
        # The command fails if it's not a git repository
        return False
    except FileNotFoundError:
        # Handle the case where the 'git' executable is not found
        print("Error: 'git' command not found. Please ensure Git is installed and in your PATH.")
        return False

