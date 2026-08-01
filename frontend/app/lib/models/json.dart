/// 서버 응답을 안전하게 꺼내는 공용 헬퍼.
///
/// 모델마다 같은 캐스팅을 되풀이하다 보면 한 곳만 빠뜨려도 그 화면이
/// 통째로 죽습니다. 여기 모아두고 모델은 이것만 씁니다.
library;

/// 중첩 객체.
///
/// ⚠ `as Map<String, dynamic>` 로 바로 캐스팅하면 타입이 조금만 달라도
///   던집니다(`_Map<dynamic, dynamic>` 등). `jsonDecode` 는 항상
///   `Map<String, dynamic>` 을 주지만 그 가정에 기대면 다른 경로로 들어온
///   값에 깨집니다. 화면 하나 때문에 앱이 죽지 않게 합니다.
Map<String, dynamic> jsonObj(dynamic v) =>
    v is Map ? v.map((k, val) => MapEntry(k.toString(), val)) : const {};

/// 객체 배열.
List<Map<String, dynamic>> jsonList(dynamic v) =>
    v is List ? v.whereType<Map>().map(jsonObj).toList() : const [];

/// 숫자.
///
/// ⚠ 서버가 `NUMERIC` 컬럼을 **문자열로** 내려보냅니다(Decimal 직렬화).
///   실측: `hrv: '36.50'`, `emotion_score: '62.00'`.
///   `num` 으로만 캐스팅하면 조용히 null 이 되어 화면에 '–' 만 뜹니다.
double? jsonNum(dynamic v) => switch (v) {
      num n => n.toDouble(),
      String s => double.tryParse(s),
      _ => null,
    };

/// 정수. 값이 없으면 **0 이 아니라 null** 입니다.
/// "0걸음"과 "측정 안 됨"은 다릅니다.
int? jsonInt(dynamic v) => switch (v) {
      num n => n.toInt(),
      String s => int.tryParse(s),
      _ => null,
    };

/// 시각. 서버는 UTC 로 주므로 로컬로 바꿔 돌려줍니다.
DateTime? jsonAt(dynamic v) =>
    v is String ? DateTime.tryParse(v)?.toLocal() : null;

String jsonStr(dynamic v, [String fallback = '']) =>
    v is String ? v : fallback;

bool jsonBool(dynamic v, [bool fallback = false]) =>
    v is bool ? v : fallback;
