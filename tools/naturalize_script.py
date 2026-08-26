# -*- coding: utf-8 -*-
"""발표 대본(docs/가이드/최종발표_대본.md) 나레이션 문장을 OpenAI 로 검토합니다.

tools/naturalize_deck.py 와 같은 패턴(스스로 고치지 않고 제안만 받아 사람이
검토)이지만, 대상이 화면 위 고정폭 카피가 아니라 **소리 내 말하는 나레이션**
이라 시스템 프롬프트를 새로 씁니다 — 글자 수 제한 대신 "말했을 때 자연스러운가"
"슬라이드 순서를 몰라도 이 문단만으로 뜻이 통하는가"를 봅니다.

⚠ 결과를 그대로 적용하지 않습니다. 제안만 받고 사람이 검토합니다.

사용법: .venv\\Scripts\\python.exe tools\\naturalize_script.py
"""
import json
import re
import sys
from pathlib import Path
from urllib import request

ROOT = Path(__file__).resolve().parent.parent
SCRIPT_MD = ROOT / "docs" / "가이드" / "최종발표_대본.md"
OUT_JSON = ROOT / "docs" / "가이드" / ".naturalize_script_suggestions.json"

KEY = None
for line in (ROOT / "backend" / ".env").read_text(encoding="utf-8").splitlines():
    if line.startswith("OPENAI_API_KEY="):
        KEY = line.split("=", 1)[1].strip()
        break
assert KEY, "OPENAI_API_KEY 를 backend/.env 에서 못 찾았습니다"

SYSTEM = """너는 한국어 발표 나레이션(구어체 대본) 검토자다. 화면에 뜨는
문구가 아니라 **발표자가 소리 내 말하는 대본**을 검토한다.

# 제품
「귀기울임(LISN)」 — 스마트워치 라이프로그(수면·활동량·심박)와 앱 사용
로그를 같이 보고 개인 기준선 대비 정서 이탈을 감지하는 케어 서비스.
위험 신호가 보이면 사용자가 앱을 열기 전에 시스템이 먼저 다가가는 것을
「선제 접촉」이라 부른다. 이 발표는 스마트인재개발원 KDT 캡스톤 최종
발표이고, 청중은 프로젝트를 처음 보는 심사위원이다.

# 검토 기준
1. **소리 내 읽었을 때 자연스러운가.** 문어체 명사구 나열이 아니라 말하는
   문장이어야 한다.
2. **주어·목적어가 빠지지 않았는가.**
3. **앞뒤 문장이 논리로 이어지는가.** 화면 순서를 모르고 이 문단만 읽어도
   무슨 얘기인지 통해야 한다.
4. **번역투가 없는가** — 사물이 스스로 하는 것처럼 쓴 수동태, 한국어에서
   안 쓰는 동사·조사 결합, 명사구로 뚝 끊기는 문장.
5. **프로젝트 용어를 일관되게 쓰는가** — 선제 접촉, 개인 기준선 이탈,
   위기 탐지, 관제 등.
6. 발표 대본이라 **격식체(합니다/습니다)를 유지**하되 딱딱한 보고서 투가
   아니라 사람 앞에서 말하는 톤이어야 한다.

# 반드시 지킬 것
- **숫자·고유명사·기술용어를 바꾸지 않는다** — 0.946, 0.609, 26회, 348건,
  schema.sql, AUC, Health Connect, FastAPI, GroupKFold 등 전부 원문 그대로.
- **길이를 원문과 비슷하게 유지한다.** 이 대본은 190자/분 기준으로 초를
  이미 계산해뒀다 — 늘리면 발표 시간 예산이 깨진다. max_chars 를 참고해
  그 언저리(±15% 이내)로 맞춰라.
- **이미 자연스러우면 그대로 둔다.** 문체 취향만 바꾸려고 고치지 마라.
- 괄호로 시작하는 "(화면 전환 지시)" 같은 무대 지시문은 검토 대상이
  아니다 — 애초에 나레이션만 넘길 것이다.

# 출력
{"items":[{"i":인덱스,"text":"고친 결과","why":"왜 고쳤는지 한 줄"}]}
형태의 JSON 객체 하나. **실제로 고칠 필요가 있는 항목만** 넣어라. 안 고친
건 빼라."""


def extract_items():
    text = SCRIPT_MD.read_text(encoding="utf-8")
    # "## 슬라이드 N — 제목 (...)" 다음에 오는 "> ..." 인용 블록만 뽑는다.
    pattern = re.compile(
        r"^## 슬라이드 (\d+) — (.+?) \(.*?\)\n\n((?:> .*\n?)+)",
        re.MULTILINE,
    )
    items = []
    for m in pattern.finditer(text):
        no = int(m.group(1))
        title = m.group(2).strip()
        quote_block = m.group(3)
        lines = [l[2:].rstrip() for l in quote_block.splitlines() if l.startswith("> ")]
        narration = " ".join(lines).strip()
        if not narration:
            continue
        items.append({
            "slide": no,
            "title": title,
            "text": narration,
            "max_chars": max(int(len(narration) * 1.15), len(narration) + 10),
        })
    return items


def main():
    items = extract_items()
    print(f"추출된 나레이션 문단: {len(items)}개")

    BATCH = 8
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
        print(f"  배치 {start}~{start + len(chunk) - 1} — {len(rows)}건 제안", flush=True)

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

    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n{len(items)}건 중 {len(out)}건 변경 제안 ({sum(1 for o in out if o['over'])}건 길이초과) → {OUT_JSON}")


if __name__ == "__main__":
    main()
