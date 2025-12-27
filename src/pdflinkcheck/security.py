"""
pdflinkcheck.security

Minimal offline link risk analysis.

This module provides a tiny, deterministic scoring engine for evaluating
external hyperlinks extracted from PDFs. It is intentionally limited in scope
and designed to be stable, low-maintenance, and fully offline.

Architecture notes (developer-facing):

- No external data files. All rule tables are embedded below.
- No network calls. No threat feeds. No URL fetching.
- No malware detection claims. This is *risk scoring*, not antivirus.
- The API mirrors validate.py:
      - score_link(url, anchor_text)
      - compute_risk(report_dict)
- compute_risk() returns a dict that can be merged into report["data"].

This keeps the feature optional, safe, and easy to integrate.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from urllib.parse import urlparse, parse_qs
import ipaddress
import re
from typing import List, Dict, Optional


# ---------------------------------------------------------------------------
# Internal static rule tables (no external files)
# ---------------------------------------------------------------------------

SUSPICIOUS_TLDS = {
    "xyz", "top", "click", "link", "rest", "gq", "ml", "cf", "tk"
}

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign",
    "fbclid", "gclid", "mc_eid"
}

HOMOGLYPHS = {
    "а": "a",
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
    anchor_text: Optional[str]
    score: int
    level: str
    reasons: List[RiskReason]

    def to_dict(self) -> Dict[str, object]:
        d = asdict(self)
        d["reasons"] = [asdict(r) for r in self.reasons]
        return d


# ---------------------------------------------------------------------------
# Rule helpers
# ---------------------------------------------------------------------------

def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except Exception:
        return False


def _contains_homoglyphs(s: str) -> bool:
    return any(ch in HOMOGLYPHS for ch in s)


def _anchor_mismatch(anchor: str, host: str) -> bool:
    anchor = anchor.lower().strip()
    host = host.lower().strip()

    tokens = re.findall(r"[a-z0-9._-]+", anchor)
    for token in tokens:
        if "." in token:
            if token not in host:
                return True
        else:
            if len(token) >= 4 and token not in host:
                return True
    return False


# ---------------------------------------------------------------------------
# Core scoring function
# ---------------------------------------------------------------------------

def score_link(url: str, anchor_text: Optional[str] = None) -> LinkRiskResult:
    reasons: List[RiskReason] = []
    score = 0

    parsed = urlparse(url)
    host = parsed.hostname or ""
    query = parsed.query or ""

    if _is_ip(host):
        reasons.append(RiskReason("ip_host", "URL uses a raw IP address.", 3))
        score += 3

    if "." in host:
        tld = host.rsplit(".", 1)[-1].lower()
        if tld in SUSPICIOUS_TLDS:
            reasons.append(RiskReason("suspicious_tld", f"TLD '.{tld}' is suspicious.", 2))
            score += 2

    if parsed.port not in (None, 80, 443):
        reasons.append(RiskReason("nonstandard_port", f"Non-standard port {parsed.port}.", 2))
        score += 2

    if len(url) > 200:
        reasons.append(RiskReason("long_url", "URL is unusually long.", 1))
        score += 1

    params = parse_qs(query)
    tracking_hits = sum(1 for p in params if p.lower() in TRACKING_PARAMS)
    if tracking_hits:
        reasons.append(RiskReason("tracking_params", f"{tracking_hits} tracking parameters found.", 1))
        score += 1

    if anchor_text and host:
        if _anchor_mismatch(anchor_text, host):
            reasons.append(RiskReason("anchor_mismatch", "Anchor text does not match URL host.", 3))
            score += 3

    if _contains_homoglyphs(host + parsed.path):
        reasons.append(RiskReason("homoglyph_suspected", "URL contains homoglyph characters.", 3))
        score += 3

    if score >= 7:
        level = "high"
    elif score >= 3:
        level = "medium"
    else:
        level = "low"

    return LinkRiskResult(url, anchor_text, score, level, reasons)


# ---------------------------------------------------------------------------
# Report-level risk computation (mirrors validate.py)
# ---------------------------------------------------------------------------

def compute_risk(report: Dict[str, object]) -> Dict[str, object]:
    external_links = report.get("data", {}).get("external_links", [])
    results = []

    for link in external_links:
        url = link.get("url") or link.get("remote_file") or link.get("target")
        anchor = link.get("link_text", "")
        if url:
            results.append(score_link(url, anchor).to_dict())

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
