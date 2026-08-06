# -*- coding: utf-8 -*-
"""산출물 5종에서 **한 표 칸 안에** 같은 문장이 두 번 나오는 곳을 찾습니다.

NFR-AI-001 이 이것으로 걸렸습니다 — 개정 문안을 앞에 붙이면서 옛 문안을
안 지워, 한 칸 안에 「211건」과 「총 200건 이상」이 같이 있었습니다.

## 왜 본문이 아니라 표 덤프를 보나

본문(쪽 레이아웃)은 **쪽 넘김에 머리글(「요구사항 정의서」)이 끼어들어**
문장이 깨집니다. 실제로 본문 기준으로 짰더니 **아는 사고를 못 잡았습니다.**
표 덤프는 한 칸이 한 줄로 나오므로 온전합니다.

## 왜 문서 안만 보나

문서 **사이** 중복은 정상입니다 — 같은 결정을 여러 문서가 참조하는 것이
오히려 맞습니다.
"""
import io
import re
import sys
import pathlib
import collections

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DOCS = ['프로젝트_기획서', '요구사항정의서', '빅데이터분석정의서',
        '데이터베이스요구사항분석서', '테이블명세서']
MIN = 30          # 이보다 짧으면 우연히 겹칩니다


def cells(text):
    """표 덤프의 각 칸."""
    for line in text.splitlines():
        if ' | ' not in line:
            continue
        for c in line.split(' | '):
            c = re.sub(r'\s+', ' ', c).strip()
            if len(c) >= MIN * 2:
                yield c


def dup_in(cell):
    """한 칸 안에서 두 번 이상 나오는 문장."""
    parts = [s.strip() for s in re.split(r'(?<=다\.)\s|(?<=함\.)\s|(?<=음\.)\s', cell)]
    c = collections.Counter(s for s in parts if len(s) >= MIN)
    return [(s, n) for s, n in c.items() if n > 1]


def run(root=pathlib.Path('.')):
    total = 0
    for d in DOCS:
        p = root / 'docs' / 'extracted' / f'{d}_귀기울임.txt'
        if not p.exists():
            print(f'⚠ {d} 없음')
            continue
        found = []
        for cell in cells(p.read_text(encoding='utf-8')):
            for s, n in dup_in(cell):
                found.append((s, n))
        seen = set()
        uniq = [(s, n) for s, n in found if not (s in seen or seen.add(s))]
        total += len(uniq)
        mark = '✅' if not uniq else '⚠'
        print(f'{mark} {d}  중복 {len(uniq)}건')
        for s, n in sorted(uniq, key=lambda x: -len(x[0]))[:5]:
            print(f'    {n}회 · {len(s)}자 — {s[:96]}…')
    print(f'\n합계 {total}건')
    return total


if __name__ == '__main__':
    run(pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path('.'))
