import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

class MaeumeBrand extends StatelessWidget {
  const MaeumeBrand({super.key, this.size = 23});
  final double size;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text('마음이',
            style: TextStyle(
                fontSize: size,
                fontWeight: FontWeight.w900,
                color: const Color(0xFF24325F))),
        const SizedBox(width: 3),
        Icon(Icons.favorite, size: size * .72, color: const Color(0xFF8D98E8)),
      ],
    );
  }
}

class MaeumeMascot extends StatelessWidget {
  const MaeumeMascot({super.key, this.size = 82, this.thinking = false});
  final double size;
  final bool thinking;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size * .88,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(size / 2),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: thinking
              ? const [Color(0xFFF8FFFF), Color(0xFFB9DFE7)]
              : const [Colors.white, Color(0xFFD7E2FF), Color(0xFFB9CAF3)],
        ),
        boxShadow: const [
          BoxShadow(
              color: Color(0x1E586AA6), blurRadius: 22, offset: Offset(0, 10))
        ],
      ),
      alignment: Alignment.center,
      child: thinking
          ? Icon(Icons.smart_toy_rounded,
              color: const Color(0xFF3E8EA0), size: size * .38)
          : Text('• ᴗ •',
              style: TextStyle(
                  color: AppColors.navy,
                  fontSize: size * .16,
                  fontWeight: FontWeight.w800)),
    );
  }
}

class AppCard extends StatelessWidget {
  const AppCard(
      {super.key,
      required this.child,
      this.padding = const EdgeInsets.all(16),
      this.color = Colors.white});
  final Widget child;
  final EdgeInsets padding;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: padding,
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppColors.line),
        boxShadow: const [
          BoxShadow(
              color: Color(0x0C374473), blurRadius: 24, offset: Offset(0, 8))
        ],
      ),
      child: Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(18),
        child: child,
      ),
    );
  }
}

class SectionTitle extends StatelessWidget {
  const SectionTitle(this.title, {super.key, this.trailing});
  final String title;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
            child: Text(title,
                style: const TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w800,
                    color: AppColors.navy))),
        if (trailing != null) trailing!,
      ],
    );
  }
}
