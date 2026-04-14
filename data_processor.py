"""Data loading and preprocessing for the MLBFD training pipeline."""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List

from training_config import REQUIRED_API_FEATURES, TrainingConfig

logger = logging.getLogger("mlbfd.data_processor")

TARGET_CANDIDATES = ["is_fraud", "fraud", "label", "class", "target", "isflaggedfraud"]
COLUMN_ALIASES: Dict[str, str] = {
    "oldbalanceorg": "balance_before",
    "newbalanceorig": "balance_after",
    "oldbalancedest": "balance_dest_before",
    "newbalancedest": "balance_dest_after",
    "type": "txn_type",
    "transactionamt": "amount",
}
DEFAULT_NUMERIC = {
    "phone_valid": 1.0,
    "is_usual_location": 1.0,
    "has_email": 1.0,
}


@dataclass
class ProcessedData:
    X_train: object
    X_test: object
    y_train: object
    y_test: object
    feature_names: List[str]
    scaler: object
    dataset_stats: Dict[str, Dict]


def _import_pd_np():
    import numpy as np
    import pandas as pd
    return pd, np


def discover_csv_files(dataset_roots: Iterable[str]) -> List[str]:
    files: List[str] = []
    for root in dataset_roots:
        base = Path(root)
        if base.exists():
            files.extend(sorted(str(p) for p in base.rglob("*.csv")))
    return files


def _sniff_delimiter(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            sample = fh.read(2048)
        return csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except Exception:
        return ","


def _read_csv(path: str, max_rows: int):
    pd, _ = _import_pd_np()
    sep = _sniff_delimiter(path)
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            return pd.read_csv(path, sep=sep, encoding=enc, low_memory=False, nrows=max_rows)
        except Exception:
            pass
    return pd.DataFrame()


def _normalize(df):
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    for old, new in COLUMN_ALIASES.items():
        if old in df.columns and new not in df.columns:
            df.rename(columns={old: new}, inplace=True)
    return df


def _find_target(df):
    lower_map = {c.lower(): c for c in df.columns}
    for candidate in TARGET_CANDIDATES:
        if candidate in lower_map:
            return lower_map[candidate]
    return None


def _engineer(df):
    pd, np = _import_pd_np()
    txn = pd.Series(df.get("txn_type", "TRANSFER")).astype(str).str.upper()
    df["is_transfer"] = (txn == "TRANSFER").astype(float)
    df["is_cash_out"] = (txn == "CASH_OUT").astype(float)
    df["is_payment"] = (txn == "PAYMENT").astype(float)
    df["is_debit"] = (txn == "DEBIT").astype(float)
    df["is_cash_in"] = (txn == "CASH_IN").astype(float)

    if "hour" not in df.columns and "step" in df.columns:
        df["hour"] = pd.to_numeric(df["step"], errors="coerce").fillna(0) % 24
    df["hour"] = pd.to_numeric(df.get("hour", 12), errors="coerce").fillna(12).clip(0, 23)

    amount = pd.to_numeric(df.get("amount", 0), errors="coerce").fillna(0).clip(lower=0)
    bal_before = pd.to_numeric(df.get("balance_before", 0), errors="coerce").fillna(0)
    bal_after = pd.to_numeric(df.get("balance_after", bal_before), errors="coerce").fillna(bal_before)
    df["amount"] = amount
    df["balance_before"] = bal_before
    df["balance_after"] = bal_after
    df["balance_change"] = bal_before - bal_after
    df["balance_change_ratio"] = df["balance_change"] / bal_before.clip(lower=1)
    df["balance_dest_before"] = pd.to_numeric(df.get("balance_dest_before", 0), errors="coerce").fillna(0)
    df["balance_dest_after"] = pd.to_numeric(df.get("balance_dest_after", amount), errors="coerce").fillna(amount)
    df["dest_balance_change"] = df["balance_dest_after"] - df["balance_dest_before"]
    df["Amount_Log"] = np.log1p(amount)
    df["Amount_Scaled"] = (amount / 100000.0).clip(0, 10)
    df["is_new_payee"] = pd.to_numeric(df.get("is_new_payee", 0), errors="coerce").fillna(0).clip(0, 1)
    df["is_known_device"] = pd.to_numeric(df.get("is_known_device", 1), errors="coerce").fillna(1).clip(0, 1)
    df["is_night"] = ((df["hour"] >= 23) | (df["hour"] <= 5)).astype(float)
    df["is_weekend"] = pd.to_numeric(df.get("is_weekend", 0), errors="coerce").fillna(0).clip(0, 1)
    df["is_business_hours"] = ((df["hour"] >= 9) & (df["hour"] <= 17)).astype(float)
    df["is_round_number"] = ((amount % 1000) == 0).astype(float)
    df["day_of_week"] = pd.to_numeric(df.get("day_of_week", 0), errors="coerce").fillna(0).clip(0, 6)
    df["distance_from_home_km"] = pd.to_numeric(df.get("distance_from_home_km", 0), errors="coerce").fillna(0).clip(0, 2000)
    df["is_collect_request"] = pd.to_numeric(df.get("is_collect_request", 0), errors="coerce").fillna(0).clip(0, 1)
    df["is_vpn"] = pd.to_numeric(df.get("is_vpn", 0), errors="coerce").fillna(0).clip(0, 1)
    df["merchant_category"] = pd.to_numeric(df.get("merchant_category", 0), errors="coerce").fillna(0)
    df["payment_app"] = pd.to_numeric(df.get("payment_app", 0), errors="coerce").fillna(0)
    df["payment_type"] = pd.to_numeric(df.get("payment_type", 0), errors="coerce").fillna(0)
    df["state"] = pd.to_numeric(df.get("state", 0), errors="coerce").fillna(0)
    df["transactions_last_24h"] = pd.to_numeric(df.get("transactions_last_24h", 0), errors="coerce").fillna(0)
    df["transactions_last_hour"] = pd.to_numeric(df.get("transactions_last_hour", 0), errors="coerce").fillna(0)
    df["vpa_age_days"] = pd.to_numeric(df.get("vpa_age_days", 0), errors="coerce").fillna(0)
    df["device_location_risk"] = (1 - df["is_known_device"]).clip(0, 1)
    df["velocity_risk"] = ((df["is_night"] == 1) & (amount > 10000)).astype(float)
    df["new_payee_night"] = ((df["is_new_payee"] == 1) & (df["is_night"] == 1)).astype(float)
    df["high_amount_new_device"] = ((amount > 20000) & (df["is_known_device"] == 0)).astype(float)
    df["young_vpa_high_amount"] = ((df["vpa_age_days"] < 30) & (amount > 10000)).astype(float)
    df["heuristic_risk_score"] = (
        (amount > 50000).astype(float) * 2
        + (amount > 20000).astype(float)
        + df["is_night"] * 2
        + df["is_new_payee"]
        + (1 - df["is_known_device"]) * 2
        + (df["is_transfer"] + df["is_cash_out"]) * 0.5
    )
    for col in REQUIRED_API_FEATURES:
        base_default = DEFAULT_NUMERIC.get(col, 0.0)
        if col not in df.columns:
            df[col] = base_default
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(base_default)
    return df


def _clean(df):
    pd, np = _import_pd_np()
    before = len(df)
    df = df.drop_duplicates().copy()
    removed = before - len(df)
    num_cols = df.select_dtypes(include=["number"]).columns
    if len(num_cols):
        df[num_cols] = df[num_cols].replace([np.inf, -np.inf], np.nan)
        df[num_cols] = df[num_cols].fillna(df[num_cols].median(numeric_only=True))
        q1 = df[num_cols].quantile(0.25)
        q3 = df[num_cols].quantile(0.75)
        iqr = q3 - q1
        df[num_cols] = df[num_cols].clip(lower=q1 - 3 * iqr, upper=q3 + 3 * iqr, axis=1)
    return df, removed


def load_and_preprocess_data(config: TrainingConfig) -> ProcessedData:
    pd, _ = _import_pd_np()
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler

    roots = config.discover_existing_dataset_roots()
    csv_files = discover_csv_files(roots)
    if not csv_files:
        raise FileNotFoundError("No CSV datasets found in configured dataset roots.")

    frames = []
    stats: Dict[str, Dict] = {}
    for path in csv_files:
        df = _read_csv(path, max_rows=config.max_rows_per_file)
        if df.empty:
            continue
        df = _normalize(df)
        target_col = _find_target(df)
        if target_col is None:
            flagged = pd.to_numeric(df.get("isFlaggedFraud", 0), errors="coerce").fillna(0)
            fraud = pd.to_numeric(df.get("isFraud", 0), errors="coerce").fillna(0)
            amount = pd.to_numeric(df.get("amount", 0), errors="coerce").fillna(0)
            df["is_fraud"] = ((flagged > 0) | (fraud > 0) | (amount > 200000)).astype(int)
        elif target_col != "is_fraud":
            df.rename(columns={target_col: "is_fraud"}, inplace=True)
        df = _engineer(df)
        df, removed = _clean(df)
        df = df[REQUIRED_API_FEATURES + ["is_fraud"]]
        frames.append(df)
        null_pct = float(df.isnull().sum().sum()) / max(1, (df.shape[0] * df.shape[1])) * 100
        stats[path] = {"rows": int(df.shape[0]), "columns": int(df.shape[1]), "null_pct": round(null_pct, 4), "duplicates_removed": int(removed)}

    if not frames:
        raise ValueError("CSV files found, but none could be processed for training.")

    combined = pd.concat(frames, ignore_index=True)
    combined, _ = _clean(combined)
    X = combined[REQUIRED_API_FEATURES].astype("float32")
    y = combined["is_fraud"].astype(int)
    stratify = y if y.nunique() > 1 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=config.test_size, random_state=config.random_state, stratify=stratify
    )
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    return ProcessedData(
        X_train=X_train_scaled,
        X_test=X_test_scaled,
        y_train=y_train.values,
        y_test=y_test.values,
        feature_names=list(REQUIRED_API_FEATURES),
        scaler=scaler,
        dataset_stats=stats,
    )
