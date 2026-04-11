"""
ubts.py — User Baseline Trust Score (UBTS) layer.

The UBTS layer answers: "Is this user behaving as they normally do?"

It computes a trust score (0–100, higher = more trustworthy) by comparing the
current transaction against the user's historical baseline stored in SQLite.
When no history is available the module returns a neutral mid-range score so
that the absence of data does not unfairly flag new users as fraudsters.

Score components
----------------
1. Account-age bonus          — older accounts earn trust
2. Transaction-frequency      — active users earn trust
3. Amount deviation           — large deviation from mean lowers trust
4. Hour-of-day consistency    — unusual hours lower trust
5. New-payee penalty          — first transaction to a payee lowers trust
"""

from __future__ import annotations

import logging
import math
from typing import Optional

logger = logging.getLogger("mlbfd.ubts")

# ---------------------------------------------------------------------------
# Tuneable constants
# ---------------------------------------------------------------------------
_AGE_BONUS_MAX: float = 15.0      # max points from account age
_AGE_BONUS_DAYS: int = 365        # days to reach max age bonus
_FREQ_BONUS_MAX: float = 15.0     # max points from transaction frequency
_FREQ_THRESHOLD: int = 50         # txns needed for max freq bonus
_AMOUNT_PENALTY_MAX: float = 25.0 # max penalty for extreme amount deviation
_HOUR_PENALTY_MAX: float = 20.0   # max penalty for unusual hour
_NEW_PAYEE_PENALTY: float = 10.0  # fixed penalty for new payee
_BASE_SCORE: float = 55.0         # neutral base (= moderate trust)


def compute_ubts(
    user_id: str,
    amount: float,
    hour: int,
    is_new_payee: bool,
    account_age_days: int = 0,
    user_transactions: Optional[list[dict]] = None,
) -> dict:
    """Compute the User Baseline Trust Score for one transaction.

    Parameters
    ----------
    user_id:
        Unique user identifier (used for logging only here; lookup is done
        by the caller before passing *user_transactions*).
    amount:
        Transaction amount in INR.
    hour:
        Hour-of-day (0–23) of the transaction.
    is_new_payee:
        True if the payee has never been transacted with before.
    account_age_days:
        Days since the account was created (0 = unknown / new).
    user_transactions:
        List of recent transaction dicts from SQLite (may be empty).

    Returns
    -------
    dict with keys:
        score (float 0–100), components (dict), explanation (str)
    """
    score: float = _BASE_SCORE
    components: dict = {}

    # ── 1. Account-age bonus ─────────────────────────────────────────────
    age_bonus = min(account_age_days / _AGE_BONUS_DAYS, 1.0) * _AGE_BONUS_MAX
    components["account_age_bonus"] = round(age_bonus, 2)
    score += age_bonus

    # ── 2. Transaction-frequency bonus ───────────────────────────────────
    n_txns = len(user_transactions) if user_transactions else 0
    freq_bonus = min(n_txns / _FREQ_THRESHOLD, 1.0) * _FREQ_BONUS_MAX
    components["frequency_bonus"] = round(freq_bonus, 2)
    score += freq_bonus

    # ── 3. Amount deviation penalty ──────────────────────────────────────
    amount_penalty = 0.0
    if user_transactions:
        amounts = [t.get("amount", 0) for t in user_transactions if t.get("amount")]
        if amounts:
            mean_amt = sum(amounts) / len(amounts)
            # Use coefficient of variation relative to mean
            if mean_amt > 0:
                deviation_ratio = abs(amount - mean_amt) / mean_amt
                # Sigmoid-shaped penalty: 0 deviation → 0 penalty, 5× deviation → ~max
                amount_penalty = _AMOUNT_PENALTY_MAX * (
                    1 - math.exp(-deviation_ratio / 2.0)
                )
    components["amount_deviation_penalty"] = -round(amount_penalty, 2)
    score -= amount_penalty

    # ── 4. Hour-of-day consistency penalty ───────────────────────────────
    hour_penalty = 0.0
    if user_transactions:
        hours = [t.get("hour", 12) for t in user_transactions if t.get("hour") is not None]
        if hours:
            mean_hour = sum(hours) / len(hours)
            # Circular distance (0–12 scale)
            diff = abs(hour - mean_hour)
            circular_diff = min(diff, 24 - diff)
            hour_penalty = _HOUR_PENALTY_MAX * min(circular_diff / 12.0, 1.0)
    else:
        # No history: apply flat penalty for night-time transactions
        if hour >= 23 or hour <= 5:
            hour_penalty = _HOUR_PENALTY_MAX * 0.6
    components["hour_penalty"] = -round(hour_penalty, 2)
    score -= hour_penalty

    # ── 5. New-payee penalty ─────────────────────────────────────────────
    if is_new_payee:
        components["new_payee_penalty"] = -_NEW_PAYEE_PENALTY
        score -= _NEW_PAYEE_PENALTY
    else:
        components["new_payee_penalty"] = 0.0

    # ── Clamp ─────────────────────────────────────────────────────────────
    score = max(0.0, min(100.0, score))

    # ── Explanation ───────────────────────────────────────────────────────
    remarks = []
    if age_bonus >= _AGE_BONUS_MAX * 0.7:
        remarks.append("established account")
    if freq_bonus >= _FREQ_BONUS_MAX * 0.7:
        remarks.append("regular transaction history")
    if amount_penalty >= _AMOUNT_PENALTY_MAX * 0.5:
        remarks.append("amount deviates significantly from baseline")
    if hour_penalty >= _HOUR_PENALTY_MAX * 0.5:
        remarks.append("unusual transaction hour for this user")
    if is_new_payee:
        remarks.append("first transaction to this payee")
    explanation = "; ".join(remarks) if remarks else "within normal behaviour"

    logger.debug("UBTS user=%s score=%.1f components=%s", user_id, score, components)
    return {
        "score": round(score, 2),
        "components": components,
        "explanation": explanation,
        "n_history_txns": n_txns,
    }
