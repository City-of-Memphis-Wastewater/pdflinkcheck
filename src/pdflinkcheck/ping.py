#!/usr/bin/env python3 
# SPDX-License-Identifier: MIT
# src/pdflinkcheck/ping.py
import logging
logger = logging.getLogger(__name__)
from .helpers import PingUrlResult

def ping_url(url:str|None):
    logger.debug(f"ping:{url=} (not yet implemented)")
    success = False
    response = 666
    text = "not yet implemented"
    result = PingUrlResult(success,response,text)
    return result