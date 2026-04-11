"""
config.py — Configuration management for MLBFD Phase 5-9.

Centralises all paths, thresholds, schema version and environment-overridable
settings so that every other module imports from here rather than hard-coding
values.  Environment variables take precedence over compiled-in defaults.
"""

import os
import logging

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("mlbfd.config")

# ---------------------------------------------------------------------------
# Directory layout
# ---------------------------------------------------------------------------
BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR: str = os.path.join(BASE_DIR, "models")
DATA_DIR: str = os.path.join(BASE_DIR, "data")
MIGRATIONS_DIR: str = os.path.join(BASE_DIR, "migrations")

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DB_PATH: str = os.environ.get(
    "MLBFD_DB_PATH",
    os.path.join(BASE_DIR, "mlbfd.sqlite3"),
)
DB_SCHEMA_VERSION: int = 1

# ---------------------------------------------------------------------------
# Model artifact file names
# ---------------------------------------------------------------------------
MODEL_FILES: dict = {
    "XGBoost": "mlbfd_mega_xgboost_model.pkl",
    "Random Forest": "mlbfd_mega_random_forest_model.pkl",
    "Logistic Regression": "mlbfd_mega_logistic_regression_model.pkl",
    "Isolation Forest": "mlbfd_mega_isolation_forest_model.pkl",
}
SCALER_FILE: str = "mlbfd_mega_scaler.pkl"
LSTM_SCALER_FILE: str = "mlbfd_mega_lstm_scaler.pkl"
FEATURE_NAMES_FILE: str = "mlbfd_mega_feature_names.pkl"
NN_MODEL_FILE: str = "mlbfd_mega_neural_network_model.keras"
LSTM_MODEL_FILE: str = "mlbfd_mega_lstm_model.keras"

# ---------------------------------------------------------------------------
# Fraud-detection thresholds (0-100 risk scale)
# ---------------------------------------------------------------------------
THRESHOLD_CRITICAL: int = int(os.environ.get("MLBFD_THRESHOLD_CRITICAL", 80))
THRESHOLD_WARNING: int = int(os.environ.get("MLBFD_THRESHOLD_WARNING", 50))

# ---------------------------------------------------------------------------
# Layer weights for final risk aggregation
# Each weight is a float; they are normalised at runtime.
# ---------------------------------------------------------------------------
LAYER_WEIGHTS: dict = {
    "ubts": float(os.environ.get("MLBFD_W_UBTS", 0.20)),
    "wts": float(os.environ.get("MLBFD_W_WTS", 0.20)),
    "website_trust": float(os.environ.get("MLBFD_W_WEBSITE", 0.10)),
    "lstm": float(os.environ.get("MLBFD_W_LSTM", 0.25)),
    "ensemble": float(os.environ.get("MLBFD_W_ENSEMBLE", 0.25)),
}

# ---------------------------------------------------------------------------
# LSTM sequence settings
# ---------------------------------------------------------------------------
LSTM_SEQ_LEN: int = int(os.environ.get("MLBFD_LSTM_SEQ_LEN", 10))

# ---------------------------------------------------------------------------
# Security / Flask
# ---------------------------------------------------------------------------
SECRET_KEY: str = os.environ.get("MLBFD_SECRET_KEY", "mlbfd-secret-key-2026")
API_RATE_LIMIT: int = int(os.environ.get("MLBFD_API_RATE_LIMIT", 100))  # req/min

# ---------------------------------------------------------------------------
# Website trust scoring heuristics
# ---------------------------------------------------------------------------
KNOWN_BRANDS: list = [
    "sbi", "icici", "hdfc", "axis", "kotak", "paytm", "phonepe", "gpay",
    "googlepay", "bhim", "npci", "upi", "rbi", "yesbank", "pnb", "canara",
    "unionbank", "boi", "bankofbaroda", "idfc", "federal", "indusind",
]
SUSPICIOUS_TLDS: list = [".xyz", ".top", ".club", ".online", ".site", ".tk",
                         ".ml", ".ga", ".cf", ".gq"]
SUSPICIOUS_KEYWORDS: list = [
    "secure", "login", "verify", "update", "kyc", "otp", "reward",
    "cashback", "prize", "lottery", "offer", "winner", "free",
    "account", "bank", "payment", "support", "help", "service",
]

# ---------------------------------------------------------------------------
# Phase 10: Advanced WTS enhancement thresholds
# ---------------------------------------------------------------------------

# --- Geo-Fencing ---
WTS_GEOFENCE_RADIUS_KM: float = float(
    os.environ.get("MLBFD_WTS_GEOFENCE_RADIUS_KM", 200.0)
)

# --- Velocity Analysis ---
WTS_MAX_SPEED_KMH: float = float(
    os.environ.get("MLBFD_WTS_MAX_SPEED_KMH", 900.0)
)
WTS_VELOCITY_WINDOW_MINUTES: int = int(
    os.environ.get("MLBFD_WTS_VELOCITY_WINDOW_MINUTES", 5)
)
WTS_VELOCITY_COUNT_THRESHOLD: int = int(
    os.environ.get("MLBFD_WTS_VELOCITY_COUNT_THRESHOLD", 5)
)

# --- Device Fingerprinting ---
WTS_DEVICE_KNOWN_THRESHOLD: int = int(
    os.environ.get("MLBFD_WTS_DEVICE_KNOWN_THRESHOLD", 10)
)
WTS_DEVICE_KNOWN_BONUS: float = float(
    os.environ.get("MLBFD_WTS_DEVICE_KNOWN_BONUS", 15.0)
)
WTS_DEVICE_COMPROMISE_WINDOW_HOURS: float = float(
    os.environ.get("MLBFD_WTS_DEVICE_COMPROMISE_WINDOW_HOURS", 1.0)
)

# --- Payee Network ---
WTS_FIRST_TIME_PAYEE_PENALTY: float = float(
    os.environ.get("MLBFD_WTS_FIRST_TIME_PAYEE_PENALTY", 15.0)
)
WTS_SUSPICIOUS_SENDER_THRESHOLD: int = int(
    os.environ.get("MLBFD_WTS_SUSPICIOUS_SENDER_THRESHOLD", 100)
)

# --- Amount Velocity ---
WTS_DAILY_SPEND_THRESHOLD: float = float(
    os.environ.get("MLBFD_WTS_DAILY_SPEND_THRESHOLD", 100000.0)
)

logger.debug("Config loaded. DB_PATH=%s  THRESHOLD_CRITICAL=%d", DB_PATH, THRESHOLD_CRITICAL)
