-- =====================================================================
--  귀기울임 (LISN) — 데이터베이스 스키마
--  과제명 : 멀티모달 라이프로그 감정 분석 기반 맞춤형 LLM 케어 및 모니터링 시스템
--
--  출처   : Documents/05_테이블명세서_귀기울임.hwp (2026.07.23 / 작성자 이응균)
--  대상   : PostgreSQL 13 이상
--
--  ※ 이 파일은 05 테이블명세서 원문을 baseline 으로 하되,
--    2026.07.29 팀 회의에서 확정된 개정안 [05-A] [05-B] [05-C] 를 반영한 상태입니다.
--    ⚠ 05 테이블명세서(HWP) 원문은 아직 미반영입니다. 문서 개정 시 이 파일을 기준으로 맞추세요.
--    개정 내역: docs/review/문서개정_체크리스트.md
--    회의 결정: docs/review/회의안건_20260729.md
-- =====================================================================


-- ---------------------------------------------------------------------
--  실행 전 확인 사항
-- ---------------------------------------------------------------------
--  1. gen_random_uuid()
--     PostgreSQL 13+ 에서는 기본 내장 함수입니다.
--     12 이하를 쓴다면 아래 확장을 먼저 설치해야 합니다.
--         CREATE EXTENSION IF NOT EXISTS pgcrypto;
--
--  2. 테이블명 대소문자
--     문서에는 USERS / LIFELOG_METRICS 처럼 대문자로 표기되어 있으나,
--     PostgreSQL 은 따옴표 없는 식별자를 소문자로 접습니다.
--     실제 생성되는 테이블명은 users, lifelog_metrics 입니다. (정상 동작)
--
--  3. 실행 순서
--     FK 의존성 때문에 USERS -> EMOTIONS -> 나머지 순서를 지켜야 합니다.
--     이 파일은 이미 그 순서로 정렬되어 있습니다.
-- ---------------------------------------------------------------------


-- =====================================================================
--  1. USERS — 사용자 정보
--     회원 계정 프로필, 비밀번호 해시, 선호 챗봇 성격 및 푸시 토큰 관리
-- =====================================================================
CREATE TABLE USERS (
    user_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    name            VARCHAR(100) NOT NULL,
    phone           TEXT,   -- [05-B] AES-256-GCM 암호문(Base64) 저장
    birth_date      DATE,
    gender          VARCHAR(10) CHECK (gender IN ('MALE', 'FEMALE', 'OTHER')),
    fcm_token       TEXT,
    height_cm       NUMERIC(5,2) CHECK (height_cm > 0),
    persona_type    VARCHAR(20) NOT NULL DEFAULT 'FRIEND'   -- [05-C]
                        CHECK (persona_type IN ('FRIEND', 'COUNSELOR')),
    terms_agreed    BOOLEAN NOT NULL DEFAULT FALSE,
    terms_agreed_at TIMESTAMPTZ,
    CONSTRAINT chk_terms_logic CHECK (
        (terms_agreed = FALSE AND terms_agreed_at IS NULL) OR
        (terms_agreed = TRUE  AND terms_agreed_at IS NOT NULL)
    )
);

-- [05-C] ✅ 2026.07.29 확정 — DEFAULT 'FRIEND' 추가
--   persona_type 이 NOT NULL 인데 DEFAULT 가 없어 회원가입 INSERT 가 실패했습니다.
--   회원가입 화면(MAIN_JOIN_02)은 이메일/비밀번호/이름/생년월일/성별만 받고,
--   페르소나 선택은 로그인 이후 MLCM_300 에서 이루어지기 때문입니다.
--   DEFAULT 'FRIEND' 로 해소했으며 CHAT_SESSIONS.persona_type 과 정의가 일치합니다.

-- [05-B] ✅ 2026.07.29 확정 — VARCHAR(20) -> TEXT
--   02-F (3) 에서 연락처를 AES-256-GCM 컬럼 암호화 대상으로 확정했습니다.
--   IV·인증태그를 포함한 암호문을 Base64 로 담으면 60자를 넘어 VARCHAR(20) 에
--   저장할 수 없으므로 TEXT 로 변경했습니다.
--   ※ 암호화 컬럼이므로 phone 기준 검색·정렬·중복확인은 불가능합니다.
--     현재 로그인·본인확인은 email 기준이고 SMS 발송 계획이 없어 제약이 없습니다.
--     추후 phone 조회가 필요해지면 별도 blind index(HMAC) 도입을 검토해야 합니다.

-- [문서 내부 불일치] ✅ 2026.07.29 확정 — VARCHAR(20) 으로 통일
--   05 테이블명세서의 컬럼 정의표(20)와 CREATE 스크립트(50)가 달랐습니다.
--   실제 최대값이 'COUNSELOR'(9자)이고 CHAT_SESSIONS.persona_type 이 이미
--   VARCHAR(20) 이므로 20 으로 맞췄습니다. HWP 문서의 CREATE 스크립트도 수정 필요.


-- =====================================================================
--  2. EMOTIONS — 감정 마스터
--     시스템 공통 감정 코드(9개) 및 분류 기준 정의
-- =====================================================================
CREATE TABLE EMOTIONS (
    emotion_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    emotion_code VARCHAR(50) NOT NULL UNIQUE,
    emotion_name VARCHAR(50) NOT NULL,
    category     VARCHAR(20) NOT NULL CHECK (category IN ('NORMAL', 'CAUTION', 'CRITICAL'))
);


-- =====================================================================
--  3. DEVICE_HEALTH_CONNECTIONS — 디바이스 헬스 연동 정보
-- =====================================================================
CREATE TABLE DEVICE_HEALTH_CONNECTIONS (
    connection_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id            UUID NOT NULL REFERENCES USERS(user_id) ON DELETE CASCADE,
    device_name        VARCHAR(100),
    platform_type      VARCHAR(50) NOT NULL
        CHECK (platform_type IN ('HEALTH_CONNECT', 'APPLE_HEALTH')),
    permission_granted BOOLEAN NOT NULL DEFAULT FALSE,   -- [05-A] 기기 내 권한 승인 상태
    agreed_at          TIMESTAMPTZ NOT NULL,
    last_synced_at     TIMESTAMPTZ,                      -- [05-A] 미수신 감지·재시도 판단 기준
    consent_scopes     JSONB NOT NULL DEFAULT
        '{"activity": true, "sleep": true, "body_composition": false}'
);

-- [05-A] ✅ 2026.07.29 확정 — 앱 push 구조 전환에 따른 개정
--   Health Connect 는 Android on-device 권한 모델이라 서버가 보유할 OAuth
--   access token 이 존재하지 않습니다. access_token 컬럼을 제거하고
--   permission_granted / last_synced_at 를 추가했습니다.
--
--   last_synced_at 은 두 곳에서 사용됩니다.
--     1) 앱   — 이 시각 이후의 신규 데이터만 Health Connect 에서 조회
--     2) 서버 — 일정 시간 이상 미갱신 시 미수신으로 감지하고 FCM 무음 푸시로
--               앱 동기화를 유도 (USERS.fcm_token 사용)
--
--   ⚠ 연동 문서: 02 요구사항정의서 MLCM_200 이 서버 pull -> 앱 push 로,
--     NFR-DV-002 의 재시도 주체가 서버 스케줄러 -> 앱 클라이언트로 이동합니다.
--     04 DB요구사항분석서 2) 객체 정의서도 동일하게 개정 필요.
--
--   APPLE_HEALTH 는 구현 범위에서 제외(안건 2)되었으나 enum 값은 유지합니다.
--   제거하면 platform_type 에 값이 하나뿐이라 컬럼의 존재 이유가 사라집니다.


-- =====================================================================
--  4. LIFELOG_METRICS — 시계열 라이프로그
--     생체 시계열 데이터(걸음수, 수면, 심박수, HRV) 및 원시 JSONB 보관
-- =====================================================================
CREATE TABLE LIFELOG_METRICS (
    metric_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id              UUID NOT NULL REFERENCES USERS(user_id) ON DELETE CASCADE,
    steps                INTEGER DEFAULT 0 CHECK (steps >= 0),
    distance             INTEGER DEFAULT 0 CHECK (distance >= 0),
    calories             INTEGER DEFAULT 0 CHECK (calories >= 0),
    sleep_start_at       TIMESTAMPTZ,
    sleep_end_at         TIMESTAMPTZ,
    total_sleep_min      INTEGER CHECK (total_sleep_min >= 0),
    deep_sleep_min       INTEGER CHECK (deep_sleep_min >= 0),
    light_sleep_min      INTEGER CHECK (light_sleep_min >= 0),
    rem_sleep_min        INTEGER CHECK (rem_sleep_min >= 0),
    awake_min            INTEGER CHECK (awake_min >= 0),
    sleep_onset_min      INTEGER CHECK (sleep_onset_min >= 0),
    sleep_efficiency_pct NUMERIC(5,2) CHECK (sleep_efficiency_pct BETWEEN 0 AND 100),
    heart_rate           INTEGER DEFAULT 0 CHECK (heart_rate >= 0),
    hrv                  NUMERIC(5,2) DEFAULT 0 CHECK (hrv >= 0),
    raw_payload          JSONB,
    collected_at         TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_lifelog_user_collected UNIQUE (user_id, collected_at)
);


-- =====================================================================
--  5. CHAT_SESSIONS — 챗봇 대화 세션 및 메시지
-- =====================================================================
CREATE TABLE CHAT_SESSIONS (
    session_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES USERS(user_id) ON DELETE CASCADE,
    persona_type    VARCHAR(20) NOT NULL DEFAULT 'FRIEND'
        CHECK (persona_type IN ('FRIEND', 'COUNSELOR')),
    messages        JSONB NOT NULL,   -- PII [MASK] 치환 후 저장
    session_summary TEXT,             -- 세션 종료 시 LLM 자동 생성 요약
    started_at      TIMESTAMPTZ NOT NULL,
    ended_at        TIMESTAMPTZ
);


-- =====================================================================
--  6. EMOTION_RISK_SCORES — 정서 위험도 예측 결과
-- =====================================================================
CREATE TABLE EMOTION_RISK_SCORES (
    score_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES USERS(user_id) ON DELETE CASCADE,
    emotion_id    UUID NOT NULL REFERENCES EMOTIONS(emotion_id) ON DELETE RESTRICT,
    emotion_score NUMERIC(5,2) NOT NULL CHECK (emotion_score BETWEEN 0 AND 100),
    risk_level    VARCHAR(20) NOT NULL
        CHECK (risk_level IN ('NORMAL', 'CAUTION', 'CRITICAL')),
    risk_score    NUMERIC(5,2) NOT NULL CHECK (risk_score BETWEEN 0 AND 100),
    model_version VARCHAR(50) NOT NULL,
    evaluated_at  TIMESTAMPTZ NOT NULL
);


-- =====================================================================
--  7. HEALING_CONTENTS — 힐링 콘텐츠 마스터
--     CAUTION(주의) 단계 추천용 감정별 맞춤 콘텐츠 메타데이터
-- =====================================================================
CREATE TABLE HEALING_CONTENTS (
    content_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    emotion_id   UUID NOT NULL REFERENCES EMOTIONS(emotion_id) ON DELETE RESTRICT,
    category     VARCHAR(20) NOT NULL
        CHECK (category IN ('MUSIC', 'FOOD', 'EXERCISE', 'ARTICLE')),
    title        VARCHAR(200) NOT NULL,
    description  TEXT,
    external_url TEXT NOT NULL
);

-- [문서 내부 불일치] ✅ 2026.07.29 확정 — VARCHAR(20) 으로 통일
--   컬럼 정의표(20)와 CREATE 스크립트(50)가 달랐습니다.
--   실제 최대값이 'EXERCISE'(8자)이므로 정의표 쪽 20 을 따랐습니다.
--   HWP 문서의 CREATE 스크립트도 수정 필요.


-- =====================================================================
--  8. BODY_COMPOSITION_METRICS — 체성분 데이터
-- =====================================================================
CREATE TABLE BODY_COMPOSITION_METRICS (
    body_metric_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id            UUID NOT NULL REFERENCES USERS(user_id) ON DELETE CASCADE,
    weight_kg          NUMERIC(5,2) CHECK (weight_kg >= 0),
    body_water_kg      NUMERIC(5,2) CHECK (body_water_kg >= 0),
    body_fat_kg        NUMERIC(5,2) CHECK (body_fat_kg >= 0),
    muscle_mass_kg     NUMERIC(5,2) CHECK (muscle_mass_kg >= 0),
    muscle_mass_min_kg NUMERIC(5,2) CHECK (muscle_mass_min_kg >= 0),
    muscle_mass_max_kg NUMERIC(5,2) CHECK (muscle_mass_max_kg >= 0),
    skeletal_muscle_kg NUMERIC(5,2) CHECK (skeletal_muscle_kg >= 0),
    bmr_kcal           INTEGER CHECK (bmr_kcal >= 0),
    measured_at        TIMESTAMPTZ NOT NULL
);


-- =====================================================================
--  인덱스
-- =====================================================================
--  04 DB요구사항분석서 5항이 (user_id, collected_at DESC) 복합 인덱스를
--  필수로 규정하고 있습니다.
--
--  참고: 위 UNIQUE (user_id, collected_at) 제약이 이미 btree 인덱스를 만들고,
--  PostgreSQL 은 btree 를 역방향으로도 효율적으로 스캔하므로 DESC 정렬 조회에도
--  사실상 동일한 성능이 나옵니다. 다만 문서 요건과 스키마를 일치시키기 위해
--  명시적으로 선언합니다.
CREATE INDEX idx_lifelog_user_collected
    ON LIFELOG_METRICS (user_id, collected_at DESC);

--  위험도 조회 / 관리자 관제 대시보드(MLCM_501) 고위험군 우선 정렬용
CREATE INDEX idx_risk_user_evaluated
    ON EMOTION_RISK_SCORES (user_id, evaluated_at DESC);

--  체성분 이력 조회용
CREATE INDEX idx_body_user_measured
    ON BODY_COMPOSITION_METRICS (user_id, measured_at DESC);

--  대화 세션 목록 조회용
CREATE INDEX idx_chat_user_started
    ON CHAT_SESSIONS (user_id, started_at DESC);

--  CAUTION 단계 콘텐츠 추천 시 감정별 필터링용
CREATE INDEX idx_healing_emotion
    ON HEALING_CONTENTS (emotion_id);

--  [05-A] 라이프로그 미수신 감지 배치용
--  권한이 승인된 연동만 대상으로 last_synced_at 이 오래된 순으로 스캔합니다.
--  임계 시간을 넘긴 사용자에게 FCM 무음 푸시를 보내 앱 동기화를 유도합니다.
CREATE INDEX idx_device_last_synced
    ON DEVICE_HEALTH_CONNECTIONS (last_synced_at)
    WHERE permission_granted = TRUE;


-- =====================================================================
--  마스터 데이터 — EMOTIONS 9종
-- =====================================================================
--  category 컬럼이 곧 기본 위험도 값입니다. (04 DB요구사항분석서 6항)
--  단, ANGER 만 emotion_score 에 따라 런타임에 동적 재분류됩니다.
--      ANGER + emotion_score <  70  ->  CAUTION
--      ANGER + emotion_score >= 70  ->  CRITICAL
--  CRISIS 는 emotion_score 와 무관하게 즉시 CRITICAL 확정입니다.
INSERT INTO EMOTIONS (emotion_code, emotion_name, category) VALUES
    ('JOY',        '기쁨',   'NORMAL'),
    ('DELIGHT',    '즐거움', 'NORMAL'),
    ('HAPPINESS',  '행복',   'NORMAL'),
    ('SADNESS',    '슬픔',   'CAUTION'),
    ('ANXIETY',    '불안',   'CAUTION'),
    ('LONELINESS', '외로움', 'CAUTION'),
    ('ANGER',      '분노',   'CAUTION'),   -- emotion_score >= 70 이면 CRITICAL 로 재분류
    ('DESPAIR',    '절망',   'CRITICAL'),
    ('CRISIS',     '위기',   'CRITICAL');
