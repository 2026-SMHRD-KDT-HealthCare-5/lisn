# -*- coding: utf-8 -*-
"""발표자료·시연영상 문구를 OpenAI 로 전면 재작성합니다.

기존 naturalize.py 와 다른 점 — 글자만 던지지 않고 **각 문구가 무슨 일을
하는 문구인지**(제목인가 설명인가, 어느 화면 위에 뜨는가, 앞뒤로 무슨 말이
오는가)를 함께 줍니다. 사람이 지적한 실패 유형(주어·목적어 누락, 앞뒤
논리 연결 없음, 프로젝트 용어 안 씀)을 프롬프트에 그대로 넣었습니다.

⚠ 결과를 그대로 적용하지 않습니다. 제안만 받고 사람이 검토합니다.
"""
import json, sys
from pathlib import Path
from urllib import request

ROOT = Path("C:/project/LISN")
KEY = None
for line in (ROOT / "backend" / ".env").read_text(encoding="utf-8").splitlines():
    if line.startswith("OPENAI_API_KEY="):
        KEY = line.split("=", 1)[1].strip()
        break
assert KEY, "OPENAI_API_KEY 를 backend/.env 에서 못 찾았습니다"

SYSTEM = """너는 한국어 발표·영상 카피라이터다. 스타트업 제품 발표에서
직접 말하듯 자연스러운 한국어를 쓴다.

# 제품
「귀기울임(LISN)」 — 스마트워치 라이프로그(수면·활동량·심박)와 챗봇 대화를
같이 보고 정서 위험을 감지하는 정신건강 케어 앱. 위험 신호가 보이면
**사용자가 앱을 열기 전에 시스템이 먼저 알림을 보내 말을 건다.** 이걸
이 프로젝트에서는 「선제 접촉」이라고 부른다. 관리자는 별도 관제 웹에서
전체 대상자의 위험도를 본다.

# 지금 문구들의 문제 (사람이 직접 지적한 것)
1. **주어·목적어가 빠져 있다.** "수면 패턴이 5일째 무너진 것을" 이 아니라
   "**사용자의** 수면 패턴이 5일째 무너진 것을" 이어야 한다. 설명하는
   글인데 누구 얘긴지가 없다.
2. **앞 문장과 뒤 문장이 논리로 안 이어진다.** 앞에서 "알아챕니다"라고
   했으면 뒤에는 "그래서 어떻게 한다"가 와야 한다. 두 문장이 따로 논다.
3. **프로젝트가 쓰는 용어를 안 쓴다.** 「선제 접촉」이라는 말을 문서에서
   쓰는데 영상 자막에서는 안 쓴다. 용어가 있으면 그걸 써야 한다.
4. **번역투다.** 영어를 옮긴 것처럼 어색하다 —
   - 사물이 스스로 하는 것처럼 쓴 수동태 ("앱은 열리지 않습니다")
   - 한국어에서 안 쓰는 동사·조사 결합 ("밀어 올리는 구조", "알림이 닿고")
   - 문장이 명사구로 뚝 끊기는 것
   - 영어 라벨을 그대로 옮긴 제목

# 좋은 예 (사람이 직접 써 준 방향)
나쁨: "수면 패턴이 5일째 무너진 것을 시스템이 먼저 알아챕니다." /
      "알림은 먼저 오고, 첫 마디는 앱 안에서 기다립니다."
좋음: "사용자의 수면 패턴이 5일째 무너진 것을 시스템이 먼저 알아챕니다." /
      "이상 징후가 발견되면 알림으로 먼저 말을 겁니다. 앱을 열면 상태를
       묻는 첫 마디가 준비돼 있습니다."
→ 주어를 넣고, 앞 문장의 「알아챘다」를 뒤 문장이 「그래서 이렇게 한다」로
   받고, 프로젝트 용어(선제 접촉/첫 마디)를 쓴다.

# 반드시 지킬 것
- **숫자를 바꾸지 않는다.** 0.946, 319건, 33개, 2052ms, 3일, 5일째 등 전부 원문 그대로.
- **사실관계를 바꾸지 않는다.** 더 강하게도 약하게도 말하지 않는다.
- **고유명사·기술용어를 바꾸지 않는다** — 귀기울임, LISN, FCM, Health Connect,
  WorkManager, OAuth, CRITICAL, model_version, db/schema.sql, KcBERT 등.
- **길이 제한을 지킨다.** 각 항목의 max_chars 를 넘기지 마라. 고정 상자·
  영상 자막 폭에 들어가야 한다. 넘기면 화면을 침범한다.
- **이미 자연스러우면 그대로 둔다.** 문체만 바꾸려고 고치지 마라.
- 제목(role=title)은 짧고 힘있게. 설명(role=body)은 완결된 문장으로.
- 라벨·표 머리글(role=label)은 명사구가 정상이다. 억지로 문장 만들지 마라.

# 출력
{"items":[{"i":인덱스,"text":"고친 결과","why":"왜 고쳤는지 한 줄"}]}
형태의 JSON 객체 하나. **실제로 고친 항목만** 넣어라. 안 고친 건 빼라."""

items = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
BATCH = 20
MODEL = "gpt-5.4"
results = {}

for start in range(0, len(items), BATCH):
    chunk = items[start:start + BATCH]
    numbered = []
    for j, it in enumerate(chunk):
        row = {"i": start + j}
        row.update(it)
        numbered.append(row)
    body = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": json.dumps(numbered, ensure_ascii=False, indent=1)},
        ],
        "response_format": {"type": "json_object"},
    }).encode("utf-8")
    req = request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body, method="POST",
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
    )
    with request.urlopen(req, timeout=180) as r:
        resp = json.loads(r.read())
    parsed = json.loads(resp["choices"][0]["message"]["content"])
    rows = parsed.get("items", [])
    for row in rows:
        results[row["i"]] = row
    print(f"  배치 {start}~{start+len(chunk)-1} — {len(rows)}건 제안", flush=True)

out = []
for idx, it in enumerate(items):
    r = results.get(idx)
    if not r:
        continue
    new = r["text"]
    if new == it["text"]:
        continue
    rec = dict(it)
    rec["i"] = idx
    rec["original"] = it["text"]
    rec["suggested"] = new
    rec["why"] = r.get("why", "")
    rec["over"] = len(new) > it.get("max_chars", 999)
    del rec["text"]
    out.append(rec)

Path(sys.argv[2]).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"\n{len(items)}건 중 {len(out)}건 변경 제안 ({sum(1 for o in out if o['over'])}건 길이초과)")
