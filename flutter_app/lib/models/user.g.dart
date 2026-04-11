// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'user.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

User _$UserFromJson(Map<String, dynamic> json) => User(
      id: json['id'] as String,
      name: json['name'] as String,
      email: json['email'] as String?,
      phone: json['phone'] as String?,
      createdAt: DateTime.parse(json['createdAt'] as String),
      preferences: json['preferences'] as Map<String, dynamic>?,
    );

Map<String, dynamic> _$UserToJson(User instance) => <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
      'email': instance.email,
      'phone': instance.phone,
      'createdAt': instance.createdAt.toIso8601String(),
      'preferences': instance.preferences,
    };

AppStats _$AppStatsFromJson(Map<String, dynamic> json) => AppStats(
      totalPredictions: json['totalPredictions'] as int,
      fraudCount: json['fraudCount'] as int,
      suspiciousCount: json['suspiciousCount'] as int,
      safeCount: json['safeCount'] as int,
      averageRiskScore: (json['averageRiskScore'] as num).toDouble(),
      fraudRate: (json['fraudRate'] as num).toDouble(),
      lastUpdated: json['lastUpdated'] == null
          ? null
          : DateTime.parse(json['lastUpdated'] as String),
    );

Map<String, dynamic> _$AppStatsToJson(AppStats instance) => <String, dynamic>{
      'totalPredictions': instance.totalPredictions,
      'fraudCount': instance.fraudCount,
      'suspiciousCount': instance.suspiciousCount,
      'safeCount': instance.safeCount,
      'averageRiskScore': instance.averageRiskScore,
      'fraudRate': instance.fraudRate,
      'lastUpdated': instance.lastUpdated?.toIso8601String(),
    };
