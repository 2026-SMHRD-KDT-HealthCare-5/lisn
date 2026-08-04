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
        //
        // ⚠ 다만 9pt 아래로는 내리지 않습니다. 홈처럼 브랜드를 작게 쓰는
        //   자리에서 비율만 따르면 LISN 이 7pt 가 돼 글자가 뭉갭니다.
        Padding(
          padding: EdgeInsets.only(top: size * .18),
          child: Text('LISN',
              style: TextStyle(
                  fontSize: (size * .5).clamp(9.0, 40.0),
                  fontWeight: FontWeight.w800,
                  letterSpacing: .5,
                  color: const Color(0xFF8D98E8))),
        ),
      ],
    );
  }
}

/// 마음이의 표정.
///
/// ⚠ **위기 상태에서 웃는 얼굴을 쓰지 마세요.** 「지금 마음이 많이 힘들어 보여요」
///   옆에서 캐릭터가 웃고 있으면 공감이 아니라 **무시로 읽힙니다.**
///
/// ⚠ **그렇다고 슬픈 표정을 쓰지도 마세요.** 캐릭터가 같이 괴로워하면 감정을 더
///   키우고, 사용자가 자기 상태를 「남까지 힘들게 하는 것」으로 받아들이게 됩니다.
///   위기 화면에 경고색을 쓰지 않는 것과 같은 이유입니다.
///
/// 그래서 위기에는 **담담한 표정**입니다. 판단하지 않고 곁에 있는 상태.
enum MascotMood {
  /// 기본. 웃는 눈.
  smile,

  /// 주의·심각. 웃지 않되 슬퍼하지도 않습니다.
  calm,

  /// 응답을 기다리는 중.
  thinking,
}

class MaeumeMascot extends StatelessWidget {
  const MaeumeMascot({super.key, this.size = 82, this.mood = MascotMood.smile});

  final double size;
  final MascotMood mood;

  MascotMood get _mood => mood;

  /// 서버가 준 위험 단계로 표정을 정합니다.
  ///
  /// **앱이 점수로 다시 판정하지 않습니다**(데이터베이스요구사항분석서 6항). `risk_level` 만 봅니다.
  static MascotMood moodFor(String? riskLevel) => switch (riskLevel) {
        'CRITICAL' || 'CAUTION' => MascotMood.calm,
        _ => MascotMood.smile,
      };

  @override
  Widget build(BuildContext context) {
    // 담담한 표정에도 색을 어둡게 하지 않습니다. 화면이 무거워지면 사용자가
    // 앱을 피하게 됩니다 — 위기 화면에 경고색을 안 쓰는 것과 같은 이유입니다.
    final gradient = switch (_mood) {
      MascotMood.thinking => const [Color(0xFFF8FFFF), Color(0xFFB9DFE7)],
      _ => const [Colors.white, Color(0xFFD7E2FF), Color(0xFFB9CAF3)],
    };

    return Container(
      width: size,
      height: size * .88,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(size / 2),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: gradient,
        ),
        boxShadow: const [
          BoxShadow(
              color: Color(0x1E586AA6), blurRadius: 22, offset: Offset(0, 10))
        ],
      ),
      alignment: Alignment.center,
      child: switch (_mood) {
        MascotMood.thinking => Icon(Icons.smart_toy_rounded,
            color: const Color(0xFF3E8EA0), size: size * .38),
        // 'ᴗ' 웃는 입 → '·' 다문 입. 눈은 그대로라 시선은 계속 사용자를 향합니다.
        MascotMood.calm => Text('• · •',
            style: TextStyle(
                color: AppColors.navy,
                fontSize: size * .16,
                fontWeight: FontWeight.w800)),
        MascotMood.smile => Text('• ᴗ •',
            style: TextStyle(
                color: AppColors.navy,
                fontSize: size * .16,
                fontWeight: FontWeight.w800)),
      },
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

/// 다시 불러오는 동안 남겨두는 직전 내용.
///
/// **다시 조회할 때 화면을 로딩으로 갈아치우지 않습니다.** 보여줄 것이 이미
/// 있는데 비우면 본문이 통째로 접혔다 펴져 화면이 크게 튑니다. 실제로
/// 홈·라이프로그·리포트·설정 네 화면에서 지적을 받아 고쳤습니다.
///
/// 로딩 표시는 **보여줄 것이 아직 없을 때만**(최초 진입) 씁니다.
///
/// ⚠ 조작을 막는 것이 핵심입니다. 흐린 값은 곧 덮어써지므로, 이 사이 토글을
///   누르면 사라질 값을 바꾸게 됩니다.
///
/// ⚠ 이 안에 `RepaintBoundary` 를 두지 마세요. 리포트 PDF 는 화면을 캡처해
///   만들기 때문에, 흐린 상태가 찍히면 **바뀐 기간의 머리말에 이전 기간의
///   그림**이 들어갑니다.
class StaleContent extends StatelessWidget {
  const StaleContent({super.key, required this.child});

  final Widget child;

  /// 갱신 중임이 보이되 내용은 읽을 수 있는 정도.
  static const double opacity = 0.45;

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: Opacity(opacity: opacity, child: child),
    );
  }
}
