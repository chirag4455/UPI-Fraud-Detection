"""Single-entry automated model training pipeline.

Run:
    python train_all_models.py
"""

from __future__ import annotations

import json
import logging
import pickle
import traceback
from datetime import datetime
from pathlib import Path

from data_processor import load_and_preprocess_data
from model_evaluator import evaluate_and_report
from model_trainer import train_all_models
from training_config import TrainingConfig


def _setup_logger(config: TrainingConfig) -> logging.Logger:
    config.ensure_output_dirs()
    log_path = Path(config.output_logs_dir) / f"train_all_models_{config.timestamp}.log"
    logger = logging.getLogger("mlbfd.pipeline")
    logger.setLevel(logging.INFO)
    logger.handlers = []
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)
    logger.info("Training log path: %s", log_path)
    return logger


def _memory_snapshot() -> dict:
    try:
        import psutil
        vm = psutil.virtual_memory()
        return {"total_gb": round(vm.total / (1024 ** 3), 2), "used_gb": round(vm.used / (1024 ** 3), 2), "percent": vm.percent}
    except Exception:
        return {}


def main() -> int:
    config = TrainingConfig()
    logger = _setup_logger(config)
    logger.info("=== MLBFD Automated Training Pipeline Started ===")
    logger.info("Dataset roots detected: %s", config.discover_existing_dataset_roots())
    logger.info("Memory at start: %s", _memory_snapshot())
    try:
        logger.info("[1/5] Loading + preprocessing data")
        processed = load_and_preprocess_data(config)
        logger.info("Data ready (train=%d, test=%d, features=%d)", len(processed.y_train), len(processed.y_test), len(processed.feature_names))

        logger.info("[2/5] Training all 6 models")
        models, metrics, history = train_all_models(processed, config)
        logger.info("Models trained: %s", list(models.keys()))

        logger.info("[3/5] Evaluating and building reports")
        eval_output = evaluate_and_report(config, processed, models, metrics, history)

        logger.info("[4/5] Writing registry + metadata")
        model_dir = Path(config.output_models_dir)
        nn_ext = metrics.get("Neural Network", {}).get("save_extension", ".keras")
        lstm_ext = metrics.get("LSTM", {}).get("save_extension", ".keras")
        registry = {
            "generated_at": datetime.now().isoformat(),
            "version": config.timestamp,
            "model_prefix": config.model_prefix,
            "models": {
                "xgboost": f"{config.model_prefix}xgboost_model.pkl",
                "random_forest": f"{config.model_prefix}random_forest_model.pkl",
                "logistic_regression": f"{config.model_prefix}logistic_regression_model.pkl",
                "isolation_forest": f"{config.model_prefix}isolation_forest_model.pkl",
                "neural_network": f"{config.model_prefix}neural_network_model{nn_ext}",
                "lstm": f"{config.model_prefix}lstm_model{lstm_ext}",
            },
            "supporting": {
                "scaler": f"{config.model_prefix}scaler.pkl",
                "lstm_scaler": f"{config.model_prefix}lstm_scaler.pkl",
                "feature_names": f"{config.model_prefix}feature_names.pkl",
                "ubts": f"{config.model_prefix}ubts.pkl",
                "results": f"{config.model_prefix}results.pkl",
            },
            "report": eval_output.get("report_path"),
        }
        (model_dir / "model_registry.json").write_text(json.dumps(registry, indent=2), encoding="utf-8")
        with open(model_dir / "training_metadata.pkl", "wb") as fh:
            pickle.dump(registry, fh)
        (model_dir / "README_AUTOMATED_TRAINING.md").write_text(
            "\n".join([
                "# MLBFD Automated Training Artifacts",
                "",
                f"Generated at: {registry['generated_at']}",
                f"Version: {registry['version']}",
                "",
                "Outputs:",
                "- 6 trained models (XGBoost, RF, LR, Isolation Forest, NN, LSTM)",
                "- mlbfd_mega_scaler.pkl",
                "- mlbfd_mega_lstm_scaler.pkl",
                "- mlbfd_mega_feature_names.pkl",
                "- mlbfd_mega_ubts.pkl",
                "- mlbfd_mega_results.pkl",
                "- model_registry.json",
                "- HTML report + PNG visualizations in training_reports/",
            ]),
            encoding="utf-8",
        )

        logger.info("[5/5] Completed")
        logger.info("Memory at end: %s", _memory_snapshot())
        return 0
    except Exception as exc:
        logger.error("Pipeline failed: %s", exc)
        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
