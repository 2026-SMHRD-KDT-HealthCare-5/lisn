"""앱 런처 아이콘 · 알림 아이콘 생성 — assets/images/home_emotion.png 에서

왜 필요한가
    Flutter 프로젝트를 만들면 `ic_launcher.png` 가 **Flutter 기본 로고**로
    들어옵니다(544바이트). 그대로 두면 홈 화면·앱 서랍·최근 앱·**푸시 알림**
    어디에나 Flutter 로고가 박힙니다. 시연 영상 전 컷에 남습니다.

무엇을 만드는가
    1. 적응형 아이콘(Android 8+ 정본)
         mipmap-anydpi-v26/ic_launcher.xml   ← 배경/전경 두 겹을 가리킴
         mipmap-*/ic_launcher_foreground.png ← 마스코트 (108dp 캔버스)
         mipmap-*/ic_launcher_background.png ← 브랜드 그라데이션
    2. 레거시 아이콘 (Android 7 이하)
         mipmap-*/ic_launcher.png            ← 둘을 합쳐 구운 정사각형
    3. 알림 작은 아이콘
         drawable-*/ic_stat_maeume.png       ← **흰 실루엣 + 투명 배경**

⚠ **알림 아이콘은 반드시 흰 실루엣이어야 합니다.** Android 는 상태표시줄
  아이콘의 **알파 채널만** 씁니다. 색이 있는 이미지를 넣으면 색은 전부
  버려지고 불투명한 부분이 통째로 흰 덩어리로 칠해집니다. 마스코트를
  그대로 넣으면 「흰 하트 뭉치」가 됩니다 — 그래서 알파를 임계값으로
  잘라 윤곽만 남깁니다.

⚠ **적응형 아이콘의 안전 영역은 가운데 66/108 입니다.** 바깥 테두리는
  런처 모양(원·둥근네모·물방울)에 따라 잘려 나갑니다. 마스코트를 캔버스
  가득 채우면 귀가 잘립니다.

사용:
    python tools/make_app_icon.py
    (다시 돌려도 안전합니다. 같은 파일을 덮어씁니다)
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "frontend/app/assets/images/home_emotion.png"
RES = ROOT / "frontend/app/android/app/src/main/res"

# 브랜드 색 — lib/theme/app_colors.dart 와 맞춥니다.
#   primary #647BEC 를 위로 살짝 밝게 흘려 차분한 그라데이션을 만듭니다.
BG_TOP = (169, 190, 248)     # #A9BEF8
BG_BOTTOM = (122, 144, 238)  # #7A90EE

# 적응형 아이콘 캔버스는 108dp, 안전 영역은 가운데 66dp.
# 마스코트를 안전 영역의 92% 로 넣어 여유를 둡니다.
ADAPTIVE_DP = 108
SAFE_DP = 66
FILL_RATIO = 0.92

DENSITIES = {  # 이름: dp 당 픽셀 배율
    "mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4,
}
LEGACY_DP = 48   # 레거시 런처 아이콘
STAT_DP = 24     # 알림 작은 아이콘


def trimmed(im: Image.Image) -> Image.Image:
    """투명 여백을 잘라냅니다. 안 자르면 마스코트가 실제보다 작아 보입니다."""
    box = im.getbbox()
    return im.crop(box) if box else im


def fit_square(im: Image.Image, size: int) -> Image.Image:
    """정사각형 캔버스 가운데에 비율을 지켜 넣습니다."""
    im = im.copy()
    im.thumbnail((size, size), Image.LANCZOS)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(im, ((size - im.width) // 2, (size - im.height) // 2), im)
    return out


def gradient(size: int) -> Image.Image:
    out = Image.new("RGBA", (size, size))
    d = ImageDraw.Draw(out)
    for y in range(size):
        t = y / max(size - 1, 1)
        d.line(
            [(0, y), (size, y)],
            fill=tuple(round(a + (b - a) * t) for a, b in zip(BG_TOP, BG_BOTTOM)) + (255,),
        )
    return out


def silhouette(im: Image.Image, size: int) -> Image.Image:
    """흰 실루엣 + 투명 배경. 알파 128 이상만 남깁니다.

    임계값을 두는 이유: 원본 가장자리의 반투명 픽셀까지 흰색으로 칠하면
    윤곽이 부옇게 번져 작은 크기에서 형체를 알아볼 수 없습니다.
    """
    fitted = fit_square(im, size)
    alpha = fitted.split()[3].point(lambda a: 255 if a >= 128 else 0)
    out = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    out.putalpha(alpha)
    return out


def main() -> None:
    src = trimmed(Image.open(SRC).convert("RGBA"))
    print(f"원본 {SRC.name} → 여백 제거 후 {src.size}")

    for name, scale in DENSITIES.items():
        mip = RES / f"mipmap-{name}"
        drw = RES / f"drawable-{name}"
        mip.mkdir(parents=True, exist_ok=True)
        drw.mkdir(parents=True, exist_ok=True)

        # ── 적응형: 배경
        full = round(ADAPTIVE_DP * scale)
        gradient(full).save(mip / "ic_launcher_background.png")

        # ── 적응형: 전경 (안전 영역 안에만 그림)
        fg = Image.new("RGBA", (full, full), (0, 0, 0, 0))
        inner = round(SAFE_DP * scale * FILL_RATIO)
        mascot = fit_square(src, inner)
        fg.paste(mascot, ((full - inner) // 2, (full - inner) // 2), mascot)
        fg.save(mip / "ic_launcher_foreground.png")

        # ── 레거시: 배경 위에 마스코트를 구워 정사각형으로
        leg = round(LEGACY_DP * scale)
        base = gradient(leg)
        m = fit_square(src, round(leg * 0.74))
        base.paste(m, ((leg - m.width) // 2, (leg - m.height) // 2), m)
        base.save(mip / "ic_launcher.png")

        # ── 알림 작은 아이콘
        silhouette(src, round(STAT_DP * scale)).save(drw / "ic_stat_maeume.png")

        print(f"  {name:8s} 적응형 {full}px · 레거시 {leg}px · 알림 {round(STAT_DP*scale)}px")

    # ── 적응형 아이콘 선언
    anydpi = RES / "mipmap-anydpi-v26"
    anydpi.mkdir(parents=True, exist_ok=True)
    xml = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n'
        '    <background android:drawable="@mipmap/ic_launcher_background" />\n'
        '    <foreground android:drawable="@mipmap/ic_launcher_foreground" />\n'
        '</adaptive-icon>\n'
    )
    (anydpi / "ic_launcher.xml").write_text(xml, encoding="utf-8")
    (anydpi / "ic_launcher_round.xml").write_text(xml, encoding="utf-8")
    print("적응형 선언 2개 작성 (ic_launcher.xml · ic_launcher_round.xml)")


if __name__ == "__main__":
    main()
