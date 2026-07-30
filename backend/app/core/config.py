## config.py / database.py 내용 데이터베이스 읽어오는데
## 파이썬언어로 변환해서 연결(fastapi 사용때문)
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
settings = Settings()