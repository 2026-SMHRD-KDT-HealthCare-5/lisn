"""환경 설정. 값은 backend/.env 에서 읽는다 (.env.example 참고)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str

    # 인증 — access token 단일, refresh 없음.
    # 근거: docs/review/API설계_사전결정.md 1절
    jwt_secret: str = "CHANGE_ME"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24

    # 비밀번호 재설정 토큰. 별도 테이블을 두지 않고 짧은 수명의 JWT 로 처리한다.
    password_reset_expire_minutes: int = 30

    openai_api_key: str = ""

    # AI 추론 서버. 내부 통신이라 인증이 없으므로 외부에 포트를 열지 말 것.
    ai_server_url: str = "http://localhost:8001"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
