"""SQLAlchemy 선언 기반 클래스.

db/schema.sql 이 스키마의 정본이다. 이 모델들은 그 DDL 을 파이썬에서 다루기
위한 매핑일 뿐이며, 여기서 스키마를 새로 정의하지 않는다.

- 테이블은 schema.sql 로 만든다. Base.metadata.create_all() 을 쓰지 않는다.
- alembic 도 쓰지 않는다. 정본이 둘이 되면 반드시 어긋난다.
  스키마를 바꿀 때는 schema.sql 을 고치고 DB 를 다시 만든다.
  근거: docs/결정/API설계_사전결정.md 4절
"""

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# 데이터베이스요구사항분석서: 모든 날짜/시간 컬럼은 TIMESTAMPTZ 로 통일한다.
#
# ⚠ Mapped[datetime] 만 쓰면 SQLAlchemy 가 timezone=False 로 추론해
#   TIMESTAMP WITHOUT TIME ZONE 을 생성한다. 그 상태로 tz-aware 값을 넣으면
#   asyncpg 가 "can't subtract offset-naive and offset-aware datetimes" 로 죽는다.
#   시각 컬럼에는 반드시 이 타입을 명시할 것.
TimestampTZ = DateTime(timezone=True)
