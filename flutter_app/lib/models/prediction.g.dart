// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'prediction.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

LayerScore _$LayerScoreFromJson(Map<String, dynamic> json) => LayerScore(
      layer: json['layer'] as String,
      score: (json['score'] as num).toDouble(),
      explanation: json['explanation'] as String,
      details: json['details'] as Map<String, dynamic>?,
    );

Map<String, dynamic> _$LayerScoreToJson(LayerScore instance) =>
    <String, dynamic>{
      'layer': instance.layer,
      'score': instance.score,
      'explanation': instance.explanation,
      'details': instance.details,
    };

EnsembleVote _$EnsembleVoteFromJson(Map<String, dynamic> json) => EnsembleVote(
      model: json['model'] as String,
      probability: (json['probability'] as num).toDouble(),
      verdict: json['verdict'] as String,
    );

Map<String, dynamic> _$EnsembleVoteToJson(EnsembleVote instance) =>
    <String, dynamic>{
      'model': instance.model,
      'probability': instance.probability,
      'verdict': instance.verdict,
    };

Prediction _$PredictionFromJson(Map<String, dynamic> json) => Prediction(
      transactionId: json['transactionId'] as String,
      riskScore: (json['riskScore'] as num).toDouble(),
      riskLevel: $enumDecode(_$RiskLevelEnumMap, json['riskLevel']),
      verdict: json['verdict'] as String,
      layerScores: (json['layerScores'] as List<dynamic>)
          .map((e) => LayerScore.fromJson(e as Map<String, dynamic>))
          .toList(),
      ensembleVotes: (json['ensembleVotes'] as List<dynamic>)
          .map((e) => EnsembleVote.fromJson(e as Map<String, dynamic>))
          .toList(),
      timestamp: DateTime.parse(json['timestamp'] as String),
      isCached: json['isCached'] as bool? ?? false,
      sessionId: json['sessionId'] as String?,
    );

Map<String, dynamic> _$PredictionToJson(Prediction instance) =>
    <String, dynamic>{
      'transactionId': instance.transactionId,
      'riskScore': instance.riskScore,
      'riskLevel': _$RiskLevelEnumMap[instance.riskLevel]!,
      'verdict': instance.verdict,
      'layerScores': instance.layerScores.map((e) => e.toJson()).toList(),
      'ensembleVotes': instance.ensembleVotes.map((e) => e.toJson()).toList(),
      'timestamp': instance.timestamp.toIso8601String(),
      'isCached': instance.isCached,
      'sessionId': instance.sessionId,
    };

const _$RiskLevelEnumMap = {
  RiskLevel.safe: 'safe',
  RiskLevel.suspicious: 'suspicious',
  RiskLevel.fraud: 'fraud',
};

T _$enumDecode<T>(
  Map<T, dynamic> enumValues,
  dynamic source, {
  T? unknownValue,
}) {
  if (source == null) {
    throw ArgumentError(
        'A value must be provided. Supported values: ${enumValues.values.join(', ')}');
  }
  for (final entry in enumValues.entries) {
    if (entry.value == source) return entry.key;
  }
  if (unknownValue == null) {
    throw ArgumentError(
        '`$source` is not one of the supported values: ${enumValues.values.join(', ')}');
  }
  return unknownValue;
}
