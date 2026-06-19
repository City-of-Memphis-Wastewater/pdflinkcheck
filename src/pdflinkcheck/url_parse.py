# src/pdflinkcheck/utl_parse.py

from urllib.parse import ParseResult, urlparse

def parse_url_helper(url: str) -> tuple[ParseResult, str, str]:
    """
    Normalizes and parses a URL, handling missing schemas safely.
    Returns: (parsed_object, host_string, query_string)
    """
    if "://" not in url and not url.startswith(("//", "mailto:", "tel:")):
        parsed = urlparse(f"http://{url}")
    else:
        parsed = urlparse(url)

    return parsed, (parsed.hostname or ""), (parsed.query or "")
