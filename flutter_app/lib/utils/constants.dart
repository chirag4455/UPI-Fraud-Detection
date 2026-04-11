import 'package:flutter/material.dart';

/// App-wide constants
class AppConstants {
  // App metadata
  static const String appName = 'UPI Fraud Detector';
  static const String appVersion = '1.0.0';
  static const String appBuildNumber = '1';

  // Animation durations
  static const Duration animShort = Duration(milliseconds: 200);
  static const Duration animMedium = Duration(milliseconds: 400);
  static const Duration animLong = Duration(milliseconds: 800);
  static const Duration animGauge = Duration(milliseconds: 1200);

  // Spacing
  static const double spaceXs = 4.0;
  static const double spaceSm = 8.0;
  static const double spaceMd = 16.0;
  static const double spaceLg = 24.0;
  static const double spaceXl = 32.0;

  // Border radius
  static const double radiusSm = 8.0;
  static const double radiusMd = 12.0;
  static const double radiusLg = 16.0;
  static const double radiusXl = 24.0;
  static const double radiusFull = 999.0;

  // Risk score colours
  static const Color colorSafe = Color(0xFF2E7D32);        // Green 800
  static const Color colorSafeLight = Color(0xFF81C784);   // Green 300
  static const Color colorSuspicious = Color(0xFFF57C00);  // Orange 700
  static const Color colorSuspiciousLight = Color(0xFFFFB74D); // Orange 300
  static const Color colorFraud = Color(0xFFC62828);       // Red 800
  static const Color colorFraudLight = Color(0xFFE57373);  // Red 300

  // Layer names (must match backend keys)
  static const String layerUbts = 'UBTS';
  static const String layerWts = 'WTS';
  static const String layerWebsiteTrust = 'Website Trust';
  static const String layerLstm = 'LSTM';
  static const String layerEnsemble = 'Ensemble';

  // Navigation route names
  static const String routeHome = '/';
  static const String routeQrScanner = '/qr-scanner';
  static const String routeTransactionInput = '/transaction-input';
  static const String routeDashboard = '/dashboard';
  static const String routeHistory = '/history';
  static const String routeSettings = '/settings';
  static const String routePredictionResult = '/prediction-result';
}
