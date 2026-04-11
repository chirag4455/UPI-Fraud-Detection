import 'package:json_annotation/json_annotation.dart';

part 'transaction.g.dart';

enum TransactionStatus {
  pending,
  completed,
  failed,
  flagged,
}

@JsonSerializable()
class Transaction {
  final String id;
  final String payeeVpa;
  final String payeeName;
  final double amount;
  final String currency;
  final DateTime timestamp;
  final TransactionStatus status;
  final String? note;
  final String? deviceId;
  final double? latitude;
  final double? longitude;
  final bool isSynced;

  const Transaction({
    required this.id,
    required this.payeeVpa,
    required this.payeeName,
    required this.amount,
    this.currency = 'INR',
    required this.timestamp,
    this.status = TransactionStatus.pending,
    this.note,
    this.deviceId,
    this.latitude,
    this.longitude,
    this.isSynced = false,
  });

  factory Transaction.fromJson(Map<String, dynamic> json) =>
      _$TransactionFromJson(json);

  Map<String, dynamic> toJson() => _$TransactionToJson(this);

  Transaction copyWith({
    String? id,
    String? payeeVpa,
    String? payeeName,
    double? amount,
    String? currency,
    DateTime? timestamp,
    TransactionStatus? status,
    String? note,
    String? deviceId,
    double? latitude,
    double? longitude,
    bool? isSynced,
  }) {
    return Transaction(
      id: id ?? this.id,
      payeeVpa: payeeVpa ?? this.payeeVpa,
      payeeName: payeeName ?? this.payeeName,
      amount: amount ?? this.amount,
      currency: currency ?? this.currency,
      timestamp: timestamp ?? this.timestamp,
      status: status ?? this.status,
      note: note ?? this.note,
      deviceId: deviceId ?? this.deviceId,
      latitude: latitude ?? this.latitude,
      longitude: longitude ?? this.longitude,
      isSynced: isSynced ?? this.isSynced,
    );
  }

  /// Mask VPA for display (e.g. "merchant@okaxis" → "me***@okaxis")
  String get maskedVpa {
    final parts = payeeVpa.split('@');
    if (parts.length != 2) return payeeVpa;
    final handle = parts[0];
    final domain = parts[1];
    if (handle.length <= 2) return '$handle***@$domain';
    return '${handle.substring(0, 2)}***@$domain';
  }

  @override
  String toString() => 'Transaction(id: $id, payee: $payeeVpa, amount: $amount)';

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is Transaction && runtimeType == other.runtimeType && id == other.id;

  @override
  int get hashCode => id.hashCode;
}
