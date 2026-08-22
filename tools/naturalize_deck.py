"""발표자료 문구를 OpenAI 로 자연스럽게 다듬습니다.

⚠ **결과를 그대로 적용하지 않습니다.** 여기서는 제안만 받고, 사람(에이전트)이
하나씩 검토해서 실제로 자연스러워졌는지 · 숫자와 사실관계가 안 바뀌었는지
확인한 뒤 build.js 에 직접 반영합니다.
"""
import json
from pathlib import Path
from urllib import request

ROOT = Path("C:/project/LISN")
KEY = None
for line in (ROOT / "backend" / ".env").read_text(encoding="utf-8").splitlines():
    if line.startswith("OPENAI_API_KEY="):
        KEY = line.split("=", 1)[1].strip()
        break
assert KEY, "OPENAI_API_KEY 를 backend/.env 에서 못 찾았습니다"

items = json.loads(Path("/tmp/deck_texts.json").read_text(encoding="utf-8"))

SYSTEM = """너는 한국어 프레젠테이션 문구 감수자다. 아래 규칙을 반드시 지킨다.

1. 숫자를 절대 바꾸지 않는다 — 0.946, 319건, 33개, 2052ms 같은 값은 원문
   그대로 유지한다. 반올림·표현 방식(예: "319건"->"약 300건")도 바꾸지 않는다.
2. 사실관계·주장의 의미를 바꾸지 않는다. 더 강하게도 더 약하게도 말하지 않는다.
3. 고유명사·전문용어·코드 식별자를 바꾸지 않는다 — 귀기울임, LISN, FCM,
   Health Connect, WorkManager, OAuth, CRITICAL, model_version, db/schema.sql
   같은 것들.
4. 길이를 원문과 비슷하게 유지한다. 발표 슬라이드의 고정된 상자 안에
   들어가야 한다 — 원문보다 눈에 띄게 길어지면 안 된다.
5. 바꿀 필요가 없으면 원문을 그대로 돌려준다. 이미 자연스러운 한국어
   문장을 굳이 고치지 않는다. 손볼 이유가 없는데 문체만 바꾸지 않는다.
6. 찾아야 할 것은 번역투다 — 영어를 그대로 옮긴 듯한 어색한 표현:
   - 주어 없이 사물이 스스로 동작하는 것처럼 쓴 수동태
     (예: "앱은 열리지 않습니다" - 사람이 안 여는 건데 앱이 안 열리는 것처럼 씀)
   - 한국어에서 잘 안 쓰는 동사·조사 결합 (예: "밀어 올리는 구조")
   - 영어 라벨을 그대로 한국어로 옮긴 제목 (예: "문제와 답" <- "Problem & Answer")
   - 문장이 명사구로 뚝 끊기는 것 (주어·서술어가 없어야 할 자리에 없는 것)

출력은 {"items": [{"i": 인덱스, "text": "고친 결과(또는 원문 그대로)"}, ...]}
형태의 JSON 객체 하나로만 한다. 바뀐 항목만 넣어도 되고 전부 넣어도 된다 —
다만 안 바뀐 항목을 넣을 땐 반드시 원문과 완전히 동일해야 한다."""

BATCH = 25
MODEL = "gpt-5.4"
results = {}

for start in range(0, len(items), BATCH):
    chunk = items[start:start + BATCH]
    numbered = [{"i": start + j, "slide": it["slide"], "text": it["text"]} for j, it in enumerate(chunk)]
    body = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": json.dumps(numbered, ensure_ascii=False)},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.3,
    }).encode("utf-8")

    req = request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body, method="POST",
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
    )
    with request.urlopen(req, timeout=90) as r:
        resp = json.loads(r.read())
    content = resp["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    rows = parsed.get("items", parsed if isinstance(parsed, list) else [])
    for row in rows:
        results[row["i"]] = row["text"]
    print(f"  배치 {start}~{start + len(chunk) - 1} 처리 완료 ({len(rows)}건 응답)")

out = []
for idx, it in enumerate(items):
    new = results.get(idx, it["text"])
    if new != it["text"]:
        out.append({"slide": it["slide"], "original": it["text"], "suggested": new})

Path("/tmp/naturalize_suggestions.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8"
)
print(f"\n총 {len(items)}건 중 {len(out)}건 변경 제안")
