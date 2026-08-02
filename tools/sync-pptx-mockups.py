# -*- coding: utf-8 -*-
"""화면설계서 와이어프레임을 `docs/design/` 시안으로 맞춥니다.

각 슬라이드의 **화면 ID 를 읽어** 같은 이름의 PNG 를 찾아 넣습니다. 매핑을
손으로 적지 않으므로 슬라이드가 늘어도 그대로 돌아갑니다.

```powershell
python tools/sync-pptx-mockups.py            # 무엇이 바뀌는지만 봅니다
python tools/sync-pptx-mockups.py --apply    # 실제로 적용
```

## 왜 필요한가

PPTX 안 이미지는 `ppt/media/` 에 **복사본**으로 들어갑니다. `docs/design/` 시안을
고쳐도 덱은 그대로입니다. 둘이 갈리면 **설계서만 옛 화면을 보여줍니다.**

## ⚠ 그림이 2개인 슬라이드

`MAIN_JOIN_03` 은 두 장이 **같은 자리에 겹쳐** 있고(하나는 보이지도 않음),
`MAIN_CHAT_01` 은 성격 카드 두 장이 좌우로 놓여 있었습니다. 재제작 시안은
**한 장에 다 담고 있으므로** 첫 번째 그림만 남기고 나머지는 지웁니다.

## ⚠ 이 스크립트는 그림만 바꿉니다

화면설명 문구는 건드리지 않습니다. 시안과 문구가 어긋나는 항목(`SD-A③`~`SD-A⑥`)은
따로 처리해야 합니다.
"""
import argparse
import re
import struct
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

DECK = Path('Documents/화면설계서_귀기울임.pptx')
DESIGN = Path('docs/design')

# 폰 화면 그림의 표준 위치·크기(slide15 기준). 비율 0.4621 로 시안과 같습니다.
PHONE = {'off': (5135035, 0), 'ext': (2379765, 5150055)}
# 관리자 웹 시안은 가로형이라 따로 둡니다.
WEB = {'off': (3922000, 1075027), 'ext': (4800000, 3000000)}
WEB_SCREENS = {'ADMIN_LOGIN_01', 'ADMIN_DASH_01'}


def png_size(data):
    return struct.unpack('>II', data[16:24])


def screen_id_of(xml):
    """슬라이드의 화면 ID. '화면 ID' 라벨 **다음** 런들을 이어붙입니다.

    ⚠ 첫 번째로 나오는 MAIN_* 을 쓰면 안 됩니다. 화면설명 본문에도
      `MAIN_LOGIN_01 이동` 같은 참조가 들어 있어 엉뚱한 걸 집습니다.
    """
    runs = re.findall(r'<a:t>([^<]*)</a:t>', xml)
    for i, t in enumerate(runs):
        if t.strip() == '화면 ID':
            joined = ''.join(runs[i + 1:i + 5]).strip()
            m = re.match(r'[A-Z][A-Z_0-9]+', joined)
            return m.group(0) if m else None
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='실제로 씁니다')
    args = ap.parse_args()

    src = ZipFile(DECK)
    items = {n: src.read(n) for n in src.namelist()}
    infos = {n: src.getinfo(n) for n in src.namelist()}
    src.close()

    # 표시 순서
    pres = items['ppt/presentation.xml'].decode('utf-8')
    prels = items['ppt/_rels/presentation.xml.rels'].decode('utf-8')
    tgt = dict(re.findall(r'Id="([^"]+)"[^>]*Target="(slides/slide\d+\.xml)"', prels))
    order = [tgt[r] for r in re.findall(r'<p:sldId id="\d+" r:id="([^"]+)"/>', pres)]

    media_no = 200          # 기존 번호와 겹치지 않게
    changed = 0

    for pos, target in enumerate(order, 1):
        part = 'ppt/' + target
        xml = items[part].decode('utf-8')
        screen = screen_id_of(xml)
        if not screen:
            continue

        png = DESIGN / f'{screen}.png'
        if not png.exists():
            print(f'  {pos:2d} {screen:20s} ⚠ 시안 없음 — 건너뜁니다')
            continue

        pics = re.findall(r'<p:pic>.*?</p:pic>', xml, re.S)
        if not pics:
            print(f'  {pos:2d} {screen:20s} ⚠ 그림 도형이 없습니다')
            continue

        blob = png.read_bytes()
        w, h = png_size(blob)
        geo = WEB if screen in WEB_SCREENS else PHONE

        rels_part = f'ppt/slides/_rels/{Path(target).name}.rels'
        rels = items[rels_part].decode('utf-8')
        cur = dict(re.findall(r'Id="([^"]+)"[^>]*Target="\.\./media/([^"]+)"', rels))

        embed = re.search(r'r:embed="([^"]+)"', pics[0]).group(1)
        same = cur.get(embed) and items.get(f'ppt/media/{cur[embed]}') == blob
        note = []

        # 2번째 이후 그림은 제거 — 재제작 시안이 한 장에 다 담고 있습니다.
        for extra in pics[1:]:
            xml = xml.replace(extra, '')
            note.append('여분 그림 1개 제거')

        # 첫 그림: 이미지 교체 + 위치·크기 표준화
        media_no += 1
        media = f'ppt/media/image{media_no}.png'
        new_pic = pics[0]
        new_pic = re.sub(r'<a:off x="-?\d+" y="-?\d+"/>',
                         f'<a:off x="{geo["off"][0]}" y="{geo["off"][1]}"/>', new_pic)
        new_pic = re.sub(r'<a:ext cx="\d+" cy="\d+"/>',
                         f'<a:ext cx="{geo["ext"][0]}" cy="{geo["ext"][1]}"/>', new_pic)
        xml = xml.replace(pics[0], new_pic)

        if same and not note:
            print(f'  {pos:2d} {screen:20s} 이미 최신')
            continue

        items[media] = blob
        rels = re.sub(r'(<Relationship Id="' + embed + r'"[^>]*Target=")[^"]+(")',
                      lambda m: m.group(1) + f'../media/image{media_no}.png' + m.group(2),
                      rels)
        items[rels_part] = rels.encode('utf-8')
        items[part] = xml.encode('utf-8')
        changed += 1
        tail = (' · ' + ', '.join(note)) if note else ''
        print(f'  {pos:2d} {screen:20s} <- {png.name} ({w}x{h}){tail}')

    if not args.apply:
        print(f'\n{changed}장이 바뀝니다. 적용하려면 --apply')
        return

    with ZipFile(DECK, 'w', ZIP_DEFLATED) as z:
        for n in items:
            z.writestr(infos.get(n, n), items[n])

    # 참조 검증 — media 가 빠지면 「그림을 표시할 수 없습니다」가 뜹니다.
    with ZipFile(DECK) as z:
        names = set(z.namelist())
        for n in names:
            if not re.match(r'ppt/slides/_rels/slide\d+\.xml\.rels$', n):
                continue
            for t in re.findall(r'Target="\.\./media/([^"]+)"', z.read(n).decode('utf-8')):
                if f'ppt/media/{t}' not in names:
                    raise SystemExit(f'{n}: media/{t} 가 없습니다')
    print(f'\n{changed}장 적용 · 참조 검증 통과')


if __name__ == '__main__':
    main()
