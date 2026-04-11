import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:uuid/uuid.dart';
import '../models/transaction.dart';
import '../models/prediction.dart';
import '../providers/prediction_provider.dart';
import '../utils/constants.dart';
import '../utils/validators.dart';
import '../utils/formatters.dart';
import '../widgets/custom_app_bar.dart';
import '../widgets/risk_gauge.dart';
import '../widgets/layer_breakdown_card.dart';

class TransactionInputScreen extends StatefulWidget {
  final String? prefillVpa;
  final String? prefillName;
  final double? prefillAmount;
  final String? prefillNote;

  const TransactionInputScreen({
    super.key,
    this.prefillVpa,
    this.prefillName,
    this.prefillAmount,
    this.prefillNote,
  });

  @override
  State<TransactionInputScreen> createState() => _TransactionInputScreenState();
}

class _TransactionInputScreenState extends State<TransactionInputScreen> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _vpaController;
  late final TextEditingController _nameController;
  late final TextEditingController _amountController;
  late final TextEditingController _noteController;

  bool _analysed = false;

  @override
  void initState() {
    super.initState();
    _vpaController =
        TextEditingController(text: widget.prefillVpa ?? '');
    _nameController =
        TextEditingController(text: widget.prefillName ?? '');
    _amountController = TextEditingController(
        text: widget.prefillAmount?.toStringAsFixed(2) ?? '');
    _noteController =
        TextEditingController(text: widget.prefillNote ?? '');
  }

  @override
  void dispose() {
    _vpaController.dispose();
    _nameController.dispose();
    _amountController.dispose();
    _noteController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;

    final transaction = Transaction(
      id: const Uuid().v4(),
      payeeVpa: _vpaController.text.trim(),
      payeeName: _nameController.text.trim(),
      amount: double.parse(_amountController.text.trim()),
      timestamp: DateTime.now(),
    );

    final provider = context.read<PredictionProvider>();
    await provider.predict(transaction);

    if (mounted) {
      setState(() => _analysed = true);
    }
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<PredictionProvider>();
    return Scaffold(
      appBar: const CustomAppBar(title: 'Check Transaction'),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppConstants.spaceMd),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Input form
            Form(
              key: _formKey,
              child: Column(
                children: [
                  TextFormField(
                    controller: _vpaController,
                    decoration: const InputDecoration(
                      labelText: 'Payee UPI ID',
                      hintText: 'e.g. merchant@okaxis',
                      prefixIcon: Icon(Icons.account_balance_wallet_outlined),
                    ),
                    keyboardType: TextInputType.emailAddress,
                    validator: Validators.vpa,
                    textInputAction: TextInputAction.next,
                  ),
                  const SizedBox(height: AppConstants.spaceMd),
                  TextFormField(
                    controller: _nameController,
                    decoration: const InputDecoration(
                      labelText: 'Payee Name (optional)',
                      hintText: 'e.g. Chirag Stores',
                      prefixIcon: Icon(Icons.person_outline),
                    ),
                    validator: Validators.payeeName,
                    textInputAction: TextInputAction.next,
                  ),
                  const SizedBox(height: AppConstants.spaceMd),
                  TextFormField(
                    controller: _amountController,
                    decoration: const InputDecoration(
                      labelText: 'Amount (₹)',
                      hintText: 'e.g. 500.00',
                      prefixIcon: Icon(Icons.currency_rupee_outlined),
                    ),
                    keyboardType: const TextInputType.numberWithOptions(
                        decimal: true),
                    validator: Validators.amount,
                    textInputAction: TextInputAction.next,
                  ),
                  const SizedBox(height: AppConstants.spaceMd),
                  TextFormField(
                    controller: _noteController,
                    decoration: const InputDecoration(
                      labelText: 'Note (optional)',
                      hintText: 'e.g. Grocery payment',
                      prefixIcon: Icon(Icons.note_alt_outlined),
                    ),
                    textInputAction: TextInputAction.done,
                    onFieldSubmitted: (_) => _submit(),
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppConstants.spaceLg),
            ElevatedButton.icon(
              onPressed: provider.isLoading ? null : _submit,
              icon: provider.isLoading
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.shield_outlined),
              label:
                  Text(provider.isLoading ? 'Analysing…' : 'Check for Fraud'),
            ),
            // Error message
            if (provider.state == PredictionState.error)
              Padding(
                padding: const EdgeInsets.only(top: AppConstants.spaceMd),
                child: Card(
                  color: Theme.of(context).colorScheme.errorContainer,
                  child: Padding(
                    padding: const EdgeInsets.all(AppConstants.spaceMd),
                    child: Text(
                      provider.errorMessage ?? 'An error occurred',
                      style: TextStyle(
                          color: Theme.of(context).colorScheme.onErrorContainer),
                    ),
                  ),
                ),
              ),
            // Result
            if (_analysed && provider.currentPrediction != null) ...[
              const SizedBox(height: AppConstants.spaceLg),
              _PredictionResult(prediction: provider.currentPrediction!),
            ],
          ],
        ),
      ),
    );
  }
}

class _PredictionResult extends StatelessWidget {
  final Prediction prediction;

  const _PredictionResult({required this.prediction});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final color = _riskColor(prediction.riskLevel);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Risk gauge
        Card(
          child: Padding(
            padding: const EdgeInsets.all(AppConstants.spaceLg),
            child: Column(
              children: [
                Text(
                  'Fraud Risk Analysis',
                  style: theme.textTheme.titleMedium
                      ?.copyWith(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: AppConstants.spaceLg),
                Center(
                  child: RiskGauge(
                    score: prediction.riskScore,
                    riskLevel: prediction.riskLevel,
                    size: 220,
                  ),
                ),
                const SizedBox(height: AppConstants.spaceMd),
                Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: AppConstants.spaceLg,
                      vertical: AppConstants.spaceSm),
                  decoration: BoxDecoration(
                    color: color.withOpacity(0.12),
                    borderRadius:
                        BorderRadius.circular(AppConstants.radiusFull),
                  ),
                  child: Text(
                    prediction.verdictLabel,
                    style: theme.textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: color,
                      letterSpacing: 1.5,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: AppConstants.spaceMd),
        // Layer breakdown
        LayerBreakdownCard(prediction: prediction),
      ],
    );
  }

  Color _riskColor(RiskLevel level) {
    switch (level) {
      case RiskLevel.safe:
        return AppConstants.colorSafe;
      case RiskLevel.suspicious:
        return AppConstants.colorSuspicious;
      case RiskLevel.fraud:
        return AppConstants.colorFraud;
    }
  }
}
