"""Model training module for MLBFD automated pipeline."""

from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import Dict, Tuple

from training_config import TrainingConfig

logger = logging.getLogger("mlbfd.model_trainer")


def _evaluate_binary(y_true, y_pred, y_prob):
    from sklearn.metrics import accuracy_score, average_precision_score, f1_score, precision_score, recall_score, roc_auc_score
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, y_prob)) if len(set(y_true)) > 1 else 0.5,
        "pr_auc": float(average_precision_score(y_true, y_prob)),
    }


def train_all_models(processed_data, config: TrainingConfig) -> Tuple[Dict[str, object], Dict[str, Dict], Dict]:
    import numpy as np
    from sklearn.ensemble import IsolationForest, RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import classification_report, confusion_matrix
    from sklearn.model_selection import cross_val_score
    from sklearn.neural_network import MLPClassifier
    from sklearn.preprocessing import MinMaxScaler

    X_train, X_test = processed_data.X_train, processed_data.X_test
    y_train, y_test = processed_data.y_train, processed_data.y_test

    models: Dict[str, object] = {}
    metrics: Dict[str, Dict] = {}
    history: Dict = {}

    # XGBoost (fallback if unavailable)
    try:
        import xgboost as xgb
        xgb_model = xgb.XGBClassifier(random_state=config.random_state, n_jobs=-1, **config.model_hyperparameters["xgboost"])
    except Exception:
        logger.warning("xgboost unavailable; using RandomForest fallback in XGBoost slot")
        xgb_model = RandomForestClassifier(random_state=config.random_state, n_estimators=180, class_weight="balanced", n_jobs=-1)
    xgb_model.fit(X_train, y_train)
    xgb_prob = xgb_model.predict_proba(X_test)[:, 1]
    xgb_pred = (xgb_prob >= 0.5).astype(int)
    models["XGBoost"] = xgb_model
    metrics["XGBoost"] = {**_evaluate_binary(y_test, xgb_pred, xgb_prob), "confusion_matrix": confusion_matrix(y_test, xgb_pred).tolist(), "classification_report": classification_report(y_test, xgb_pred, output_dict=True, zero_division=0)}
    try:
        metrics["XGBoost"]["cv_f1_mean"] = float(cross_val_score(xgb_model, X_train, y_train, cv=3, scoring="f1", n_jobs=1).mean())
    except Exception:
        pass

    rf_model = RandomForestClassifier(random_state=config.random_state, n_jobs=-1, **config.model_hyperparameters["random_forest"])
    rf_model.fit(X_train, y_train)
    rf_prob = rf_model.predict_proba(X_test)[:, 1]
    rf_pred = (rf_prob >= 0.5).astype(int)
    models["Random Forest"] = rf_model
    metrics["Random Forest"] = {**_evaluate_binary(y_test, rf_pred, rf_prob), "confusion_matrix": confusion_matrix(y_test, rf_pred).tolist(), "classification_report": classification_report(y_test, rf_pred, output_dict=True, zero_division=0)}
    try:
        metrics["Random Forest"]["cv_f1_mean"] = float(cross_val_score(rf_model, X_train, y_train, cv=3, scoring="f1", n_jobs=1).mean())
    except Exception:
        pass

    lr_model = LogisticRegression(random_state=config.random_state, n_jobs=-1, **config.model_hyperparameters["logistic_regression"])
    lr_model.fit(X_train, y_train)
    lr_prob = lr_model.predict_proba(X_test)[:, 1]
    lr_pred = (lr_prob >= 0.5).astype(int)
    models["Logistic Regression"] = lr_model
    metrics["Logistic Regression"] = {**_evaluate_binary(y_test, lr_pred, lr_prob), "confusion_matrix": confusion_matrix(y_test, lr_pred).tolist(), "classification_report": classification_report(y_test, lr_pred, output_dict=True, zero_division=0)}
    try:
        metrics["Logistic Regression"]["cv_f1_mean"] = float(cross_val_score(lr_model, X_train, y_train, cv=3, scoring="f1", n_jobs=1).mean())
    except Exception:
        pass

    iso_model = IsolationForest(random_state=config.random_state, n_jobs=-1, **config.model_hyperparameters["isolation_forest"])
    iso_model.fit(X_train)
    iso_pred = (iso_model.predict(X_test) == -1).astype(int)
    iso_score = -iso_model.score_samples(X_test)
    iso_prob = (iso_score - iso_score.min()) / (iso_score.max() - iso_score.min() + 1e-9)
    models["Isolation Forest"] = iso_model
    metrics["Isolation Forest"] = {**_evaluate_binary(y_test, iso_pred, iso_prob), "confusion_matrix": confusion_matrix(y_test, iso_pred).tolist(), "classification_report": classification_report(y_test, iso_pred, output_dict=True, zero_division=0)}

    # Neural Network (TF preferred, sklearn fallback)
    nn_ext = ".keras"
    try:
        import tensorflow as tf
        nn = tf.keras.Sequential([
            tf.keras.layers.Input(shape=(X_train.shape[1],)),
            tf.keras.layers.Dense(256, activation="relu"),
            tf.keras.layers.Dropout(0.3),
            tf.keras.layers.Dense(128, activation="relu"),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(1, activation="sigmoid"),
        ])
        nn.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
        nn_hist = nn.fit(
            X_train, y_train, validation_split=0.15,
            epochs=config.model_hyperparameters["neural_network"]["epochs"],
            batch_size=config.model_hyperparameters["neural_network"]["batch_size"],
            verbose=0,
        )
        nn_prob = nn.predict(X_test, verbose=0).reshape(-1)
        history["Neural Network"] = {k: [float(v) for v in vals] for k, vals in nn_hist.history.items()}
        nn_model = nn
    except Exception:
        nn_ext = ".pkl"
        logger.warning("TensorFlow unavailable; using MLP fallback for Neural Network")
        nn_model = MLPClassifier(random_state=config.random_state, hidden_layer_sizes=(128, 64), max_iter=50)
        nn_model.fit(X_train, y_train)
        nn_prob = nn_model.predict_proba(X_test)[:, 1]
        history["Neural Network"] = {}
    nn_pred = (nn_prob >= 0.5).astype(int)
    models["Neural Network"] = nn_model
    metrics["Neural Network"] = {**_evaluate_binary(y_test, nn_pred, nn_prob), "confusion_matrix": confusion_matrix(y_test, nn_pred).tolist(), "classification_report": classification_report(y_test, nn_pred, output_dict=True, zero_division=0), "save_extension": nn_ext}

    # LSTM (TF preferred, sklearn fallback)
    lstm_scaler = MinMaxScaler()
    X_train_lstm = lstm_scaler.fit_transform(X_train)
    X_test_lstm = lstm_scaler.transform(X_test)
    lstm_ext = ".keras"
    try:
        import tensorflow as tf
        X_train_seq = np.expand_dims(X_train_lstm, axis=1)
        X_test_seq = np.expand_dims(X_test_lstm, axis=1)
        lstm = tf.keras.Sequential([
            tf.keras.layers.Input(shape=(X_train_seq.shape[1], X_train_seq.shape[2])),
            tf.keras.layers.LSTM(96),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(1, activation="sigmoid"),
        ])
        lstm.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
        lstm_hist = lstm.fit(
            X_train_seq, y_train, validation_split=0.15,
            epochs=config.model_hyperparameters["lstm"]["epochs"],
            batch_size=config.model_hyperparameters["lstm"]["batch_size"],
            verbose=0,
        )
        lstm_prob = lstm.predict(X_test_seq, verbose=0).reshape(-1)
        history["LSTM"] = {k: [float(v) for v in vals] for k, vals in lstm_hist.history.items()}
        lstm_model = lstm
    except Exception:
        lstm_ext = ".pkl"
        logger.warning("TensorFlow unavailable; using MLP fallback for LSTM")
        lstm_model = MLPClassifier(random_state=config.random_state, hidden_layer_sizes=(64,), max_iter=40)
        lstm_model.fit(X_train_lstm, y_train)
        lstm_prob = lstm_model.predict_proba(X_test_lstm)[:, 1]
        history["LSTM"] = {}
    lstm_pred = (lstm_prob >= 0.5).astype(int)
    models["LSTM"] = lstm_model
    metrics["LSTM"] = {**_evaluate_binary(y_test, lstm_pred, lstm_prob), "confusion_matrix": confusion_matrix(y_test, lstm_pred).tolist(), "classification_report": classification_report(y_test, lstm_pred, output_dict=True, zero_division=0), "save_extension": lstm_ext}

    # Persist required artifacts
    model_dir = Path(config.output_models_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    for name, fname in {
        "XGBoost": "xgboost_model.pkl",
        "Random Forest": "random_forest_model.pkl",
        "Logistic Regression": "logistic_regression_model.pkl",
        "Isolation Forest": "isolation_forest_model.pkl",
    }.items():
        with open(model_dir / f"{config.model_prefix}{fname}", "wb") as fh:
            pickle.dump(models[name], fh)

    nn_path = model_dir / f"{config.model_prefix}neural_network_model{nn_ext}"
    if nn_ext == ".keras":
        models["Neural Network"].save(nn_path)
    else:
        with open(nn_path, "wb") as fh:
            pickle.dump(models["Neural Network"], fh)

    lstm_path = model_dir / f"{config.model_prefix}lstm_model{lstm_ext}"
    if lstm_ext == ".keras":
        models["LSTM"].save(lstm_path)
    else:
        with open(lstm_path, "wb") as fh:
            pickle.dump(models["LSTM"], fh)

    with open(model_dir / f"{config.model_prefix}lstm_scaler.pkl", "wb") as fh:
        pickle.dump(lstm_scaler, fh)
    with open(model_dir / f"{config.model_prefix}ubts.pkl", "wb") as fh:
        pickle.dump(
            {
                "fraud_rate_train": float(np.mean(y_train)),
                "fraud_rate_test": float(np.mean(y_test)),
                "sample_count_train": int(len(y_train)),
                "sample_count_test": int(len(y_test)),
            },
            fh,
        )
    return models, metrics, history
