"""
Configuration for the automated end-to-end model training pipeline.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _dataset_roots_from_env() -> list[Path] | None:
    raw = os.environ.get("MLBFD_DATASET_ROOTS")
    if not raw:
        return None
    parts = [p.strip() for p in raw.replace(";", ",").split(",") if p.strip()]
    return [Path(p) for p in parts] if parts else None


REQUIRED_FEATURES_57: list[str] = [
    "amount",
    "hour",
    "balance_before",
    "balance_after",
    "balance_dest_before",
    "balance_dest_after",
    "balance_change",
    "balance_change_ratio",
    "dest_balance_change",
    "is_cash_out",
    "is_transfer",
    "is_payment",
    "is_debit",
    "is_cash_in",
    "card_id",
    "card_type",
    "card_category",
    "address_code",
    "product_type",
    "has_email",
    "count_c1",
    "count_c2",
    "count_c3",
    "count_c5",
    "count_c6",
    "count_c9",
    "count_c13",
    "count_c14",
    "delta_d1",
    "delta_d2",
    "delta_d3",
    "delta_d4",
    "delta_d10",
    "delta_d15",
    "name_email_sim",
    "customer_age",
    "days_since_request",
    "intended_balance",
    "zip_activity",
    "velocity_6h",
    "velocity_24h",
    "branch_activity",
    "dob_emails",
    "credit_risk",
    "phone_valid",
    "session_length",
    "device_os",
    "Amount_Log",
    "Amount_Scaled",
    "is_new_payee",
    "is_known_device",
    "is_night",
    "is_weekend",
    "is_business_hours",
    "is_round_number",
    "heuristic_risk_score",
    "amount_vs_avg_ratio",
]


@dataclass(slots=True)
class TrainingConfig:
    base_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent)
    model_output_dir: Path = field(
        default_factory=lambda: Path(
            os.environ.get(
                "MLBFD_MODEL_OUTPUT_DIR",
                r"D:\Major Project\MLBFD_Phase4\backend\models",
            )
        )
    )
    log_output_dir: Path = field(
        default_factory=lambda: Path(
            os.environ.get(
                "MLBFD_LOG_OUTPUT_DIR",
                r"D:\Major Project\MLBFD_Phase4\backend\training_logs",
            )
        )
    )
    report_output_dir: Path = field(
        default_factory=lambda: Path(
            os.environ.get(
                "MLBFD_REPORT_OUTPUT_DIR",
                r"D:\Major Project\MLBFD_Phase4\backend\training_reports",
            )
        )
    )
    dataset_roots: list[Path] = field(default_factory=list)
    target_candidates: tuple[str, ...] = (
        "isFraud",
        "is_fraud",
        "fraud",
        "label",
        "target",
        "Class",
    )
    test_size: float = float(os.environ.get("MLBFD_TEST_SIZE", 0.2))
    random_state: int = int(os.environ.get("MLBFD_RANDOM_STATE", 42))
    batch_size: int = int(os.environ.get("MLBFD_BATCH_SIZE", 1024))
    epochs: int = int(os.environ.get("MLBFD_EPOCHS", 10))
    lstm_seq_len: int = int(os.environ.get("MLBFD_LSTM_SEQ_LEN", 10))
    max_rows_per_file: int | None = (
        int(os.environ["MLBFD_MAX_ROWS_PER_FILE"])
        if os.environ.get("MLBFD_MAX_ROWS_PER_FILE")
        else None
    )
    chunk_size: int = int(os.environ.get("MLBFD_CHUNK_SIZE", 200000))
    feature_list: list[str] = field(default_factory=lambda: REQUIRED_FEATURES_57.copy())

    model_params: dict = field(
        default_factory=lambda: {
            "xgboost": {"n_estimators": 250, "max_depth": 6, "learning_rate": 0.08},
            "random_forest": {"n_estimators": 220, "max_depth": 18, "n_jobs": -1},
            "logistic_regression": {"C": 1.0, "max_iter": 1200},
            "isolation_forest": {"n_estimators": 220, "contamination": "auto", "n_jobs": -1},
            "neural_network": {"hidden_units": [128, 64, 32], "dropout": 0.25},
            "lstm": {"units": 48, "dropout": 0.2},
        }
    )

    def __post_init__(self) -> None:
        if not self.dataset_roots:
            env_roots = _dataset_roots_from_env()
            if env_roots:
                self.dataset_roots = env_roots
            else:
                self.dataset_roots = [
                    Path(r"D:\Major Project\Datasets\Tier1"),
                    Path(r"D:\Major Project\Datasets\Tier2"),
                    Path(r"D:\Major Project\MLBFD_Phase1\Data"),
                    Path(r"D:\Major Project\MLBFD_Phase2\Data"),
                ]

    def ensure_output_dirs(self) -> None:
        for p in (self.model_output_dir, self.log_output_dir, self.report_output_dir):
            p.mkdir(parents=True, exist_ok=True)

    def resolve_dataset_roots(self) -> list[Path]:
        roots = list(self.dataset_roots)
        local_fallback = [
            self.base_dir / "datasets" / "Tier1",
            self.base_dir / "datasets" / "Tier2",
            self.base_dir / "data",
        ]
        roots.extend(local_fallback)
        existing: list[Path] = []
        seen: set[str] = set()
        for root in roots:
            key = str(root)
            if key in seen:
                continue
            seen.add(key)
            if root.exists():
                existing.append(root)
        return existing
