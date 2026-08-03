# -*- coding: utf-8 -*-
"""문서 정합성 검사 — 사람이 세지 말고 이걸 돌리세요

```powershell
python tools/check_docs.py            # 전부
python tools/check_docs.py --only 인용 # 한 검사만
```

## 왜 만들었나

2026.08.03 세션에서 같은 패턴이 반복됐습니다.

    개정 범위    11건 -> 24 -> 26 -> 27
    NFR 측정     통과(무효) -> 미달 -> 통과
    중복 규칙    해결 -> 다른 자리에서 재발

**기계가 검사하는 곳은 재발하지 않았고, 사람이 읽어서 확인한 곳은 전부
재발했습니다.** `test_schema_drift.py`·`persona_label_test.dart` 가 지키는
값은 한 번도 어긋나지 않았는데, 검사 장치가 없던 액션 매핑은 고친 뒤에
또 갈렸습니다.

「다음엔 더 꼼꼼히 보겠습니다」는 해결책이 아닙니다. **세는 일을 사람이
하지 않게 만드는 것**이 해결책입니다.

## 검사 항목

    모델명        LightGBM·LSTM·Autoencoder 가 03 밖에 남아 있는가
    성능목표      F1 0.80 · Accuracy 85 목표가 03 밖에 남아 있는가
    링크          문서 간 마크다운 링크가 실재하는가
    인용          개정안이 인용한 「현재 문장」이 추출본에 실제로 있는가

**「인용」이 핵심입니다.** 개정안이 인용한 원문이 실제와 달랐던 사고가
과거에 있었고(CLAUDE.md), 지금도 사람이 눈으로 대조하고 있습니다.

## 03 만 예외인 이유

03 빅데이터분석정의서는 **「검증했고 채택하지 않았다」는 근거를 담는
문서**입니다. 모델명과 목표 수치가 거기 남아 있어야 나머지 문서에서
지운 이유의 출처가 됩니다.
"""
import argparse
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / 'docs'
EXTRACTED = DOCS / 'extracted'

# 03 은 근거 문서라 예외입니다.
EXEMPT = ('03_',)

FAILED = []


def report(name, problems, detail=''):
    if problems:
        FAILED.append(name)
        print(f'\n✗ {name} — {len(problems)}건')
        if detail:
            print(f'  {detail}')
        for p in problems[:20]:
            print(f'    {p}')
        if len(problems) > 20:
            print(f'    … 외 {len(problems) - 20}건')
    else:
        print(f'✓ {name}')


def extracted_files():
    return [p for p in EXTRACTED.glob('*.txt')
            if not p.name.startswith(EXEMPT)]


# ---------------------------------------------------------------------------

def check_모델명():
    """폐기한 모델 이름이 03 밖에 남아 있는지."""
    pat = re.compile(r'LightGBM|LSTM|Autoencoder', re.IGNORECASE)
    bad = []
    for f in extracted_files():
        for i, line in enumerate(f.read_text(encoding='utf-8').splitlines(), 1):
            if pat.search(line):
                bad.append(f'{f.name}:{i}  {line.strip()[:70]}')
    report('모델명', bad,
           '03 은 근거 문서라 예외입니다. 나머지에서는 전부 빠져야 합니다.')


def check_성능목표():
    """달성하지 못한 목표 수치가 03 밖에 남아 있는지."""
    pats = [
        re.compile(r'F1[- ]?Score\s*0\.80'),
        re.compile(r'F1-score\)?\s*80'),
        re.compile(r'정확도\s*\(?Accuracy\)?\s*85'),
        re.compile(r'Accuracy\s*85'),
        re.compile(r'85%\s*위험도\s*분류'),
    ]
    bad = []
    for f in extracted_files():
        for i, line in enumerate(f.read_text(encoding='utf-8').splitlines(), 1):
            if any(p.search(line) for p in pats):
                bad.append(f'{f.name}:{i}  {line.strip()[:70]}')
    report('성능목표', bad,
           '03 이 「도달하지 못해 채택하지 않음」으로 기록한 수치입니다.')


def check_링크():
    """문서 간 마크다운 링크가 실재하는지."""
    bad = []
    targets = list(DOCS.rglob('*.md')) + list(ROOT.glob('*.md'))
    for f in targets:
        base = f.parent
        for m in re.finditer(r'\]\(([^)#]+\.md)(?:#[^)]*)?\)', f.read_text(encoding='utf-8')):
            link = m.group(1)
            if link.startswith(('http://', 'https://')):
                continue
            if not (base / link).resolve().exists():
                rel = f.relative_to(ROOT)
                bad.append(f'{rel} -> {link}')
    report('링크', bad, '가리키는 파일이 없습니다. 합치거나 지운 뒤 남은 참조입니다.')


# ---------------------------------------------------------------------------

def _norm(s: str) -> str:
    """대조용 정규화.

    ⚠ 추출본은 **셀 폭에 맞춰 줄이 갈립니다.** 「앱에서 최소 15분 / 간격
      전송」처럼 한 문장이 두 줄로 쪼개집니다. 그래서 공백을 전부 지우고
      비교합니다. 실제로 grep 0건인데 반영돼 있던 사례가 두 번 있었습니다.
    """
    s = unicodedata.normalize('NFKC', s)
    s = s.replace('“', '"').replace('”', '"').replace('’', "'").replace('‘', "'")
    return re.sub(r'\s+', '', s)


def _strip_md(s: str) -> str:
    """개정안 표기를 벗겨 원문만 남깁니다."""
    s = re.sub(r'\*\*(.+?)\*\*', r'\1', s)
    s = re.sub(r'`(.+?)`', r'\1', s)
    return s


CHUNK = 10          # 대조 단위 글자 수
NEED = 0.85         # 이만큼 맞으면 「있다」로 봅니다


def _found(needle: str, haystacks) -> bool:
    """추출본에 있는지 — **조각 단위**로 봅니다.

    ⚠ **한 문장이 통째로 이어져 있지 않습니다.** 추출본은 표를 왼쪽부터
      훑기 때문에 **옆 칸 텍스트가 문장 중간에 끼어듭니다.**

          - 상시 라이프로그 모니터링
          스마트워치로 상시 모니터링하여 미세한 감정 조기 발견. 정서적 이상 징
          주요 서비스          <- 옆 칸 레이블이 문장을 자릅니다
          후는 본인이 자각하기 어려운 경우가 많아, ...

      그래서 공백만 지워서는 못 찾습니다. 조각으로 잘라 **몇 %가 있는지**로
      판정합니다. 이게 CLAUDE.md 가 「문구 검색으로 판정하지 마세요」라고
      경고한 바로 그 문제입니다.
    """
    if len(needle) < CHUNK:
        return any(needle in h for h in haystacks)
    chunks = [needle[i:i + CHUNK] for i in range(0, len(needle) - CHUNK + 1, CHUNK)]
    hit = sum(1 for c in chunks if any(c in h for h in haystacks))
    return hit / len(chunks) >= NEED


def check_인용():
    """개정안이 인용한 「현재 문장」이 추출본에 실제로 있는지.

    ⚠ **`**현재 문장**` 표시 뒤의 인용 블록만** 봅니다. 개정안은 설명에도
      인용 블록을 쓰기 때문에, 전부 대조하면 자기 글을 원문으로 착각해
      오탐이 쏟아집니다.

    이 검사가 필요한 이유 — **개정안이 인용한 원문이 실제와 달랐던 사고가
    과거에 있었습니다**(CLAUDE.md). 인용이 틀리면 엉뚱한 곳을 고칩니다.
    """
    plan = DOCS / '결정' / '기획서_개정안.md'
    if not plan.exists():
        report('인용', [], '개정안 없음 — 건너뜁니다')
        return

    haystacks = [_norm(f.read_text(encoding='utf-8'))
                 for f in EXTRACTED.glob('*.txt')]
    if not haystacks:
        report('인용', ['docs/extracted 가 비어 있습니다'])
        return

    lines = plan.read_text(encoding='utf-8').splitlines()
    bad = []
    checked = 0
    i = 0
    while i < len(lines):
        if '**현재 문장**' not in lines[i]:
            i += 1
            continue
        # 다음 인용 블록을 통째로 모읍니다. 한 문장이 여러 줄로 적혀 있습니다.
        j = i + 1
        while j < len(lines) and not lines[j].strip().startswith('> '):
            if lines[j].strip() and not lines[j].startswith('('):
                break
            j += 1
        block = []
        while j < len(lines) and lines[j].strip().startswith('> '):
            block.append(lines[j].strip()[2:].strip())
            j += 1
        i = j

        # ⚠ **블록을 통째로 잇고 한 번만 대조합니다.** 줄 단위로 보면 개정안이
        #   폭에 맞춰 접어놓은 자리에서 문장이 잘려 있는 그대로 찾게 됩니다.
        joined = ' '.join(block)
        # 「…」 는 제가 줄인 표시입니다. 앞뒤가 잘려 있으므로 대조 대상이 아닙니다.
        parts = [p for p in re.split(r'…|\.\.\.', joined) if len(_norm(p)) >= 20]
        for quote in parts:
            quote = _strip_md(quote).strip()
            checked += 1
            if not _found(_norm(quote), haystacks):
                bad.append(quote[:60])

    report('인용', bad,
           f'{checked}건 대조. 못 찾은 것은 원문이 바뀌었거나 인용이 부정확합니다.')


# ---------------------------------------------------------------------------

def _run(cmd, cwd, pat):
    """테스트를 돌려 건수를 뽑습니다.

    ⚠ **`shutil.which` 로 실행 파일을 찾습니다.** Windows 에서 `flutter`·`npm`
      은 `.bat`/`.cmd` 라 `shell=False` 로는 못 찾습니다.
    """
    import shutil
    import subprocess
    exe = shutil.which(cmd[0])
    if not exe:
        return None, f'{cmd[0]} 을(를) PATH 에서 찾지 못했습니다'
    try:
        r = subprocess.run([exe] + cmd[1:], cwd=ROOT / cwd, capture_output=True,
                           text=True, timeout=900, errors='replace')
    except Exception as e:
        return None, str(e)
    out = (r.stdout or '') + (r.stderr or '')
    m = re.findall(pat, out)
    return (int(m[-1]) if m else None), out[-200:]


def check_테스트건수():
    """문서가 주장하는 회귀 테스트 건수가 실제와 같은지.

    ⚠ **느립니다**(3~5분). `--with-tests` 를 줘야 돕니다.

    이 검사가 필요한 이유 — `SESSION-HANDOFF.md` 에 「213건」이라 적혀 있었는데
    내역 합(59+15+126+14)은 **214** 였습니다. 아무도 눈치채지 못했고, 그
    사이 backend 는 59에서 77로 늘었습니다. **손으로 적은 숫자는 적는 순간부터
    틀리기 시작합니다.**
    """
    suites = [
        ('backend', ['python', '-m', 'pytest', '-q'], 'backend', r'(\d+) passed'),
        ('AI', ['python', '-m', 'pytest', '-q'], 'ai/server', r'(\d+) passed'),
        ('앱', ['flutter', 'test'], 'frontend/app', r'\+(\d+): All tests passed'),
        ('관리자 웹', ['npm', 'test', '--silent'], 'frontend/admin', r'pass (\d+)'),
    ]
    counts, bad = {}, []
    for name, cmd, cwd, pat in suites:
        n, tail = _run(cmd, cwd, pat)
        if n is None:
            bad.append(f'{name}: 건수를 읽지 못했습니다 — {tail.strip()[:80]}')
        else:
            counts[name] = n

    detail = ' · '.join(f'{k} {v}' for k, v in counts.items())
    hand = DOCS / 'SESSION-HANDOFF.md'
    claimed = re.search(r'회귀 테스트 \| \*\*(\d+)건', hand.read_text(encoding='utf-8'))
    if claimed and len(counts) == len(suites):
        total = sum(counts.values())
        if int(claimed.group(1)) != total:
            bad.append(f'SESSION-HANDOFF 는 {claimed.group(1)}건 · 실제 {total}건 ({detail})')
    elif not claimed:
        bad.append('SESSION-HANDOFF 에서 회귀 테스트 건수를 못 찾았습니다')

    report('테스트건수', bad, '실제: ' + (detail or '측정 실패'))


CHECKS = {
    '모델명': check_모델명,
    '성능목표': check_성능목표,
    '링크': check_링크,
    '인용': check_인용,
}
SLOW = {'테스트건수': check_테스트건수}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', choices=list(CHECKS) + list(SLOW))
    ap.add_argument('--with-tests', action='store_true',
                    help='테스트를 실제로 돌려 건수를 대조합니다 (느림)')
    args = ap.parse_args()

    todo = dict(CHECKS)
    if args.with_tests or args.only in SLOW:
        todo.update(SLOW)

    print('문서 정합성 검사')
    print('=' * 60)
    for name, fn in todo.items():
        if args.only and name != args.only:
            continue
        fn()

    if not (args.with_tests or args.only):
        print('\n  (테스트 건수 대조는 --with-tests 로 함께 돌립니다)')

    print('\n' + '=' * 60)
    if FAILED:
        print(f'✗ {len(FAILED)}개 항목 실패: {", ".join(FAILED)}')
        print('\n⚠ 개정이 끝났다고 말하기 전에 이게 전부 통과해야 합니다.')
        return 1
    print('✓ 전부 통과')
    return 0


if __name__ == '__main__':
    sys.exit(main())
