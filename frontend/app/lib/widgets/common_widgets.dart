import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

/// 서비스명 표기 — **귀기울임**
///
/// ⚠ 여기에 '마음이'를 쓰지 않습니다. 그건 챗봇 캐릭터의 이름이고
///   서비스명이 아닙니다(SD-03 확정). 산출물 5종과 발표자료, 관리자 웹이
///   모두 '귀기울임(LISN)'을 쓰므로 앱만 다른 이름이면 정합성이 깨집니다.
///
///   '마음이'는 **캐릭터가 말하거나 캐릭터를 가리킬 때만** 씁니다.
///   예) '마음이가 생각하고 있어요' · 페르소나 프롬프트의 자기소개
class LisnBrand extends StatelessWidget {
  const LisnBrand({super.key, this.size = 23});
  final double size;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text('귀기울임',
            style: TextStyle(
                fontSize: size,
                fontWeight: FontWeight.w900,
                color: const Color(0xFF24325F))),
        const SizedBox(width: 4),
        // 영문 표기는 한글 서비스명보다 작게 둡니다. 같은 크기로 나란히 두면
        // 둘이 별개 이름처럼 읽힙니다.
        Padding(
          padding: EdgeInsets.only(top: size * .18),
          child: Text('LISN',
              style: TextStyle(
                  fontSize: size * .5,
                  fontWeight: FontWeight.w800,
                  letterSpacing: .5,
                  color: const Color(0xFF8D98E8))),
        ),
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
