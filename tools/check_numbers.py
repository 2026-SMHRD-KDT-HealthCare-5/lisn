# -*- coding: utf-8 -*-
"""산출물 5종에 흩어진 같은 값이 서로 맞는지 봅니다

```powershell
python tools/check_numbers.py
```

## 왜 만들었나

**같은 숫자가 여러 문서에 흩어져 있고, 한 곳만 고치면 조용히 갈립니다.**
2026.08.06 하루에만 세 번 겪었습니다.

    API 개수        문서 30 · 실제 33
    테이블 수        CLAUDE.md 8 · schema.sql 9
    평가셋 규모      한 칸 안에서 「211건」과 「총 200건 이상」이 동시에

마지막 것이 특히 나빴습니다 — **같은 셀 안에서 모순**이었는데도 사람 눈으로
넉 달을 못 봤습니다.

## 무엇을 보나

**정본이 코드·데이터에 있는 값**은 거기서 읽어 문서와 대조합니다.
정본이 문서에만 있는 값은 **문서끼리** 대조합니다.

⚠ **문서에 안 나오는 것은 통과입니다.** 모든 문서가 모든 값을 적을 필요는
  없습니다. 잡는 것은 **서로 다르게 적힌 경우**뿐입니다.

⚠ **여기 없는 값은 검사되지 않습니다.** 새 수치가 문서에 들어가면
  `CHECKS` 에 넣으세요. 안 넣으면 검사한 줄 알고 넘어갑니다.
"""
import io
import re
import sys
import pathlib

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

ROOT = pathlib.Path(__file__).resolve().parent.parent
EX = ROOT / 'docs' / 'extracted'

DOCS = ['프로젝트_기획서', '요구사항정의서', '빅데이터분석정의서',
        '데이터베이스요구사항분석서', '테이블명세서']

# 이름 → (정규식, 기대값, 설명)
#
# 기대값이 None 이면 **문서끼리 서로 같은지**만 봅니다.
CHECKS = [
    ('평가셋 규모',   r'고정 평가셋 (\d+)건',        '211', '위기 판정 평가셋'),
    # ⚠ 「비위기 발화 100건」 안의 「발화 100건」이 걸립니다. 앞을 막습니다.
    ('위기 발화',     r'(?<!비)위기 발화 (\d+)건',    '111', ''),
    ('비위기 발화',   r'비위기 발화 (\d+)건',        '100', ''),
    # ⚠ 키워드 단독 재현율 0.081 과 구분해야 합니다. 앞 문구로 묶습니다.
    ('재현율 실측',   r'문맥 판정의 재현율은 (0\.\d+)', '0.793', '2단계'),
    ('키워드 재현율', r'키워드 단독 판정의 재현율은 (0\.\d+)', '0.081', 'NFR-DV-003 경로'),
    ('정밀도 실측',   r'정밀도는 (0\.\d+)',          '0.967', ''),
    ('F1 실측',       r'F1-Score 는 (0\.\d+)',       '0.871', ''),
    ('재현율 목표',   r'재현율\(Recall\) (\d+)%',    '90', ''),
    ('F1 목표',       r'F1-Score (0\.\d+) 이상',     '0.85', ''),
    ('수집 주기',     r'최소 (\d+)분',               '15', '앱 → 백엔드 전송'),
    # ⚠ 「몇 초 이내」가 여럿입니다. **다른 요구를 한 줄로 묶으면 안 됩니다.**
    #   3초 = 긴급 UI 노출(NFR-DV-001·TS-001) · 5초 = AI 분석·전처리(기획서)
    #   · 1.5초 = 판정 지연(빅데이터분석정의서). 각각 따로 봅니다.
    ('긴급 UI 지연',  r'UI 노출까지 지연시간 (\d+)초|UI가 (\d+)초 이내', '3', 'NFR-TS-001'),
    ('대화 응답 예산', r'응답 지연시간을 (\d+)초 이내',  '3', 'NFR-DV-001'),
    ('미수신 감지',   r'(\d+)시간 이상 갱신되지',     '3', 'NFR-DV-002'),
]


def load():
    out = {}
    for d in DOCS:
        p = EX / f'{d}_귀기울임.txt'
        if p.exists():
            out[d] = re.sub(r'\s+', ' ', p.read_text(encoding='utf-8'))
    return out


def schema_tables():
    """`schema.sql` 이 정본입니다."""
    sql = (ROOT / 'db' / 'schema.sql').read_text(encoding='utf-8')
    return len(re.findall(r'CREATE TABLE (\w+)', sql))


def main():
    texts = load()
    bad = []

    for name, pat, expect, note in CHECKS:
        found = {}
        for d, t in texts.items():
            # ⚠ 그룹이 둘 이상이면 findall 이 **튜플**을 줍니다. 폅니다.
            vals = set()
            for hit in re.findall(pat, t):
                if isinstance(hit, tuple):
                    vals |= {x for x in hit if x}
                else:
                    vals.add(hit)
            if vals:
                found[d] = vals
        if not found:
            continue
        allv = set().union(*found.values())
        if expect and allv - {expect}:
            where = ' · '.join(f'{d}={"/".join(sorted(v))}' for d, v in found.items())
            bad.append(f'{name} — 기대 {expect} · 실제 {where}')
        elif not expect and len(allv) > 1:
            where = ' · '.join(f'{d}={"/".join(sorted(v))}' for d, v in found.items())
            bad.append(f'{name} — 문서마다 다름: {where}')
        else:
            print(f'  ✓ {name:12} {expect or "/".join(allv)}'
                  f'  ({len(found)}개 문서){"  " + note if note else ""}')

    # 테이블 수 — schema.sql 이 정본
    n = schema_tables()
    tbl = {}
    for d, t in texts.items():
        for m in re.findall(r'테이블 (\d+)개|(\d+)개 테이블', t):
            v = m[0] or m[1]
            tbl.setdefault(d, set()).add(v)
    wrong = {d: v for d, v in tbl.items() if v - {str(n)}}
    if wrong:
        bad.append(f'테이블 수 — schema.sql {n}개 · 문서 '
                   + ' · '.join(f'{d}={"/".join(sorted(v))}' for d, v in wrong.items()))
    else:
        print(f'  ✓ {"테이블 수":12} {n}  (schema.sql 정본)')

    print()
    if bad:
        print(f'✗ 어긋난 값 {len(bad)}건')
        for b in bad:
            print(f'    {b}')
        return 1
    print('✓ 문서 간 수치가 전부 맞습니다')
    return 0


if __name__ == '__main__':
    sys.exit(main())
