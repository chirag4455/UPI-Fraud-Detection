"""Evaluation, visualization and reporting for automated MLBFD training."""

from __future__ import annotations

import json
import logging
import pickle
from datetime import datetime
from pathlib import Path
from typing import Dict

from training_config import TrainingConfig

logger = logging.getLogger("mlbfd.model_evaluator")


def evaluate_and_report(config: TrainingConfig, processed_data, models: Dict[str, object], metrics: Dict, history: Dict) -> Dict:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from sklearn.metrics import PrecisionRecallDisplay, RocCurveDisplay, confusion_matrix

    model_dir = Path(config.output_models_dir)
    report_dir = Path(config.output_reports_dir)
    report_dir.mkdir(parents=True, exist_ok=True)

    X_test, y_test = processed_data.X_test, processed_data.y_test
    prob_map = {}
    for name, model in models.items():
        try:
            if name == "Isolation Forest":
                score = -model.score_samples(X_test)
                prob_map[name] = (score - score.min()) / (score.max() - score.min() + 1e-9)
            elif name in {"Neural Network", "LSTM"} and hasattr(model, "predict") and not hasattr(model, "predict_proba"):
                prob_map[name] = model.predict(X_test, verbose=0).reshape(-1).astype(float)
            elif hasattr(model, "predict_proba"):
                prob_map[name] = model.predict_proba(X_test)[:, 1]
            else:
                prob_map[name] = model.predict(X_test).astype(float)
        except Exception:
            pass

    plt.figure(figsize=(10, 7))
    for name, probs in prob_map.items():
        try:
            RocCurveDisplay.from_predictions(y_test, probs, name=name)
        except Exception:
            pass
    plt.title("ROC Curves")
    roc_path = report_dir / "mlbfd_mega_roc_curves.png"
    plt.tight_layout()
    plt.savefig(roc_path, dpi=130)
    plt.close()

    plt.figure(figsize=(10, 7))
    for name, probs in prob_map.items():
        try:
            PrecisionRecallDisplay.from_predictions(y_test, probs, name=name)
        except Exception:
            pass
    plt.title("Precision-Recall Curves")
    pr_path = report_dir / "mlbfd_mega_precision_recall.png"
    plt.tight_layout()
    plt.savefig(pr_path, dpi=130)
    plt.close()

    metric_keys = ["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc"]
    model_names = list(metrics.keys())
    x = np.arange(len(metric_keys))
    width = max(0.08, 0.9 / max(1, len(model_names)))
    plt.figure(figsize=(14, 8))
    for idx, name in enumerate(model_names):
        vals = [float(metrics[name].get(k, 0.0)) for k in metric_keys]
        plt.bar(x + idx * width, vals, width=width, label=name)
    plt.xticks(x + width * (len(model_names) / 2), metric_keys, rotation=20)
    plt.ylim(0, 1.05)
    plt.title("Model Comparison")
    plt.legend()
    comparison_path = report_dir / "mlbfd_mega_model_comparison.png"
    plt.tight_layout()
    plt.savefig(comparison_path, dpi=130)
    plt.close()

    # Confusion matrix grid
    names = list(prob_map.keys())
    if names:
        fig, axes = plt.subplots(2, 3, figsize=(16, 10))
        axes = axes.flatten()
        for i, name in enumerate(names[:6]):
            y_pred = (prob_map[name] >= 0.5).astype(int)
            cm = confusion_matrix(y_test, y_pred)
            axes[i].imshow(cm, cmap="Blues")
            axes[i].set_title(name)
            for r in range(cm.shape[0]):
                for c in range(cm.shape[1]):
                    axes[i].text(c, r, str(cm[r, c]), ha="center", va="center")
        for j in range(len(names), len(axes)):
            axes[j].set_visible(False)
        cm_path = report_dir / "mlbfd_mega_confusion_matrices.png"
        plt.tight_layout()
        plt.savefig(cm_path, dpi=130)
        plt.close()

    if "XGBoost" in models and hasattr(models["XGBoost"], "feature_importances_"):
        vals = models["XGBoost"].feature_importances_
        top_idx = np.argsort(vals)[-20:]
        names = np.array(processed_data.feature_names)[top_idx]
        plt.figure(figsize=(10, 8))
        plt.barh(names, vals[top_idx])
        plt.title("XGBoost Feature Importance")
        importance_path = report_dir / "mlbfd_mega_xgb_importance.png"
        plt.tight_layout()
        plt.savefig(importance_path, dpi=130)
        plt.close()

    for model_name, hist in history.items():
        if not hist:
            continue
        plt.figure(figsize=(10, 6))
        for key, values in hist.items():
            plt.plot(values, label=key)
        plt.title(f"{model_name} Training History")
        plt.legend()
        out = report_dir / ("mlbfd_mega_nn_history.png" if model_name == "Neural Network" else "mlbfd_mega_lstm_history.png")
        plt.tight_layout()
        plt.savefig(out, dpi=130)
        plt.close()

    try:
        import shap
        if "XGBoost" in models:
            sample = processed_data.X_test[:500]
            explainer = shap.TreeExplainer(models["XGBoost"])
            shap_values = explainer.shap_values(sample)
            shap.summary_plot(shap_values, sample, show=False)
            shap_summary = report_dir / "mlbfd_mega_shap_summary.png"
            plt.tight_layout()
            plt.savefig(shap_summary, dpi=130)
            plt.close()
    except Exception as exc:
        logger.info("SHAP skipped: %s", exc)

    results_payload = {
        "generated_at": datetime.now().isoformat(),
        "metrics": metrics,
        "dataset_stats": processed_data.dataset_stats,
        "feature_count": len(processed_data.feature_names),
        "feature_names": processed_data.feature_names,
    }
    with open(model_dir / f"{config.model_prefix}results.pkl", "wb") as fh:
        pickle.dump(results_payload, fh)
    with open(model_dir / f"{config.model_prefix}feature_names.pkl", "wb") as fh:
        pickle.dump(processed_data.feature_names, fh)
    with open(model_dir / f"{config.model_prefix}scaler.pkl", "wb") as fh:
        pickle.dump(processed_data.scaler, fh)

    html_path = report_dir / "mlbfd_mega_training_report.html"
    html = [
        "<html><head><title>MLBFD Automated Training Report</title></head><body>",
        "<h1>MLBFD Automated Training Report</h1>",
        f"<p>Generated: {datetime.now().isoformat()}</p>",
        "<h2>Dataset Statistics</h2>",
        "<pre>",
        json.dumps(processed_data.dataset_stats, indent=2),
        "</pre>",
        "<h2>Metrics</h2>",
        "<pre>",
        json.dumps(metrics, indent=2),
        "</pre>",
    ]
    html.append("<h2>Generated Charts</h2>")
    for chart in [
        "mlbfd_mega_roc_curves.png",
        "mlbfd_mega_precision_recall.png",
        "mlbfd_mega_model_comparison.png",
        "mlbfd_mega_confusion_matrices.png",
        "mlbfd_mega_xgb_importance.png",
        "mlbfd_mega_nn_history.png",
        "mlbfd_mega_lstm_history.png",
        "mlbfd_mega_shap_summary.png",
    ]:
        if (report_dir / chart).exists():
            html.append(f"<div><h4>{chart}</h4><img src='{chart}' style='max-width:900px'/></div>")
    html.append("</body></html>")
    html_path.write_text("\n".join(html), encoding="utf-8")
    visuals = [str(roc_path), str(pr_path), str(comparison_path)]
    cm_path = report_dir / "mlbfd_mega_confusion_matrices.png"
    if cm_path.exists():
        visuals.append(str(cm_path))
    return {"results_payload": results_payload, "report_path": str(html_path), "visualizations": visuals}
