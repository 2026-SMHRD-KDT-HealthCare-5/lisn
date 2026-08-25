# -*- coding: utf-8 -*-
r"""발표자료 폰트 임베드용 정적 글꼴을 만듭니다. 2026.08.25

    .venv/Scripts/python.exe tools/capture/make_embed_fonts.py

## 왜 `make_fonts.py`(영상용)와 따로 있나

영상용은 ffmpeg drawtext 가 **파일 경로**로 글꼴을 받으므로 이름이
아무래도 상관없습니다. **PowerPoint 폰트 임베드는 다릅니다** — 슬라이드가
`fontFace: "Noto Sans KR DemiLight"` 처럼 **이름**으로 글꼴을 지정하고,
PowerPoint 는 그 이름과 **정확히 같은 family 로 설치된 폰트**를 찾아
임베드합니다. `make_fonts.py` 가 뽑는 정적 인스턴스는 전부 family 가
`Noto Sans KR`/`Regular` 로만 찍혀 있어(가변폰트 인스턴싱의 부작용),
이름별로 설치할 수 없습니다.

## 이 스크립트가 하는 일

`NotoSansKR-VF.ttf`(Windows 에 이미 설치돼 있음)를 세 굵기로 인스턴싱한
뒤, **name 테이블(ID 1·2·4·6)과 OS/2·head 의 굵게 플래그를 다시 씁니다.**

| family | subfamily | 용도 |
|---|---|---|
| `Noto Sans KR` | Regular | 본문·일반 제목 |
| `Noto Sans KR` | **Bold** | `bold: true` 로 쓰는 28곳 |
| `Noto Sans KR DemiLight` | Regular | 보조 설명 |

`NanumMyeongjo`(대형 헤드라인)는 **Google Fonts 원본을 그대로** 씁니다 —
내부 name 이 이미 `NanumMyeongjo`/`Regular`·`NanumMyeongjo`/`Bold` 로
정확합니다(공백 없는 이름 — CSS 별칭 `'Nanum Myeongjo'` 와 다릅니다).
`fonts.gstatic.com` 에서 내려받습니다.

## 이 폰트들을 실제로 임베드하려면 (한 번만)

이 스크립트는 **파일을 만들 뿐 설치하지 않습니다.** 임베드는 세 단계입니다.

```powershell
# ① 이 PC 에 없는 굵기로 폰트를 만든다
.venv\Scripts\python.exe tools\capture\make_embed_fonts.py

# ② 방금 만든 5개를 이 PC 에 설치한다(관리자 권한 불필요 — 사용자별 설치)
#    설치 안 되면 PowerPoint 가 대체 글꼴을 임베드해 화면과 달라진다
```
```powershell
$src = "tools\capture\fonts_embed"; $dst = "$env:LOCALAPPDATA\Microsoft\Windows\Fonts"
New-Item -ItemType Directory -Force -Path $dst | Out-Null
Add-Type @"
using System; using System.Runtime.InteropServices;
public class FontInst {
  [DllImport("gdi32.dll", CharSet = CharSet.Auto)]
  public static extern int AddFontResource(string f);
  [DllImport("user32.dll", CharSet = CharSet.Auto)]
  public static extern int SendMessage(int h, int m, int w, int l);
}
"@
Get-ChildItem "$src\*.ttf" | ForEach-Object {
    $d = Join-Path $dst $_.Name
    Copy-Item $_.FullName $d -Force
    $n = [IO.Path]::GetFileNameWithoutExtension($_.Name) + " (TrueType)"
    New-ItemProperty -Path "HKCU:\Software\Microsoft\Windows NT\CurrentVersion\Fonts" `
        -Name $n -Value $d -PropertyType String -Force | Out-Null
    [FontInst]::AddFontResource($d) | Out-Null
}
[FontInst]::SendMessage(0xffff, 0x1D, 0, 0) | Out-Null
```

```powershell
# ③ presentation.xml 에 embedTrueTypeFonts=1 을 심고, PowerPoint 로 SaveAs
#    ⚠ 반드시 SaveAs 입니다. Presentation.Save() 로는 임베드가 안 됩니다 —
#      COM 이 .Save() 를 「빠른 저장」 경로로 처리해 폰트 임베드 로직을
#      타지 않습니다(2026.08.25 실측으로 확인). SaveAs 는 전체 재작성
#      경로를 타서 그때 임베드합니다.
```
```python
import zipfile, os
SRC = r"documents\최종발표자료_귀기울임.pptx"
with zipfile.ZipFile(SRC) as z:
    xml = z.read("ppt/presentation.xml").decode("utf-8")
xml2 = xml.replace('saveSubsetFonts="1"', 'embedTrueTypeFonts="1" saveSubsetFonts="0"')
tmp = SRC + ".tmp"
with zipfile.ZipFile(SRC) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
    for item in zin.infolist():
        data = zin.read(item.filename)
        if item.filename == "ppt/presentation.xml":
            data = xml2.encode("utf-8")
        zout.writestr(item, data)
os.replace(tmp, SRC)
```
```powershell
$path = (Resolve-Path "documents\최종발표자료_귀기울임.pptx").Path
$ppt = New-Object -ComObject PowerPoint.Application
try {
    $pres = $ppt.Presentations.Open($path, $false, $true, $false)
    $pres.SaveAs($path, 24)   # 24 = ppSaveAsOpenXMLPresentation
    $pres.Close()
} finally {
    $ppt.Quit()
    [Runtime.Interopservices.Marshal]::ReleaseComObject($ppt) | Out-Null
}
```

## 확인

```python
import zipfile
z = zipfile.ZipFile(SRC)
print([n for n in z.namelist() if "font" in n.lower()])
# ppt/fonts/font1.fntdata ~ font5.fntdata 다섯 개가 보여야 합니다.
# 파일 크기도 7~8MB -> 20~25MB 로 뜁니다(폰트 3종 × 6MB 안팎).
```

⚠ **재생성(`build_deck.js`)하면 이 임베드가 다시 풀립니다.** 8/24·8/25
양쪽에서 실제로 겪었습니다. **문구·디자인을 바꿀 때마다 이 절차를
마지막에 한 번 더 돌리세요.**
"""
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

SRC_VF = Path(r"C:\Windows\Fonts\NotoSansKR-VF.ttf")
OUT = Path(__file__).resolve().parent / "fonts_embed"

#  Google Fonts CSS 가 주는 URL 은 버전이 바뀔 수 있으니, 안 바뀌는
#  fonts.googleapis.com/css2 엔드포인트로 매번 실제 주소를 물어본다.
NANUM_CSS = "https://fonts.googleapis.com/css2?family=Nanum+Myeongjo:wght@400;700&display=swap"


def set_names(font: TTFont, family: str, subfamily: str, bold: bool) -> None:
    """name 테이블과 굵게 플래그를 다시 쓴다.

    ⚠ **OS/2.fsSelection·head.macStyle 을 맞추지 않으면** PowerPoint 가
      「굵게」 버튼을 눌러도 이 폰트를 안 쓰고 가짜(faux) 굵게를 그립니다 —
      Bold 파일인데 시스템이 Bold 로 인식을 못 하기 때문입니다.
    """
    full = family if subfamily == "Regular" else f"{family} {subfamily}"
    ps = (family + "-" + subfamily).replace(" ", "")
    name = font["name"]
    for pid, eid, lid in ((3, 1, 0x409), (1, 0, 0)):
        name.setName(family, 1, pid, eid, lid)
        name.setName(subfamily, 2, pid, eid, lid)
        name.setName(full, 4, pid, eid, lid)
        name.setName(ps, 6, pid, eid, lid)
        #  타이포그래픽 이름(16/17)이 남아 있으면 일부 뷰어가 그쪽을
        #  진짜 family 로 본다 — 지운다.
        name.removeNames(nameID=16)
        name.removeNames(nameID=17)
    if "OS/2" in font:
        if bold:
            font["OS/2"].fsSelection |= 0x20
            font["OS/2"].fsSelection &= ~0x40
        else:
            font["OS/2"].fsSelection &= ~0x20
            font["OS/2"].fsSelection |= 0x40
        font["OS/2"].usWeightClass = 700 if bold else 400
    if "head" in font:
        mac = font["head"].macStyle
        font["head"].macStyle = (mac | 0x1) if bold else (mac & ~0x1)


def instance(weight: int) -> TTFont:
    if not SRC_VF.exists():
        raise SystemExit(f"원본 글꼴이 없습니다: {SRC_VF}\n  Noto Sans KR 을 설치하세요.")
    f = TTFont(SRC_VF)
    instancer.instantiateVariableFont(f, {"wght": weight}, inplace=True)
    return f


def download_nanum() -> None:
    """NanumMyeongjo Regular·Bold 를 Google Fonts 에서 받는다.

    ⚠ **웹 별칭(`'Nanum Myeongjo'`, 공백 있음)이 아니라 폰트 내부 진짜
      이름(`NanumMyeongjo`, 공백 없음)을 그대로 씁니다.** 파일을 다시
      만들지 않고 원본을 그대로 저장만 합니다 — 이미 이름이 정확합니다.
    """
    import re
    import urllib.request

    req = urllib.request.Request(NANUM_CSS, headers={"User-Agent": "Mozilla/5.0"})
    css = urllib.request.urlopen(req, timeout=20).read().decode("utf-8")
    blocks = re.findall(
        r"font-weight:\s*(\d+);.*?src:\s*url\(([^)]+)\)", css, re.S
    )
    weights = {w: u for w, u in blocks}
    for w, dst_name in (("400", "NanumMyeongjo-Regular.ttf"),
                        ("700", "NanumMyeongjo-Bold.ttf")):
        if w not in weights:
            raise SystemExit(f"NanumMyeongjo 굵기 {w} 를 CSS 에서 못 찾았습니다")
        dst = OUT / dst_name
        if dst.exists():
            continue
        urllib.request.urlretrieve(weights[w], dst)
        print(f"  {dst}  ({dst.stat().st_size // 1024}KB)  다운로드")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    jobs = [
        (400, "Noto Sans KR", "Regular", False, "NotoSansKR-Regular.ttf"),
        (700, "Noto Sans KR", "Bold", True, "NotoSansKR-Bold.ttf"),
        (350, "Noto Sans KR DemiLight", "Regular", False, "NotoSansKRDemiLight-Regular.ttf"),
    ]
    for weight, fam, sub, bold, fname in jobs:
        dst = OUT / fname
        if dst.exists():
            print(f"  {dst}  (이미 있음)")
            continue
        font = instance(weight)
        set_names(font, fam, sub, bold=bold)
        font.save(dst)
        print(f"  {dst}  ({dst.stat().st_size // 1024}KB)  family={fam!r} sub={sub!r}")

    download_nanum()
    print("\n다음 -- 위 설명의 (2)설치 (3)SaveAs 단계를 진행하세요.")


if __name__ == "__main__":
    main()
