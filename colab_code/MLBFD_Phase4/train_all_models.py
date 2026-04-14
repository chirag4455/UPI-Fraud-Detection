"""
Entry point for complete automated all-dataset model training.
"""

from __future__ import annotations

import logging
import pickle
import time
from datetime import UTC, datetime

from data_processor import DataProcessor
from model_evaluator import evaluate_and_report
from model_trainer import train_all_models
from training_config import TrainingConfig


def _configure_logging(cfg: TrainingConfig) -> str:
    cfg.ensure_output_dirs()
    log_path = cfg.log_output_dir / "training_log.txt"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.FileHandler(log_path, mode="w", encoding="utf-8"), logging.StreamHandler()],
        force=True,
    )
    return str(log_path)


def main() -> int:
    cfg = TrainingConfig()
    log_path = _configure_logging(cfg)
    logger = logging.getLogger("mlbfd.train_all")
    start = time.time()
    logger.info("Starting automated training pipeline.")

    try:
        processor = DataProcessor(cfg)
        data_bundle = processor.process()
        logger.info(
            "Loaded and processed %d rows from %d datasets.",
            data_bundle["row_count"],
            len(data_bundle["datasets_used"]),
        )

        trainer_bundle = train_all_models(data_bundle, cfg)
        evaluator_bundle = evaluate_and_report(data_bundle, trainer_bundle, cfg)

        summary = {
            "timestamp": datetime.now(UTC).isoformat(),
            "duration_seconds": round(time.time() - start, 2),
            "datasets_used": data_bundle["datasets_used"],
            "row_count": data_bundle["row_count"],
            "fraud_count": data_bundle["fraud_count"],
            "trained_models": sorted(list(trainer_bundle["models"].keys())),
            "metrics": evaluator_bundle["metrics"],
            "report_path": evaluator_bundle["report_path"],
            "log_path": log_path,
        }
        with open(cfg.model_output_dir / "mlbfd_mega_results.pkl", "wb") as f:
            pickle.dump(summary["metrics"], f)
        with open(cfg.report_output_dir / "mlbfd_mega_training_summary.pkl", "wb") as f:
            pickle.dump(summary, f)

        logger.info("Pipeline completed successfully in %.2f seconds.", time.time() - start)
        logger.info("Training report: %s", summary["report_path"])
        return 0
    except Exception as exc:
        logger.exception("Training pipeline failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
