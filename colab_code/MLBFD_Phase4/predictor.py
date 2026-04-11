"""
predictor.py — Multi-layer fraud-detection orchestrator (Phase 6).

Runs all detection layers in order, aggregates scores into a final risk_score
(0–100), generates a human-readable explanation and stores the result to
SQLite via db.py.

Layer pipeline
--------------
1. UBTS  — user baseline trust score
2. WTS   — wallet trust score
3. Website Trust — URL / payee-name phishing check
4. LSTM sequence inference — temporal pattern probability
5. Ensemble ML models      — XGBoost, RF, NN, LR, IF probabilities
6. Final aggregation       — weighted average → risk_score → verdict

The orchestrator is intentionally stateless: all persistent state is read from
(and written to) SQLite through db.py.  It gracefully degrades if any
individual layer raises an exception.
"""

from __future__ import annotations

import logging
import os
import pickle
from datetime import datetime
from typing import Any, Optional

import numpy as np
import pandas as pd

import db
from config import (
    LAYER_WEIGHTS,
    MODEL_DIR,
    MODEL_FILES,
    SCALER_FILE,
    FEATURE_NAMES_FILE,
    NN_MODEL_FILE,
    LSTM_MODEL_FILE,
    THRESHOLD_CRITICAL,
    THRESHOLD_WARNING,
)
from ubts import compute_ubts
from wts import compute_wts
from website_trust import score_url, score_payee_name
from lstm_sequence import build_lstm_sequence

logger = logging.getLogger("mlbfd.predictor")

# ---------------------------------------------------------------------------
# Module-level model cache (loaded once on import)
# ---------------------------------------------------------------------------
_models: dict = {}
_scaler = None
_feature_names: list = []
_models_loaded = False


def _load_models() -> None:
    """Load ML model artifacts from disk (idempotent)."""
    global _models, _scaler, _feature_names, _models_loaded
    if _models_loaded:
        return

    # Sklearn / XGBoost models
    for name, fname in MODEL_FILES.items():
        fpath = os.path.join(MODEL_DIR, fname)
        if os.path.exists(fpath):
            try:
                with open(fpath, "rb") as fh:
                    _models[name] = pickle.load(fh)
                logger.info("Loaded model: %s", name)
            except Exception as exc:
                logger.warning("Failed to load %s: %s", name, exc)

    # Keras models
    try:
        import tensorflow as tf  # type: ignore

        nn_path = os.path.join(MODEL_DIR, NN_MODEL_FILE)
        if os.path.exists(nn_path):
            _models["Neural Network"] = tf.keras.models.load_model(nn_path)
            logger.info("Loaded model: Neural Network")

        lstm_path = os.path.join(MODEL_DIR, LSTM_MODEL_FILE)
        if os.path.exists(lstm_path):
            _models["LSTM"] = tf.keras.models.load_model(lstm_path)
            logger.info("Loaded model: LSTM")
    except Exception as exc:
        logger.warning("Keras models not loaded: %s", exc)

    # Scaler & feature names
    scaler_path = os.path.join(MODEL_DIR, SCALER_FILE)
    if os.path.exists(scaler_path):
        with open(scaler_path, "rb") as fh:
            _scaler = pickle.load(fh)

    fn_path = os.path.join(MODEL_DIR, FEATURE_NAMES_FILE)
    if os.path.exists(fn_path):
        with open(fn_path, "rb") as fh:
            _feature_names = pickle.load(fh)

    _models_loaded = True
    logger.info("Predictor: %d models loaded, %d features", len(_models), len(_feature_names))


# ---------------------------------------------------------------------------
# Feature vector builder (reuses logic from app.py for backward compat)
# ---------------------------------------------------------------------------

def _build_feature_df(txn: dict) -> pd.DataFrame:
    """Build a feature DataFrame from a transaction dict."""
    features: dict[str, float] = {f: 0.0 for f in _feature_names}
    amount = float(txn.get("amount", 0))
    hour = int(txn.get("hour", 12))
    bal_before = float(txn.get("balance_before", 0))
    bal_after = float(txn.get("balance_after", 0))
    txn_type = (txn.get("txn_type") or "TRANSFER").upper()
    is_new_payee = int(txn.get("is_new_payee", 0))
    is_known_device = int(txn.get("is_known_device", 1))

    features.update(
        amount=amount,
        hour=hour,
        balance_before=bal_before,
        balance_after=bal_after,
        balance_change=bal_before - bal_after,
        balance_change_ratio=(bal_before - bal_after) / max(bal_before, 1),
        balance_dest_before=0,
        balance_dest_after=amount,
        dest_balance_change=amount,
        is_transfer=1.0 if txn_type == "TRANSFER" else 0.0,
        is_cash_out=1.0 if txn_type == "CASH_OUT" else 0.0,
        is_payment=1.0 if txn_type == "PAYMENT" else 0.0,
        is_debit=1.0 if txn_type == "DEBIT" else 0.0,
        is_cash_in=1.0 if txn_type == "CASH_IN" else 0.0,
        Amount_Log=float(np.log1p(amount)),
        Amount_Scaled=min(amount / 100000, 10.0),
        is_new_payee=float(is_new_payee),
        is_known_device=float(is_known_device),
        is_night=1.0 if (hour >= 23 or hour <= 5) else 0.0,
        is_weekend=0.0,
        is_business_hours=1.0 if (9 <= hour <= 17) else 0.0,
        is_round_number=1.0 if amount % 1000 == 0 else 0.0,
        day_of_week=float(datetime.now().weekday()),
    )
    is_night = features.get("is_night", 0)
    features["velocity_risk"] = 1.0 if (is_night and amount > 10000) else 0.0
    features["new_payee_night"] = 1.0 if (is_new_payee and is_night) else 0.0
    features["high_amount_new_device"] = (
        1.0 if (amount > 20000 and not is_known_device) else 0.0
    )
    features["young_vpa_high_amount"] = 0.0
    features["device_location_risk"] = 0.0 if is_known_device else 1.0

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
    features["heuristic_risk_score"] = float(risk)

    return pd.DataFrame([features])[_feature_names]


# ---------------------------------------------------------------------------
# Ensemble prediction
# ---------------------------------------------------------------------------

def _run_ensemble(feature_df: pd.DataFrame) -> dict:
    """Run all ensemble models and return per-model results + aggregate prob."""
    if _scaler is None or not _models:
        return {"probabilities": [0.5], "votes": {}, "ensemble_prob": 0.5}

    scaled = _scaler.transform(feature_df)
    votes: dict[str, str] = {}
    probs: list[float] = []

    for name, model in _models.items():
        if name == "LSTM":
            continue  # LSTM handled separately via lstm_sequence
        try:
            if name == "Isolation Forest":
                pred = model.predict(scaled)
                is_fraud = 1 if pred[0] == -1 else 0
                prob = 0.8 if is_fraud else 0.2
            elif name == "Neural Network":
                prob = float(model.predict(scaled, verbose=0)[0][0])
                is_fraud = 1 if prob > 0.5 else 0
            else:
                is_fraud = int(model.predict(scaled)[0])
                prob = (
                    float(model.predict_proba(scaled)[0][1])
                    if hasattr(model, "predict_proba")
                    else (0.8 if is_fraud else 0.2)
                )
            votes[name] = "FRAUD" if is_fraud else "SAFE"
            probs.append(prob)
        except Exception as exc:
            logger.warning("Model %s inference error: %s", name, exc)
            votes[name] = "ERROR"

    ensemble_prob = float(np.mean(probs)) if probs else 0.5
    return {"probabilities": probs, "votes": votes, "ensemble_prob": ensemble_prob}


# ---------------------------------------------------------------------------
# LSTM inference via lstm_sequence module
# ---------------------------------------------------------------------------

def _run_lstm(current_txn: dict, history: list[dict]) -> float:
    """Return LSTM fraud probability (0–1) using real sequence inference."""
    lstm_model = _models.get("LSTM")
    if lstm_model is None:
        return 0.5  # neutral fallback

    try:
        seq_array, seq_len = build_lstm_sequence(current_txn, history)
        prob = float(lstm_model.predict(seq_array, verbose=0)[0][0])
        logger.debug("LSTM inference prob=%.4f seq_len=%d", prob, seq_len)
        return prob
    except Exception as exc:
        logger.warning("LSTM inference failed: %s", exc)
        return 0.5


# ---------------------------------------------------------------------------
# Score aggregation
# ---------------------------------------------------------------------------

def _aggregate(
    ubts_score: float,
    wts_score: float,
    website_score: float,
    lstm_prob: float,
    ensemble_prob: float,
) -> float:
    """Aggregate layer scores into a single risk_score (0–100).

    UBTS, WTS and website_score are *trust* scores (high = safe).
    lstm_prob and ensemble_prob are *fraud* probabilities (high = risky).
    We convert trust scores to risk contributions before weighting.
    """
    w = LAYER_WEIGHTS
    total_w = sum(w.values())

    risk_from_ubts = (100.0 - ubts_score) * w["ubts"]
    risk_from_wts = (100.0 - wts_score) * w["wts"]
    risk_from_website = (100.0 - website_score) * w["website_trust"]
    risk_from_lstm = lstm_prob * 100.0 * w["lstm"]
    risk_from_ensemble = ensemble_prob * 100.0 * w["ensemble"]

    raw = (risk_from_ubts + risk_from_wts + risk_from_website
           + risk_from_lstm + risk_from_ensemble) / total_w
    return max(0.0, min(100.0, raw))


def _build_explanation(
    txn: dict,
    ubts: dict,
    wts: dict,
    website: dict,
    risk_score: float,
) -> tuple[str, list[dict]]:
    """Generate human-readable explanation + SHAP-style factor list."""
    reasons: list[str] = []
    factors: list[dict] = []

    amount = float(txn.get("amount", 0))
    hour = int(txn.get("hour", 12))
    is_new_payee = bool(int(txn.get("is_new_payee", 0)))
    is_known_device = bool(int(txn.get("is_known_device", 1)))

    if amount > 50000:
        reasons.append("Very high amount (INR {:,.0f})".format(amount))
        factors.append({"feature": "Amount", "impact": 0.35, "width": 35})
    elif amount > 20000:
        reasons.append("High amount (INR {:,.0f})".format(amount))
        factors.append({"feature": "Amount", "impact": 0.20, "width": 20})
    else:
        factors.append({"feature": "Amount", "impact": -0.10, "width": 10})

    if hour >= 23 or hour <= 5:
        reasons.append("Unusual hour ({}:00)".format(hour))
        factors.append({"feature": "Hour (Night)", "impact": 0.28, "width": 28})
    else:
        factors.append({"feature": "Hour", "impact": -0.05, "width": 5})

    if is_new_payee:
        reasons.append("New payee — first transaction")
        factors.append({"feature": "New Payee", "impact": 0.15, "width": 15})

    if not is_known_device:
        reasons.append("Unknown/new device")
        factors.append({"feature": "Unknown Device", "impact": 0.22, "width": 22})

    if ubts.get("score", 100) < 40:
        reasons.append("Low user trust score ({:.0f})".format(ubts.get("score", 0)))
        factors.append({"feature": "UBTS (low)", "impact": 0.18, "width": 18})

    if wts.get("score", 100) < 40:
        reasons.append("Low wallet trust score ({:.0f})".format(wts.get("score", 0)))
        factors.append({"feature": "WTS (low)", "impact": 0.15, "width": 15})

    if website.get("is_suspicious"):
        reasons.append("Suspicious URL/payee: {}".format(website.get("explanation", "")))
        factors.append({"feature": "Suspicious URL", "impact": 0.30, "width": 30})

    factors.sort(key=lambda x: abs(x["impact"]), reverse=True)
    explanation = " | ".join(reasons) if reasons else "No significant risk factors."
    return explanation, factors[:6]


# ---------------------------------------------------------------------------
# Main prediction entry-point
# ---------------------------------------------------------------------------

def predict(txn: dict) -> dict:
    """Run all detection layers and return a complete prediction result.

    Parameters
    ----------
    txn:
        Dict with transaction fields:
        ``user_id``, ``payer_upi``, ``payee_upi``, ``amount``, ``hour``,
        ``balance_before``, ``balance_after``, ``txn_type``, ``txn_id``,
        ``is_new_payee``, ``is_known_device``, ``device_id``,
        ``latitude``, ``longitude``, ``payee_name`` (optional URL/name).

    Returns
    -------
    dict with full prediction metadata.
    """
    _load_models()

    user_id: str = txn.get("user_id", "anonymous")
    txn_id: str = txn.get("txn_id", "TXN{:06d}".format(
        len(db._fallback_predictions) + 1))

    # ── Fetch user history from SQLite ────────────────────────────────────
    history = db.get_user_transactions(user_id, limit=10)
    user_record = db.get_user(user_id)
    account_age_days = (user_record or {}).get("account_age_days", 0)

    # ── Layer 1: UBTS ─────────────────────────────────────────────────────
    try:
        ubts_result = compute_ubts(
            user_id=user_id,
            amount=float(txn.get("amount", 0)),
            hour=int(txn.get("hour", 12)),
            is_new_payee=bool(int(txn.get("is_new_payee", 0))),
            account_age_days=account_age_days,
            user_transactions=history,
        )
    except Exception as exc:
        logger.warning("UBTS error: %s", exc)
        ubts_result = {"score": 50.0, "explanation": "error", "components": {}}

    # ── Layer 2: WTS ──────────────────────────────────────────────────────
    try:
        wts_result = compute_wts(
            user_id=user_id,
            device_id=txn.get("device_id"),
            is_known_device=bool(int(txn.get("is_known_device", 1))),
            latitude=txn.get("latitude"),
            longitude=txn.get("longitude"),
            payee_upi=txn.get("payee_upi"),
            amount=float(txn.get("amount", 0)),
            user_transactions=history,
        )
    except Exception as exc:
        logger.warning("WTS error: %s", exc)
        wts_result = {"score": 50.0, "explanation": "error", "components": {}}

    # ── Layer 3: Website Trust ────────────────────────────────────────────
    try:
        url_or_name = txn.get("payee_name") or txn.get("info_url") or ""
        if url_or_name.startswith("http"):
            website_result = score_url(url_or_name)
        else:
            website_result = score_payee_name(url_or_name)
    except Exception as exc:
        logger.warning("WebsiteTrust error: %s", exc)
        website_result = {"score": 75.0, "is_suspicious": False, "explanation": "error"}

    # ── Layer 4: LSTM sequence inference ─────────────────────────────────
    try:
        lstm_prob = _run_lstm(txn, history)
    except Exception as exc:
        logger.warning("LSTM error: %s", exc)
        lstm_prob = 0.5

    # ── Layer 5: Ensemble models ──────────────────────────────────────────
    try:
        feature_df = _build_feature_df(txn)
        ensemble_result = _run_ensemble(feature_df)
    except Exception as exc:
        logger.warning("Ensemble error: %s", exc)
        ensemble_result = {"votes": {}, "ensemble_prob": 0.5}

    ensemble_prob: float = ensemble_result.get("ensemble_prob", 0.5)

    # ── Layer 6: Aggregation ──────────────────────────────────────────────
    ubts_score = ubts_result.get("score", 50.0)
    wts_score = wts_result.get("score", 50.0)
    website_score = website_result.get("score", 75.0)

    risk_score = _aggregate(
        ubts_score, wts_score, website_score, lstm_prob, ensemble_prob
    )

    if risk_score >= THRESHOLD_CRITICAL:
        verdict = "FRAUD DETECTED"
        icon = "!!!"
        css_class = "fraud"
        color = "#e74c3c"
    elif risk_score >= THRESHOLD_WARNING:
        verdict = "SUSPICIOUS"
        icon = "!!"
        css_class = "warning"
        color = "#f39c12"
    else:
        verdict = "SAFE TRANSACTION"
        icon = "OK"
        css_class = "safe"
        color = "#2ecc71"

    explanation, shap_reasons = _build_explanation(
        txn, ubts_result, wts_result, website_result, risk_score
    )

    fraud_votes = sum(1 for v in ensemble_result.get("votes", {}).values() if v == "FRAUD")
    total_votes = sum(1 for v in ensemble_result.get("votes", {}).values() if v != "ERROR")

    layer_detail: dict[str, Any] = {
        "ubts": {"score": ubts_score, "components": ubts_result.get("components", {}),
                 "explanation": ubts_result.get("explanation", "")},
        "wts": {"score": wts_score, "components": wts_result.get("components", {}),
                "explanation": wts_result.get("explanation", "")},
        "website_trust": {"score": website_score,
                          "is_suspicious": website_result.get("is_suspicious", False),
                          "explanation": website_result.get("explanation", "")},
        "lstm": {"prob": lstm_prob, "seq_len": 10},
        "ensemble": {"prob": ensemble_prob, "votes": ensemble_result.get("votes", {})},
    }

    prediction: dict = {
        "txn_id": txn_id,
        "user_id": user_id,
        "prediction": 1 if risk_score >= THRESHOLD_WARNING else 0,
        "risk_score": round(risk_score, 1),
        "verdict": verdict,
        "icon": icon,
        "class": css_class,
        "color": color,
        "ubts_score": round(ubts_score, 2),
        "wts_score": round(wts_score, 2),
        "website_score": round(website_score, 2),
        "lstm_prob": round(lstm_prob, 4),
        "ensemble_prob": round(ensemble_prob, 4),
        "model_votes": ensemble_result.get("votes", {}),
        "fraud_votes": fraud_votes,
        "total_votes": total_votes,
        "explanation": explanation,
        "shap_reasons": shap_reasons,
        "layer_detail": layer_detail,
    }

    # ── Persist to SQLite ─────────────────────────────────────────────────
    db.upsert_user(user_id, txn.get("payer_upi"), account_age_days)
    db.save_transaction({**txn, "txn_id": txn_id, "user_id": user_id})
    db.save_prediction(prediction)

    return prediction
