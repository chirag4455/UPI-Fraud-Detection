// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'transaction.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

Transaction _$TransactionFromJson(Map<String, dynamic> json) => Transaction(
      id: json['id'] as String,
      payeeVpa: json['payeeVpa'] as String,
      payeeName: json['payeeName'] as String,
      amount: (json['amount'] as num).toDouble(),
      currency: json['currency'] as String? ?? 'INR',
      timestamp: DateTime.parse(json['timestamp'] as String),
      status: $enumDecodeNullable(_$TransactionStatusEnumMap, json['status']) ??
          TransactionStatus.pending,
      note: json['note'] as String?,
      deviceId: json['deviceId'] as String?,
      latitude: (json['latitude'] as num?)?.toDouble(),
      longitude: (json['longitude'] as num?)?.toDouble(),
      isSynced: json['isSynced'] as bool? ?? false,
    );

Map<String, dynamic> _$TransactionToJson(Transaction instance) =>
    <String, dynamic>{
      'id': instance.id,
      'payeeVpa': instance.payeeVpa,
      'payeeName': instance.payeeName,
      'amount': instance.amount,
      'currency': instance.currency,
      'timestamp': instance.timestamp.toIso8601String(),
      'status': _$TransactionStatusEnumMap[instance.status]!,
      'note': instance.note,
      'deviceId': instance.deviceId,
      'latitude': instance.latitude,
      'longitude': instance.longitude,
      'isSynced': instance.isSynced,
    };

const _$TransactionStatusEnumMap = {
  TransactionStatus.pending: 'pending',
  TransactionStatus.completed: 'completed',
  TransactionStatus.failed: 'failed',
  TransactionStatus.flagged: 'flagged',
};

T _$enumDecodeNullable<T>(
  Map<T, dynamic> enumValues,
  dynamic source, {
  T? unknownValue,
}) {
  if (source == null) {
    return unknownValue ?? (throw ArgumentError('A value must be provided. Supported values: ${enumValues.values.join(', ')}'));
  }
  return _$enumDecode(enumValues, source, unknownValue: unknownValue);
}

T _$enumDecode<T>(
  Map<T, dynamic> enumValues,
  dynamic source, {
  T? unknownValue,
}) {
  if (source == null) {
    throw ArgumentError('A value must be provided. Supported values: ${enumValues.values.join(', ')}');
  }
  for (final entry in enumValues.entries) {
    if (entry.value == source) return entry.key;
  }
  if (unknownValue == null) {
    throw ArgumentError('`$source` is not one of the supported values: ${enumValues.values.join(', ')}');
  }
  return unknownValue;
}
