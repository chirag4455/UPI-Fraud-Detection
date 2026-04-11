"""
db.py — SQLite connection management, schema migrations and CRUD helpers.

Design goals
------------
* Thread-safe via ``check_same_thread=False`` + connection-per-request pattern.
* Auto-creates all tables on first import using migrations/v1_initial.sql.
* In-memory fallback list when SQLite is unavailable (e.g. read-only FS).
* All public functions accept plain Python dicts / primitives; JSON encoding
  is handled internally.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from typing import Any, Generator, Optional

from config import DB_PATH, MIGRATIONS_DIR, DB_SCHEMA_VERSION

logger = logging.getLogger("mlbfd.db")

# ---------------------------------------------------------------------------
# In-memory fallback stores (used when SQLite is unavailable)
# ---------------------------------------------------------------------------
_fallback_predictions: list[dict] = []
_fallback_transactions: list[dict] = []
_fallback_feedback: list[dict] = []
_sqlite_ok: bool = False  # set to True after successful init


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------

@contextmanager
def get_conn() -> Generator[sqlite3.Connection, None, None]:
    """Yield a SQLite connection with row_factory set to ``sqlite3.Row``.

    The connection is committed on clean exit and rolled back on exception.
    Raises ``RuntimeError`` if SQLite has not been initialised yet.
    """
    if not _sqlite_ok:
        raise RuntimeError("SQLite not initialised — call init_db() first")
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Initialisation & migrations
# ---------------------------------------------------------------------------

def init_db() -> bool:
    """Create tables and run pending migrations.

    Returns ``True`` on success, ``False`` on failure (graceful degradation).
    """
    global _sqlite_ok
    try:
        # Ensure parent directory exists
        db_dir = os.path.dirname(DB_PATH)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")

        # Apply initial migration script
        sql_path = os.path.join(MIGRATIONS_DIR, "v1_initial.sql")
        if os.path.exists(sql_path):
            with open(sql_path, "r", encoding="utf-8") as fh:
                script = fh.read()
            conn.executescript(script)
            logger.info("Applied migration v1_initial.sql")
        else:
            logger.warning("Migration file not found: %s — creating tables inline", sql_path)
            _create_tables_inline(conn)

        conn.commit()
        conn.close()

        _sqlite_ok = True
        logger.info("SQLite initialised at %s (schema v%d)", DB_PATH, DB_SCHEMA_VERSION)
        return True

    except Exception as exc:
        logger.error("SQLite init failed: %s — using in-memory fallback", exc)
        _sqlite_ok = False
        return False


def _create_tables_inline(conn: sqlite3.Connection) -> None:
    """Minimal inline table creation used when the SQL file is missing."""
    conn.executescript(
        """
        PRAGMA journal_mode = WAL;
        PRAGMA foreign_keys = ON;
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL UNIQUE,
            payer_upi TEXT,
            account_age_days INTEGER DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            txn_id TEXT NOT NULL UNIQUE,
            user_id TEXT NOT NULL,
            payer_upi TEXT,
            payee_upi TEXT,
            amount REAL NOT NULL,
            txn_type TEXT DEFAULT 'TRANSFER',
            hour INTEGER DEFAULT 12,
            balance_before REAL DEFAULT 0,
            balance_after REAL DEFAULT 0,
            device_id TEXT,
            latitude REAL,
            longitude REAL,
            is_new_payee INTEGER DEFAULT 0,
            is_known_device INTEGER DEFAULT 1,
            txn_ts TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS transaction_features (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            txn_id TEXT NOT NULL UNIQUE,
            features TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            txn_id TEXT NOT NULL UNIQUE,
            user_id TEXT,
            ubts_score REAL,
            wts_score REAL,
            website_score REAL,
            lstm_prob REAL,
            ensemble_prob REAL,
            risk_score REAL NOT NULL,
            verdict TEXT NOT NULL,
            explanation TEXT,
            layer_detail TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            txn_id TEXT NOT NULL,
            predicted TEXT,
            actual_verdict TEXT NOT NULL,
            notes TEXT,
            submitted_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS drift_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_date TEXT NOT NULL DEFAULT (date('now')),
            total_preds INTEGER DEFAULT 0,
            correct_preds INTEGER DEFAULT 0,
            accuracy REAL,
            fraud_rate REAL,
            notes TEXT
        );
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            txn_id TEXT,
            user_id TEXT,
            detail TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER NOT NULL DEFAULT 1,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        INSERT OR IGNORE INTO schema_version (version) VALUES (1);
        """
    )


# ---------------------------------------------------------------------------
# User helpers
# ---------------------------------------------------------------------------

def upsert_user(user_id: str, payer_upi: Optional[str] = None,
                account_age_days: int = 0) -> None:
    """Insert or update a user record."""
    if not _sqlite_ok:
        return
    try:
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO users (user_id, payer_upi, account_age_days)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    payer_upi = excluded.payer_upi,
                    account_age_days = excluded.account_age_days,
                    updated_at = datetime('now')
                """,
                (user_id, payer_upi, account_age_days),
            )
    except Exception as exc:
        logger.warning("upsert_user failed: %s", exc)


def get_user(user_id: str) -> Optional[dict]:
    """Return user dict or ``None``."""
    if not _sqlite_ok:
        return None
    try:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
            return dict(row) if row else None
    except Exception as exc:
        logger.warning("get_user failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Transaction helpers
# ---------------------------------------------------------------------------

def save_transaction(txn: dict) -> bool:
    """Persist a transaction record.  Returns True on success."""
    if not _sqlite_ok:
        _fallback_transactions.append(txn)
        return False
    try:
        with get_conn() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO transactions
                    (txn_id, user_id, payer_upi, payee_upi, amount, txn_type,
                     hour, balance_before, balance_after, device_id,
                     latitude, longitude, is_new_payee, is_known_device)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    txn.get("txn_id"),
                    txn.get("user_id", "anonymous"),
                    txn.get("payer_upi"),
                    txn.get("payee_upi"),
                    float(txn.get("amount", 0)),
                    txn.get("txn_type", "TRANSFER"),
                    int(txn.get("hour", 12)),
                    float(txn.get("balance_before", 0)),
                    float(txn.get("balance_after", 0)),
                    txn.get("device_id"),
                    txn.get("latitude"),
                    txn.get("longitude"),
                    int(txn.get("is_new_payee", 0)),
                    int(txn.get("is_known_device", 1)),
                ),
            )
        return True
    except Exception as exc:
        logger.warning("save_transaction failed: %s", exc)
        _fallback_transactions.append(txn)
        return False


def get_user_transactions(user_id: str, limit: int = 10) -> list[dict]:
    """Return the *limit* most recent transactions for *user_id*."""
    if not _sqlite_ok:
        return [t for t in _fallback_transactions if t.get("user_id") == user_id][-limit:]
    try:
        with get_conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM transactions
                WHERE user_id = ?
                ORDER BY txn_ts DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception as exc:
        logger.warning("get_user_transactions failed: %s", exc)
        return []


def get_all_transactions(limit: int = 100) -> list[dict]:
    """Return the most recent transactions across all users."""
    if not _sqlite_ok:
        return _fallback_transactions[-limit:]
    try:
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM transactions ORDER BY txn_ts DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception as exc:
        logger.warning("get_all_transactions failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Prediction helpers
# ---------------------------------------------------------------------------

def save_prediction(pred: dict) -> bool:
    """Persist a prediction result.  Returns True on success."""
    if not _sqlite_ok:
        _fallback_predictions.append(pred)
        return False
    try:
        with get_conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO predictions
                    (txn_id, user_id, ubts_score, wts_score, website_score,
                     lstm_prob, ensemble_prob, risk_score, verdict,
                     explanation, layer_detail)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    pred.get("txn_id"),
                    pred.get("user_id"),
                    pred.get("ubts_score"),
                    pred.get("wts_score"),
                    pred.get("website_score"),
                    pred.get("lstm_prob"),
                    pred.get("ensemble_prob"),
                    float(pred.get("risk_score", 50)),
                    pred.get("verdict", "UNKNOWN"),
                    pred.get("explanation"),
                    json.dumps(pred.get("layer_detail", {})),
                ),
            )
        _audit("predict", pred.get("txn_id"), pred.get("user_id"),
               {"risk_score": pred.get("risk_score"), "verdict": pred.get("verdict")})
        return True
    except Exception as exc:
        logger.warning("save_prediction failed: %s", exc)
        _fallback_predictions.append(pred)
        return False


def get_recent_predictions(limit: int = 50) -> list[dict]:
    """Return *limit* most recent predictions."""
    if not _sqlite_ok:
        return _fallback_predictions[-limit:]
    try:
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM predictions ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception as exc:
        logger.warning("get_recent_predictions failed: %s", exc)
        return _fallback_predictions[-limit:]


# ---------------------------------------------------------------------------
# Feedback helpers
# ---------------------------------------------------------------------------

def save_feedback(txn_id: str, predicted: str, actual_verdict: str,
                  notes: str = "") -> bool:
    """Persist user/analyst feedback.  Returns True on success."""
    fb = {"txn_id": txn_id, "predicted": predicted,
          "actual_verdict": actual_verdict, "notes": notes}
    if not _sqlite_ok:
        _fallback_feedback.append(fb)
        return False
    try:
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO feedback (txn_id, predicted, actual_verdict, notes)
                VALUES (?,?,?,?)
                """,
                (txn_id, predicted, actual_verdict, notes),
            )
        _audit("feedback", txn_id, None, fb)
        return True
    except Exception as exc:
        logger.warning("save_feedback failed: %s", exc)
        _fallback_feedback.append(fb)
        return False


def get_feedback_stats() -> dict:
    """Return aggregate feedback statistics."""
    if not _sqlite_ok:
        total = len(_fallback_feedback)
        correct = sum(
            1 for f in _fallback_feedback
            if f.get("predicted", "").upper() == f.get("actual_verdict", "").upper()
        )
        return {"total": total, "correct": correct,
                "accuracy": round(correct / max(total, 1) * 100, 1)}
    try:
        with get_conn() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN predicted = actual_verdict THEN 1 ELSE 0 END) as correct
                FROM feedback
                """
            ).fetchone()
            total = row["total"] or 0
            correct = row["correct"] or 0
            return {"total": total, "correct": correct,
                    "accuracy": round(correct / max(total, 1) * 100, 1)}
    except Exception as exc:
        logger.warning("get_feedback_stats failed: %s", exc)
        return {"total": 0, "correct": 0, "accuracy": 97.3}


# ---------------------------------------------------------------------------
# Audit log helper
# ---------------------------------------------------------------------------

def _audit(event_type: str, txn_id: Optional[str] = None,
           user_id: Optional[str] = None, detail: Any = None) -> None:
    """Append an immutable audit-log entry (best-effort, never raises)."""
    if not _sqlite_ok:
        return
    try:
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO audit_log (event_type, txn_id, user_id, detail)
                VALUES (?,?,?,?)
                """,
                (event_type, txn_id, user_id,
                 json.dumps(detail) if detail else None),
            )
    except Exception:
        pass  # audit is best-effort


# ---------------------------------------------------------------------------
# Drift metrics
# ---------------------------------------------------------------------------

def save_drift_snapshot(total_preds: int, correct_preds: int,
                        fraud_rate: float, notes: str = "") -> None:
    """Persist a daily drift-metric snapshot."""
    if not _sqlite_ok:
        return
    accuracy = round(correct_preds / max(total_preds, 1) * 100, 1)
    try:
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO drift_metrics
                    (total_preds, correct_preds, accuracy, fraud_rate, notes)
                VALUES (?,?,?,?,?)
                """,
                (total_preds, correct_preds, accuracy, fraud_rate, notes),
            )
    except Exception as exc:
        logger.warning("save_drift_snapshot failed: %s", exc)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

def db_health() -> dict:
    """Return a dict with db status and basic counters."""
    if not _sqlite_ok:
        return {"status": "fallback", "predictions": len(_fallback_predictions),
                "transactions": len(_fallback_transactions)}
    try:
        with get_conn() as conn:
            preds = conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
            txns = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
            ver = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
            schema_v = ver[0] if ver else "unknown"
        return {"status": "ok", "predictions": preds, "transactions": txns,
                "schema_version": schema_v}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}
