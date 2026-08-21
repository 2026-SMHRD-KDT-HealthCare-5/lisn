-- =====================================================================
--  관제 코호트 시드 — 관리자 관제 대시보드(MLCM_501 ❶❷) 시연용
--
--  왜 필요한가
--    2026.08.22 시연 준비 중 관리자 웹을 실제로 띄워보니 이렇게 나왔습니다.
--
--        전체 2명 중 1명 평가 완료 · 심각 대상자 100%
--
--    판정 이력이 있는 사용자가 `demo.crisis` **한 명뿐**이라,
--    「전체 대상자의 위험도 분포를 한눈에」라는 화면이 막대 하나가 됩니다.
--    분포·정렬·검색·필터가 전부 **대상자가 여럿일 때만** 의미가 있는데
--    데이터가 그걸 못 받쳐 줍니다. 시연에서 「이게 모니터링인가요」를
--    부르는 자리입니다.
--
--    이 시드는 **관제 화면을 보여주기 위한 코호트**를 만듭니다.
--
--  적용:
--    psql -U postgres -d lisn -f db/seed_demo_cohort.sql
--
--  되돌리기: 아래 「정리」 절의 DELETE 한 줄. 재실행해도 안전합니다.
--
--  ⚠ **`seed_demo_persona.sql` 과 함께 씁니다.** 그쪽은 **한 사람을 깊게**
--    (14일 라이프로그 + 악화 곡선) 만들어 홈·리포트·위기 이력을 채우고,
--    이쪽은 **여러 사람을 얕게** 만들어 분포·목록을 채웁니다. 역할이 다르니
--    둘 다 넣으세요. 서로 건드리지 않습니다(이메일 접두사가 다릅니다).
--
--  ---------------------------------------------------------------------
--  ⚠ 이건 만들어낸 데이터입니다. 절대 성능 근거로 쓰지 마세요.
--
--    `model_version = 'seed-demo-v0'` 로 박아 뒀습니다. 실제 판정
--    ('rule-baseline-v1')과 구분하기 위해서이고, 이 값이 보이면 사람이
--    손으로 넣은 값입니다. 화면 캡처를 발표자료에 쓸 때도 알고 쓰세요.
--
--  ⚠ 운영·공용 DB 에 넣지 마세요. 로컬 시연용입니다.
--     (CLAUDE.md — 「시드 스크립트를 공용 DB 에 넣지 마세요」)
--  ---------------------------------------------------------------------
--
--  이 시드가 만드는 것
--    USERS                9명 (role='USER')
--    EMOTION_RISK_SCORES  9명 × 최근 5일 = 45건
--    LIFELOG_METRICS      9명 × 최근 5일 = 45건
--
--  분포 설계 — 관제 화면이 「할 일이 있는 화면」으로 보이게
--    심각 2 · 주의 3 · 안정 3 · 미평가 1
--
--    미평가 1명을 일부러 남깁니다. 관리자 화면이 「미평가 N명은 아직
--    라이프로그가 쌓이지 않은 대상자입니다. 위험이 없다는 뜻이 아닙니다」
--    라고 안내하는데, 그 문구가 살아 있는 화면이어야 설명이 됩니다.
--
--  ⚠ 이름은 실존 인물과 무관한 조합입니다. 이메일 도메인 `.example` 은
--    RFC 2606 예약 도메인이라 실제로 존재할 수 없습니다.
-- =====================================================================

BEGIN;

-- ---------------------------------------------------------------------
--  정리 — 재실행 가능하게. ON DELETE CASCADE 로 하위 행이 같이 지워집니다.
-- ---------------------------------------------------------------------
DELETE FROM USERS WHERE email LIKE 'cohort.%@lisn-test.example';


-- ---------------------------------------------------------------------
--  1. 대상자 9명
--
--  ⚠ password_hash 는 `demo.crisis` 와 같은 값(bcrypt('rldnfdla'))입니다.
--    로그인해 볼 일은 없지만 NOT NULL 이라 채워야 하고, 새 해시를 지어내면
--    「이건 무슨 비밀번호냐」가 됩니다.
-- ---------------------------------------------------------------------
INSERT INTO USERS (
    email, password_hash, name, birth_date, gender, height_cm,
    persona_type, terms_agreed, terms_agreed_at,
    sensitive_agreed, sensitive_agreed_at, role
)
SELECT
    c.email,
    '$2b$12$yONlSdzTOeuS.SvDtp9yxeiKyiDUgxqvw1V/YLt88MhkEpZh7heki',
    c.name, c.birth, c.gender, c.height, c.persona,
    TRUE, now() - INTERVAL '40 days',
    TRUE, now() - INTERVAL '40 days',
    'USER'
FROM (VALUES
    ('cohort.01@lisn-test.example', '박서준', DATE '1994-03-02', 'MALE',   176.0, 'FRIEND'),
    ('cohort.02@lisn-test.example', '이하은', DATE '1998-11-25', 'FEMALE', 161.5, 'COUNSELOR'),
    ('cohort.03@lisn-test.example', '정민우', DATE '1991-07-14', 'MALE',   181.0, 'FRIEND'),
    ('cohort.04@lisn-test.example', '최유진', DATE '2000-01-09', 'FEMALE', 166.0, 'FRIEND'),
    ('cohort.05@lisn-test.example', '강도현', DATE '1988-09-30', 'MALE',   173.5, 'COUNSELOR'),
    ('cohort.06@lisn-test.example', '윤소미', DATE '1997-05-18', 'FEMALE', 159.0, 'FRIEND'),
    ('cohort.07@lisn-test.example', '임태호', DATE '1993-12-03', 'MALE',   178.0, 'FRIEND'),
    ('cohort.08@lisn-test.example', '한지우', DATE '1999-08-21', 'OTHER',  170.0, 'COUNSELOR'),
    -- ⚠ 09 는 **일부러 판정을 만들지 않습니다.** 아래 3절 참고.
    ('cohort.09@lisn-test.example', '오세영', DATE '1995-02-16', 'FEMALE', 163.0, 'FRIEND')
) AS c(email, name, birth, gender, height, persona);


-- ---------------------------------------------------------------------
--  2. 라이프로그 — 8명 × 최근 5일
--
--  판정과 **같은 방향**으로 움직이게 짰습니다. 관리자가 상세 리포트를 열면
--  감정 추이와 라이프로그가 함께 그려지는데, 둘이 어긋나면 화면 설명이
--  데이터로 반박됩니다(seed_demo_persona.sql 과 같은 이유).
--
--    심각군  수면 짧고 걸음 적음 · HRV 낮음
--    주의군  중간
--    안정군  수면 충분 · 활동 많음 · HRV 높음
-- ---------------------------------------------------------------------
INSERT INTO LIFELOG_METRICS (
    user_id, steps, distance, calories, total_active_min,
    total_sleep_min, deep_sleep_min, light_sleep_min, rem_sleep_min,
    awake_min, sleep_efficiency_pct, heart_rate, hrv, collected_at
)
-- sleep_min 은 VALUES 에 **분 단위 실값**으로 직접 둡니다. 파생 계산을
-- LATERAL 로 빼면 같은 SELECT 안에서 별칭을 못 봐서 오류가 납니다.
SELECT
    u.user_id,
    (p.steps + (d.n * 137) % 400)::int,
    ((p.steps + (d.n * 137) % 400) * 7 / 10)::int,
    ((p.steps + (d.n * 137) % 400) / 22)::int,
    p.active_min,
    (p.sleep_min + (d.n * 23) % 40)::int,
    (p.sleep_min * 22 / 100)::int,
    (p.sleep_min * 55 / 100)::int,
    (p.sleep_min * 18 / 100)::int,
    p.awake_min,
    p.efficiency,
    p.hr,
    p.hrv,
    date_trunc('day', now()) - make_interval(days => d.n) + INTERVAL '9 hours'
FROM USERS u
JOIN (VALUES
    -- email, 걸음, 활동분, 수면분, 각성분, 수면효율, 심박, HRV
    ('cohort.01@lisn-test.example', 2100,  35, 205, 44, 71.0, 88, 24.0),
    ('cohort.02@lisn-test.example', 2600,  41, 230, 38, 74.5, 85, 26.5),
    ('cohort.03@lisn-test.example', 5200,  72, 355, 26, 84.0, 74, 39.0),
    ('cohort.04@lisn-test.example', 4800,  68, 340, 29, 82.5, 76, 37.5),
    ('cohort.05@lisn-test.example', 5600,  77, 362, 24, 85.5, 72, 41.0),
    ('cohort.06@lisn-test.example', 8600, 121, 452, 17, 91.5, 63, 54.0),
    ('cohort.07@lisn-test.example', 9200, 128, 468, 15, 92.5, 61, 57.5),
    ('cohort.08@lisn-test.example', 7900, 112, 430, 19, 90.0, 65, 51.0)
) AS p(email, steps, active_min, sleep_min, awake_min, efficiency, hr, hrv)
  ON u.email = p.email
CROSS JOIN generate_series(0, 4) AS d(n);


-- ---------------------------------------------------------------------
--  3. 감정 위험도 판정 — 8명 × 최근 5일
--
--  ⚠ **관제 대시보드는 「사용자별 최신 1건」만 셉니다**(admin.py
--    `_latest_score_subq`). 그래서 분포를 정하는 것은 각 사람의 **D-0 행**
--    입니다. 앞날짜는 상세 리포트의 추이선을 위해 넣습니다.
--
--  ⚠ **cohort.09(오세영)에는 판정을 넣지 않습니다.** 관리자 화면의
--    「미평가 N명은 아직 라이프로그가 쌓이지 않은 대상자입니다. 위험이
--    없다는 뜻이 아니므로 함께 확인하세요」 안내가 살아 있어야, 그 문구를
--    시연에서 설명할 수 있습니다. 데이터를 다 채우면 그 배려가 안 보입니다.
--
--  최신(D-0) 기준 분포 —  심각 2 · 주의 3 · 안정 3
-- ---------------------------------------------------------------------
INSERT INTO EMOTION_RISK_SCORES (
    user_id, emotion_id, emotion_score, risk_level, risk_score,
    model_version, evaluated_at
)
SELECT
    u.user_id,
    e.emotion_id,
    -- 오래된 날일수록 완만하게: D-0 이 가장 뚜렷합니다.
    GREATEST(0, LEAST(100, p.score - d.n * 4))::numeric(5,2),
    CASE
        WHEN d.n = 0 THEN p.level
        -- 앞날짜는 한 단계 낮춰 「점점 나빠지는 흐름」으로 보이게 합니다.
        WHEN p.level = 'CRITICAL' AND d.n <= 2 THEN 'CAUTION'
        WHEN p.level = 'CRITICAL' THEN 'NORMAL'
        WHEN p.level = 'CAUTION'  AND d.n <= 2 THEN 'CAUTION'
        ELSE 'NORMAL'
    END,
    GREATEST(0, LEAST(100, p.score - d.n * 4))::numeric(5,2),
    'seed-demo-v0',
    date_trunc('day', now()) - make_interval(days => d.n) + INTERVAL '9 hours 30 minutes'
FROM USERS u
JOIN (VALUES
    -- 심각 2
    ('cohort.01@lisn-test.example', 'SADNESS',  92.0, 'CRITICAL'),
    ('cohort.02@lisn-test.example', 'ANXIETY',  88.0, 'CRITICAL'),
    -- 주의 3
    ('cohort.03@lisn-test.example', 'ANXIETY',  63.0, 'CAUTION'),
    ('cohort.04@lisn-test.example', 'SADNESS',  58.0, 'CAUTION'),
    ('cohort.05@lisn-test.example', 'ANGER',    66.0, 'CAUTION'),
    -- 안정 3
    ('cohort.06@lisn-test.example', 'HAPPINESS', 24.0, 'NORMAL'),
    ('cohort.07@lisn-test.example', 'HAPPINESS', 19.0, 'NORMAL'),
    ('cohort.08@lisn-test.example', 'HAPPINESS', 27.0, 'NORMAL')
) AS p(email, emotion_code, score, level)
  ON u.email = p.email
JOIN EMOTIONS e ON e.emotion_code = p.emotion_code
CROSS JOIN generate_series(0, 4) AS d(n);

COMMIT;


-- =====================================================================
--  확인 — 관제 대시보드가 보게 될 분포
-- =====================================================================
SELECT
    s.risk_level,
    COUNT(*) AS 인원
FROM EMOTION_RISK_SCORES s
JOIN (
    SELECT user_id, MAX(evaluated_at) AS latest
    FROM EMOTION_RISK_SCORES GROUP BY user_id
) m ON m.user_id = s.user_id AND m.latest = s.evaluated_at
GROUP BY s.risk_level
ORDER BY s.risk_level;
