import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../models/prediction.dart';
import '../utils/constants.dart';
import '../utils/formatters.dart';

/// Animated arc gauge that visually represents a fraud risk score (0–100).
///
/// Colour gradient:
///   0–30  → Green (safe)
///   30–60 → Amber (suspicious)
///   60–100→ Red (fraud)
class RiskGauge extends StatefulWidget {
  final double score;
  final RiskLevel riskLevel;
  final double size;
  final bool animate;

  const RiskGauge({
    super.key,
    required this.score,
    required this.riskLevel,
    this.size = 200,
    this.animate = true,
  });

  @override
  State<RiskGauge> createState() => _RiskGaugeState();
}

class _RiskGaugeState extends State<RiskGauge>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _scoreAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: AppConstants.animGauge,
    );
    _scoreAnimation = Tween<double>(begin: 0, end: widget.score).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeOutCubic),
    );
    if (widget.animate) {
      _controller.forward();
    } else {
      _controller.value = 1.0;
    }
  }

  @override
  void didUpdateWidget(RiskGauge oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.score != widget.score) {
      _scoreAnimation =
          Tween<double>(begin: oldWidget.score, end: widget.score).animate(
        CurvedAnimation(parent: _controller, curve: Curves.easeOutCubic),
      );
      _controller
        ..reset()
        ..forward();
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Color _colorForScore(double score) {
    if (score < AppConstants.colorSafe.value) {
      return AppConstants.colorSafe;
    }
    if (score < 30) return AppConstants.colorSafe;
    if (score < 60) return AppConstants.colorSuspicious;
    return AppConstants.colorFraud;
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _scoreAnimation,
      builder: (context, _) {
        final currentScore = _scoreAnimation.value;
        final color = _colorForScore(currentScore);
        return SizedBox(
          width: widget.size,
          height: widget.size * 0.7,
          child: Stack(
            alignment: Alignment.bottomCenter,
            children: [
              CustomPaint(
                size: Size(widget.size, widget.size * 0.7),
                painter: _GaugePainter(
                  score: currentScore,
                  color: color,
                  backgroundColor:
                      Theme.of(context).colorScheme.surfaceContainerHighest,
                  strokeWidth: widget.size * 0.12,
                ),
              ),
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      currentScore.toStringAsFixed(0),
                      style: TextStyle(
                        fontSize: widget.size * 0.22,
                        fontWeight: FontWeight.bold,
                        color: color,
                      ),
                    ),
                    Text(
                      _verdictLabel(widget.riskLevel),
                      style: TextStyle(
                        fontSize: widget.size * 0.08,
                        fontWeight: FontWeight.w600,
                        color: color,
                        letterSpacing: 1.2,
                      ),
                    ),
                  ],
                ),
              ),
              // Min / Max labels
              Positioned(
                left: 0,
                bottom: 0,
                child: Text(
                  '0',
                  style: TextStyle(
                    fontSize: widget.size * 0.07,
                    color:
                        Theme.of(context).colorScheme.onSurface.withOpacity(0.5),
                  ),
                ),
              ),
              Positioned(
                right: 0,
                bottom: 0,
                child: Text(
                  '100',
                  style: TextStyle(
                    fontSize: widget.size * 0.07,
                    color:
                        Theme.of(context).colorScheme.onSurface.withOpacity(0.5),
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  String _verdictLabel(RiskLevel level) {
    switch (level) {
      case RiskLevel.safe:
        return '✓ SAFE';
      case RiskLevel.suspicious:
        return '⚠ SUSPICIOUS';
      case RiskLevel.fraud:
        return '✗ FRAUD';
    }
  }
}

class _GaugePainter extends CustomPainter {
  final double score;
  final Color color;
  final Color backgroundColor;
  final double strokeWidth;

  _GaugePainter({
    required this.score,
    required this.color,
    required this.backgroundColor,
    required this.strokeWidth,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height);
    final radius = size.width / 2 - strokeWidth / 2;
    const startAngle = math.pi;
    const sweepAngle = math.pi;

    // Background arc
    final bgPaint = Paint()
      ..color = backgroundColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      startAngle,
      sweepAngle,
      false,
      bgPaint,
    );

    // Foreground arc
    final fgPaint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    final progress = (score.clamp(0, 100)) / 100;
    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      startAngle,
      sweepAngle * progress,
      false,
      fgPaint,
    );
  }

  @override
  bool shouldRepaint(_GaugePainter old) =>
      old.score != score || old.color != color;
}
