"""
wts.py — Wallet Trust Score (WTS) layer.

The WTS layer answers: "Is the wallet (device + location + payee network)
behaving trustworthily?"

It examines device consistency, geolocation patterns, known-payee network size
and velocity signals derived from recent transaction history.

Score components
----------------
1. Device consistency     — known device earns trust
2. Geolocation pattern    — transactions from usual location earn trust
3. Known-payee bonus      — large payee network suggests legitimate activity
4. Velocity penalty       — many transactions in a short window raises risk
5. High-amount + new-device combined risk

Returns: float 0–100 (higher = more trustworthy)
"""

from __future__ import annotations

import logging
import math
from typing import Optional

logger = logging.getLogger("mlbfd.wts")

# ---------------------------------------------------------------------------
# Tuneable constants
# ---------------------------------------------------------------------------
_DEVICE_BONUS: float = 20.0         # known device bonus
_NEW_DEVICE_PENALTY: float = 15.0   # unknown device penalty
_LOCATION_BONUS_MAX: float = 15.0   # max bonus for consistent location
_PAYEE_BONUS_MAX: float = 20.0      # max bonus for large payee network
_PAYEE_THRESHOLD: int = 10          # unique payees to reach max bonus
_VELOCITY_PENALTY_MAX: float = 25.0 # max penalty for rapid transactions
_VELOCITY_WINDOW_MIN: int = 60      # minutes window for velocity check
_VELOCITY_THRESHOLD: int = 5        # txns in window = max penalty
_HIGH_AMT_NEW_DEVICE_PENALTY: float = 15.0
_HIGH_AMOUNT_THRESHOLD: float = 20000.0
_BASE_SCORE: float = 45.0


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in kilometres between two coordinates."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def compute_wts(
    user_id: str,
    device_id: Optional[str],
    is_known_device: bool,
    latitude: Optional[float],
    longitude: Optional[float],
    payee_upi: Optional[str],
    amount: float,
    user_transactions: Optional[list[dict]] = None,
) -> dict:
    """Compute the Wallet Trust Score for one transaction.

    Parameters
    ----------
    user_id:
        Unique user identifier (logging only).
    device_id:
        Fingerprint/identifier of the device initiating the transaction.
    is_known_device:
        True if the device has been seen before for this user.
    latitude, longitude:
        GPS coordinates of the transaction (may be None).
    payee_upi:
        Destination UPI VPA (may be None).
    amount:
        Transaction amount in INR.
    user_transactions:
        Recent transaction dicts from SQLite.

    Returns
    -------
    dict with keys: score (float 0–100), components (dict), explanation (str)
    """
    score: float = _BASE_SCORE
    components: dict = {}

    # ── 1. Device consistency ─────────────────────────────────────────────
    if is_known_device:
        components["device_bonus"] = _DEVICE_BONUS
        score += _DEVICE_BONUS
    else:
        components["device_bonus"] = -_NEW_DEVICE_PENALTY
        score -= _NEW_DEVICE_PENALTY

    # ── 2. Geolocation consistency ────────────────────────────────────────
    location_bonus = 0.0
    if latitude is not None and longitude is not None and user_transactions:
        past_lats = [t.get("latitude") for t in user_transactions if t.get("latitude")]
        past_lons = [t.get("longitude") for t in user_transactions if t.get("longitude")]
        if past_lats and past_lons:
            mean_lat = sum(past_lats) / len(past_lats)
            mean_lon = sum(past_lons) / len(past_lons)
            dist_km = _haversine_km(latitude, longitude, mean_lat, mean_lon)
            # Bonus decays with distance: 0 km → full bonus, 500 km → 0
            location_bonus = _LOCATION_BONUS_MAX * max(0.0, 1.0 - dist_km / 500.0)
    elif latitude is None:
        # No GPS data → neutral contribution
        location_bonus = _LOCATION_BONUS_MAX * 0.3
    components["location_bonus"] = round(location_bonus, 2)
    score += location_bonus

    # ── 3. Known-payee network bonus ─────────────────────────────────────
    payee_bonus = 0.0
    if user_transactions:
        unique_payees = {t.get("payee_upi") for t in user_transactions if t.get("payee_upi")}
        payee_count = len(unique_payees)
        payee_bonus = min(payee_count / _PAYEE_THRESHOLD, 1.0) * _PAYEE_BONUS_MAX
        # Extra: if current payee is already in the known set, add bonus
        if payee_upi and payee_upi in unique_payees:
            payee_bonus = min(payee_bonus + 5.0, _PAYEE_BONUS_MAX)
    components["payee_network_bonus"] = round(payee_bonus, 2)
    score += payee_bonus

    # ── 4. Transaction velocity penalty ──────────────────────────────────
    velocity_penalty = 0.0
    if user_transactions:
        # Approximate: count recent transactions (we don't parse timestamps,
        # so we proxy with the total count in the window returned by the query)
        recent_count = len(user_transactions)
        if recent_count >= _VELOCITY_THRESHOLD:
            velocity_penalty = _VELOCITY_PENALTY_MAX * min(
                (recent_count - _VELOCITY_THRESHOLD + 1) / _VELOCITY_THRESHOLD, 1.0
            )
    components["velocity_penalty"] = -round(velocity_penalty, 2)
    score -= velocity_penalty

    # ── 5. High-amount + unknown-device combined penalty ─────────────────
    combined_penalty = 0.0
    if amount >= _HIGH_AMOUNT_THRESHOLD and not is_known_device:
        combined_penalty = _HIGH_AMT_NEW_DEVICE_PENALTY
    components["high_amt_new_device_penalty"] = -round(combined_penalty, 2)
    score -= combined_penalty

    # ── Clamp ─────────────────────────────────────────────────────────────
    score = max(0.0, min(100.0, score))

    # ── Explanation ───────────────────────────────────────────────────────
    remarks = []
    if is_known_device:
        remarks.append("trusted device")
    else:
        remarks.append("unknown/new device")
    if location_bonus < _LOCATION_BONUS_MAX * 0.3 and latitude is not None:
        remarks.append("unusual transaction location")
    if payee_bonus >= _PAYEE_BONUS_MAX * 0.6:
        remarks.append("familiar payee network")
    if velocity_penalty >= _VELOCITY_PENALTY_MAX * 0.5:
        remarks.append("high transaction velocity")
    if combined_penalty > 0:
        remarks.append("large amount on unrecognised device")
    explanation = "; ".join(remarks) if remarks else "normal wallet behaviour"

    logger.debug("WTS user=%s score=%.1f components=%s", user_id, score, components)
    return {
        "score": round(score, 2),
        "components": components,
        "explanation": explanation,
    }
