import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:csv/csv.dart';
import 'dart:io';
import '../providers/transaction_provider.dart';
import '../models/transaction.dart';
import '../models/prediction.dart';
import '../utils/constants.dart';
import '../utils/formatters.dart';
import '../widgets/custom_app_bar.dart';
import '../widgets/transaction_card.dart';
import '../widgets/risk_gauge.dart';
import '../widgets/layer_breakdown_card.dart';

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  final _searchController = TextEditingController();
  final _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<TransactionProvider>().loadTransactions(refresh: true);
    });
    _scrollController.addListener(_onScroll);
  }

  @override
  void dispose() {
    _searchController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (_scrollController.position.pixels >=
        _scrollController.position.maxScrollExtent - 200) {
      context.read<TransactionProvider>().loadTransactions();
    }
  }

  Future<void> _exportCsv() async {
    final provider = context.read<TransactionProvider>();
    final rows = [
      ['ID', 'Payee VPA', 'Payee Name', 'Amount', 'Risk Score', 'Verdict', 'Date'],
      ...provider.transactions.map((t) {
        final pred = provider.predictions[t.id];
        return [
          t.id,
          t.payeeVpa,
          t.payeeName,
          t.amount.toStringAsFixed(2),
          pred?.riskScore.toStringAsFixed(1) ?? '-',
          pred?.verdictLabel ?? '-',
          AppFormatters.dateTime(t.timestamp),
        ];
      }),
    ];
    final csv = const ListToCsvConverter().convert(rows);
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('CSV prepared (${rows.length - 1} transactions)')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<TransactionProvider>();
    final txns = provider.transactions;

    return Scaffold(
      appBar: CustomAppBar(
        title: 'Transaction History',
        showBackButton: false,
        actions: [
          IconButton(
            onPressed: _exportCsv,
            icon: const Icon(Icons.download_outlined),
            tooltip: 'Export CSV',
          ),
          IconButton(
            onPressed: () => provider.loadTransactions(refresh: true),
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh',
          ),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(56),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(
              AppConstants.spaceMd,
              0,
              AppConstants.spaceMd,
              AppConstants.spaceSm,
            ),
            child: TextField(
              controller: _searchController,
              decoration: InputDecoration(
                hintText: 'Search by payee name or UPI ID',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: _searchController.text.isNotEmpty
                    ? IconButton(
                        onPressed: () {
                          _searchController.clear();
                          provider.setSearchQuery('');
                        },
                        icon: const Icon(Icons.clear),
                      )
                    : null,
              ),
              onChanged: (q) =>
                  provider.setSearchQuery(q),
            ),
          ),
        ),
      ),
      body: Column(
        children: [
          // Filter chips
          _FilterChips(provider: provider),
          // Transaction list
          Expanded(
            child: txns.isEmpty && !provider.isLoading
                ? _EmptyState(hasFilters: provider.searchQuery.isNotEmpty ||
                    provider.statusFilter != null)
                : ListView.builder(
                    controller: _scrollController,
                    itemCount: txns.length + (provider.hasMore ? 1 : 0),
                    itemBuilder: (context, i) {
                      if (i >= txns.length) {
                        return const Padding(
                          padding: EdgeInsets.all(AppConstants.spaceLg),
                          child: Center(child: CircularProgressIndicator()),
                        );
                      }
                      final t = txns[i];
                      return TransactionCard(
                        transaction: t,
                        prediction: provider.predictions[t.id],
                        onTap: () => _showDetails(context, t,
                            provider.predictions[t.id]),
                        onDelete: () => _confirmDelete(context, provider, t.id),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }

  void _showDetails(
      BuildContext context, Transaction t, Prediction? prediction) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(
            top: Radius.circular(AppConstants.radiusXl)),
      ),
      builder: (_) => _DetailSheet(transaction: t, prediction: prediction),
    );
  }

  Future<void> _confirmDelete(
      BuildContext context, TransactionProvider provider, String id) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Delete Transaction?'),
        content: const Text(
            'This will permanently remove the transaction from local storage.'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Cancel')),
          TextButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Delete',
                  style: TextStyle(color: Colors.red))),
        ],
      ),
    );
    if (confirmed == true) {
      await provider.deleteTransaction(id);
    }
  }
}

class _FilterChips extends StatelessWidget {
  final TransactionProvider provider;

  const _FilterChips({required this.provider});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(
        horizontal: AppConstants.spaceMd,
        vertical: AppConstants.spaceSm,
      ),
      child: Row(
        children: [
          FilterChip(
            label: const Text('All'),
            selected: provider.statusFilter == null,
            onSelected: (_) => provider.setStatusFilter(null),
          ),
          const SizedBox(width: AppConstants.spaceSm),
          FilterChip(
            label: const Text('Safe'),
            selected: provider.statusFilter == 'safe',
            onSelected: (_) => provider.setStatusFilter('safe'),
          ),
          const SizedBox(width: AppConstants.spaceSm),
          FilterChip(
            label: const Text('Suspicious'),
            selected: provider.statusFilter == 'suspicious',
            onSelected: (_) => provider.setStatusFilter('suspicious'),
          ),
          const SizedBox(width: AppConstants.spaceSm),
          FilterChip(
            label: const Text('Fraud'),
            selected: provider.statusFilter == 'fraud',
            onSelected: (_) => provider.setStatusFilter('fraud'),
          ),
          if (provider.statusFilter != null) ...[
            const SizedBox(width: AppConstants.spaceSm),
            ActionChip(
              label: const Text('Clear'),
              onPressed: provider.clearFilters,
              avatar: const Icon(Icons.close, size: 14),
            ),
          ],
        ],
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  final bool hasFilters;

  const _EmptyState({required this.hasFilters});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppConstants.spaceXl),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              hasFilters ? Icons.search_off : Icons.history,
              size: 80,
              color: theme.colorScheme.onSurface.withOpacity(0.2),
            ),
            const SizedBox(height: AppConstants.spaceMd),
            Text(
              hasFilters ? 'No matching transactions' : 'No transaction history',
              style: theme.textTheme.bodyLarge?.copyWith(
                  color: theme.colorScheme.onSurface.withOpacity(0.5)),
            ),
          ],
        ),
      ),
    );
  }
}

class _DetailSheet extends StatelessWidget {
  final Transaction transaction;
  final Prediction? prediction;

  const _DetailSheet({required this.transaction, this.prediction});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.7,
      maxChildSize: 0.95,
      builder: (_, controller) => ListView(
        controller: controller,
        padding: const EdgeInsets.all(AppConstants.spaceMd),
        children: [
          // Handle
          Center(
            child: Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: theme.colorScheme.onSurface.withOpacity(0.3),
                borderRadius: BorderRadius.circular(AppConstants.radiusFull),
              ),
            ),
          ),
          const SizedBox(height: AppConstants.spaceMd),
          Text('Transaction Details',
              style: theme.textTheme.titleLarge
                  ?.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: AppConstants.spaceMd),
          // Transaction info
          _InfoRow('UPI ID', transaction.maskedVpa),
          _InfoRow('Payee', transaction.payeeName.isEmpty
              ? '-'
              : transaction.payeeName),
          _InfoRow('Amount', AppFormatters.currency(transaction.amount)),
          _InfoRow('Date', AppFormatters.dateTime(transaction.timestamp)),
          if (transaction.note != null && transaction.note!.isNotEmpty)
            _InfoRow('Note', transaction.note!),
          const Divider(height: AppConstants.spaceLg),
          if (prediction != null) ...[
            Center(
              child: RiskGauge(
                score: prediction!.riskScore,
                riskLevel: prediction!.riskLevel,
                size: 200,
              ),
            ),
            const SizedBox(height: AppConstants.spaceMd),
            LayerBreakdownCard(prediction: prediction!),
          ] else
            const Center(child: Text('No prediction available')),
        ],
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;

  const _InfoRow(this.label, this.value);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppConstants.spaceXs),
      child: Row(
        children: [
          SizedBox(
            width: 90,
            child: Text(
              label,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Theme.of(context)
                        .colorScheme
                        .onSurface
                        .withOpacity(0.5),
                  ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: Theme.of(context)
                  .textTheme
                  .bodyMedium
                  ?.copyWith(fontWeight: FontWeight.w500),
            ),
          ),
        ],
      ),
    );
  }
}
