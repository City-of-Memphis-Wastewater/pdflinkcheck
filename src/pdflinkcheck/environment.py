# pdflinkcheck/environment.py

from functools import cache

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
