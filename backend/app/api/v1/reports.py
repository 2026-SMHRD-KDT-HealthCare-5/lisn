"""정서 리포트 엔드포인트 — MLCM_500

화면: MAIN_REPORT_01
명세: docs/결정/API명세_초안.md 6절
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.models import EmotionRiskScore
from app.schemas.report import ReportOut
from app.services.report import build_report

router = APIRouter(prefix="/reports", tags=["reports"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=ReportOut)
async def my_report(
    user: CurrentUser,
    db: DbSession,
    date_from: Annotated[datetime | None, Query(alias="from")] = None,
    date_to: Annotated[datetime | None, Query(alias="to")] = None,
):
    """본인 정서 리포트 — MLCM_500

    선행조건이 "분석 히스토리가 최소 1일 이상 존재" 이므로 이력이 없으면
    409 로 데이터 부족을 알린다. 빈 차트를 내리면 클라이언트가
    "분석 실패"인지 "아직 데이터 없음"인지 구분할 수 없다.
    """
    count = await db.scalar(
        select(func.count())
        .select_from(EmotionRiskScore)
        .where(EmotionRiskScore.user_id == user.user_id)
    )
    if not count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="아직 분석된 기록이 없습니다. 하루 이상 라이프로그가 수집되면 리포트를 볼 수 있어요",
        )

    return await build_report(db, user.user_id, date_from, date_to)


# PDF 내보내기(FR-MN-001)는 **클라이언트가 만듭니다** — 2026.08.01 확정.
#
# 서버에 GET /reports/export 를 두지 않습니다. Flutter 에 MAIN_REPORT_01 화면이
# 이미 있어 그대로 조판할 수 있고, 서버 생성은 한글 폰트 임베드와 차트 라이브러리를
# 백엔드에 새로 붙여야 해서 남은 일정에 비해 비용이 큽니다.
#
# → 앱은 위 GET /reports 응답을 그대로 써서 PDF 를 만듭니다. **이 엔드포인트가
#   PDF 의 데이터 원본**이므로, 리포트에 넣을 항목이 늘면 여기 응답부터 넓히세요.
#
# ⚠ 기기별로 여백·해상도 편차가 생깁니다. 상담기관에 제출되는 문서라 최소한
#   기간·생성일시·본인 식별 정보는 어느 기기에서 뽑아도 같은 위치에 있어야 합니다.
#   앱 쪽 규격은 docs/design/HANDOFF-CODEX.md 를 보세요.
