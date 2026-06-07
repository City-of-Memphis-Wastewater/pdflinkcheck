#!/usr/bin/env python3 
# SPDX-License-Identifier: MIT
# src/pdflinkcheck/ping.py
from dataclasses import dataclass
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

    e@property
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

# --- Useful Functions, External-Facing, Discoverible, Stable, Primitives, Etc ---
def ping_url(url:str|None):
    logger.debug(f"ping:{url=} (not yet implemented)")
    success = False
    response = 666
    text = "not yet implemented"
    result = PingUrlResult(success,response,text)
    return result


# Helper internal functions, with underscore
#None
