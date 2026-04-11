import 'package:json_annotation/json_annotation.dart';

part 'user.g.dart';

@JsonSerializable()
class User {
  final String id;
  final String name;
  final String? email;
  final String? phone;
  final DateTime createdAt;
  final Map<String, dynamic>? preferences;

  const User({
    required this.id,
    required this.name,
    this.email,
    this.phone,
    required this.createdAt,
    this.preferences,
  });

  factory User.fromJson(Map<String, dynamic> json) => _$UserFromJson(json);

  Map<String, dynamic> toJson() => _$UserToJson(this);

  User copyWith({
    String? id,
    String? name,
    String? email,
    String? phone,
    DateTime? createdAt,
    Map<String, dynamic>? preferences,
  }) {
    return User(
      id: id ?? this.id,
      name: name ?? this.name,
      email: email ?? this.email,
      phone: phone ?? this.phone,
      createdAt: createdAt ?? this.createdAt,
      preferences: preferences ?? this.preferences,
    );
  }

  @override
  String toString() => 'User(id: $id, name: $name)';

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is User && runtimeType == other.runtimeType && id == other.id;

  @override
  int get hashCode => id.hashCode;
}

@JsonSerializable()
class AppStats {
  final int totalPredictions;
  final int fraudCount;
  final int suspiciousCount;
  final int safeCount;
  final double averageRiskScore;
  final double fraudRate;
  final DateTime? lastUpdated;

  const AppStats({
    required this.totalPredictions,
    required this.fraudCount,
    required this.suspiciousCount,
    required this.safeCount,
    required this.averageRiskScore,
    required this.fraudRate,
    this.lastUpdated,
  });

  factory AppStats.fromJson(Map<String, dynamic> json) =>
      _$AppStatsFromJson(json);

  Map<String, dynamic> toJson() => _$AppStatsToJson(this);

  factory AppStats.empty() => AppStats(
        totalPredictions: 0,
        fraudCount: 0,
        suspiciousCount: 0,
        safeCount: 0,
        averageRiskScore: 0.0,
        fraudRate: 0.0,
      );
}
