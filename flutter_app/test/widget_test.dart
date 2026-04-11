import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:upi_fraud_detection/models/prediction.dart';
import 'package:upi_fraud_detection/widgets/risk_gauge.dart';
import 'package:upi_fraud_detection/widgets/layer_breakdown_card.dart';
import 'package:upi_fraud_detection/widgets/transaction_card.dart';
import 'package:upi_fraud_detection/widgets/custom_app_bar.dart';
import '../fixtures/mock_data.dart';

Widget _wrap(Widget child) {
  return MaterialApp(
    theme: ThemeData(useMaterial3: true),
    home: Scaffold(body: child),
  );
}

void main() {
  group('RiskGauge widget', () {
    testWidgets('renders score text', (tester) async {
      await tester.pumpWidget(_wrap(
        RiskGauge(
          score: 75.0,
          riskLevel: RiskLevel.fraud,
          animate: false,
        ),
      ));
      expect(find.text('75'), findsOneWidget);
    });

    testWidgets('renders SAFE verdict', (tester) async {
      await tester.pumpWidget(_wrap(
        RiskGauge(
          score: 15.0,
          riskLevel: RiskLevel.safe,
          animate: false,
        ),
      ));
      expect(find.textContaining('SAFE'), findsAtLeastNWidgets(1));
    });

    testWidgets('renders SUSPICIOUS verdict', (tester) async {
      await tester.pumpWidget(_wrap(
        RiskGauge(
          score: 45.0,
          riskLevel: RiskLevel.suspicious,
          animate: false,
        ),
      ));
      expect(find.textContaining('SUSPICIOUS'), findsAtLeastNWidgets(1));
    });

    testWidgets('renders FRAUD verdict', (tester) async {
      await tester.pumpWidget(_wrap(
        RiskGauge(
          score: 80.0,
          riskLevel: RiskLevel.fraud,
          animate: false,
        ),
      ));
      expect(find.textContaining('FRAUD'), findsAtLeastNWidgets(1));
    });

    testWidgets('renders 0 and 100 labels', (tester) async {
      await tester.pumpWidget(_wrap(
        RiskGauge(
          score: 50.0,
          riskLevel: RiskLevel.suspicious,
          animate: false,
        ),
      ));
      expect(find.text('0'), findsOneWidget);
      expect(find.text('100'), findsOneWidget);
    });
  });

  group('LayerBreakdownCard widget', () {
    testWidgets('renders detection layers title', (tester) async {
      await tester.pumpWidget(_wrap(
        LayerBreakdownCard(prediction: mockPredictionSafe),
      ));
      expect(find.text('Detection Layers'), findsOneWidget);
    });

    testWidgets('renders all layer names', (tester) async {
      await tester.pumpWidget(_wrap(
        LayerBreakdownCard(prediction: mockPredictionSafe),
      ));
      for (final layer in mockPredictionSafe.layerScores) {
        expect(find.text(layer.layer), findsOneWidget);
      }
    });

    testWidgets('renders ensemble votes section', (tester) async {
      await tester.pumpWidget(_wrap(
        LayerBreakdownCard(prediction: mockPredictionSafe),
      ));
      expect(find.text('Ensemble Votes'), findsOneWidget);
      for (final vote in mockPredictionSafe.ensembleVotes) {
        expect(find.text(vote.model), findsOneWidget);
      }
    });
  });

  group('TransactionCard widget', () {
    testWidgets('renders payee name', (tester) async {
      await tester.pumpWidget(_wrap(
        TransactionCard(transaction: mockTransaction1),
      ));
      expect(find.text('Test Merchant'), findsOneWidget);
    });

    testWidgets('renders masked VPA', (tester) async {
      await tester.pumpWidget(_wrap(
        TransactionCard(transaction: mockTransaction1),
      ));
      expect(find.text('me***@okaxis'), findsOneWidget);
    });

    testWidgets('renders verdict when prediction provided', (tester) async {
      await tester.pumpWidget(_wrap(
        TransactionCard(
          transaction: mockTransaction1,
          prediction: mockPredictionSafe,
        ),
      ));
      expect(find.text('SAFE'), findsOneWidget);
    });

    testWidgets('calls onTap when tapped', (tester) async {
      bool tapped = false;
      await tester.pumpWidget(_wrap(
        TransactionCard(
          transaction: mockTransaction1,
          onTap: () => tapped = true,
        ),
      ));
      await tester.tap(find.byType(TransactionCard));
      await tester.pump();
      expect(tapped, isTrue);
    });
  });

  group('CustomAppBar widget', () {
    testWidgets('renders title', (tester) async {
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          appBar: const CustomAppBar(title: 'Test Title'),
          body: const SizedBox.shrink(),
        ),
      ));
      expect(find.text('Test Title'), findsOneWidget);
    });

    testWidgets('renders actions', (tester) async {
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          appBar: CustomAppBar(
            title: 'Test',
            actions: [
              IconButton(
                onPressed: () {},
                icon: const Icon(Icons.settings),
              ),
            ],
          ),
          body: const SizedBox.shrink(),
        ),
      ));
      expect(find.byIcon(Icons.settings), findsOneWidget);
    });
  });

  group('OfflineBanner widget', () {
    testWidgets('renders offline message', (tester) async {
      await tester.pumpWidget(_wrap(const OfflineBanner()));
      expect(find.textContaining('Offline'), findsOneWidget);
    });
  });

  group('LoadingOverlay widget', () {
    testWidgets('shows child when not loading', (tester) async {
      await tester.pumpWidget(_wrap(
        const LoadingOverlay(
          isLoading: false,
          child: Text('Content'),
        ),
      ));
      expect(find.text('Content'), findsOneWidget);
      expect(find.byType(CircularProgressIndicator), findsNothing);
    });

    testWidgets('shows spinner when loading', (tester) async {
      await tester.pumpWidget(_wrap(
        const LoadingOverlay(
          isLoading: true,
          message: 'Please wait...',
          child: Text('Content'),
        ),
      ));
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      expect(find.text('Please wait...'), findsOneWidget);
    });
  });
}
