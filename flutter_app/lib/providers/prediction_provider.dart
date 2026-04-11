import 'package:flutter/foundation.dart';
import '../models/prediction.dart';
import '../models/transaction.dart';
import '../services/api_service.dart';
import '../services/storage_service.dart';

enum PredictionState { idle, loading, success, error }

class PredictionProvider extends ChangeNotifier {
  final ApiService _api;
  final StorageService _storage;

  PredictionState _state = PredictionState.idle;
  Prediction? _currentPrediction;
  String? _errorMessage;

  PredictionProvider({required ApiService api, required StorageService storage})
      : _api = api,
        _storage = storage;

  PredictionState get state => _state;
  Prediction? get currentPrediction => _currentPrediction;
  String? get errorMessage => _errorMessage;
  bool get isLoading => _state == PredictionState.loading;

  /// Fetches a live prediction for [transaction] and caches the result locally.
  Future<Prediction?> predict(Transaction transaction) async {
    _state = PredictionState.loading;
    _errorMessage = null;
    notifyListeners();

    try {
      // Check if we already have a cached prediction
      final cached = await _storage.getPrediction(transaction.id);
      if (cached != null) {
        _currentPrediction = cached;
        _state = PredictionState.success;
        notifyListeners();
        return cached;
      }

      // Call API
      final prediction = await _api.predict(transaction);

      // Persist locally
      await _storage.saveTransaction(transaction);
      await _storage.savePrediction(prediction);

      _currentPrediction = prediction;
      _state = PredictionState.success;
      notifyListeners();
      return prediction;
    } catch (e) {
      _errorMessage = _formatError(e);
      _state = PredictionState.error;
      notifyListeners();
      return null;
    }
  }

  void clearPrediction() {
    _currentPrediction = null;
    _state = PredictionState.idle;
    _errorMessage = null;
    notifyListeners();
  }

  String _formatError(Object e) {
    return 'Prediction failed: ${e.toString()}';
  }
}
