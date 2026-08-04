"""`db/schema.sql` ↔ SQLAlchemy 모델 정합 — DB 없이 돕니다.

이 프로젝트의 전제는 **`db/schema.sql` 이 스키마 정본**이고 모델은 그 DDL 의
파이썬 매핑일 뿐이라는 것입니다. `create_all()` 도 alembic 도 쓰지 않아서,
둘이 어긋나도 **아무것도 알려주지 않습니다.** 컬럼을 한쪽에만 추가하면 운영
중에 `UndefinedColumnError` 로 처음 드러납니다.

여기서 컬럼 이름 집합만 비교합니다. 타입까지 보려면 방언 매핑 표가 필요한데,
그 표 자체가 또 하나의 정본이 되어 버립니다. **이름이 맞으면 대부분의 드리프트가
잡히고, 타입은 데이터베이스요구사항분석서·테이블명세서 대조에서 봅니다.**

    cd backend
    python -m pytest tests/test_schema_drift.py -q
"""

import re
from pathlib import Path

import pytest

from app.models import base  # noqa: F401  — 메타데이터 등록용
from app.models import chat, emotion, lifelog, user  # noqa: F401

SCHEMA_SQL = Path(__file__).resolve().parents[2] / "db" / "schema.sql"

# 컬럼 정의가 아닌 줄. 테이블 레벨 제약은 컬럼이 아니다.
_NOT_A_COLUMN = re.compile(
    r"^\s*(CONSTRAINT|PRIMARY\s+KEY|UNIQUE|CHECK|FOREIGN\s+KEY)\b", re.IGNORECASE
)


def parse_schema_sql() -> dict[str, set[str]]:
    """CREATE TABLE 블록에서 테이블별 컬럼 이름을 뽑는다."""
    text = SCHEMA_SQL.read_text(encoding="utf-8")
    tables: dict[str, set[str]] = {}

    for match in re.finditer(
        r"CREATE\s+TABLE\s+(\w+)\s*\((.*?)\n\);", text, re.DOTALL | re.IGNORECASE
    ):
        name = match.group(1).lower()
        columns: set[str] = set()
        for raw in match.group(2).splitlines():
            line = raw.split("--")[0].strip()  # 주석에 근거가 병기돼 있다
            if not line or _NOT_A_COLUMN.match(line):
                continue
            first = line.split()[0]
            if first.isidentifier():
                columns.add(first.lower())
        tables[name] = columns

    return tables


SCHEMA_TABLES = parse_schema_sql()
MODEL_TABLES = {
    name.lower(): {c.name.lower() for c in table.columns}
    for name, table in base.Base.metadata.tables.items()
}


def test_schema_sql_을_읽었다():
    """정규식이 헛돌면 뒤 테스트가 전부 조용히 통과한다."""
    assert len(SCHEMA_TABLES) == 8, f"파싱된 테이블: {sorted(SCHEMA_TABLES)}"
    assert SCHEMA_TABLES["lifelog_metrics"], "컬럼 파싱 실패"


def test_모델이_정본에_없는_테이블을_만들지_않는다():
    extra = set(MODEL_TABLES) - set(SCHEMA_TABLES)
    assert not extra, (
        f"모델에만 있는 테이블: {sorted(extra)}. "
        "schema.sql 이 정본입니다 — 먼저 DDL 에 추가하세요."
    )


@pytest.mark.parametrize("table", sorted(MODEL_TABLES))
def test_모델_컬럼이_정본_DDL_과_같다(table):
    """모델에만 있는 컬럼은 즉시 런타임 오류가 되고,

    DDL 에만 있는 컬럼은 모델이 못 읽는 데이터가 된다. 둘 다 막는다.
    """
    schema_cols = SCHEMA_TABLES[table]
    model_cols = MODEL_TABLES[table]

    only_model = model_cols - schema_cols
    only_schema = schema_cols - model_cols

    assert not only_model, (
        f"[{table}] 모델에만 있음: {sorted(only_model)} — "
        "DB 에 없는 컬럼이라 조회 즉시 UndefinedColumnError 가 납니다."
    )
    assert not only_schema, (
        f"[{table}] schema.sql 에만 있음: {sorted(only_schema)} — "
        "모델이 이 컬럼을 못 읽습니다."
    )
