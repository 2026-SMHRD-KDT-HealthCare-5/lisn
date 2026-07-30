from fastapi import FastAPI, HTTPException
from sqlalchemy import text

from app.core.database import engine

app = FastAPI(
    title="귀기울임 API",
    version="1.0.0",
)


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