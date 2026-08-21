-- =====================================================================
--  데모 데이터 날짜 밀기 — 시연·촬영 직전에 돌립니다
--
--  왜 필요한가
--    `seed_demo_persona.sql` · `seed_demo_cohort.sql` 은 collected_at 을
--    now() 기준 상대값으로 넣습니다. 그래서 **자정을 넘기면** 가장 최근
--    기록이 「어제」가 되고, 홈 화면의 수면·걸음·HRV 가 전부 「-」로 나옵니다.
--    화면이 깨진 게 아니라 오늘 데이터가 없는 것인데, 원인을 찾는 데
--    시간이 걸립니다.
--
--  ⚠ **그럼 시드를 다시 돌리면 되지 않나 — 안 됩니다.**
--    두 시드 모두 `DELETE FROM USERS` 로 시작합니다. 다시 넣으면 user_id 가
--    새로 발급되면서 아래가 **전부 같이 사라집니다.**
--
--      · FCM 토큰       → 앱을 다시 띄워 재등록해야 푸시 시연이 됩니다
--      · 선제 접촉 세션 → 홈의 「마음이가 먼저 말을 걸었어요」 카드가 사라집니다.
--                         쿨다운(3일) 때문에 그 자리에서 다시 만들 수도 없습니다
--      · 앱 로그인 세션 → user_id 가 바뀌어 끊깁니다
--
--    촬영 직전에 이걸 날리면 복구에 시간이 걸립니다. 그래서 **지우지 않고
--    날짜만 미는** 경로를 따로 뒀습니다.
--
--  무엇을 하는가
--    demo.* · cohort.* 계정의 **가장 최근 기록이 「지금」에 가장 가까워지도록**
--    그 계정의 모든 라이프로그·판정·체성분 시각을 같은 일수만큼 통째로 밉니다.
--    계정별로 따로 계산하므로 시드를 서로 다른 날 넣었어도 각자 맞춰집니다.
--
--    ⚠ 「오늘 날짜」가 아니라 **「지금을 넘지 않는 가장 가까운 시각」**입니다.
--      이유는 아래 1절 주석에 있습니다 — 미래 데이터가 시연을 망칩니다.
--
--  ⚠ **간격은 보존됩니다.** 계정 안에서 전부 같은 일수를 더하기 때문에
--    14일 악화 곡선의 모양과 라이프로그↔판정의 짝이 그대로 유지됩니다.
--    날짜별로 다르게 밀면 곡선이 뭉개지고 리포트의 두 차트가 어긋납니다.
--
--  적용:
--    psql -U postgres -d lisn -f db/refresh_demo_dates.sql
--
--  여러 번 돌려도 안전합니다. 이미 오늘이면 밀 일수가 0 이라 아무것도 안 합니다.
--
--  ⚠ 개발 DB 전용입니다. 운영·공용 DB 에서 돌리지 마세요.
-- =====================================================================

BEGIN;

-- ---------------------------------------------------------------------
--  1. 계정별로 며칠을 밀지 계산
--
--  기준은 「그 계정의 가장 최근 기록」입니다. 라이프로그와 판정 중 더 나중
--  것을 봅니다 — cohort.09 처럼 판정이 없는 계정도 있고, 반대의 경우도
--  있을 수 있어서입니다.
--
--  ⚠ 날짜 비교는 **Asia/Seoul 로 변환한 뒤** 합니다. timestamptz 를 그냥
--    ::date 로 자르면 DB 세션 타임존을 따라가, UTC 세션에서는 한국 시각
--    오전 9시 이전 기록이 「어제」로 계산됩니다.
-- ---------------------------------------------------------------------
CREATE TEMP TABLE demo_shift ON COMMIT DROP AS
WITH targets AS (
    SELECT user_id
      FROM USERS
     WHERE email LIKE 'demo.%'
        OR email LIKE 'cohort.%'
),
newest AS (
    SELECT t.user_id,
           GREATEST(
               COALESCE((SELECT max(l.collected_at) FROM LIFELOG_METRICS l
                          WHERE l.user_id = t.user_id), '-infinity'::timestamptz),
               COALESCE((SELECT max(s.evaluated_at) FROM EMOTION_RISK_SCORES s
                          WHERE s.user_id = t.user_id), '-infinity'::timestamptz)
           ) AS newest_at
      FROM targets t
)
--  ⚠ **미래로 밀지 않습니다.** 「오늘 날짜로 맞추기」를 날짜 뺄셈으로 하면,
--    시드의 시각(오전 10시)보다 이른 시각에 돌릴 때 데이터가 **몇 시간
--    앞선 미래**에 놓입니다. 그러면 시연 중 실제로 발생한 위기가 만들어낸
--    데이터보다 **아래로 밀려** 관제 목록에서 안 보입니다(2026.08.22 실측).
--
--    그래서 경과 시간을 **일 단위로 내림**합니다. 시각(오전 10시 등)은
--    그대로 보존되면서 — 수면 구간이 한밤중에 남아야 차트가 말이 됩니다 —
--    가장 최근 기록이 지금을 넘지 않습니다.
SELECT user_id,
       FLOOR(EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - newest_at)) / 86400)::int AS days
  FROM newest
 -- 기록이 하나도 없는 계정은 밀 것이 없습니다.
 WHERE newest_at <> '-infinity'::timestamptz;

-- 뒤로 미는 일은 하지 않습니다. 이미 오늘이거나(0) 미래에 있는 데이터(<0)는
-- 사람이 일부러 넣었을 수 있으니 건드리지 않습니다.
DELETE FROM demo_shift WHERE days <= 0;


-- ---------------------------------------------------------------------
--  2. 라이프로그 — 시각 컬럼 5개를 모두 같이 밉니다
--
--  ⚠ collected_at 만 밀면 안 됩니다. 수면 구간(sleep_start_at/end_at)이
--    옛 날짜에 남아 리포트의 수면 차트가 어제 자리에 그려집니다.
--
--  ⚠ **한 번에 밀면 고유 제약에 걸립니다.** `uq_lifelog_user_collected`
--    가 (user_id, collected_at) 에 걸려 있고 DEFERRABLE 이 아닙니다.
--    +1일을 밀면 8/08 행이 8/09 로 가는데, **아직 안 밀린 기존 8/09 행이
--    그 자리에 있어** 그 순간 충돌합니다. UPDATE 는 행 단위로 즉시
--    검사하고 처리 순서를 보장하지 않으니 "큰 날짜부터"로도 못 피합니다.
--
--    그래서 **멀리 보냈다가 되돌립니다.** 먼저 그 계정 행 전체를 아무도
--    없는 미래(+10000일)로 옮기면, 원래 자리가 통째로 비어 두 번째
--    UPDATE 가 목표 날짜로 안전하게 내려옵니다. 트랜잭션 안이라 중간
--    상태는 밖에서 보이지 않습니다.
-- ---------------------------------------------------------------------
UPDATE LIFELOG_METRICS l
   SET collected_at      = l.collected_at      + make_interval(days => d.days + 10000),
       activity_start_at = l.activity_start_at + make_interval(days => d.days + 10000),
       activity_end_at   = l.activity_end_at   + make_interval(days => d.days + 10000),
       sleep_start_at    = l.sleep_start_at    + make_interval(days => d.days + 10000),
       sleep_end_at      = l.sleep_end_at      + make_interval(days => d.days + 10000)
  FROM demo_shift d
 WHERE d.user_id = l.user_id;

UPDATE LIFELOG_METRICS l
   SET collected_at      = l.collected_at      - make_interval(days => 10000),
       activity_start_at = l.activity_start_at - make_interval(days => 10000),
       activity_end_at   = l.activity_end_at   - make_interval(days => 10000),
       sleep_start_at    = l.sleep_start_at    - make_interval(days => 10000),
       sleep_end_at      = l.sleep_end_at      - make_interval(days => 10000)
  FROM demo_shift d
 WHERE d.user_id = l.user_id;


-- ---------------------------------------------------------------------
--  3. 정서 위험도 판정
-- ---------------------------------------------------------------------
UPDATE EMOTION_RISK_SCORES s
   SET evaluated_at = s.evaluated_at + make_interval(days => d.days)
  FROM demo_shift d
 WHERE d.user_id = s.user_id;


-- ---------------------------------------------------------------------
--  4. 체성분 — 시드에 없을 수도 있지만, 손으로 넣어 뒀다면 같이 밀어야
--     리포트에서 라이프로그와 어긋나지 않습니다.
-- ---------------------------------------------------------------------
UPDATE BODY_COMPOSITION_METRICS b
   SET measured_at = b.measured_at + make_interval(days => d.days)
  FROM demo_shift d
 WHERE d.user_id = b.user_id;


-- ---------------------------------------------------------------------
--  5. 무엇을 밀었는지 보고
-- ---------------------------------------------------------------------
SELECT u.email, d.days AS shifted_days
  FROM demo_shift d
  JOIN USERS u ON u.user_id = d.user_id
 ORDER BY u.email;

COMMIT;


-- =====================================================================
--  확인 — 촬영 전 이 값이 오늘인지 보세요
-- =====================================================================
--   SELECT u.email, max(l.collected_at) AT TIME ZONE 'Asia/Seoul' AS newest
--     FROM USERS u JOIN LIFELOG_METRICS l ON l.user_id = u.user_id
--    WHERE u.email LIKE 'demo.%' OR u.email LIKE 'cohort.%'
--    GROUP BY u.email ORDER BY u.email;
--
--  ⚠ 앱은 홈 데이터를 캐시하지 않지만, **이미 떠 있는 화면은 다시 그리지
--    않습니다.** 당겨서 새로고침하거나 탭을 다시 누르세요.
