import 'package:flutter/material.dart';
import '../models/prediction.dart';
import '../utils/constants.dart';

/// Card that shows per-layer fraud scores with explanations.
class LayerBreakdownCard extends StatelessWidget {
  final Prediction prediction;

  const LayerBreakdownCard({super.key, required this.prediction});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppConstants.spaceMd),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Detection Layers',
              style: theme.textTheme.titleMedium
                  ?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: AppConstants.spaceMd),
            ...prediction.layerScores.map(
              (layer) => _LayerRow(layer: layer),
            ),
            if (prediction.ensembleVotes.isNotEmpty) ...[
              const Divider(height: AppConstants.spaceLg),
              Text(
                'Ensemble Votes',
                style: theme.textTheme.titleSmall
                    ?.copyWith(fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: AppConstants.spaceSm),
              ...prediction.ensembleVotes.map(
                (vote) => _VoteRow(vote: vote),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _LayerRow extends StatelessWidget {
  final LayerScore layer;

  const _LayerRow({required this.layer});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final color = _colorForScore(layer.score);
    return Padding(
      padding: const EdgeInsets.only(bottom: AppConstants.spaceMd),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(_iconForLayer(layer.layer), size: 18, color: color),
              const SizedBox(width: AppConstants.spaceSm),
              Expanded(
                child: Text(
                  layer.layer,
                  style: theme.textTheme.bodyMedium
                      ?.copyWith(fontWeight: FontWeight.w600),
                ),
              ),
              Text(
                layer.score.toStringAsFixed(1),
                style: theme.textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: color,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppConstants.spaceXs),
          ClipRRect(
            borderRadius: BorderRadius.circular(AppConstants.radiusFull),
            child: LinearProgressIndicator(
              value: layer.score / 100,
              backgroundColor:
                  theme.colorScheme.surfaceContainerHighest,
              valueColor: AlwaysStoppedAnimation<Color>(color),
              minHeight: 6,
            ),
          ),
          if (layer.explanation.isNotEmpty) ...[
            const SizedBox(height: AppConstants.spaceXs),
            Text(
              layer.explanation,
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurface.withOpacity(0.6),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Color _colorForScore(double score) {
    if (score < 30) return AppConstants.colorSafe;
    if (score < 60) return AppConstants.colorSuspicious;
    return AppConstants.colorFraud;
  }

  IconData _iconForLayer(String layer) {
    switch (layer.toUpperCase()) {
      case 'UBTS':
        return Icons.person_outline;
      case 'WTS':
        return Icons.account_balance_wallet_outlined;
      case 'WEBSITE TRUST':
        return Icons.language_outlined;
      case 'LSTM':
        return Icons.timeline_outlined;
      case 'ENSEMBLE':
        return Icons.hub_outlined;
      default:
        return Icons.layers_outlined;
    }
  }
}

class _VoteRow extends StatelessWidget {
  final EnsembleVote vote;

  const _VoteRow({required this.vote});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isFraud = vote.verdict.toUpperCase().contains('FRAUD');
    final color = isFraud ? AppConstants.colorFraud : AppConstants.colorSafe;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppConstants.spaceXs),
      child: Row(
        children: [
          Icon(
            isFraud ? Icons.cancel_outlined : Icons.check_circle_outline,
            size: 16,
            color: color,
          ),
          const SizedBox(width: AppConstants.spaceSm),
          Expanded(
            child: Text(
              vote.model,
              style: theme.textTheme.bodySmall,
            ),
          ),
          Text(
            '${(vote.probability * 100).toStringAsFixed(1)}%',
            style: theme.textTheme.bodySmall?.copyWith(
              fontWeight: FontWeight.w600,
              color: color,
            ),
          ),
        ],
      ),
    );
  }
}
