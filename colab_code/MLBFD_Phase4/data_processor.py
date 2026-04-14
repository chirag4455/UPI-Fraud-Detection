"""
Data loading and preprocessing for automated all-dataset training.
"""

from __future__ import annotations

import logging
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler, StandardScaler

from training_config import TrainingConfig

logger = logging.getLogger("mlbfd.data_processor")


def _safe_num(series: pd.Series | float | int, index: pd.Index, default: float = 0.0) -> pd.Series:
    if isinstance(series, pd.Series):
        return pd.to_numeric(series, errors="coerce").fillna(default)
    return pd.Series(default if series is None else series, index=index, dtype=float).fillna(default)


class DataProcessor:
    def __init__(self, config: TrainingConfig) -> None:
        self.config = config

    def _discover_csvs(self) -> list[Path]:
        files: list[Path] = []
        for root in self.config.resolve_dataset_roots():
            files.extend(sorted(root.rglob("*.csv")))
        unique: list[Path] = []
        seen: set[str] = set()
        for f in files:
            key = str(f.resolve())
            if key not in seen:
                seen.add(key)
                unique.append(f)
        return unique

    def _read_csv(self, path: Path) -> pd.DataFrame:
        logger.info("Loading dataset: %s", path)
        if self.config.max_rows_per_file:
            return pd.read_csv(path, low_memory=False, nrows=self.config.max_rows_per_file)

        if path.stat().st_size > 400 * 1024 * 1024:
            chunks: list[pd.DataFrame] = []
            for chunk in pd.read_csv(path, low_memory=False, chunksize=self.config.chunk_size):
                chunks.append(chunk)
                if self.config.max_rows_per_file and sum(len(c) for c in chunks) >= self.config.max_rows_per_file:
                    break
            return pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()
        return pd.read_csv(path, low_memory=False)

    def _find_target(self, df: pd.DataFrame) -> pd.Series:
        for col in self.config.target_candidates:
            if col in df.columns:
                return _safe_num(df[col], df.index).clip(0, 1).astype(int)
        return pd.Series(np.zeros(len(df), dtype=int), index=df.index)

    def _engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        out = pd.DataFrame(index=df.index)
        amount = _safe_num(df.get("amount", df.get("Amount", df.get("TransactionAmt", 0.0))), df.index)
        hour = _safe_num(df.get("hour", df.get("Hour", df.get("step", 12))), df.index).clip(0, 23)
        bal_before = _safe_num(df.get("balance_before", df.get("oldbalanceOrg", 0.0)), df.index)
        bal_after = _safe_num(df.get("balance_after", df.get("newbalanceOrig", 0.0)), df.index)
        bal_dest_before = _safe_num(df.get("balance_dest_before", df.get("oldbalanceDest", 0.0)), df.index)
        bal_dest_after = _safe_num(df.get("balance_dest_after", df.get("newbalanceDest", 0.0)), df.index)

        txn_type = df.get("txn_type", df.get("type", "TRANSFER")).astype(str).str.upper()
        out["amount"] = amount
        out["hour"] = hour
        out["balance_before"] = bal_before
        out["balance_after"] = bal_after
        out["balance_dest_before"] = bal_dest_before
        out["balance_dest_after"] = bal_dest_after
        out["balance_change"] = bal_before - bal_after
        out["balance_change_ratio"] = (out["balance_change"] / bal_before.replace(0, 1)).astype(float)
        out["dest_balance_change"] = bal_dest_after - bal_dest_before
        out["is_cash_out"] = (txn_type == "CASH_OUT").astype(float)
        out["is_transfer"] = (txn_type == "TRANSFER").astype(float)
        out["is_payment"] = (txn_type == "PAYMENT").astype(float)
        out["is_debit"] = (txn_type == "DEBIT").astype(float)
        out["is_cash_in"] = (txn_type == "CASH_IN").astype(float)

        for src, dst in [
            ("card_id", "card_id"),
            ("card_type", "card_type"),
            ("card_category", "card_category"),
            ("addr1", "address_code"),
            ("ProductCD", "product_type"),
            ("has_email", "has_email"),
            ("C1", "count_c1"),
            ("C2", "count_c2"),
            ("C3", "count_c3"),
            ("C5", "count_c5"),
            ("C6", "count_c6"),
            ("C9", "count_c9"),
            ("C13", "count_c13"),
            ("C14", "count_c14"),
            ("D1", "delta_d1"),
            ("D2", "delta_d2"),
            ("D3", "delta_d3"),
            ("D4", "delta_d4"),
            ("D10", "delta_d10"),
            ("D15", "delta_d15"),
            ("name_email_sim", "name_email_sim"),
            ("customer_age", "customer_age"),
            ("days_since_request", "days_since_request"),
            ("intended_balance", "intended_balance"),
            ("zip_activity", "zip_activity"),
            ("velocity_6h", "velocity_6h"),
            ("velocity_24h", "velocity_24h"),
            ("branch_activity", "branch_activity"),
            ("dob_emails", "dob_emails"),
            ("credit_risk", "credit_risk"),
            ("phone_valid", "phone_valid"),
            ("session_length", "session_length"),
            ("device_os", "device_os"),
            ("amount_vs_avg_ratio", "amount_vs_avg_ratio"),
        ]:
            out[dst] = _safe_num(df.get(src, 0.0), df.index)

        out["Amount_Log"] = np.log1p(out["amount"].clip(lower=0))
        out["Amount_Scaled"] = np.minimum(out["amount"] / 100000.0, 10.0)
        out["is_new_payee"] = _safe_num(df.get("is_new_payee", 0.0), df.index).clip(0, 1)
        out["is_known_device"] = _safe_num(df.get("is_known_device", 1.0), df.index).clip(0, 1)
        out["is_night"] = ((out["hour"] >= 23) | (out["hour"] <= 5)).astype(float)
        out["is_weekend"] = _safe_num(df.get("is_weekend", 0.0), df.index).clip(0, 1)
        out["is_business_hours"] = ((out["hour"] >= 9) & (out["hour"] <= 17)).astype(float)
        out["is_round_number"] = ((out["amount"] % 1000) == 0).astype(float)
        out["heuristic_risk_score"] = (
            (out["amount"] > 50000).astype(int) * 2
            + (out["amount"] > 20000).astype(int)
            + out["is_night"].astype(int) * 2
            + out["is_new_payee"].astype(int)
            + (1 - out["is_known_device"]).astype(int) * 2
            + out["is_transfer"].astype(int)
            + out["is_cash_out"].astype(int)
        ).astype(float)

        for col in self.config.feature_list:
            if col not in out.columns:
                out[col] = 0.0
        out = out[self.config.feature_list]
        out = out.replace([np.inf, -np.inf], np.nan).fillna(0.0)
        return out

    def process(self) -> dict:
        datasets = self._discover_csvs()
        if not datasets:
            raise FileNotFoundError("No CSV datasets found in configured dataset roots.")

        frames: list[pd.DataFrame] = []
        targets: list[pd.Series] = []
        used_files: list[str] = []
        for path in datasets:
            try:
                df = self._read_csv(path)
            except Exception as exc:  # pragma: no cover - defensive path
                logger.warning("Skipping unreadable dataset %s: %s", path, exc)
                continue
            if df.empty:
                continue
            frames.append(self._engineer_features(df))
            targets.append(self._find_target(df))
            used_files.append(str(path))

        if not frames:
            raise RuntimeError("All discovered CSV datasets failed to load.")

        X = pd.concat(frames, ignore_index=True)
        y = pd.concat(targets, ignore_index=True).astype(int)
        merged = X.copy()
        merged["target"] = y.values
        merged = merged.drop_duplicates().reset_index(drop=True)
        y = merged.pop("target").astype(int)
        X = merged

        stratify = y if y.nunique() > 1 else None
        X_train, X_test, y_train, y_test = train_test_split(
            X.values.astype(np.float32),
            y.values.astype(int),
            test_size=self.config.test_size,
            random_state=self.config.random_state,
            stratify=stratify,
        )

        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        lstm_scaler = MinMaxScaler()
        X_train_lstm = lstm_scaler.fit_transform(X_train_scaled)
        X_test_lstm = lstm_scaler.transform(X_test_scaled)

        self.config.ensure_output_dirs()
        with open(self.config.model_output_dir / "mlbfd_mega_scaler.pkl", "wb") as f:
            pickle.dump(scaler, f)
        with open(self.config.model_output_dir / "mlbfd_mega_lstm_scaler.pkl", "wb") as f:
            pickle.dump(lstm_scaler, f)
        with open(self.config.model_output_dir / "mlbfd_mega_feature_names.pkl", "wb") as f:
            pickle.dump(self.config.feature_list, f)

        return {
            "X_train": X_train_scaled,
            "X_test": X_test_scaled,
            "X_train_lstm": X_train_lstm,
            "X_test_lstm": X_test_lstm,
            "y_train": y_train,
            "y_test": y_test,
            "feature_names": self.config.feature_list,
            "datasets_used": used_files,
            "row_count": int(len(X)),
            "fraud_count": int(y.sum()),
        }
