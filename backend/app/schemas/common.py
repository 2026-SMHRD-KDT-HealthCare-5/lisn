"""스키마 공용 타입."""

from typing import Annotated

from pydantic import AfterValidator, Field

# --------------------------------------------------------------------------
# 비밀번호 — bcrypt 72바이트 한계
# --------------------------------------------------------------------------
# ⚠ bcrypt 는 **72바이트**를 넘는 입력을 거부한다(bcrypt 5.x 는 ValueError).
#   `Field(max_length=64)` 는 **글자 수**를 세므로 한글 25자(75바이트)가 그대로
#   통과해 해시 단계에서 터졌다 — 사용자에게는 500 으로 보인다. 한국어 서비스라
#   실제로 밟을 수 있는 경로다(2026.08.02 확인).
#
#   **잘라서 저장하지 않는다.** 조용히 자르면 사용자가 입력한 문자열과 실제
#   비밀번호가 달라져, 다른 기기에서 같은 값을 넣어도 로그인이 되는 것처럼
#   보이거나 안 되는 것처럼 보이는 혼란이 생긴다. 여기서 막고 422 로 돌려준다.
BCRYPT_MAX_BYTES = 72


def _fits_bcrypt(v: str) -> str:
    n = len(v.encode())
    if n > BCRYPT_MAX_BYTES:
        raise ValueError(
            f"비밀번호가 너무 깁니다. 한글은 한 글자가 3바이트라 "
            f"{BCRYPT_MAX_BYTES}바이트를 넘을 수 없습니다(입력 {n}바이트)"
        )
    return v


#: **새로 정하는** 비밀번호에만 쓴다.
#:
#: ⚠ 로그인·탈퇴·비밀번호 변경의 **현재 비밀번호**에는 붙이지 않는다.
#:   그쪽은 `verify_password` 가 bcrypt 의 ValueError 를 잡아 False 로
#:   떨어뜨리므로 이미 안전하고, 여기에 422 를 붙이면 **입력 형식만으로
#:   응답이 갈려** 계정 존재 여부 탐색에 쓸 수 있는 단서를 준다.
NewPassword = Annotated[
    str,
    Field(min_length=8, max_length=64),
    AfterValidator(_fits_bcrypt),
]
