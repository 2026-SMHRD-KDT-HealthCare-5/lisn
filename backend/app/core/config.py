"""환경 설정. 값은 backend/.env 에서 읽는다 (.env.example 참고)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str

    # 인증 — access token 단일, refresh 없음.
    # 근거: docs/결정/API설계_사전결정.md 1절
    jwt_secret: str = "CHANGE_ME"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24

    # 비밀번호 재설정 토큰. 별도 테이블을 두지 않고 짧은 수명의 JWT 로 처리한다.
    password_reset_expire_minutes: int = 30

    # ⚠ 재설정 토큰을 로그에 찍을지. **기본값 꺼짐을 바꾸지 말 것.**
    #   토큰은 그 자체로 계정 탈취 수단이라, 로그를 보는 사람은 누구나 남의
    #   비밀번호를 바꿀 수 있다. SMTP 가 없어 개발 중 흐름을 타봐야 할 때만 켠다.
    password_reset_log_token: bool = False

    # 컬럼 암호화 키(AES-256-GCM). base64 인코딩된 32바이트.
    # 02-F (3) 대상은 현재 USERS.phone 하나다.
    #   생성: python -c "import base64,os; print(base64.b64encode(os.urandom(32)).decode())"
    encryption_key: str = "CHANGE_ME"

    # ----------------------------------------------------------------
    # LLM 공급자 — 전환 가능 (2026.08.01 PM 확정)
    # ----------------------------------------------------------------
    # 평소 개발은 **Gemini**(무료 한도), 정확도 검사와 시연은 **OpenAI**.
    #
    # ⚠ Gemini 는 **임시 수단**이다. 산출 문서 01·02 의 "외부 OpenAI API" 가 정본이고
    #   문서는 고치지 않는다. 그러니 **OpenAI 경로를 죽이지 말 것** —
    #   죽이면 문서와 실제 시스템이 어긋난다.
    #
    #   .env 에서 LLM_PROVIDER=openai 로 바꾸고 서버를 재기동하면 됩니다.
    #
    # Gemini 는 OpenAI 호환 엔드포인트를 제공해 SDK 는 openai 를 그대로 쓴다.
    # 다만 Responses API 는 미지원이라 양쪽 다 Chat Completions 로 통일했다
    # (llm.py 헤더 주석 참조).
    llm_provider: str = "gemini"          # "gemini" | "openai"

    gemini_api_key: str = ""
    openai_api_key: str = ""

    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"

    # ⚠ Gemini 는 작업마다 **다른 모델**을 쓴다. 무료 한도(RPM/RPD)가 모델별로 따로
    #   잡혀서, 전부 한 모델에 몰면 그 하나가 병목이 된다. 특히 앞의 둘은
    #   analyze_and_reply 에서 **동시에** 호출되므로 반드시 갈라놔야 한다.
    #
    # 2026.08.01 실측 — 무료 키로 실제 호출해 확인한 결과다.
    #   gemini-3.6-flash        OK 2.74s
    #   gemini-3.5-flash        503 UNAVAILABLE   ← 쓰지 말 것
    #   gemini-3.5-flash-lite   OK 0.93s
    #   gemini-3.1-flash-lite   OK 0.93s
    #   gemini-2.5-flash        OK 1.22s
    #   gemini-2.5-flash-lite   OK 1.12s
    #   gemini-2.5-pro          429 무료 한도 없음  ← 쓰지 말 것
    gemini_model_crisis: str = "gemini-3.6-flash"        # 위기 판정 — 안전 직결, 가장 좋은 모델
    gemini_model_reply: str = "gemini-2.5-flash"         # 페르소나 응답 — 품질·지연 균형
    gemini_model_summary: str = "gemini-3.5-flash-lite"  # 세션 요약 — 백그라운드
    gemini_model_daily: str = "gemini-3.1-flash-lite"    # 홈 한줄 요약 — 캐시됨

    # ⚠ 무료 티어는 모델이 통째로 503 이 되는 일이 있다. 기본 재시도(2회)를 그대로 두면
    #   죽은 모델 하나가 NFR-DV-001 3초 예산을 통째로 먹는다(실측 13.95초).
    #   빠르게 포기하고 키워드 fallback(NFR-DV-003)으로 넘기는 편이 맞다.
    llm_timeout_seconds: float = 8.0
    llm_max_retries: int = 0

    # OpenAI 는 쿼터를 분산할 이유가 없어 한 모델로 통일한다. 정확도 기준선이므로
    # 네 작업이 같은 모델을 써야 Gemini 와의 비교가 의미를 갖는다.
    openai_model: str = "gpt-5.6"

    # AI 추론 서버. 내부 통신이라 인증이 없으므로 외부에 포트를 열지 말 것.
    ai_server_url: str = "http://localhost:8001"

    # 브라우저 기반 관리자 웹의 개발 origin. 쉼표로 여러 값을 지정한다.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
