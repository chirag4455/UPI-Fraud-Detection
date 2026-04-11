import 'package:flutter/material.dart';
import 'constants.dart';

/// Material Design 3 theme for the UPI Fraud Detection app
class AppTheme {
  static const _seedColor = Color(0xFF1565C0); // Blue 800

  // ---------------------------------------------------------------------------
  // Light theme
  // ---------------------------------------------------------------------------

  static ThemeData get light {
    final colorScheme = ColorScheme.fromSeed(
      seedColor: _seedColor,
      brightness: Brightness.light,
    );
    return _buildTheme(colorScheme);
  }

  // ---------------------------------------------------------------------------
  // Dark theme
  // ---------------------------------------------------------------------------

  static ThemeData get dark {
    final colorScheme = ColorScheme.fromSeed(
      seedColor: _seedColor,
      brightness: Brightness.dark,
    );
    return _buildTheme(colorScheme);
  }

  // ---------------------------------------------------------------------------
  // Shared theme builder
  // ---------------------------------------------------------------------------

  static ThemeData _buildTheme(ColorScheme colorScheme) {
    return ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      fontFamily: 'Inter',

      // AppBar
      appBarTheme: AppBarTheme(
        centerTitle: true,
        elevation: 0,
        scrolledUnderElevation: 2,
        backgroundColor: colorScheme.surface,
        foregroundColor: colorScheme.onSurface,
        titleTextStyle: TextStyle(
          fontFamily: 'Inter',
          fontWeight: FontWeight.w600,
          fontSize: 18,
          color: colorScheme.onSurface,
        ),
      ),

      // Cards
      cardTheme: CardThemeData(
        elevation: 2,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppConstants.radiusLg),
        ),
        margin: const EdgeInsets.symmetric(
          horizontal: AppConstants.spaceMd,
          vertical: AppConstants.spaceSm,
        ),
      ),

      // Elevated buttons
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppConstants.radiusMd),
          ),
          padding: const EdgeInsets.symmetric(
            horizontal: AppConstants.spaceLg,
            vertical: AppConstants.spaceMd,
          ),
          textStyle: const TextStyle(
            fontFamily: 'Inter',
            fontWeight: FontWeight.w600,
            fontSize: 16,
          ),
        ),
      ),

      // Outlined buttons
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppConstants.radiusMd),
          ),
          padding: const EdgeInsets.symmetric(
            horizontal: AppConstants.spaceLg,
            vertical: AppConstants.spaceMd,
          ),
        ),
      ),

      // Input decoration
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppConstants.radiusMd),
          borderSide: BorderSide.none,
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppConstants.radiusMd),
          borderSide: BorderSide(color: colorScheme.outline.withOpacity(0.5)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppConstants.radiusMd),
          borderSide: BorderSide(color: colorScheme.primary, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppConstants.radiusMd),
          borderSide: BorderSide(color: colorScheme.error),
        ),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: AppConstants.spaceMd,
          vertical: AppConstants.spaceMd,
        ),
      ),

      // Bottom nav bar
      navigationBarTheme: NavigationBarThemeData(
        elevation: 4,
        labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
        indicatorColor: colorScheme.primaryContainer,
      ),

      // Chip
      chipTheme: ChipThemeData(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppConstants.radiusFull),
        ),
      ),
    );
  }
}
