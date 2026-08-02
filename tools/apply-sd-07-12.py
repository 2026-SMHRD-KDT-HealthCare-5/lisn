# -*- coding: utf-8 -*-
"""화면설계서 SD-07 · SD-12 반영 (2026.08.02 1회용)

두 건 모두 **화면설명이 한 줄 늘어납니다.** 기존 스크립트들은 런 내용만
바꿨는데, 줄을 늘리려면 문단(`<a:p>`)을 새로 만들어야 합니다.

## 문단을 복제합니다

마지막 `<a:p>` 를 그대로 복사해 뒤에 붙이고 글자만 바꿉니다. 서식이
문단 속성(`<a:pPr>`)과 런 속성(`<a:rPr>`)에 흩어져 있어서, 새로 쓰는 것보다
복제가 안전합니다.

## SD-07 — MAIN_LOGIN_01

시안에 「비밀번호를 잊으셨나요? 비밀번호 찾기」 링크가 있는데 화면설명에
없었습니다. `MLCM_102` 진입점이 화면설계서에서 빠져 있던 셈입니다.
유스케이스 ID 도 `MLCM_100 / MLCM_102` 로 바꿉니다(Part C 잔여 1건).

## SD-12 — MAIN_CHAT_02

「대화 기록 조회/삭제」가 화면개요에는 있는데 화면설명에는 없었습니다.
시안에도 대화 기록 카드가 그려져 있습니다.
중복으로 들어간 「화면개요」 라벨 하나도 함께 지웁니다.
"""
import re
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

DECK = Path('Documents/화면설계서_귀기울임.pptx')


def set_runs(xml, updates):
    out, pos, idx = [], 0, 0
    for m in re.finditer(r'(<a:t>)([^<]*)(</a:t>)', xml):
        out.append(xml[pos:m.start()])
        body = updates.get(idx, m.group(2))
        body = body.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        out.append(m.group(1) + body + m.group(3))
        pos, idx = m.end(), idx + 1
    out.append(xml[pos:])
    return ''.join(out)


def clone_last_para(xml, marker_text, new_runs):
    """`marker_text` 런이 들어 있는 도형의 마지막 문단을 복제해 뒤에 붙입니다."""
    for sp in re.findall(r'<p:sp>.*?</p:sp>', xml, re.S):
        if f'<a:t>{marker_text}</a:t>' not in sp:
            continue
        paras = re.findall(r'<a:p>.*?</a:p>', sp, re.S)
        # ⚠ 마지막 문단이 **빈 문단**인 경우가 있습니다(런 0개). 그걸 복제하면
        #   글자를 넣을 자리가 없습니다. 런이 충분한 마지막 문단을 고릅니다.
        usable = [q for q in paras
                  if len(re.findall(r'<a:t>[^<]*</a:t>', q)) >= len(new_runs)]
        if not usable:
            continue
        last = usable[-1]
        clone = last
        texts = re.findall(r'<a:t>[^<]*</a:t>', clone)
        if len(texts) < len(new_runs):
            raise SystemExit(f'복제 대상 문단의 런이 {len(texts)}개뿐입니다')
        for i, t in enumerate(texts):
            val = new_runs[i] if i < len(new_runs) else ''
            val = val.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            clone = clone.replace(t, f'<a:t>{val}</a:t>', 1)
        new_sp = sp.replace(last, last + clone, 1)
        return xml.replace(sp, new_sp, 1)
    raise SystemExit(f'{marker_text} 를 가진 도형을 찾지 못했습니다')


def move_marker(xml, char, xy):
    for sp in re.findall(r'<p:sp>.*?</p:sp>', xml, re.S):
        if ''.join(re.findall(r'<a:t>([^<]*)</a:t>', sp)) != char:
            continue
        return xml.replace(sp, re.sub(r'<a:off x="-?\d+" y="-?\d+"/>',
                                      f'<a:off x="{xy[0]}" y="{xy[1]}"/>', sp, 1), 1)
    raise SystemExit(f'마커 {char} 없음')


def add_marker(xml, src_char, new_char, xy):
    """기존 마커 도형을 복제해 새 번호를 만듭니다."""
    for sp in re.findall(r'<p:sp>.*?</p:sp>', xml, re.S):
        if ''.join(re.findall(r'<a:t>([^<]*)</a:t>', sp)) != src_char:
            continue
        nid = max(int(i) for i in re.findall(r'<p:cNvPr id="(\d+)"', xml)) + 1
        clone = re.sub(r'<p:cNvPr id="\d+" name="[^"]*"',
                       f'<p:cNvPr id="{nid}" name="가로 글상자 {nid}"', sp, 1)
        clone = re.sub(r'<a:off x="-?\d+" y="-?\d+"/>',
                       f'<a:off x="{xy[0]}" y="{xy[1]}"/>', clone, 1)
        clone = clone.replace(f'<a:t>{src_char}</a:t>', f'<a:t>{new_char}</a:t>')
        return xml.replace('</p:spTree>', clone + '</p:spTree>', 1)
    raise SystemExit(f'복제 원본 {src_char} 없음')


IMG_X, IMG_W, IMG_H = 5135035, 2379765, 5150055


def at(px, py):
    return (int(IMG_X + px / 780 * IMG_W - 133350), int(py / 1688 * IMG_H - 133350))


def main():
    src = ZipFile(DECK)
    items = {n: src.read(n) for n in src.namelist()}
    infos = {n: src.getinfo(n) for n in src.namelist()}
    src.close()

    # ── SD-07 · Part C — MAIN_LOGIN_01 ────────────────────────────────
    part = 'ppt/slides/slide7.xml'
    xml = items[part].decode('utf-8')
    xml = set_runs(xml, {
        2: ' 이메일 입력창: 계정 이메일 입력', 3: '', 4: '', 5: '', 6: '',
        8: ' 비밀번호 입력창: 마스킹 처리 입력',
        10: ' 로그인 버튼: JWT 발급 후 MAIN_HOME_01 이동',
        12: ' 비밀번호 찾기: MAIN_LOGIN_02 이동',
        18: 'MLCM_100 / MLCM_102',            # Part C 재매핑 잔여 1건
    })
    xml = clone_last_para(xml, '❹', ['❺', ' 회원가입 버튼: MAIN_JOIN_01 이동'])
    # 시안의 요소 위치에 맞춰 ❹(비밀번호 찾기)·❺(회원가입) 배치
    xml = move_marker(xml, '❹', at(50, 1183))
    xml = add_marker(xml, '❹', '❺', at(50, 1277))
    items[part] = xml.encode('utf-8')
    print('  SD-07  MAIN_LOGIN_01  ❹ 비밀번호 찾기 신설 · ❺ 회원가입 · MLCM_102 추가')

    # ── SD-12 — MAIN_CHAT_02 ──────────────────────────────────────────
    part = 'ppt/slides/slide12.xml'
    xml = items[part].decode('utf-8')
    xml = set_runs(xml, {
        4: ' 대화 메시지 영역',                      # '메세지' 오타도 함께
        8: ' 대화 기록: 세션 목록 최근순 조회·상세·삭제', 9: '', 10: '',
        25: '',                                     # 중복 「화면개요」 라벨
    })
    xml = clone_last_para(xml, '❹', ['❺', ' 대화종료: 홈 화면(MAIN_HOME_01)으로 이동'])
    xml = move_marker(xml, '❹', at(60, 600))        # 대화 기록 카드
    xml = add_marker(xml, '❹', '❺', (7137371, 55810))  # 대화 종료 버튼
    items[part] = xml.encode('utf-8')
    print('  SD-12  MAIN_CHAT_02   ❹ 대화 기록 신설 · ❺ 대화종료 · 중복 라벨 삭제')

    with ZipFile(DECK, 'w', ZIP_DEFLATED) as z:
        for n in items:
            z.writestr(infos.get(n, n), items[n])
    print('\n적용 완료')


if __name__ == '__main__':
    main()
