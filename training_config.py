"""Configuration for the automated MLBFD training pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import os


REQUIRED_API_FEATURES: List[str] = [
    "amount", "hour", "balance_before", "balance_after", "balance_change",
    "balance_change_ratio", "balance_dest_before", "balance_dest_after",
    "dest_balance_change", "is_transfer", "is_cash_out", "is_payment", "is_debit",
    "is_cash_in", "Amount_Log", "Amount_Scaled", "is_new_payee", "is_known_device",
    "is_night", "is_weekend", "is_business_hours", "is_round_number", "day_of_week",
    "distance_from_home_km", "is_collect_request", "is_vpn", "merchant_category",
    "payment_app", "payment_type", "state", "transactions_last_24h",
    "transactions_last_hour", "vpa_age_days", "device_location_risk", "velocity_risk",
    "new_payee_night", "high_amount_new_device", "young_vpa_high_amount",
    "heuristic_risk_score", "amount_vs_avg_ratio", "velocity_6h", "velocity_24h",
    "phone_valid", "session_length", "device_os", "name_email_sim", "customer_age",
    "days_since_request", "zip_activity", "branch_activity", "credit_risk",
    "is_usual_location", "has_email", "card_type", "card_category", "address_code",
    "product_type",
]
NUMERIC_EPSILON: float = 1e-9


def _default_dataset_roots() -> List[str]:
    env_roots = os.environ.get("MLBFD_DATASET_ROOTS", "").strip()
    if env_roots:
        return [p.strip() for p in env_roots.split(",") if p.strip()]
    return [
        r"D:\Major Project\Datasets",
        r"D:\Major Project\MLBFD_Phase1\Data",
        r"D:\Major Project\MLBFD_Phase2\Data",
        r"D:\Major Project\MLBFD",
    ]


@dataclass
class TrainingConfig:
    dataset_roots: List[str] = field(default_factory=_default_dataset_roots)
    output_models_dir: str = "colab_code/MLBFD_Phase4/backend/models"
    output_logs_dir: str = "colab_code/MLBFD_Phase4/backend/training_logs"
    output_reports_dir: str = "colab_code/MLBFD_Phase4/backend/training_reports"
    random_state: int = 42
    test_size: float = 0.2
    max_rows_per_file: int = 300_000
    # Default heuristic cutoff (amount in INR) for datasets without explicit fraud labels.
    # Tuned to flag unusually large UPI-like transactions while remaining conservative.
    fraud_heuristic_amount_threshold: float = 200_000.0
    cv_n_jobs: int = -1
    heuristic_score_weights: Dict[str, float] = field(
        default_factory=lambda: {
            "amt_gt_50000": 2.0,
            "amt_gt_20000": 1.0,
            "night_multiplier": 2.0,
            "new_payee": 1.0,
            "unknown_device_multiplier": 2.0,
            "transfer_or_cash_out": 0.5,
        }
    )
    model_hyperparameters: Dict[str, Dict] = field(
        default_factory=lambda: {
            "xgboost": {"n_estimators": 250, "max_depth": 7, "learning_rate": 0.08, "subsample": 0.85, "colsample_bytree": 0.8, "eval_metric": "logloss"},
            "random_forest": {"n_estimators": 250, "max_depth": 20, "class_weight": "balanced"},
            "logistic_regression": {"C": 1.0, "max_iter": 1000, "class_weight": "balanced"},
            "isolation_forest": {"n_estimators": 200, "contamination": 0.1, "max_features": 0.8},
            "neural_network": {"epochs": 20, "batch_size": 1024},
            "lstm": {"epochs": 12, "batch_size": 1024},
        }
    )

    @property
    def timestamp(self) -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    @property
    def model_prefix(self) -> str:
        return "mlbfd_mega_"

    def ensure_output_dirs(self) -> None:
        for path in [self.output_models_dir, self.output_logs_dir, self.output_reports_dir]:
            Path(path).mkdir(parents=True, exist_ok=True)

    def discover_existing_dataset_roots(self) -> List[str]:
        local_fallbacks = [
            "datasets",
            "colab_code/MLBFD_Phase4/datasets",
            "colab_code/MLBFD_Phase1/Data",
            "colab_code/MLBFD_Phase2/Data",
        ]
        candidates = self.dataset_roots + [str(Path(os.getcwd()) / p) for p in local_fallbacks]
        seen = set()
        existing: List[str] = []
        for p in candidates:
            rp = str(Path(p).resolve())
            if Path(p).exists() and rp not in seen:
                seen.add(rp)
                existing.append(rp)
        return existing
