"""ElevenLabs로 시연영상 내레이션을 만듭니다.

키/음성ID는 로컬 파일에서 읽습니다 — 채팅에도, 이 스크립트에도 값 자체는
없습니다.
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

SEC = Path(r"C:\Users\HOME\AppData\Local\Temp\claude\C--project-LISN\fda14023-1984-4212-8502-e63cf816ef36\scratchpad\secrets")
OUT = Path(r"C:\Users\HOME\AppData\Local\Temp\claude\C--project-LISN\fda14023-1984-4212-8502-e63cf816ef36\scratchpad\video\tts")
OUT.mkdir(parents=True, exist_ok=True)

KEY = (SEC / "elevenlabs_api_key.txt").read_text(encoding="utf-8").strip()
# Sarah — 프리메이드(무료 API 가능). Seulki(전문 보이스)는 Free 플랜 API 에서
# 막혀 대체했다 (2026.08.22, "Free users cannot use library voices via the API").
VOICE = "EXAVITQu4vr4xnSDxMaL"

# 구간 목표 초 — build_video.sh 의 각 파트 길이와 맞춥니다.
SEGMENTS = {
    "00": (9, "귀기울임. 먼저 말을 거는 정서 케어입니다."),
    "01": (44, "사용자는 앱을 열지 않았습니다. 수면이 닷새째 무너진 것을, 시스템이 먼저 알아챕니다. "
                "알림을 누르면 첫 마디가 이미 준비되어 있습니다. "
                "무엇을 보고 말을 걸었는지도 함께 보여줍니다. 감시가 아니라, 관심으로 읽히도록."),
    "02": (33, "성격은 둘 중에 고릅니다. 따스한 공감형과, 현실적인 조언형. "
                "서버는 위기 판정과 응답 생성을 동시에 돌립니다. 순서대로 하면 3초를 넘기기 때문입니다."),
    "02b": (14, "위기가 확인되면 챗봇 답변을 버립니다. 위로가, 위험을 덮지 않게."),
    "03": (36, "수면과 활동량, 심박을 모읍니다. 개인 기준선에서 얼마나 벗어났는지를 봅니다. "
                "데이터가 사흘치에 못 미치면 정상이라고 말하지 않습니다. 모르는 것과, 괜찮은 것은 다릅니다."),
    "04": (35, "관리자는 위험도 분포를 한 화면에서 봅니다. 위험한 사람이 위로 옵니다. "
                "채팅에서 감지한 위기도 여기 기록됩니다. 미평가 인원은, 정상으로 세지 않습니다."),
    "99": (10, "귀기울임. 감지한 것을, 사람에게 닿게 합니다."),
}

URL = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE}"

total_chars = sum(len(t) for _, t in SEGMENTS.values())
print(f"총 글자수: {total_chars}")

for name, (want_sec, text) in SEGMENTS.items():
    body = json.dumps({
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            # ⚠ 안정성을 조금 높게 잡습니다. 너무 낮으면 문장마다 톤이
            #   들쭉날쭉해지고, 짧은 나레이션에서는 그게 더 도드라집니다.
            "stability": 0.55,
            "similarity_boost": 0.8,
            "style": 0.15,
            "use_speaker_boost": True,
        },
    }).encode("utf-8")

    req = urllib.request.Request(
        URL, data=body, method="POST",
        headers={"xi-api-key": KEY, "Content-Type": "application/json", "Accept": "audio/mpeg"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            audio = r.read()
    except urllib.error.HTTPError as e:
        print(f"  {name}: 오류 {e.code} {e.read().decode()[:200]}")
        sys.exit(1)

    path = OUT / f"{name}.mp3"
    path.write_bytes(audio)
    print(f"  {name:4s} {len(text):3d}자  목표 {want_sec:2d}s  -> {path.name} ({len(audio)} bytes)")
    time.sleep(0.5)  # 무료 티어 rate limit 배려

print(f"\n완료 -> {OUT}")
