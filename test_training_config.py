"""Lightweight tests for automated training pipeline configuration."""

from __future__ import annotations

import unittest

from training_config import REQUIRED_API_FEATURES, TrainingConfig


class TestTrainingConfig(unittest.TestCase):
    def test_required_feature_count(self):
        self.assertEqual(len(REQUIRED_API_FEATURES), 57)

    def test_required_feature_uniqueness(self):
        self.assertEqual(len(REQUIRED_API_FEATURES), len(set(REQUIRED_API_FEATURES)))

    def test_output_dirs_defined(self):
        cfg = TrainingConfig()
        self.assertTrue(cfg.output_models_dir)
        self.assertTrue(cfg.output_logs_dir)
        self.assertTrue(cfg.output_reports_dir)


if __name__ == "__main__":
    unittest.main(verbosity=2)
