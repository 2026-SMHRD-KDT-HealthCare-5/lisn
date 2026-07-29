import 'package:flutter/material.dart';

abstract final class AppColors {
  static const navy = Color(0xFF172147);
  static const primary = Color(0xFF647BEC);
  static const muted = Color(0xFF7C86A5);
  static const line = Color(0xFFE8EBF4);
  static const soft = Color(0xFFF5F7FD);
  static const background = Color(0xFFF7F9FD);
  static const pink = Color(0xFFFFF0F2);
  static const purple = Color(0xFFF1EFFF);
  static const mint = Color(0xFFEAF8F4);
  static const blue = Color(0xFFEAF5FF);
  static const teal = Color(0xFF48AFA1);
}

abstract final class AppTheme {
  static ThemeData get light {
    final scheme = ColorScheme.fromSeed(
      seedColor: AppColors.primary,
      brightness: Brightness.light,
      surface: Colors.white,
    );
    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      scaffoldBackgroundColor: Colors.white,
      fontFamily: 'sans-serif',
      textTheme: const TextTheme(
        headlineLarge:
            TextStyle(color: AppColors.navy, fontWeight: FontWeight.w800),
        headlineMedium:
            TextStyle(color: AppColors.navy, fontWeight: FontWeight.w800),
        titleLarge:
            TextStyle(color: AppColors.navy, fontWeight: FontWeight.w800),
        titleMedium:
            TextStyle(color: AppColors.navy, fontWeight: FontWeight.w700),
        bodyMedium: TextStyle(color: AppColors.navy),
        bodySmall: TextStyle(color: AppColors.muted),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: const Color(0xFFFBFCFF),
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(13),
          borderSide: const BorderSide(color: AppColors.line),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(13),
          borderSide: const BorderSide(color: AppColors.primary, width: 1.4),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          elevation: 0,
          backgroundColor: AppColors.primary,
          foregroundColor: Colors.white,
          minimumSize: const Size.fromHeight(52),
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          textStyle: const TextStyle(fontWeight: FontWeight.w700),
        ),
      ),
    );
  }
}
