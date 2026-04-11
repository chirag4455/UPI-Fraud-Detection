"""
wts_enhancements.py — Advanced Wallet Trust Score (WTS) Enhancements (Phase 10).

This module extends the base WTS layer with:
  1. Device Geo-Fencing       — Haversine-based distance check vs last known location
  2. Velocity Analysis        — Impossible-travel detection & speed-ratio scoring
  3. Device Fingerprinting    — Device-ID consistency, compromised-device flagging
  4. Payee Network Analysis   — First-time payee penalty, suspicious payee patterns
  5. Amount Velocity          — Daily spend threshold, round-number pattern detection

All thresholds are imported from config.py so they can be tuned without code changes.

Each public function returns a dict:
  {
      "score_delta": float,   # positive = trust boost, negative = penalty
      "flag": bool,           # True = suspicious signal detected
      "detail": str,          # human-readable explanation
  }
"""

from __future__ import annotations

import math
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("mlbfd.wts_enhancements")

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in kilometres between two WGS-84 coordinates."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(min(a, 1.0)))


def _parse_timestamp(ts: object) -> Optional[datetime]:
    """Try to parse *ts* as a UTC-aware datetime; return None on failure."""
    if ts is None:
        return None
    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    if isinstance(ts, (int, float)):
        try:
            return datetime.fromtimestamp(float(ts), tz=timezone.utc)
        except (OSError, OverflowError, ValueError):
            return None
    if isinstance(ts, str):
        for fmt in (
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S.%f",
        ):
            try:
                dt = datetime.strptime(ts, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    return None


# ---------------------------------------------------------------------------
# Part 1: Device Geo-Fencing
# ---------------------------------------------------------------------------

def check_geofence(
    latitude: Optional[float],
    longitude: Optional[float],
    user_transactions: Optional[list[dict]],
    geofence_radius_km: float = 200.0,
    home_lat: Optional[float] = None,
    home_lon: Optional[float] = None,
) -> dict:
    """Check whether the current transaction location is within the geo-fence.

    Parameters
    ----------
    latitude, longitude:
        Current transaction GPS coordinates.
    user_transactions:
        Historical transaction dicts (must contain ``latitude`` and
        ``longitude`` fields for location-aware checks).
    geofence_radius_km:
        Maximum allowed distance from the last known location (default 200 km).
    home_lat, home_lon:
        Optional registered home-region coordinates.  If provided and the
        current location is within *geofence_radius_km* of home, the
        transaction is whitelisted (no penalty).

    Returns
    -------
    dict with keys ``score_delta``, ``flag``, ``detail``.
    """
    if latitude is None or longitude is None:
        return {"score_delta": 0.0, "flag": False, "detail": "no GPS data"}

    # Whitelist: home region check
    if home_lat is not None and home_lon is not None:
        home_dist = _haversine_km(latitude, longitude, home_lat, home_lon)
        if home_dist <= geofence_radius_km:
            return {
                "score_delta": 5.0,
                "flag": False,
                "detail": "within home region ({:.1f} km from home)".format(home_dist),
            }

    # No history → no penalty (first transaction)
    if not user_transactions:
        return {"score_delta": 0.0, "flag": False, "detail": "first transaction; no geo-fence applied"}

    # Find the most recent transaction with valid coordinates
    last_lat: Optional[float] = None
    last_lon: Optional[float] = None
    for txn in reversed(user_transactions):
        lat = txn.get("latitude")
        lon = txn.get("longitude")
        if lat is not None and lon is not None:
            last_lat, last_lon = float(lat), float(lon)
            break

    if last_lat is None or last_lon is None:
        return {"score_delta": 0.0, "flag": False, "detail": "no prior location data"}

    dist_km = _haversine_km(latitude, longitude, last_lat, last_lon)
    if dist_km <= geofence_radius_km:
        bonus = max(0.0, 10.0 * (1.0 - dist_km / geofence_radius_km))
        return {
            "score_delta": round(bonus, 2),
            "flag": False,
            "detail": "within geo-fence ({:.1f} km from last location)".format(dist_km),
        }
    else:
        # Penalty scales with how far outside the fence we are (capped at -20)
        overshoot = dist_km - geofence_radius_km
        penalty = min(20.0, overshoot / 100.0 * 5.0)
        return {
            "score_delta": -round(penalty, 2),
            "flag": True,
            "detail": "outside geo-fence ({:.1f} km from last location, radius {:.0f} km)".format(
                dist_km, geofence_radius_km
            ),
        }


# ---------------------------------------------------------------------------
# Part 2: Velocity Analysis
# ---------------------------------------------------------------------------

def check_velocity(
    latitude: Optional[float],
    longitude: Optional[float],
    timestamp: object,
    user_transactions: Optional[list[dict]],
    max_speed_kmh: float = 900.0,
    short_window_minutes: int = 5,
    short_window_count: int = 5,
) -> dict:
    """Detect impossible travel and rapid-transaction velocity.

    Parameters
    ----------
    latitude, longitude:
        Current transaction GPS coordinates.
    timestamp:
        Current transaction timestamp (datetime, ISO string, or UNIX float).
    user_transactions:
        Historical transaction dicts, each optionally containing
        ``latitude``, ``longitude``, ``timestamp`` fields.
    max_speed_kmh:
        Maximum physically plausible travel speed in km/h (default 900 km/h
        — commercial flight speed).  Anything faster is flagged as impossible.
    short_window_minutes:
        Length of the short-burst window in minutes (default 5).
    short_window_count:
        Number of transactions within *short_window_minutes* that triggers a
        rapid-velocity flag (default 5).

    Returns
    -------
    dict with keys ``score_delta``, ``flag``, ``detail``.
    """
    details: list[str] = []
    total_penalty = 0.0
    flagged = False

    current_dt = _parse_timestamp(timestamp)

    # ── Impossible travel detection ────────────────────────────────────────
    if (
        latitude is not None
        and longitude is not None
        and user_transactions
        and current_dt is not None
    ):
        for txn in reversed(user_transactions):
            prev_lat = txn.get("latitude")
            prev_lon = txn.get("longitude")
            prev_ts = txn.get("timestamp")
            if prev_lat is None or prev_lon is None or prev_ts is None:
                continue

            prev_dt = _parse_timestamp(prev_ts)
            if prev_dt is None:
                continue

            time_diff_h = abs((current_dt - prev_dt).total_seconds()) / 3600.0
            if time_diff_h <= 0:
                continue  # same timestamp; skip

            dist_km = _haversine_km(latitude, longitude, float(prev_lat), float(prev_lon))
            speed_kmh = dist_km / time_diff_h

            if speed_kmh > max_speed_kmh:
                # Velocity risk score: how many times over the speed limit
                ratio = speed_kmh / max_speed_kmh
                penalty = min(25.0, 10.0 * ratio)
                total_penalty += penalty
                flagged = True
                details.append(
                    "impossible travel: {:.0f} km/h (limit {:.0f} km/h), "
                    "{:.1f} km in {:.1f} min".format(
                        speed_kmh, max_speed_kmh, dist_km, time_diff_h * 60
                    )
                )
            break  # only check the most recent previous location

    # ── Rapid-transaction burst detection ─────────────────────────────────
    if user_transactions and current_dt is not None:
        window_secs = short_window_minutes * 60
        recent_count = 0
        for txn in user_transactions:
            ts = txn.get("timestamp")
            if ts is None:
                continue
            txn_dt = _parse_timestamp(ts)
            if txn_dt is None:
                continue
            if abs((current_dt - txn_dt).total_seconds()) <= window_secs:
                recent_count += 1

        if recent_count >= short_window_count:
            burst_penalty = min(15.0, 3.0 * (recent_count - short_window_count + 1))
            total_penalty += burst_penalty
            flagged = True
            details.append(
                "{} transactions in {} minutes (threshold {})".format(
                    recent_count, short_window_minutes, short_window_count
                )
            )
    elif user_transactions and current_dt is None:
        # Fallback: count-based proxy when timestamps are unavailable
        if len(user_transactions) >= short_window_count:
            burst_penalty = 10.0
            total_penalty += burst_penalty
            flagged = True
            details.append(
                "{} recent transactions (velocity proxy)".format(len(user_transactions))
            )

    if not details:
        details.append("normal velocity")

    return {
        "score_delta": -round(min(total_penalty, 30.0), 2),
        "flag": flagged,
        "detail": "; ".join(details),
    }


# ---------------------------------------------------------------------------
# Part 3: Device Fingerprinting Enhancements
# ---------------------------------------------------------------------------

def check_device_fingerprint(
    device_id: Optional[str],
    user_transactions: Optional[list[dict]],
    known_device_threshold: int = 10,
    compromise_window_hours: float = 1.0,
    known_device_bonus: float = 15.0,
) -> dict:
    """Enhanced device fingerprint analysis.

    Parameters
    ----------
    device_id:
        Current transaction device identifier.
    user_transactions:
        Historical transactions, each optionally containing ``device_id``,
        ``timestamp``, and ``country`` / ``latitude``+``longitude`` fields.
    known_device_threshold:
        Minimum prior uses of this device to award the *known device bonus*.
    compromise_window_hours:
        Window in hours within which seeing the same device_id from multiple
        countries/continents is considered a compromise signal.
    known_device_bonus:
        Trust points awarded if the device is a known, long-established device.

    Returns
    -------
    dict with keys ``score_delta``, ``flag``, ``detail``.
    """
    if not device_id:
        return {"score_delta": -5.0, "flag": True, "detail": "missing device ID"}

    if not user_transactions:
        return {"score_delta": -10.0, "flag": True, "detail": "new device (first transaction)"}

    # Count how many times this device_id appears in history
    device_uses = [t for t in user_transactions if t.get("device_id") == device_id]
    use_count = len(device_uses)

    # New device detection
    if use_count == 0:
        return {"score_delta": -10.0, "flag": True, "detail": "new device not seen before"}

    # Known device bonus
    if use_count >= known_device_threshold:
        return {
            "score_delta": known_device_bonus,
            "flag": False,
            "detail": "established device (seen {} times)".format(use_count),
        }

    # ── Compromised device check: same device_id from 2+ distinct regions ──
    # Use country field if available; otherwise derive rough region from lat/lon
    now = datetime.now(tz=timezone.utc)
    window_secs = compromise_window_hours * 3600.0

    recent_txns = []
    for t in device_uses:
        ts = t.get("timestamp")
        if ts is None:
            continue
        dt = _parse_timestamp(ts)
        if dt is not None and abs((now - dt).total_seconds()) <= window_secs:
            recent_txns.append(t)

    if len(recent_txns) >= 2:
        # Check for distinct countries
        countries = {t.get("country") for t in recent_txns if t.get("country")}
        if len(countries) >= 2:
            return {
                "score_delta": -20.0,
                "flag": True,
                "detail": "compromised device: seen in {} countries within {:.0f} h ({})".format(
                    len(countries), compromise_window_hours, ", ".join(sorted(countries))
                ),
            }

    # Legitimate known device (below threshold but previously seen)
    partial_bonus = round(known_device_bonus * (use_count / known_device_threshold), 2)
    return {
        "score_delta": partial_bonus,
        "flag": False,
        "detail": "recognised device (seen {} times)".format(use_count),
    }


# ---------------------------------------------------------------------------
# Part 4: Payee Network Analysis
# ---------------------------------------------------------------------------

def check_payee_network(
    payee_upi: Optional[str],
    user_transactions: Optional[list[dict]],
    all_recent_payee_counts: Optional[dict] = None,
    first_time_penalty: float = 15.0,
    suspicious_sender_threshold: int = 100,
    suspicious_sender_window_hours: float = 1.0,
) -> dict:
    """Analyse payee behaviour and user→payee relationship.

    Parameters
    ----------
    payee_upi:
        Destination UPI VPA.
    user_transactions:
        This user's historical transactions.
    all_recent_payee_counts:
        Optional dict mapping payee_upi → count of distinct senders in last
        *suspicious_sender_window_hours* hours.  Populated by the caller from
        an aggregated DB query.
    first_time_penalty:
        Trust penalty applied for a new payee (default 15).
    suspicious_sender_threshold:
        Number of distinct senders to this payee within the window that
        triggers a suspicious-payee flag (default 100).
    suspicious_sender_window_hours:
        Window for the suspicious-sender count (informational; the count is
        assumed to cover this window).

    Returns
    -------
    dict with keys ``score_delta``, ``flag``, ``detail``.
    """
    if not payee_upi:
        return {"score_delta": 0.0, "flag": False, "detail": "no payee UPI"}

    # Frequency: how many times has this user sent to this payee?
    frequency = 0
    if user_transactions:
        frequency = sum(1 for t in user_transactions if t.get("payee_upi") == payee_upi)

    # Suspicious payee pattern (many senders in short window)
    if all_recent_payee_counts:
        sender_count = all_recent_payee_counts.get(payee_upi, 0)
        if sender_count >= suspicious_sender_threshold:
            return {
                "score_delta": -20.0,
                "flag": True,
                "detail": "suspicious payee: {} distinct senders in {:.0f} h".format(
                    sender_count, suspicious_sender_window_hours
                ),
            }

    if frequency == 0:
        return {
            "score_delta": -first_time_penalty,
            "flag": True,
            "detail": "first-time payee; -{}pts".format(first_time_penalty),
        }

    # Trust grows with frequency (capped at +10)
    bonus = min(10.0, 2.0 * frequency)
    return {
        "score_delta": round(bonus, 2),
        "flag": False,
        "detail": "familiar payee (sent {} times before)".format(frequency),
    }


# ---------------------------------------------------------------------------
# Part 5: Amount Velocity
# ---------------------------------------------------------------------------

def check_amount_velocity(
    amount: float,
    user_transactions: Optional[list[dict]],
    timestamp: object = None,
    daily_threshold: float = 100000.0,
    high_amount_threshold: float = 20000.0,
    high_risk_multiplier: float = 2.0,
    round_number_window: int = 5,
) -> dict:
    """Analyse amount patterns for velocity fraud signals.

    Parameters
    ----------
    amount:
        Current transaction amount in INR.
    user_transactions:
        Historical transactions, each optionally containing ``amount`` and
        ``timestamp`` fields.
    timestamp:
        Current transaction timestamp (used to filter today's transactions).
    daily_threshold:
        Maximum expected daily spend (default INR 1,00,000).
    high_amount_threshold:
        Amount above which a transaction is considered high-value.
    high_risk_multiplier:
        Risk multiplier applied when high amount + high-risk device combination
        is detected (used only when the caller passes device risk context).
    round_number_window:
        How many recent transactions to inspect for round-number pattern.

    Returns
    -------
    dict with keys ``score_delta``, ``flag``, ``detail``.
    """
    details: list[str] = []
    total_penalty = 0.0
    flagged = False

    current_dt = _parse_timestamp(timestamp)

    # ── Daily amount threshold ─────────────────────────────────────────────
    if user_transactions:
        # Sum amounts for transactions on the same calendar day
        if current_dt is not None:
            today_amounts = []
            for t in user_transactions:
                ts = t.get("timestamp")
                if ts is None:
                    continue
                txn_dt = _parse_timestamp(ts)
                if txn_dt is None:
                    continue
                if txn_dt.date() == current_dt.date():
                    try:
                        today_amounts.append(float(t.get("amount", 0)))
                    except (TypeError, ValueError):
                        pass
            daily_total = sum(today_amounts) + amount
        else:
            # Fallback: sum all provided transactions
            try:
                daily_total = sum(float(t.get("amount", 0)) for t in user_transactions) + amount
            except (TypeError, ValueError):
                daily_total = amount

        if daily_total > daily_threshold:
            excess = daily_total - daily_threshold
            penalty = min(15.0, excess / daily_threshold * 10.0)
            total_penalty += penalty
            flagged = True
            details.append(
                "daily spend {:.0f} exceeds threshold {:.0f}".format(daily_total, daily_threshold)
            )

    # ── Round-number pattern detection ────────────────────────────────────
    if user_transactions:
        recent = user_transactions[-round_number_window:]
        round_amounts = [
            t for t in recent
            if t.get("amount") is not None and float(t.get("amount")) % 1000 == 0
        ]
        if len(round_amounts) >= max(2, round_number_window - 1) and amount % 1000 == 0:
            penalty = 5.0
            total_penalty += penalty
            flagged = True
            details.append(
                "round-number pattern ({}/{} recent transactions are multiples of 1000)".format(
                    len(round_amounts), len(recent)
                )
            )

    # ── High amount flagging ───────────────────────────────────────────────
    if amount >= high_amount_threshold:
        details.append("high transaction amount ({:.0f})".format(amount))

    if not details:
        details.append("normal amount velocity")

    return {
        "score_delta": -round(min(total_penalty, 20.0), 2),
        "flag": flagged,
        "detail": "; ".join(details),
    }


# ---------------------------------------------------------------------------
# Composite enhanced WTS adjustment
# ---------------------------------------------------------------------------

def compute_enhanced_wts_adjustments(
    device_id: Optional[str],
    latitude: Optional[float],
    longitude: Optional[float],
    payee_upi: Optional[str],
    amount: float,
    timestamp: object = None,
    user_transactions: Optional[list[dict]] = None,
    all_recent_payee_counts: Optional[dict] = None,
    home_lat: Optional[float] = None,
    home_lon: Optional[float] = None,
    # Config knobs (pulled from config.py by caller)
    geofence_radius_km: float = 200.0,
    max_speed_kmh: float = 900.0,
    velocity_window_minutes: int = 5,
    velocity_count_threshold: int = 5,
    device_known_threshold: int = 10,
    device_known_bonus: float = 15.0,
    device_compromise_window_hours: float = 1.0,
    first_time_payee_penalty: float = 15.0,
    daily_spend_threshold: float = 100000.0,
) -> dict:
    """Run all Phase 10 enhancement checks and return a composite adjustment.

    Returns
    -------
    dict with keys:
      ``total_delta`` — net score change (sum of all sub-checks)
      ``flags``       — list of flagged check names
      ``components``  — per-check dicts (score_delta, flag, detail)
      ``explanation`` — human-readable summary
    """
    geo = check_geofence(
        latitude, longitude, user_transactions,
        geofence_radius_km=geofence_radius_km,
        home_lat=home_lat, home_lon=home_lon,
    )
    vel = check_velocity(
        latitude, longitude, timestamp, user_transactions,
        max_speed_kmh=max_speed_kmh,
        short_window_minutes=velocity_window_minutes,
        short_window_count=velocity_count_threshold,
    )
    dev = check_device_fingerprint(
        device_id, user_transactions,
        known_device_threshold=device_known_threshold,
        known_device_bonus=device_known_bonus,
        compromise_window_hours=device_compromise_window_hours,
    )
    pay = check_payee_network(
        payee_upi, user_transactions,
        all_recent_payee_counts=all_recent_payee_counts,
        first_time_penalty=first_time_payee_penalty,
    )
    amt = check_amount_velocity(
        amount, user_transactions, timestamp,
        daily_threshold=daily_spend_threshold,
    )

    components = {
        "geofence": geo,
        "velocity": vel,
        "device_fingerprint": dev,
        "payee_network": pay,
        "amount_velocity": amt,
    }

    total_delta = sum(c["score_delta"] for c in components.values())
    flags = [name for name, c in components.items() if c["flag"]]

    explanations = [
        "{}: {}".format(name, c["detail"])
        for name, c in components.items()
        if c["flag"]
    ]
    explanation = "; ".join(explanations) if explanations else "all enhanced checks nominal"

    return {
        "total_delta": round(total_delta, 2),
        "flags": flags,
        "components": components,
        "explanation": explanation,
    }
