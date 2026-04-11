# Phase 12: Flutter Mobile App — UPI Fraud Detection Client

## Overview

Phase 12 delivers a production-ready **Flutter mobile application** for real-time UPI fraud detection. The app integrates with the Phase 5–11 Flask backend, providing QR code scanning, live ML-powered predictions, a user dashboard, transaction history, and offline support.

---

## App Architecture

```
flutter_app/
├── lib/
│   ├── main.dart                     # App entry point, Provider setup
│   ├── config/
│   │   └── api_config.dart           # API URLs, timeouts, DB config
│   ├── models/
│   │   ├── transaction.dart          # Transaction model + JSON serialization
│   │   ├── prediction.dart           # Prediction + LayerScore + EnsembleVote
│   │   └── user.dart                 # User profile + AppStats
│   ├── services/
│   │   ├── api_service.dart          # Dio HTTP client with retry logic
│   │   ├── storage_service.dart      # SQLite local cache (sqflite)
│   │   └── qr_scanner_service.dart   # UPI QR parsing (offline)
│   ├── providers/
│   │   ├── prediction_provider.dart  # Prediction state + API/cache logic
│   │   ├── transaction_provider.dart # Transaction list, filters, sync
│   │   └── settings_provider.dart    # User preferences (SharedPreferences)
│   ├── screens/
│   │   ├── home_screen.dart          # Main screen with bottom nav + scan CTA
│   │   ├── qr_scanner_screen.dart    # Camera-based UPI QR scanner
│   │   ├── transaction_input_screen.dart  # Manual UPI details entry + results
│   │   ├── dashboard_screen.dart     # Stats + pie chart + risk gauge
│   │   ├── history_screen.dart       # Searchable / filterable transaction log
│   │   └── settings_screen.dart      # API config, theme, notifications
│   ├── widgets/
│   │   ├── risk_gauge.dart           # Animated arc gauge (0–100, colour-coded)
│   │   ├── layer_breakdown_card.dart # Per-layer score bars + ensemble votes
│   │   ├── transaction_card.dart     # List tile with risk badge
│   │   └── custom_app_bar.dart       # Reusable AppBar + OfflineBanner + LoadingOverlay
│   └── utils/
│       ├── constants.dart            # Spacing, colours, route names
│       ├── theme.dart                # Material Design 3 light/dark themes
│       ├── validators.dart           # Form validation helpers
│       └── formatters.dart           # Currency, date, VPA masking, compact numbers
├── test/
│   ├── widget_test.dart              # 16 widget tests
│   ├── unit/
│   │   ├── models_test.dart          # 16 model unit tests
│   │   ├── validators_test.dart      # 17 validation unit tests
│   │   ├── formatters_test.dart      # 12 formatter unit tests
│   │   └── qr_scanner_service_test.dart  # 14 QR parsing unit tests
│   ├── integration_test/
│   │   └── app_test.dart             # 12 integration tests
│   └── fixtures/
│       └── mock_data.dart            # Reusable test fixtures
├── android/
│   └── app/src/main/AndroidManifest.xml  # Permissions config
├── ios/
│   └── Runner/Info.plist             # iOS permissions + metadata
└── pubspec.yaml                       # Dependencies
```

---

## Features Delivered

### ✅ QR Code Scanner (`qr_scanner_screen.dart`)
- **Real-time camera scanning** using `mobile_scanner`
- **UPI deep-link parsing**: `upi://pay?pa=...&pn=...&am=...`
- Auto-navigates to transaction input with pre-filled fields
- Torch toggle and camera flip controls
- Graceful error handling for invalid QR codes
- Custom scanner overlay with corner brackets

### ✅ Real-time Fraud Detection (`transaction_input_screen.dart`)
- Calls `/api/predict` with transaction data
- **Animated risk gauge** (0–100, green → amber → red)
- Verdict: ✓ SAFE / ⚠ SUSPICIOUS / ✗ FRAUD DETECTED
- **Layer breakdown card**: UBTS, WTS, Website Trust, LSTM, Ensemble
- Progress bars per layer with explanations
- Ensemble vote breakdown per model

### ✅ Manual Transaction Entry
- Form fields: Payee UPI, Name, Amount (₹), Note
- Full input validation (VPA format, amount range 0–₹2,00,000)
- Keyboard actions and field focus management

### ✅ Dashboard (`dashboard_screen.dart`)
- Stats grid: Total checks, Safe, Suspicious, Fraud counts
- **Pie chart** (fl_chart) for risk distribution
- Average risk score progress bar
- Fraud rate indicator with threshold alerts
- Pull-to-refresh, server sync

### ✅ Transaction History (`history_screen.dart`)
- Infinite scroll pagination
- **Search** by payee name or UPI ID
- **Filter chips**: All / Safe / Suspicious / Fraud
- Tap for detailed bottom sheet: full prediction + gauge + layer breakdown
- Swipe-to-delete with confirmation dialog
- **CSV export** button

### ✅ User Settings (`settings_screen.dart`)
- API base URL configuration + connection test
- **Theme selector**: Light / Dark / System
- Push notifications toggle
- Auto-sync toggle
- Last sync timestamp
- Open Source Licenses page

### ✅ Offline Mode
- All predictions and transactions cached in **SQLite** (`sqflite`)
- Shows OfflineBanner when API unavailable
- QR parsing works fully offline (pure Dart)
- Stats computed from local DB when server unreachable

### ✅ Security
- **VPA masking**: `merchant@okaxis` → `me***@okaxis`
- No plaintext sensitive data in logs
- HTTPS-ready Dio configuration
- Retry interceptor with exponential backoff (max 3 attempts)

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `dio` | ^5.3.2 | HTTP client with interceptors |
| `provider` | ^6.1.1 | State management |
| `mobile_scanner` | ^3.5.5 | QR code camera scanning |
| `sqflite` | ^2.3.0 | Local SQLite database |
| `shared_preferences` | ^2.2.2 | User settings persistence |
| `intl` | ^0.19.0 | Localisation & formatting |
| `fl_chart` | ^0.66.2 | Pie/bar/line charts |
| `json_annotation` | ^4.8.1 | JSON model serialization |
| `flutter_secure_storage` | ^9.0.0 | Encrypted settings storage |
| `csv` | ^6.0.0 | CSV export for history |
| `connectivity_plus` | ^5.0.2 | Network connectivity detection |
| `permission_handler` | ^11.1.0 | Runtime permissions |
| `uuid` | ^4.3.3 | Transaction ID generation |
| `timeago` | ^3.6.1 | Relative time formatting |

---

## Test Coverage

### Unit Tests (59 tests)
| Suite | Tests | Description |
|-------|-------|-------------|
| `models_test.dart` | 16 | Transaction/Prediction/AppStats JSON, equality, masking |
| `validators_test.dart` | 17 | VPA, amount, name, URL validation |
| `formatters_test.dart` | 12 | Currency, date, VPA mask, compact numbers |
| `qr_scanner_service_test.dart` | 14 | QR parse, validate, build, error cases |

### Widget Tests (16 tests)
| Suite | Tests | Description |
|-------|-------|-------------|
| `widget_test.dart` | 16 | RiskGauge, LayerBreakdown, TransactionCard, AppBar, Overlay |

### Integration Tests (12 tests)
| Suite | Tests | Description |
|-------|-------|-------------|
| `app_test.dart` | 12 | App launch, navigation, form validation, settings |

**Total: 87 tests** ✅

---

## API Integration

| Endpoint | Method | Usage |
|----------|--------|-------|
| `/api/health` | GET | Connection check in settings |
| `/api/predict` | POST | Fraud prediction for a transaction |
| `/api/qr/parse` | POST | Server-side QR parsing (fallback) |
| `/api/stats` | GET | Global stats for dashboard sync |
| `/api/history` | GET | Server-side transaction history |
| `/api/feedback` | POST | User correction submission |

---

## Risk Score Colour Coding

| Range | Colour | Verdict |
|-------|--------|---------|
| 0 – 29 | 🟢 Green (`#2E7D32`) | ✓ SAFE |
| 30 – 59 | 🟡 Amber (`#F57C00`) | ⚠ SUSPICIOUS |
| 60 – 100 | 🔴 Red (`#C62828`) | ✗ FRAUD DETECTED |

---

## Platform Support

| Platform | Status |
|----------|--------|
| Android (API 21+) | ✅ Full support |
| iOS (iOS 12+) | ✅ Full support |
| Mobile landscape | ✅ Supported |
| Tablet (7"+) | ✅ Responsive layout |

### Required Permissions
- **Camera** — QR code scanning
- **Internet** — API calls
- **Location** (optional) — Geo-velocity fraud detection
- **Storage** (Android ≤28) — CSV export

---

## Running the App

### Prerequisites
```bash
flutter doctor   # Verify Flutter installation
flutter pub get  # Install dependencies
```

### Start the backend
```bash
cd colab_code/MLBFD_Phase4
python app.py    # Flask server on port 5000
```

### Run on device/emulator
```bash
cd flutter_app
flutter run
```

### Run tests
```bash
flutter test test/unit/
flutter test test/widget_test.dart
flutter test integration_test/app_test.dart  # Requires connected device
```

### Build release APK
```bash
flutter build apk --release
```

---

## Success Criteria

| Criterion | Status |
|-----------|--------|
| QR scanner working (parses UPI format) | ✅ |
| Real-time predictions displayed correctly | ✅ |
| Risk gauge colour-coded (Green/Yellow/Red) | ✅ |
| Layer breakdown shown with explanations | ✅ |
| Transaction history saved + synced | ✅ |
| Offline mode functional | ✅ |
| All screens responsive (mobile + tablet) | ✅ |
| Unit tests passing (20+) | ✅ 59 unit tests |
| Integration tests passing (10+) | ✅ 12 integration tests |
| API integration complete | ✅ |

---

## Phase Status

| Phase | Status | Notes |
|-------|--------|-------|
| 1–4 | ✅ Complete | Data pipeline + ML training |
| 5–9 | ✅ Merged | SQLite + REST API + Multi-layer detection |
| 10 | ✅ Complete | Advanced WTS geo-fencing + velocity |
| 11 | ✅ Complete | XGBoost ensemble optimisation |
| **12** | **✅ Complete** | **Flutter Mobile App** |
