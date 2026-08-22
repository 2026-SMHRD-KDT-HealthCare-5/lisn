# -*- coding: utf-8 -*-
"""자막 글자가 실제 렌더 크기에서 획을 잃는지 검사합니다.

⚠ **왜 필요한가** — 2026.08.22 에 관제 컷 자막의 「맡」이 fontsize 29 에서
  ㅏ 의 세로획을 통째로 잃어 「맡」이 「맏-」처럼 보였습니다. 완성본을
  눈으로 훑고도 못 봤고, 사람이 지적해서 알았습니다. 이런 건 **한 글자짜리
  결함이라 눈으로는 반드시 놓칩니다.**

원리 — **ffmpeg drawtext 로 직접 그립니다.** PIL 로 그리면 힌팅이 달라서
재현되지 않습니다(실제로 PIL 판으로는 「맡」을 못 잡았습니다). 같은 글자를
①실제 크기와 ②8배 크기로 그린 뒤 8배본을 줄여, 잉크량(불투명 픽셀 합)을
견줍니다. 힌팅이 획을 지우면 실제 크기 쪽이 뚜렷하게 적습니다.

기준 — **또래와 견줍니다.** 절대 잉크량으로 재면 얇은 굵기가 통째로 걸립니다
(400 대신 350 을 쓰던 때 자막 글자 전부가 -40% 로 나왔는데 실제로는 멀쩡했습니다).
그래서 같은 크기 글자들의 잉크 손실 **중앙값**을 구하고, 거기서 5%p 넘게 더
잃은 글자만 집어냅니다. 획이 빠진 글자는 또래 사이에서 반드시 튑니다 —
Malgun 29px 에서 「맡」은 또래가 -7% 일 때 -13.4% 였습니다.

판정은 사람이 합니다 — 걸린 글자를 `glyph_suspects.png` 로 10배 확대해 뽑아
주니 그것만 보면 됩니다. 문장부호는 원래 얇아 비율이 요동쳐 뺍니다.
"""
import json, os, subprocess, sys, tempfile
from pathlib import Path
from PIL import Image

FF = os.environ.get("FFMPEG_BIN") or Path(os.environ.get("TEMP", "/tmp"), "ffmpeg_path").read_text().strip()
ROOT = Path(__file__).resolve().parents[2]
BRAND = json.loads((ROOT / "docs" / "design" / "brand.json").read_text(encoding="utf-8"))
# ⚠ 영상이 실제로 쓰는 글꼴로 검사해야 합니다. 예전엔 Malgun 을 박아 뒀는데
#   영상이 Noto Sans KR 로 바뀌면서 엉뚱한 글꼴을 재던 적이 있습니다.
_W = BRAND["font"]
FONTS = {
    "title": ROOT / "tools" / "capture" / "fonts" / f"NotoSansKR-{_W['weightTitle']}.ttf",
    "body":  ROOT / "tools" / "capture" / "fonts" / f"NotoSansKR-{_W['weightBody']}.ttf",
}
def fontfile(size):
    """제목(42px 이상)은 굵은 쪽, 설명은 얇은 쪽으로 그립니다.

    ⚠ ffmpeg drawtext 는 역슬래시 경로를 못 받습니다. 슬래시로 바꾸고
      드라이브 콜론만 escape 해야 합니다 — C:/... -> C\:/...
      역슬래시로 넘겼더니 ffmpeg 이 통째로 죽었습니다(exit 3221225477).
    """
    p = FONTS["title"] if size >= 42 else FONTS["body"]
    return str(p).replace(chr(92), "/").replace(":", chr(92) + ":", 1)
SKIP = set(" .,·—「」()[]'\"~-·…!?:;/")
LIMIT = -5.0   # 또래 중앙값보다 이만큼(%p) 더 잃으면 의심

def render(ch, size, out):
    box = size * 4
    subprocess.run(
        [FF, "-y", "-f", "lavfi", "-i", f"color=c=black:s={box}x{box}:d=1", "-frames:v", "1",
         "-vf", f"drawtext=fontfile='{fontfile(size)}':text='{ch}':fontsize={size}:fontcolor=white:x={size}:y={size}",
         "-update", "1", str(out)],
        check=True, capture_output=True)

def ink(path, size=None):
    im = Image.open(path).convert("L")
    if size:
        im = im.resize((size, size), Image.LANCZOS)
    return sum(im.get_flattened_data()) / 255.0

def check(rows):
    bad_total = 0
    seen = set()
    import statistics
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        cache = {}

        def delta(ch, size):
            key = (ch, size)
            if key not in cache:
                a, b = td / "a.png", td / "b.png"
                render(ch, size, a)
                render(ch, size * 8, b)
                cache[key] = (ink(a) - ink(b, size * 4)) / ink(b, size * 4) * 100
            return cache[key]

        # 크기별로 또래 중앙값을 먼저 구합니다
        chars_by_size = {}
        for row in rows:
            chars_by_size.setdefault(row["size"], set()).update(
                c for c in row["text"] if c not in SKIP)
        base = {}
        for size, chars in chars_by_size.items():
            vals = [delta(c, size) for c in sorted(chars)]
            base[size] = statistics.median(vals) if vals else 0.0

        for row in rows:
            text, size, label = row["text"], row["size"], row.get("label", "")
            med = base[size]
            hits = [(c, delta(c, size) - med)
                    for c in dict.fromkeys(text)
                    if c not in SKIP and delta(c, size) - med < LIMIT]
            if hits:
                bad_total += len(hits)
                seen.update((size, c) for c, _ in hits)
                detail = ", ".join(f"「{c}」 {d:+.0f}%p" for c, d in hits)
                print(f"  ✗ [{label}] {size}px — 또래보다 {detail}")
                print(f"       {text}")
            else:
                print(f"  ✓ [{label}] {size}px  {text}")
    return bad_total, sorted(seen)


def contact(suspects, out, zoom=10):
    """의심 글자를 실제 렌더 크기로 그린 뒤 확대해 한 장에 모읍니다.

    -11% 대에는 멀쩡한 글자도 걸립니다. 숫자만 보고 판단하지 말고 이 그림을
    열어 획이 실제로 빠졌는지 보세요 — 「맡」은 ㅏ 세로획이 아예 없습니다.
    """
    import tempfile
    from PIL import Image
    with tempfile.TemporaryDirectory() as td:
        tiles = []
        for i, (size, ch) in enumerate(suspects):
            f = Path(td) / f"{i}.png"
            render(ch, size, f)
            im = Image.open(f).convert("L").crop((size // 2, size // 2, size * 2, size * 2))
            tiles.append(im.resize((im.width * zoom, im.height * zoom), Image.NEAREST))
        w = sum(t.width for t in tiles) + 20 * (len(tiles) + 1)
        h = max(t.height for t in tiles) + 20
        sheet = Image.new("L", (w, h), 0)
        x = 20
        for im in tiles:
            sheet.paste(im, (x, 10)); x += im.width + 20
        sheet.save(out)


if __name__ == "__main__":
    rows = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    n, suspects = check(rows)
    print()
    if n:
        out = Path("glyph_suspects.png")
        contact(suspects, out)
        print(f"⚠ 의심 글자 {n}건 — {out} 를 열어 눈으로 확인하세요.")
        print("   획이 실제로 빠졌으면 낱말을 바꾸거나 fontsize 를 올립니다.")
        print("   또래보다 -5%p 안팎은 대개 멀쩡합니다. 실제 결함이던 「맡」은 -14%p 였습니다.")
    else:
        print("✓ 모든 자막이 렌더 크기에서 온전합니다")
    sys.exit(1 if n else 0)
