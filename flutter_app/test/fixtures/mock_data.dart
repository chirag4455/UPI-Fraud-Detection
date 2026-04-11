// Mock data for tests
import 'package:upi_fraud_detection/models/transaction.dart';
import 'package:upi_fraud_detection/models/prediction.dart';
import 'package:upi_fraud_detection/models/user.dart';

final mockTransaction1 = Transaction(
  id: 'txn-001',
  payeeVpa: 'merchant@okaxis',
  payeeName: 'Test Merchant',
  amount: 500.0,
  timestamp: DateTime(2025, 1, 15, 10, 30),
  status: TransactionStatus.completed,
  isSynced: true,
);

final mockTransaction2 = Transaction(
  id: 'txn-002',
  payeeVpa: 'suspicious@paytm',
  payeeName: 'Unknown Vendor',
  amount: 9999.0,
  timestamp: DateTime(2025, 1, 16, 14, 22),
  status: TransactionStatus.flagged,
);

final mockTransaction3 = Transaction(
  id: 'txn-003',
  payeeVpa: 'fraud@fake',
  payeeName: '',
  amount: 50000.0,
  timestamp: DateTime(2025, 1, 17, 9, 0),
);

final mockPredictionSafe = Prediction(
  transactionId: 'txn-001',
  riskScore: 15.0,
  riskLevel: RiskLevel.safe,
  verdict: 'SAFE',
  layerScores: [
    LayerScore(layer: 'UBTS', score: 12.0, explanation: 'User baseline normal'),
    LayerScore(layer: 'WTS', score: 10.0, explanation: 'Wallet trust high'),
    LayerScore(layer: 'Website Trust', score: 8.0, explanation: 'Domain trusted'),
    LayerScore(layer: 'LSTM', score: 20.0, explanation: 'Sequence normal'),
    LayerScore(
        layer: 'Ensemble', score: 15.0, explanation: 'Ensemble vote: SAFE'),
  ],
  ensembleVotes: [
    EnsembleVote(model: 'XGBoost', probability: 0.08, verdict: 'SAFE'),
    EnsembleVote(model: 'Random Forest', probability: 0.12, verdict: 'SAFE'),
    EnsembleVote(model: 'Logistic Regression', probability: 0.09, verdict: 'SAFE'),
  ],
  timestamp: DateTime(2025, 1, 15, 10, 30, 5),
);

final mockPredictionSuspicious = Prediction(
  transactionId: 'txn-002',
  riskScore: 55.0,
  riskLevel: RiskLevel.suspicious,
  verdict: 'SUSPICIOUS',
  layerScores: [
    LayerScore(
        layer: 'UBTS', score: 50.0, explanation: 'Unusual amount for user'),
    LayerScore(layer: 'WTS', score: 60.0, explanation: 'New device detected'),
    LayerScore(
        layer: 'Website Trust',
        score: 45.0,
        explanation: 'Domain registered recently'),
    LayerScore(
        layer: 'LSTM', score: 55.0, explanation: 'Slightly unusual sequence'),
    LayerScore(
        layer: 'Ensemble',
        score: 55.0,
        explanation: 'Split vote: 3 suspicious, 2 safe'),
  ],
  ensembleVotes: [
    EnsembleVote(model: 'XGBoost', probability: 0.52, verdict: 'SUSPICIOUS'),
    EnsembleVote(model: 'Random Forest', probability: 0.60, verdict: 'SUSPICIOUS'),
    EnsembleVote(
        model: 'Logistic Regression', probability: 0.45, verdict: 'SAFE'),
  ],
  timestamp: DateTime(2025, 1, 16, 14, 22, 10),
);

final mockPredictionFraud = Prediction(
  transactionId: 'txn-003',
  riskScore: 92.0,
  riskLevel: RiskLevel.fraud,
  verdict: 'FRAUD DETECTED',
  layerScores: [
    LayerScore(
        layer: 'UBTS',
        score: 95.0,
        explanation: 'Amount far exceeds user baseline'),
    LayerScore(layer: 'WTS', score: 90.0, explanation: 'Unknown device, new SIM'),
    LayerScore(
        layer: 'Website Trust',
        score: 88.0,
        explanation: 'Phishing domain detected'),
    LayerScore(layer: 'LSTM', score: 93.0, explanation: 'Anomalous sequence'),
    LayerScore(
        layer: 'Ensemble',
        score: 92.0,
        explanation: 'All models vote FRAUD'),
  ],
  ensembleVotes: [
    EnsembleVote(model: 'XGBoost', probability: 0.94, verdict: 'FRAUD'),
    EnsembleVote(model: 'Random Forest', probability: 0.91, verdict: 'FRAUD'),
    EnsembleVote(
        model: 'Logistic Regression', probability: 0.88, verdict: 'FRAUD'),
  ],
  timestamp: DateTime(2025, 1, 17, 9, 0, 8),
);

final mockStats = AppStats(
  totalPredictions: 100,
  fraudCount: 8,
  suspiciousCount: 12,
  safeCount: 80,
  averageRiskScore: 22.5,
  fraudRate: 0.08,
  lastUpdated: DateTime(2025, 1, 17, 12, 0),
);
