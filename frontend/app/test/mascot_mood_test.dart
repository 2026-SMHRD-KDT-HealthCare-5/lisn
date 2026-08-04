/// 위기 상태에서 마음이가 웃지 않아야 한다
///
/// 「지금 마음이 많이 힘들어 보여요」 옆에서 캐릭터가 웃고 있으면 공감이 아니라
/// **무시로 읽힙니다.** 반대로 슬픈 표정을 쓰면 감정을 더 키우고, 사용자가 자기
/// 상태를 「남까지 힘들게 하는 것」으로 받아들이게 됩니다.
///
/// 그래서 위기에는 **담담한 표정**입니다. 이 테스트는 그 규칙을 고정합니다.
library;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:maeume_care/widgets/common_widgets.dart';

/// 위젯 안의 표정 문자열.
String faceOf(WidgetTester tester) {
  final text = tester.widget<Text>(
    find.descendant(of: find.byType(MaeumeMascot), matching: find.byType(Text)),
  );
  return text.data ?? '';
}

const _smile = '• ᴗ •';
const _calm = '• · •';

Future<void> _pump(WidgetTester tester, MascotMood mood) {
  return tester.pumpWidget(MaterialApp(
    home: Scaffold(body: Center(child: MaeumeMascot(mood: mood))),
  ));
}

void main() {
  testWidgets('평소에는 웃는 표정이다', (tester) async {
    await _pump(tester, MascotMood.smile);
    expect(faceOf(tester), _smile);
  });

  testWidgets('담담한 표정은 웃지 않는다', (tester) async {
    await _pump(tester, MascotMood.calm);
    expect(faceOf(tester), isNot(_smile));
    expect(faceOf(tester), _calm);
  });

  test('심각·주의는 담담한 표정으로 매핑된다', () {
    // ⚠ 서버가 준 risk_level 만 봅니다. 점수로 다시 판정하지 않습니다(데이터베이스요구사항분석서 6항).
    expect(MaeumeMascot.moodFor('CRITICAL'), MascotMood.calm);
    expect(MaeumeMascot.moodFor('CAUTION'), MascotMood.calm);
  });

  test('안정이거나 평가 이력이 없으면 웃는 표정이다', () {
    expect(MaeumeMascot.moodFor('NORMAL'), MascotMood.smile);
    // 미평가는 「위험이 없다」가 아니라 「아직 모른다」입니다. 이때 담담한 표정을
    // 쓰면 가입 직후 사용자에게 이유 없이 무거운 인상을 줍니다.
    expect(MaeumeMascot.moodFor(null), MascotMood.smile);
  });

  test('모르는 값이 와도 담담한 표정으로 떨어지지 않는다', () {
    // 서버가 새 단계를 추가하면 여기서 걸러지지 않습니다. 다만 오타 하나로
    // 전 사용자 화면이 무거워지는 것보다는 낫습니다.
    expect(MaeumeMascot.moodFor('UNKNOWN'), MascotMood.smile);
  });

  testWidgets('응답을 기다릴 때는 표정 대신 아이콘이다', (tester) async {
    await _pump(tester, MascotMood.thinking);
    expect(find.byType(Text), findsNothing);
    expect(find.byIcon(Icons.smart_toy_rounded), findsOneWidget);
  });
}
