/// Form validation helpers
class Validators {
  /// Validates a UPI VPA address.
  /// Returns null if valid, error message string if invalid.
  static String? vpa(String? value) {
    if (value == null || value.trim().isEmpty) {
      return 'UPI ID is required';
    }
    final trimmed = value.trim();
    final parts = trimmed.split('@');
    if (parts.length != 2) {
      return 'Invalid UPI ID format (e.g. name@bank)';
    }
    final handle = parts[0];
    final domain = parts[1];
    if (handle.isEmpty) return 'UPI handle cannot be empty';
    if (domain.isEmpty) return 'UPI domain cannot be empty';
    if (handle.length < 3) return 'UPI handle too short';
    if (domain.length < 2) return 'UPI domain too short';
    return null;
  }

  /// Validates a transaction amount.
  static String? amount(String? value) {
    if (value == null || value.trim().isEmpty) {
      return 'Amount is required';
    }
    final parsed = double.tryParse(value.trim());
    if (parsed == null) return 'Enter a valid number';
    if (parsed <= 0) return 'Amount must be greater than zero';
    if (parsed > 200000) return 'Amount exceeds ₹2,00,000 UPI limit';
    return null;
  }

  /// Validates a payee name.
  static String? payeeName(String? value) {
    if (value == null || value.trim().isEmpty) return null; // optional
    if (value.trim().length < 2) return 'Name too short';
    if (value.trim().length > 100) return 'Name too long';
    return null;
  }

  /// Validates an API base URL.
  static String? apiUrl(String? value) {
    if (value == null || value.trim().isEmpty) {
      return 'API URL is required';
    }
    final trimmed = value.trim();
    final uri = Uri.tryParse(trimmed);
    if (uri == null || !uri.hasScheme) {
      return 'Enter a valid URL (e.g. http://192.168.1.100:5000)';
    }
    if (uri.scheme != 'http' && uri.scheme != 'https') {
      return 'URL must start with http:// or https://';
    }
    return null;
  }

  /// Validates that a string is not empty.
  static String? required(String? value, [String fieldName = 'This field']) {
    if (value == null || value.trim().isEmpty) {
      return '$fieldName is required';
    }
    return null;
  }
}
