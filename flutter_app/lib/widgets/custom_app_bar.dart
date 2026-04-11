import 'package:flutter/material.dart';
import '../utils/constants.dart';

/// Custom app bar with consistent styling across all screens.
class CustomAppBar extends StatelessWidget implements PreferredSizeWidget {
  final String title;
  final List<Widget>? actions;
  final Widget? leading;
  final bool showBackButton;
  final PreferredSizeWidget? bottom;

  const CustomAppBar({
    super.key,
    required this.title,
    this.actions,
    this.leading,
    this.showBackButton = true,
    this.bottom,
  });

  @override
  Size get preferredSize => Size.fromHeight(
        kToolbarHeight + (bottom?.preferredSize.height ?? 0),
      );

  @override
  Widget build(BuildContext context) {
    return AppBar(
      title: Text(title),
      leading: showBackButton && Navigator.of(context).canPop()
          ? BackButton(onPressed: () => Navigator.of(context).pop())
          : leading,
      automaticallyImplyLeading: showBackButton,
      actions: actions,
      bottom: bottom,
    );
  }
}

/// A status banner shown at the top of screens when the API is offline.
class OfflineBanner extends StatelessWidget {
  const OfflineBanner({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      color: AppConstants.colorSuspicious.withOpacity(0.9),
      padding: const EdgeInsets.symmetric(
        vertical: AppConstants.spaceSm,
        horizontal: AppConstants.spaceMd,
      ),
      child: const Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.wifi_off, color: Colors.white, size: 16),
          SizedBox(width: AppConstants.spaceSm),
          Text(
            'Offline — showing cached data',
            style: TextStyle(color: Colors.white, fontSize: 13),
          ),
        ],
      ),
    );
  }
}

/// A loading overlay widget
class LoadingOverlay extends StatelessWidget {
  final bool isLoading;
  final Widget child;
  final String? message;

  const LoadingOverlay({
    super.key,
    required this.isLoading,
    required this.child,
    this.message,
  });

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        child,
        if (isLoading)
          Container(
            color: Colors.black.withOpacity(0.4),
            child: Center(
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(AppConstants.spaceLg),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const CircularProgressIndicator(),
                      if (message != null) ...[
                        const SizedBox(height: AppConstants.spaceMd),
                        Text(message!),
                      ],
                    ],
                  ),
                ),
              ),
            ),
          ),
      ],
    );
  }
}
