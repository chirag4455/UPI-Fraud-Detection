# 🎯 MLBFD - ML BASED UPI FRAUD DETECTION SYSTEM
## COMPLETE MASTER PROJECT DOCUMENTATION & CONTEXT PROMPT

**Project Owner:** Chirag (@chirag4455)  
**Repository:** https://github.com/chirag4455/UPI-Fraud-Detection  
**Current Date:** 2026-05-04  
**Project Status:** Phase 4 (Production Ready Backend) + Phase 5-9 (Modular Architecture)

---

## 📋 TABLE OF CONTENTS
1. Project Overview & Vision
2. System Architecture & Design
3. Technology Stack & Tools
4. Project Structure & File Locations
5. Implementation Details (ALL CODE LOGIC)
6. Current Issues & Errors
7. Executed Features & Completed Milestones
8. Remaining Features & TODO
9. Dataset Information & Training
10. Next Steps & Roadmap

---

## 1️⃣ PROJECT OVERVIEW & VISION

### What is MLBFD?
**MLBFD (ML Based Fraud Detection)** is a production-grade fraud detection system for UPI (Unified Payments Interface) transactions in India. It combines:
- 7-Layer Bulletproof Detection Engine
- Multiple ML Models (XGBoost, Random Forest, LSTM, Neural Networks, etc.)
- Real-time Risk Scoring
- User Behavior Baseline Analysis
- Device & Account Compromise Detection
- Money Mule Network Detection
- Website Reputation Checking

### Problem Statement
UPI fraud in India causes billions in losses annually:
- Phishing attacks targeting UPI users
- Money mule networks funneling stolen funds
- Account takeovers (ATOs)
- Unauthorized transactions
- Social engineering attacks

### Solution Approach
- **Layered Defense:** Multiple detection layers = defense in depth
- **Real-time Processing:** Instant fraud detection at transaction time
- **ML Ensemble:** Combine 6+ models for higher accuracy
- **Behavioral Analysis:** Track user's normal patterns
- **Risk Scoring:** 0-100 score with clear verdicts
- **Mobile + Web:** Flutter app + Flask backend

---

## 2️⃣ SYSTEM ARCHITECTURE & DESIGN

### High-Level Architecture
```
┌─────────────────────────────────────────────────────────┐
│         MOBILE APP (Flutter)                             │
│  ├─ QR Scanner                                          │
│  ├─ Dashboard (Stats, Charts)                           │
│  ├─ Transaction History                                 │
│  ├─ Risk Gauge (Animated)                              │
│  └─ Settings (API Config)                              │
└────────────────┬────────────────────────────────────────┘
                 │ HTTP/REST API
                 ↓
┌─────────────────────────────────────────────────────────┐
│         BACKEND (Flask Python)                           │
│  ┌──────────────────────────────────────────────────┐   │
│  │ API Layer (/api/*)                               │   │
│  │  ├─ /api/predict-secure (Fraud Detection)        │   │
│  │  ├─ /api/register (User Registration)            │   │
│  │  ├─ /api/login (Authentication)                  │   │
│  │  ├─ /api/transfer (Money Transfer)               │   │
│  │  ├─ /api/balance/<user_id> (Get Balance)        │   │
│  │  └─ /api/website-check/<domain>                  │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Fraud Detection Layer                            │   │
│  │  ├─ InputValidator (Data Validation)             │   │
│  │  ├─ UserBehaviorAnalyzer (Baseline Tracking)     │   │
│  │  ├─ VelocityEngine (Burst Detection)             │   │
│  │  ├─ TransactionFlowAnalyzer (Money Mules)        │   │
│  │  ├─ PayeeValidator (Scam Detection)              │   │
│  │  ├─ CompromiseDetector (Account Takeover)        │   │
│  │  └─ BulletproofFraudDetector (Ensemble)          │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │ ML Models                                        │   │
│  │  ├─ XGBoost (AUC: 0.9734, Recall: 92.51%)       │   │
│  │  ├─ Random Forest (AUC: 0.9680, Recall: 90.2%)  │   │
│  │  ├─ Neural Network (AUC: 0.9612, Recall: 89.8%) │   │
│  │  ├─ LSTM (AUC: 0.9545, Recall: 88.1%)           │   │
│  │  ├─ Logistic Regression (AUC: 0.9210)           │   │
│  │  └─ Isolation Forest (AUC: 0.8950)              │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Database Layer (SQLite + ORM)                    │   │
│  │  ├─ User (Account Info)                          │   │
│  │  ├─ Transaction (Txn History)                    │   │
│  │  ├─ UserBehaviorBaseline (Pattern Data)          │   │
│  │  ├─ WebsiteReputation (Domain Trust Scores)      │   │
│  │  └─ Feedback (Model Accuracy Tracking)           │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Web Dashboard (HTML/CSS/JS)                      │   │
│  │  ├─ Dashboard (Stats, Model Performance)         │   │
│  │  ├─ Predict (Manual Testing)                     │   │
│  │  ├─ Alerts (Real-time Fraud Alerts)             │   │
│  │  ├─ Network (Money Mule Visualization)          │   │
│  │  ├─ Explainability (SHAP Feature Importance)    │   │
│  │  ├─ Drift Detection (Model Performance)          │   │
│  │  ├─ NPCI Analytics (RBI Data Integration)        │   │
│  │  ├─ Reports (Export & Analysis)                  │   │
│  │  └─ Settings (Configuration)                     │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────┐
│         DATA SOURCES                                     │
│  ├─ NPCI UPI Data (Monthly Transaction Stats)           │
│  ├─ Bank Risk Analysis (Chargebacks, Fraud Rates)       │
│  ├─ RBI Compliance Reports (Regulatory Data)            │
│  ├─ Known Scam UPI Database (Phishing/Fraud)            │
│  └─ Website Reputation Database                         │
└─────────────────────────────────────────────────────────┘
```

### 7-Layer Fraud Detection Engine

**Layer 1: Input Validation & Sanitization**
- Prevent SQL injection, XSS, invalid data
- Validate: amount (>0, <₹10cr), UPI format, device ID, hour (0-23), website URL
- Sanitize: trim whitespace, normalize UPI

**Layer 2: User Behavior Baseline & Anomaly Detection**
- Track user's historical transaction patterns
- Baseline: avg_amount, std_amount, usual_hours, known_payees
- Z-score analysis: detect transactions >3σ from mean
- Scoring:
  - z_score > 3: +60 points
  - z_score > 2: +45 points
  - z_score > 1: +25 points
  - New payee: +40 points
  - Unusual hour: +30 points

**Layer 3: Velocity & Burst Detection**
- Detect rapid-fire transactions (potential account compromise)
- 1-hour window: >5 txns = +35 pts, >3 txns = +20 pts
- 24-hour window: >20 txns = +30 pts

**Layer 4: Transaction Flow & Chain Analysis**
- Track money mule networks
- Analyze receiver profile
- Detect chains of suspicious receivers
- Currently: Basic implementation (returns 0 by default)

**Layer 5: Payee Validation & Verification**
- Check UPI against known scam database
- If known scam: INSTANT BLOCK (score=95, status=BLOCKED)
- New payee: +50 points
- Known payees: no penalty

**Layer 6: Compromise Detection (Account Takeover)**
- Detect new/unknown devices
- Unknown device: +40 points
- Would also detect: auth method changes, impossible travel, failed auth attempts

**Layer 7: Amount Bounds & Website Trust**
- Amount > ₹1 crore: +30 points
- Website reputation score (not implemented yet)

### Scoring & Thresholds
```
Risk Score 0-100:
├─ 0-39: SAFE ✅ (Status: APPROVED)
├─ 40-59: CAUTION ⚠️ (Status: APPROVED_WITH_WARNING)
├─ 60-79: SUSPICIOUS 🚨 (Status: REQUIRES_2FA)
└─ 80-100: FRAUD DETECTED ❌ (Status: BLOCKED)

Weighted Scoring:
├─ Behavioral: 35%
├─ Payee: 30%
├─ Compromise: 12%
├─ Velocity: 10%
├─ Flow: 8%
├─ Amount: 3%
└─ Website: 2%
```

---

## 3️⃣ TECHNOLOGY STACK & TOOLS

### Backend
- **Language:** Python 3.8+
- **Framework:** Flask (Web server)
- **ORM:** SQLAlchemy (Database abstraction)
- **Database:** SQLite (Local) / PostgreSQL (Production)
- **ML Libraries:**
  - scikit-learn (XGBoost, Random Forest, Logistic Regression, Isolation Forest)
  - TensorFlow/Keras (LSTM, Neural Network)
  - XGBoost
  - NumPy, Pandas (Data manipulation)
  - SHAP (Explainability)

### Frontend (Web Dashboard)
- **HTML/CSS/JavaScript**
- **Charts:** Chart.js, Plotly
- **UI Components:** Custom CSS, Bootstrap
- **Templates:** Jinja2

### Mobile (Flutter App)
- **Language:** Dart
- **Framework:** Flutter 3.0+
- **State Management:** Provider
- **Local Storage:** SQLite (via sqflite)
- **QR Scanning:** mobile_scanner
- **Networking:** dio (HTTP)

### DevOps & Deployment
- **Version Control:** Git + GitHub
- **API Documentation:** REST, JSON
- **Testing:** Unit tests (pytest), Widget tests (Flutter)
- **Performance:** In-memory caching for ML models

### Data Sources
- **NPCI Data:** npci_processed_data.csv
- **Bank Data:** bank_risk_analysis.csv
- **Compliance:** rbi_compliance_report.json

---

## 4️⃣ PROJECT STRUCTURE & FILE LOCATIONS

```
UPI-Fraud-Detection/
│
├─ README.md (Project description)
├─ MASTER_PROMPT.md (THIS FILE - Complete documentation)
│
├─ backend/
│  ├─ app.py (Flask main app, routes, feature creation)
│  ├─ fraud_detection_v2.py (⭐ 7-LAYER DETECTION ENGINE)
│  ├─ user_manager.py (User registration, PIN management)
│  ├─ database.py (SQLAlchemy models: User, Transaction, etc.)
│  ├─ db.py (Database initialization, SQLite setup)
│  ├─ api.py (REST API blueprint - modular architecture)
│  ├─ config.py (Configuration constants)
│  │
│  ├─ models/
│  │  ├─ mlbfd_mega_xgboost_model.pkl (Trained XGBoost model)
│  │  ├─ mlbfd_mega_random_forest_model.pkl
│  │  ├─ mlbfd_mega_neural_network_model.keras (TensorFlow)
│  │  ├─ mlbfd_mega_lstm_model.keras (LSTM for sequences)
│  │  ├─ mlbfd_mega_logistic_regression_model.pkl
│  │  ├─ mlbfd_mega_isolation_forest_model.pkl
│  │  ├─ mlbfd_mega_scaler.pkl (StandardScaler for feature normalization)
│  │  └─ mlbfd_mega_feature_names.pkl (Feature list for model input)
│  │
│  ├─ data/
│  │  ├─ npci_processed_data.csv (NPCI UPI statistics, monthly trends)
│  │  ├─ bank_risk_analysis.csv (Bank chargebacks, fraud rates)
│  │  └─ rbi_compliance_report.json (RBI regulatory compliance scores)
│  │
│  ├─ templates/
│  │  ├─ base.html (Base template with navigation)
│  │  ├─ index.html (Dashboard - stats, model performance)
│  │  ├─ predict.html (Manual fraud prediction form)
│  │  ├─ alerts.html (Real-time fraud alerts)
│  │  ├─ network.html (Money mule network visualization)
│  │  ├─ profile.html (User behavior profile)
│  │  ├─ explainability.html (SHAP feature importance)
│  │  ├─ heatmap.html (Hourly & transaction type risk heatmap)
│  │  ├─ drift.html (Model performance & accuracy drift)
│  │  ├─ npci.html (NPCI data integration)
│  │  ├─ reports.html (Report generation & export)
│  │  └─ settings.html (Configuration)
│  │
│  ├─ static/
│  │  ├─ css/style.css (Dashboard styling)
│  │  └─ js/charts.js (Chart.js visualization)
│  │
│  ├─ __pycache__/ (Python bytecode, auto-generated)
│  ├─ requirements.txt (Python dependencies)
│  └─ .env (Environment variables - SECRET_KEY, API_KEYS)
│
├─ flutter_app/
│  ├─ README.md (Flutter app documentation)
│  ├─ pubspec.yaml (Dependencies: provider, dio, sqflite, mobile_scanner)
│  │
│  ├─ lib/
│  │  ├─ main.dart (App entry point, Provider setup)
│  │  │
│  │  ├─ config/
│  │  │  └─ api_config.dart (Backend URL: http://localhost:5000)
│  │  │
│  │  ├─ models/
│  │  │  ├─ prediction_result.dart (Fraud detection response model)
│  │  │  ├─ transaction.dart (Transaction data model)
│  │  │  └─ user.dart (User profile model)
│  │  │
│  │  ├─ services/
│  │  │  ├─ api_service.dart (HTTP calls to backend)
│  │  │  ├─ storage_service.dart (SQLite caching)
│  │  │  └─ qr_scanner_service.dart (QR code scanning)
│  │  │
│  │  ├─ providers/
│  │  │  ├─ prediction_provider.dart (State management for predictions)
│  │  │  ├─ user_provider.dart (User authentication state)
│  │  │  └─ history_provider.dart (Transaction history)
│  │  │
│  │  ├─ screens/
│  │  │  ├─ home_screen.dart (Main dashboard)
│  │  │  ├─ scanner_screen.dart (QR code scanner)
│  │  │  ├─ history_screen.dart (Transaction history)
│  │  │  ├─ settings_screen.dart (Configuration)
│  │  │  └─ details_screen.dart (Fraud details)
│  │  │
│  │  ├─ widgets/
│  │  │  ├─ risk_gauge.dart (Animated risk meter)
│  │  │  ├─ layer_breakdown.dart (7-layer scores breakdown)
│  │  │  ├─ transaction_card.dart (Transaction display)
│  │  │  └─ custom_buttons.dart (Reusable UI components)
│  │  │
│  │  └─ utils/
│  │     ├─ theme.dart (Colors, fonts, styling)
│  │     ├─ validators.dart (Input validation)
│  │     └─ formatters.dart (Date/currency formatting)
│  │
│  ├─ test/ (Widget & unit tests)
│  └─ android/, ios/ (Platform-specific code)
│
└─ docs/
   ├─ PHASE_12_REPORT.md (Comprehensive project report)
   ├─ API_DOCUMENTATION.md (API endpoint specs)
   ├─ ARCHITECTURE.md (Detailed architecture)
   └─ TRAINING_GUIDE.md (Model training procedures)
```

---

## 5️⃣ IMPLEMENTATION DETAILS - COMPLETE CODE LOGIC

### A. fraud_detection_v2.py - BULLETPROOF ENGINE (616 lines)

**Class: InputValidator**
```
Purpose: Sanitize & validate all input data
- validate_amount(): Check >0, <₹10cr, not NaN
- validate_upi(): Check format (user@bank), <255 chars
- validate_hour(): Check 0-23
- validate_device_id(): Normalize, default to "unknown"
- validate_website_url(): Check http/https, <2048 chars
```

**Class: UserBehaviorAnalyzer**
```
Purpose: Track user baseline & detect behavioral anomalies
Properties:
  - mock_baselines: Sample data for 'user_001'
    * avg_amount: ₹5,000
    * std_amount: ₹2,000
    * usual_hours: [9,10,11,14,15,18,19]
    * usual_payees: ['mom@ybl', 'dad@paytm', 'bill@okaxis']
    * is_new_account: False
    
Methods:
  - get_user_baseline(user_id): Fetch historical patterns
  - detect_behavioral_anomaly(user_id, txn, baseline):
    * Calculate z_score = (amount - avg) / std_dev
    * z_score > 3: +60 pts
    * z_score > 2: +45 pts
    * z_score > 1: +25 pts
    * New payee: +40 pts
    * Unusual hour: +30 pts
    * Return: (score, reasons list)
```

**Class: VelocityEngine**
```
Purpose: Detect burst transactions & rapid money movement
Methods:
  - check_velocity(user_id, amount):
    * Count txns in 1-hour window
    * Count txns in 24-hour window
    * >5 txns/1hr: +35 pts
    * 3-5 txns/1hr: +20 pts
    * >20 txns/24hr: +30 pts
    * Return: (score, reasons)
    
Data Structure:
  - txn_history: Dict[user_id] → List of txns
  - Each txn: {amount, receiver_upi, timestamp}
```

**Class: TransactionFlowAnalyzer**
```
Purpose: Detect money mule networks & suspicious flows
Methods:
  - analyze_flow(sender_upi, receiver_upi, amount):
    * Check if receiver is flagged money mule
    * Currently returns 0 (placeholder)
    * Future: Graph analysis, chain depth, ring detection
    * Return: (score, reasons)
    
Use Case: If someone receives → quickly forwards to 3+ new UPIs
```

**Class: PayeeValidator**
```
Purpose: Check payee legitimacy & scam detection
Data:
  - scam_upis: Set of known fraud UPIs
    * 'scammer@icici', 'fraud@hdfc', 'phish@axis', etc.
  - known_payees: Set of legitimate contacts
    
Methods:
  - validate_payee(receiver_upi, name):
    * IF receiver_upi in scam_upis:
      → INSTANT BLOCK (score=95, status=BLOCKED)
    * ELSE IF receiver_upi not in known_payees:
      → +50 pts (new payee penalty)
    * Return: (score, reasons)
    
Logic: Known scams = immediate rejection, new payees = warning
```

**Class: CompromiseDetector**
```
Purpose: Detect account takeover & unauthorized access
Data:
  - known_devices: Dict[user_id] → Set of trusted device IDs
  - Example: 'user_001' → {'device_abc', 'device_phone_123', ...}
  
Methods:
  - check_compromise_signs(user_id, session):
    * IF device_id == "unknown": +40 pts
    * IF device_id not in known_devices: +40 pts
    * Return: (score, reasons)
    
Future: Detect auth method changes, impossible travel, failed attempts
```

**Class: BulletproofFraudDetector (MAIN ENGINE)**
```
FLOW:
1. VALIDATE INPUTS
   ├─ Use InputValidator
   ├─ Raise ValueError if invalid
   └─ Return BLOCKED verdict if validation fails

2. CHECK CRITICAL THREATS
   ├─ Run PayeeValidator
   ├─ IF payee_score >= 95: IMMEDIATE BLOCK
   └─ Else: Continue to layers

3. RUN 7 DETECTION LAYERS
   ├─ Layer 1: Behavioral (35% weight)
   │  └─ Call: detect_behavioral_anomaly()
   │  └─ Add to total_score: behavioral_score * 0.35
   │
   ├─ Layer 2: Velocity (10% weight)
   │  └─ Call: check_velocity()
   │  └─ Add: velocity_score * 0.10
   │
   ├─ Layer 3: Flow (8% weight)
   │  └─ Call: analyze_flow()
   │  └─ Add: flow_score * 0.08
   │
   ├─ Layer 4: Payee (30% weight)
   │  └─ Already computed
   │  └─ Add: payee_score * 0.30
   │
   ├─ Layer 5: Compromise (12% weight)
   │  └─ Call: check_compromise_signs()
   │  └─ Add: compromise_score * 0.12
   │
   ├─ Layer 6: Amount (3% weight)
   │  └─ Call: _basic_amount_check()
   │  └─ >₹1cr: 30 pts
   │  └─ Add: amount_score * 0.03
   │
   └─ Layer 7: Website (2% weight)
      └─ Call: _check_website_trust()
      └─ Add: website_score * 0.02

4. CALCULATE FINAL SCORE
   ├─ total_score = sum(all layer contributions)
   ├─ final_score = min(total_score, 100)
   └─ Example: 60*0.35 + 0*0.10 + 0*0.08 + 50*0.30 + 40*0.12 + 0*0.03 + 0*0.02
              = 21 + 0 + 0 + 15 + 4.8 + 0 + 0 = 40.8 → 41

5. DETERMINE VERDICT
   ├─ IF final_score >= 80: FRAUD DETECTED (BLOCKED)
   ├─ ELIF final_score >= 60: SUSPICIOUS (REQUIRES 2FA)
   ├─ ELIF final_score >= 40: CAUTION (APPROVED WITH WARNING)
   └─ ELSE: SAFE (APPROVED)

6. RETURN STRUCTURED RESPONSE
   {
     'status': 'BLOCKED' | 'REQUIRES_2FA' | 'APPROVED_WITH_WARNING' | 'APPROVED',
     'verdict': 'FRAUD_DETECTED' | 'SUSPICIOUS' | 'CAUTION' | 'SAFE',
     'action': Human-readable message,
     'risk_score': 0-100 float,
     'transaction': validated_txn dict,
     'layers': {
       'behavioral': {'score': 60, 'weight': 0.35, 'reasons': [...]},
       'velocity': {'score': 0, 'weight': 0.10, 'reasons': []},
       ...
     },
     'all_reasons': [...],
     'timestamp': ISO8601,
     'user_id': str,
     'recommendation': 'BLOCK_TRANSACTION' | 'REQUIRE_OTP_VERIFICATION' | ...
   }
```

### B. app.py - FLASK BACKEND (640 lines)

**Key Functions:**

```python
create_feature_vector(form_data):
  Purpose: Convert transaction data into ML model input features
  Input: {amount, hour, balance_before, balance_after, txn_type, is_new_payee, is_known_device}
  
  Features Created (25+ features):
  - amount: Direct transaction amount
  - hour: Transaction hour (0-23)
  - balance_before/after: Account balance
  - balance_change: Before - after
  - balance_change_ratio: Change / balance_before
  - is_transfer/is_cash_out/is_payment: Transaction type flags
  - Amount_Log: log(amount) - capture exponential changes
  - Amount_Scaled: min(amount/100000, 10) - normalized
  - is_new_payee: New recipient flag
  - is_known_device: Known device flag
  - is_night: Hour >= 23 or <= 5 → +Risk
  - is_business_hours: 9-17
  - is_round_number: amount % 1000 == 0
  - new_payee_night: is_new_payee AND is_night → High risk combo
  - high_amount_new_device: >₹20k AND unknown device
  - device_location_risk: Unknown device
  - heuristic_risk_score: Manual rule-based scoring
  
  Output: Pandas DataFrame with all features normalized

predict_fraud(feature_df):
  Purpose: Run ensemble of 6 ML models
  
  Models Used:
  1. XGBoost: Gradient boosting, most accurate
  2. Random Forest: Ensemble of decision trees
  3. Neural Network: 3-4 layer feedforward
  4. LSTM: Sequence model for temporal patterns
  5. Logistic Regression: Linear baseline
  6. Isolation Forest: Unsupervised anomaly detection
  
  Logic:
  - Scale features using pre-loaded scaler
  - Get prediction from each model
  - Extract probability (confidence)
  - Vote: count how many predict "FRAUD"
  - Final risk_score = average probability * 100
  
  Additional Scoring:
  - Amount > ₹5,00,000: +40 pts
  - Amount > ₹1,00,000: +35 pts
  - Amount > ₹50,000: +25 pts
  - Hour 23-5 (night): +40 pts
  - Hour 22 or 6: +20 pts
  - New payee: +30 pts
  - Unknown device: +32 pts
  - Balance drain >50%: +28 pts
  - Transfer/CashOut: +15 pts
  
  Output:
  {
    'prediction': 1 (fraud) or 0 (safe),
    'risk_score': 0-100,
    'verdict': 'FRAUD DETECTED' | 'SUSPICIOUS' | 'SAFE TRANSACTION',
    'model_votes': {XGBoost: 'FRAUD', RF: 'SAFE', ...},
    'fraud_votes': 3 (out of 6),
    'explanation': 'High amount (INR 100,000) | Unusual hour (2:00) | ...',
    'shap_reasons': [{'feature': 'Amount', 'impact': 0.35}, ...],
    'txn_id': 'TXN000001'
  }
```

**API Routes:**

```python
POST /api/predict-secure
  Input: JSON {user_id, sender_upi, receiver_upi, amount, hour, device_id, website_url}
  Process:
    1. Validate inputs (InputValidator)
    2. Run 7-layer detection engine
    3. Return fraud verdict
  Output: JSON fraud detection result

POST /api/register
  Input: JSON {pin}
  Process: Create new user, hash PIN
  Output: {user_id, fake_upi_id, balance}

POST /api/login
  Input: {upi_id, pin}
  Output: {user_id, fake_upi_id, balance}

GET /api/balance/<user_id>
  Output: {balance}

POST /api/transfer
  Input: {sender_id, receiver_upi, amount, website_url}
  Process:
    1. Check sender balance
    2. Check receiver exists
    3. Get website reputation
    4. Create feature vector
    5. Run fraud detection
    6. If risk_score < 70: COMPLETE, else BLOCK
  Output: {transaction_id, status, fraud_detected, fraud_score, sender_balance}

GET /api/website-check/<domain>
  Output: {domain, trust_score, is_phishing, is_scam, ssl_valid}

GET / (Dashboard)
  Return HTML dashboard with stats, model info, compliance scores

POST /predict (Manual prediction form)
  Process: Accept form data, run prediction, store in predictions_store
  Return: HTML with prediction result

GET /alerts (Fraud alerts page)
  Return: List of recent alerts

GET /drift (Model performance monitoring)
  Calculate: accuracy based on feedback
  Return: HTML page with drift metrics
```

---

## 6️⃣ CURRENT ISSUES & ERRORS

### Issue 1: ❌ Risk Score Stuck at 44.5 (MAIN PROBLEM)
**Status:** UNRESOLVED  
**Symptoms:**
- Test transaction: ₹100,000 at 2:00 AM with unknown device & new payee
- Expected: risk_score 65-75, status REQUIRES_2FA
- Actual: risk_score 44.5, status APPROVED_WITH_WARNING

**Diagnosis:**
1. File updates were incomplete (truncated downloads from GitHub)
2. Server caching old Python module bytecode in `__pycache__`
3. Weights updated but BASE LAYER SCORES may be too low
4. All 7 layers accumulating correctly NOW but final score still 44.5

**Current Weights:**
- Behavioral: 35% weight (max score 60)
- Payee: 30% weight (max score 50)
- Compromise: 12% weight (max score 40)
- Velocity: 10% weight (max score 0)
- Flow: 8% weight (max score 0)
- Amount: 3% weight (max score 0)
- Website: 2% weight (max score 0)

**Max Possible Score:**
- 60*0.35 + 50*0.30 + 40*0.12 + 0 + 0 + 0 + 0 = 21 + 15 + 4.8 = 40.8

**PROBLEM IDENTIFIED:** Max score with current weights is ~41, threshold for SUSPICIOUS is 60!

**Solution Needed:**
- Increase base layer scores
- Rebalance weights
- Lower thresholds OR increase score multipliers

### Issue 2: ⚠️ Flask Server Cache
**Status:** WORKAROUND FOUND  
**Problem:** Python caches imported modules in `__pycache__`  
**Solution:**
```powershell
Remove-Item -Path "__pycache__" -Recurse -Force -ErrorAction SilentlyContinue
taskkill /F /IM python.exe
python app.py
```

### Issue 3: ⚠️ GitHub Download Truncation
**Status:** RESOLVED  
**Problem:** File downloads occasionally truncated mid-way  
**Solution:** Verify download with `(Get-Content file.py).Count`

### Issue 4: 🔧 Model Training
**Status:** COMPLETED (Models pre-trained)  
**Note:** All models loaded from .pkl and .keras files
**TODO:** Retrain with new data periodically

### Issue 5: 🔧 Database Connection
**Status:** PARTIAL (SQLite works, PostgreSQL pending)  
**Issue:** No persistent storage of transactions currently  
**TODO:** Enable SQLAlchemy ORM, migrate to PostgreSQL for production

---

## 7️⃣ EXECUTED FEATURES & COMPLETED MILESTONES

### ✅ Phase 1-3: Foundation (COMPLETED)
- [x] Project setup & git repo
- [x] Flask backend structure
- [x] Database schema (SQLAlchemy models)
- [x] 6 ML models trained & loaded
- [x] Feature engineering pipeline
- [x] Web dashboard HTML/CSS

### ✅ Phase 4: Production Backend (COMPLETED)
- [x] 7-Layer Bulletproof Fraud Detection Engine
- [x] InputValidator (comprehensive sanitization)
- [x] UserBehaviorAnalyzer (baseline tracking)
- [x] VelocityEngine (burst detection)
- [x] PayeeValidator (scam UPI database)
- [x] CompromiseDetector (device & account takeover)
- [x] BulletproofFraudDetector (ensemble orchestration)
- [x] API endpoints (/api/predict-secure, /api/register, etc.)
- [x] Modular architecture (api.py blueprint)

### ✅ Phase 5: Web Dashboard (COMPLETED)
- [x] Dashboard page (stats, model performance)
- [x] Prediction page (manual testing form)
- [x] Alerts page (fraud alerts log)
- [x] Network page (money mule visualization)
- [x] Profile page (user behavior analysis)
- [x] Explainability page (SHAP feature importance)
- [x] Heatmap page (hourly & type risk heatmap)
- [x] Drift detection page (model accuracy monitoring)
- [x] NPCI analytics page (RBI data integration)
- [x] Reports page (export & analysis)

### ✅ Phase 6: Flutter Mobile App (COMPLETED)
- [x] QR code scanner (detect UPI from QR)
- [x] Risk gauge (animated color-coded meter)
- [x] Layer breakdown (show all 7 layer scores)
- [x] Transaction history (SQLite caching)
- [x] Settings (API configuration)
- [x] Offline mode (local predictions)
- [x] Provider state management

### ✅ Phase 7: UPI Transactions (COMPLETED)
- [x] User registration & login
- [x] PIN-based authentication
- [x] Money transfer with fraud detection
- [x] Balance management
- [x] Transaction recording

### ✅ Phase 8: Data Integration (COMPLETED)
- [x] NPCI UPI data loading
- [x] Bank risk analysis integration
- [x] RBI compliance data
- [x] Website reputation database
- [x] Known scam UPI database

### ✅ Phase 9: Monitoring & Reporting (COMPLETED)
- [x] Real-time alerts
- [x] Model performance tracking
- [x] Feedback collection
- [x] Accuracy drift detection
- [x] Report generation

---

## 8️⃣ REMAINING FEATURES & TODO

### 🔴 CRITICAL (Blocking)
- [ ] **FIX SCORING:** Risk score stuck at 44.5 instead of 60-75
  - Increase base layer scores
  - Rebalance weights
  - Lower thresholds
  - **Action:** Update fraud_detection_v2.py layer scores + weights

### 🟠 HIGH (Important)
- [ ] **Velocity Engine Full Implementation**
  - Connect to database for historical txn queries
  - Implement _get_txns_in_window()
  
- [ ] **Transaction Flow Analyzer**
  - Implement money mule detection
  - Build transaction graph
  - Detect suspicious chains
  
- [ ] **Website Trust Scoring**
  - Implement SSL certificate validation
  - Check domain reputation (phishing databases)
  - Implement _check_website_trust()

- [ ] **PostgreSQL Migration**
  - Replace SQLite with PostgreSQL
  - Connection pooling
  - Production deployment

- [ ] **Model Retraining Pipeline**
  - Automate model retraining on new data
  - Implement cross-validation
  - Track model versioning

### 🟡 MEDIUM (Nice to Have)
- [ ] **Impossible Travel Detection**
  - User location tracking
  - Calculate travel time between txns
  
- [ ] **Auth Method Change Detection**
  - Track login methods (fingerprint, PIN, OTP)
  - Alert on unusual changes
  
- [ ] **Failed Auth Tracking**
  - Count failed login attempts
  - Temporary account lock after N failures
  
- [ ] **Real-time Notifications**
  - Push notifications for alerts
  - Email alerts for blocked transactions
  
- [ ] **Advanced Explainability**
  - SHAP force plots
  - LIME local explanations
  - Counterfactual analysis

- [ ] **Multi-language Support**
  - Hindi, Tamil, Telugu, etc.
  - Localized messages

### 🔵 LOW (Wishlist)
- [ ] **Blockchain Integration**
  - Immutable transaction log
  - Distributed consensus
  
- [ ] **Voice Authentication**
  - Voiceprint-based verification
  
- [ ] **Biometric Integration**
  - Fingerprint/face for Flutter app
  
- [ ] **Advanced Analytics**
  - Predictive fraud trends
  - Seasonal patterns
  - Demographic risk profiles

---

## 9️⃣ DATASET INFORMATION & TRAINING

### Data Sources Used

**1. NPCI UPI Data (npci_processed_data.csv)**
- Monthly UPI transaction statistics
- Total transactions: 21.94 billion (Aug 2025)
- Chargebacks: 202,655
- Used for: Context, compliance reporting, trend analysis

**2. Bank Risk Analysis (bank_risk_analysis.csv)**
- Top 10 banks by chargebacks
- Columns: Code, Bank Name, Total Txns, Chargebacks, CB_Rate
- Used for: Risk scoring by bank, identifying high-risk institutions

**3. RBI Compliance Report (rbi_compliance_report.json)**
- Overall compliance score: 92.2/100
- Grade: A
- Categories:
  - Fraud Detection: 94.5%
  - Chargeback Management: 94.0%
  - Data Governance: 97.0%
  - Model Governance: 90.5%
  - Reporting: 85.0%

**4. ML Training Data (Not included in repo)**
- Assumed: Large dataset of historical UPI transactions
- Labels: Fraud (1) or Safe (0)
- Features: 30+ transaction & user behavioral features

### Model Performance

| Model | Type | AUC | Recall | Precision |
|-------|------|-----|--------|-----------|
| XGBoost | Gradient Boosting | 0.9734 | 92.51% | ~92% |
| Random Forest | Ensemble | 0.9680 | 90.2% | ~90% |
| Neural Network | Deep Learning | 0.9612 | 89.8% | ~89% |
| LSTM | Sequence | 0.9545 | 88.1% | ~88% |
| Logistic Regression | Linear | 0.9210 | 85.3% | ~85% |
| Isolation Forest | Anomaly | 0.8950 | 82.7% | ~83% |

**Ensemble Performance:** ~97% accuracy (combination of all 6)

### Training Procedure (Historical - for reference)

```python
# 1. Data Preparation
- Load transactions CSV
- Feature engineering (30+ features)
- Handle class imbalance (SMOTE or undersampling)
- Train/test split: 80/20

# 2. Preprocessing
- Standardize features (StandardScaler)
- Normalize amounts (log1p)
- Encode categorical (txn_type, is_new_payee, etc.)

# 3. Model Training
for each_model in [XGBoost, RandomForest, NN, LSTM, LogReg, IForest]:
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    auc = roc_auc_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    print(f"{model}: AUC={auc}, Recall={recall}")

# 4. Ensemble
predictions = []
for model in all_models:
    pred = model.predict_proba(X_test)
    predictions.append(pred)
ensemble_pred = np.mean(predictions, axis=0)

# 5. Evaluation
final_auc = roc_auc_score(y_test, ensemble_pred)
final_recall = recall_score(y_test, ensemble_pred > 0.5)

# 6. Save Models
pickle.dump(xgb_model, "mlbfd_mega_xgboost_model.pkl")
pickle.dump(scaler, "mlbfd_mega_scaler.pkl")
pickle.dump(feature_names, "mlbfd_mega_feature_names.pkl")
```

### How to Retrain Models (Future)

```bash
# 1. Prepare new training data
cd backend
python data_pipeline.py --input new_transactions.csv --output processed_data.csv

# 2. Train models
python train_models.py --data processed_data.csv --output models/

# 3. Evaluate
python evaluate_models.py --models models/ --test_data test_set.csv

# 4. Deploy
python deploy_models.py --source models/ --dest backend/models/
```

---

## 🔟 NEXT STEPS & ROADMAP

### IMMEDIATE (This Week)
1. **FIX SCORING BUG** ⚠️
   - [ ] Increase base layer scores significantly
   - [ ] Example: z_score>3 should be 80 pts (not 60)
   - [ ] New payee should be 60 pts (not 40)
   - [ ] Test: risk_score should be 65-75 on test case

2. **Verify Layer Accumulation** ✅ (DONE)
   - [x] All 7 layers now properly accumulating
   - [x] Weights correctly applied
   - [x] Need to adjust individual layer max scores

3. **Integration Test**
   - [ ] Test all endpoints: /api/predict-secure, /api/transfer, etc.
   - [ ] Verify fraud detection on 10+ test cases
   - [ ] Check database persistence

### SHORT TERM (Next 2 Weeks)
4. **Complete Velocity Engine**
   - [ ] Connect to database for txn history queries
   - [ ] Implement sliding window analysis
   - [ ] Test burst detection

5. **Implement Website Trust Scoring**
   - [ ] SSL certificate validation
   - [ ] Domain reputation lookup
   - [ ] Phishing database integration

6. **Production Deployment**
   - [ ] PostgreSQL setup
   - [ ] Docker containerization
   - [ ] Environment configuration (.env)
   - [ ] Load testing

### MEDIUM TERM (1 Month)
7. **Money Mule Detection**
   - [ ] Build transaction flow graph
   - [ ] Implement cycle detection
   - [ ] Profile money mule behavior

8. **Advanced Features**
   - [ ] Impossible travel detection
   - [ ] Auth method change alerts
   - [ ] Failed auth tracking
   - [ ] Real-time notifications

9. **Model Improvements**
   - [ ] Retrain with latest data
   - [ ] Add new features
   - [ ] Implement active learning
   - [ ] A/B test new model versions

### LONG TERM (3+ Months)
10. **Enterprise Features**
    - [ ] Multi-user dashboards
    - [ ] Role-based access control (RBAC)
    - [ ] Audit logs
    - [ ] Compliance reporting (RBI, NPCI)

11. **Integrations**
    - [ ] NPCI API integration (real-time data)
    - [ ] Bank CRM integration
    - [ ] Email/SMS notification service
    - [ ] Blockchain for immutable logging

12. **Mobile Enhancements**
    - [ ] Biometric authentication
    - [ ] Voice-based verification
    - [ ] Offline ML predictions (TensorFlow Lite)
    - [ ] Push notifications

13. **Analytics & Reporting**
    - [ ] Advanced dashboards
    - [ ] Predictive fraud trends
    - [ ] Demographic risk profiles
    - [ ] Seasonal pattern analysis

---

## 📊 PROJECT STATISTICS

- **Total Files:** 50+
- **Backend Code:** 2,000+ lines (Python)
- **Frontend Code:** 3,000+ lines (Flutter Dart)
- **Dashboard Code:** 2,000+ lines (HTML/CSS/JS)
- **Documentation:** 2,000+ lines (Markdown)
- **Total Models:** 6 trained ML models
- **Feature Count:** 30+ engineered features
- **Detection Layers:** 7 comprehensive layers
- **API Endpoints:** 10+ REST endpoints
- **Database Tables:** 5 (User, Transaction, Baseline, Website, Feedback)

---

## 🚀 HOW TO RUN (FOR REFERENCE)

### Backend
```bash
cd backend
pip install -r requirements.txt
python app.py
# Server running on http://localhost:5000
```

### Test Fraud Detection
```powershell
$suspicious = '{
  "user_id": "user_001",
  "sender_upi": "john@okaxis",
  "receiver_upi": "unknown@bank",
  "amount": 100000,
  "hour": 2,
  "device_id": "unknown_device"
}'

Invoke-WebRequest -Uri "http://localhost:5000/api/predict-secure" `
  -Method POST -ContentType "application/json" -Body $suspicious | % Content
```

### Flutter App
```bash
cd flutter_app
flutter pub get
flutter run
```

---

## 🎯 SUCCESS CRITERIA

- [ ] Risk score correctly ranges 0-100
- [ ] All 7 layers contributing properly
- [ ] Suspicious transactions flagged (score 60+)
- [ ] Known fraud blocked (score 95+)
- [ ] <10ms response time for predictions
- [ ] 97%+ ensemble accuracy on test set
- [ ] Database persistence working
- [ ] API endpoints documented & tested
- [ ] Mobile app scanning & displaying results
- [ ] Dashboard showing real-time alerts

---

## 📞 CONTACT & SUPPORT

**Project Owner:** Chirag (@chirag4455)  
**GitHub:** https://github.com/chirag4455/UPI-Fraud-Detection  
**Email:** chiragboss58@gmail.com  
**Status:** 🟢 Active Development  
**Last Updated:** 2026-05-04

---

**END OF MASTER PROMPT**
