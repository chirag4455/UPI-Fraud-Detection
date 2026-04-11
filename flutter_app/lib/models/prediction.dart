import 'package:json_annotation/json_annotation.dart';

part 'prediction.g.dart';

enum RiskLevel {
  safe,
  suspicious,
  fraud,
}

@JsonSerializable()
class LayerScore {
  final String layer;
  final double score;
  final String explanation;
  final Map<String, dynamic>? details;

  const LayerScore({
    required this.layer,
    required this.score,
    required this.explanation,
    this.details,
  });

  factory LayerScore.fromJson(Map<String, dynamic> json) =>
      _$LayerScoreFromJson(json);

  Map<String, dynamic> toJson() => _$LayerScoreToJson(this);
}

@JsonSerializable()
class EnsembleVote {
  final String model;
  final double probability;
  final String verdict;

  const EnsembleVote({
    required this.model,
    required this.probability,
    required this.verdict,
  });

  factory EnsembleVote.fromJson(Map<String, dynamic> json) =>
      _$EnsembleVoteFromJson(json);

  Map<String, dynamic> toJson() => _$EnsembleVoteToJson(this);
}

@JsonSerializable()
class Prediction {
  final String transactionId;
  final double riskScore;
  final RiskLevel riskLevel;
  final String verdict;
  final List<LayerScore> layerScores;
  final List<EnsembleVote> ensembleVotes;
  final DateTime timestamp;
  final bool isCached;
  final String? sessionId;

  const Prediction({
    required this.transactionId,
    required this.riskScore,
    required this.riskLevel,
    required this.verdict,
    required this.layerScores,
    required this.ensembleVotes,
    required this.timestamp,
    this.isCached = false,
    this.sessionId,
  });

  factory Prediction.fromJson(Map<String, dynamic> json) =>
      _$PredictionFromJson(json);

  Map<String, dynamic> toJson() => _$PredictionToJson(this);

  /// Returns a RiskLevel enum based on riskScore value
  static RiskLevel riskLevelFromScore(double score) {
    if (score < 30.0) return RiskLevel.safe;
    if (score < 60.0) return RiskLevel.suspicious;
    return RiskLevel.fraud;
  }

  /// Returns human-readable verdict string
  String get verdictLabel {
    switch (riskLevel) {
      case RiskLevel.safe:
        return 'SAFE';
      case RiskLevel.suspicious:
        return 'SUSPICIOUS';
      case RiskLevel.fraud:
        return 'FRAUD DETECTED';
    }
  }

  @override
  String toString() =>
      'Prediction(txn: $transactionId, score: $riskScore, level: $riskLevel)';

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is Prediction &&
          runtimeType == other.runtimeType &&
          transactionId == other.transactionId;

  @override
  int get hashCode => transactionId.hashCode;
}
