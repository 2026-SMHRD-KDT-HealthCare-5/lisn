import asyncio
import contextlib
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1 import api_router
from app.core.config import settings
from app.core.database import AsyncSessionLocal, engine
from app.services import sync_watch

logger = logging.getLogger(__name__)


async def _sync_watch_loop():
    """미수신 감지를 주기적으로 돌린다 — NFR-DV-002 (구현_갭 갭3).

    APScheduler 를 들이지 않은 이유 — 주기가 하나뿐이고 크론 표현식도
    필요 없다. SMTP 를 smtplib 로 붙인 것과 같은 판단이다.

    ⚠ **한 번 실패해도 루프를 멈추지 않는다.** DB 가 잠깐 끊겨 예외가
      나면 그대로 죽어서, 서버는 살아 있는데 미수신 감지만 조용히 멈춘
      상태가 된다. 그런 고장은 아무도 모른다.
    """
    interval = settings.sync_watch_interval_minutes * 60
    while True:
        await asyncio.sleep(interval)
        try:
            async with AsyncSessionLocal() as db:
                await sync_watch.scan(db)
        except Exception:
            logger.exception("[sync-watch] 스캔 실패 — 다음 주기에 다시 시도합니다")


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI):
    task = None
    if settings.sync_watch_enabled:
        task = asyncio.create_task(_sync_watch_loop())
        logger.info(
            "[sync-watch] 미수신 감지 시작 — %d분 주기",
            settings.sync_watch_interval_minutes,
        )
    yield
    if task is not None:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


app = FastAPI(
    lifespan=lifespan,
    title="귀기울임 API",
    version="1.0.0",
    description=(
        "구현이 진행되면 이 /docs 가 API 명세의 정본이 됩니다. "
        "docs/결정/API명세_초안.md 는 착수용 초안이므로 갱신하지 않습니다."
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
