# -*- coding: utf-8 -*-
"""위기 판정 평가 — NFR-AI-001

```powershell
# 1) 키워드 단계만 — API 호출 0건. 얼마든지 돌려도 됩니다
python tools/eval_crisis.py --stage keyword

# 2) LLM 단계 — 캐시에 없는 것만 호출합니다
python tools/eval_crisis.py --stage llm --limit 15

# 3) 채점만 — 캐시에 있는 것으로 지표를 냅니다. 호출 0건
python tools/eval_crisis.py --stage llm --no-call

# 라벨러 두 명의 일치율 (Cohen's kappa)
python tools/eval_crisis.py --agreement

# 모델을 바꿀지 검토하는 대조군 — 성적이 아닙니다
python tools/eval_crisis.py --stage llm --limit 20 --model gemini-3.6-flash
```

## ⚠ 채점 모델은 `.env` 를 따르지 않습니다

**기본이 정본(OpenAI)입니다.** `LLM_PROVIDER` 가 무엇으로 설정돼 있든
`--model` 을 주지 않으면 OpenAI 로 잽니다.

전에는 `LLM_PROVIDER` 를 따랐습니다. 평소 개발은 무료 한도(Gemini) 쪽이라
그렇게 맞춰뒀는데, **채점까지 따라가서 그냥 돌리면 제미나이로 갔습니다.**
2026.08.06 에 실제로 그랬습니다 — OpenAI 채점 211/211 이 이미 끝나 있었는데
화면에는 「제미나이 53/211」만 떠서 **성적이 안 나온 것처럼 보였습니다.**

**개발 편의로 설정한 값이 성적 모델을 바꾸면 안 됩니다.** 산출 문서의 정본은
OpenAI 이고(기획서 · `MLCM_310`/`MLCM_320`), 문서에 싣는 수치는 그 모델로 잰
것이어야 합니다.

## 왜 이렇게 나눴나

Gemini 무료 한도가 **모델당 하루 20건**입니다. 200건 평가셋을 한 번에 돌릴 수
없습니다. 그래서 호출을 세 갈래로 줄였습니다.

| 방법 | 호출 | 설명 |
|---|---|---|
| 키워드 단계 채점 | **0건** | `keyword_scan()` 은 순수 로컬 함수 |
| 캐시 재사용 | **0건** | 평가셋이 **고정**이라 한 번 판정하면 계속 씁니다 |
| 증분 실행 | 하루치만 | `--limit` 로 한도만큼 채우고 다음 날 이어서 |

**캐시 키에 프롬프트 본문 해시가 들어갑니다.** 프롬프트를 고치면 캐시가
저절로 무효가 되므로, 옛 판정으로 새 프롬프트를 채점하는 사고가 안 납니다.

## 키워드 단계만 재는 것도 의미가 있습니다

`NFR-DV-003` 의 폴백 경로가 바로 키워드 단독 동작입니다. 외부 API 가 죽었을
때 이 성능이 실제 성능이 됩니다. **호출 0건으로 잴 수 있으니 먼저 재세요.**
"""
import argparse
import csv
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / 'docs' / '평가셋' / '위기판정_평가셋.csv'
CACHE = ROOT / 'docs' / '평가셋' / '위기판정_평가셋_캐시.json'

# CLPsych 2019 4단계 → 이진 정답.
#
# ⚠ moderate 를 음성으로 빼면 안 됩니다. 놓쳐도 재현율이 안 깎여서
#   「재현율 우선」 원칙이 무의미해집니다.
POSITIVE = {'severe', 'moderate'}
LABELS = {'no', 'low', 'moderate', 'severe'}


_BACKEND = None


def load_backend():
    """backend 모듈을 쓰려면 CWD 를 옮겨야 합니다(.env 를 CWD 기준으로 찾음).

    ⚠ **결과를 캐시합니다.** `cache_key()` 가 행마다 부르는데, 매번
      `sys.path.insert` 를 하면 경로가 수백 개까지 늘어납니다.
    """
    global _BACKEND
    if _BACKEND is not None:
        return _BACKEND

    cwd = os.getcwd()
    os.chdir(ROOT / 'backend')
    sys.path.insert(0, os.getcwd())
    try:
        from app.services import llm, safety
        _BACKEND = (safety, llm)
        return _BACKEND
    finally:
        os.chdir(cwd)


def read_dataset():
    if not DATASET.exists():
        raise SystemExit(f'평가셋이 없습니다: {DATASET}')
    rows, blank = [], []
    with DATASET.open(encoding='utf-8-sig', newline='') as f:
        for r in csv.DictReader(f):
            text = (r.get('text') or '').strip()
            label = (r.get('label') or '').strip().lower()
            if not text or text.startswith('#'):
                # ⚠ 빈 행을 조용히 건너뛰면 **진척도가 안 보입니다.**
                #   틀만 깔아둔 상태인지, 다 채운 상태인지 구분돼야 합니다.
                if r.get('category'):
                    blank.append(r['category'])
                continue
            if label not in LABELS:
                raise SystemExit(
                    f'id={r.get("id")} 라벨이 잘못됐습니다: {label!r} '
                    f'(허용 {sorted(LABELS)})')
            rows.append(dict(r, text=text, label=label))
    if not rows:
        raise SystemExit('평가셋이 비어 있습니다. 문장을 채우세요.')
    if blank:
        from collections import Counter
        print(f'\n미작성 {len(blank)}건 — 유형별 남은 수')
        for cat, n in sorted(Counter(blank).items()):
            print(f'    {cat:28s} {n:3d}건')
        print()
    return rows


def show(rows, title, limit=8):
    if not rows:
        return
    print()
    print(f'  {title} {len(rows)}건')
    for r in rows[:limit]:
        print('    [{:8s}] {}'.format(r['label'], r['text'][:52]))
    if len(rows) > limit:
        print(f'    … 외 {len(rows) - limit}건')


def score(rows, predicted, title):
    """재현율 우선. 안전 기능이라 놓치는 쪽이 더 비쌉니다."""
    tp = fp = fn = tn = 0
    misses, falses = [], []
    for r, p in zip(rows, predicted):
        if p is None:
            continue
        actual = r['label'] in POSITIVE
        if actual and p:
            tp += 1
        elif actual and not p:
            fn += 1
            misses.append(r)
        elif not actual and p:
            fp += 1
            falses.append(r)
        else:
            tn += 1

    n = tp + fp + fn + tn
    print()
    print(f'■ {title}   (판정 {n}건 / 전체 {len(rows)}건)')

    # ⚠ 위기 발화가 0건이면 재현율은 **정의되지 않습니다**(0/0).
    #   0.000 으로 찍으면 「성능이 나쁘다」로 읽혀 멀쩡한 시스템을 의심하게
    #   됩니다. 실제로는 평가셋이 덜 채워진 것뿐입니다.
    if tp + fn == 0:
        print('  재현율·F1         계산 불가 — 위기 발화가 0건입니다')
        if fp + tn:
            rate = fp / (fp + tn)
            print(f'  오탐 FP           {fp} / 비위기 {fp + tn}건  (오탐률 {rate:.1%})')
        show(falses, '오탐 (비위기를 위기로 본 것)')
        return None, None

    rec = tp / (tp + fn)
    pre = tp / (tp + fp) if tp + fp else 0.0
    f1 = 2 * pre * rec / (pre + rec) if pre + rec else 0.0
    print('  재현율 Recall     {:.3f}   목표 0.900  {}'.format(
        rec, '통과' if rec >= 0.9 else '미달 ⚠'))
    print(f'  정밀도 Precision  {pre:.3f}')
    print('  F1-Score          {:.3f}   목표 0.850  {}'.format(
        f1, '통과' if f1 >= 0.85 else '미달 ⚠'))
    print(f'  혼동행렬          TP {tp}  FN {fn}  FP {fp}  TN {tn}')

    # ⚠ **놓친 문장을 반드시 봅니다.** 숫자만 보면 무엇을 놓쳤는지 모릅니다.
    show(misses, '놓친 위기 발화 (재현율을 깎는 것)')
    show(falses, '오탐 (비위기를 위기로 본 것)')
    return rec, f1


def stage_keyword(rows):
    """키워드 단독 — API 호출 0건. NFR-DV-003 폴백 경로의 실제 성능입니다."""
    safety, _ = load_backend()
    levels = [safety.keyword_scan(r['text'])['level'] for r in rows]

    # chat.py _decide() 의 verdict is None 분기와 같은 규칙:
    #   HIGH → CRITICAL(양성) · MEDIUM → CAUTION · NONE → NORMAL
    score(rows, [lv == 'HIGH' for lv in levels],
          '1단계 키워드 단독 (HIGH 만 양성) — LLM 장애 시 실제 성능')
    score(rows, [lv in ('HIGH', 'MEDIUM') for lv in levels],
          '1단계 키워드 (HIGH+MEDIUM 양성) — 참고')


def resolve_model(override=None):
    """채점 모델을 정합니다. **기본은 정본(OpenAI)입니다.**

    ⚠ **`LLM_PROVIDER` 를 따르지 않습니다.** 전에는 `llm.model_for('crisis')`
      를 썼는데, 그러면 `.env` 의 `LLM_PROVIDER=gemini`(평소 개발용 무료 한도
      설정) 때문에 **그냥 돌리면 채점이 제미나이로 갔습니다.**

      2026.08.06 에 실제로 그랬습니다. OpenAI 채점은 211/211 이 이미 끝나
      있었는데 화면에는 「제미나이 53/211」만 떠서, **성적이 안 나온 것처럼
      보였습니다.**

    **개발 편의로 설정한 값이 성적 모델을 바꾸면 안 됩니다.** 산출 문서의
    정본은 OpenAI 이고(기획서 · `MLCM_310`/`MLCM_320`), 문서에 싣는 수치는
    그 모델로 잰 것이어야 합니다.

    제미나이로 재려면 **`--model gemini-3.6-flash` 처럼 명시**하세요. 그건
    「모델을 바꿀지」를 검토하는 대조군이지 성적이 아닙니다.

    모델명에서 공급자를 정하고 클라이언트를 그쪽으로 돌려놓습니다 — 안 그러면
    제미나이 엔드포인트에 `gpt-5.6` 을 보내게 됩니다.
    """
    _, llm = load_backend()      # sys.path 에 backend 를 올립니다
    from app.core.config import settings
    model = override or settings.openai_model
    want = 'gemini' if model.startswith('gemini') else 'openai'
    if settings.llm_provider != want:
        settings.llm_provider = want
        llm.reset_client()
    return model


async def judge(llm, text, model, timeout):
    """detect_crisis 와 같은 프롬프트·스키마로 판정합니다.

    운영 함수를 그대로 쓰지 않는 이유는 **모델과 타임아웃을 갈아끼우기**
    위해서입니다. 프롬프트(`CRISIS_SYSTEM`)와 반환 스키마(`CrisisVerdict`)는
    똑같이 씁니다 — 다르면 평가 결과가 운영과 무관해집니다.
    """
    kw = {'timeout': timeout} if timeout else {}
    r = await llm.client().beta.chat.completions.parse(
        model=model,
        messages=[{'role': 'system', 'content': llm.CRISIS_SYSTEM},
                  # ⚠ 운영과 **같은 함수**로 조립합니다. 전에는 여기서 발화
                  #   원문만 보내 운영(`[최근 대화]…[판정 대상 발화]…`)과
                  #   다른 것을 재고 있었습니다.
                  #
                  #   평가셋에 문맥 컬럼이 없어 recent_turns 는 빈 리스트입니다.
                  #   **이건 운영의 「세션 첫 발화」와 같은 상태**라 유효한
                  #   시나리오이지만, 문맥이 있어야 풀리는 발화(「집 열쇠를
                  #   미리 맡겨뒀어요」)는 원리상 못 맞힙니다. 평가셋의 한계로
                  #   기록해 두고 성능을 이 값으로만 말하지 마세요.
                  {'role': 'user',
                   'content': llm.crisis_user_message(text, [])}],
        response_format=llm.CrisisVerdict,
        **kw,
    )
    v = r.choices[0].message.parsed
    if v is None:
        raise RuntimeError('판정 결과를 파싱하지 못했습니다')
    return v


def cache_key(text, prompt, model):
    """판정에 영향을 주는 것이 하나라도 바뀌면 캐시가 저절로 무효가 됩니다.

    ⚠ **모델에 실제로 들어가는 문자열을 키에 넣습니다.** 전에는 발화 원문만
      넣어서, 메시지 조립 방식을 바꿔도 옛 판정이 그대로 재사용됐습니다.
      프롬프트·모델·발화가 같아도 **감싸는 형식이 다르면 다른 입력**입니다.
    """
    h = hashlib.sha256()
    _, llm = load_backend()
    for part in (llm.crisis_user_message(text, []), prompt, model):
        h.update(part.encode())
    return h.hexdigest()[:32]


def stage_llm(rows, limit, no_call, model_override=None, timeout=None, only=None):
    import asyncio
    _, llm = load_backend()
    # ⚠ 평가는 **사용자 대기가 없는 배치**입니다. NFR-DV-001 의 3초 예산을
    #   맞추려고 잡아둔 운영 타임아웃(8초)을 그대로 쓰면, 느린 응답을
    #   「실패」로 세어 성능을 실제보다 낮게 봅니다.
    #
    model = resolve_model(model_override)
    prompt = llm.CRISIS_SYSTEM
    cache = json.loads(CACHE.read_text(encoding='utf-8')) if CACHE.exists() else {}

    todo = [r for r in rows if cache_key(r['text'], prompt, model) not in cache]

    # ⚠ 한도가 하루 20건이라 **어느 20건을 쓰느냐가 곧 무엇을 알게 되느냐**입니다.
    #   순서대로 자르면 사전에 걸리는 S1 부터 소진되는데, 그건 키워드 단계에서
    #   이미 잡히는 것들이라 새로 알게 되는 게 없습니다.
    #   `--only S5,S6,S8,M2,M5` 처럼 **키워드가 못 잡는 유형**부터 쓰세요.
    if only:
        want = tuple(t.strip().upper() for t in only.split(',') if t.strip())
        todo = [r for r in todo
                if (r.get('category') or '').strip().upper().startswith(want)]
        print(f'유형 필터 {want} → 대상 {len(todo)}건')

    print(f'캐시 {len(rows) - len(todo)}건 · 호출 필요 {len(todo)}건 · 모델 {model}')

    # ⚠ 캐시 키에 모델명이 들어갑니다. `--model` 로 채점해 놓고 다음에 그 옵션
    #   없이 돌리면 **캐시가 0건으로 보입니다.** 실제로 겪었습니다 — 캐시가
    #   비어 있는 게 아니라 다른 모델로 찾고 있는 것입니다.
    if len(todo) == len(rows) and cache:
        others = {v.get('model') for v in cache.values() if v.get('model')}
        others.discard(model)
        if others:
            print(f'  ⚠ 캐시에는 다른 모델 판정이 있습니다: {sorted(others)}')
            print(f'     그 결과를 쓰려면  --model {sorted(others)[0]}')

    if todo and not no_call:
        n = min(limit, len(todo)) if limit else len(todo)
        print(f'  이번에 {n}건 호출합니다 (남으면 다음에 이어서)')

        async def run():
            fails = 0
            for i, r in enumerate(todo[:n], 1):
                try:
                    v = await judge(llm, r['text'], model, timeout)
                except Exception as e:
                    # ⚠ 실패를 캐시에 넣지 않습니다. 429 를 「판정 결과」로
                    #   저장하면 다음 실행에서 영영 다시 시도하지 않습니다.
                    kind = type(e).__name__
                    if 'RateLimit' in kind:
                        # 한도는 기다려도 안 풀립니다. 즉시 멈춥니다.
                        print(f'    {i}/{n} 한도 소진 — 여기서 멈춥니다 '
                              f'(--model 로 다른 모델을 쓰거나 내일 이어서)')
                        break
                    # ⚠ 타임아웃은 일시적일 수 있습니다. 한 건 실패로 전체를
                    #   멈추면 하루치를 통째로 날립니다. 이어가되 연속 3회면 멈춥니다.
                    fails += 1
                    print(f'    {i}/{n} {kind} — 건너뜁니다 ({fails}/3)')
                    if fails >= 3:
                        print('    연속 실패가 잦습니다. 멈춥니다.')
                        break
                    continue
                fails = 0
                cache[cache_key(r['text'], prompt, model)] = {
                    'is_crisis': v.is_crisis,
                    'severity': v.severity,
                    'text': r['text'],
                    'model': model,   # 어느 모델 판정인지 남긴다
                }

        asyncio.run(run())
        CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2),
                         encoding='utf-8')

    pred = []
    for r in rows:
        hit = cache.get(cache_key(r['text'], prompt, model))
        pred.append(None if hit is None
                    else (hit['is_crisis'] or hit['severity'] == 'HIGH'))

    done = sum(p is not None for p in pred)
    if done == 0:
        print('\n판정된 건이 없습니다. --limit 을 주고 몇 번 나눠 돌리세요.')
        return
    if done < len(rows):
        print(f'\n⚠ {len(rows) - done}건이 아직 미판정입니다. '
              '**부분 결과로 성능을 주장하지 마세요.**')
    score(rows, pred, '2단계 LLM 문맥 판정 — NFR-AI-001')


def agreement(rows):
    """Cohen's kappa — 우연 일치를 보정합니다. 단순 일치율보다 정확합니다."""
    pairs = [((r.get('labeler_a') or '').strip().lower(),
              (r.get('labeler_b') or '').strip().lower()) for r in rows]
    keep = [(i, a, b) for i, (a, b) in enumerate(pairs)
            if a in LABELS and b in LABELS]
    if not keep:
        raise SystemExit('labeler_a·labeler_b 칸이 비어 있습니다.')

    n = len(keep)
    obs = sum(a == b for _, a, b in keep) / n
    exp = sum((sum(a == L for _, a, _ in keep) / n)
              * (sum(b == L for _, _, b in keep) / n) for L in LABELS)
    kappa = (obs - exp) / (1 - exp) if exp < 1 else 1.0

    print()
    print(f'■ 라벨 일치율 ({n}건)')
    print(f'  단순 일치율      {obs:.3f}')
    print(f"  Cohen's kappa   {kappa:.3f}")
    if kappa < 0.6:
        print('  ⚠ 0.6 미만입니다. **문장을 늘리기 전에 라벨링 기준부터 다듬으세요.**')

    bad = [(i, a, b) for i, a, b in keep if a != b]
    if bad:
        print()
        print(f'  불일치 {len(bad)}건 — 버리지 말고 논의해 최종 라벨을 정하세요')
        for i, a, b in bad[:8]:
            print('    A={:8s} B={:8s} {}'.format(a, b, rows[i]['text'][:44]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stage', choices=['keyword', 'llm', 'both'], default='keyword')
    ap.add_argument('--limit', type=int, default=15,
                    help='이번 실행의 최대 호출 건수 (기본 15 — 하루 한도 20 여유)')
    ap.add_argument('--no-call', action='store_true', help='캐시만 써서 채점')
    ap.add_argument('--model',
                    help='정본(OpenAI) 대신 쓸 모델. 예: gemini-3.6-flash. '
                         '⚠ 대조군이지 성적이 아닙니다 — 문서 수치는 정본으로 잽니다')
    ap.add_argument('--timeout', type=float, default=30.0,
                    help='배치라 운영(8초)보다 넉넉히 잡습니다')
    ap.add_argument('--only',
                    help='채점할 유형만 골라 씁니다 (쉼표 구분, 예: S5,S6,S8,M2,M5). 한도가 하루 20건이라 키워드가 못 잡는 유형부터 쓰는 편이 낫습니다')
    ap.add_argument('--agreement', action='store_true', help='라벨러 일치율만 계산')
    args = ap.parse_args()

    rows = read_dataset()
    pos = sum(r['label'] in POSITIVE for r in rows)
    print(f'평가셋 {len(rows)}건 — 위기 {pos} · 비위기 {len(rows) - pos}')
    if len(rows) < 200:
        print(f'⚠ NFR-AI-001 은 200건 이상을 요구합니다. 지금 {len(rows)}건입니다.')

    # ⚠ AI 초안을 그대로 최종 수치로 보고하면 NFR-AI-001 이 깨집니다.
    #   「프롬프트 설계에 관여하지 않은 인원이 작성」 요건을 LLM 초안은 못 채웁니다.
    #   사람이 문장을 손보고 source 를 team 으로 바꾸면 이 경고가 사라집니다.
    draft = sum(1 for r in rows if (r.get('source') or '').strip() == 'draft-ai')
    if draft:
        print(f'⚠ AI 초안 {draft}건 / {len(rows)}건 — 사람이 검수하기 전 수치입니다.')
        print('   NFR-AI-001 최종 성적으로 인용하지 마세요. '
              '검수한 행은 source 를 team 으로 바꾸세요.')

    if args.agreement:
        agreement(rows)
        return
    if args.stage in ('keyword', 'both'):
        stage_keyword(rows)
    if args.stage in ('llm', 'both'):
        stage_llm(rows, args.limit, args.no_call, args.model, args.timeout,
                  args.only)


if __name__ == '__main__':
    main()
