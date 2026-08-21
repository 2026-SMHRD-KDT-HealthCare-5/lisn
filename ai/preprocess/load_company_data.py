"""라라랩스 실데이터 적재 — 받으면 컬럼명만 맞추고 바로 돌립니다.

⚠ **아직 실데이터를 받지 못했습니다** (요청만 해둔 상태, 2026.08.21 작성).
  이 스크립트는 파일이 도착했을 때 지체 없이 쓰려고 미리 짜둔 것입니다.
  아래 `COLUMN_MAP` 의 **왼쪽(원본 헤더명)만** 실제 파일에 맞게 고치면,
  나머지 로직(사용자 연결 · DB 적재 · 검증)은 그대로 돌아갑니다.

## 왜 이 스크립트 하나로 끝나는가

`ai/server/main.py` 의 개인 기준선 이탈 탐지는 `LIFELOG_METRICS` 를
**직접 SELECT** 합니다(main.py:121). 즉 여기서 적재만 끝내면 —

  - AI 추론 서버 판정
  - 앱의 라이프로그·정서 리포트 화면
  - 관리자 관제 대시보드

**전부 별도 연결 없이 그 데이터를 바로 씁니다.** 새 파이프라인을 만들
필요가 없습니다.

## 회원 연결 — 회원번호는 저장하지 않습니다

`01-M①`(2026.07.30 확정)에 따라 데이터베이스요구사항분석서는 "측정 데이터는
UUID 기반 식별자로만 연결"을 규정합니다. **기업 원본의 회원번호를 그대로
저장할 컬럼이 스키마에 없습니다.** 그래서 이 스크립트는:

  1. 회원번호별로 `USERS` 행을 새로 만들거나(이미 있으면) 찾는다
  2. 회원번호 → `user_id` 매핑은 **이 실행 중에만 메모리에 있다**
  3. `--map-out` 을 주면 감사용으로 매핑을 CSV 로 남긴다
     ⚠ **그 파일은 개인정보이므로 절대 커밋하지 않는다** — `.gitignore` 에
       이미 `*_member_map.csv` 패턴을 추가해 뒀다

## 사용법

```powershell
# 1. 먼저 헤더만 확인 (DB 에 아무것도 안 씀)
python ai/preprocess/load_company_data.py --file <경로> --dry-run

# 2. COLUMN_MAP 을 실제 헤더에 맞게 고친 뒤 실제 적재
python ai/preprocess/load_company_data.py --file <경로>

# 3. 감사용 매핑을 남기고 싶으면
python ai/preprocess/load_company_data.py --file <경로> --map-out out/member_map.csv
```

`--dry-run` 은 **실제 파일이 도착하면 제일 먼저 해야 할 일**입니다. 헤더가
예상과 다르면 `COLUMN_MAP` 에 없는 열 이름을 그대로 보여주고 멈춥니다 —
추측해서 적재하지 않습니다.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "backend"))

# ---------------------------------------------------------------------------
# ⚠ 여기부터 TODO — 실제 파일을 받으면 왼쪽(원본 헤더)만 고칩니다.
#
#   지금 적힌 한글 이름은 `docs/진행/작업이력.md` 의 [05-E] 결정과
#   빅데이터분석정의서 「데이터 확보 방안」에 언급된 항목명을 그대로 옮긴
#   추정치입니다 — **실제 파일 헤더와 다를 수 있습니다.** `--dry-run` 으로
#   먼저 실제 헤더 목록을 확인하세요.
# ---------------------------------------------------------------------------

MEMBER_ID_COL = "회원번호"

# 원본 헤더 → LIFELOG_METRICS 컬럼. 값이 None 인 건 원본에 없는 파생값이라
# 로더가 계산합니다(예: sleep_efficiency_pct).
LIFELOG_COLUMN_MAP: dict[str, str] = {
    "걸음수": "steps",
    "이동거리": "distance",
    "소모칼로리": "calories",
    "활동 시작 시간": "activity_start_at",
    "활동 종료 시각": "activity_end_at",
    "총활동 시간": "total_active_min",
    "수면 시작 시각": "sleep_start_at",
    "수면 종료 시각": "sleep_end_at",
    "총수면 시간": "total_sleep_min",
    "깊은수면 시간": "deep_sleep_min",
    "얕은수면 시간": "light_sleep_min",
    "REM수면 시간": "rem_sleep_min",
    "각성 시간": "awake_min",
    "입면 소요 시간": "sleep_onset_min",
    "심박수": "heart_rate",
    "심박변이도": "hrv",
    "측정일시": "collected_at",
}

# 원본 헤더 → BODY_COMPOSITION_METRICS 컬럼.
# ⚠ muscle_mass_kg 등은 Health Connect 수집 경로엔 없지만(PL-26), 기업
#   정제 데이터에는 있습니다 — schema.sql 주석 "기업 데이터와 일치"가 이 뜻.
BODY_COLUMN_MAP: dict[str, str] = {
    "체중": "weight_kg",
    "체수분": "body_water_kg",
    "체지방량": "body_fat_kg",
    "근육량": "muscle_mass_kg",
    "근육량_최소": "muscle_mass_min_kg",
    "근육량_최대": "muscle_mass_max_kg",
    "골격근량": "skeletal_muscle_kg",
    "기초대사량": "bmr_kcal",
    "측정일시": "measured_at",
}


def _read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in (".xlsx", ".xls"):
        return pd.read_excel(path)
    return pd.read_csv(path, encoding="utf-8-sig")  # BOM 대비 — 국내 엑셀 CSV 관행


def _check_columns(df: pd.DataFrame, colmap: dict[str, str], label: str) -> list[str]:
    """매핑에 없는 컬럼을 알려준다. 추측해서 진행하지 않는다.

    ⚠ 라이프로그·체성분이 한 파일에 같이 올 수 있어, "이 매핑엔 없지만
      다른 쪽 매핑엔 있는" 열은 정상입니다 — 진짜 미매핑 열만 알립니다.
    """
    known = set(LIFELOG_COLUMN_MAP) | set(BODY_COLUMN_MAP) | {MEMBER_ID_COL}
    unknown = [c for c in df.columns if c not in known]
    if unknown:
        print(f"⚠ [{label}] 어느 COLUMN_MAP 에도 없는 열: {unknown}")
        print(f"   → 스크립트 상단 LIFELOG_COLUMN_MAP/BODY_COLUMN_MAP 에 추가하거나, 무시해도 되면 넘어가세요.")
    missing = [c for c in colmap if c not in df.columns]
    if missing:
        print(f"ℹ [{label}] 파일에 없는 매핑 대상: {missing} (해당 컬럼은 NULL 로 적재됩니다)")
    return unknown


def _split_lifelog_body(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """한 파일에 라이프로그·체성분이 같이 있을 수도, 따로일 수도 있다.

    두 매핑 중 하나라도 실제 열과 겹치면 그 프레임을 만든다. 파일이
    분리돼 오면(라이프로그 파일 / 체성분 파일 따로) 자연히 한쪽은 빈
    DataFrame 이 된다 — 오류가 아니다.
    """
    lifelog_cols = [c for c in LIFELOG_COLUMN_MAP if c in df.columns]
    body_cols = [c for c in BODY_COLUMN_MAP if c in df.columns]

    lifelog_df = df[[MEMBER_ID_COL, *lifelog_cols]].copy() if lifelog_cols else pd.DataFrame()
    body_df = df[[MEMBER_ID_COL, *body_cols]].copy() if body_cols else pd.DataFrame()
    return lifelog_df, body_df


async def _get_or_create_user(conn, member_id: str, cache: dict[str, uuid.UUID]) -> uuid.UUID:
    if member_id in cache:
        return cache[member_id]

    # 실데이터 사용자는 로그인하지 않으므로 email 은 unique 제약만 채우면
    # 됩니다. 실제 로그인이 필요해지면(예: 관리자가 콘솔에서 확인) 이
    # 이메일로 비밀번호 재설정을 태울 수 있습니다.
    email = f"realdata-{member_id}@lisn-company-import.internal"
    now = datetime.now(timezone.utc)

    user_id = await conn.fetchval(
        """
        INSERT INTO USERS (email, password_hash, name, terms_agreed, terms_agreed_at,
                            sensitive_agreed, sensitive_agreed_at)
        VALUES ($1, $2, $3, TRUE, $4, TRUE, $4)
        ON CONFLICT (email) DO UPDATE SET email = EXCLUDED.email
        RETURNING user_id
        """,
        email,
        # 실데이터 사용자는 로그인 못 하게 막습니다 — bcrypt 가 절대 만들지
        # 않을 고정 문자열이라 verify_password 가 항상 False 를 돌려줍니다.
        "!DISABLED-REALDATA-IMPORT!",
        f"실데이터 참가자 {member_id}",
        now,
    )
    cache[member_id] = user_id
    return user_id


TIMESTAMP_COLUMNS = {
    "activity_start_at", "activity_end_at", "sleep_start_at", "sleep_end_at",
    "collected_at", "measured_at",
}


def _coerce(schema_col: str, value):
    """asyncpg 는 파이썬 네이티브 타입만 받습니다.

    pandas 가 CSV 에서 읽은 값은 문자열·numpy 스칼라라 그대로 넘기면
    TIMESTAMPTZ 컬럼에서 `expected a datetime.date... got 'str'` 로 죽습니다.
    """
    if schema_col in TIMESTAMP_COLUMNS:
        ts = pd.Timestamp(value)
        if ts.tzinfo is None:
            # ⚠ 타임존 표기가 없는 값은 KST 로 간주합니다. 국내 서비스이고
            #   원본이 로컬 시각으로 올 가능성이 높습니다 — 실제 파일을
            #   받으면 이 가정이 맞는지 반드시 확인하세요.
            ts = ts.tz_localize("Asia/Seoul")
        return ts.to_pydatetime()
    if hasattr(value, "item"):
        return value.item()  # numpy 스칼라 → 파이썬 스칼라
    return value


async def load(df_all: pd.DataFrame, db_url: str, map_out: Path | None, dry_run: bool) -> None:
    lifelog_df, body_df = _split_lifelog_body(df_all)

    print(f"라이프로그 대상 행: {len(lifelog_df)}")
    print(f"체성분 대상 행: {len(body_df)}")
    print(f"고유 회원 수: {df_all[MEMBER_ID_COL].nunique()}")

    if dry_run:
        print("\n--dry-run 이라 DB 에 쓰지 않습니다. 위 개수와 열 매핑만 확인하세요.")
        return

    import asyncpg  # 지연 임포트 — dry-run 은 DB 접속 없이도 되게

    conn = await asyncpg.connect(db_url)
    cache: dict[str, uuid.UUID] = {}
    try:
        async with conn.transaction():
            for _, row in lifelog_df.iterrows():
                uid = await _get_or_create_user(conn, str(row[MEMBER_ID_COL]), cache)
                cols = {v: _coerce(v, row[k]) for k, v in LIFELOG_COLUMN_MAP.items() if k in row and pd.notna(row[k])}
                if "collected_at" not in cols:
                    continue  # NOT NULL — 없으면 이 행은 건너뜀
                fields = ", ".join(cols)
                placeholders = ", ".join(f"${i+2}" for i in range(len(cols)))
                await conn.execute(
                    f"""
                    INSERT INTO LIFELOG_METRICS (user_id, {fields})
                    VALUES ($1, {placeholders})
                    ON CONFLICT (user_id, collected_at) DO NOTHING
                    """,
                    uid,
                    *cols.values(),
                )

            for _, row in body_df.iterrows():
                uid = await _get_or_create_user(conn, str(row[MEMBER_ID_COL]), cache)
                cols = {v: _coerce(v, row[k]) for k, v in BODY_COLUMN_MAP.items() if k in row and pd.notna(row[k])}
                if "measured_at" not in cols:
                    continue
                fields = ", ".join(cols)
                placeholders = ", ".join(f"${i+2}" for i in range(len(cols)))
                await conn.execute(
                    f"""
                    INSERT INTO BODY_COMPOSITION_METRICS (user_id, {fields})
                    VALUES ($1, {placeholders})
                    """,
                    uid,
                    *cols.values(),
                )
        print(f"\n적재 완료 — 사용자 {len(cache)}명")
    finally:
        await conn.close()

    if map_out:
        map_out.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(
            [{"회원번호": k, "user_id": str(v)} for k, v in cache.items()]
        ).to_csv(map_out, index=False)
        print(f"매핑 저장(감사용, 커밋 금지): {map_out}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", required=True, type=Path, help="라라랩스 정제 데이터 파일 (CSV/Excel)")
    parser.add_argument("--dry-run", action="store_true", help="DB 에 쓰지 않고 매핑만 확인")
    parser.add_argument("--map-out", type=Path, default=None, help="회원번호↔user_id 매핑을 남길 CSV 경로")
    parser.add_argument(
        "--db-url",
        default="postgresql://postgres:postgres@localhost:5432/lisn",
        help="asyncpg 접속 문자열 (postgresql+asyncpg:// 접두사는 자동으로 벗깁니다)",
    )
    args = parser.parse_args()

    if not args.file.exists():
        raise SystemExit(f"파일이 없습니다: {args.file}")

    df = _read_table(args.file)
    print(f"읽은 행: {len(df)}  열: {list(df.columns)}\n")

    if MEMBER_ID_COL not in df.columns:
        raise SystemExit(
            f"회원 식별 컬럼 '{MEMBER_ID_COL}' 을 찾지 못했습니다. "
            f"스크립트 상단 MEMBER_ID_COL 을 실제 헤더로 고치세요."
        )

    _check_columns(df, LIFELOG_COLUMN_MAP, "LIFELOG")
    _check_columns(df, BODY_COLUMN_MAP, "BODY (파일에 없는 열만 참고 — 미매핑 열 경고는 위에서 이미 봤습니다)")

    db_url = args.db_url.replace("postgresql+asyncpg://", "postgresql://")
    asyncio.run(load(df, db_url, args.map_out, args.dry_run))


if __name__ == "__main__":
    main()
