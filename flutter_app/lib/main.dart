import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'providers/prediction_provider.dart';
import 'providers/settings_provider.dart';
import 'providers/transaction_provider.dart';
import 'screens/home_screen.dart';
import 'services/api_service.dart';
import 'services/storage_service.dart';
import 'utils/theme.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialise local storage
  final storage = StorageService();
  await storage.init();

  // Load saved settings (API URL, theme, etc.)
  final settings = SettingsProvider();
  await settings.load();

  // Build API service with the persisted base URL
  final api = ApiService(baseUrl: settings.baseUrl);

  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider.value(value: settings),
        Provider<StorageService>.value(value: storage),
        Provider<ApiService>.value(value: api),
        ChangeNotifierProvider(
          create: (ctx) => PredictionProvider(
            api: ctx.read<ApiService>(),
            storage: ctx.read<StorageService>(),
          ),
        ),
        ChangeNotifierProvider(
          create: (ctx) => TransactionProvider(
            api: ctx.read<ApiService>(),
            storage: ctx.read<StorageService>(),
          )..loadTransactions(refresh: true),
        ),
      ],
      child: const UPIFraudApp(),
    ),
  );
}

class UPIFraudApp extends StatelessWidget {
  const UPIFraudApp({super.key});

  @override
  Widget build(BuildContext context) {
    final settings = context.watch<SettingsProvider>();

    return MaterialApp(
      title: 'UPI Fraud Detector',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      darkTheme: AppTheme.dark,
      themeMode: settings.themeMode,
      home: const HomeScreen(),
    );
  }
}
