#!/usr/bin/env python3 
# SPDX-License-Identifier: MIT
# src/pdflinkcheck/ping.py
import logging
logger = logging.getLogger(__name__)
from .helpers import PingUrlResult

def ping_url(url:str|None):
    logger.debug(f"ping:{url=} (not yet implemented)")
    success = False
    status = 666
    reason = "not yet implemented"
    result = PingUrlResult(success,status,reason)
    return result