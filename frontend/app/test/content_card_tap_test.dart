/// 추천 콘텐츠 카드가 실제로 링크를 여는지 — MLCM_400
///
/// ⚠ `external_url` 은 스키마·API·모델에 다 있는데 **앱만 안 쓰고 있었습니다**
///   (2026.08.02 점검). 카드가 제목만 보여주고 눌러도 아무 일이 없었습니다.
///   추천 기능 자체가 무의미해지므로 테스트로 묶어둡니다.
library;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:maeume_care/models/home_models.dart';
import 'package:maeume_care/screens/home_screen.dart';
import 'package:maeume_care/services/home_service.dart';

class _FakeHomeService implements HomeService {
  _FakeHomeService(this._snapshot);

  final HomeSnapshot _snapshot;

  @override
  Future<HomeSnapshot> fetch() async => _snapshot;

  @override
  noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

HomeSnapshot _snapshotWith(List<ContentCard> cards) => HomeSnapshot.fromJson({
      'emotion_today': {
        'emotion_code': 'SADNESS',
        'emotion_name': '슬픔',
        'emotion_score': 55.0,
        'risk_level': 'CAUTION',
        'evaluated_at': '2026-08-02T09:00:00Z',
      },
      'lifelog_summary': {'steps': 3000, 'total_sleep_min': 380},
      'ai_summary': null,
      'action': 'CONTENT',
      'recommendations': [
        for (final c in cards)
          {
            'content_id': c.contentId,
            'category': c.category,
            'title': c.title,
            'description': c.description,
            'external_url': c.externalUrl,
          }
      ],
    });

const _card = ContentCard(
  contentId: 'c1',
  category: 'MUSIC',
  title: '잔잔히 밀려오는 파도소리',
  description: null,
  externalUrl: 'https://gongu.copyright.or.kr/example',
);

const _exerciseCard = ContentCard(
  contentId: 'c2',
  category: 'EXERCISE',
  title: '가볍게 몸 움직이기',
  description: null,
  externalUrl: 'https://health.example/exercise',
);

const _quoteCard = ContentCard(
  contentId: 'c3',
  category: 'ARTICLE',
  title: '오늘의 나에게 건네는 한마디',
  description: null,
  externalUrl: 'https://health.example/quote',
);

const _foodCard = ContentCard(
  contentId: 'c4',
  category: 'FOOD',
  title: '따뜻한 차 한 잔',
  description: null,
  externalUrl: 'https://food.example/tea',
);

/// 홈은 세로로 길어서 기본 테스트 화면(800x600)에서는 추천 섹션이 화면 밖에
/// 있습니다. ListView 가 lazy 라 아예 만들어지지 않으므로 화면을 키웁니다.
void _useTallScreen(WidgetTester tester) {
  tester.view.physicalSize = const Size(1080, 4200);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.reset);
}

void main() {
  testWidgets('추천 카드를 누르면 external_url 을 연다', (tester) async {
    _useTallScreen(tester);
    Uri? opened;
    // 실제 구조와 맞춥니다 — Scaffold 는 MainShell 이 제공하고
    // HomeScreen 은 그 안의 본문입니다(InkWell 은 Material 조상이 필요).
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: HomeScreen(
          userName: '테스터',
          homeService: _FakeHomeService(_snapshotWith(const [_card])),
          linkLauncher: (uri) async {
            opened = uri;
            return true;
          },
        ),
      ),
    ));
    await tester.pumpAndSettle();

    final card = find.byKey(const ValueKey('content-card-c1'));
    expect(card, findsOneWidget, reason: '추천 카드가 그려지지 않았습니다');

    await tester.tap(card);
    await tester.pumpAndSettle();

    expect(opened, Uri.parse('https://gongu.copyright.or.kr/example'));
  });

  testWidgets('링크를 열지 못하면 안내를 띄운다', (tester) async {
    _useTallScreen(tester);
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: HomeScreen(
          userName: '테스터',
          homeService: _FakeHomeService(_snapshotWith(const [_card])),
          linkLauncher: (_) async => false,
        ),
      ),
    ));
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const ValueKey('content-card-c1')));
    await tester.pump();

    expect(find.textContaining('링크를 열 수 없어요'), findsOneWidget);
  });

  testWidgets('홈 최하단에는 음악·운동·문구 추천을 하나씩 보여준다', (tester) async {
    _useTallScreen(tester);
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: HomeScreen(
          homeService: _FakeHomeService(_snapshotWith(
              const [_foodCard, _quoteCard, _exerciseCard, _card])),
        ),
      ),
    ));
    await tester.pumpAndSettle();

    expect(find.text('맞춤 힐링 콘텐츠'), findsOneWidget);
    expect(find.text('음악'), findsOneWidget);
    expect(find.text('운동'), findsOneWidget);
    expect(find.text('문구'), findsOneWidget);
    expect(find.byKey(const ValueKey('content-card-c4')), findsNothing,
        reason: '먹을거리 카테고리는 홈의 세 가지 추천에 포함하지 않습니다');
  });
}
