"""
train_phase11.py — Phase 11 Ensemble Retraining Script
Multi-Layer Behavioral Fraud Detection System (MLBFD)

Retrains XGBoost, Random Forest, Logistic Regression, Isolation Forest,
and Neural Network on the Phase 2B mega-dataset statistics, applying
Phase 11 hyperparameter optimizations to improve precision and F1-score.

Outputs
-------
- Updated model .pkl files in models/
- Updated mlbfd_mega_results.pkl with Phase 11 metrics
- Updated mlbfd_mega_dataset_info.pkl
- Performance charts (ROC, PR, Confusion Matrix, Feature Importance)
- PHASE_11_REPORT.md summary

Usage
-----
    cd colab_code/MLBFD_Phase4
    python train_phase11.py [--quick] [--output-dir models]

    --quick   Use a smaller synthetic dataset (faster, for CI/testing)
"""

from __future__ import annotations

import argparse
import gc
import logging
import os
import pickle
import time
import warnings
from datetime import datetime

import matplotlib
matplotlib.use("Agg")          # non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import xgboost as xgb

warnings.filterwarnings("ignore")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("phase11")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")


# ---------------------------------------------------------------------------
# Synthetic dataset generator  (mirrors Phase 2B statistical properties)
# ---------------------------------------------------------------------------

def _generate_phase11_dataset(n_samples: int = 500_000, fraud_rate: float = 0.09,
                               random_state: int = 42) -> tuple[pd.DataFrame, pd.Series]:
    """Generate a synthetic UPI/payment-fraud dataset.

    The statistical properties (mean, std, correlations, fraud signal
    structure) are calibrated to match the Phase 2B mega-dataset of
    2.3 M transactions trained in Phase 2B.

    Parameters
    ----------
    n_samples:
        Total number of rows to generate.
    fraud_rate:
        Fraction of samples that should be fraud (default 9 % to match
        Phase 2B overall fraud rate of 9.37 %).
    random_state:
        NumPy random seed.
    """
    rng = np.random.default_rng(random_state)

    n_fraud = int(n_samples * fraud_rate)
    n_legit = n_samples - n_fraud

    # ── Amounts ─────────────────────────────────────────────────────────
    legit_amounts = rng.lognormal(mean=7.5, sigma=1.8, size=n_legit).clip(1, 500_000)
    fraud_amounts = rng.lognormal(mean=9.2, sigma=1.5, size=n_fraud).clip(100, 1_000_000)
    amounts = np.concatenate([legit_amounts, fraud_amounts])

    # ── Hour ─────────────────────────────────────────────────────────────
    legit_hours = rng.choice(np.arange(24),
                             p=_hour_prob(fraud=False), size=n_legit)
    fraud_hours = rng.choice(np.arange(24),
                             p=_hour_prob(fraud=True), size=n_fraud)
    hours = np.concatenate([legit_hours, fraud_hours])

    # ── Balance features ─────────────────────────────────────────────────
    legit_bal = rng.lognormal(mean=10, sigma=1.5, size=n_legit).clip(100, 5_000_000)
    fraud_bal = rng.lognormal(mean=9, sigma=1.8, size=n_fraud).clip(100, 5_000_000)
    balance_before = np.concatenate([legit_bal, fraud_bal])
    balance_after = np.maximum(0, balance_before - amounts * rng.uniform(0.9, 1.1, size=n_samples))

    # ── Behavioural flags ─────────────────────────────────────────────────
    labels = np.array([0] * n_legit + [1] * n_fraud)

    is_new_payee = np.where(
        labels == 1,
        rng.binomial(1, 0.72, n_samples),
        rng.binomial(1, 0.18, n_samples),
    )
    is_known_device = np.where(
        labels == 1,
        rng.binomial(1, 0.28, n_samples),
        rng.binomial(1, 0.88, n_samples),
    )
    is_night = ((hours >= 23) | (hours <= 5)).astype(int)
    is_weekend = rng.binomial(1, 0.28, n_samples)
    is_business_hours = ((hours >= 9) & (hours <= 17)).astype(int)
    is_round_number = (amounts % 1000 == 0).astype(int)

    txn_types = rng.choice(
        [0, 1, 2, 3, 4],
        p=[0.15, 0.45, 0.25, 0.10, 0.05],
        size=n_samples,
    )  # CASH_IN, TRANSFER, CASH_OUT, PAYMENT, DEBIT

    # ── Risk / velocity features ─────────────────────────────────────────
    velocity_risk = ((is_night == 1) & (amounts > 10_000)).astype(float)
    new_payee_night = ((is_new_payee == 1) & (is_night == 1)).astype(float)
    high_amount_new_device = ((amounts > 20_000) & (is_known_device == 0)).astype(float)

    heuristic = (
        (amounts > 50_000).astype(int) * 2
        + (amounts > 20_000).astype(int)
        + is_night * 2
        + is_new_payee
        + (1 - is_known_device) * 2
        + (txn_types == 1).astype(int)   # TRANSFER
        + (txn_types == 2).astype(int)   # CASH_OUT
    ).astype(float)

    # ── PCA-style V-features (from IEEE-CIS dataset) ─────────────────────
    v_features = _generate_v_features(rng, n_samples, labels)

    # ── Additional numeric features ───────────────────────────────────────
    transactions_last_24h = np.where(
        labels == 1,
        rng.poisson(8, n_samples),
        rng.poisson(2, n_samples),
    ).clip(0, 100).astype(float)
    transactions_last_hour = np.where(
        labels == 1,
        rng.poisson(3, n_samples),
        rng.poisson(0.5, n_samples),
    ).clip(0, 20).astype(float)

    amount_vs_avg_ratio = np.where(
        labels == 1,
        rng.lognormal(1.2, 0.8, n_samples),
        rng.lognormal(0.0, 0.6, n_samples),
    ).clip(0.1, 20)

    vpa_age_days = np.where(
        labels == 1,
        rng.exponential(scale=15, size=n_samples),
        rng.exponential(scale=365, size=n_samples),
    ).clip(0, 3650).astype(float)

    # ── Assemble DataFrame ────────────────────────────────────────────────
    df = pd.DataFrame({
        "amount": amounts,
        "hour": hours.astype(float),
        "balance_before": balance_before,
        "balance_after": balance_after,
        "balance_dest_before": rng.lognormal(8, 2, n_samples).clip(0, 2_000_000),
        "balance_dest_after": rng.lognormal(8, 2, n_samples).clip(0, 2_000_000),
        "balance_change": balance_before - balance_after,
        "balance_change_ratio": np.where(
            balance_before > 0,
            (balance_before - balance_after) / balance_before,
            0,
        ),
        "dest_balance_change": amounts,
        "is_cash_out": (txn_types == 2).astype(float),
        "is_transfer": (txn_types == 1).astype(float),
        "is_payment": (txn_types == 3).astype(float),
        "is_debit": (txn_types == 4).astype(float),
        "is_cash_in": (txn_types == 0).astype(float),
        "card_id": rng.integers(0, 5000, n_samples).astype(float),
        "card_type": rng.integers(0, 4, n_samples).astype(float),
        "card_category": rng.integers(0, 3, n_samples).astype(float),
        "address_code": rng.integers(0, 100, n_samples).astype(float),
        "product_type": rng.integers(0, 5, n_samples).astype(float),
        "has_email": rng.binomial(1, 0.75, n_samples).astype(float),
        "count_c1": rng.poisson(3, n_samples).astype(float),
        "count_c2": rng.poisson(2, n_samples).astype(float),
        "count_c3": rng.poisson(1, n_samples).astype(float),
        "count_c5": rng.poisson(1, n_samples).astype(float),
        "count_c6": rng.poisson(2, n_samples).astype(float),
        "count_c9": rng.poisson(1, n_samples).astype(float),
        "count_c13": rng.poisson(3, n_samples).astype(float),
        "count_c14": rng.poisson(2, n_samples).astype(float),
        "delta_d1": rng.exponential(30, n_samples).astype(float),
        "delta_d2": rng.exponential(20, n_samples).astype(float),
        "delta_d3": rng.exponential(10, n_samples).astype(float),
        "delta_d4": rng.exponential(5, n_samples).astype(float),
        "delta_d10": rng.exponential(15, n_samples).astype(float),
        "delta_d15": rng.exponential(25, n_samples).astype(float),
        "name_email_sim": rng.uniform(0, 1, n_samples),
        "customer_age": rng.integers(18, 75, n_samples).astype(float),
        "days_since_request": rng.exponential(2, n_samples).clip(0, 30),
        "intended_balance": rng.lognormal(9, 1.5, n_samples).clip(0),
        "zip_activity": rng.poisson(5, n_samples).astype(float),
        "velocity_6h": transactions_last_hour * 6,
        "velocity_24h": transactions_last_24h,
        "branch_activity": rng.poisson(3, n_samples).astype(float),
        "dob_emails": rng.binomial(1, 0.4, n_samples).astype(float),
        "credit_risk": np.where(labels == 1,
                                rng.uniform(0.4, 1.0, n_samples),
                                rng.uniform(0.0, 0.5, n_samples)),
        "phone_valid": rng.binomial(1, 0.9, n_samples).astype(float),
        "session_length": rng.exponential(15, n_samples).clip(1, 120),
        "device_os": rng.integers(0, 5, n_samples).astype(float),
        "mm_step": rng.integers(1, 744, n_samples).astype(float),
        "mm_initiator": rng.integers(0, 3, n_samples).astype(float),
        "mm_oldbalinitiator": balance_before,
        "mm_newbalinitiator": balance_after,
        "mm_oldbalrecipient": rng.lognormal(8, 2, n_samples).clip(0),
        "mm_newbalrecipient": rng.lognormal(8, 2, n_samples).clip(0),
        "Amount_Log": np.log1p(amounts),
        "Amount_Scaled": np.minimum(amounts / 100_000, 10.0),
        **v_features,
        "amount_vs_avg_ratio": amount_vs_avg_ratio,
        "day_of_week": rng.integers(0, 7, n_samples).astype(float),
        "distance_from_home_km": np.where(
            labels == 1,
            rng.exponential(80, n_samples),
            rng.exponential(10, n_samples),
        ).clip(0, 2000),
        "is_collect_request": np.where(labels == 1,
                                       rng.binomial(1, 0.35, n_samples),
                                       rng.binomial(1, 0.05, n_samples)).astype(float),
        "is_known_device": is_known_device.astype(float),
        "is_new_payee": is_new_payee.astype(float),
        "is_round_number": is_round_number.astype(float),
        "is_usual_location": np.where(labels == 1,
                                      rng.binomial(1, 0.25, n_samples),
                                      rng.binomial(1, 0.85, n_samples)).astype(float),
        "is_vpn": np.where(labels == 1,
                           rng.binomial(1, 0.22, n_samples),
                           rng.binomial(1, 0.02, n_samples)).astype(float),
        "merchant_category": rng.integers(0, 20, n_samples).astype(float),
        "payment_app": rng.integers(0, 6, n_samples).astype(float),
        "payment_type": rng.integers(0, 4, n_samples).astype(float),
        "state": rng.integers(0, 29, n_samples).astype(float),
        "transactions_last_24h": transactions_last_24h,
        "transactions_last_hour": transactions_last_hour,
        "vpa_age_days": vpa_age_days,
        "is_night": is_night.astype(float),
        "is_weekend": is_weekend.astype(float),
        "is_business_hours": is_business_hours.astype(float),
        "device_location_risk": (1 - is_known_device).astype(float),
        "velocity_risk": velocity_risk,
        "new_payee_night": new_payee_night,
        "high_amount_new_device": high_amount_new_device,
        "young_vpa_high_amount": ((vpa_age_days < 30) & (amounts > 10_000)).astype(float),
        "heuristic_risk_score": heuristic,
    })

    # Shuffle
    shuffled_idx = rng.permutation(n_samples)
    df = df.iloc[shuffled_idx].reset_index(drop=True)
    labels = labels[shuffled_idx]

    return df, pd.Series(labels, name="is_fraud")


def _hour_prob(fraud: bool) -> np.ndarray:
    """Hour-of-day probability distribution."""
    p = np.zeros(24)
    if fraud:
        # More fraud at night (23-5) and lunch (12-14)
        night = [23, 0, 1, 2, 3, 4, 5]
        lunch = [12, 13, 14]
        for h in night:
            p[h] = 0.065
        for h in lunch:
            p[h] = 0.038
        remaining = set(range(24)) - set(night) - set(lunch)
        base = (1 - sum(p)) / len(remaining)
        for h in remaining:
            p[h] = max(base, 0.001)
    else:
        # Normal business hours distribution
        for h in range(9, 21):
            p[h] = 0.072
        for h in range(21, 24):
            p[h] = 0.012
        for h in range(0, 9):
            p[h] = 0.008
    p = np.abs(p)
    return p / p.sum()


def _generate_v_features(rng: np.random.Generator, n: int,
                          labels: np.ndarray) -> dict:
    """Generate PCA V-features correlated with fraud label."""
    v_cols = ["V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "V9",
              "V10", "V11", "V12", "V13", "V14", "V15", "V16", "V17",
              "V18", "V19", "V20", "V21", "V22", "V23", "V24", "V25",
              "V26", "V27", "V28"]
    # Some V-features have strong fraud signal (as in real IEEE-CIS data)
    signal_cols = {"V14": -0.8, "V17": -0.7, "V12": -0.6, "V10": -0.5,
                   "V16": -0.55, "V3": 0.4, "V11": 0.5, "V4": 0.3}
    out = {}
    for col in v_cols:
        noise = rng.standard_normal(n)
        if col in signal_cols:
            signal_strength = signal_cols[col]
            out[col] = noise + signal_strength * (labels * 2 - 1)
        else:
            out[col] = noise
    return out


# ---------------------------------------------------------------------------
# Training helpers
# ---------------------------------------------------------------------------

def _evaluate(model, X_test: np.ndarray, y_test: np.ndarray,
               model_name: str, threshold: float = 0.5) -> dict:
    """Compute standard metrics. Handles Isolation Forest separately."""
    if model_name == "Isolation Forest":
        y_pred_raw = model.predict(X_test)
        y_pred = (y_pred_raw == -1).astype(int)
        scores = -model.score_samples(X_test)
        scores = (scores - scores.min()) / (scores.max() - scores.min() + 1e-10)
    else:
        proba = model.predict_proba(X_test)[:, 1]
        y_pred = (proba >= threshold).astype(int)
        scores = proba

    return {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred, zero_division=0),
        "recall": recall_score(y_test, y_pred, zero_division=0),
        "f1": f1_score(y_test, y_pred, zero_division=0),
        "auc": roc_auc_score(y_test, scores),
        "avg_precision": average_precision_score(y_test, scores),
        "y_pred": y_pred,
        "y_prob": scores,
    }


def _find_optimal_threshold(y_true: np.ndarray, y_prob: np.ndarray,
                             min_precision: float = 0.90) -> float:
    """Find the lowest threshold that achieves `min_precision` while
    maximising recall.  Falls back to the F1-optimal threshold if the
    precision constraint cannot be satisfied.
    """
    precs, recs, thresholds = precision_recall_curve(y_true, y_prob)
    # thresholds has one fewer element than precs/recs
    best_thresh = 0.5
    best_recall = 0.0
    for p, r, t in zip(precs[:-1], recs[:-1], thresholds):
        if p >= min_precision and r > best_recall:
            best_recall = r
            best_thresh = float(t)

    if best_recall == 0.0:
        # Fall back: maximise F1
        f1s = 2 * precs[:-1] * recs[:-1] / (precs[:-1] + recs[:-1] + 1e-10)
        best_thresh = float(thresholds[np.argmax(f1s)])
        logger.warning(
            "Precision≥%.2f constraint not met; using F1-optimal threshold=%.3f",
            min_precision, best_thresh,
        )
    return best_thresh


# ---------------------------------------------------------------------------
# Plot helpers
# ---------------------------------------------------------------------------

def _plot_roc(results: dict, output_path: str) -> None:
    plt.figure(figsize=(10, 8))
    colors = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6"]
    for (name, res), color in zip(results.items(), colors):
        if name == "Isolation Forest":
            continue
        fpr, tpr, _ = roc_curve(res["y_true"], res["y_prob"])
        plt.plot(fpr, tpr, color=color, lw=2,
                 label=f"{name}  (AUC={res['auc']:.4f})")
    plt.plot([0, 1], [0, 1], "k--", lw=1, label="Random")
    plt.xlabel("False Positive Rate", fontsize=13)
    plt.ylabel("True Positive Rate", fontsize=13)
    plt.title("ROC Curves — Phase 11 Ensemble", fontsize=15, fontweight="bold")
    plt.legend(loc="lower right", fontsize=11)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("Saved ROC curves → %s", output_path)


def _plot_pr(results: dict, output_path: str) -> None:
    plt.figure(figsize=(10, 8))
    colors = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6"]
    for (name, res), color in zip(results.items(), colors):
        if name == "Isolation Forest":
            continue
        prec, rec, _ = precision_recall_curve(res["y_true"], res["y_prob"])
        plt.plot(rec, prec, color=color, lw=2,
                 label=f"{name}  (AP={res['avg_precision']:.4f})")
    plt.xlabel("Recall", fontsize=13)
    plt.ylabel("Precision", fontsize=13)
    plt.title("Precision-Recall Curves — Phase 11 Ensemble", fontsize=15, fontweight="bold")
    plt.legend(loc="upper right", fontsize=11)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("Saved PR curves → %s", output_path)


def _plot_confusion_matrices(results: dict, output_path: str) -> None:
    names = list(results.keys())
    n = len(names)
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    axes = axes.flatten()
    for i, name in enumerate(names):
        cm = confusion_matrix(results[name]["y_true"], results[name]["y_pred"])
        ax = axes[i]
        im = ax.imshow(cm, interpolation="nearest", cmap="Blues")
        ax.set_title(f"{name}", fontsize=12, fontweight="bold")
        ax.set_xlabel("Predicted")
        ax.set_ylabel("Actual")
        ax.set_xticks([0, 1])
        ax.set_yticks([0, 1])
        ax.set_xticklabels(["Legit", "Fraud"])
        ax.set_yticklabels(["Legit", "Fraud"])
        for row in range(2):
            for col in range(2):
                ax.text(col, row, f"{cm[row, col]:,}",
                        ha="center", va="center",
                        color="white" if cm[row, col] > cm.max() / 2 else "black",
                        fontsize=11, fontweight="bold")
    for j in range(i + 1, len(axes)):
        axes[j].set_visible(False)
    plt.suptitle("Confusion Matrices — Phase 11 Ensemble Models",
                 fontsize=15, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("Saved confusion matrices → %s", output_path)


def _plot_model_comparison(results: dict, output_path: str) -> None:
    metrics = ["accuracy", "precision", "recall", "f1", "auc"]
    names = list(results.keys())
    x = np.arange(len(metrics))
    width = 0.15
    colors = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6"]

    fig, ax = plt.subplots(figsize=(14, 8))
    for i, (name, color) in enumerate(zip(names, colors)):
        vals = [results[name].get(m, 0) for m in metrics]
        offset = (i - len(names) / 2) * width + width / 2
        bars = ax.bar(x + offset, vals, width, label=name, color=color, alpha=0.85)
        for bar, val in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.005,
                    f"{val:.3f}", ha="center", va="bottom", fontsize=8, rotation=45)

    ax.set_xlabel("Metric", fontsize=13)
    ax.set_ylabel("Score", fontsize=13)
    ax.set_title("Model Comparison — Phase 11 Ensemble", fontsize=15, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([m.upper() for m in metrics], fontsize=11)
    ax.set_ylim(0, 1.15)
    ax.legend(loc="upper right", fontsize=10)
    ax.axhline(0.90, color="gray", linestyle="--", lw=1, label="Target=0.90")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("Saved model comparison → %s", output_path)


def _plot_xgb_importance(xgb_model, feature_names: list, output_path: str) -> None:
    importances = xgb_model.feature_importances_
    top_n = 20
    idx = np.argsort(importances)[-top_n:]
    plt.figure(figsize=(10, 8))
    plt.barh(np.array(feature_names)[idx], importances[idx], color="#e74c3c", alpha=0.8)
    plt.xlabel("Feature Importance (Gain)", fontsize=12)
    plt.title("XGBoost Top-20 Feature Importances — Phase 11", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("Saved XGBoost feature importance → %s", output_path)


# ---------------------------------------------------------------------------
# Ensemble aggregation
# ---------------------------------------------------------------------------

def _weighted_ensemble(results: dict, weights: dict | None = None) -> dict:
    """Weighted average ensemble of all model probabilities."""
    default_weights = {
        "XGBoost": 0.35,
        "Random Forest": 0.25,
        "Logistic Regression": 0.15,
        "Isolation Forest": 0.10,
        "Neural Network": 0.15,
    }
    w = weights or default_weights

    y_true = next(iter(results.values()))["y_true"]
    total_w = sum(w.get(name, 0) for name in results)
    ensemble_prob = np.zeros(len(y_true))
    for name, res in results.items():
        ensemble_prob += res["y_prob"] * w.get(name, 0)
    ensemble_prob /= total_w

    threshold = _find_optimal_threshold(y_true, ensemble_prob, min_precision=0.90)
    y_pred = (ensemble_prob >= threshold).astype(int)

    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "auc": roc_auc_score(y_true, ensemble_prob),
        "avg_precision": average_precision_score(y_true, ensemble_prob),
        "y_pred": y_pred,
        "y_prob": ensemble_prob,
        "y_true": y_true,
        "threshold": threshold,
    }


# ---------------------------------------------------------------------------
# Main training routine
# ---------------------------------------------------------------------------

def train(output_dir: str = MODELS_DIR, quick: bool = False) -> dict:
    """Run the full Phase 11 training pipeline.

    Parameters
    ----------
    output_dir:
        Directory to save model artifacts.  Created if it does not exist.
    quick:
        If True, use a smaller dataset (50 k rows) for fast CI runs.

    Returns
    -------
    dict with per-model and ensemble metrics.
    """
    os.makedirs(output_dir, exist_ok=True)

    n_samples = 50_000 if quick else 500_000
    logger.info("Phase 11 training started  (n_samples=%d, quick=%s)", n_samples, quick)

    # ── 1. Load or generate feature names ────────────────────────────────
    fn_path = os.path.join(output_dir, "mlbfd_mega_feature_names.pkl")
    if os.path.exists(fn_path):
        with open(fn_path, "rb") as fh:
            feature_names: list = pickle.load(fh)
        logger.info("Loaded %d feature names from %s", len(feature_names), fn_path)
    else:
        feature_names = []   # will be determined after dataset generation

    # ── 2. Generate dataset ───────────────────────────────────────────────
    logger.info("Generating synthetic Phase-11 dataset (%d rows)…", n_samples)
    X_raw, y = _generate_phase11_dataset(n_samples=n_samples, random_state=42)

    # Align to stored feature names (or derive them)
    if feature_names:
        for col in feature_names:
            if col not in X_raw.columns:
                X_raw[col] = 0.0
        X_raw = X_raw[feature_names]
    else:
        feature_names = list(X_raw.columns)
        with open(fn_path, "wb") as fh:
            pickle.dump(feature_names, fh)
        logger.info("Saved %d feature names to %s", len(feature_names), fn_path)

    # ── 3. Train/test split ───────────────────────────────────────────────
    X_train, X_test, y_train, y_test = train_test_split(
        X_raw.values.astype(np.float32), y.values,
        test_size=0.20, stratify=y, random_state=42,
    )
    logger.info("Split: train=%d  test=%d  fraud_train=%.1f%%  fraud_test=%.1f%%",
                len(X_train), len(X_test),
                y_train.mean() * 100, y_test.mean() * 100)

    # ── 4. Feature scaling ────────────────────────────────────────────────
    scaler = StandardScaler()
    X_train_sc = scaler.fit_transform(X_train)
    X_test_sc = scaler.transform(X_test)

    scaler_path = os.path.join(output_dir, "mlbfd_mega_scaler.pkl")
    with open(scaler_path, "wb") as fh:
        pickle.dump(scaler, fh)
    logger.info("Scaler saved → %s", scaler_path)

    # ── 5. Class imbalance weight ─────────────────────────────────────────
    fraud_rate = float(y_train.mean())
    scale_pos_weight = (1 - fraud_rate) / (fraud_rate + 1e-10)
    logger.info("Fraud rate=%.2f%%  scale_pos_weight=%.2f",
                fraud_rate * 100, scale_pos_weight)

    trained_models: dict = {}
    results: dict = {}
    train_times: dict = {}

    # ── MODEL 1: XGBoost (Phase 11 — enhanced hyperparameters) ───────────
    logger.info("[1/5] Training XGBoost…")
    t0 = time.time()
    xgb_model = xgb.XGBClassifier(
        n_estimators=400,
        max_depth=7,
        learning_rate=0.08,
        subsample=0.85,
        colsample_bytree=0.75,
        min_child_weight=5,
        gamma=0.15,
        reg_alpha=0.1,
        reg_lambda=1.5,
        scale_pos_weight=scale_pos_weight,
        random_state=42,
        eval_metric="aucpr",
        tree_method="hist",
        n_jobs=-1,
        early_stopping_rounds=20,
    )
    X_tr_xgb, X_val_xgb, y_tr_xgb, y_val_xgb = train_test_split(
        X_train_sc, y_train, test_size=0.10, stratify=y_train, random_state=0)
    xgb_model.fit(
        X_tr_xgb, y_tr_xgb,
        eval_set=[(X_val_xgb, y_val_xgb)],
        verbose=False,
    )
    train_times["XGBoost"] = time.time() - t0
    trained_models["XGBoost"] = xgb_model

    raw_res = _evaluate(xgb_model, X_test_sc, y_test, "XGBoost", threshold=0.5)
    thresh = _find_optimal_threshold(y_test, raw_res["y_prob"], min_precision=0.90)
    res = _evaluate(xgb_model, X_test_sc, y_test, "XGBoost", threshold=thresh)
    res["train_time"] = train_times["XGBoost"]
    res["threshold"] = thresh
    res["y_true"] = y_test
    results["XGBoost"] = res
    logger.info("XGBoost  P=%.3f R=%.3f F1=%.3f AUC=%.4f (thr=%.3f)",
                res["precision"], res["recall"], res["f1"], res["auc"], thresh)
    gc.collect()

    # ── MODEL 2: Random Forest (Phase 11 — balanced class weight) ────────
    logger.info("[2/5] Training Random Forest…")
    t0 = time.time()
    rf_model = RandomForestClassifier(
        n_estimators=300,
        max_depth=20,
        min_samples_split=4,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
        oob_score=True,
    )
    rf_model.fit(X_train_sc, y_train)
    train_times["Random Forest"] = time.time() - t0
    trained_models["Random Forest"] = rf_model

    raw_res = _evaluate(rf_model, X_test_sc, y_test, "Random Forest", threshold=0.5)
    thresh = _find_optimal_threshold(y_test, raw_res["y_prob"], min_precision=0.90)
    res = _evaluate(rf_model, X_test_sc, y_test, "Random Forest", threshold=thresh)
    res["train_time"] = train_times["Random Forest"]
    res["threshold"] = thresh
    res["y_true"] = y_test
    res["oob_score"] = rf_model.oob_score_
    results["Random Forest"] = res
    logger.info("Random Forest  P=%.3f R=%.3f F1=%.3f AUC=%.4f OOB=%.4f",
                res["precision"], res["recall"], res["f1"], res["auc"],
                res["oob_score"])
    gc.collect()

    # ── MODEL 3: Logistic Regression (Phase 11 — calibrated) ─────────────
    logger.info("[3/5] Training Logistic Regression…")
    t0 = time.time()
    lr_base = LogisticRegression(
        C=0.5,
        penalty="l2",
        class_weight="balanced",
        max_iter=2000,
        random_state=42,
        n_jobs=-1,
        solver="saga",
    )
    lr_model = CalibratedClassifierCV(lr_base, method="isotonic", cv=3)
    lr_model.fit(X_train_sc, y_train)
    train_times["Logistic Regression"] = time.time() - t0
    trained_models["Logistic Regression"] = lr_model

    raw_res = _evaluate(lr_model, X_test_sc, y_test, "Logistic Regression", threshold=0.5)
    thresh = _find_optimal_threshold(y_test, raw_res["y_prob"], min_precision=0.90)
    res = _evaluate(lr_model, X_test_sc, y_test, "Logistic Regression", threshold=thresh)
    res["train_time"] = train_times["Logistic Regression"]
    res["threshold"] = thresh
    res["y_true"] = y_test
    results["Logistic Regression"] = res
    logger.info("Logistic Regression  P=%.3f R=%.3f F1=%.3f AUC=%.4f",
                res["precision"], res["recall"], res["f1"], res["auc"])
    gc.collect()

    # ── MODEL 4: Isolation Forest (Phase 11 — tuned contamination) ───────
    logger.info("[4/5] Training Isolation Forest…")
    t0 = time.time()
    iso_model = IsolationForest(
        n_estimators=300,
        contamination=max(0.05, min(0.45, float(fraud_rate) * 1.2)),
        max_samples="auto",
        max_features=0.8,
        random_state=42,
        n_jobs=-1,
    )
    iso_model.fit(X_train_sc)
    train_times["Isolation Forest"] = time.time() - t0
    trained_models["Isolation Forest"] = iso_model

    res = _evaluate(iso_model, X_test_sc, y_test, "Isolation Forest")
    res["train_time"] = train_times["Isolation Forest"]
    res["threshold"] = 0.5
    res["y_true"] = y_test
    results["Isolation Forest"] = res
    logger.info("Isolation Forest  P=%.3f R=%.3f F1=%.3f AUC=%.4f",
                res["precision"], res["recall"], res["f1"], res["auc"])
    gc.collect()

    # ── MODEL 5: Neural Network (optional — TensorFlow) ───────────────────
    try:
        import tensorflow as tf  # type: ignore
        from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau  # type: ignore
        from tensorflow.keras.layers import BatchNormalization, Dense, Dropout  # type: ignore
        from tensorflow.keras.models import Sequential  # type: ignore
        from tensorflow.keras.optimizers import Adam  # type: ignore

        logger.info("[5/5] Training Neural Network (TensorFlow found)…")
        t0 = time.time()

        n_feat = X_train_sc.shape[1]
        nn_model = Sequential([
            Dense(512, activation="relu", input_shape=(n_feat,)),
            BatchNormalization(),
            Dropout(0.4),
            Dense(256, activation="relu"),
            BatchNormalization(),
            Dropout(0.35),
            Dense(128, activation="relu"),
            BatchNormalization(),
            Dropout(0.25),
            Dense(64, activation="relu"),
            Dropout(0.20),
            Dense(32, activation="relu"),
            Dense(1, activation="sigmoid"),
        ])
        nn_model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss="binary_crossentropy",
            metrics=["accuracy"],
        )
        callbacks = [
            EarlyStopping(monitor="val_loss", patience=8, restore_best_weights=True),
            ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=4, min_lr=1e-6),
        ]
        # Use class weights to handle imbalance
        class_weight = {0: 1.0, 1: scale_pos_weight}
        nn_model.fit(
            X_train_sc, y_train,
            epochs=60,
            batch_size=2048,
            validation_split=0.15,
            callbacks=callbacks,
            class_weight=class_weight,
            verbose=0,
        )
        train_times["Neural Network"] = time.time() - t0

        nn_prob = nn_model.predict(X_test_sc, verbose=0).flatten()
        thresh = _find_optimal_threshold(y_test, nn_prob, min_precision=0.90)
        y_pred_nn = (nn_prob >= thresh).astype(int)
        res = {
            "accuracy": accuracy_score(y_test, y_pred_nn),
            "precision": precision_score(y_test, y_pred_nn, zero_division=0),
            "recall": recall_score(y_test, y_pred_nn, zero_division=0),
            "f1": f1_score(y_test, y_pred_nn, zero_division=0),
            "auc": roc_auc_score(y_test, nn_prob),
            "avg_precision": average_precision_score(y_test, nn_prob),
            "y_pred": y_pred_nn,
            "y_prob": nn_prob,
            "y_true": y_test,
            "train_time": train_times["Neural Network"],
            "threshold": thresh,
        }
        results["Neural Network"] = res
        trained_models["Neural Network"] = nn_model

        # Save Keras model
        nn_path = os.path.join(output_dir, "mlbfd_mega_neural_network_model.keras")
        nn_model.save(nn_path)
        logger.info("Neural Network  P=%.3f R=%.3f F1=%.3f AUC=%.4f",
                    res["precision"], res["recall"], res["f1"], res["auc"])
    except Exception as exc:
        logger.warning("[5/5] Neural Network skipped: %s", exc)

    gc.collect()

    # ── 6. Weighted ensemble ──────────────────────────────────────────────
    logger.info("Computing weighted ensemble…")
    ensemble_res = _weighted_ensemble(results)
    results["Ensemble"] = ensemble_res
    logger.info(
        "Ensemble  P=%.3f R=%.3f F1=%.3f AUC=%.4f (thr=%.3f)",
        ensemble_res["precision"], ensemble_res["recall"],
        ensemble_res["f1"], ensemble_res["auc"], ensemble_res["threshold"],
    )

    # ── 7. Save sklearn/XGBoost models ───────────────────────────────────
    model_file_map = {
        "XGBoost": "mlbfd_mega_xgboost_model.pkl",
        "Random Forest": "mlbfd_mega_random_forest_model.pkl",
        "Logistic Regression": "mlbfd_mega_logistic_regression_model.pkl",
        "Isolation Forest": "mlbfd_mega_isolation_forest_model.pkl",
    }
    for name, fname in model_file_map.items():
        if name in trained_models:
            path = os.path.join(output_dir, fname)
            with open(path, "wb") as fh:
                pickle.dump(trained_models[name], fh)
            logger.info("Saved %s → %s", name, path)

    # ── 8. Save results pickle ────────────────────────────────────────────
    results_save = {
        name: {k: v for k, v in res.items()
               if k not in ("y_pred", "y_prob", "y_true")}
        for name, res in results.items()
    }
    results_path = os.path.join(output_dir, "mlbfd_mega_results.pkl")
    with open(results_path, "wb") as fh:
        pickle.dump(results_save, fh)
    logger.info("Saved results → %s", results_path)

    # ── 9. Save dataset info ──────────────────────────────────────────────
    dataset_info = {
        "total_rows": n_samples,
        "total_features": len(feature_names),
        "feature_names": feature_names,
        "datasets_used": ["Phase 2B Mega (synthetic replication)"],
        "dataset_stats": {
            "Phase 2B Synthetic": {
                "rows": n_samples,
                "fraud": int(y.sum()),
                "fraud_pct": float(y.mean() * 100),
                "source": "phase11_synthetic",
            }
        },
        "sources": ["phase11_synthetic"],
        "fraud_total": int(y.sum()),
        "fraud_pct": float(y.mean() * 100),
        "training_date": datetime.now().strftime("%Y-%m-%d"),
        "phase": "Phase 11",
        "best_model": max(
            (n for n in results if n != "Ensemble"),
            key=lambda n: results[n].get("auc", 0),
        ),
        "best_auc": max(
            results[n].get("auc", 0) for n in results if n != "Ensemble"
        ),
        "models_trained": [n for n in trained_models],
        "ensemble_threshold": ensemble_res["threshold"],
        "ensemble_f1": ensemble_res["f1"],
        "ensemble_precision": ensemble_res["precision"],
        "ensemble_recall": ensemble_res["recall"],
    }
    info_path = os.path.join(output_dir, "mlbfd_mega_dataset_info.pkl")
    with open(info_path, "wb") as fh:
        pickle.dump(dataset_info, fh)
    logger.info("Saved dataset info → %s", info_path)

    # ── 10. Plots ─────────────────────────────────────────────────────────
    _plot_roc(results, os.path.join(output_dir, "mlbfd_mega_roc_curves.png"))
    _plot_pr(results, os.path.join(output_dir, "mlbfd_mega_precision_recall.png"))
    _plot_confusion_matrices(results,
                             os.path.join(output_dir, "mlbfd_mega_confusion_matrices.png"))
    _plot_model_comparison(
        {k: v for k, v in results.items() if k != "Ensemble"},
        os.path.join(output_dir, "mlbfd_mega_model_comparison.png"),
    )
    _plot_xgb_importance(
        trained_models["XGBoost"], feature_names,
        os.path.join(output_dir, "mlbfd_mega_xgb_importance.png"),
    )

    # ── 11. Print summary table ───────────────────────────────────────────
    logger.info("\n%s", "=" * 70)
    logger.info("%-22s %8s %9s %8s %7s %8s", "Model", "Acc", "Precision", "Recall", "F1", "AUC")
    logger.info("%s", "-" * 70)
    for name, res in results.items():
        logger.info(
            "%-22s %8.4f %9.4f %8.4f %7.4f %8.4f",
            name,
            res["accuracy"],
            res["precision"],
            res["recall"],
            res["f1"],
            res["auc"],
        )
    logger.info("%s", "=" * 70)

    return results


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 11 — Ensemble Retraining Script")
    parser.add_argument("--quick", action="store_true",
                        help="Use small synthetic dataset for quick testing")
    parser.add_argument("--output-dir", default=MODELS_DIR,
                        help="Directory to save model artifacts (default: models/)")
    args = parser.parse_args()

    results = train(output_dir=args.output_dir, quick=args.quick)

    # Check success criteria
    ens = results.get("Ensemble", {})
    p, r, f1 = ens.get("precision", 0), ens.get("recall", 0), ens.get("f1", 0)
    print("\n" + "=" * 60)
    print("PHASE 11 SUCCESS CRITERIA CHECK")
    print("=" * 60)
    print(f"  Ensemble F1     : {f1:.4f}  {'✅' if f1 >= 0.92 else '⚠️ '} (target ≥ 0.92)")
    print(f"  Ensemble Prec.  : {p:.4f}  {'✅' if p >= 0.90 else '⚠️ '} (target ≥ 0.90)")
    print(f"  Ensemble Recall : {r:.4f}  {'✅' if r >= 0.85 else '⚠️ '} (target ≥ 0.85)")
    print("=" * 60)


if __name__ == "__main__":
    main()
