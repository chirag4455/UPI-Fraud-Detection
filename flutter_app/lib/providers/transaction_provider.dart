import 'package:flutter/foundation.dart';
import '../models/transaction.dart';
import '../models/prediction.dart';
import '../services/api_service.dart';
import '../services/storage_service.dart';
import '../models/user.dart';

enum TransactionLoadState { idle, loading, loaded, error }

class TransactionProvider extends ChangeNotifier {
  final ApiService _api;
  final StorageService _storage;

  TransactionLoadState _state = TransactionLoadState.idle;
  List<Transaction> _transactions = [];
  Map<String, Prediction> _predictions = {};
  AppStats _stats = AppStats.empty();
  String? _errorMessage;
  bool _hasMore = true;
  int _currentPage = 1;

  // Filters
  String _searchQuery = '';
  String? _statusFilter;
  DateTime? _fromDate;
  DateTime? _toDate;

  TransactionProvider({
      required ApiService api, required StorageService storage})
      : _api = api,
        _storage = storage;

  TransactionLoadState get state => _state;
  List<Transaction> get transactions => List.unmodifiable(_transactions);
  Map<String, Prediction> get predictions => Map.unmodifiable(_predictions);
  AppStats get stats => _stats;
  String? get errorMessage => _errorMessage;
  bool get hasMore => _hasMore;
  bool get isLoading => _state == TransactionLoadState.loading;
  String get searchQuery => _searchQuery;
  String? get statusFilter => _statusFilter;
  DateTime? get fromDate => _fromDate;
  DateTime? get toDate => _toDate;

  // ---------------------------------------------------------------------------
  // Load / refresh
  // ---------------------------------------------------------------------------

  Future<void> loadTransactions({bool refresh = false}) async {
    if (_state == TransactionLoadState.loading) return;

    if (refresh) {
      _transactions = [];
      _predictions = {};
      _currentPage = 1;
      _hasMore = true;
    }

    if (!_hasMore) return;

    _state = TransactionLoadState.loading;
    _errorMessage = null;
    notifyListeners();

    try {
      final txns = await _storage.getTransactions(
        limit: 20,
        offset: (_currentPage - 1) * 20,
        search: _searchQuery.isEmpty ? null : _searchQuery,
        status: _statusFilter,
        fromDate: _fromDate,
        toDate: _toDate,
      );

      if (txns.length < 20) _hasMore = false;
      _transactions.addAll(txns);
      _currentPage++;

      // Load associated predictions
      for (final t in txns) {
        final pred = await _storage.getPrediction(t.id);
        if (pred != null) _predictions[t.id] = pred;
      }

      await _refreshStats();
      _state = TransactionLoadState.loaded;
    } catch (e) {
      _errorMessage = 'Failed to load history: ${e.toString()}';
      _state = TransactionLoadState.error;
    }

    notifyListeners();
  }

  Future<void> _refreshStats() async {
    try {
      final raw = await _storage.getLocalStats();
      _stats = AppStats(
        totalPredictions: raw['total_predictions'] as int,
        fraudCount: raw['fraud_count'] as int,
        suspiciousCount: raw['suspicious_count'] as int,
        safeCount: raw['safe_count'] as int,
        averageRiskScore: raw['average_risk_score'] as double,
        fraudRate: raw['fraud_rate'] as double,
        lastUpdated: DateTime.now(),
      );
    } catch (_) {
      // Keep previous stats on error
    }
  }

  // ---------------------------------------------------------------------------
  // Filters
  // ---------------------------------------------------------------------------

  void setSearchQuery(String query) {
    _searchQuery = query;
    loadTransactions(refresh: true);
  }

  void setStatusFilter(String? status) {
    _statusFilter = status;
    loadTransactions(refresh: true);
  }

  void setDateRange(DateTime? from, DateTime? to) {
    _fromDate = from;
    _toDate = to;
    loadTransactions(refresh: true);
  }

  void clearFilters() {
    _searchQuery = '';
    _statusFilter = null;
    _fromDate = null;
    _toDate = null;
    loadTransactions(refresh: true);
  }

  // ---------------------------------------------------------------------------
  // Sync with server
  // ---------------------------------------------------------------------------

  Future<void> syncWithServer() async {
    try {
      final serverStats = await _api.getStats();
      _stats = serverStats;
      notifyListeners();
    } catch (_) {
      // Ignore – keep local stats
    }
  }

  // ---------------------------------------------------------------------------
  // Delete
  // ---------------------------------------------------------------------------

  Future<void> deleteTransaction(String id) async {
    await _storage.deleteTransaction(id);
    _transactions.removeWhere((t) => t.id == id);
    _predictions.remove(id);
    await _refreshStats();
    notifyListeners();
  }
}
