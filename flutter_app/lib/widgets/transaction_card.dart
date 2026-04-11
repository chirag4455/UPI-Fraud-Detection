import 'package:flutter/material.dart';
import '../models/transaction.dart';
import '../models/prediction.dart';
import '../utils/constants.dart';
import '../utils/formatters.dart';

/// A list tile-style card showing a single transaction with its prediction.
class TransactionCard extends StatelessWidget {
  final Transaction transaction;
  final Prediction? prediction;
  final VoidCallback? onTap;
  final VoidCallback? onDelete;

  const TransactionCard({
    super.key,
    required this.transaction,
    this.prediction,
    this.onTap,
    this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final pred = prediction;
    final hasRisk = pred != null;
    final riskColor = hasRisk ? _riskColor(pred.riskLevel) : null;

    return Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppConstants.radiusLg),
        child: Padding(
          padding: const EdgeInsets.all(AppConstants.spaceMd),
          child: Row(
            children: [
              // Risk indicator dot / icon
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: (riskColor ?? theme.colorScheme.primaryContainer)
                      .withOpacity(0.15),
                  borderRadius: BorderRadius.circular(AppConstants.radiusMd),
                ),
                child: Icon(
                  _riskIcon(pred?.riskLevel),
                  color: riskColor ?? theme.colorScheme.primary,
                  size: 22,
                ),
              ),
              const SizedBox(width: AppConstants.spaceMd),
              // Transaction info
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      transaction.payeeName.isEmpty
                          ? transaction.maskedVpa
                          : transaction.payeeName,
                      style: theme.textTheme.bodyLarge
                          ?.copyWith(fontWeight: FontWeight.w600),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 2),
                    Text(
                      transaction.maskedVpa,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurface.withOpacity(0.6),
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      AppFormatters.dateTime(transaction.timestamp),
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurface.withOpacity(0.4),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: AppConstants.spaceSm),
              // Amount + risk score
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    AppFormatters.currencyShort(transaction.amount),
                    style: theme.textTheme.bodyLarge?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  if (hasRisk) ...[
                    const SizedBox(height: 4),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 2),
                      decoration: BoxDecoration(
                        color: riskColor!.withOpacity(0.15),
                        borderRadius:
                            BorderRadius.circular(AppConstants.radiusFull),
                      ),
                      child: Text(
                        pred.verdictLabel,
                        style: theme.textTheme.labelSmall?.copyWith(
                          color: riskColor,
                          fontWeight: FontWeight.bold,
                          letterSpacing: 0.5,
                        ),
                      ),
                    ),
                  ],
                ],
              ),
              if (onDelete != null) ...[
                const SizedBox(width: AppConstants.spaceXs),
                IconButton(
                  onPressed: onDelete,
                  icon: const Icon(Icons.delete_outline),
                  iconSize: 18,
                  color: theme.colorScheme.error.withOpacity(0.7),
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(),
                ),
              ],
            ],
          ),
        ),
      ),
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

  IconData _riskIcon(RiskLevel? level) {
    switch (level) {
      case RiskLevel.safe:
        return Icons.check_circle_outline;
      case RiskLevel.suspicious:
        return Icons.warning_amber_outlined;
      case RiskLevel.fraud:
        return Icons.dangerous_outlined;
      case null:
        return Icons.payment_outlined;
    }
  }
}
