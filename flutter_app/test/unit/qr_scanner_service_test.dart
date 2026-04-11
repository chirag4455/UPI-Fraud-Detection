import 'package:test/test.dart';
import 'package:upi_fraud_detection/services/qr_scanner_service.dart';

void main() {
  group('QrScannerService.parseUpiQr', () {
    test('parses full UPI QR correctly', () {
      const raw =
          'upi://pay?pa=merchant@okaxis&pn=Test+Merchant&am=500.00&cu=INR&tn=Groceries';
      final result = QrScannerService.parseUpiQr(raw);
      expect(result['vpa'], 'merchant@okaxis');
      expect(result['payeeName'], 'Test+Merchant');
      expect(result['amount'], '500.00');
      expect(result['currency'], 'INR');
      expect(result['note'], 'Groceries');
    });

    test('parses minimal QR (pa only)', () {
      const raw = 'upi://pay?pa=user@paytm';
      final result = QrScannerService.parseUpiQr(raw);
      expect(result['vpa'], 'user@paytm');
      expect(result['payeeName'], isNull);
      expect(result['amount'], isNull);
    });

    test('throws on non-UPI QR', () {
      expect(
        () => QrScannerService.parseUpiQr('https://google.com'),
        throwsArgumentError,
      );
    });

    test('throws on QR missing pa', () {
      expect(
        () => QrScannerService.parseUpiQr('upi://pay?pn=Test&am=100'),
        throwsArgumentError,
      );
    });

    test('is case-insensitive for scheme', () {
      const raw = 'UPI://pay?pa=test@upi';
      final result = QrScannerService.parseUpiQr(raw);
      expect(result['vpa'], 'test@upi');
    });

    test('handles encoded characters in pn', () {
      const raw = 'upi://pay?pa=shop@icici&pn=My%20Shop&am=100';
      final result = QrScannerService.parseUpiQr(raw);
      expect(result['payeeName'], 'My Shop');
    });
  });

  group('QrScannerService.isValidVpa', () {
    test('valid VPAs pass', () {
      expect(QrScannerService.isValidVpa('merchant@okaxis'), isTrue);
      expect(QrScannerService.isValidVpa('9876543210@paytm'), isTrue);
    });

    test('invalid VPAs fail', () {
      expect(QrScannerService.isValidVpa('noatsign'), isFalse);
      expect(QrScannerService.isValidVpa('@nodomain'), isFalse);
      expect(QrScannerService.isValidVpa('nohandle@'), isFalse);
      expect(QrScannerService.isValidVpa('a@b@c'), isFalse);
    });
  });

  group('QrScannerService.isUpiQr', () {
    test('detects UPI QR', () {
      expect(QrScannerService.isUpiQr('upi://pay?pa=a@b'), isTrue);
    });

    test('rejects non-UPI', () {
      expect(QrScannerService.isUpiQr('https://example.com'), isFalse);
    });
  });

  group('QrScannerService.buildUpiQr', () {
    test('builds valid UPI deep-link', () {
      final qr = QrScannerService.buildUpiQr(
        vpa: 'merchant@okaxis',
        payeeName: 'My Store',
        amount: 250.0,
        note: 'Payment',
      );
      expect(qr, startsWith('upi://pay?'));
      expect(qr, contains('pa=merchant%40okaxis'));
      expect(qr, contains('am=250.00'));
    });

    test('built QR can be parsed back', () {
      final qr = QrScannerService.buildUpiQr(
        vpa: 'test@upi',
        amount: 100.0,
      );
      final parsed = QrScannerService.parseUpiQr(qr);
      expect(parsed['vpa'], 'test@upi');
      expect(parsed['amount'], '100.00');
    });
  });
}
