# -*- coding: utf-8 -*-
"""자막이 컷마다 같은 규칙으로 그려지는지 검사합니다.

⚠ **왜 필요한가** — 2026.08.22 에 관제 컷(05)만 번호와 제목을 한 덩어리로
  묶어 **남색 42px 가운데 정렬**로 그리고 있었습니다. 앱 컷은 번호가
  인디고 30px, 제목이 남색 76px, 전부 x=170 좌측 정렬인데 말입니다.
  한 영상 안에서 컷마다 색도 정렬도 달라 보였고, 사람이 지적해서 알았습니다.

  컷마다 함수를 따로 짜면 이런 어긋남이 **반드시** 생깁니다. 그래서 규칙을
  글로 적어 두고 기계가 대조합니다.

규칙 — 화면 위에 얹는 자막(앱 컷·관제 컷)은 전부 아래를 지킵니다.
  번호  fontsize 30 · NUM_C   · x=170
  제목  fontsize 76 · TITLE_C · x=170
  설명  fontsize 30 · BODY_C  · x=170
y 좌표는 다를 수 있습니다 — 세로 화면은 옆에, 가로 화면은 위에 놓이니까요.

타이틀·마무리 카드(card 함수)는 화면이 없는 전면 카드라 별도 규칙입니다.
"""
import re
import sys
from pathlib import Path

SRC = Path(__file__).with_name("build_video.sh")
RULE = {  # 역할: (fontsize, 색 변수, x)
    "번호": ("30", "NUM_C", "170"),
    "제목": ("76", "TITLE_C", "170"),
    "설명": ("30", "BODY_C", "170"),
}
# 자막 템플릿의 자리표시자 -> 역할
SLOT = {"@NO@": "번호", "@T@": "제목", "@L1@": "설명", "@L2@": "설명", "@L3@": "설명"}
COLORSLOT = {"@I@": "NUM_C", "@N@": "TITLE_C", "@M@": "BODY_C"}

SPEC = re.compile(
    r"drawtext=fontfile=(?P<font>[^:]+):text='?(?P<text>[^':]+)'?:"
    r"fontsize=(?P<size>\d+):fontcolor=(?P<color>[^:]+):x=(?P<x>[^:,\]]+)")


def role_of(text):
    if text in SLOT:
        return SLOT[text]
    if text == "${no}":
        return "번호"
    if text == "${title}":
        return "제목"
    if text in ("${l1}", "${l2}", "${l3}"):
        return "설명"
    return None


def colour_of(raw):
    raw = raw.strip()
    if raw in COLORSLOT:
        return COLORSLOT[raw]
    m = re.fullmatch(r"\$\{?([A-Z_]+)\}?", raw)
    return m.group(1) if m else raw


def main():
    src = SRC.read_text(encoding="utf-8")
    # card() 는 전면 카드라 별도 규칙 — 검사에서 뺍니다
    body = "\n".join(l for l in src.splitlines() if "text='${kicker}'" not in l)
    bad = []
    seen = 0
    for m in SPEC.finditer(body):
        role = role_of(m.group("text"))
        if not role:
            continue
        seen += 1
        want_size, want_color, want_x = RULE[role]
        got = (m.group("size"), colour_of(m.group("color")), m.group("x").strip())
        if got != (want_size, want_color, want_x):
            bad.append((role, m.group("text"), got, (want_size, want_color, want_x)))

    for role, text, got, want in bad:
        print(f"  ✗ {role} ({text})")
        print(f"      지금: fontsize={got[0]} · {got[1]} · x={got[2]}")
        print(f"      규칙: fontsize={want[0]} · {want[1]} · x={want[2]}")
    print()
    if bad:
        print(f"⚠ 자막 규칙을 벗어난 곳 {len(bad)}건 — 컷마다 다르게 보입니다")
        return 1
    print(f"✓ 자막 {seen}곳이 모두 같은 규칙을 씁니다 (번호30 · 제목76 · 설명30 · 전부 x=170)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
