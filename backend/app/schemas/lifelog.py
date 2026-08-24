"""라이프로그 · 체성분 스키마 — MLCM_200"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

# 15분 간격이면 하루 96건. 전송 실패 누적과 지연을 감안해도 넉넉한 상한.
# 초과분을 서버가 잘라내면 유실이 조용히 생기므로 413 으로 거절한다.
MAX_BATCH = 200


class LifelogItem(BaseModel):
    """앱이 Health Connect 에서 읽어 보내는 한 시점의 측정치."""

    collected_at: datetime

    steps: int | None = Field(default=None, ge=0)
    distance: int | None = Field(default=None, ge=0)
    calories: int | None = Field(default=None, ge=0)

    activity_start_at: datetime | None = None
    activity_end_at: datetime | None = None
    total_active_min: int | None = Field(default=None, ge=0)

    sleep_start_at: datetime | None = None
    sleep_end_at: datetime | None = None
    total_sleep_min: int | None = Field(default=None, ge=0)
    deep_sleep_min: int | None = Field(default=None, ge=0)
    light_sleep_min: int | None = Field(default=None, ge=0)
    rem_sleep_min: int | None = Field(default=None, ge=0)
    awake_min: int | None = Field(default=None, ge=0)
    sleep_onset_min: int | None = Field(default=None, ge=0)
    sleep_efficiency_pct: Decimal | None = Field(default=None, ge=0, le=100)

    heart_rate: int | None = Field(default=None, ge=0)
    hrv: Decimal | None = Field(default=None, ge=0)

    # [05-U] 앱 사용 로그. 특별권한을 승인하지 않은 단말은 전부 None 으로 온다.
    #   ⚠ 패키지명·앱 이름은 받지 않는다 — 집계값 셋뿐이다.
    screen_time_min: int | None = Field(default=None, ge=0)
    night_screen_min: int | None = Field(default=None, ge=0)
    app_session_count: int | None = Field(default=None, ge=0)


class LifelogBatch(BaseModel):
    items: list[LifelogItem] = Field(min_length=1)


class LifelogBatchResult(BaseModel):
    """last_synced_at 은 서버가 확정해 돌려준다.

    앱이 자기 시계로 갱신하면 단말 시간이 틀어졌을 때 그 구간이 영구 유실된다.
    앱은 이 값을 다음 델타 조회의 기준으로 써야 한다.
    """

    accepted: int
    last_synced_at: datetime


class LifelogOut(LifelogItem):
    model_config = {"from_attributes": True}


class BodyCompositionIn(BaseModel):
    measured_at: datetime
    weight_kg: Decimal | None = Field(default=None, ge=0)
    body_water_kg: Decimal | None = Field(default=None, ge=0)
    body_fat_kg: Decimal | None = Field(default=None, ge=0)
    muscle_mass_kg: Decimal | None = Field(default=None, ge=0)
    muscle_mass_min_kg: Decimal | None = Field(default=None, ge=0)
    muscle_mass_max_kg: Decimal | None = Field(default=None, ge=0)
    skeletal_muscle_kg: Decimal | None = Field(default=None, ge=0)
    bmr_kcal: int | None = Field(default=None, ge=0)


class BodyCompositionOut(BodyCompositionIn):
    model_config = {"from_attributes": True}
