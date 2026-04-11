-- migrations/v1_initial.sql
-- SQLite schema for MLBFD Phase 5-9
-- Version: 1  (increment DB_SCHEMA_VERSION in config.py for future migrations)
-- Applied automatically by db.py on first startup.

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- -------------------------------------------------------------------------
-- model_meta: registry of deployed model artifacts
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS model_meta (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    model_name    TEXT    NOT NULL,
    version       TEXT    NOT NULL DEFAULT '1.0',
    artifact_path TEXT,
    auc           REAL,
    recall        REAL,
    trained_at    TEXT,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- -------------------------------------------------------------------------
-- users: minimal user registry (UPI-ID-based)
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        TEXT    NOT NULL UNIQUE,   -- hashed / masked UPI handle
    payer_upi      TEXT,                       -- masked e.g. ab***@ybl
    account_age_days INTEGER DEFAULT 0,
    created_at     TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at     TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- -------------------------------------------------------------------------
-- transactions: raw transaction log
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS transactions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    txn_id          TEXT    NOT NULL UNIQUE,
    user_id         TEXT    NOT NULL,
    payer_upi       TEXT,
    payee_upi       TEXT,
    amount          REAL    NOT NULL,
    txn_type        TEXT    DEFAULT 'TRANSFER',
    hour            INTEGER DEFAULT 12,
    balance_before  REAL    DEFAULT 0,
    balance_after   REAL    DEFAULT 0,
    device_id       TEXT,
    latitude        REAL,
    longitude       REAL,
    is_new_payee    INTEGER DEFAULT 0,
    is_known_device INTEGER DEFAULT 1,
    txn_ts          TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- -------------------------------------------------------------------------
-- transaction_features: engineered feature vector (JSON blob)
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS transaction_features (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    txn_id      TEXT    NOT NULL UNIQUE,
    features    TEXT    NOT NULL,   -- JSON object: feature_name -> value
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (txn_id) REFERENCES transactions(txn_id) ON DELETE CASCADE
);

-- -------------------------------------------------------------------------
-- predictions: fraud-detection output for each transaction
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS predictions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    txn_id          TEXT    NOT NULL UNIQUE,
    user_id         TEXT,
    ubts_score      REAL,
    wts_score       REAL,
    website_score   REAL,
    lstm_prob       REAL,
    ensemble_prob   REAL,
    risk_score      REAL    NOT NULL,
    verdict         TEXT    NOT NULL,
    explanation     TEXT,
    layer_detail    TEXT,   -- JSON breakdown per layer
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (txn_id) REFERENCES transactions(txn_id) ON DELETE CASCADE
);

-- -------------------------------------------------------------------------
-- feedback: user / analyst corrections
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS feedback (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    txn_id          TEXT    NOT NULL,
    predicted       TEXT,
    actual_verdict  TEXT    NOT NULL,   -- 'FRAUD' | 'SAFE'
    notes           TEXT,
    submitted_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (txn_id) REFERENCES transactions(txn_id) ON DELETE CASCADE
);

-- -------------------------------------------------------------------------
-- drift_metrics: periodic model-drift snapshots
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS drift_metrics (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_date   TEXT    NOT NULL DEFAULT (date('now')),
    total_preds     INTEGER DEFAULT 0,
    correct_preds   INTEGER DEFAULT 0,
    accuracy        REAL,
    fraud_rate      REAL,
    notes           TEXT
);

-- -------------------------------------------------------------------------
-- audit_log: immutable append-only event record
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type  TEXT    NOT NULL,   -- e.g. 'predict', 'feedback', 'login'
    txn_id      TEXT,
    user_id     TEXT,
    detail      TEXT,               -- JSON payload
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- -------------------------------------------------------------------------
-- schema_version: tracks applied migration level
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS schema_version (
    version     INTEGER NOT NULL DEFAULT 1,
    applied_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO schema_version (version) VALUES (1);
