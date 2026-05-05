# UPI-Fraud-Detection

**MLBFD — Multi-Layer Behavioral Fraud Detection**

A real-time UPI transaction fraud detection system combining ensemble ML models, user/wallet trust scoring, and a Flutter mobile frontend.

---

## Project Structure

```
UPI-Fraud-Detection/
├── colab_code/
│   └── MLBFD_Phase4/         ← Python Flask backend
│       ├── app.py             # Main Flask application
│       ├── api.py             # REST API Blueprint (/api/*)
│       ├── predictor.py       # Multi-layer fraud orchestrator
│       ├── config.py          # Centralised configuration
│       ├── db.py              # SQLite connection management
│       ├── ubts.py            # User Baseline Trust Score
│       ├── wts.py             # Wallet Trust Score
│       ├── requirements.txt   # Python dependencies
│       ├── .env.example       # Environment variable template
│       ├── migrations/
│       │   └── v1_initial.sql # Database schema
│       └── models/            # ML model artifacts (not committed)
├── flutter_app/               ← Flutter mobile frontend
│   ├── lib/
│   │   ├── main.dart
│   │   ├── screens/
│   │   ├── services/
│   │   ├── providers/
│   │   ├── models/
│   │   └── widgets/
│   └── pubspec.yaml
├── PHASE_11_REPORT.md
├── PHASE_12_REPORT.md
└── README.md
```

---

## Backend Setup

### Prerequisites
- Python 3.10+
- ML model files placed in `colab_code/MLBFD_Phase4/models/` (see `models/README_MODELS.md`)

### Installation

```bash
cd colab_code/MLBFD_Phase4

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment variables
cp .env.example .env
# Edit .env as needed
```

### Running the Backend

```bash
python app.py
```

The server starts at `http://127.0.0.1:5000`.

> **Note:** The application starts successfully even if ML model files are absent — it degrades gracefully and serves the UI without predictions.

---

## Flutter Frontend Setup

### Prerequisites
- Flutter SDK 3.x
- Dart SDK

### Running the App

```bash
cd flutter_app
flutter pub get
flutter run
```

To run on Chrome (web):
```bash
flutter run -d chrome
```

Configure the backend URL in `lib/config/api_config.dart` or via the in-app settings screen.

---

## ML Models

Model artifacts are large binary files and are **not committed** to this repository. Place the following files in `colab_code/MLBFD_Phase4/models/` before running the backend:

| File | Description |
|------|-------------|
| `mlbfd_mega_xgboost_model.pkl` | XGBoost classifier |
| `mlbfd_mega_random_forest_model.pkl` | Random Forest classifier |
| `mlbfd_mega_logistic_regression_model.pkl` | Logistic Regression classifier |
| `mlbfd_mega_isolation_forest_model.pkl` | Isolation Forest anomaly detector |
| `mlbfd_mega_neural_network_model.keras` | Dense Neural Network |
| `mlbfd_mega_lstm_model.keras` | LSTM temporal model |
| `mlbfd_mega_scaler.pkl` | StandardScaler for feature normalisation |
| `mlbfd_mega_feature_names.pkl` | Ordered list of feature names |
| `mlbfd_mega_lstm_scaler.pkl` | Scaler for LSTM input |
| `mlbfd_mega_ubts.pkl` | User Baseline Trust Score data |
| `mlbfd_mega_results.pkl` | Saved training results |

---

## Phase Reports

| Phase | Report |
|-------|--------|
| Phase 10 | `colab_code/MLBFD_Phase4/PHASE_10_REPORT.md` |
| Phase 11 | `PHASE_11_REPORT.md` |
| Phase 12 | `PHASE_12_REPORT.md` |
