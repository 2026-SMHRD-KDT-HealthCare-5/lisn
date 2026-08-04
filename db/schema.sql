-- =====================================================================
--  귀기울임 (LISN) — 데이터베이스 스키마
--  과제명 : 멀티모달 라이프로그 감정 분석 기반 맞춤형 LLM 케어 및 모니터링 시스템
--
--  출처   : Documents/05_테이블명세서_귀기울임.hwp (2026.07.23 / 작성자 이응균)
--  대상   : PostgreSQL 13 이상
--
--  ※ 이 파일은 테이블명세서 원문을 baseline 으로 하되,
--    2026.07.29 팀 회의에서 확정된 개정안 [05-A] [05-B] [05-C] 를 반영한 상태입니다.
--    ⚠ 테이블명세서(HWP) 원문은 아직 미반영입니다. 문서 개정 시 이 파일을 기준으로 맞추세요.
--    개정 내역: docs/진행/문서개정_체크리스트.md
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
    sensitive_agreed    BOOLEAN NOT NULL DEFAULT FALSE,   -- [05-K]
    sensitive_agreed_at TIMESTAMPTZ,                      -- [05-K]
    role                VARCHAR(20) NOT NULL DEFAULT 'USER'   -- [SD-E1]
                            CHECK (role IN ('USER', 'ADMIN')),
    care_alert_agreed    BOOLEAN NOT NULL DEFAULT TRUE,   -- [05-N] 케어 알림
    content_alert_agreed BOOLEAN NOT NULL DEFAULT TRUE,   -- [05-N] 콘텐츠·리포트
    CONSTRAINT chk_terms_logic CHECK (
        (terms_agreed = FALSE AND terms_agreed_at IS NULL) OR
        (terms_agreed = TRUE  AND terms_agreed_at IS NOT NULL)
    ),
    CONSTRAINT chk_sensitive_logic CHECK (
        (sensitive_agreed = FALSE AND sensitive_agreed_at IS NULL) OR
        (sensitive_agreed = TRUE  AND sensitive_agreed_at IS NOT NULL)
    )
);

-- [05-N] ✅ 2026.08.03 확정 — 알림 수신 동의 2컬럼 신설
--   `MLCM_400` 5단계가 "사용자가 **알림 수신 동의 상태인 경우**" 를 전제하는데
--   그 상태를 담을 컬럼이 없었습니다. `fcm_token` 은 있는데 동의는 없어서,
--   요구사항이 이미 전제하는 것을 저장할 수 없는 상태였습니다.
--   신규 요구가 아니라 **기존 요구사항의 미반영**입니다.
--
--   ⚠ **왜 하나가 아니라 둘인가** — 안전 알림과 콘텐츠 알림을 한 토글에
--     묶으면 **콘텐츠 알림이 귀찮아 끈 사람이 선제 접촉(MLCM_220)까지
--     끕니다.** 그리고 알림을 끄는 사람일수록 앱을 안 여는 사람, 즉 우리가
--     놓치면 안 되는 쪽입니다. 하나로 두는 편이 구현은 쉽지만 기능의 존재
--     이유와 충돌합니다.
--         care_alert_agreed     선제 접촉 · 정서 상태 안내
--         content_alert_agreed  힐링 콘텐츠 추천(MLCM_400) · 주간 리포트
--
--   ⚠ **기본값이 TRUE 입니다.** `MLCM_400` 5단계가 동의 상태를 전제하는데
--     기본이 꺼져 있으면 그 유스케이스가 기본 상태에서 동작하지 않습니다.
--     다만 첫 실행 안내에서 끌 수 있어야 합니다 — 동의 없이 켜두는 것과
--     다릅니다.
--
--   ⚠ 화면설계서 `MAIN_SETTING_01` ❷ 는 토글 **1개**로, 앱은 **3개**로 되어
--     있었습니다. 셋 다 달랐습니다. 화면설계서가 정본이므로 그쪽을 2개로
--     고칩니다(개정안 「알림 수신 동의를 2개로」).
--   ⚠ 연동 문서: 데이터베이스요구사항분석서 객체 정의서 USERS 속성 목록, 테이블명세서 컬럼 정의표 및 CREATE 스크립트

-- [SD-E1] ✅ 2026.07.30 확정 — 관리자 구분 컬럼 신설
--   관리자 기능이 요구사항·기능명세·발표자료에 모두 있는데 데이터 모델에
--   관리자라는 개념이 없었습니다. 어떤 계정이 관리자인지 판별할 수단이 없어
--   MLCM_501(관리자 관제 대시보드)을 구현할 수 없는 상태였습니다.
--     요구사항정의서 MLCM_501  관련 액터 "관리자", 선행조건 "관리자 계정으로 로그인되어 있어야 함"
--     요구사항정의서 FR-MN-003 관리자가 전체 사용자 위험도 분포를 조회하고 고위험군 우선 식별
--     요구사항정의서 MLCM_510  판정 이력을 관리자가 통계·모니터링 목적으로 조회
--     데이터베이스요구사항분석서 3)        접근통제를 "본인 및 권한 있는 관리자로 제한"
--   ※ DEFAULT 'USER' 로 두어 회원가입 흐름을 건드리지 않습니다(05-C 와 같은 방식).
--     관리자는 일반 가입 후 승격합니다. 시드로 넣으려면 bcrypt 해시를 SQL 에
--     하드코딩해야 해 오히려 지저분해집니다.
--         UPDATE USERS SET role = 'ADMIN' WHERE email = '<관리자 이메일>';
--   ※ 별도 관리자 테이블은 채택하지 않았습니다. 로그인 로직·JWT 발급 경로·
--     비밀번호 정책이 각각 둘이 되어, 관리자 한두 명 때문에 인증 체계를
--     복제하는 셈이 됩니다.
--   ※ 이 컬럼이 02-F (6) 의 방어 논리를 완성합니다. "접근통제(본인 및 권한 있는
--     관리자로 제한)" 라는 문장이 지금까지는 판별 수단 없이 떠 있었습니다.
--   ⚠ 연동 문서: 데이터베이스요구사항분석서 객체 정의서 USERS 속성 목록, 테이블명세서 컬럼 정의표 및 CREATE 스크립트,
--     화면설계서 ADMIN_LOGIN_01(SD-N6). 상세는 docs/결정/화면설계서_개정안.md Part E

-- [05-K] ✅ 2026.07.30 확정 — 민감정보 별도 동의 기록 2컬럼 추가
--   02-L 로 "민감정보는 일반 개인정보 동의와 구분된 별도 동의 항목으로 처리한다"를
--   요구사항정의서에 반영했으나, 동의 기록은 terms_agreed BOOLEAN 하나뿐이었습니다.
--   동의 항목이 둘인데 참/거짓 하나로는 어느 항목에 동의했는지 표현할 수 없어
--   "별도 동의를 받는다"는 문서와 스키마가 어긋났습니다.
--   ※ 법 요건(제23조 제1항)은 화면에서 별도 항목으로 분리하면 충족되며, 이 컬럼은
--     동의 시점 증빙을 남기기 위한 것입니다. 데이터베이스요구사항분석서가 동의 여부·일시 관리를
--     명시하고 있어 민감정보만 기록이 없으면 누락으로 보입니다.
--   ※ sensitive_agreed_at 하나로 줄일 수 있으나 terms_agreed 쌍과 형식을 맞췄습니다.
--     같은 테이블에서 두 동의가 다른 방식이면 그 자체가 질문을 만듭니다.

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
--   테이블명세서의 컬럼 정의표(20)와 CREATE 스크립트(50)가 달랐습니다.
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
--   ⚠ 연동 문서: 요구사항정의서 MLCM_200 이 서버 pull -> 앱 push 로,
--     NFR-DV-002 의 재시도 주체가 서버 스케줄러 -> 앱 클라이언트로 이동합니다.
--     데이터베이스요구사항분석서 2) 객체 정의서도 동일하게 개정 필요.
--
--   APPLE_HEALTH 는 구현 범위에서 제외(안건 2)되었으나 enum 값은 유지합니다.
--   제거하면 platform_type 에 값이 하나뿐이라 컬럼의 존재 이유가 사라집니다.


-- =====================================================================
--  4. LIFELOG_METRICS — 시계열 라이프로그
--     생체 시계열 데이터(걸음수, 활동, 수면, 심박수, HRV) 및 원시 JSONB 보관
-- =====================================================================
CREATE TABLE LIFELOG_METRICS (
    metric_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id              UUID NOT NULL REFERENCES USERS(user_id) ON DELETE CASCADE,
    steps                INTEGER DEFAULT 0 CHECK (steps >= 0),
    distance             INTEGER DEFAULT 0 CHECK (distance >= 0),
    calories             INTEGER DEFAULT 0 CHECK (calories >= 0),
    activity_start_at    TIMESTAMPTZ,                                -- [05-E]
    activity_end_at      TIMESTAMPTZ,                                -- [05-E]
    total_active_min     INTEGER CHECK (total_active_min >= 0),      -- [05-E]
    sleep_start_at       TIMESTAMPTZ,
    sleep_end_at         TIMESTAMPTZ,
    total_sleep_min      INTEGER CHECK (total_sleep_min >= 0),
    deep_sleep_min       INTEGER CHECK (deep_sleep_min >= 0),
    light_sleep_min      INTEGER CHECK (light_sleep_min >= 0),
    rem_sleep_min        INTEGER CHECK (rem_sleep_min >= 0),
    awake_min            INTEGER CHECK (awake_min >= 0),
    sleep_onset_min      INTEGER CHECK (sleep_onset_min >= 0),
    sleep_efficiency_pct NUMERIC(5,2) CHECK (sleep_efficiency_pct BETWEEN 0 AND 100),
    heart_rate           INTEGER CHECK (heart_rate >= 0),        -- [05-H]
    hrv                  NUMERIC(5,2) CHECK (hrv >= 0),          -- [05-H]
    collected_at         TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_lifelog_user_collected UNIQUE (user_id, collected_at)
);

-- [05-E] ✅ 2026.07.29 확정 — 활동 시각 3컬럼 추가
--   기업(라라랩스) 제공 라이프로그 메타데이터에 '활동 시작 시간'·'활동 종료 시각'·
--   '총활동 시간'이 있는데 대응 컬럼이 없어 적재 시 버려지는 항목이었습니다.
--   수면은 sleep_start_at·sleep_end_at·total_sleep_min 로 시작·종료·총시간을 모두
--   받는데 활동만 steps·distance·calories 로 총량뿐이라 구조도 비대칭이었습니다.
--   ※ 메타데이터는 hh:mm:ss 로 제공되지만 TIMESTAMPTZ 로 받습니다.
--     데이터베이스요구사항분석서 2) 가 "모든 날짜/시간 컬럼은 TIMESTAMPTZ 로 통일"을 규정하고 있고,
--     날짜 컬럼과 합쳐야 자정을 넘긴 활동 구간을 표현할 수 있기 때문입니다.
--   ※ 적재 시 활동 시각이 없는 데이터 출처(PMData·GLOBEM·Health Connect 일부)가
--     있으므로 NULL 을 허용합니다. 분석은 NOT NULL 인 구간에 한해 수행합니다.

-- [05-G] ✅ 2026.07.30 확정 — raw_payload 제거
--   비고가 "추가 수면단계/활동 확장용"이었으나 무엇을 담는지 정의가 없었습니다.
--   활동 시각 3컬럼을 [05-E] 로 정식 컬럼화하면서(JSONB 보관 절충안 미채택)
--   확장 슬롯의 존재 이유가 사라졌습니다. 실제로 쓰지 않는 컬럼을 "확장용"으로
--   남겨두면 적재 규격이 불명확해지므로 제거합니다.
--   추후 신규 지표가 생기면 그때 정식 컬럼으로 추가합니다.

-- [05-H] ✅ 2026.07.30 확정 — heart_rate·hrv 의 DEFAULT 0 제거
--   심박수 0 은 "측정되지 않음"이 아니라 생물학적으로 불가능한 값입니다.
--   워치 미착용 구간이 전부 0 으로 적재되면 개인별 14일 기준값(평균 심박)이
--   왜곡되고, LSTM Autoencoder 가 그 0 을 정상 패턴으로 학습합니다.
--   NULL 로 두어 결측과 실측을 구분하고, 분석 파이프라인이 해당 구간을
--   제외하도록 합니다. steps·distance·calories 는 실제로 0 일 수 있어 유지합니다.


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
--  데이터베이스요구사항분석서 5항이 (user_id, collected_at DESC) 복합 인덱스를
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
--  category 컬럼이 곧 기본 위험도 값입니다. (데이터베이스요구사항분석서 6항)
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
