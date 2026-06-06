#!/usr/bin/env python3 
# SPDX-License-Identifier: MIT
# src/pdflinkcheck/ping.py
import logging
logger = logging.getLogger(__name__)
from .helpers import PingUrlResult


@dataclass()
class PingUrlResult:
    success: bool
    status: int
    reason: str
   
    @property
    def success(self) -> str:
        """Typical web return status integer interpretations."""
        return {
            True: 200,
            False: 404,
            None: 666
        }.get(self.status, "Error.")

    def __bool__(self):
        return self.success

    
def ping_url(url:str|None):
    logger.debug(f"ping:{url=} (not yet implemented)")
    success = False
    response = 666
    text = "not yet implemented"
    result = PingUrlResult(success,response,text)
    return result


# exanple
'''
class ObtainResult:
    value: Optional[str] = None
    is_new: Optional[bool] = False  # True=New, False=Known, None=Cancelled

    @property
    def status_message(self) -> str:
        """Generic statuses that work for any key/service."""
        return {
            True: "Value stored.",
            False: "Value resolved.",
            None: "Exited."
        }.get(self.is_new, "Error.")

    def __bool__(self):
        return self.value is not None
'''
