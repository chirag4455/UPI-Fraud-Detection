import 'package:test/test.dart';
import 'package:upi_fraud_detection/utils/formatters.dart';

void main() {
  group('AppFormatters.currency', () {
    test('formats whole number correctly', () {
      final result = AppFormatters.currency(1000.0);
      expect(result, contains('1,000'));
      expect(result, contains('₹'));
    });

    test('formats decimal correctly', () {
      final result = AppFormatters.currency(1234.56);
      expect(result, contains('1,234'));
    });

    test('formats zero', () {
      final result = AppFormatters.currency(0.0);
      expect(result, contains('₹'));
    });
  });

  group('AppFormatters.riskPercent', () {
    test('formats score with one decimal', () {
      expect(AppFormatters.riskPercent(72.4), '72.4%');
      expect(AppFormatters.riskPercent(0.0), '0.0%');
      expect(AppFormatters.riskPercent(100.0), '100.0%');
    });
  });

  group('AppFormatters.riskLabel', () {
    test('formats as X / 100', () {
      expect(AppFormatters.riskLabel(72.4), '72 / 100');
      expect(AppFormatters.riskLabel(0.0), '0 / 100');
    });
  });

  group('AppFormatters.maskVpa', () {
    test('masks middle of handle', () {
      expect(AppFormatters.maskVpa('merchant@okaxis'), 'me***@okaxis');
    });

    test('short handle gets stars appended', () {
      expect(AppFormatters.maskVpa('a@upi'), 'a***@upi');
    });

    test('invalid VPA returned unchanged', () {
      expect(AppFormatters.maskVpa('invalid'), 'invalid');
    });

    test('exactly 2 chars handle', () {
      expect(AppFormatters.maskVpa('ab@upi'), 'ab***@upi');
    });
  });

  group('AppFormatters.compactNumber', () {
    test('small number unchanged', () {
      expect(AppFormatters.compactNumber(999), '999');
    });

    test('thousands abbreviated', () {
      expect(AppFormatters.compactNumber(1500), '1.5K');
      expect(AppFormatters.compactNumber(10000), '10.0K');
    });

    test('millions abbreviated', () {
      expect(AppFormatters.compactNumber(1200000), '1.2M');
    });
  });

  group('AppFormatters.percent', () {
    test('ratio to percent string', () {
      final result = AppFormatters.percent(0.082);
      expect(result, contains('8'));
    });

    test('zero percent', () {
      final result = AppFormatters.percent(0.0);
      expect(result, contains('0'));
    });
  });

  group('AppFormatters.date', () {
    test('formats date correctly', () {
      final dt = DateTime(2025, 1, 5);
      expect(AppFormatters.date(dt), '05 Jan 2025');
    });
  });
}
