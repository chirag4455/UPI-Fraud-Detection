"""
Model evaluation, visualizations, and report generation.
"""

from __future__ import annotations

import html
import logging
import pickle
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from sklearn.metrics import (
    accuracy_score,
    auc,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

from training_config import TrainingConfig

logger = logging.getLogger("mlbfd.model_evaluator")


def _metrics(y_true: np.ndarray, y_pred: np.ndarray, y_prob: np.ndarray) -> dict:
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "auc": float(roc_auc_score(y_true, y_prob)) if len(np.unique(y_true)) > 1 else 0.5,
    }


def evaluate_and_report(
    data_bundle: dict,
    trainer_bundle: dict,
    config: TrainingConfig,
) -> dict:
    config.ensure_output_dirs()
    reports_dir = Path(config.report_output_dir)
    models_dir = Path(config.model_output_dir)
    y_test = np.asarray(data_bundle["y_test"])
    feature_names = data_bundle["feature_names"]

    all_metrics: dict = {}
    preds = trainer_bundle["predictions"]

    for name, payload in preds.items():
        y_true = np.asarray(payload.get("y_true_override", y_test))
        y_pred = np.asarray(payload["y_pred"])
        y_prob = np.asarray(payload["y_prob"])
        all_metrics[name] = _metrics(y_true, y_pred, y_prob)
        if "cv_auc" in payload:
            all_metrics[name]["cv_auc"] = float(payload["cv_auc"])

    with open(models_dir / "mlbfd_mega_results.pkl", "wb") as f:
        pickle.dump(all_metrics, f)

    # Confusion matrices
    cols = 3
    rows = max(1, int(np.ceil(len(preds) / cols)))
    fig, axes = plt.subplots(rows, cols, figsize=(6 * cols, 5 * rows))
    axes = np.array(axes).reshape(rows, cols)
    for idx, (name, payload) in enumerate(preds.items()):
        r, c = divmod(idx, cols)
        y_true = np.asarray(payload.get("y_true_override", y_test))
        cm = confusion_matrix(y_true, payload["y_pred"])
        sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", ax=axes[r, c])
        axes[r, c].set_title(name)
        axes[r, c].set_xlabel("Pred")
        axes[r, c].set_ylabel("True")
    for idx in range(len(preds), rows * cols):
        r, c = divmod(idx, cols)
        axes[r, c].axis("off")
    cm_path = reports_dir / "mlbfd_mega_confusion_matrices.png"
    fig.tight_layout()
    fig.savefig(cm_path, dpi=150)
    plt.close(fig)

    # ROC and PR curves
    fig, ax = plt.subplots(figsize=(10, 7))
    for name, payload in preds.items():
        y_true = np.asarray(payload.get("y_true_override", y_test))
        if len(np.unique(y_true)) < 2:
            continue
        fpr, tpr, _ = roc_curve(y_true, payload["y_prob"])
        ax.plot(fpr, tpr, label=f"{name} (AUC={auc(fpr, tpr):.3f})")
    ax.plot([0, 1], [0, 1], "k--", alpha=0.5)
    ax.set_title("ROC Curves")
    ax.legend()
    roc_path = reports_dir / "mlbfd_mega_roc_curves.png"
    fig.savefig(roc_path, dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 7))
    for name, payload in preds.items():
        y_true = np.asarray(payload.get("y_true_override", y_test))
        if len(np.unique(y_true)) < 2:
            continue
        p, r, _ = precision_recall_curve(y_true, payload["y_prob"])
        ax.plot(r, p, label=name)
    ax.set_title("Precision-Recall Curves")
    ax.legend()
    pr_path = reports_dir / "mlbfd_mega_precision_recall.png"
    fig.savefig(pr_path, dpi=150)
    plt.close(fig)

    # Model comparison chart
    metric_order = ["accuracy", "precision", "recall", "f1", "auc"]
    names = list(all_metrics.keys())
    vals = np.array([[all_metrics[n][m] for m in metric_order] for n in names])
    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(names))
    width = 0.15
    for i, m in enumerate(metric_order):
        ax.bar(x + i * width, vals[:, i], width=width, label=m.upper())
    ax.set_xticks(x + width * 2)
    ax.set_xticklabels(names, rotation=25, ha="right")
    ax.set_ylim(0, 1)
    ax.legend()
    comp_path = reports_dir / "mlbfd_mega_model_comparison.png"
    fig.tight_layout()
    fig.savefig(comp_path, dpi=150)
    plt.close(fig)

    # Feature importance (RF, XGB where available)
    trained = trainer_bundle["models"]
    for model_name, out_name in [
        ("Random Forest", "mlbfd_mega_rf_feature_importance.png"),
        ("XGBoost", "mlbfd_mega_xgb_importance.png"),
    ]:
        model = trained.get(model_name)
        if model is None or not hasattr(model, "feature_importances_"):
            continue
        imp = np.asarray(model.feature_importances_)
        order = np.argsort(imp)[-20:]
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.barh(np.array(feature_names)[order], imp[order], color="tab:blue")
        ax.set_title(f"{model_name} Top-20 Feature Importance")
        fig.tight_layout()
        fig.savefig(reports_dir / out_name, dpi=150)
        plt.close(fig)

    # Training history plots
    histories = trainer_bundle.get("histories", {})
    if "Neural Network" in histories:
        hist = histories["Neural Network"]
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.plot(hist.get("loss", []), label="loss")
        ax.plot(hist.get("val_loss", []), label="val_loss")
        ax.legend()
        ax.set_title("Neural Network Training History")
        fig.savefig(reports_dir / "mlbfd_mega_nn_history.png", dpi=150)
        plt.close(fig)
    if "LSTM" in histories:
        hist = histories["LSTM"]
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.plot(hist.get("loss", []), label="loss")
        ax.plot(hist.get("val_loss", []), label="val_loss")
        ax.legend()
        ax.set_title("LSTM Training History")
        fig.savefig(reports_dir / "mlbfd_mega_lstm_history.png", dpi=150)
        plt.close(fig)

    # HTML report
    report_path = reports_dir / "mlbfd_mega_training_report.html"
    rows = "\n".join(
        f"<tr><td>{html.escape(name)}</td>"
        f"<td>{m['accuracy']:.4f}</td><td>{m['precision']:.4f}</td>"
        f"<td>{m['recall']:.4f}</td><td>{m['f1']:.4f}</td><td>{m['auc']:.4f}</td></tr>"
        for name, m in all_metrics.items()
    )
    report_html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>MLBFD Mega Training Report</title></head>
<body>
<h1>MLBFD Mega Training Report</h1>
<table border="1" cellspacing="0" cellpadding="6">
<tr><th>Model</th><th>Accuracy</th><th>Precision</th><th>Recall</th><th>F1</th><th>AUC-ROC</th></tr>
{rows}
</table>
<h2>Visualizations</h2>
<ul>
<li><img src="{cm_path.name}" width="900"></li>
<li><img src="{roc_path.name}" width="900"></li>
<li><img src="{pr_path.name}" width="900"></li>
<li><img src="{comp_path.name}" width="900"></li>
</ul>
</body></html>"""
    report_path.write_text(report_html, encoding="utf-8")
    logger.info("Training report generated: %s", report_path)

    return {"metrics": all_metrics, "report_path": str(report_path)}

