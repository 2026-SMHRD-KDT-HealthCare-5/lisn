# -*- coding: utf-8 -*-
"""시연영상용 정적 Noto Sans KR 을 만듭니다.

⚠ **왜 필요한가** — 발표자료는 글꼴을 '이름'으로 지정하면 PowerPoint 가
  알아서 굵기를 고릅니다. 하지만 영상은 ffmpeg drawtext 라 **글꼴 파일**을
  줘야 하고, drawtext 에는 굵기를 고르는 옵션이 없습니다.

  Windows 에 깔린 `NotoSansKR-VF.ttf` 는 가변폰트인데 **기본 굵기가
  Thin(100)** 입니다. 그대로 넘기면 자막이 종잇장처럼 얇게 나옵니다.
  그래서 여기서 굵기를 고정한 정적 폰트를 뽑아 씁니다.

  이걸 몰라서 한동안 영상만 Malgun Gothic 을 썼고, 발표자료(Noto Sans KR)와
  **글꼴이 아예 다른 채로** 나갔습니다(2026.08.22 지적받음).

출력은 tools/capture/fonts/ 이고 .gitignore 대상입니다 — 원본이 Windows 에
있으니 필요할 때 다시 뽑으면 됩니다(10MB 짜리를 저장소에 넣지 않습니다).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = Path(r"C:\Windows\Fonts\NotoSansKR-VF.ttf")
OUT = ROOT / "tools" / "capture" / "fonts"
BRAND = json.loads((ROOT / "docs" / "design" / "brand.json").read_text(encoding="utf-8"))


def build(weight: int, name: str) -> Path:
    dst = OUT / name
    if dst.exists():
        return dst
    from fontTools.varLib import instancer
    from fontTools.ttLib import TTFont
    if not SRC.exists():
        sys.exit(f"원본 글꼴이 없습니다: {SRC}\n  Noto Sans KR 을 설치하세요.")
    f = TTFont(SRC)
    instancer.instantiateVariableFont(f, {"wght": weight}, inplace=True)
    OUT.mkdir(parents=True, exist_ok=True)
    f.save(dst)
    return dst


if __name__ == "__main__":
    fw = BRAND["font"]
    made = [
        build(fw["weightTitle"], f"NotoSansKR-{fw['weightTitle']}.ttf"),
        build(fw["weightBody"], f"NotoSansKR-{fw['weightBody']}.ttf"),
    ]
    for p in made:
        print(f"  {p.relative_to(ROOT)}  ({p.stat().st_size // 1024}KB)")
