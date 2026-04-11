# UPI Fraud Detection — Flutter Mobile App

A production-ready Flutter mobile application for real-time UPI fraud detection with QR code scanning, live ML predictions, and a user dashboard.

---

## Features

- 📷 **QR Code Scanner** — Scan UPI QR codes and instantly check for fraud
- 🛡️ **Live Fraud Detection** — Real-time risk scores from the ML backend
- 📊 **Risk Gauge** — Animated colour-coded gauge (Green / Amber / Red)
- 🔍 **Layer Breakdown** — UBTS, WTS, Website Trust, LSTM, Ensemble scores
- 📱 **Dashboard** — Stats, pie chart, fraud rate tracking
- 📋 **Transaction History** — Search, filter, export to CSV
- ⚙️ **Settings** — API URL, theme, notifications, sync
- 🔌 **Offline Mode** — SQLite cache for offline predictions

---

## Quick Start

### 1. Start the backend
```bash
cd ../colab_code/MLBFD_Phase4
pip install flask numpy pandas scikit-learn
python app.py
```

### 2. Install Flutter dependencies
```bash
flutter pub get
```

### 3. Run the app
```bash
flutter run
```

### 4. Run tests
```bash
flutter test
```

---

## Project Structure

```
lib/
├── main.dart              # Entry point + Provider setup
├── config/api_config.dart # API config & constants
├── models/                # Data models with JSON serialization
├── services/              # API, Storage, QR Scanner
├── providers/             # State management (Provider)
├── screens/               # App screens
├── widgets/               # Reusable UI components
└── utils/                 # Theme, validators, formatters
```

---

## Configuration

Open **Settings** → update the **Backend URL** to point to your Flask server.

Default: `http://localhost:5000`

For a real device, use your computer's LAN IP:  
`http://192.168.x.x:5000`

---

## Build

```bash
# Debug APK
flutter build apk --debug

# Release APK
flutter build apk --release

# iOS
flutter build ios --release
```

---

See [PHASE_12_REPORT.md](../PHASE_12_REPORT.md) for full documentation.
