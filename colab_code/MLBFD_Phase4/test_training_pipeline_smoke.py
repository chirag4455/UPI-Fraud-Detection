from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from data_processor import DataProcessor
from model_evaluator import evaluate_and_report
from model_trainer import train_all_models
from training_config import TrainingConfig


class TestTrainingPipelineSmoke(unittest.TestCase):
    def test_end_to_end_small_dataset(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            data_dir = root / "Tier1"
            data_dir.mkdir(parents=True)
            out_models = root / "models"
            out_logs = root / "logs"
            out_reports = root / "reports"

            n = 120
            df = pd.DataFrame(
                {
                    "amount": np.linspace(100, 90000, n),
                    "hour": np.random.randint(0, 24, n),
                    "oldbalanceOrg": np.random.uniform(1000, 100000, n),
                    "newbalanceOrig": np.random.uniform(100, 80000, n),
                    "oldbalanceDest": np.random.uniform(100, 100000, n),
                    "newbalanceDest": np.random.uniform(100, 120000, n),
                    "type": np.random.choice(["TRANSFER", "CASH_OUT", "PAYMENT"], n),
                    "isFraud": np.array([0] * 90 + [1] * 30),
                }
            )
            df.to_csv(data_dir / "train.csv", index=False)

            cfg = TrainingConfig(
                dataset_roots=[data_dir],
                model_output_dir=out_models,
                log_output_dir=out_logs,
                report_output_dir=out_reports,
                epochs=1,
                batch_size=32,
                lstm_seq_len=5,
            )

            data_bundle = DataProcessor(cfg).process()
            self.assertEqual(len(data_bundle["feature_names"]), 57)
            self.assertTrue((out_models / "mlbfd_mega_scaler.pkl").exists())
            self.assertTrue((out_models / "mlbfd_mega_feature_names.pkl").exists())

            trainer_bundle = train_all_models(data_bundle, cfg)
            self.assertIn("Random Forest", trainer_bundle["models"])
            self.assertIn("Logistic Regression", trainer_bundle["models"])
            self.assertIn("Isolation Forest", trainer_bundle["models"])
            self.assertTrue((out_models / "mlbfd_mega_random_forest_model.pkl").exists())
            self.assertTrue((out_models / "mlbfd_mega_logistic_regression_model.pkl").exists())
            self.assertTrue((out_models / "mlbfd_mega_isolation_forest_model.pkl").exists())
            self.assertTrue((out_models / "mlbfd_mega_ubts.pkl").exists())

            eval_bundle = evaluate_and_report(data_bundle, trainer_bundle, cfg)
            self.assertTrue(Path(eval_bundle["report_path"]).exists())
            self.assertTrue((out_reports / "mlbfd_mega_confusion_matrices.png").exists())
            self.assertTrue((out_reports / "mlbfd_mega_roc_curves.png").exists())
            self.assertTrue((out_reports / "mlbfd_mega_precision_recall.png").exists())
            self.assertTrue((out_models / "mlbfd_mega_results.pkl").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
