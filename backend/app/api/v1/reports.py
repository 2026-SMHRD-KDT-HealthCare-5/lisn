"""정서 리포트 엔드포인트 — MLCM_500

화면: MAIN_REPORT_01
명세: docs/API명세_초안.md 6절
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


# TODO(PDF): FR-MN-001 이 "PDF 로 내보내 상담기관·주치의 등과 공유" 를 규정한다.
#   GET /reports/export 가 필요하다. 차트 렌더링이 들어가므로 서버에서 그릴지
#   클라이언트가 화면을 캡처해 만들지 먼저 정해야 한다.
#   - 서버 생성: 일관된 결과. 다만 한글 폰트 임베드와 차트 라이브러리가 필요
#   - 클라이언트 생성: Flutter 에 이미 화면이 있어 재사용 가능. 기기별 편차 발생
