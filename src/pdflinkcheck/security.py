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
from urllib.parse import urlparse, parse_qs
import ipaddress
from typing import List, Dict, Optional


# ---------------------------------------------------------------------------
# Static rule tables (embedded; no external files)
# ---------------------------------------------------------------------------

SUSPICIOUS_TLDS = {
    "xyz", "top", "click", "link", "rest", "gq", "ml", "cf", "tk"
}

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign",
    "fbclid", "gclid", "mc_eid"
}

# Minimal homoglyph table (expandable)
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

@dataclass
class RiskReason:
    rule_id: str
    description: str
    weight: int


@dataclass
class LinkRiskResult:
    url: str
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
    except Exception:
        return False


def _contains_homoglyphs(s: str) -> bool:
    return any(ch in HOMOGLYPHS for ch in s)


# ---------------------------------------------------------------------------
# Core scoring function (URL‑structure‑based only)
# ---------------------------------------------------------------------------

def score_link(url: str) -> LinkRiskResult:
    reasons: List[RiskReason] = []
    score = 0

    parsed = urlparse(url)
    host = parsed.hostname or ""
    query = parsed.query or ""

    # IP‑based URL
    if _is_ip(host):
        reasons.append(RiskReason("ip_host", "URL uses a raw IP address.", 3))
        score += 3

    # Suspicious TLD
    if "." in host:
        tld = host.rsplit(".", 1)[-1].lower()
        if tld in SUSPICIOUS_TLDS:
            reasons.append(RiskReason("suspicious_tld", f"TLD '.{tld}' is commonly abused.", 2))
            score += 2

    # Non‑standard port
    if parsed.port not in (None, 80, 443):
        reasons.append(RiskReason("nonstandard_port", f"Non‑standard port {parsed.port}.", 2))
        score += 2

    # Long URL
    if len(url) > 200:
        reasons.append(RiskReason("long_url", "URL is unusually long.", 1))
        score += 1

    # Tracking parameters
    params = parse_qs(query)
    tracking_hits = sum(1 for p in params if p.lower() in TRACKING_PARAMS)
    if tracking_hits:
        reasons.append(RiskReason("tracking_params", f"{tracking_hits} tracking parameters found.", 1))
        score += 1

    # Homoglyph detection
    if _contains_homoglyphs(host + parsed.path):
        reasons.append(RiskReason("homoglyph_suspected", "URL contains homoglyph characters.", 3))
        score += 3
    # Risk level mapping
    if score == 0:
        level = "none"
    elif score <= 2:
        level = "low"
    elif score <= 6:
        level = "medium"
    else:
        level = "high"


    return LinkRiskResult(url, score, level, reasons)


# ---------------------------------------------------------------------------
# Report‑level risk computation (mirrors validate.py)
# ---------------------------------------------------------------------------

def compute_risk(report: Dict[str, object]) -> Dict[str, object]:
    external_links = report.get("data", {}).get("external_links", [])
    results = []

    for link in external_links:
        url = link.get("url") or link.get("remote_file") or link.get("target")
        if url:
            results.append(score_link(url).to_dict())

    return {
        "risk_summary": {
            "total_external": len(external_links),
            "scored": len(results),
            "high_risk": sum(1 for r in results if r["level"] == "high"),
            "medium_risk": sum(1 for r in results if r["level"] == "medium"),
            "low_risk": sum(1 for r in results if r["level"] == "low"),
        },
        "risk_details": results
    }
