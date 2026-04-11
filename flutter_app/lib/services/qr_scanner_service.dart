/// Service for parsing and validating UPI QR codes locally (offline support)
class QrScannerService {
  static final RegExp _upiSchemeRe = RegExp(r'^upi://pay\?', caseSensitive: false);

  /// Parse a raw QR string into a structured UPI payment map.
  ///
  /// Supports the standard UPI deep-link format:
  ///   `upi://pay?pa=<vpa>&pn=<name>&am=<amount>&cu=<currency>&tn=<note>`
  ///
  /// Returns a map with keys: [vpa], [payeeName], [amount], [currency], [note].
  /// Throws [ArgumentError] if the QR is not a valid UPI link.
  static Map<String, String?> parseUpiQr(String raw) {
    final trimmed = raw.trim();

    if (!_upiSchemeRe.hasMatch(trimmed)) {
      throw ArgumentError('Not a valid UPI QR code: $trimmed');
    }

    // Replace scheme so we can parse as URL
    final urlString = trimmed.replaceFirst(
        RegExp(r'^upi://', caseSensitive: false), 'https://upi/');

    final uri = Uri.tryParse(urlString);
    if (uri == null) {
      throw ArgumentError('Malformed UPI QR code: $trimmed');
    }

    final vpa = uri.queryParameters['pa'];
    if (vpa == null || vpa.isEmpty) {
      throw ArgumentError('UPI QR missing payee address (pa): $trimmed');
    }

    return {
      'vpa': vpa,
      'payeeName': uri.queryParameters['pn'],
      'amount': uri.queryParameters['am'],
      'currency': uri.queryParameters['cu'] ?? 'INR',
      'note': uri.queryParameters['tn'],
      'merchantCode': uri.queryParameters['mc'],
      'transactionId': uri.queryParameters['tr'],
    };
  }

  /// Validates a UPI VPA string (basic format check).
  /// A valid VPA looks like: `name@bank` or `number@upi`
  static bool isValidVpa(String vpa) {
    final parts = vpa.split('@');
    if (parts.length != 2) return false;
    final handle = parts[0].trim();
    final domain = parts[1].trim();
    return handle.isNotEmpty && domain.isNotEmpty && !domain.contains('@');
  }

  /// Attempts to detect if a QR is a UPI link without throwing.
  static bool isUpiQr(String raw) {
    return _upiSchemeRe.hasMatch(raw.trim());
  }

  /// Builds a UPI QR deep-link from components (useful for testing).
  static String buildUpiQr({
    required String vpa,
    String? payeeName,
    double? amount,
    String currency = 'INR',
    String? note,
  }) {
    final params = <String>['pa=${Uri.encodeComponent(vpa)}'];
    if (payeeName != null) params.add('pn=${Uri.encodeComponent(payeeName)}');
    if (amount != null) params.add('am=${amount.toStringAsFixed(2)}');
    params.add('cu=$currency');
    if (note != null) params.add('tn=${Uri.encodeComponent(note)}');
    return 'upi://pay?${params.join('&')}';
  }
}
