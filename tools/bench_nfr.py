# -*- coding: utf-8 -*-
"""성능 요건 실측 — NFR-DV-001 · NFR-TS-001 · NFR-DV-003 · 암복호화

```powershell
# 백엔드(8000)·AI 서버(8001)가 떠 있어야 합니다
python tools/bench_nfr.py
python tools/bench_nfr.py --runs 10          # 반복 횟수
python tools/bench_nfr.py --skip-llm         # LLM 호출 없이 로컬 항목만
```

## 왜 여러 번 재나

LLM 왕복은 편차가 큽니다. **한 번 재고 「3초 통과」라고 쓰면 안 됩니다.**
중앙값과 최댓값을 함께 보고, 최댓값이 예산을 넘으면 통과로 치지 않습니다.

## 측정하지 못하는 것

`NFR-AI-001`(위기 판정 재현율 90%·F1 0.85)은 **고정 평가셋 200건이 있어야**
합니다. 저장소에 없으므로 이 스크립트는 재지 않습니다. 만들기 전에는
성능을 주장할 수 없습니다.
"""
import argparse
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = 'http://127.0.0.1:8000/api/v1'
AI = 'http://127.0.0.1:8001'


def call(method, url, body=None, token=None, timeout=30):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('Accept', 'application/json')
    if data:
        req.add_header('Content-Type', 'application/json')
    if token:
        req.add_header('Authorization', f'Bearer {token}')
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            status = r.status
    except urllib.error.HTTPError as e:
        raw, status = e.read(), e.code
    except Exception as e:
        return (time.perf_counter() - t0) * 1000, 0, {'error': str(e)}
    ms = (time.perf_counter() - t0) * 1000
    try:
        return ms, status, json.loads(raw) if raw else {}
    except Exception:
        return ms, status, {}


def stat(name, samples, budget_ms=None, unit='ms'):
    """중앙값·최댓값을 함께 보고합니다. 최댓값이 예산을 넘으면 통과가 아닙니다."""
    if not samples:
        print(f'  {name:34s} 측정 실패')
        return None
    med = statistics.median(samples)
    mx = max(samples)
    line = f'  {name:34s} 중앙값 {med:8.1f}{unit}  최댓값 {mx:8.1f}{unit}  n={len(samples)}'
    if budget_ms is not None:
        ok = mx <= budget_ms
        line += f'   예산 {budget_ms}{unit}  {"통과" if ok else "초과 ⚠"}'
    print(line)
    return med, mx


# ─────────────────────────────────────────────────────────────
def bench_crypto(runs):
    """AES-256-GCM 컬럼 암복호화 — 02-F(3) · 안건 4"""
    # ⚠ `Settings` 가 `.env` 를 **CWD 기준**으로 찾습니다. backend/ 로 옮겨
    #   불러온 뒤 되돌립니다. 안 그러면 database_url 누락으로 죽습니다.
    import os
    cwd = os.getcwd()
    os.chdir('backend')
    sys.path.insert(0, os.getcwd())
    try:
        from app.core.crypto import decrypt, encrypt
    finally:
        os.chdir(cwd)

    plain = '010-1234-5678'
    enc, dec = [], []
    for _ in range(runs * 20):     # 마이크로벤치라 표본을 넉넉히
        t = time.perf_counter()
        c = encrypt(plain)
        enc.append((time.perf_counter() - t) * 1000)
        t = time.perf_counter()
        assert decrypt(c) == plain
        dec.append((time.perf_counter() - t) * 1000)
    print('\n■ 컬럼 암복호화 (AES-256-GCM)')
    stat('encrypt', enc, 200)
    stat('decrypt', dec, 200)


def login(email, password):
    ms, st, body = call('POST', f'{BASE}/auth/login',
                        {'email': email, 'password': password})
    return body.get('access_token'), ms, st


def bench_api(token, runs):
    print('\n■ 조회 API 응답')
    for name, path in [('홈 대시보드', '/home'),
                       ('라이프로그 30일', '/lifelog?limit=100'),
                       ('정서 리포트', '/reports'),
                       ('체성분', '/body-composition?limit=30')]:
        xs = [call('GET', f'{BASE}{path}', token=token)[0] for _ in range(runs)]
        stat(name, xs)


def bench_ai(user_id, runs):
    print('\n■ AI 추론 서버 (MLCM_210)')
    xs, codes = [], set()
    for _ in range(runs):
        ms, st, _ = call('POST', f'{AI}/internal/analyze/lifelog',
                         {'user_id': user_id})
        xs.append(ms)
        codes.add(st)
    stat('정서 위험도 분석', xs)
    print(f'    응답 코드 {sorted(codes)}'
          f'{"  (422 = 지표 부족. 판정 자체를 끊는 정상 동작)" if 422 in codes else ""}')


# 응답 생성이 실패했을 때 서버가 넣는 문구(llm.FALLBACK_REPLY).
# 여기 걸리면 **LLM 이 돌지 않은 회차**입니다.
_FALLBACK_MARKS = (
    '생각을 정리하는 데 시간이',
    '답변을 준비하는 데 시간이',
)


def bench_chat(token, runs, utterance, label, budget):
    """NFR-DV-001 / NFR-TS-001

    ⚠ **LLM 이 실제로 돌았는지 함께 확인합니다.** 외부 API 가 실패하면 서버는
      즉시 폴백으로 넘어가고, 그 **실패 왕복 시간이 정상 응답보다 훨씬 짧게
      찍힙니다.** 2026.08.03 에 실제로 170ms 가 「예산 3000ms 통과」로 나왔는데
      전부 429(무료 한도 소진)였습니다. **숫자만 보면 구분이 안 됩니다.**

      두 가지로 판별합니다.
        risk.source == 'KEYWORD'  -> 위기 판정 LLM 이 안 돌았다
        reply 가 폴백 문구         -> 응답 생성 LLM 이 안 돌았다

      하나라도 걸리면 수치를 **무효로 표시**합니다. 통과/초과를 적지 않습니다.
    """
    ms, st, s = call('POST', f'{BASE}/chat/sessions', {'persona_type': 'FRIEND'},
                     token=token)
    sid = s.get('session_id')
    if not sid:
        print(f'  {label}: 세션 생성 실패 ({st})')
        return
    xs, actions = [], set()
    kw_only, fallback = 0, 0
    for _ in range(runs):
        ms, st, body = call('POST', f'{BASE}/chat/sessions/{sid}/messages',
                            {'content': utterance}, token=token, timeout=60)
        xs.append(ms)
        risk = body.get('risk') or {}
        actions.add(risk.get('action'))
        if risk.get('source') == 'KEYWORD':
            kw_only += 1
        reply = body.get('reply') or ''
        if any(m in reply for m in _FALLBACK_MARKS):
            fallback += 1

    invalid = kw_only or fallback
    # ⚠ 무효인 회차가 있으면 예산 판정을 아예 내리지 않습니다. 「통과」라고
    #   적어두면 다음 사람이 그 숫자를 근거로 씁니다.
    stat(label, xs, None if invalid else budget)
    print(f'    판정 {sorted(a for a in actions if a)}')

    if invalid:
        print(f'    ⚠ 무효 — LLM 이 돌지 않은 회차가 있습니다 '
              f'(위기판정 폴백 {kw_only}/{runs} · 응답 폴백 {fallback}/{runs})')
        print('      이 수치를 성능 근거로 쓰지 마세요. 서버 로그에서 '
              '429·5xx 를 확인하고 공급자 설정을 점검한 뒤 다시 재세요.')

    call('POST', f'{BASE}/chat/sessions/{sid}/end', {}, token=token)
    return not invalid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runs', type=int, default=5)
    ap.add_argument('--skip-llm', action='store_true')
    ap.add_argument('--email', default='demo.crisis@lisn-test.example')
    ap.add_argument('--password', default='rldnfdla')  # 팀 공용 테스트 비밀번호
    args = ap.parse_args()

    print(f'성능 실측 — 반복 {args.runs}회')
    print('=' * 78)

    bench_crypto(args.runs)

    token, ms, st = login(args.email, args.password)
    if not token:
        print(f'\n⚠ 로그인 실패({st}) — 서버 항목을 건너뜁니다.')
        print('   백엔드가 떠 있는지, 계정이 맞는지 확인하세요.')
        return
    print(f'\n■ 인증\n  {"로그인":34s} {ms:8.1f}ms')

    _, _, me = call('GET', f'{BASE}/users/me', token=token)
    bench_api(token, args.runs)
    if me.get('user_id'):
        bench_ai(me['user_id'], args.runs)

    if args.skip_llm:
        print('\n(--skip-llm 이라 대화 항목을 건너뜁니다)')
        return

    print('\n■ 챗봇 대화 — NFR-DV-001 / NFR-TS-001')
    ok_normal = bench_chat(token, args.runs, '오늘 회사에서 신경 쓰이는 일이 많았어요.',
                           'NFR-DV-001 일반 발화', 3000)
    # high 키워드 '죽고 싶' 이 들어간 발화라야 1차 필터까지 함께 검증됩니다.
    ok_crisis = bench_chat(token, args.runs, '요즘 정말 죽고 싶다는 생각이 들어요.',
                           'NFR-TS-001 위기 발화', 3000)

    print('\n' + '=' * 78)
    print('측정하지 않은 것')
    print('  NFR-AI-001  위기 판정 재현율 90%·F1 0.85 — **평가셋 사람 검수 후 재측정**')
    print('  NFR-DV-002  재시도 30초·3회 — 앱 단위 테스트가 고정 (lifelog_sync_test.dart)')

    if not (ok_normal and ok_crisis):
        # ⚠ 종료코드로도 알립니다. 출력만 보면 ⚠ 를 지나칠 수 있고, 실제로
        #   한 번 지나쳐서 실패 왕복 시간을 「통과」로 문서에 적었습니다.
        print('\n⚠ 이번 실행은 무효입니다. 위 ⚠ 표시를 보세요.')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main() or 0)
