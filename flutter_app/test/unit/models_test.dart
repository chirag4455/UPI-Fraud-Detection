import 'package:test/test.dart';
import 'package:upi_fraud_detection/models/transaction.dart';
import 'package:upi_fraud_detection/models/prediction.dart';
import 'package:upi_fraud_detection/models/user.dart';
import '../fixtures/mock_data.dart';

void main() {
  group('Transaction model', () {
    test('creates correctly', () {
      expect(mockTransaction1.id, 'txn-001');
      expect(mockTransaction1.payeeVpa, 'merchant@okaxis');
      expect(mockTransaction1.amount, 500.0);
      expect(mockTransaction1.currency, 'INR');
      expect(mockTransaction1.status, TransactionStatus.completed);
    });

    test('maskedVpa hides middle characters', () {
      expect(mockTransaction1.maskedVpa, 'me***@okaxis');
    });

    test('maskedVpa handles short handle', () {
      final t = Transaction(
        id: 'x',
        payeeVpa: 'a@upi',
        payeeName: '',
        amount: 10,
        timestamp: DateTime.now(),
      );
      expect(t.maskedVpa, 'a***@upi');
    });

    test('maskedVpa preserves invalid VPA unchanged', () {
      final t = Transaction(
        id: 'x',
        payeeVpa: 'notavpa',
        payeeName: '',
        amount: 10,
        timestamp: DateTime.now(),
      );
      expect(t.maskedVpa, 'notavpa');
    });

    test('copyWith preserves unchanged fields', () {
      final copy = mockTransaction1.copyWith(amount: 999.0);
      expect(copy.amount, 999.0);
      expect(copy.payeeVpa, mockTransaction1.payeeVpa);
      expect(copy.id, mockTransaction1.id);
    });

    test('equality based on id', () {
      final same = mockTransaction1.copyWith(amount: 9999.0);
      expect(same, equals(mockTransaction1));
    });

    test('toJson / fromJson round-trip', () {
      final json = mockTransaction1.toJson();
      final restored = Transaction.fromJson(json);
      expect(restored.id, mockTransaction1.id);
      expect(restored.amount, mockTransaction1.amount);
      expect(restored.payeeVpa, mockTransaction1.payeeVpa);
      expect(restored.status, mockTransaction1.status);
    });

    test('fromJson handles missing optional fields', () {
      final json = {
        'id': 'test',
        'payeeVpa': 'a@b',
        'payeeName': 'Name',
        'amount': 100.0,
        'timestamp': DateTime.now().toIso8601String(),
      };
      final t = Transaction.fromJson(json);
      expect(t.note, isNull);
      expect(t.deviceId, isNull);
      expect(t.isSynced, isFalse);
    });
  });

  group('Prediction model', () {
    test('riskLevelFromScore returns correct level', () {
      expect(Prediction.riskLevelFromScore(0), RiskLevel.safe);
      expect(Prediction.riskLevelFromScore(29.9), RiskLevel.safe);
      expect(Prediction.riskLevelFromScore(30), RiskLevel.suspicious);
      expect(Prediction.riskLevelFromScore(59.9), RiskLevel.suspicious);
      expect(Prediction.riskLevelFromScore(60), RiskLevel.fraud);
      expect(Prediction.riskLevelFromScore(100), RiskLevel.fraud);
    });

    test('verdictLabel returns correct string', () {
      expect(mockPredictionSafe.verdictLabel, 'SAFE');
      expect(mockPredictionSuspicious.verdictLabel, 'SUSPICIOUS');
      expect(mockPredictionFraud.verdictLabel, 'FRAUD DETECTED');
    });

    test('layerScores list has correct length', () {
      expect(mockPredictionSafe.layerScores.length, 5);
      expect(mockPredictionFraud.layerScores.length, 5);
    });

    test('ensembleVotes parsed correctly', () {
      expect(mockPredictionSafe.ensembleVotes.length, 3);
      expect(mockPredictionSafe.ensembleVotes.first.model, 'XGBoost');
      expect(mockPredictionSafe.ensembleVotes.first.verdict, 'SAFE');
    });

    test('toJson / fromJson round-trip', () {
      final json = mockPredictionSafe.toJson();
      final restored = Prediction.fromJson(json);
      expect(restored.transactionId, mockPredictionSafe.transactionId);
      expect(restored.riskScore, mockPredictionSafe.riskScore);
      expect(restored.riskLevel, mockPredictionSafe.riskLevel);
      expect(restored.layerScores.length, mockPredictionSafe.layerScores.length);
    });

    test('equality based on transactionId', () {
      expect(
        mockPredictionSafe,
        equals(Prediction(
          transactionId: 'txn-001',
          riskScore: 999,
          riskLevel: RiskLevel.fraud,
          verdict: 'X',
          layerScores: const [],
          ensembleVotes: const [],
          timestamp: DateTime.now(),
        )),
      );
    });
  });

  group('AppStats model', () {
    test('empty factory creates zero stats', () {
      final s = AppStats.empty();
      expect(s.totalPredictions, 0);
      expect(s.fraudRate, 0.0);
    });

    test('fromJson / toJson round-trip', () {
      final json = mockStats.toJson();
      final restored = AppStats.fromJson(json);
      expect(restored.totalPredictions, mockStats.totalPredictions);
      expect(restored.fraudCount, mockStats.fraudCount);
      expect(restored.fraudRate, mockStats.fraudRate);
    });
  });
}
