import 'package:test/test.dart';
import 'package:upi_fraud_detection/utils/validators.dart';

void main() {
  group('Validators.vpa', () {
    test('valid VPA passes', () {
      expect(Validators.vpa('merchant@okaxis'), isNull);
      expect(Validators.vpa('user123@upi'), isNull);
      expect(Validators.vpa('test.user@icici'), isNull);
    });

    test('null returns error', () {
      expect(Validators.vpa(null), isNotNull);
    });

    test('empty string returns error', () {
      expect(Validators.vpa(''), isNotNull);
      expect(Validators.vpa('  '), isNotNull);
    });

    test('missing @ returns error', () {
      expect(Validators.vpa('merchantokaxis'), isNotNull);
    });

    test('multiple @ returns error', () {
      expect(Validators.vpa('a@b@c'), isNotNull);
    });

    test('short handle returns error', () {
      expect(Validators.vpa('ab@upi'), isNotNull);
    });

    test('empty domain returns error', () {
      expect(Validators.vpa('merchant@'), isNotNull);
    });
  });

  group('Validators.amount', () {
    test('valid amounts pass', () {
      expect(Validators.amount('100'), isNull);
      expect(Validators.amount('0.01'), isNull);
      expect(Validators.amount('199999.99'), isNull);
    });

    test('null returns error', () {
      expect(Validators.amount(null), isNotNull);
    });

    test('empty returns error', () {
      expect(Validators.amount(''), isNotNull);
    });

    test('zero returns error', () {
      expect(Validators.amount('0'), isNotNull);
    });

    test('negative returns error', () {
      expect(Validators.amount('-100'), isNotNull);
    });

    test('exceeds UPI limit returns error', () {
      expect(Validators.amount('200001'), isNotNull);
    });

    test('non-numeric returns error', () {
      expect(Validators.amount('abc'), isNotNull);
    });
  });

  group('Validators.payeeName', () {
    test('valid names pass', () {
      expect(Validators.payeeName('Test Merchant'), isNull);
      expect(Validators.payeeName(null), isNull);  // optional
      expect(Validators.payeeName(''), isNull);    // optional
    });

    test('single char returns error', () {
      expect(Validators.payeeName('A'), isNotNull);
    });

    test('too long returns error', () {
      expect(Validators.payeeName('A' * 101), isNotNull);
    });
  });

  group('Validators.apiUrl', () {
    test('valid HTTP URL passes', () {
      expect(Validators.apiUrl('http://192.168.1.1:5000'), isNull);
      expect(Validators.apiUrl('https://api.example.com'), isNull);
    });

    test('null returns error', () {
      expect(Validators.apiUrl(null), isNotNull);
    });

    test('empty returns error', () {
      expect(Validators.apiUrl(''), isNotNull);
    });

    test('invalid scheme returns error', () {
      expect(Validators.apiUrl('ftp://example.com'), isNotNull);
    });

    test('no scheme returns error', () {
      expect(Validators.apiUrl('example.com'), isNotNull);
    });
  });

  group('Validators.required', () {
    test('non-empty passes', () {
      expect(Validators.required('value'), isNull);
    });

    test('null returns error', () {
      expect(Validators.required(null), isNotNull);
    });

    test('whitespace returns error', () {
      expect(Validators.required('   '), isNotNull);
    });
  });
}
