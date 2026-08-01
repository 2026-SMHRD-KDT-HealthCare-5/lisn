-- =====================================================================
--  개발 DB 테스트 계정 정리
--
--  왜 필요한가
--    회귀 테스트는 계정을 만들고 끝나면 지웁니다(`DELETE /users/me`). 그런데
--    테스트가 중간에 실패하면 정리 단계까지 못 가서 계정이 남습니다. 쌓이면
--    관제 대시보드의 「전체 N명」과 위험도 분포가 실제보다 희석돼 보입니다.
--    실측: 35명 중 4명만 평가됨 — 나머지는 대부분 고아 계정이었습니다.
--
--  적용:
--    psql -U postgres -d lisn -f db/cleanup_test_accounts.sql
--
--  ⚠ 개발 DB 전용입니다. 운영 DB 에서 돌리지 마세요.
-- =====================================================================


-- ---------------------------------------------------------------------
--  지우기 전에 무엇이 지워지는지 봅니다. 이 SELECT 를 먼저 돌리세요.
-- ---------------------------------------------------------------------
--
--   SELECT email, name FROM USERS u
--    WHERE u.role = 'USER'
--      AND (u.email LIKE '%@lisn-test.example' OR u.email LIKE '%@lisn.dev')
--      AND u.email NOT LIKE 'demo.%'
--      AND u.email NOT IN ('test@lisn.dev', 'user@lisn.dev')
--      AND NOT EXISTS (SELECT 1 FROM EMOTION_RISK_SCORES s WHERE s.user_id = u.user_id)
--      AND NOT EXISTS (SELECT 1 FROM LIFELOG_METRICS l WHERE l.user_id = u.user_id)
--      AND NOT EXISTS (SELECT 1 FROM BODY_COMPOSITION_METRICS b WHERE b.user_id = u.user_id)
--      AND NOT EXISTS (SELECT 1 FROM CHAT_SESSIONS c WHERE c.user_id = u.user_id)
--      AND NOT EXISTS (SELECT 1 FROM DEVICE_HEALTH_CONNECTIONS d WHERE d.user_id = u.user_id);


BEGIN;

DELETE FROM USERS u
 WHERE
   -- 관리자는 건드리지 않습니다. 지우면 관제 화면에 못 들어갑니다.
   u.role = 'USER'

   -- 테스트가 쓰는 두 도메인만. `.example` 은 RFC 2606 예약이라 실사용자가
   -- 있을 수 없고, `@lisn.dev` 는 초기 수동 검증에 쓰던 것입니다.
   AND (u.email LIKE '%@lisn-test.example' OR u.email LIKE '%@lisn.dev')

   -- 데모 페르소나는 남깁니다. 관제 화면 확인용으로 일부러 넣은 것입니다.
   AND u.email NOT LIKE 'demo.%'

   -- 손으로 만든 것으로 보이는 개발용 로그인. 팀원이 쓰고 있을 수 있어
   -- 자동 정리 대상에서 뺍니다. 지우려면 이 줄을 지우세요.
   AND u.email NOT IN ('test@lisn.dev', 'user@lisn.dev')

   -- ⚠ **데이터가 하나라도 붙어 있으면 남깁니다.** 누군가 수동으로 만들어
   --   확인 중인 계정일 수 있고, ON DELETE CASCADE 라 같이 사라집니다.
   AND NOT EXISTS (SELECT 1 FROM EMOTION_RISK_SCORES s WHERE s.user_id = u.user_id)
   AND NOT EXISTS (SELECT 1 FROM LIFELOG_METRICS l WHERE l.user_id = u.user_id)
   AND NOT EXISTS (SELECT 1 FROM BODY_COMPOSITION_METRICS b WHERE b.user_id = u.user_id)
   AND NOT EXISTS (SELECT 1 FROM CHAT_SESSIONS c WHERE c.user_id = u.user_id)
   AND NOT EXISTS (SELECT 1 FROM DEVICE_HEALTH_CONNECTIONS d WHERE d.user_id = u.user_id);

COMMIT;


-- =====================================================================
--  확인
-- =====================================================================
--   SELECT role, count(*) FROM USERS GROUP BY role;
--
--  관제 대시보드의 「전체 N명」이 줄었는지 새로고침해서 보세요.
--  ⚠ role 은 DB 를 보므로 재로그인 없이 반영됩니다. 다만 화면 데이터는
--    캐시하지 않으니 탭을 다시 눌러야 새로 조회합니다.
