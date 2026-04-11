"""
test_predictor_integration.py — Phase 11 Integration Tests for predictor.py

Tests the full prediction pipeline including:
- Model loading from disk
- Feature vector construction
- Ensemble inference
- Risk score aggregation
- Prediction output schema validation

Run from the MLBFD_Phase4 directory:
    python -m pytest test_predictor_integration.py -v
    python test_predictor_integration.py          (no pytest required)
"""

from __future__ import annotations

import os
import sys
import pickle
import unittest

import numpy as np

# Ensure the Phase4 directory is on the path so modules resolve
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_txn(**overrides) -> dict:
    """Return a minimal valid transaction dict with sensible defaults."""
    base = {
        "txn_id": "TEST_TXN_001",
        "user_id": "user_test_001",
        "payer_upi": "test@upi",
        "payee_upi": "merchant@upi",
        "payee_name": "Test Merchant",
        "amount": 5000.0,
        "txn_type": "TRANSFER",
        "hour": 14,
        "balance_before": 50000.0,
        "balance_after": 45000.0,
        "is_new_payee": 0,
        "is_known_device": 1,
        "device_id": "device_001",
        "latitude": 12.9716,
        "longitude": 77.5946,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Test: model artifact loading
# ---------------------------------------------------------------------------

class TestModelArtifacts(unittest.TestCase):
    """Verify that all expected model .pkl files exist and load correctly."""

    MODEL_DIR = os.path.join(HERE, "models")

    EXPECTED_FILES = [
        "mlbfd_mega_xgboost_model.pkl",
        "mlbfd_mega_random_forest_model.pkl",
        "mlbfd_mega_logistic_regression_model.pkl",
        "mlbfd_mega_isolation_forest_model.pkl",
        "mlbfd_mega_scaler.pkl",
        "mlbfd_mega_feature_names.pkl",
        "mlbfd_mega_results.pkl",
        "mlbfd_mega_dataset_info.pkl",
    ]

    def test_model_files_exist(self):
        for fname in self.EXPECTED_FILES:
            path = os.path.join(self.MODEL_DIR, fname)
            self.assertTrue(
                os.path.exists(path),
                msg=f"Model artifact missing: {path}",
            )

    def test_model_files_loadable(self):
        for fname in self.EXPECTED_FILES:
            path = os.path.join(self.MODEL_DIR, fname)
            if not os.path.exists(path):
                self.skipTest(f"File not found: {path}")
            with open(path, "rb") as fh:
                obj = pickle.load(fh)
            self.assertIsNotNone(obj, msg=f"Failed to load: {fname}")

    def test_feature_names_count(self):
        path = os.path.join(self.MODEL_DIR, "mlbfd_mega_feature_names.pkl")
        if not os.path.exists(path):
            self.skipTest("feature_names not found")
        with open(path, "rb") as fh:
            names = pickle.load(fh)
        self.assertIsInstance(names, list)
        self.assertGreaterEqual(len(names), 50,
                                msg="Expected at least 50 features")

    def test_scaler_transform(self):
        scaler_path = os.path.join(self.MODEL_DIR, "mlbfd_mega_scaler.pkl")
        fn_path = os.path.join(self.MODEL_DIR, "mlbfd_mega_feature_names.pkl")
        if not os.path.exists(scaler_path) or not os.path.exists(fn_path):
            self.skipTest("Scaler or feature names not found")
        with open(scaler_path, "rb") as fh:
            scaler = pickle.load(fh)
        with open(fn_path, "rb") as fh:
            feature_names = pickle.load(fh)
        n_feat = len(feature_names)
        dummy = np.zeros((1, n_feat))
        transformed = scaler.transform(dummy)
        self.assertEqual(transformed.shape, (1, n_feat))

    def test_results_pkl_schema(self):
        path = os.path.join(self.MODEL_DIR, "mlbfd_mega_results.pkl")
        if not os.path.exists(path):
            self.skipTest("results pkl not found")
        with open(path, "rb") as fh:
            res = pickle.load(fh)
        self.assertIsInstance(res, dict)
        for model_name, metrics in res.items():
            self.assertIsInstance(metrics, dict, msg=f"Bad results entry for {model_name}")
            for metric in ("accuracy", "precision", "recall", "f1", "auc"):
                self.assertIn(metric, metrics,
                              msg=f"Missing metric '{metric}' for {model_name}")

    def test_dataset_info_schema(self):
        path = os.path.join(self.MODEL_DIR, "mlbfd_mega_dataset_info.pkl")
        if not os.path.exists(path):
            self.skipTest("dataset_info pkl not found")
        with open(path, "rb") as fh:
            info = pickle.load(fh)
        for key in ("total_rows", "total_features", "feature_names",
                    "best_model", "best_auc", "models_trained"):
            self.assertIn(key, info, msg=f"Missing key '{key}' in dataset_info")


# ---------------------------------------------------------------------------
# Test: ensemble prediction
# ---------------------------------------------------------------------------

class TestEnsemblePrediction(unittest.TestCase):
    """Smoke-test the _run_ensemble function from predictor.py."""

    def setUp(self):
        """Load predictor module and initialise models."""
        try:
            import predictor as pred
            pred._load_models()
            self.pred = pred
            self.models_available = bool(pred._models)
        except Exception as exc:
            self.pred = None
            self.models_available = False
            self._skip_reason = str(exc)

    def _skip_if_no_models(self):
        if not self.models_available:
            reason = getattr(self, "_skip_reason", "models not available")
            self.skipTest(f"Skipping — predictor models unavailable: {reason}")

    def test_ensemble_returns_dict(self):
        self._skip_if_no_models()
        import pandas as pd
        feature_names = self.pred._feature_names
        df = pd.DataFrame([{f: 0.0 for f in feature_names}])[feature_names]
        result = self.pred._run_ensemble(df)
        self.assertIsInstance(result, dict)
        self.assertIn("ensemble_prob", result)
        self.assertIn("votes", result)

    def test_ensemble_prob_range(self):
        self._skip_if_no_models()
        import pandas as pd
        feature_names = self.pred._feature_names
        for amount in [100, 5000, 75000]:
            df = pd.DataFrame([{f: 0.0 for f in feature_names}])[feature_names]
            df.at[0, "amount"] = float(amount)
            df.at[0, "Amount_Log"] = np.log1p(amount)
            df.at[0, "Amount_Scaled"] = min(amount / 100_000, 10.0)
            result = self.pred._run_ensemble(df)
            prob = result["ensemble_prob"]
            self.assertGreaterEqual(prob, 0.0, msg=f"prob < 0 for amount={amount}")
            self.assertLessEqual(prob, 1.0, msg=f"prob > 1 for amount={amount}")

    def test_ensemble_no_crash_missing_models(self):
        self._skip_if_no_models()
        import pandas as pd
        # Test with empty models dict (graceful degradation)
        original = self.pred._models.copy()
        self.pred._models = {}
        try:
            feature_names = self.pred._feature_names
            df = pd.DataFrame([{f: 0.0 for f in feature_names}])[feature_names]
            result = self.pred._run_ensemble(df)
            self.assertEqual(result["ensemble_prob"], 0.5,
                             msg="Expected neutral fallback when no models")
        finally:
            self.pred._models = original


# ---------------------------------------------------------------------------
# Test: feature builder
# ---------------------------------------------------------------------------

class TestFeatureBuilder(unittest.TestCase):
    """Test the _build_feature_df function in predictor.py."""

    def setUp(self):
        try:
            import predictor as pred
            pred._load_models()
            self.pred = pred
            self.available = bool(pred._feature_names)
        except Exception:
            self.pred = None
            self.available = False

    def _skip_if_unavailable(self):
        if not self.available:
            self.skipTest("predictor not importable or feature_names empty")

    def test_build_feature_df_shape(self):
        self._skip_if_unavailable()
        txn = _make_txn()
        df = self.pred._build_feature_df(txn)
        n_feat = len(self.pred._feature_names)
        self.assertEqual(df.shape, (1, n_feat))

    def test_build_feature_df_columns(self):
        self._skip_if_unavailable()
        txn = _make_txn()
        df = self.pred._build_feature_df(txn)
        self.assertEqual(list(df.columns), self.pred._feature_names)

    def test_feature_amount_log(self):
        self._skip_if_unavailable()
        amount = 10000.0
        txn = _make_txn(amount=amount)
        df = self.pred._build_feature_df(txn)
        if "Amount_Log" in df.columns:
            expected = np.log1p(amount)
            self.assertAlmostEqual(df.at[0, "Amount_Log"], expected, places=4)

    def test_feature_is_night_flag(self):
        self._skip_if_unavailable()
        txn_night = _make_txn(hour=2)
        txn_day = _make_txn(hour=14)
        if "is_night" not in self.pred._feature_names:
            self.skipTest("is_night not in feature names")
        df_n = self.pred._build_feature_df(txn_night)
        df_d = self.pred._build_feature_df(txn_day)
        self.assertEqual(df_n.at[0, "is_night"], 1.0)
        self.assertEqual(df_d.at[0, "is_night"], 0.0)

    def test_feature_balance_change(self):
        self._skip_if_unavailable()
        txn = _make_txn(balance_before=50000.0, balance_after=44000.0)
        df = self.pred._build_feature_df(txn)
        if "balance_change" in df.columns:
            self.assertAlmostEqual(df.at[0, "balance_change"], 6000.0, places=1)


# ---------------------------------------------------------------------------
# Test: full predict() end-to-end
# ---------------------------------------------------------------------------

class TestPredictEndToEnd(unittest.TestCase):
    """Run the full predict() function and validate the output schema."""

    REQUIRED_KEYS = [
        "txn_id", "user_id", "prediction", "risk_score", "verdict",
        "explanation", "ubts_score", "wts_score", "website_score",
        "lstm_prob", "ensemble_prob", "model_votes", "fraud_votes",
        "total_votes", "shap_reasons", "layer_detail",
    ]

    def setUp(self):
        try:
            import db
            db.init_db()
            import predictor as pred
            pred._load_models()
            self.pred = pred
            self.available = True
        except Exception as exc:
            self.pred = None
            self.available = False
            self._skip_reason = str(exc)

    def _skip_if_unavailable(self):
        if not self.available:
            reason = getattr(self, "_skip_reason", "predictor unavailable")
            self.skipTest(f"Skipping — {reason}")

    def test_predict_returns_dict(self):
        self._skip_if_unavailable()
        result = self.pred.predict(_make_txn())
        self.assertIsInstance(result, dict)

    def test_predict_required_keys(self):
        self._skip_if_unavailable()
        result = self.pred.predict(_make_txn())
        for key in self.REQUIRED_KEYS:
            self.assertIn(key, result, msg=f"Missing key '{key}' in prediction result")

    def test_risk_score_range(self):
        self._skip_if_unavailable()
        result = self.pred.predict(_make_txn(amount=500.0))
        score = result["risk_score"]
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 100.0)

    def test_high_risk_transaction(self):
        """A night-time, high-amount, new-payee, unknown-device transfer
        should produce a higher risk score than a routine safe transaction."""
        self._skip_if_unavailable()
        safe_txn = _make_txn(
            amount=200.0, hour=11, is_new_payee=0, is_known_device=1
        )
        risky_txn = _make_txn(
            amount=95000.0, hour=2, is_new_payee=1, is_known_device=0,
            txn_type="TRANSFER",
        )
        safe_result = self.pred.predict(safe_txn)
        risky_result = self.pred.predict(risky_txn)
        self.assertGreater(
            risky_result["risk_score"],
            safe_result["risk_score"],
            msg="High-risk transaction should have higher risk_score than safe one",
        )

    def test_verdict_values(self):
        self._skip_if_unavailable()
        result = self.pred.predict(_make_txn())
        valid_verdicts = {"FRAUD DETECTED", "SUSPICIOUS", "SAFE TRANSACTION"}
        self.assertIn(result["verdict"], valid_verdicts)

    def test_ensemble_prob_populated(self):
        self._skip_if_unavailable()
        result = self.pred.predict(_make_txn())
        self.assertGreaterEqual(result["ensemble_prob"], 0.0)
        self.assertLessEqual(result["ensemble_prob"], 1.0)

    def test_predict_suspicious_url(self):
        """A transaction with a suspicious phishing-like URL should
        have a higher website_score risk contribution."""
        self._skip_if_unavailable()
        safe = self.pred.predict(_make_txn(payee_name=""))
        suspicious = self.pred.predict(
            _make_txn(payee_name="http://secure-upi-login-verify.xyz/kyc")
        )
        self.assertLess(
            suspicious["website_score"],
            safe.get("website_score", 100),
            msg="Suspicious URL should lower website_score",
        )

    def test_layer_detail_keys(self):
        self._skip_if_unavailable()
        result = self.pred.predict(_make_txn())
        ld = result["layer_detail"]
        for layer in ("ubts", "wts", "website_trust", "lstm", "ensemble"):
            self.assertIn(layer, ld, msg=f"Missing layer '{layer}' in layer_detail")


# ---------------------------------------------------------------------------
# Test: Phase 11 model performance
# ---------------------------------------------------------------------------

class TestPhase11ModelPerformance(unittest.TestCase):
    """Verify that retrained models meet Phase 11 success criteria."""

    MODEL_DIR = os.path.join(HERE, "models")

    def test_ensemble_meets_targets(self):
        """Ensemble must satisfy Phase 11 success criteria."""
        path = os.path.join(self.MODEL_DIR, "mlbfd_mega_results.pkl")
        if not os.path.exists(path):
            self.skipTest("results pkl not found")
        with open(path, "rb") as fh:
            results = pickle.load(fh)

        if "Ensemble" not in results:
            self.skipTest("Ensemble results not in pkl (may be single-model run)")

        ens = results["Ensemble"]
        self.assertGreaterEqual(ens.get("f1", 0), 0.92,
                                msg=f"Ensemble F1={ens.get('f1', 0):.4f} < 0.92")
        self.assertGreaterEqual(ens.get("precision", 0), 0.90,
                                msg=f"Ensemble Precision={ens.get('precision', 0):.4f} < 0.90")
        self.assertGreaterEqual(ens.get("recall", 0), 0.85,
                                msg=f"Ensemble Recall={ens.get('recall', 0):.4f} < 0.85")

    def test_xgboost_auc_acceptable(self):
        """XGBoost AUC should be ≥ 0.95 (Phase 2B baseline was 0.9734)."""
        path = os.path.join(self.MODEL_DIR, "mlbfd_mega_results.pkl")
        if not os.path.exists(path):
            self.skipTest("results pkl not found")
        with open(path, "rb") as fh:
            results = pickle.load(fh)
        if "XGBoost" not in results:
            self.skipTest("XGBoost results not found")
        auc = results["XGBoost"].get("auc", 0)
        self.assertGreaterEqual(auc, 0.95,
                                msg=f"XGBoost AUC={auc:.4f} dropped below 0.95")

    def test_dataset_info_phase11(self):
        """dataset_info should record Phase 11 as the training phase."""
        path = os.path.join(self.MODEL_DIR, "mlbfd_mega_dataset_info.pkl")
        if not os.path.exists(path):
            self.skipTest("dataset_info pkl not found")
        with open(path, "rb") as fh:
            info = pickle.load(fh)
        self.assertEqual(info.get("phase"), "Phase 11",
                         msg="dataset_info.phase should be 'Phase 11'")


# ---------------------------------------------------------------------------
# Test runner (no pytest required)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestModelArtifacts))
    suite.addTests(loader.loadTestsFromTestCase(TestEnsemblePrediction))
    suite.addTests(loader.loadTestsFromTestCase(TestFeatureBuilder))
    suite.addTests(loader.loadTestsFromTestCase(TestPredictEndToEnd))
    suite.addTests(loader.loadTestsFromTestCase(TestPhase11ModelPerformance))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
