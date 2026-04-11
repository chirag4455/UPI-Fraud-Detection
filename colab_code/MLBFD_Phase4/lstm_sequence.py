"""
lstm_sequence.py — Build LSTM input sequences from transaction history.

Fetches the last N transactions from SQLite (or falls back to a zero-padded
single-step sequence), builds a full 108-feature vector for each step using
the same feature set the model was trained on, scales with
``mlbfd_mega_lstm_scaler.pkl``, and returns a (1, seq_len, n_features) numpy
array ready to feed into the LSTM model.
"""

from __future__ import annotations

import logging
import os
import pickle
from typing import Optional, Tuple

import numpy as np

from config import MODEL_DIR, LSTM_SCALER_FILE, FEATURE_NAMES_FILE, LSTM_SEQ_LEN

logger = logging.getLogger("mlbfd.lstm_sequence")

# ---------------------------------------------------------------------------
# Lazy-load scaler and feature names
# ---------------------------------------------------------------------------
_lstm_scaler = None
_feature_names: list = []


def _load_artifacts() -> None:
    """Load (and cache) the LSTM scaler and feature names from disk."""
    global _lstm_scaler, _feature_names

    if not _feature_names:
        fn_path = os.path.join(MODEL_DIR, FEATURE_NAMES_FILE)
        if os.path.exists(fn_path):
            with open(fn_path, "rb") as fh:
                _feature_names = pickle.load(fh)
            logger.info("Feature names loaded: %d features", len(_feature_names))
        else:
            logger.warning("Feature names file not found at %s", fn_path)

    if _lstm_scaler is None:
        path = os.path.join(MODEL_DIR, LSTM_SCALER_FILE)
        if os.path.exists(path):
            with open(path, "rb") as fh:
                _lstm_scaler = pickle.load(fh)
            logger.info("LSTM scaler loaded from %s", path)
        else:
            logger.warning("LSTM scaler not found at %s — will use raw values", path)


# ---------------------------------------------------------------------------
# Feature vector builder for a single transaction dict
# ---------------------------------------------------------------------------

def _txn_to_feature_vector(txn: dict) -> np.ndarray:
    """Convert a transaction dict to a full feature array matching training schema."""
    _load_artifacts()
    feature_names = _feature_names

    features: dict = {f: 0.0 for f in feature_names}

    amount = float(txn.get("amount", 0))
    hour = int(txn.get("hour", 12))
    bal_before = float(txn.get("balance_before", 0))
    bal_after = float(txn.get("balance_after", 0))
    bal_change = bal_before - bal_after
    bal_change_ratio = bal_change / max(bal_before, 1.0)
    txn_type = (txn.get("txn_type") or "TRANSFER").upper()
    is_new_payee = int(txn.get("is_new_payee", 0))
    is_known_device = int(txn.get("is_known_device", 1))
    is_night = int(hour >= 23 or hour <= 5)

    risk = 0
    if amount > 50000:
        risk += 2
    if amount > 20000:
        risk += 1
    if is_night:
        risk += 2
    if is_new_payee:
        risk += 1
    if not is_known_device:
        risk += 2
    if txn_type in ("TRANSFER", "CASH_OUT"):
        risk += 1

    updates = {
        "amount": amount,
        "hour": hour,
        "balance_before": bal_before,
        "balance_after": bal_after,
        "balance_change": bal_change,
        "balance_change_ratio": bal_change_ratio,
        "balance_dest_after": amount,
        "dest_balance_change": amount,
        "is_transfer": 1.0 if txn_type == "TRANSFER" else 0.0,
        "is_cash_out": 1.0 if txn_type == "CASH_OUT" else 0.0,
        "is_payment": 1.0 if txn_type == "PAYMENT" else 0.0,
        "is_debit": 1.0 if txn_type == "DEBIT" else 0.0,
        "is_cash_in": 1.0 if txn_type == "CASH_IN" else 0.0,
        "Amount_Log": float(np.log1p(amount)),
        "Amount_Scaled": min(amount / 100000.0, 10.0),
        "is_new_payee": float(is_new_payee),
        "is_known_device": float(is_known_device),
        "is_night": float(is_night),
        "is_weekend": 0.0,
        "is_business_hours": 1.0 if (9 <= hour <= 17) else 0.0,
        "is_round_number": 1.0 if amount % 1000 == 0 else 0.0,
        "velocity_risk": 1.0 if (is_night and amount > 10000) else 0.0,
        "new_payee_night": 1.0 if (is_new_payee and is_night) else 0.0,
        "high_amount_new_device": 1.0 if (amount > 20000 and not is_known_device) else 0.0,
        "device_location_risk": 0.0 if is_known_device else 1.0,
        "heuristic_risk_score": float(risk),
        "young_vpa_high_amount": 0.0,
    }
    for k, v in updates.items():
        if k in features:
            features[k] = v

    if feature_names:
        return np.array([features.get(f, 0.0) for f in feature_names], dtype=np.float32)
    return np.zeros(15, dtype=np.float32)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_lstm_sequence(
    current_txn: dict,
    history: Optional[list[dict]] = None,
    seq_len: int = LSTM_SEQ_LEN,
) -> Tuple[np.ndarray, int]:
    """Build a scaled LSTM input tensor for one inference call.

    Parameters
    ----------
    current_txn:
        Dict of the current (pending) transaction features.
    history:
        List of past transaction dicts (most-recent first, from SQLite).
        May be ``None`` or empty.
    seq_len:
        Desired sequence length (default ``LSTM_SEQ_LEN`` from config).

    Returns
    -------
    Tuple of:
        * ``np.ndarray`` of shape ``(1, seq_len, n_features)``
        * ``int`` — actual number of real history steps (rest are zero-padded)
    """
    _load_artifacts()
    history = history or []

    n_features = len(_feature_names) if _feature_names else 15

    # Build a list of feature vectors (history + current), newest last
    past = history[: seq_len - 1][::-1]  # reverse so oldest first
    steps = [_txn_to_feature_vector(t) for t in past]
    steps.append(_txn_to_feature_vector(current_txn))

    actual_len = len(steps)

    # Zero-pad at the beginning to reach seq_len
    while len(steps) < seq_len:
        steps.insert(0, np.zeros(n_features, dtype=np.float32))

    seq = np.stack(steps[-seq_len:], axis=0)  # (seq_len, n_features)

    # Scale each time-step independently
    if _lstm_scaler is not None:
        try:
            seq = _lstm_scaler.transform(seq)
        except Exception as exc:
            logger.warning("LSTM scaler transform failed: %s — using raw values", exc)

    result = seq[np.newaxis, :, :]  # (1, seq_len, n_features)
    logger.debug(
        "LSTM sequence built: shape=%s actual_steps=%d", result.shape, actual_len
    )
    return result.astype(np.float32), actual_len
