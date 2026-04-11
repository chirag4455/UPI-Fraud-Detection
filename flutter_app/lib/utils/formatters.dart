import 'package:intl/intl.dart';

/// Formatting utilities for the UPI Fraud Detection app
class AppFormatters {
  static final _currencyFormat =
      NumberFormat.currency(locale: 'en_IN', symbol: '₹', decimalDigits: 2);
  static final _shortCurrencyFormat =
      NumberFormat.currency(locale: 'en_IN', symbol: '₹', decimalDigits: 0);
  static final _percentFormat =
      NumberFormat.percentPattern()..maximumFractionDigits = 1;
  static final _dateFormat = DateFormat('dd MMM yyyy');
  static final _dateTimeFormat = DateFormat('dd MMM yyyy, hh:mm a');
  static final _timeFormat = DateFormat('hh:mm a');

  // ---------------------------------------------------------------------------
  // Currency
  // ---------------------------------------------------------------------------

  /// Formats amount as Indian Rupees: ₹1,23,456.78
  static String currency(double amount) => _currencyFormat.format(amount);

  /// Short format without decimals: ₹1,23,456
  static String currencyShort(double amount) =>
      _shortCurrencyFormat.format(amount);

  // ---------------------------------------------------------------------------
  // Risk score
  // ---------------------------------------------------------------------------

  /// Formats risk score as a percentage string: "72.4%"
  static String riskPercent(double score) =>
      '${score.toStringAsFixed(1)}%';

  /// Formats risk score 0–100 as a displayable label: "72 / 100"
  static String riskLabel(double score) =>
      '${score.toStringAsFixed(0)} / 100';

  // ---------------------------------------------------------------------------
  // Dates
  // ---------------------------------------------------------------------------

  /// dd MMM yyyy (e.g. "05 Jan 2025")
  static String date(DateTime dt) => _dateFormat.format(dt);

  /// dd MMM yyyy, hh:mm a (e.g. "05 Jan 2025, 02:30 PM")
  static String dateTime(DateTime dt) => _dateTimeFormat.format(dt);

  /// hh:mm a (e.g. "02:30 PM")
  static String time(DateTime dt) => _timeFormat.format(dt);

  // ---------------------------------------------------------------------------
  // VPA masking
  // ---------------------------------------------------------------------------

  /// Masks a VPA for safe display: "me***@okaxis"
  static String maskVpa(String vpa) {
    final parts = vpa.split('@');
    if (parts.length != 2) return vpa;
    final handle = parts[0];
    final domain = parts[1];
    if (handle.length <= 2) return '${handle}***@$domain';
    return '${handle.substring(0, 2)}***@$domain';
  }

  // ---------------------------------------------------------------------------
  // Numbers
  // ---------------------------------------------------------------------------

  /// Compact number: 1234 → "1.2K", 1200000 → "1.2M"
  static String compactNumber(int n) {
    if (n >= 1000000) return '${(n / 1000000).toStringAsFixed(1)}M';
    if (n >= 1000) return '${(n / 1000).toStringAsFixed(1)}K';
    return n.toString();
  }

  /// Formats a percentage 0–1 as "12.5%"
  static String percent(double ratio) => _percentFormat.format(ratio);
}
