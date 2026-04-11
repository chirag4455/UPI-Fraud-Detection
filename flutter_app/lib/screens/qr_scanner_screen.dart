import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:provider/provider.dart';
import '../providers/prediction_provider.dart';
import '../services/qr_scanner_service.dart';
import '../utils/constants.dart';
import '../widgets/custom_app_bar.dart';
import 'transaction_input_screen.dart';

class QrScannerScreen extends StatefulWidget {
  const QrScannerScreen({super.key});

  @override
  State<QrScannerScreen> createState() => _QrScannerScreenState();
}

class _QrScannerScreenState extends State<QrScannerScreen> {
  final MobileScannerController _controller = MobileScannerController();
  bool _scanned = false;
  String? _errorMessage;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _onDetect(BarcodeCapture capture) {
    if (_scanned) return;
    final barcode = capture.barcodes.firstOrNull;
    if (barcode == null) return;
    final raw = barcode.rawValue ?? '';
    if (raw.isEmpty) return;

    setState(() => _scanned = true);

    try {
      final parsed = QrScannerService.parseUpiQr(raw);
      _navigateToInput(parsed, raw);
    } catch (e) {
      setState(() {
        _errorMessage = 'Invalid QR: ${e.toString()}';
        _scanned = false;
      });
    }
  }

  void _navigateToInput(Map<String, String?> parsed, String raw) {
    Navigator.pushReplacement(
      context,
      MaterialPageRoute(
        builder: (_) => TransactionInputScreen(
          prefillVpa: parsed['vpa'],
          prefillName: parsed['payeeName'],
          prefillAmount: parsed['amount'] != null
              ? double.tryParse(parsed['amount']!)
              : null,
          prefillNote: parsed['note'],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: const CustomAppBar(title: 'Scan UPI QR'),
      body: Stack(
        children: [
          MobileScanner(
            controller: _controller,
            onDetect: _onDetect,
          ),
          // Viewfinder overlay
          _ScannerOverlay(),
          // Bottom controls
          Positioned(
            bottom: 0,
            left: 0,
            right: 0,
            child: Container(
              color: Colors.black87,
              padding: const EdgeInsets.all(AppConstants.spaceLg),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (_errorMessage != null)
                    Padding(
                      padding:
                          const EdgeInsets.only(bottom: AppConstants.spaceMd),
                      child: Text(
                        _errorMessage!,
                        style: const TextStyle(color: Colors.redAccent),
                        textAlign: TextAlign.center,
                      ),
                    ),
                  Text(
                    'Point camera at a UPI QR code',
                    style: const TextStyle(color: Colors.white70, fontSize: 14),
                  ),
                  const SizedBox(height: AppConstants.spaceMd),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                    children: [
                      // Torch
                      IconButton(
                        onPressed: () => _controller.toggleTorch(),
                        icon: const Icon(Icons.flashlight_on_outlined),
                        color: Colors.white,
                        tooltip: 'Toggle torch',
                      ),
                      // Flip camera
                      IconButton(
                        onPressed: () => _controller.switchCamera(),
                        icon: const Icon(Icons.flip_camera_ios_outlined),
                        color: Colors.white,
                        tooltip: 'Flip camera',
                      ),
                      // Manual entry
                      TextButton.icon(
                        onPressed: () {
                          Navigator.pushReplacement(
                            context,
                            MaterialPageRoute(
                                builder: (_) => const TransactionInputScreen()),
                          );
                        },
                        icon: const Icon(Icons.edit, color: Colors.white70),
                        label: const Text(
                          'Manual Entry',
                          style: TextStyle(color: Colors.white70),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Translucent overlay with a square cutout to guide the user
class _ScannerOverlay extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      painter: _OverlayPainter(),
      child: Container(),
    );
  }
}

class _OverlayPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    const cutoutSize = 260.0;
    final cutoutRect = Rect.fromCenter(
      center: Offset(size.width / 2, size.height / 2 - 40),
      width: cutoutSize,
      height: cutoutSize,
    );

    final paint = Paint()..color = Colors.black54;

    // Four shadow regions around the cutout
    canvas.drawRect(Rect.fromLTRB(0, 0, size.width, cutoutRect.top), paint);
    canvas.drawRect(
        Rect.fromLTRB(0, cutoutRect.top, cutoutRect.left, cutoutRect.bottom),
        paint);
    canvas.drawRect(
        Rect.fromLTRB(
            cutoutRect.right, cutoutRect.top, size.width, cutoutRect.bottom),
        paint);
    canvas.drawRect(
        Rect.fromLTRB(0, cutoutRect.bottom, size.width, size.height), paint);

    // Corner brackets
    const bracketLen = 24.0;
    const bracketWidth = 3.0;
    final bracketPaint = Paint()
      ..color = Colors.white
      ..strokeWidth = bracketWidth
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    void drawCorner(Offset corner, double dx, double dy) {
      canvas.drawLine(corner, corner.translate(dx, 0), bracketPaint);
      canvas.drawLine(corner, corner.translate(0, dy), bracketPaint);
    }

    drawCorner(cutoutRect.topLeft, bracketLen, bracketLen);
    drawCorner(cutoutRect.topRight, -bracketLen, bracketLen);
    drawCorner(cutoutRect.bottomLeft, bracketLen, -bracketLen);
    drawCorner(cutoutRect.bottomRight, -bracketLen, -bracketLen);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
