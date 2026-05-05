"""
Train all fraud models and persist artifacts.
"""

from __future__ import annotations

import logging
import pickle
import time
from pathlib import Path

import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import cross_val_score

from training_config import TrainingConfig

logger = logging.getLogger("mlbfd.model_trainer")


def _to_lstm_sequences(X: np.ndarray, y: np.ndarray, seq_len: int) -> tuple[np.ndarray, np.ndarray]:
    if len(X) <= seq_len:
        return np.empty((0, seq_len, X.shape[1])), np.empty((0,))
    seq_x, seq_y = [], []
    for i in range(seq_len, len(X)):
        seq_x.append(X[i - seq_len : i])
        seq_y.append(y[i])
    return np.array(seq_x), np.array(seq_y)


def train_all_models(data: dict, config: TrainingConfig) -> dict:
    X_train = data["X_train"]
    X_test = data["X_test"]
    y_train = data["y_train"]
    y_test = data["y_test"]

    config.ensure_output_dirs()
    out = Path(config.model_output_dir)
    trained_models: dict = {}
    predictions: dict = {}
    histories: dict = {}
    training_times: dict = {}

    # 1) XGBoost
    start = time.time()
    try:
        import xgboost as xgb

        xgb_params = dict(config.model_params["xgboost"])
        xgb_params.setdefault("random_state", config.random_state)
        xgb_params.setdefault("eval_metric", "logloss")
        xgb_params.setdefault("tree_method", "hist")
        xgb_params.setdefault("n_jobs", -1)
        xgb_model = xgb.XGBClassifier(**xgb_params)
        xgb_model.fit(X_train, y_train)
        y_prob = xgb_model.predict_proba(X_test)[:, 1]
        trained_models["XGBoost"] = xgb_model
        predictions["XGBoost"] = {"y_prob": y_prob, "y_pred": (y_prob >= 0.5).astype(int)}
    except Exception as exc:  # pragma: no cover - dependency/runtime variability
        logger.warning("XGBoost training skipped: %s", exc)
    training_times["XGBoost"] = time.time() - start

    # 2) Random Forest (with CV)
    start = time.time()
    rf = RandomForestClassifier(**config.model_params["random_forest"], random_state=config.random_state)
    rf.fit(X_train, y_train)
    cv_auc = cross_val_score(rf, X_train, y_train, cv=3, scoring="roc_auc").mean()
    y_prob = rf.predict_proba(X_test)[:, 1]
    trained_models["Random Forest"] = rf
    predictions["Random Forest"] = {"y_prob": y_prob, "y_pred": (y_prob >= 0.5).astype(int), "cv_auc": cv_auc}
    training_times["Random Forest"] = time.time() - start

    # 3) Logistic Regression (with CV)
    start = time.time()
    lr = LogisticRegression(
        **config.model_params["logistic_regression"],
        random_state=config.random_state,
        class_weight="balanced",
    )
    lr.fit(X_train, y_train)
    cv_auc = cross_val_score(lr, X_train, y_train, cv=3, scoring="roc_auc").mean()
    y_prob = lr.predict_proba(X_test)[:, 1]
    trained_models["Logistic Regression"] = lr
    predictions["Logistic Regression"] = {"y_prob": y_prob, "y_pred": (y_prob >= 0.5).astype(int), "cv_auc": cv_auc}
    training_times["Logistic Regression"] = time.time() - start

    # 4) Isolation Forest
    start = time.time()
    iso = IsolationForest(**config.model_params["isolation_forest"], random_state=config.random_state)
    iso.fit(X_train)
    scores = -iso.decision_function(X_test)
    y_prob = (scores - scores.min()) / (scores.max() - scores.min() + 1e-12)
    trained_models["Isolation Forest"] = iso
    predictions["Isolation Forest"] = {"y_prob": y_prob, "y_pred": (y_prob >= 0.5).astype(int)}
    training_times["Isolation Forest"] = time.time() - start

    # 5) Neural Network (Keras)
    start = time.time()
    try:
        import tensorflow as tf
        from tensorflow.keras import Sequential
        from tensorflow.keras.layers import Dense, Dropout

        gpu_count = len(tf.config.list_physical_devices("GPU"))
        logger.info("TensorFlow detected. GPU devices: %d", gpu_count)
        nn = Sequential(
            [
                Dense(config.model_params["neural_network"]["hidden_units"][0], activation="relu", input_shape=(X_train.shape[1],)),
                Dropout(config.model_params["neural_network"]["dropout"]),
                Dense(config.model_params["neural_network"]["hidden_units"][1], activation="relu"),
                Dropout(config.model_params["neural_network"]["dropout"]),
                Dense(config.model_params["neural_network"]["hidden_units"][2], activation="relu"),
                Dense(1, activation="sigmoid"),
            ]
        )
        nn.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
        hist = nn.fit(
            X_train,
            y_train,
            validation_split=0.1,
            epochs=config.epochs,
            batch_size=config.batch_size,
            verbose=0,
        )
        y_prob = nn.predict(X_test, verbose=0).flatten()
        nn.save(out / "mlbfd_mega_neural_network_model.keras")
        trained_models["Neural Network"] = nn
        predictions["Neural Network"] = {"y_prob": y_prob, "y_pred": (y_prob >= 0.5).astype(int)}
        histories["Neural Network"] = hist.history
    except Exception as exc:  # pragma: no cover - dependency/runtime variability
        logger.warning("Neural Network training skipped: %s", exc)
    training_times["Neural Network"] = time.time() - start

    # 6) LSTM (Keras)
    start = time.time()
    try:
        from tensorflow.keras import Sequential
        from tensorflow.keras.layers import LSTM, Dense, Dropout

        X_seq_train, y_seq_train = _to_lstm_sequences(data["X_train_lstm"], y_train, config.lstm_seq_len)
        X_seq_test, y_seq_test = _to_lstm_sequences(data["X_test_lstm"], y_test, config.lstm_seq_len)
        if len(X_seq_train) > 0 and len(X_seq_test) > 0:
            lstm = Sequential(
                [
                    LSTM(config.model_params["lstm"]["units"], input_shape=(X_seq_train.shape[1], X_seq_train.shape[2])),
                    Dropout(config.model_params["lstm"]["dropout"]),
                    Dense(1, activation="sigmoid"),
                ]
            )
            lstm.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
            hist = lstm.fit(
                X_seq_train,
                y_seq_train,
                validation_split=0.1,
                epochs=config.epochs,
                batch_size=max(config.lstm_min_batch_size, config.batch_size // 2),
                verbose=0,
            )
            y_prob = lstm.predict(X_seq_test, verbose=0).flatten()
            lstm.save(out / "mlbfd_mega_lstm_model.keras")
            trained_models["LSTM"] = lstm
            predictions["LSTM"] = {
                "y_prob": y_prob,
                "y_pred": (y_prob >= 0.5).astype(int),
                "y_true_override": y_seq_test,
            }
            histories["LSTM"] = hist.history
    except Exception as exc:  # pragma: no cover - dependency/runtime variability
        logger.warning("LSTM training skipped: %s", exc)
    training_times["LSTM"] = time.time() - start

    file_map = {
        "XGBoost": "mlbfd_mega_xgboost_model.pkl",
        "Random Forest": "mlbfd_mega_random_forest_model.pkl",
        "Logistic Regression": "mlbfd_mega_logistic_regression_model.pkl",
        "Isolation Forest": "mlbfd_mega_isolation_forest_model.pkl",
    }
    for name, fname in file_map.items():
        if name in trained_models:
            with open(out / fname, "wb") as f:
                pickle.dump(trained_models[name], f)

    # Lightweight UBTS artifact for compatibility and traceability.
    ubts_payload = {
        "threshold_warning": config.threshold_warning,
        "threshold_critical": config.threshold_critical,
        "created_from": "train_all_models.py",
    }
    with open(out / "mlbfd_mega_ubts.pkl", "wb") as f:
        pickle.dump(ubts_payload, f)

    # Quick sanity metric for cache/debug
    auc_snapshot = {
        m: float(roc_auc_score(y_test if "y_true_override" not in p else p["y_true_override"], p["y_prob"]))
        for m, p in predictions.items()
        if len(p.get("y_prob", [])) > 0
    }

    return {
        "models": trained_models,
        "predictions": predictions,
        "histories": histories,
        "training_times": training_times,
        "auc_snapshot": auc_snapshot,
    }
