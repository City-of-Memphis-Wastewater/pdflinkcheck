#!/usr/bin/env python3 
# SPDX-License-Identifier: MIT
# src/pdflinkcheck/ping.py
from dataclasses import dataclass
import urllib.request
import urllib.error
import logging
logger = logging.getLogger(__name__)


# ---  Local Imports ---
#None

# --- Data Classes, Enum, Flag, and stability
# dataclass example(s): ObtainResult

@dataclass()
#@dataclass
class PingUrlResult:
    status: int
    reason: str

    @property
    def success(self) -> bool | None:

        if self.status == 0:
            return None

        if 200 <= self.status < 400:
            return True

        return False
        
    @property
    def success_text(self) -> str:
        return {
            200: "OK",
            404: "Not Found",
            666: "Not Yet Implemented",
        }.get(self.status, "Error.")
    
    #def __bool__(self):
    #   return self.success

# --- 

def ping_url(url:str|None):
    logger.debug(f"ping:{url=} (not yet implemented)")
    response = 666
    text = "not yet implemented"
    result = PingUrlResult(response,text)
    return result

# ---

def ping_url_mock(url: str | None) -> PingUrlResult:
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
            return PingUrlResult(response.status, response.reason)
            
    except urllib.error.HTTPError as e:
        # Server responded with an error code (e.g., 404, 403, 500)
        return PingUrlResult(e.code, e.reason)
        
    except urllib.error.URLError as e:
        # Connection failed entirely (e.g., DNS failure, network down)
        return PingUrlResult(0, f"Connection Failed: {e.reason}")
        
    except Exception as e:
        # Catch-all for timeouts or unexpected errors
        return PingUrlResult(0, str(e))
