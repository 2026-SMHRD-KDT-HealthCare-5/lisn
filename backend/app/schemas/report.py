"""정서 리포트 · 관리자 관제 스키마 — MLCM_500 · MLCM_501"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class RiskPoint(BaseModel):
    """감정 추이 곡선의 한 점."""

    evaluated_at: datetime
    emotion_code: str
    emotion_name: str
    emotion_score: Decimal
    risk_level: Literal["NORMAL", "CAUTION", "CRITICAL"]
    risk_score: Decimal


class LifelogPoint(BaseModel):
    """감정 추이와 같은 시간축에 겹칠 라이프로그."""

    collected_at: datetime
    steps: int | None
    total_sleep_min: int | None
    heart_rate: int | None
    hrv: Decimal | None


class RiskDistribution(BaseModel):
    normal: int = 0
    caution: int = 0
    critical: int = 0


class ReportOut(BaseModel):
    """MLCM_500 · MAIN_REPORT_01

    관리자 상세 조회(MLCM_501 ❸)도 같은 스키마를 쓴다. 대상 user_id 만
    관리자가 지정한다 — 시각화 규격을 맞추기 위함이다.
    """

    user_id: uuid.UUID
    date_from: datetime | None
    date_to: datetime | None
    distribution: RiskDistribution
    emotion_trend: list[RiskPoint]
    lifelog_trend: list[LifelogPoint]
    summary: str


# --------------------------------------------------------------------------
# 관리자 관제
# --------------------------------------------------------------------------

class AdminDashboard(BaseModel):
    """전체 위험도 분포 — MLCM_501 ❶

    각 사용자의 **최신 평가 1건**만 세운다. 전체 행을 세면 자주 측정한
    사용자가 분포를 왜곡한다.
    """

    distribution: RiskDistribution
    total_users: int
    evaluated_users: int
    generated_at: datetime


class AdminUserRow(BaseModel):
    """대상자 목록 한 행 — MLCM_501 ❷"""

    user_id: uuid.UUID
    name: str
    email: str
    risk_level: Literal["NORMAL", "CAUTION", "CRITICAL"] | None
    risk_score: Decimal | None
    emotion_code: str | None
    evaluated_at: datetime | None


class EmergencyEvent(BaseModel):
    """위기 사건 이력 — MLCM_501 ❹ · MLCM_510 5단계

    별도 테이블을 만들지 않는다. EMOTION_RISK_SCORES 의 risk_level='CRITICAL'
    행이 곧 판정 이력이다.
    """

    score_id: uuid.UUID
    user_id: uuid.UUID
    name: str
    emotion_code: str
    emotion_score: Decimal
    risk_score: Decimal
    model_version: str
    evaluated_at: datetime


class SyncFailure(BaseModel):
    """미수신 재시도 실패 — NFR-DV-002 ④ 관리자 알림

    별도 알림 테이블을 만들지 않는다. DEVICE_HEALTH_CONNECTIONS 의
    sync_status='RETRY_FAILED' 행이 곧 알림 대상 목록이다 — 위기 사건
    이력이 EMOTION_RISK_SCORES 를 그대로 쓰는 것과 같은 방식이다.
    """

    connection_id: uuid.UUID
    user_id: uuid.UUID
    name: str
    device_name: str | None
    last_synced_at: datetime | None
    nudged_at: datetime | None
