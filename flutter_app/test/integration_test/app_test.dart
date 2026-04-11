// Integration tests for the UPI Fraud Detection Flutter app.
//
// These tests exercise end-to-end user flows using the flutter_test framework.
// They require a connected device or emulator with the app installed.
// Run with: flutter test integration_test/app_test.dart

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:upi_fraud_detection/main.dart' as app;

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  group('App launch', () {
    testWidgets('app starts without crashing', (tester) async {
      app.main();
      await tester.pumpAndSettle(const Duration(seconds: 3));
      // App should be visible
      expect(find.byType(MaterialApp), findsOneWidget);
    });

    testWidgets('home screen shows bottom nav bar', (tester) async {
      app.main();
      await tester.pumpAndSettle(const Duration(seconds: 3));
      expect(find.byType(NavigationBar), findsOneWidget);
    });

    testWidgets('all nav destinations are present', (tester) async {
      app.main();
      await tester.pumpAndSettle(const Duration(seconds: 3));
      expect(find.text('Scan'), findsOneWidget);
      expect(find.text('Dashboard'), findsOneWidget);
      expect(find.text('History'), findsOneWidget);
      expect(find.text('Settings'), findsOneWidget);
    });
  });

  group('Navigation', () {
    testWidgets('tapping Dashboard nav shows dashboard', (tester) async {
      app.main();
      await tester.pumpAndSettle(const Duration(seconds: 3));
      await tester.tap(find.text('Dashboard'));
      await tester.pumpAndSettle();
      expect(find.text('Dashboard'), findsAtLeastNWidgets(1));
    });

    testWidgets('tapping History nav shows history screen', (tester) async {
      app.main();
      await tester.pumpAndSettle(const Duration(seconds: 3));
      await tester.tap(find.text('History'));
      await tester.pumpAndSettle();
      expect(find.text('Transaction History'), findsOneWidget);
    });

    testWidgets('tapping Settings nav shows settings screen', (tester) async {
      app.main();
      await tester.pumpAndSettle(const Duration(seconds: 3));
      await tester.tap(find.text('Settings'));
      await tester.pumpAndSettle();
      expect(find.text('Settings'), findsAtLeastNWidgets(1));
      expect(find.text('API Configuration'), findsOneWidget);
    });
  });

  group('Transaction input', () {
    testWidgets('manual entry button navigates to input screen', (tester) async {
      app.main();
      await tester.pumpAndSettle(const Duration(seconds: 3));
      await tester.tap(find.text('Manual Entry'));
      await tester.pumpAndSettle();
      expect(find.text('Check Transaction'), findsOneWidget);
    });

    testWidgets('input form validates empty fields', (tester) async {
      app.main();
      await tester.pumpAndSettle(const Duration(seconds: 3));
      await tester.tap(find.text('Manual Entry'));
      await tester.pumpAndSettle();
      // Tap check button without filling form
      await tester.tap(find.text('Check for Fraud'));
      await tester.pumpAndSettle();
      expect(find.text('UPI ID is required'), findsOneWidget);
    });

    testWidgets('input form validates invalid amount', (tester) async {
      app.main();
      await tester.pumpAndSettle(const Duration(seconds: 3));
      await tester.tap(find.text('Manual Entry'));
      await tester.pumpAndSettle();

      await tester.enterText(
          find.widgetWithText(TextFormField, 'e.g. name@bank'), 'test@upi');
      await tester.enterText(
          find.widgetWithText(TextFormField, 'e.g. 500.00'), '-100');
      await tester.tap(find.text('Check for Fraud'));
      await tester.pumpAndSettle();
      expect(find.text('Amount must be greater than zero'), findsOneWidget);
    });
  });

  group('Settings screen', () {
    testWidgets('API URL field is populated with default', (tester) async {
      app.main();
      await tester.pumpAndSettle(const Duration(seconds: 3));
      await tester.tap(find.text('Settings'));
      await tester.pumpAndSettle();
      expect(
          find.widgetWithText(TextFormField, 'http://localhost:5000'),
          findsWidgets);
    });

    testWidgets('theme dropdown is present', (tester) async {
      app.main();
      await tester.pumpAndSettle(const Duration(seconds: 3));
      await tester.tap(find.text('Settings'));
      await tester.pumpAndSettle();
      expect(find.byType(DropdownButton<ThemeMode>), findsOneWidget);
    });

    testWidgets('notifications toggle is present', (tester) async {
      app.main();
      await tester.pumpAndSettle(const Duration(seconds: 3));
      await tester.tap(find.text('Settings'));
      await tester.pumpAndSettle();
      expect(find.byType(SwitchListTile), findsAtLeastNWidgets(2));
    });
  });
}
