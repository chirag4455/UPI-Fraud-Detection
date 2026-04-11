import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/transaction_provider.dart';
import '../providers/settings_provider.dart';
import '../utils/constants.dart';
import '../utils/formatters.dart';
import '../widgets/transaction_card.dart';
import '../widgets/custom_app_bar.dart';
import 'qr_scanner_screen.dart';
import 'transaction_input_screen.dart';
import 'dashboard_screen.dart';
import 'history_screen.dart';
import 'settings_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _selectedIndex = 0;

  static final List<Widget> _pages = [
    const _ScanPage(),
    const DashboardScreen(),
    const HistoryScreen(),
    const SettingsScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _pages[_selectedIndex],
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: (i) => setState(() => _selectedIndex = i),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.qr_code_scanner_outlined),
            selectedIcon: Icon(Icons.qr_code_scanner),
            label: 'Scan',
          ),
          NavigationDestination(
            icon: Icon(Icons.dashboard_outlined),
            selectedIcon: Icon(Icons.dashboard),
            label: 'Dashboard',
          ),
          NavigationDestination(
            icon: Icon(Icons.history_outlined),
            selectedIcon: Icon(Icons.history),
            label: 'History',
          ),
          NavigationDestination(
            icon: Icon(Icons.settings_outlined),
            selectedIcon: Icon(Icons.settings),
            label: 'Settings',
          ),
        ],
      ),
    );
  }
}

/// The main Scan/Check page shown as the first tab
class _ScanPage extends StatelessWidget {
  const _ScanPage();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final txnProvider = context.watch<TransactionProvider>();
    final recentTxns = txnProvider.transactions.take(3).toList();

    return Scaffold(
      appBar: const CustomAppBar(
        title: 'UPI Fraud Detector',
        showBackButton: false,
      ),
      body: RefreshIndicator(
        onRefresh: () => txnProvider.loadTransactions(refresh: true),
        child: ListView(
          padding: const EdgeInsets.all(AppConstants.spaceMd),
          children: [
            // Hero action cards
            Row(
              children: [
                Expanded(
                  child: _ActionCard(
                    icon: Icons.qr_code_scanner,
                    label: 'Scan QR',
                    color: theme.colorScheme.primary,
                    onTap: () => Navigator.push(
                      context,
                      MaterialPageRoute(
                          builder: (_) => const QrScannerScreen()),
                    ),
                  ),
                ),
                const SizedBox(width: AppConstants.spaceMd),
                Expanded(
                  child: _ActionCard(
                    icon: Icons.edit_outlined,
                    label: 'Manual Entry',
                    color: theme.colorScheme.secondary,
                    onTap: () => Navigator.push(
                      context,
                      MaterialPageRoute(
                          builder: (_) => const TransactionInputScreen()),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppConstants.spaceLg),
            // Stats summary
            _StatsSummary(stats: txnProvider.stats),
            const SizedBox(height: AppConstants.spaceLg),
            // Recent transactions
            if (recentTxns.isNotEmpty) ...[
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'Recent Checks',
                    style: theme.textTheme.titleMedium
                        ?.copyWith(fontWeight: FontWeight.bold),
                  ),
                  TextButton(
                    onPressed: () {},
                    child: const Text('See All'),
                  ),
                ],
              ),
              ...recentTxns.map((t) => TransactionCard(
                    transaction: t,
                    prediction: txnProvider.predictions[t.id],
                  )),
            ] else
              Center(
                child: Padding(
                  padding: const EdgeInsets.all(AppConstants.spaceXl),
                  child: Column(
                    children: [
                      Icon(Icons.qr_code_2,
                          size: 80,
                          color: theme.colorScheme.onSurface.withOpacity(0.2)),
                      const SizedBox(height: AppConstants.spaceMd),
                      Text(
                        'No transactions yet',
                        style: theme.textTheme.bodyLarge?.copyWith(
                            color: theme.colorScheme.onSurface.withOpacity(0.5)),
                      ),
                      const SizedBox(height: AppConstants.spaceSm),
                      Text(
                        'Scan a UPI QR code or enter payment details manually',
                        textAlign: TextAlign.center,
                        style: theme.textTheme.bodySmall?.copyWith(
                            color: theme.colorScheme.onSurface.withOpacity(0.4)),
                      ),
                    ],
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _ActionCard extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;

  const _ActionCard({
    required this.icon,
    required this.label,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppConstants.radiusLg),
        child: Padding(
          padding: const EdgeInsets.all(AppConstants.spaceLg),
          child: Column(
            children: [
              Icon(icon, size: 40, color: color),
              const SizedBox(height: AppConstants.spaceSm),
              Text(
                label,
                style: Theme.of(context)
                    .textTheme
                    .bodyMedium
                    ?.copyWith(fontWeight: FontWeight.w600),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _StatsSummary extends StatelessWidget {
  final dynamic stats;

  const _StatsSummary({required this.stats});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppConstants.spaceMd),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceAround,
          children: [
            _StatItem(
              label: 'Total',
              value: '${stats.totalPredictions}',
              color: theme.colorScheme.primary,
            ),
            _StatItem(
              label: 'Safe',
              value: '${stats.safeCount}',
              color: AppConstants.colorSafe,
            ),
            _StatItem(
              label: 'Suspicious',
              value: '${stats.suspiciousCount}',
              color: AppConstants.colorSuspicious,
            ),
            _StatItem(
              label: 'Fraud',
              value: '${stats.fraudCount}',
              color: AppConstants.colorFraud,
            ),
          ],
        ),
      ),
    );
  }
}

class _StatItem extends StatelessWidget {
  final String label;
  final String value;
  final Color color;

  const _StatItem(
      {required this.label, required this.value, required this.color});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(
          value,
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.bold,
                color: color,
              ),
        ),
        const SizedBox(height: 2),
        Text(
          label,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
              ),
        ),
      ],
    );
  }
}
