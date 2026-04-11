import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:fl_chart/fl_chart.dart';
import '../providers/transaction_provider.dart';
import '../models/user.dart';
import '../utils/constants.dart';
import '../utils/formatters.dart';
import '../widgets/custom_app_bar.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<TransactionProvider>().loadTransactions(refresh: true);
    });
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<TransactionProvider>();
    final stats = provider.stats;
    final theme = Theme.of(context);

    return Scaffold(
      appBar: CustomAppBar(
        title: 'Dashboard',
        showBackButton: false,
        actions: [
          IconButton(
            onPressed: () => provider.syncWithServer(),
            icon: const Icon(Icons.sync),
            tooltip: 'Sync with server',
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () => provider.loadTransactions(refresh: true),
        child: ListView(
          padding: const EdgeInsets.all(AppConstants.spaceMd),
          children: [
            // Stats grid
            _StatsGrid(stats: stats),
            const SizedBox(height: AppConstants.spaceMd),
            // Pie chart
            if (stats.totalPredictions > 0) ...[
              _RiskDistributionChart(stats: stats),
              const SizedBox(height: AppConstants.spaceMd),
            ],
            // Avg risk score card
            _AverageRiskCard(stats: stats),
            const SizedBox(height: AppConstants.spaceMd),
            // Fraud rate card
            _FraudRateCard(stats: stats),
            const SizedBox(height: AppConstants.spaceMd),
            // Last sync
            if (stats.lastUpdated != null)
              Center(
                child: Text(
                  'Last updated: ${AppFormatters.dateTime(stats.lastUpdated!)}',
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.onSurface.withOpacity(0.4),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _StatsGrid extends StatelessWidget {
  final AppStats stats;

  const _StatsGrid({required this.stats});

  @override
  Widget build(BuildContext context) {
    return GridView.count(
      crossAxisCount: 2,
      crossAxisSpacing: AppConstants.spaceMd,
      mainAxisSpacing: AppConstants.spaceMd,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      childAspectRatio: 1.6,
      children: [
        _GridStatCard(
          label: 'Total Checks',
          value: AppFormatters.compactNumber(stats.totalPredictions),
          icon: Icons.analytics_outlined,
          color: Theme.of(context).colorScheme.primary,
        ),
        _GridStatCard(
          label: 'Safe',
          value: AppFormatters.compactNumber(stats.safeCount),
          icon: Icons.check_circle_outline,
          color: AppConstants.colorSafe,
        ),
        _GridStatCard(
          label: 'Suspicious',
          value: AppFormatters.compactNumber(stats.suspiciousCount),
          icon: Icons.warning_amber_outlined,
          color: AppConstants.colorSuspicious,
        ),
        _GridStatCard(
          label: 'Fraud',
          value: AppFormatters.compactNumber(stats.fraudCount),
          icon: Icons.dangerous_outlined,
          color: AppConstants.colorFraud,
        ),
      ],
    );
  }
}

class _GridStatCard extends StatelessWidget {
  final String label;
  final String value;
  final IconData icon;
  final Color color;

  const _GridStatCard({
    required this.label,
    required this.value,
    required this.icon,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppConstants.spaceMd),
        child: Row(
          children: [
            Icon(icon, color: color, size: 30),
            const SizedBox(width: AppConstants.spaceSm),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  value,
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                        fontWeight: FontWeight.bold,
                        color: color,
                      ),
                ),
                Text(
                  label,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Theme.of(context)
                            .colorScheme
                            .onSurface
                            .withOpacity(0.6),
                      ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _RiskDistributionChart extends StatelessWidget {
  final AppStats stats;

  const _RiskDistributionChart({required this.stats});

  @override
  Widget build(BuildContext context) {
    final total = stats.totalPredictions;
    if (total == 0) return const SizedBox.shrink();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppConstants.spaceMd),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Risk Distribution',
              style: Theme.of(context)
                  .textTheme
                  .titleMedium
                  ?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: AppConstants.spaceMd),
            SizedBox(
              height: 200,
              child: PieChart(
                PieChartData(
                  sections: [
                    PieChartSectionData(
                      value: stats.safeCount.toDouble(),
                      color: AppConstants.colorSafe,
                      title: 'Safe',
                      radius: 60,
                      titleStyle: const TextStyle(
                          color: Colors.white,
                          fontSize: 12,
                          fontWeight: FontWeight.bold),
                    ),
                    PieChartSectionData(
                      value: stats.suspiciousCount.toDouble(),
                      color: AppConstants.colorSuspicious,
                      title: 'Suspicious',
                      radius: 60,
                      titleStyle: const TextStyle(
                          color: Colors.white,
                          fontSize: 12,
                          fontWeight: FontWeight.bold),
                    ),
                    PieChartSectionData(
                      value: stats.fraudCount.toDouble(),
                      color: AppConstants.colorFraud,
                      title: 'Fraud',
                      radius: 60,
                      titleStyle: const TextStyle(
                          color: Colors.white,
                          fontSize: 12,
                          fontWeight: FontWeight.bold),
                    ),
                  ],
                  centerSpaceRadius: 40,
                  sectionsSpace: 2,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _AverageRiskCard extends StatelessWidget {
  final AppStats stats;

  const _AverageRiskCard({required this.stats});

  @override
  Widget build(BuildContext context) {
    final score = stats.averageRiskScore;
    final color = score < 30
        ? AppConstants.colorSafe
        : score < 60
            ? AppConstants.colorSuspicious
            : AppConstants.colorFraud;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppConstants.spaceMd),
        child: Row(
          children: [
            const Icon(Icons.speed_outlined, size: 36),
            const SizedBox(width: AppConstants.spaceMd),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Average Risk Score',
                    style: Theme.of(context).textTheme.titleSmall,
                  ),
                  const SizedBox(height: AppConstants.spaceXs),
                  LinearProgressIndicator(
                    value: score / 100,
                    color: color,
                    backgroundColor: color.withOpacity(0.2),
                    minHeight: 8,
                    borderRadius:
                        BorderRadius.circular(AppConstants.radiusFull),
                  ),
                ],
              ),
            ),
            const SizedBox(width: AppConstants.spaceMd),
            Text(
              AppFormatters.riskLabel(score),
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: color,
                  ),
            ),
          ],
        ),
      ),
    );
  }
}

class _FraudRateCard extends StatelessWidget {
  final AppStats stats;

  const _FraudRateCard({required this.stats});

  @override
  Widget build(BuildContext context) {
    final rate = stats.fraudRate;
    return Card(
      color: rate > 0.1
          ? AppConstants.colorFraud.withOpacity(0.08)
          : null,
      child: Padding(
        padding: const EdgeInsets.all(AppConstants.spaceMd),
        child: Row(
          children: [
            Icon(
              Icons.shield_outlined,
              size: 36,
              color: rate > 0.1
                  ? AppConstants.colorFraud
                  : AppConstants.colorSafe,
            ),
            const SizedBox(width: AppConstants.spaceMd),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Fraud Rate',
                      style: Theme.of(context).textTheme.titleSmall),
                  Text(
                    rate > 0.1
                        ? 'High fraud activity detected in your transactions'
                        : 'Fraud rate is within normal range',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Theme.of(context)
                              .colorScheme
                              .onSurface
                              .withOpacity(0.6),
                        ),
                  ),
                ],
              ),
            ),
            Text(
              AppFormatters.percent(rate),
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: rate > 0.1
                        ? AppConstants.colorFraud
                        : AppConstants.colorSafe,
                  ),
            ),
          ],
        ),
      ),
    );
  }
}
