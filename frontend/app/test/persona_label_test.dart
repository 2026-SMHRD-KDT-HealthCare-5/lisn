/// 챗봇 성격 이름이 화면설계서와 갈리지 않게 — MAIN_CHAT_01
///
/// ## 왜 이 테스트가 필요한가
///
/// 앱만 「다정한 공감가 / 이성적인 분석가」를 쓰고 있었습니다. 화면설계서·
/// 프로젝트 기획서·시안 **세 곳이 모두** 「따스한 공감형 / 현실적인
/// 조언형」인데 앱 혼자 달랐습니다.
///
/// 화면에 큼직하게 뜨는 글자라 눈에 띌 것 같지만, **어느 쪽이 맞는지 알아야만
/// 문제로 보입니다.** 앱만 보면 아무 이상이 없어서 심사 자리에서 문서와 나란히
/// 놓기 전까지 아무도 눈치채지 못합니다.
///
/// ⚠ 이건 `health_permission_drift_test.dart`·`test_schema_drift.py` 와 같은
///   종류입니다. **정본이 딴 데 있는 값**을 기계가 대조합니다.
///
/// 이름을 바꿔야 한다면 **화면설계서를 먼저 고치고** 여기를 맞추세요.
library;

import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:maeume_care/screens/chat_screen.dart';

/// 화면설계서 추출본. `python tools/doc2txt.py` 로 갱신됩니다.
const _extract = '../../docs/extracted/화면설계서_귀기울임.txt';

void main() {
  test('추출본을 실제로 읽었는지 먼저 확인한다', () {
    // ⚠ 파일이 없거나 비면 아래 검사가 전부 통과해버립니다.
    final f = File(_extract);
    expect(f.existsSync(), isTrue, reason: '$_extract 가 없습니다');
    expect(f.readAsStringSync(), contains('MAIN_CHAT_01'));
  });

  /// PPTX 는 한 줄이 여러 런으로 갈리고, 편집할 때마다 갈리는 자리가
  /// 바뀝니다. 추출기가 런 사이에 공백을 넣으므로 `[T]` 가 `[ T ]` 로
  /// 나오기도 합니다. 실제로 2026.08.05 재저장에서 그렇게 깨졌습니다.
  ///
  /// **공백만 지우고 비교합니다.** 문안이 바뀌면 여전히 잡히고, 서식
  /// 때문에 생긴 공백에는 흔들리지 않습니다. `safety.keyword_scan()` 이
  /// 사전과 입력에서 공백만 지우고 비교하는 것과 같은 방식입니다.
  String squash(String s) => s.replaceAll(RegExp(r'\s+'), '');

  test('성격 이름이 화면설계서 문안과 같다', () {
    final doc = squash(File(_extract).readAsStringSync());
    for (final p in ChatPersona.values) {
      expect(doc, contains(squash(p.label)),
          reason: '「${p.label}」이 화면설계서에 없습니다. '
              '앱만 바꾸지 말고 문서를 먼저 고치세요');
    }
  });

  test('화면설명의 [F]·[T] 표기와 같다', () {
    final doc = squash(File(_extract).readAsStringSync());
    // 화면설명 ❶ [F] 따스한 공감형 : … / ❷ [T] 현실적인 조언형 : …
    expect(
        doc,
        contains(squash(
            '[${ChatPersona.feeling.tag}] ${ChatPersona.feeling.label}')));
    expect(
        doc,
        contains(squash(
            '[${ChatPersona.thinking.tag}] ${ChatPersona.thinking.label}')));
  });

  test('⚠ 서버 코드 값은 스키마 값 그대로여야 한다', () {
    // 이름을 바꾸다 code 까지 건드리면 서버 CHECK 제약에 걸립니다.
    expect(ChatPersona.feeling.code, 'FRIEND');
    expect(ChatPersona.thinking.code, 'COUNSELOR');
  });

  test('이름이 한 곳에만 적혀 있다', () {
    // ⚠ 전에는 personaName 과 카드에 따로 적혀 있어서 한쪽만 고치면 조용히
    //   갈렸습니다. enum 밖에 리터럴이 다시 생기지 않게 막습니다.
    final src = File('lib/screens/chat_screen.dart').readAsStringSync();
    for (final p in ChatPersona.values) {
      final literal = "'${p.label}'";
      expect(literal.allMatches(src).length, 1,
          reason: '${p.label} 리터럴이 여러 곳에 있습니다. enum 값을 쓰세요');
    }
  });
}
