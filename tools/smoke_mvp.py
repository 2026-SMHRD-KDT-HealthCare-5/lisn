# -*- coding: utf-8 -*-
"""MVP 관통 점검 — 수집 → 분석 → 케어 → 관제

```powershell
# 백엔드 8000 · AI 서버 8001 이 떠 있어야 합니다
python tools/smoke_mvp.py
python tools/smoke_mvp.py --skip-llm    # LLM 한도를 아낍니다
```

## 200 이 아니라 **값**을 봅니다

`bench_nfr.py` 는 속도를 재고, 이 스크립트는 **흐름이 실제로 이어지는지**를
봅니다. 200 만 확인하면 「빈 배열을 정상 응답으로 돌려주는」 상태를 통과로
칩니다. 그래서 각 단계마다 **다음 단계가 쓸 값이 실제로 들어 있는지**
확인합니다.

예를 들어 라이프로그 조회가 200 이어도 `steps` 가 전부 `null` 이면
분석이 돌 수 없습니다. 그건 실패로 봐야 합니다.
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request

BASE = 'http://127.0.0.1:8000/api/v1'
AI = 'http://127.0.0.1:8001'

PASS, FAIL, WARN = [], [], []


def call(method, url, body=None, token=None, timeout=40):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('Accept', 'application/json')
    if data:
        req.add_header('Content-Type', 'application/json')
    if token:
        req.add_header('Authorization', f'Bearer {token}')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw, status = r.read(), r.status
    except urllib.error.HTTPError as e:
        raw, status = e.read(), e.code
    except Exception as e:
        return 0, {'error': str(e)}
    try:
        return status, json.loads(raw) if raw else {}
    except Exception:
        return status, {}


def check(name, ok, detail=''):
    bucket = PASS if ok is True else (WARN if ok is None else FAIL)
    mark = {True: '✅', None: '⚠', False: '❌'}[ok]
    print(f'  {mark} {name:44s} {detail}')
    bucket.append(name)
    return ok is True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--skip-llm', action='store_true')
    ap.add_argument('--email', default='demo.crisis@lisn-test.example')
    ap.add_argument('--password', default='rldnfdla')
    args = ap.parse_args()

    print('MVP 관통 점검 — 수집 → 분석 → 케어 → 관제')
    print('=' * 74)

    # ── 0. 서비스 ────────────────────────────────────────────────
    print('\n[0] 서비스')
    st, _ = call('GET', 'http://127.0.0.1:8000/docs')
    if not check('백엔드 8000', st == 200, f'HTTP {st}'):
        print('\n백엔드가 없으면 나머지를 못 봅니다. 먼저 띄우세요.')
        return
    st, body = call('GET', f'{AI}/health')
    check('AI 서버 8001', st == 200, f"model_version={body.get('model_version', '?')}")

    # ── 1. 인증 ──────────────────────────────────────────────────
    print('\n[1] 인증 — MLCM_100')
    st, body = call('POST', f'{BASE}/auth/login',
                    {'email': args.email, 'password': args.password})
    token = body.get('access_token')
    if not check('로그인 → JWT 발급', bool(token), f'HTTP {st}'):
        print('\n로그인이 안 되면 나머지를 못 봅니다.')
        print('  db/seed_demo_persona.sql 을 넣었는지 확인하세요.')
        return
    st, me = call('GET', f'{BASE}/users/me', token=token)
    check('내 정보 조회', st == 200 and bool(me.get('user_id')),
          f"{me.get('name', '?')} · role={me.get('role', '?')}")
    uid = me.get('user_id')

    # ⚠ 관리자 계정에는 라이프로그가 없는 것이 **정상**입니다. 관제만 봅니다.
    #   이걸 실패로 잡으면 「관리자로 돌렸더니 7건 실패」 같은 오해가 납니다.
    admin_only = me.get('role') == 'ADMIN'
    if admin_only:
        print('\n  ℹ 관리자 계정입니다 — 사용자 데이터 절은 건너뛰고 관제만 봅니다.')

    if admin_only:
        run_admin(token)
        return

    # ── 2. 수집 ──────────────────────────────────────────────────
    print('\n[2] 수집 — MLCM_200')
    st, conns = call('GET', f'{BASE}/devices/connections', token=token)
    check('기기 연동 조회', st == 200, f'{len(conns) if isinstance(conns, list) else 0}건')

    st, logs = call('GET', f'{BASE}/lifelog?limit=100', token=token)
    n = len(logs) if isinstance(logs, list) else 0
    # ⚠ 200 만 보면 안 됩니다. 값이 비어 있으면 분석이 못 돕니다.
    has_steps = any(r.get('steps') is not None for r in logs) if n else False
    has_sleep = any(r.get('total_sleep_min') is not None for r in logs) if n else False
    check('라이프로그 조회', st == 200 and n > 0, f'{n}건')
    check('  └ 걸음·수면 실측치 존재', has_steps and has_sleep,
          f"steps={'O' if has_steps else 'X'} sleep={'O' if has_sleep else 'X'}")

    st, body_comp = call('GET', f'{BASE}/body-composition?limit=30', token=token)
    m = len(body_comp) if isinstance(body_comp, list) else 0
    check('체성분 조회', st == 200,
          f'{m}건' + ('  (선택 항목이라 0건도 정상)' if m == 0 else ''))

    # ── 3. 분석 ──────────────────────────────────────────────────
    print('\n[3] 분석 — MLCM_210')
    st, verdict = call('POST', f'{AI}/internal/analyze/lifelog', {'user_id': uid})
    ok = st == 200 and verdict.get('emotion_code')
    check('AI 정서 위험도 판정', bool(ok),
          f"{verdict.get('emotion_code', '')} / {verdict.get('risk_level', '')}"
          f" score={verdict.get('risk_score', '')}" if ok else f'HTTP {st}')
    if ok and verdict.get('model_version', '').startswith('rule-'):
        check('  └ 판정 근거', None,
              f"{verdict['model_version']} — **모델 아님, 규칙 자리표시자**")

    # ── 4. 케어 ──────────────────────────────────────────────────
    print('\n[4] 케어 — MLCM_400 · MLCM_310')
    st, home = call('GET', f'{BASE}/home', token=token)
    emo = home.get('emotion_today') or {}
    action = home.get('action')
    check('홈 대시보드', st == 200 and bool(action),
          f"action={action} · {emo.get('emotion_name', '?')}"
          f"/{emo.get('risk_level', '?')}")
    check('  └ 오늘 지표 표시', bool((home.get('lifelog_summary') or {}).get('steps')),
          str(home.get('lifelog_summary') or {})[:44])
    check('  └ AI 한줄 요약', bool(home.get('ai_summary')),
          (home.get('ai_summary') or '')[:36])

    st, recs = call('GET', f'{BASE}/contents/recommendations', token=token)
    k = len(recs) if isinstance(recs, list) else 0
    # ⚠ CRITICAL 이면 추천을 **중단하는 것이 정상**입니다 — MLCM_510 2단계.
    if action == 'EMERGENCY':
        check('위기 시 콘텐츠 추천 중단', k == 0,
              f'{k}건' + ('  (0건이어야 정상)' if k == 0 else '  ⚠ 위기인데 추천이 나옵니다'))
    else:
        check('힐링 콘텐츠 추천', st == 200 and k > 0, f'{k}건')

    st, rep = call('GET', f'{BASE}/reports', token=token)
    pts = len(rep.get('emotion_trend', [])) if isinstance(rep, dict) else 0
    dist = rep.get('distribution') or {}
    check('정서 리포트', st == 200 and pts > 0,
          f"추이 {pts}포인트 · 분포 {dist}")

    # ── 5. 대화 ──────────────────────────────────────────────────
    print('\n[5] 대화 — MLCM_310 · MLCM_320')
    if args.skip_llm:
        check('챗봇 (건너뜀)', None, '--skip-llm')
    else:
        st, s = call('POST', f'{BASE}/chat/sessions',
                     {'persona_type': 'FRIEND'}, token=token)
        sid = s.get('session_id')
        check('세션 시작 + 인사말', bool(sid) and bool(s.get('greeting')),
              (s.get('greeting') or '')[:34])

        if sid:
            t = time.perf_counter()
            st, r = call('POST', f'{BASE}/chat/sessions/{sid}/messages',
                         {'content': '오늘 회사에서 신경 쓰이는 일이 많았어요.'},
                         token=token, timeout=60)
            ms = (time.perf_counter() - t) * 1000
            reply = r.get('reply')
            act = (r.get('risk') or {}).get('action')
            src = (r.get('risk') or {}).get('source')
            # ⚠ 폴백 문구도 reply 로 내려옵니다. source 로 갈라야 합니다.
            check('일반 대화 응답', bool(reply), f'{ms:.0f}ms · action={act}')
            check('  └ LLM 판정 경로', src == 'LLM' or None,
                  f'source={src}' + ('  (KEYWORD = LLM 실패·폴백)'
                                     if src == 'KEYWORD' else ''))

            st, r = call('POST', f'{BASE}/chat/sessions/{sid}/messages',
                         {'content': '요즘 정말 죽고 싶다는 생각이 들어요.'},
                         token=token, timeout=60)
            act = (r.get('risk') or {}).get('action')
            check('위기 발화 → 긴급 전환', act == 'EMERGENCY',
                  f"action={act} level={(r.get('risk') or {}).get('level')}")
            check('  └ 위기 시 일반 응답 차단', r.get('reply') is None,
                  'reply=None' if r.get('reply') is None else '⚠ 응답이 함께 왔습니다')

            call('PATCH', f'{BASE}/chat/sessions/{sid}/end', {}, token=token)
            st, hist = call('GET', f'{BASE}/chat/sessions', token=token)
            check('대화 기록 조회', st == 200 and len(hist) > 0,
                  f'{len(hist) if isinstance(hist, list) else 0}건')

    # ── 6. 접근 통제 ──────────────────────────────────────────────
    print('\n[6] 관제 접근 통제 — MLCM_501')
    st, _ = call('GET', f'{BASE}/admin/dashboard', token=token)
    # ⚠ 403 이 **정상**입니다. 일반 계정이 관제를 보이면 그게 사고입니다.
    check('일반 계정 관제 차단', st == 403, f'HTTP {st}  (403 이어야 정상)')

    summary()


def run_admin(token):
    """관제 경로 — MLCM_501. 관리자 계정으로만 봅니다."""
    print('\n[관제] MLCM_501')
    st, dash = call('GET', f'{BASE}/admin/dashboard', token=token)
    check('❶ 위험도 분포', st == 200, str(dash.get('distribution') or dash)[:50])

    st, users = call('GET', f'{BASE}/admin/users?limit=5', token=token)
    items = users if isinstance(users, list) else (users or {}).get('items', [])
    check('❹ 대상자 목록', st == 200 and len(items) > 0, f'{len(items)}건')

    st, found = call('GET', f'{BASE}/admin/users?q=demo&limit=5', token=token)
    f2 = found if isinstance(found, list) else (found or {}).get('items', [])
    check('❷~❸ 이름·이메일 검색', st == 200, f'q=demo → {len(f2)}건')

    if items:
        tid = items[0].get('user_id')
        st, rep = call('GET', f'{BASE}/admin/users/{tid}/report', token=token)
        pts = len((rep or {}).get('emotion_trend', []))
        check('❺ 대상자 상세', st == 200, f'추이 {pts}포인트')

    st, ev = call('GET', f'{BASE}/admin/emergency-events?limit=5', token=token)
    m = len(ev) if isinstance(ev, list) else len((ev or {}).get('items', []))
    check('❻ 위기 사건 이력', st == 200, f'{m}건')

    summary()


def summary():
    # ── 정리 ─────────────────────────────────────────────────────
    # ── 정리 ─────────────────────────────────────────────────────
    print('\n' + '=' * 74)
    print(f'통과 {len(PASS)} · 주의 {len(WARN)} · 실패 {len(FAIL)}')
    if FAIL:
        print('\n실패한 항목')
        for x in FAIL:
            print(f'  ❌ {x}')
    if WARN:
        print('\n주의가 필요한 항목')
        for x in WARN:
            print(f'  ⚠ {x}')
    sys.exit(1 if FAIL else 0)


if __name__ == '__main__':
    main()
