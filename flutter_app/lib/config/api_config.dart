// API configuration constants
class ApiConfig {
  // Default backend URL – can be overridden via Settings
  static const String defaultBaseUrl = 'http://localhost:5000';

  // API version prefix
  static const String apiVersion = '/api';

  // Endpoint paths
  static const String predictEndpoint = '/api/predict';
  static const String parseQrEndpoint = '/api/qr/parse';
  static const String statsEndpoint = '/api/stats';
  static const String healthEndpoint = '/api/health';
  static const String feedbackEndpoint = '/api/feedback';
  static const String historyEndpoint = '/api/history';

  // HTTP timeouts (milliseconds)
  static const int connectTimeout = 10000;
  static const int receiveTimeout = 30000;
  static const int sendTimeout = 10000;

  // Retry configuration
  static const int maxRetryAttempts = 3;
  static const int retryDelayMs = 1000;

  // Pagination
  static const int defaultPageSize = 20;
  static const int maxPageSize = 100;

  // Risk score thresholds
  static const double safeLowerBound = 0.0;
  static const double safeUpperBound = 30.0;
  static const double suspiciousLowerBound = 30.0;
  static const double suspiciousUpperBound = 60.0;
  static const double fraudLowerBound = 60.0;
  static const double fraudUpperBound = 100.0;

  // SharedPreferences keys
  static const String prefBaseUrl = 'api_base_url';
  static const String prefApiKey = 'api_key';
  static const String prefThemeMode = 'theme_mode';
  static const String prefNotificationsEnabled = 'notifications_enabled';
  static const String prefAutoSyncEnabled = 'auto_sync_enabled';
  static const String prefLastSyncTime = 'last_sync_time';

  // SQLite
  static const String dbName = 'upi_fraud_detection.db';
  static const int dbVersion = 1;
}
