import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../config/api_config.dart';
import '../models/prediction.dart';
import '../models/transaction.dart';
import '../models/user.dart';

/// Centralized HTTP API service using Dio
class ApiService {
  late Dio _dio;
  String _baseUrl;

  ApiService({String? baseUrl}) : _baseUrl = baseUrl ?? ApiConfig.defaultBaseUrl {
    _initDio();
  }

  void _initDio() {
    _dio = Dio(BaseOptions(
      baseUrl: _baseUrl,
      connectTimeout: const Duration(milliseconds: ApiConfig.connectTimeout),
      receiveTimeout: const Duration(milliseconds: ApiConfig.receiveTimeout),
      sendTimeout: const Duration(milliseconds: ApiConfig.sendTimeout),
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    ));

    // Logging interceptor (debug only)
    _dio.interceptors.add(LogInterceptor(
      requestBody: true,
      responseBody: true,
      error: true,
    ));

    // Retry interceptor with exponential back-off
    _dio.interceptors.add(_RetryInterceptor(_dio));
  }

  /// Update base URL at runtime (from settings)
  Future<void> updateBaseUrl(String url) async {
    _baseUrl = url;
    _dio.options.baseUrl = url;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(ApiConfig.prefBaseUrl, url);
  }

  // ---------------------------------------------------------------------------
  // Health check
  // ---------------------------------------------------------------------------

  /// Returns true if API is reachable and healthy
  Future<bool> checkHealth() async {
    try {
      final response = await _dio.get(ApiConfig.healthEndpoint);
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  // ---------------------------------------------------------------------------
  // Prediction
  // ---------------------------------------------------------------------------

  /// Sends transaction data to the /api/predict endpoint and returns [Prediction]
  Future<Prediction> predict(Transaction transaction) async {
    final payload = {
      'transaction_id': transaction.id,
      'payee_vpa': transaction.payeeVpa,
      'payee_name': transaction.payeeName,
      'amount': transaction.amount,
      'currency': transaction.currency,
      'timestamp': transaction.timestamp.toIso8601String(),
      if (transaction.deviceId != null) 'device_id': transaction.deviceId,
      if (transaction.latitude != null) 'latitude': transaction.latitude,
      if (transaction.longitude != null) 'longitude': transaction.longitude,
    };

    final response = await _dio.post(
      ApiConfig.predictEndpoint,
      data: jsonEncode(payload),
    );

    return _parsePredictionResponse(transaction.id, response.data);
  }

  Prediction _parsePredictionResponse(
      String transactionId, Map<String, dynamic> data) {
    final riskScore = (data['risk_score'] as num?)?.toDouble() ?? 0.0;
    final riskLevel = Prediction.riskLevelFromScore(riskScore);

    final layerScores = <LayerScore>[];
    if (data['layers'] is Map) {
      final layers = data['layers'] as Map<String, dynamic>;
      layers.forEach((key, value) {
        layerScores.add(LayerScore(
          layer: key,
          score: (value['score'] as num?)?.toDouble() ?? 0.0,
          explanation: (value['explanation'] as String?) ?? '',
          details: value['details'] as Map<String, dynamic>?,
        ));
      });
    }

    final votes = <EnsembleVote>[];
    if (data['ensemble_votes'] is List) {
      for (final v in (data['ensemble_votes'] as List)) {
        votes.add(EnsembleVote(
          model: v['model'] as String? ?? '',
          probability: (v['probability'] as num?)?.toDouble() ?? 0.0,
          verdict: v['verdict'] as String? ?? '',
        ));
      }
    }

    return Prediction(
      transactionId: transactionId,
      riskScore: riskScore,
      riskLevel: riskLevel,
      verdict: data['verdict'] as String? ?? riskLevel.name.toUpperCase(),
      layerScores: layerScores,
      ensembleVotes: votes,
      timestamp: DateTime.now(),
      sessionId: data['session_id'] as String?,
    );
  }

  // ---------------------------------------------------------------------------
  // QR parsing
  // ---------------------------------------------------------------------------

  /// Parses a raw UPI QR string via the backend
  Future<Map<String, dynamic>> parseQrCode(String rawQr) async {
    final response = await _dio.post(
      ApiConfig.parseQrEndpoint,
      data: jsonEncode({'qr_data': rawQr}),
    );
    return response.data as Map<String, dynamic>;
  }

  // ---------------------------------------------------------------------------
  // Stats
  // ---------------------------------------------------------------------------

  /// Fetches global prediction statistics
  Future<AppStats> getStats() async {
    final response = await _dio.get(ApiConfig.statsEndpoint);
    final data = response.data as Map<String, dynamic>;
    return AppStats(
      totalPredictions: (data['total_predictions'] as int?) ?? 0,
      fraudCount: (data['fraud_count'] as int?) ?? 0,
      suspiciousCount: (data['suspicious_count'] as int?) ?? 0,
      safeCount: (data['safe_count'] as int?) ?? 0,
      averageRiskScore: (data['average_risk_score'] as num?)?.toDouble() ?? 0.0,
      fraudRate: (data['fraud_rate'] as num?)?.toDouble() ?? 0.0,
      lastUpdated: DateTime.now(),
    );
  }

  // ---------------------------------------------------------------------------
  // History
  // ---------------------------------------------------------------------------

  /// Fetches prediction history from the server
  Future<List<Map<String, dynamic>>> getHistory({
    int page = 1,
    int pageSize = ApiConfig.defaultPageSize,
    String? search,
    String? status,
    DateTime? fromDate,
    DateTime? toDate,
  }) async {
    final queryParams = <String, dynamic>{
      'page': page,
      'page_size': pageSize,
      if (search != null && search.isNotEmpty) 'search': search,
      if (status != null) 'status': status,
      if (fromDate != null) 'from_date': fromDate.toIso8601String(),
      if (toDate != null) 'to_date': toDate.toIso8601String(),
    };

    final response = await _dio.get(
      ApiConfig.historyEndpoint,
      queryParameters: queryParams,
    );
    return (response.data['results'] as List<dynamic>)
        .map((e) => e as Map<String, dynamic>)
        .toList();
  }

  // ---------------------------------------------------------------------------
  // Feedback
  // ---------------------------------------------------------------------------

  /// Submits user feedback / correction for a prediction
  Future<void> submitFeedback({
    required String transactionId,
    required bool isCorrect,
    String? userLabel,
    String? comment,
  }) async {
    await _dio.post(
      ApiConfig.feedbackEndpoint,
      data: jsonEncode({
        'transaction_id': transactionId,
        'is_correct': isCorrect,
        if (userLabel != null) 'user_label': userLabel,
        if (comment != null) 'comment': comment,
      }),
    );
  }
}

// ---------------------------------------------------------------------------
// Retry interceptor
// ---------------------------------------------------------------------------

class _RetryInterceptor extends Interceptor {
  final Dio dio;

  _RetryInterceptor(this.dio);

  @override
  Future<void> onError(
      DioException err, ErrorInterceptorHandler handler) async {
    final extra = err.requestOptions.extra;
    final retryCount = (extra['retry_count'] as int?) ?? 0;

    if (_shouldRetry(err) && retryCount < ApiConfig.maxRetryAttempts) {
      final delay = ApiConfig.retryDelayMs * (1 << retryCount); // exponential
      await Future.delayed(Duration(milliseconds: delay));

      final options = err.requestOptions
        ..extra['retry_count'] = retryCount + 1;

      try {
        final response = await dio.fetch(options);
        handler.resolve(response);
      } catch (e) {
        handler.next(err);
      }
    } else {
      handler.next(err);
    }
  }

  bool _shouldRetry(DioException err) {
    return err.type == DioExceptionType.connectionTimeout ||
        err.type == DioExceptionType.receiveTimeout ||
        err.type == DioExceptionType.connectionError ||
        (err.response?.statusCode != null &&
            err.response!.statusCode! >= 500);
  }
}
