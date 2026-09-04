-- =====================================================================
--  데모 페르소나 시각 갱신 — 심사 기간 내내 화면이 살아 있게 합니다
--
--  왜 필요한가
--    seed_demo_persona.sql 은 collected_at 을 now() 기준 상대값으로 넣습니다.
--    그래서 자정을 넘기면 가장 최근 기록이 「어제」가 되고, 홈 화면은 오늘
--    라이프로그를 읽으므로 수면·걸음·HRV 가 전부 「-」로 나옵니다.
--    평가원은 본인 일정대로 들어오니, 시드를 넣은 날에만 보이면 곤란합니다.
--
--  무엇을 하는가
--    데모 계정의 기록 전체를 **같은 간격만큼 통째로 앞으로 밉니다.**
--    가장 최근 기록이 항상 「지금」이 됩니다. 30일치 곡선의 모양과
--    기록 사이의 간격은 그대로 보존됩니다.
--
--  왜 시드를 다시 돌리지 않는가
--    시드는 계정을 지우고 다시 넣어 **user_id 가 바뀝니다.** 그러면 앱에
--    로그인해 둔 세션이 끊기고, 평가원이 쓰는 도중에 튕깁니다.
--    이 스크립트는 행을 지우지 않으므로 세션이 유지됩니다.
--
--  적용:
--    docker compose exec -T postgres psql -U postgres -d lisn < db/refresh_demo_persona.sql
--
--  성질
--    - 여러 번 돌려도 안전합니다. 돌릴 때마다 「지금」에 다시 맞춥니다
--    - 며칠 걸러 돌려도 한 번에 따라잡습니다. 밀린 날짜를 세지 않고
--      **현재 시각과의 차이**를 재서 그만큼 밀기 때문입니다
--    - 계정이나 라이프로그가 없으면 아무것도 바꾸지 않고 알려줍니다
--
--  ⚠ 데모 계정 한 명만 건드립니다. 아래 이메일을 바꾸지 마세요 —
--    실제 사용자의 기록을 밀면 판정 근거가 통째로 어긋납니다.
-- =====================================================================

DO $$
DECLARE
    uid UUID;
    gap INTERVAL;
    n_life INT;
    n_risk INT;
BEGIN
    SELECT user_id INTO uid
      FROM users
     WHERE email = 'demo.crisis@lisn-test.example';

    IF uid IS NULL THEN
        RAISE NOTICE '건너뜀 — 데모 계정이 없습니다. seed_demo_persona.sql 을 먼저 넣으세요.';
        RETURN;
    END IF;

    -- 홈 화면이 읽는 것이 라이프로그이므로 기준을 여기서 잡습니다.
    SELECT now() - max(collected_at) INTO gap
      FROM lifelog_metrics
     WHERE user_id = uid;

    IF gap IS NULL THEN
        RAISE NOTICE '건너뜀 — 데모 계정에 라이프로그가 없습니다.';
        RETURN;
    END IF;

    -- ⚠ 두 번에 나눠 미는 이유 — UNIQUE (user_id, collected_at) 때문입니다.
    --   한 번에 밀면 아직 안 옮겨진 행의 자리로 먼저 옮겨진 행이 들어가
    --   문장 도중에 제약이 깨집니다(PostgreSQL 은 비지연 제약을 행마다
    --   즉시 검사합니다). 먼저 아무도 없는 먼 미래로 통째로 치우고,
    --   거기서 목표 시각으로 되돌리면 부딪칠 행이 없습니다.
    --   같은 간격으로 밀므로 행끼리 겹치는 일도 없습니다.
    UPDATE lifelog_metrics
       SET collected_at = collected_at + INTERVAL '1000 years'
     WHERE user_id = uid;

    UPDATE lifelog_metrics
       SET collected_at = collected_at - INTERVAL '1000 years' + gap
     WHERE user_id = uid;
    GET DIAGNOSTICS n_life = ROW_COUNT;

    -- 위기 점수도 **같은 간격**으로 밉니다. 따로 밀면 라이프로그와
    -- 판정 시각이 어긋나 관제 화면의 근거가 맞지 않습니다.
    -- 이쪽은 유니크 제약이 없어 한 번에 밀어도 됩니다.
    UPDATE emotion_risk_scores
       SET evaluated_at = evaluated_at + gap
     WHERE user_id = uid;
    GET DIAGNOSTICS n_risk = ROW_COUNT;

    RAISE NOTICE '% 만큼 밀었습니다 — 라이프로그 %행 · 위기점수 %행', gap, n_life, n_risk;
END $$;

-- 확인용. 「최근 기록」이 0에 가까우면 성공입니다.
SELECT u.email,
       u.role,
       max(l.collected_at)          AS "최근기록",
       now() - max(l.collected_at)  AS "지금과의차이",
       count(*)                     AS "라이프로그행수"
  FROM users u
  JOIN lifelog_metrics l ON l.user_id = u.user_id
 WHERE u.email = 'demo.crisis@lisn-test.example'
 GROUP BY u.email, u.role;
