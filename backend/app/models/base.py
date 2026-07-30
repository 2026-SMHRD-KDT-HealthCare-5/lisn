"""SQLAlchemy 선언 기반 클래스.

db/schema.sql 이 스키마의 정본이다. 이 모델들은 그 DDL 을 파이썬에서 다루기
위한 매핑일 뿐이며, 여기서 스키마를 새로 정의하지 않는다.

- 테이블은 schema.sql 로 만든다. Base.metadata.create_all() 을 쓰지 않는다.
- alembic 도 쓰지 않는다. 정본이 둘이 되면 반드시 어긋난다.
  스키마를 바꿀 때는 schema.sql 을 고치고 DB 를 다시 만든다.
  근거: docs/review/API설계_사전결정.md 4절
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
