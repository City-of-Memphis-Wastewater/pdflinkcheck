#!/usr/bin/env python3 
# SPDX-License-Identifier: MIT
# src/pdflinkcheck/ping.py
from dataclasses import dataclass
import urllib.request
import urllib.error
from urllib.parse import urlparse
import logging
logger = logging.getLogger(__name__)


# ---  Local Imports ---
#None

# --- Data Classes, Enum, Flag, and stability
# dataclass example(s): ObtainResult

@dataclass()
#@dataclass
class PingUrlResult:
    status_code: int
    reason: str

    @property
    def success(self) -> bool | None:

        if self.status_code == 0:
            return None

        if 200 <= self.status_code < 400:
            return True

        return False
        
    @property
    def success_text(self) -> str:
        return {
            200: "OK",
            404: "Not Found",
            666: "Not Yet Implemented",
        }.get(self.status_code, "Error.")
    
# ---

def ping_url(url: str | None) -> PingUrlResult:
    """Pings a URL using a HEAD request to check if it's valid/accessible."""
    if not url:
        return PingUrlResult(0, "Empty or None URL")

    logger.debug(f"ping: {url=}")

    # Use a standard User-Agent because some servers block the default Python one
    req = urllib.request.Request(
        url, 
        method="HEAD", 
        headers={"User-Agent": "Mozilla/5.0 (pdflinkcheck)"}
    )

    try:
        # 5-second timeout so a dead link doesn't hang your script forever
        with urllib.request.urlopen(req, timeout=5) as response:
            return PingUrlResult(status_code = response.status, reason = response.reason)
            
    except urllib.error.HTTPError as e:
        # Server responded with an error code (e.g., 404, 403, 500)
        return PingUrlResult(status_code = e.code, reason = e.reason)
        
    except urllib.error.URLError as e:
        # Connection failed entirely (e.g., DNS failure, network down)
        return PingUrlResult(status_code = 0, reason = f"Connection Failed: {e.reason}")
        
    except Exception as e:
        # Catch-all for timeouts or unexpected errors
        return PingUrlResult(status_code = 0, reason = str(e))


def is_valid_web_url(url:str)->bool:
    try:
        parsed = urlparse(url)
        # Ensure it has a valid scheme and an actual destination host
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False