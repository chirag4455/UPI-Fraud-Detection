"""
api.py — Flask Blueprint: mobile-ready REST API endpoints (Phase 6).

Endpoints
---------
POST /api/predict       — Full multi-layer fraud detection
POST /api/qr/parse      — Parse a UPI QR code payload
POST /api/feedback      — Submit feedback / correction for a prediction
GET  /api/health        — Service health + DB status
GET  /api/stats         — Aggregate prediction stats

All responses are JSON.  Input is validated minimally; richer validation
can be layered on top with Flask-WTF or Pydantic.

Error format
------------
{
    "success": false,
    "error": "<human-readable message>",
    "code": "<machine-readable error code>"
}
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from functools import wraps
from typing import Any, Callable

from flask import Blueprint, jsonify, request, current_app

import db
import predictor as pred_module
from qr_parser import parse_upi_qr, mask_vpa

logger = logging.getLogger("mlbfd.api")

api_bp = Blueprint("api", __name__, url_prefix="/api")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ok(data: Any, status: int = 200):
    """Return a JSON success response."""
    return jsonify({"success": True, **data}), status


def _err(message: str, code: str = "error", status: int = 400):
    """Return a JSON error response."""
    return jsonify({"success": False, "error": message, "code": code}), status


def _require_json(fn: Callable) -> Callable:
    """Decorator: return 415 if request Content-Type is not application/json."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not request.is_json:
            return _err("Content-Type must be application/json",
                        "unsupported_media_type", 415)
        return fn(*args, **kwargs)
    return wrapper


def _get_str(data: dict, key: str, default: str = "") -> str:
    val = data.get(key, default)
    return str(val).strip() if val is not None else default


def _get_float(data: dict, key: str, default: float = 0.0) -> float:
    try:
        return float(data.get(key, default))
    except (TypeError, ValueError):
        return default


def _get_int(data: dict, key: str, default: int = 0) -> int:
    try:
        return int(data.get(key, default))
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# POST /api/predict
# ---------------------------------------------------------------------------

@api_bp.route("/predict", methods=["POST"])
@_require_json
def api_predict():
    """Run multi-layer fraud detection on a transaction.

    Request body (JSON)
    -------------------
    Required:
        amount          (float)   — transaction amount in INR
    Optional:
        user_id         (str)     — hashed user identifier
        payer_upi       (str)     — sender VPA
        payee_upi       (str)     — recipient VPA
        payee_name      (str)     — recipient display name or URL
        txn_type        (str)     — TRANSFER | PAYMENT | CASH_OUT | DEBIT
        hour            (int)     — hour of day 0-23
        balance_before  (float)
        balance_after   (float)
        is_new_payee    (int)     — 1 = first transaction to this payee
        is_known_device (int)     — 0 = unknown device
        device_id       (str)
        latitude        (float)
        longitude       (float)
        txn_id          (str)     — caller-supplied ID (auto-generated if omitted)

    Response (JSON)
    ---------------
    {
        "success": true,
        "txn_id": "...",
        "risk_score": 73.2,
        "verdict": "SUSPICIOUS",
        "explanation": "...",
        "ubts_score": 62.4,
        "wts_score": 58.1,
        "website_score": 75.0,
        "lstm_prob": 0.68,
        "ensemble_prob": 0.71,
        "layer_detail": { ... },
        "model_votes": { ... },
        "timestamp": "2026-04-11T15:00:00"
    }
    """
    data = request.get_json(silent=True) or {}

    amount = _get_float(data, "amount")
    if amount <= 0:
        return _err("'amount' must be a positive number", "invalid_amount")

    txn_id = _get_str(data, "txn_id") or "TXN-{}".format(uuid.uuid4().hex[:8].upper())

    txn = {
        "txn_id": txn_id,
        "user_id": _get_str(data, "user_id", "anonymous"),
        "payer_upi": _get_str(data, "payer_upi"),
        "payee_upi": _get_str(data, "payee_upi"),
        "payee_name": _get_str(data, "payee_name"),
        "amount": amount,
        "txn_type": _get_str(data, "txn_type", "TRANSFER").upper(),
        "hour": _get_int(data, "hour", datetime.now().hour),
        "balance_before": _get_float(data, "balance_before"),
        "balance_after": _get_float(data, "balance_after"),
        "is_new_payee": _get_int(data, "is_new_payee", 0),
        "is_known_device": _get_int(data, "is_known_device", 1),
        "device_id": _get_str(data, "device_id"),
        "latitude": data.get("latitude"),
        "longitude": data.get("longitude"),
    }

    try:
        result = pred_module.predict(txn)
    except Exception as exc:
        logger.exception("Prediction error for txn_id=%s", txn_id)
        return _err("Prediction failed: {}".format(exc), "prediction_error", 500)

    # Strip internal UI fields; return API-friendly subset
    response = {
        "txn_id": result.get("txn_id"),
        "risk_score": result.get("risk_score"),
        "verdict": result.get("verdict"),
        "explanation": result.get("explanation"),
        "ubts_score": result.get("ubts_score"),
        "wts_score": result.get("wts_score"),
        "website_score": result.get("website_score"),
        "lstm_prob": result.get("lstm_prob"),
        "ensemble_prob": result.get("ensemble_prob"),
        "layer_detail": result.get("layer_detail", {}),
        "model_votes": result.get("model_votes", {}),
        "fraud_votes": result.get("fraud_votes", 0),
        "total_votes": result.get("total_votes", 0),
        "timestamp": datetime.utcnow().isoformat(),
    }
    return _ok(response)


# ---------------------------------------------------------------------------
# POST /api/qr/parse
# ---------------------------------------------------------------------------

@api_bp.route("/qr/parse", methods=["POST"])
@_require_json
def api_qr_parse():
    """Parse a UPI QR code payload.

    Request body (JSON)
    -------------------
        payload (str) — raw QR code string (upi://pay?... or plain VPA)

    Response (JSON)
    ---------------
    {
        "success": true,
        "vpa": "merchant@okaxis",
        "vpa_masked": "me***@okaxis",
        "payee_name": "Merchant Name",
        "amount": 250.0,
        "amount_fixed": true,
        "currency": "INR",
        "txn_ref": "...",
        "note": "...",
        "mcc": "...",
        "info_url": "..."
    }
    """
    data = request.get_json(silent=True) or {}
    payload = _get_str(data, "payload")

    if not payload:
        return _err("'payload' field is required", "missing_payload")

    result = parse_upi_qr(payload)

    if not result["success"]:
        return _err(result.get("error", "QR parse failed"), "qr_parse_error", 422)

    vpa = result.get("vpa")
    return _ok({
        "vpa": vpa,
        "vpa_masked": mask_vpa(vpa),
        "payee_name": result.get("payee_name"),
        "amount": result.get("amount"),
        "amount_fixed": result.get("amount_fixed", False),
        "currency": result.get("currency", "INR"),
        "txn_ref": result.get("txn_ref"),
        "note": result.get("note"),
        "mcc": result.get("mcc"),
        "info_url": result.get("info_url"),
    })


# ---------------------------------------------------------------------------
# POST /api/feedback
# ---------------------------------------------------------------------------

@api_bp.route("/feedback", methods=["POST"])
@_require_json
def api_feedback():
    """Submit user/analyst feedback for a prediction.

    Request body (JSON)
    -------------------
        txn_id          (str) — transaction ID to correct
        actual_verdict  (str) — 'FRAUD' or 'SAFE'
        predicted       (str) — original verdict (optional)
        notes           (str) — free-text notes (optional)

    Response (JSON)
    ---------------
    { "success": true, "message": "Feedback recorded" }
    """
    data = request.get_json(silent=True) or {}

    txn_id = _get_str(data, "txn_id")
    if not txn_id:
        return _err("'txn_id' is required", "missing_txn_id")

    actual_verdict = _get_str(data, "actual_verdict", "").upper()
    if actual_verdict not in ("FRAUD", "SAFE"):
        return _err("'actual_verdict' must be 'FRAUD' or 'SAFE'",
                    "invalid_verdict")

    predicted = _get_str(data, "predicted", "")
    notes = _get_str(data, "notes", "")

    ok = db.save_feedback(txn_id, predicted, actual_verdict, notes)
    return _ok({"message": "Feedback recorded", "persisted": ok})


# ---------------------------------------------------------------------------
# GET /api/health
# ---------------------------------------------------------------------------

@api_bp.route("/health", methods=["GET"])
def api_health():
    """Return service health and DB status.

    Response (JSON)
    ---------------
    {
        "success": true,
        "status": "ok",
        "db": { "status": "ok", "predictions": 42, "transactions": 55 },
        "models_loaded": 4,
        "timestamp": "..."
    }
    """
    db_status = db.db_health()
    pred_module._load_models()
    return _ok({
        "status": "ok",
        "db": db_status,
        "models_loaded": len(pred_module._models),
        "timestamp": datetime.utcnow().isoformat(),
    })


# ---------------------------------------------------------------------------
# GET /api/stats
# ---------------------------------------------------------------------------

@api_bp.route("/stats", methods=["GET"])
def api_stats():
    """Return aggregate prediction statistics.

    Response (JSON)
    ---------------
    {
        "success": true,
        "total_predictions": 120,
        "frauds_detected": 14,
        "fraud_rate": 11.67,
        "feedback": { "total": 5, "correct": 4, "accuracy": 80.0 },
        "timestamp": "..."
    }
    """
    preds = db.get_recent_predictions(limit=1000)
    total = len(preds)
    frauds = sum(
        1 for p in preds
        if (p.get("verdict") or "").upper() not in ("SAFE TRANSACTION", "SAFE")
    )
    fraud_rate = round(frauds / max(total, 1) * 100, 2)
    feedback_stats = db.get_feedback_stats()

    return _ok({
        "total_predictions": total,
        "frauds_detected": frauds,
        "fraud_rate": fraud_rate,
        "feedback": feedback_stats,
        "timestamp": datetime.utcnow().isoformat(),
    })
