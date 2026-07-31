from fastapi import APIRouter

from app.api.v1 import admin, auth, chat, devices, home, lifelog, reports, users

# 버전 접두사는 처음부터 붙인다. 나중에 붙이면 클라이언트를 전부 고쳐야 한다.
api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(devices.router)
api_router.include_router(lifelog.router)
api_router.include_router(chat.router)
api_router.include_router(reports.router)
api_router.include_router(home.router)
api_router.include_router(admin.router)
