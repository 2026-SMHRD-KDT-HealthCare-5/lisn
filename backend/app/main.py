from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1 import api_router
from app.core.config import settings
from app.core.database import engine

app = FastAPI(
    title="귀기울임 API",
    version="1.0.0",
    description=(
        "구현이 진행되면 이 /docs 가 API 명세의 정본이 됩니다. "
        "docs/API명세_초안.md 는 착수용 초안이므로 갱신하지 않습니다."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/health/db")
async def database_health_check():
    try:
        async with engine.connect() as connection:
            result = await connection.execute(text("SELECT 1"))
            result.scalar_one()

        return {
            "status": "ok",
            "database": "connected",
        }
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail=f"Database connection failed: {error}",
        )
