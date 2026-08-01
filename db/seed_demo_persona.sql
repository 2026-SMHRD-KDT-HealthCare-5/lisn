-- =====================================================================
--  데모 페르소나 시드 — 위기 사건 이력(MLCM_501 ❹ · MLCM_510)용 테스트 데이터
--
--  왜 필요한가
--    관리자 관제 웹의 「위기 사건 이력」은 EMOTION_RISK_SCORES 에서
--    risk_level='CRITICAL' 인 행을 읽습니다. 실제 라이프로그를 14일 쌓지 않으면
--    이 화면이 영영 비어 있어 개발·시연 중에 확인할 수가 없습니다.
--
--  적용:
--    psql -U postgres -d lisn -f db/seed_demo_persona.sql
--
--  되돌리기:  아래 「정리」 절의 DELETE 한 줄. 재실행해도 안전합니다
--             (같은 계정을 먼저 지우고 다시 넣습니다).
--
--  ---------------------------------------------------------------------
--  ⚠ 이건 만들어낸 데이터입니다. 절대 성능 근거로 쓰지 마세요.
--
--    model_version 을 'seed-demo-v0' 로 박아 뒀습니다. 실제 판정 결과
--    ('rule-placeholder-v0' 또는 이후의 모델 버전)와 **구분되도록** 하기
--    위해서입니다. 이 값이 보이면 사람이 손으로 넣은 값입니다.
--
--    화면 캡처를 발표자료에 쓸 때도 이 점을 알고 쓰세요.
--
--  ⚠ 운영 DB 에 넣지 마세요. 개발·시연용입니다.
--  ---------------------------------------------------------------------
--
--  이 시드가 만드는 것
--    USERS               1명  (role='USER' 이어야 대상자 목록에 뜹니다)
--    LIFELOG_METRICS    14일  (리포트 ❹ 결합 차트 · AI 서버 재판정용)
--    EMOTION_RISK_SCORES 14건 (안정 6 → 주의 4 → 심각 4)
--
--  CHAT_SESSIONS 는 만들지 않습니다. 관리자 화면 어디에서도 읽지 않고,
--  위기 대화문을 굳이 지어낼 이유가 없습니다.
-- =====================================================================

BEGIN;

-- ---------------------------------------------------------------------
--  정리 — 재실행 가능하게. ON DELETE CASCADE 로 하위 행이 같이 지워집니다.
-- ---------------------------------------------------------------------
DELETE FROM USERS WHERE email = 'demo.crisis@lisn-test.example';


-- ---------------------------------------------------------------------
--  1. 페르소나
--
--  ⚠ phone 은 NULL 입니다. 04 문서(02-F 3항)가 AES-256-GCM 을 요구하는데
--    SQL 로는 암호문을 만들 수 없습니다. 연락처가 필요하면 앱/API 로 넣으세요.
--
--  이메일 도메인이 `.example` 인 것은 의도한 것입니다. RFC 2606 예약 도메인이라
--  실제로 존재할 수 없어, 실사용자와 혼동되지 않습니다.
-- ---------------------------------------------------------------------
INSERT INTO USERS (
    email, password_hash, name, birth_date, gender, height_cm,
    persona_type, terms_agreed, terms_agreed_at,
    sensitive_agreed, sensitive_agreed_at, role
) VALUES (
    'demo.crisis@lisn-test.example',
    -- bcrypt('rldnfdla') — 팀 공용 테스트 비밀번호
    '$2b$12$yONlSdzTOeuS.SvDtp9yxeiKyiDUgxqvw1V/YLt88MhkEpZh7heki',
    '데모 김하늘',
    '1996-04-11',
    'FEMALE',
    164.0,
    'COUNSELOR',          -- 위기 상황이라 상담사 페르소나
    TRUE, now() - INTERVAL '30 days',
    TRUE, now() - INTERVAL '30 days',
    'USER'
);


-- ---------------------------------------------------------------------
--  2. 라이프로그 14일
--
--  이 서비스의 전제는 "행동·생체 패턴의 변화가 정서 위험에 선행한다" 입니다.
--  그래서 값을 무작위로 넣지 않고 **악화 곡선**으로 짰습니다.
--
--    D-13 ~ D-8   수면 ~420분 · 걸음 ~7000   평소
--    D-7  ~ D-4   수면 감소   · 걸음 감소     흔들리기 시작
--    D-3  ~ D-0   수면 ~180분 · 걸음 ~400     고립
--
--  아래 3절의 감정 판정과 같은 방향으로 움직입니다. 둘이 어긋나면
--  "라이프로그로 정서를 읽는다"는 화면 설명이 데이터로 반박됩니다.
--
--  ⚠ collected_at 은 now() 기준 상대값입니다. 리포트 기본 조회 구간이
--    최근 30일이라, 고정 날짜로 박으면 나중에 창 밖으로 밀려납니다.
-- ---------------------------------------------------------------------
INSERT INTO LIFELOG_METRICS (
    user_id, steps, distance, calories, total_active_min,
    total_sleep_min, deep_sleep_min, light_sleep_min, rem_sleep_min,
    awake_min, sleep_efficiency_pct, heart_rate, hrv, collected_at
)
SELECT
    u.user_id,
    d.steps, d.distance, d.calories, d.active_min,
    d.sleep_min, d.deep_min, d.light_min, d.rem_min,
    d.awake_min, d.efficiency, d.hr, d.hrv,
    date_trunc('day', now()) - make_interval(days => d.days_ago) + INTERVAL '9 hours'
FROM USERS u
CROSS JOIN (VALUES
    --      d전,걸음,거리,칼로리,활동,수면,깊은,얕은,렘,깸,효율,심박,HRV
    (13,  7420, 5100, 2180, 68, 421, 92, 236,  78, 15, 93.5, 66, 48.2),
    (12,  6980, 4820, 2050, 61, 408, 88, 229,  75, 16, 92.8, 67, 47.1),
    (11,  7810, 5390, 2240, 74, 433, 95, 244,  80, 14, 94.1, 65, 49.6),
    (10,  7140, 4930, 2110, 65, 415, 90, 232,  77, 16, 93.0, 66, 47.8),
    ( 9,  6650, 4590, 1980, 58, 396, 84, 222,  73, 17, 91.9, 68, 45.3),
    ( 8,  7020, 4840, 2070, 63, 402, 86, 226,  74, 16, 92.4, 67, 46.5),
    -- 여기서부터 흔들립니다
    ( 7,  4880, 3370, 1620, 41, 351, 71, 200,  63, 17, 88.7, 71, 40.9),
    ( 6,  3960, 2730, 1450, 33, 322, 62, 186,  57, 17, 86.5, 73, 38.2),
    ( 5,  3210, 2210, 1310, 27, 298, 55, 174,  52, 17, 84.9, 75, 35.6),
    ( 4,  2470, 1700, 1180, 21, 271, 47, 160,  47, 17, 82.3, 78, 32.8),
    -- 고립
    ( 3,  1180,  810,  990, 11, 224, 34, 136,  38, 16, 77.5, 82, 28.4),
    ( 2,   740,  510,  920,  7, 196, 27, 121,  33, 15, 74.1, 85, 25.9),
    ( 1,   460,  320,  880,  4, 178, 22, 111,  29, 16, 71.6, 88, 23.7),
    ( 0,   390,  270,  860,  3, 171, 20, 107,  28, 16, 70.4, 89, 22.8)
) AS d(days_ago, steps, distance, calories, active_min,
       sleep_min, deep_min, light_min, rem_min, awake_min, efficiency, hr, hrv)
WHERE u.email = 'demo.crisis@lisn-test.example';


-- ---------------------------------------------------------------------
--  3. 정서 위험도 판정 14건
--
--  ⚠ emotion_id 를 UUID 로 직접 쓰지 마세요. gen_random_uuid() 로 만들어져
--    환경마다 다릅니다. emotion_code 로 조회해서 넣습니다.
--
--  ⚠ risk_level 은 ai/server/main.py 의 risk_level_of() 정책과 **일치해야**
--    합니다(04 문서 6항). 어긋난 데이터를 넣으면 나중에 규칙을 의심하게 됩니다.
--        JOY·DELIGHT·HAPPINESS        -> NORMAL
--        SADNESS·ANXIETY·LONELINESS   -> CAUTION
--        ANGER                        -> CAUTION (단 emotion_score >= 70 이면 CRITICAL)
--        DESPAIR·CRISIS               -> CRITICAL
--
--  CRITICAL 4건이 「위기 사건 이력」에 뜹니다.
-- ---------------------------------------------------------------------
INSERT INTO EMOTION_RISK_SCORES (
    user_id, emotion_id, emotion_score, risk_level, risk_score,
    model_version, evaluated_at
)
SELECT
    u.user_id, e.emotion_id, d.emotion_score, d.risk_level, d.risk_score,
    'seed-demo-v0',
    date_trunc('day', now()) - make_interval(days => d.days_ago) + INTERVAL '10 hours'
FROM USERS u
CROSS JOIN (VALUES
    --      d전, 감정코드,      감정점수, 위험단계,   위험점수
    (13, 'HAPPINESS',  71.20, 'NORMAL',   12.40),
    (12, 'JOY',        68.50, 'NORMAL',   15.10),
    (11, 'HAPPINESS',  74.90, 'NORMAL',    9.80),
    (10, 'DELIGHT',    66.30, 'NORMAL',   17.60),
    ( 9, 'HAPPINESS',  61.70, 'NORMAL',   22.30),
    ( 8, 'JOY',        59.40, 'NORMAL',   24.90),
    ( 7, 'ANXIETY',    48.60, 'CAUTION',  41.20),
    ( 6, 'ANXIETY',    55.10, 'CAUTION',  48.70),
    ( 5, 'SADNESS',    62.80, 'CAUTION',  56.30),
    ( 4, 'LONELINESS', 69.40, 'CAUTION',  63.90),
    ( 3, 'DESPAIR',    78.20, 'CRITICAL', 74.60),
    ( 2, 'DESPAIR',    84.70, 'CRITICAL', 81.30),
    ( 1, 'CRISIS',     91.50, 'CRITICAL', 89.80),
    ( 0, 'CRISIS',     93.80, 'CRITICAL', 92.40)
) AS d(days_ago, emotion_code, emotion_score, risk_level, risk_score)
JOIN EMOTIONS e ON e.emotion_code = d.emotion_code
WHERE u.email = 'demo.crisis@lisn-test.example';

COMMIT;


-- =====================================================================
--  확인
-- =====================================================================
--   SELECT name, emotion_code, risk_level, evaluated_at
--     FROM EMOTION_RISK_SCORES s
--     JOIN USERS u USING (user_id)
--     JOIN EMOTIONS e USING (emotion_id)
--    WHERE s.model_version = 'seed-demo-v0' AND s.risk_level = 'CRITICAL'
--    ORDER BY evaluated_at DESC;
--
--  API 로 보려면 관리자 계정으로 로그인한 뒤
--   GET /api/v1/admin/emergency-events
--   GET /api/v1/admin/users?risk_level=CRITICAL
--
--  ⚠ role 은 JWT 에 박힙니다. UPDATE users SET role='ADMIN' 만 하고 기존
--    토큰을 쓰면 계속 403 입니다. 승격 후 재로그인하세요.
--
-- =====================================================================
--  정리 — 시드를 지울 때
-- =====================================================================
--   DELETE FROM USERS WHERE email = 'demo.crisis@lisn-test.example';
--
--  손으로 넣은 판정만 골라 지우려면 (계정은 남기고):
--   DELETE FROM EMOTION_RISK_SCORES WHERE model_version = 'seed-demo-v0';
