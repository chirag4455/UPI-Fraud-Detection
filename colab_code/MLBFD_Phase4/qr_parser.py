"""
qr_parser.py — UPI QR code / deep-link parser.

Parses the standard ``upi://pay?...`` URI format used by BHIM, PhonePe,
Google Pay and other UPI apps.  Also handles raw VPA strings (no scheme).

UPI deep-link spec (NPCI): https://www.npci.org.in/PDF/npci/upi/circular/2017/
    upi://pay?
        pa=<VPA>&          # payee address (mandatory)
        pn=<name>&         # payee name
        mc=<MCC>&          # merchant category code
        tr=<txn_ref>&      # transaction reference
        tn=<note>&         # transaction note
        am=<amount>&       # pre-filled amount
        cu=<currency>&     # currency (default INR)
        url=<link>         # optional info URL

Returns a structured dict with parsed fields + metadata.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import parse_qs, unquote, urlparse
from typing import Optional

logger = logging.getLogger("mlbfd.qr_parser")

# Simple VPA pattern: local@provider
_VPA_RE = re.compile(r"^[a-zA-Z0-9.\-_+]+@[a-zA-Z0-9.\-]+$")


def parse_upi_qr(payload: Optional[str]) -> dict:
    """Parse a UPI QR code payload and return structured data.

    Handles:
    * ``upi://pay?pa=...`` (standard deep-link)
    * ``https://...`` QR codes that redirect to a UPI deep-link
    * Raw VPA strings like ``merchant@okaxis``

    Parameters
    ----------
    payload:
        Raw string scanned from the QR code.

    Returns
    -------
    dict with keys:
        success (bool), vpa (str), payee_name (str), amount (float|None),
        amount_fixed (bool), currency (str), txn_ref (str), note (str),
        mcc (str), info_url (str), raw (str), error (str|None)
    """
    result: dict = {
        "success": False,
        "vpa": None,
        "payee_name": None,
        "amount": None,
        "amount_fixed": False,
        "currency": "INR",
        "txn_ref": None,
        "note": None,
        "mcc": None,
        "info_url": None,
        "raw": payload or "",
        "error": None,
    }

    if not payload:
        result["error"] = "empty payload"
        return result

    payload = payload.strip()

    # ── Bare VPA string (no scheme) ───────────────────────────────────────
    if _VPA_RE.match(payload):
        result["success"] = True
        result["vpa"] = payload.lower()
        logger.debug("QR parsed as bare VPA: %s", payload)
        return result

    # ── Normalise scheme ──────────────────────────────────────────────────
    # Some QRs use UPIID:// or UPI://
    normalised = re.sub(r"^upiid://", "upi://", payload, flags=re.IGNORECASE)
    normalised = re.sub(r"^upi://", "upi://", normalised, flags=re.IGNORECASE)

    # Handle https:// QR codes that encode a UPI deep-link as a redirect URL
    if normalised.lower().startswith("http"):
        # Attempt to find embedded upi:// in the URL
        upi_match = re.search(r"upi://pay\?[^\s\"']+", payload, re.IGNORECASE)
        if upi_match:
            normalised = upi_match.group(0)
        else:
            result["error"] = "HTTPS QR code without embedded UPI deep-link"
            logger.warning("QR parse failed: %s", result["error"])
            return result

    # ── Parse as UPI deep-link ────────────────────────────────────────────
    try:
        # urllib.parse.urlparse handles upi:// correctly on Python ≥ 3.9
        # For older versions we replace the scheme.
        parseable = normalised.replace("upi://", "https://", 1)
        parsed = urlparse(parseable)
        qs = parse_qs(parsed.query, keep_blank_values=False)
    except Exception as exc:
        result["error"] = "URL parse error: {}".format(exc)
        return result

    def _first(key: str) -> Optional[str]:
        vals = qs.get(key)
        return unquote(vals[0]).strip() if vals else None

    vpa = _first("pa")
    if not vpa:
        result["error"] = "missing mandatory 'pa' (payee address) field"
        return result

    # Validate VPA format
    if not _VPA_RE.match(vpa):
        result["error"] = "invalid VPA format: {}".format(vpa)
        return result

    amount_str = _first("am")
    amount: Optional[float] = None
    amount_fixed = False
    if amount_str:
        try:
            amount = float(amount_str)
            amount_fixed = True  # pre-filled amount should be treated as fixed
        except ValueError:
            logger.warning("Invalid amount in QR: %s", amount_str)

    result.update(
        success=True,
        vpa=vpa.lower(),
        payee_name=_first("pn"),
        amount=amount,
        amount_fixed=amount_fixed,
        currency=(_first("cu") or "INR").upper(),
        txn_ref=_first("tr"),
        note=_first("tn"),
        mcc=_first("mc"),
        info_url=_first("url"),
    )

    logger.debug("QR parsed: vpa=%s amount=%s fixed=%s", vpa, amount, amount_fixed)
    return result


def mask_vpa(vpa: Optional[str]) -> str:
    """Return a privacy-safe masked VPA (e.g. ``ab***@ybl``).

    The first two characters are preserved; the local-part is masked with
    asterisks; the provider domain is preserved in full.

    Example
    -------
    >>> mask_vpa("chirag123@oksbi")
    'ch*****@oksbi'
    """
    if not vpa:
        return "***@***"
    parts = vpa.split("@", 1)
    local = parts[0]
    domain = parts[1] if len(parts) > 1 else "upi"
    masked = local[:2] + "*" * max(len(local) - 2, 3)
    return "{}@{}".format(masked, domain)
