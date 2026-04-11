# Model Artifact Registry — MLBFD Phase 11

> **Multi-Layer Behavioral Fraud Detection System**
> Version history, file manifest, and integration notes for all
> serialized model artifacts stored in this directory.

---

## Directory Layout

```
models/
├── mlbfd_mega_xgboost_model.pkl             # XGBoost classifier (primary)
├── mlbfd_mega_random_forest_model.pkl       # Random Forest classifier
├── mlbfd_mega_logistic_regression_model.pkl # Calibrated Logistic Regression
├── mlbfd_mega_isolation_forest_model.pkl    # Isolation Forest anomaly detector
├── mlbfd_mega_neural_network_model.keras    # Neural Network (Keras/TensorFlow)
├── mlbfd_mega_lstm_model.keras              # LSTM sequence model (Keras/TF)
├── mlbfd_mega_scaler.pkl                    # StandardScaler fitted on training data
├── mlbfd_mega_lstm_scaler.pkl               # MinMaxScaler for LSTM sequences
├── mlbfd_mega_feature_names.pkl             # Ordered list of 108 feature names
├── mlbfd_mega_results.pkl                   # Per-model evaluation metrics dict
├── mlbfd_mega_dataset_info.pkl              # Dataset metadata + training config
│
├── mlbfd_mega_roc_curves.png                # ROC curves (all models)
├── mlbfd_mega_precision_recall.png          # Precision-Recall curves
├── mlbfd_mega_confusion_matrices.png        # Confusion matrices per model
├── mlbfd_mega_model_comparison.png          # Bar chart: Acc / P / R / F1 / AUC
├── mlbfd_mega_xgb_importance.png            # XGBoost top-20 feature importances
├── mlbfd_mega_dataset_composition.png       # Dataset source breakdown
├── mlbfd_mega_nn_history.png                # Neural Network training curves
├── mlbfd_mega_lstm_history.png              # LSTM training curves
├── mlbfd_mega_shap_bar.png                  # SHAP bar chart
└── mlbfd_mega_shap_summary.png              # SHAP beeswarm summary plot
```

---

## Version History

| Version | Phase       | Date       | Highlight |
|---------|-------------|------------|-----------|
| v1.0    | Phase 2B    | 2026-03-06 | Initial mega-dataset training (2.3 M rows, 5 sources) |
| v2.0    | **Phase 11** | **2026-04-11** | Hyperparameter re-tuning, threshold optimisation, ensemble weighting |

---

## Phase 11 Model Specifications

### XGBoost (`mlbfd_mega_xgboost_model.pkl`)

| Parameter | Phase 2B | Phase 11 |
|-----------|----------|----------|
| `n_estimators` | 300 | 400 |
| `max_depth` | 8 | 7 |
| `learning_rate` | 0.10 | 0.08 |
| `subsample` | 0.80 | 0.85 |
| `colsample_bytree` | 0.80 | 0.75 |
| `min_child_weight` | — | 5 |
| `gamma` | — | 0.15 |
| `reg_alpha` | — | 0.10 |
| `reg_lambda` | 1.0 | 1.5 |
| `scale_pos_weight` | 1 | auto (fraud-rate based) |
| `eval_metric` | logloss | aucpr |
| Early stopping | ✗ | ✅ (20 rounds) |
| `tree_method` | hist | hist |

### Random Forest (`mlbfd_mega_random_forest_model.pkl`)

| Parameter | Phase 2B | Phase 11 |
|-----------|----------|----------|
| `n_estimators` | 200 | 300 |
| `max_depth` | 15 | 20 |
| `min_samples_split` | 10 | 4 |
| `min_samples_leaf` | 5 | 2 |
| `class_weight` | — | `balanced` |
| `oob_score` | ✗ | ✅ |

### Logistic Regression (`mlbfd_mega_logistic_regression_model.pkl`)

| Parameter | Phase 2B | Phase 11 |
|-----------|----------|----------|
| `C` | 1.0 | 0.5 |
| `penalty` | default | l2 |
| `class_weight` | — | `balanced` |
| `solver` | default | saga |
| `max_iter` | 1000 | 2000 |
| Calibration | ✗ | ✅ `CalibratedClassifierCV` (isotonic, cv=3) |

### Isolation Forest (`mlbfd_mega_isolation_forest_model.pkl`)

| Parameter | Phase 2B | Phase 11 |
|-----------|----------|----------|
| `n_estimators` | 200 | 300 |
| `contamination` | 0.10 | auto (1.2 × fraud rate) |
| `max_features` | 1.0 | 0.8 |

### Neural Network (`mlbfd_mega_neural_network_model.keras`)

| Aspect | Phase 2B | Phase 11 |
|--------|----------|----------|
| Architecture | 256→128→64→32→1 | 512→256→128→64→32→1 |
| Batch Norm | per layer | per Dense layer |
| Dropout | 0.4→0.3→0.2 | 0.4→0.35→0.25→0.20 |
| Optimizer | Adam | Adam (lr=0.001, ReduceLROnPlateau) |
| Epochs | 50 | 60 (EarlyStopping patience=8) |
| Class weighting | ✗ | ✅ (scale_pos_weight) |

---

## Ensemble Configuration (Phase 11)

| Model | Weight |
|-------|--------|
| XGBoost | **0.35** |
| Random Forest | 0.25 |
| Neural Network | 0.15 |
| Logistic Regression | 0.15 |
| Isolation Forest | 0.10 |

**Threshold strategy:** For each model, an optimal classification threshold
is found by maximising recall subject to `precision ≥ 0.90`.  The ensemble
probability is a weighted average of all model outputs; the final ensemble
threshold is found by the same strategy.

---

## Feature Schema

- **Total features:** 108
- **Stored in:** `mlbfd_mega_feature_names.pkl`
- **Categories:**

| Category | Features |
|----------|----------|
| Amount & balance | `amount`, `balance_before/after`, `balance_change*`, `dest_balance_*`, `Amount_Log`, `Amount_Scaled` |
| Transaction type | `is_cash_out`, `is_transfer`, `is_payment`, `is_debit`, `is_cash_in` |
| Behavioural | `is_new_payee`, `is_known_device`, `is_night`, `is_weekend`, `is_business_hours` |
| Velocity | `velocity_6h`, `velocity_24h`, `transactions_last_hour`, `transactions_last_24h` |
| Risk composite | `velocity_risk`, `new_payee_night`, `high_amount_new_device`, `heuristic_risk_score` |
| PCA (IEEE-CIS) | `V1`–`V28` |
| IEEE-CIS extended | `count_c*`, `delta_d*`, `card_*`, `address_code`, etc. |
| UPI-specific | `vpa_age_days`, `payment_app`, `payment_type`, `is_collect_request`, `is_vpn` |
| Geography | `state`, `distance_from_home_km`, `device_location_risk` |

---

## Loading Models in Code

```python
import pickle, os

MODEL_DIR = "models"

# Scaler and feature names (always load first)
with open(os.path.join(MODEL_DIR, "mlbfd_mega_scaler.pkl"), "rb") as f:
    scaler = pickle.load(f)
with open(os.path.join(MODEL_DIR, "mlbfd_mega_feature_names.pkl"), "rb") as f:
    feature_names = pickle.load(f)

# Sklearn / XGBoost models
model_files = {
    "XGBoost":             "mlbfd_mega_xgboost_model.pkl",
    "Random Forest":       "mlbfd_mega_random_forest_model.pkl",
    "Logistic Regression": "mlbfd_mega_logistic_regression_model.pkl",
    "Isolation Forest":    "mlbfd_mega_isolation_forest_model.pkl",
}
models = {}
for name, fname in model_files.items():
    with open(os.path.join(MODEL_DIR, fname), "rb") as f:
        models[name] = pickle.load(f)

# Keras models (requires TensorFlow)
import tensorflow as tf
models["Neural Network"] = tf.keras.models.load_model(
    os.path.join(MODEL_DIR, "mlbfd_mega_neural_network_model.keras"))
models["LSTM"] = tf.keras.models.load_model(
    os.path.join(MODEL_DIR, "mlbfd_mega_lstm_model.keras"))

# Inference example
import pandas as pd
import numpy as np

feature_dict = {f: 0.0 for f in feature_names}
feature_dict["amount"] = 5000.0
feature_dict["is_new_payee"] = 1.0
feature_dict["is_night"] = 1.0

X = pd.DataFrame([feature_dict])[feature_names].values.astype(np.float32)
X_scaled = scaler.transform(X)

xgb_prob = models["XGBoost"].predict_proba(X_scaled)[0][1]
print(f"XGBoost fraud probability: {xgb_prob:.4f}")
```

---

## Retraining (Phase 11)

```bash
# Full retraining (requires original datasets or will use synthetic data)
cd colab_code/MLBFD_Phase4
python train_phase11.py

# Quick smoke-test (50 k synthetic rows, ~2 minutes)
python train_phase11.py --quick

# Custom output directory
python train_phase11.py --output-dir /path/to/models
```

The retraining script (`train_phase11.py`) will:
1. Generate / load training data
2. Re-fit `StandardScaler` and overwrite `mlbfd_mega_scaler.pkl`
3. Train all models with Phase 11 hyperparameters
4. Save updated `.pkl` files
5. Regenerate all visualisation `.png` files
6. Print a success-criteria summary

---

## Integration Tests

```bash
cd colab_code/MLBFD_Phase4
python test_predictor_integration.py       # built-in runner
python -m pytest test_predictor_integration.py -v   # pytest
```

25 tests covering model artifact loading, feature construction,
ensemble inference, risk aggregation, and Phase 11 performance targets.

---

## Notes

- The `.keras` Keras models require **TensorFlow ≥ 2.13**.
  The system gracefully degrades to 4-model ensemble when TensorFlow
  is not installed.
- All `.pkl` files use Python's built-in `pickle` (protocol 4).  They
  are **not** cross-version safe — retrain if upgrading scikit-learn or
  XGBoost major versions.
- The `CalibratedClassifierCV` wrapper around Logistic Regression means
  the raw estimator is no longer directly accessible; use
  `model.predict_proba()` as normal.
