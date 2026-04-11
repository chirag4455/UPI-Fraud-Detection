import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../config/api_config.dart';

class SettingsProvider extends ChangeNotifier {
  String _baseUrl = ApiConfig.defaultBaseUrl;
  ThemeMode _themeMode = ThemeMode.system;
  bool _notificationsEnabled = true;
  bool _autoSyncEnabled = true;
  DateTime? _lastSyncTime;

  String get baseUrl => _baseUrl;
  ThemeMode get themeMode => _themeMode;
  bool get notificationsEnabled => _notificationsEnabled;
  bool get autoSyncEnabled => _autoSyncEnabled;
  DateTime? get lastSyncTime => _lastSyncTime;

  Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();

    _baseUrl = prefs.getString(ApiConfig.prefBaseUrl) ?? ApiConfig.defaultBaseUrl;

    final themeName = prefs.getString(ApiConfig.prefThemeMode);
    _themeMode = _parseThemeMode(themeName);

    _notificationsEnabled =
        prefs.getBool(ApiConfig.prefNotificationsEnabled) ?? true;
    _autoSyncEnabled = prefs.getBool(ApiConfig.prefAutoSyncEnabled) ?? true;

    final syncTs = prefs.getString(ApiConfig.prefLastSyncTime);
    _lastSyncTime = syncTs != null ? DateTime.tryParse(syncTs) : null;

    notifyListeners();
  }

  Future<void> setBaseUrl(String url) async {
    _baseUrl = url;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(ApiConfig.prefBaseUrl, url);
    notifyListeners();
  }

  Future<void> setThemeMode(ThemeMode mode) async {
    _themeMode = mode;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(ApiConfig.prefThemeMode, mode.name);
    notifyListeners();
  }

  Future<void> setNotificationsEnabled(bool enabled) async {
    _notificationsEnabled = enabled;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(ApiConfig.prefNotificationsEnabled, enabled);
    notifyListeners();
  }

  Future<void> setAutoSyncEnabled(bool enabled) async {
    _autoSyncEnabled = enabled;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(ApiConfig.prefAutoSyncEnabled, enabled);
    notifyListeners();
  }

  Future<void> updateLastSyncTime() async {
    _lastSyncTime = DateTime.now();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
        ApiConfig.prefLastSyncTime, _lastSyncTime!.toIso8601String());
    notifyListeners();
  }

  ThemeMode _parseThemeMode(String? name) {
    switch (name) {
      case 'light':
        return ThemeMode.light;
      case 'dark':
        return ThemeMode.dark;
      default:
        return ThemeMode.system;
    }
  }
}
