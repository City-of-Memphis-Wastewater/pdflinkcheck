"""
pdflinkcheck.security

Offline, deterministic link‑risk scoring for PDF hyperlinks.

This module intentionally avoids any heuristics that depend on PDF text
extraction quality (e.g., anchor text analysis), because real‑world PDFs
often contain inconsistent OCR output, concatenated strings, or placeholder
text. Only URL‑structure‑based signals are used.

Stable, low‑maintenance, and fully offline.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from urllib.parse import parse_qs
import ipaddress
from enum import Enum
from typing import List, Dict, Optional
import logging 

logger = logging.getLogger(__name__)


from .url_parse import parse_url_helper

# ---------------------------------------------------------------------------
# Static rule tables (embedded; no external files)
# ---------------------------------------------------------------------------

# Top level domain (tld)
SUSPICIOUS_TLDS_LIST = {
    "xyz", "top", "click", "link", "rest", "gq", "ml", "cf", "tk"
}

# Tracking parameters
"""
These parameters collectively allow detailed attribution of website traffic and conversions:
- **utm_** parameters are universal for tracking campaigns across all traffic sources.
- **fbclid** and **gclid** are platform-specific identifiers for Facebook and Google Ads.
- **mc_eid** is specific to email marketing, like Mailchimp campaigns.
"""
TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign",
    "fbclid", "gclid", "mc_eid"
}

# Minimal homoglyph table (expandable)
"""
"а" → Latin "a" (Cyrillic small letter a, U+0430 vs Latin a U+0061)
"е" → Latin "e" (Cyrillic small letter ie, U+0435 vs Latin e U+0065)
"і" → Latin "i" (Cyrillic small letter i, U+0456 vs Latin i U+0069)
"ο" → Latin "o" (Greek small omicron, U+03BF vs Latin o U+006F)
"р" → Latin "p" (Cyrillic small er, U+0440 vs Latin p U+0070)
"ѕ" → Latin "s" (Cyrillic small letter dze, U+0455 vs Latin s U+0073)
"у" → Latin "y" (Cyrillic small letter u, U+0443 vs Latin y U+0079)

These characters have distinct Unicode code points from their Latin lookalikes 
but are visually nearly identical, making them classic homoglyphs. 
The purpose of such mappings is often to detect or simulate homoglyph attacks, 
such as phishing domains, email spoofing, or source code obfuscation, 
where attackers substitute visually similar characters from alternate scripts to deceive users or systems.
"""
HOMOGLYPHS = {
    "а": "a",  # Cyrillic
    "е": "e",
    "і": "i",
    "ο": "o",
    "р": "p",
    "ѕ": "s",
    "у": "y",
}

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class RiskReasonEnum(str, Enum):
    SUSPICIOUS_TLDS_RISK = "risk_suspicious_tld"
    NONSTANDARD_PORT = "risk_nonstandard_port"
    LONG_URL = "risk_long_url"
    TRACKING_PARAMS = "risk_tracking_params"
    HOMOGLYPH_SUSPECTED = "risk_homoglyph_suspected"
    IP_HOST = "risk_ip_host"

@dataclass
class RiskReason:
    rule_id: str
    description: str
    weight: int

class RiskLevel(str, Enum):
    ZERO = "zero"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class LinkRiskResult:
    score: int
    level: str
    reasons: List[RiskReason]

    def to_dict(self) -> Dict[str, object]:
        d = asdict(self)
        d["reasons"] = [asdict(r) for r in self.reasons]
        return d


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except Exception as e:
        # this is a good thing, don't yell - IP addresses are a security risk
        #logger.debug(f"Issue with IP address assessment: {e}") 
        return False

def _contains_homoglyphs(s: str) -> bool:
    return any(ch in HOMOGLYPHS for ch in s)


# ---------------------------------------------------------------------------
# Core scoring function (URL‑structure‑based only)
# ---------------------------------------------------------------------------

def score_link_security_risk(url: str) -> LinkRiskResult:
    reasons: List[RiskReason] = []
    score = 0

    parsed,host,query = parse_url_helper(url)

    # IP‑based URL
    if _is_ip(host):
        reasons.append(RiskReason(RiskReasonEnum.IP_HOST.value, "URL uses a raw IP address.", 3))
        score += 3

    # Suspicious TLD
    if "." in host:
        tld = host.rsplit(".", 1)[-1].lower()
        if tld in SUSPICIOUS_TLDS_LIST:
            reasons.append(RiskReason(RiskReasonEnum.SUSPICIOUS_TLDS_RISK.value, f"TLD '.{tld}' is commonly abused.", 2))
            score += 2

    # Non‑standard port
    if parsed.port not in (None, 80, 443):
        reasons.append(RiskReason(RiskReasonEnum.NONSTANDARD_PORT.value, f"Non‑standard port {parsed.port}.", 2))
        score += 2

    # Long URL
    if len(url) > 200:
        reasons.append(RiskReason(RiskReasonEnum.LONG_URL.value, "URL is unusually long.", 1))
        score += 1

    # Tracking parameters
    params = parse_qs(query)
    tracking_hits = sum(1 for p in params if p.lower() in TRACKING_PARAMS)
    if tracking_hits:
        reasons.append(RiskReason(RiskReasonEnum.TRACKING_PARAMS.value, f"{tracking_hits} tracking parameters found.", 1))
        score += 1

    # Homoglyph detection
    if _contains_homoglyphs(host + parsed.path):
        reasons.append(RiskReason(RiskReasonEnum.HOMOGLYPH_SUSPECTED.value, "URL contains homoglyph characters.", 3))
        score += 3


    # Risk level mapping
    if score == 0:
        level = RiskLevel.ZERO.value
    elif score <= 2:
        level = RiskLevel.LOW.value
    elif score <= 6:
        level = RiskLevel.MEDIUM.value
    else:
        level = RiskLevel.HIGH.value


    return LinkRiskResult(score, level, reasons)

# ---------------------------------------------------------------------------
# Report‑level risk computation (mirrors validate.py)
# ---------------------------------------------------------------------------

def compute_risk(report: Dict[str, object]) -> Dict[str, object]:
    logger.debug("security.compute_risk()")
    external_links = report.get("data", {}).get("external_links", [])
    results = []

    for link in external_links:
        url = link.get("details",{}).get("url") or link.get("details",{}).get("remote_file") or link.get("details",{}).get("target")
        if url:
            result_link = score_link_security_risk(url).to_dict()
            results.append(result_link)
            link["security_risk"] = result_link # mutate that junt, originally empty from helpers.create_link_dict()

    return {
        "risk_summary": {
            "total_external": len(external_links),
            "scored": len(results),
            "high_risk": sum(1 for r in results if r["level"] == RiskLevel.HIGH.value),
            "medium_risk": sum(1 for r in results if r["level"] == RiskLevel.MEDIUM.value),
            "low_risk": sum(1 for r in results if r["level"] == RiskLevel.LOW.value),
            "zero_risk": sum(1 for r in results if r["level"] == RiskLevel.ZERO.value),
        }
        #"risk_details": results
    }
