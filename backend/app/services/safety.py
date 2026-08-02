"""PII 마스킹 · 1차 키워드 위기 필터.

두 기능 모두 **백엔드 내부에서만 동작**한다. 외부 API 에 의존하지 않으므로
OpenAI 장애 시에도 살아 있다 — NFR-DV-003 이 요구하는 fallback 의 근거다.
"""

import json
import re
from functools import lru_cache
from pathlib import Path

_KEYWORD_FILE = Path(__file__).resolve().parent.parent / "data" / "crisis_keywords.json"


# --------------------------------------------------------------------------
# PII 마스킹 — NFR-DE-002
# --------------------------------------------------------------------------
# 대화 저장 시 성명·전화번호·주소 등 개인식별정보를 [MASK] 로 치환한다.
# 마스킹은 저장 시점에 서버가 수행하고 클라이언트는 원문을 그대로 보낸다.
#
# ⚠ 정규식으로 한국어 성명을 일반적으로 잡는 것은 불가능하다. 여기서는
#   기계적으로 식별 가능한 패턴만 처리하고, 이름은 "OOO 님" 같은 호칭 패턴만
#   보수적으로 잡는다. 완전한 비식별화가 아니라 위험 완화 조치다.
_PII_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"01[016789][-.\s]?\d{3,4}[-.\s]?\d{4}"), "[MASK:전화]"),
    (re.compile(r"0\d{1,2}[-.\s]\d{3,4}[-.\s]\d{4}"), "[MASK:전화]"),
    (re.compile(r"\d{6}[-\s]?[1-4]\d{6}"), "[MASK:주민번호]"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "[MASK:이메일]"),
    (re.compile(r"\d{1,3}(-\d{1,3})?번지"), "[MASK:주소]"),
    (re.compile(r"[가-힣]+(시|도)\s*[가-힣]+(구|군|시)\s*[가-힣0-9]+(동|로|길)"), "[MASK:주소]"),
]


def mask_pii(text: str) -> str:
    for pattern, repl in _PII_PATTERNS:
        text = pattern.sub(repl, text)
    return text


# --------------------------------------------------------------------------
# 1차 키워드 필터 — 03-B
# --------------------------------------------------------------------------

# ⚠ 사전은 "죽고 싶" 처럼 띄어쓰기가 들어간 형태로 적혀 있는데, 실제 사용자는
#   "죽고싶다" 처럼 붙여 쓴다. 원문 그대로 비교하면 **공백 하나에 필터가 통째로
#   뚫린다** — 평가셋 200건에서 실제로 확인된 결함이다.
#
#   그래서 사전과 입력에서 **공백만** 지우고 비교한다. 구두점은 남긴다.
#   구두점까지 지우면 "그만두고. 싶은" 같은 문장 경계를 넘어 매칭돼 오탐이 는다.
#   U+200B~200D · U+2060 · U+FEFF 는 눈에 안 보이는 문자다. 복사·붙여넣기로
#   섞여 들어오면 공백처럼 필터를 뚫으므로 같이 지운다.
_WHITESPACE = re.compile(r"[\s\u200b-\u200d\u2060\ufeff]+")


def _squash(text: str) -> str:
    return _WHITESPACE.sub("", text)


@lru_cache(maxsize=1)
def _keywords() -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """(원본 키워드, 공백 제거형) 쌍. 원본은 matched 로 돌려주기 위해 남긴다."""
    data = json.loads(_KEYWORD_FILE.read_text(encoding="utf-8"))
    return (
        [(k, _squash(k)) for k in data.get("high", [])],
        [(k, _squash(k)) for k in data.get("medium", [])],
    )


def keyword_scan(text: str) -> dict:
    """키워드 매칭 결과.

    반환값의 level 은 '판정'이 아니라 '신호 강도'다. 최종 위험도는
    2차 LLM 문맥 분석까지 거쳐 결정된다.
    """
    high, medium = _keywords()
    # 공백을 지운 쪽에서만 비교한다. 원문 매칭은 이쪽에 모두 포함되므로
    # 따로 볼 필요가 없다 (공백을 지워도 부분 문자열 관계는 유지된다).
    squashed = _squash(text)
    hits_high = [k for k, s in high if s in squashed]
    hits_medium = [k for k, s in medium if s in squashed]

    if hits_high:
        level = "HIGH"
    elif hits_medium:
        level = "MEDIUM"
    else:
        level = "NONE"

    return {
        "level": level,
        "matched": hits_high + hits_medium,
    }
