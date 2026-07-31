"""컬럼 단위 암호화 — AES-256-GCM.

02-F (3) 이 컬럼 암호화 대상을 "유출 시 즉각적 2차 피해가 발생하는 항목"으로
한정했다. 현재 대상은 USERS.phone 하나다.

라이프로그·체성분 측정치는 대상이 아니다. 기간별 집계와 복합 인덱스가
서비스의 핵심 동작이라 컬럼 암호화를 적용하면 기능 자체가 불가능해진다.
그쪽은 전송 구간 보호와 접근통제로 보호한다 — 02-F (6).

※ 암호화 컬럼은 검색·정렬·중복확인이 불가능하다. phone 은 로그인·본인확인에
  쓰이지 않고 SMS 발송 계획도 없어 제약이 실기능에 걸리지 않는다.
  추후 phone 조회가 필요해지면 blind index(HMAC) 를 별도로 둬야 한다.
"""

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings

# GCM 권장 nonce 길이
NONCE_BYTES = 12


def _key() -> bytes:
    raw = settings.encryption_key
    if not raw or raw == "CHANGE_ME":
        raise RuntimeError(
            "ENCRYPTION_KEY 가 설정되지 않았습니다. "
            "backend/.env 에 base64 인코딩된 32바이트 키를 넣으세요."
        )
    key = base64.b64decode(raw)
    if len(key) != 32:
        raise RuntimeError(f"ENCRYPTION_KEY 는 32바이트여야 합니다 (현재 {len(key)})")
    return key


def encrypt(plain: str | None) -> str | None:
    """평문 -> base64(nonce + ciphertext+tag).

    nonce 를 암호문 앞에 붙여 함께 저장한다. 복호화에 필요하고 비밀이 아니다.
    """
    if plain is None or plain == "":
        return None
    nonce = os.urandom(NONCE_BYTES)
    sealed = AESGCM(_key()).encrypt(nonce, plain.encode(), None)
    return base64.b64encode(nonce + sealed).decode()


def decrypt(stored: str | None) -> str | None:
    if stored is None or stored == "":
        return None
    try:
        raw = base64.b64decode(stored, validate=True)
        nonce, sealed = raw[:NONCE_BYTES], raw[NONCE_BYTES:]
        return AESGCM(_key()).decrypt(nonce, sealed, None).decode()
    except Exception as e:
        # 암호화 도입 전에 평문으로 저장된 행이 남아 있으면 여기로 온다.
        # 조용히 원문을 돌려주면 평문 저장이 정상인 것처럼 보이므로 명시적으로 막는다.
        raise RuntimeError(
            "연락처 복호화에 실패했습니다. 암호화 적용 전에 저장된 평문 행이거나 "
            "ENCRYPTION_KEY 가 바뀌었을 수 있습니다."
        ) from e


def generate_key() -> str:
    """운영/개발 키 생성용. 결과를 .env 의 ENCRYPTION_KEY 에 넣는다."""
    return base64.b64encode(os.urandom(32)).decode()
