"""
website_trust.py — Website / URL trust-scoring layer.

Detects phishing attempts embedded in UPI transaction metadata such as the
``pn`` (payee name) field or any URL submitted alongside a payment request.

All checks are **offline heuristics** (v1) — no external network call is made
so the system works in air-gapped / Colab environments.

Score components
----------------
1. HTTPS presence              — HTTP sites lose trust
2. Brand impersonation check   — typosquatting / lookalike domains
3. Suspicious keyword density  — high density lowers trust
4. Suspicious TLD              — .xyz/.top/etc lower trust
5. URL length penalty          — very long URLs are a red flag
6. Subdomain depth penalty     — deep subdomains are suspicious

Returns: float 0–100 (higher = more trustworthy)
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urlparse
from typing import Optional

from config import KNOWN_BRANDS, SUSPICIOUS_TLDS, SUSPICIOUS_KEYWORDS

logger = logging.getLogger("mlbfd.website_trust")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_BASE_SCORE: float = 75.0
_HTTPS_BONUS: float = 10.0
_HTTP_PENALTY: float = 20.0
_BRAND_IMPERSONATION_PENALTY: float = 35.0
_SUSPICIOUS_KEYWORD_PENALTY_PER: float = 5.0
_SUSPICIOUS_KEYWORD_MAX_PENALTY: float = 25.0
_SUSPICIOUS_TLD_PENALTY: float = 20.0
_URL_LENGTH_THRESHOLD: int = 75
_URL_LENGTH_PENALTY_MAX: float = 10.0
_SUBDOMAIN_DEPTH_THRESHOLD: int = 3
_SUBDOMAIN_PENALTY: float = 10.0


def _extract_domain(url: str) -> str:
    """Return lowercase domain (including subdomains) from a URL string."""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    parsed = urlparse(url)
    return (parsed.netloc or parsed.path).lower().split(":")[0]


def _is_typosquat(domain: str, brands: list[str]) -> bool:
    """Return True if *domain* appears to impersonate one of the *brands*.

    Checks:
    * Exact brand name embedded in subdomain (e.g. sbi.fraud-login.com)
    * Simple edit-distance ≤ 2 against brand names ≥ 4 chars
    """
    parts = domain.replace("-", ".").split(".")
    # Check subdomains / labels for brand presence
    for brand in brands:
        for part in parts[:-1]:   # exclude the TLD part
            if brand in part:
                return True

    # Levenshtein-1 check against the second-level domain
    sld = parts[-2] if len(parts) >= 2 else domain
    for brand in brands:
        if len(brand) >= 4 and _levenshtein(sld, brand) <= 2 and sld != brand:
            return True
    return False


def _levenshtein(s1: str, s2: str) -> int:
    """Compute Levenshtein distance between two short strings."""
    if len(s1) < len(s2):
        s1, s2 = s2, s1
    if not s2:
        return len(s1)
    prev = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr = [i + 1]
        for j, c2 in enumerate(s2):
            curr.append(min(prev[j + 1] + 1, curr[j] + 1,
                            prev[j] + (0 if c1 == c2 else 1)))
        prev = curr
    return prev[-1]


def score_url(url: Optional[str]) -> dict:
    """Compute the Website Trust Score for a given URL or payee-name string.

    Parameters
    ----------
    url:
        A URL string, a payee name that might contain a URL, or ``None``.
        When ``None`` or an empty string, a neutral score is returned.

    Returns
    -------
    dict with keys: score (float 0–100), components (dict), explanation (str),
                    is_suspicious (bool)
    """
    if not url:
        return {
            "score": 80.0,
            "components": {},
            "explanation": "no URL provided",
            "is_suspicious": False,
        }

    url_lower = url.lower()
    score: float = _BASE_SCORE
    components: dict = {}
    remarks: list[str] = []

    # ── 1. HTTPS check ────────────────────────────────────────────────────
    if url_lower.startswith("https://"):
        components["https_bonus"] = _HTTPS_BONUS
        score += _HTTPS_BONUS
    elif url_lower.startswith("http://"):
        components["http_penalty"] = -_HTTP_PENALTY
        score -= _HTTP_PENALTY
        remarks.append("insecure HTTP connection")
    else:
        components["https_bonus"] = 0.0  # no scheme — neutral

    # ── 2. Brand impersonation ────────────────────────────────────────────
    try:
        domain = _extract_domain(url_lower)
    except Exception:
        domain = url_lower

    impersonation_penalty = 0.0
    if _is_typosquat(domain, KNOWN_BRANDS):
        impersonation_penalty = _BRAND_IMPERSONATION_PENALTY
        remarks.append("suspected brand impersonation / typosquatting")
    components["brand_impersonation_penalty"] = -round(impersonation_penalty, 2)
    score -= impersonation_penalty

    # ── 3. Suspicious keywords ────────────────────────────────────────────
    kw_hits = [kw for kw in SUSPICIOUS_KEYWORDS if kw in url_lower]
    kw_penalty = min(len(kw_hits) * _SUSPICIOUS_KEYWORD_PENALTY_PER,
                     _SUSPICIOUS_KEYWORD_MAX_PENALTY)
    if kw_hits:
        remarks.append("suspicious keywords: {}".format(", ".join(kw_hits[:3])))
    components["keyword_penalty"] = -round(kw_penalty, 2)
    score -= kw_penalty

    # ── 4. Suspicious TLD ─────────────────────────────────────────────────
    tld_penalty = 0.0
    for tld in SUSPICIOUS_TLDS:
        if domain.endswith(tld):
            tld_penalty = _SUSPICIOUS_TLD_PENALTY
            remarks.append("high-risk TLD ({})".format(tld))
            break
    components["tld_penalty"] = -round(tld_penalty, 2)
    score -= tld_penalty

    # ── 5. URL length penalty ─────────────────────────────────────────────
    url_len = len(url)
    length_penalty = 0.0
    if url_len > _URL_LENGTH_THRESHOLD:
        excess = url_len - _URL_LENGTH_THRESHOLD
        length_penalty = min(excess / 50.0, 1.0) * _URL_LENGTH_PENALTY_MAX
    components["url_length_penalty"] = -round(length_penalty, 2)
    score -= length_penalty

    # ── 6. Subdomain depth penalty ────────────────────────────────────────
    subdomain_penalty = 0.0
    subdomain_depth = len(domain.split("."))
    if subdomain_depth > _SUBDOMAIN_DEPTH_THRESHOLD:
        subdomain_penalty = _SUBDOMAIN_PENALTY
        remarks.append("deep subdomain structure")
    components["subdomain_penalty"] = -round(subdomain_penalty, 2)
    score -= subdomain_penalty

    # ── Clamp ─────────────────────────────────────────────────────────────
    score = max(0.0, min(100.0, score))
    is_suspicious = score < 50.0

    explanation = "; ".join(remarks) if remarks else "URL appears legitimate"
    logger.debug("WebsiteTrust score=%.1f suspicious=%s", score, is_suspicious)
    return {
        "score": round(score, 2),
        "components": components,
        "explanation": explanation,
        "is_suspicious": is_suspicious,
    }


def score_payee_name(payee_name: Optional[str]) -> dict:
    """Check a payee display name for impersonation signals.

    Payee names sometimes contain embedded URLs or obvious brand fakes
    (e.g. "SBI Bank Support").  This is a lightweight wrapper around
    :func:`score_url` that also runs a direct brand-name check.
    """
    if not payee_name:
        return {"score": 80.0, "components": {}, "explanation": "no payee name",
                "is_suspicious": False}

    name_lower = payee_name.lower()
    base = score_url(payee_name)  # reuse URL scorer for embedded-URL detection

    # Extra: direct brand mention with suspicious extra words
    brand_hit = any(brand in name_lower for brand in KNOWN_BRANDS)
    suspicious_extra = any(kw in name_lower for kw in ["support", "helpline",
                                                        "customer", "care",
                                                        "refund", "kyc"])
    if brand_hit and suspicious_extra:
        penalty = 20.0
        base["score"] = max(0.0, base["score"] - penalty)
        base["components"]["brand_support_penalty"] = -penalty
        base["explanation"] += "; possible impersonation of bank/brand support"
        base["is_suspicious"] = base["score"] < 50.0

    return base
