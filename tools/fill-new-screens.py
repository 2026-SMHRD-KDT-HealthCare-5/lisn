# -*- coding: utf-8 -*-
"""화면설계서 신규 6화면 문안 채우기 — SD-N1~SD-N6 (2026.08.02 1회용)

`tools/add-pptx-slide.ps1` 로 slide15(MAIN_SETTING_01)를 6장 복제한 뒤,
각 슬라이드의 글자를 개정안 Part B 문안으로 갈아끼우고 표시 순서를 맞춥니다.

## 왜 인덱스로 바꾸나

`patch-pptx-text.ps1` 은 문자열 매칭인데, 이 슬라이드에는 **'설정' 이 두 번**
나옵니다(화면이름 · 메뉴경로). 문자열로는 어느 쪽인지 갈리지 않습니다.
그래서 `<a:t>` 의 **등장 순서**로 지정합니다.

## 서식이 유지되는 이유

`<a:t>` 안의 글자만 바꾸고 `<a:rPr>`(서식)은 건드리지 않습니다. 한 줄이 여러
런으로 쪼개진 곳(`MAIN_` + `SETTING` + `_01`)은 **첫 런에 전체 문장을 넣고
나머지를 빈 문자열**로 만듭니다 — patch-pptx-text.ps1 과 같은 방식입니다.
"""
import re
import shutil
import zipfile
from pathlib import Path

DECK = Path('Documents/화면설계서_귀기울임.pptx')

# slide15 의 <a:t> 등장 순서. 원본이 바뀌면 이 표도 바뀝니다.
I_CALLOUT = [2, 4, 6, 8, 10]   # ❶~❺ 본문
I_MARK5 = 9                    # ➎ 기호 (4줄짜리 화면에서는 비웁니다)
I_SCREEN_ID = [12, 13, 14]     # 'MAIN_' + 'SETTING' + '_01'
I_NAME = 16                    # 화면이름
I_USECASE = [18, 19]           # 'MLCM_' + '110 / MLCM_101'
I_OVERVIEW = 22                # 화면개요
I_MENU = 24                    # 메뉴경로

SCREENS = [
    {
        'file': 'slide16.xml',
        'id': 'MAIN_LOGIN_02',
        'name': '비밀번호 재설정 화면',
        'usecase': 'MLCM_102',
        'overview': '비밀번호 분실 시 이메일 인증을 통해 새 비밀번호로 재설정하는 화면',
        'menu': '로그인/비밀번호 찾기',
        'callouts': [
            ' 이메일 입력창: 가입 시 사용한 이메일 입력',
            ' 인증 메일 발송: 재설정 링크·인증 코드 발송',
            ' 발송 안내: 미가입 이메일도 동일 문구, 실제 미발송',
            ' 새 비밀번호 입력창: 새 비밀번호·확인 입력',
            ' 재설정 완료: 비밀번호 갱신 후 MAIN_LOGIN_01 이동',
        ],
        'after': 7,   # MAIN_LOGIN_01 뒤
        'png': 'MAIN_LOGIN_02',
    },
    {
        'file': 'slide17.xml',
        'id': 'MAIN_REPORT_01',
        'name': '정서 리포트 화면',
        'usecase': 'MLCM_500',
        'overview': '본인의 기간별 감정 위험도 스코어 추이와 라이프로그 변화를 '
                    '대시보드로 조회하고 PDF로 내보내는 화면',
        'menu': '라이프로그/정서 리포트',
        'callouts': [
            ' 조회 기간: 주·월·직접 지정 전환. 변경 시 재조회',
            ' 감정 변화 곡선: 기간별 감정 스코어 추이 표시',
            ' 위험 단계 분포: 안정·주의·심각 단계 비율 표시',
            ' 결합 차트: 감정 추이와 수면·활동량 동일 시간축',
            ' 종합 요약 문구·PDF 내보내기 버튼 제공',
        ],
        'after': 14,  # MAIN_LIFELOG_01 뒤
        'png': 'MAIN_REPORT_01',
    },
    {
        'file': 'slide18.xml',
        'id': 'MAIN_SETTING_02',
        'name': '계정 관리 화면',
        'usecase': 'MLCM_103',
        'overview': '계정 정보를 확인하고 회원 탈퇴를 처리하는 화면',
        'menu': '설정/계정 관리',
        'callouts': [
            ' 계정 정보: 이메일, 이름, 가입일 표시',
            ' 비밀번호 변경: 현재 비밀번호 확인 후 변경',
            ' 회원 탈퇴: 탈퇴 절차 시작. 비밀번호 재입력 확인',
            ' 삭제 범위 안내: 라이프로그·체성분·대화·분석·기기',
            ' 최종 확인 후 탈퇴 처리, MAIN_LOGIN_01 복귀',
        ],
        'after': 15,  # MAIN_SETTING_01 뒤
        'png': 'MAIN_SETTING_02',
    },
    {
        'file': 'slide19.xml',
        'id': 'MAIN_EMERGENCY_01',
        'name': '긴급 상담 연결 화면',
        'usecase': 'MLCM_510',
        'overview': '정서 위험도가 CRITICAL로 판정된 경우 콘텐츠 추천을 중단하고 '
                    '전문 상담기관 직통 연결을 안내하는 화면',
        'menu': '(전역 · CRITICAL 판정 시 자동 노출)',
        'callouts': [
            ' 상태 안내: 도움이 필요한 신호가 감지되었음을 안내',
            ' 긴급 상담 연결: 109 자살예방상담전화 통화 연결',
            ' 개인정보 안내: 전화 앱만 실행, 분석 데이터 미전송',
            ' 닫기: 이전 화면 복귀. 판정 이력은 기록됨',
            ' 노출 중 힐링 콘텐츠 추천은 표시하지 않음',
        ],
        'after': 15,
        'png': 'MAIN_EMERGENCY_01',
    },
    {
        'file': 'slide20.xml',
        'id': 'ADMIN_LOGIN_01',
        'name': '관리자 로그인 화면',
        'usecase': 'MLCM_100 / MLCM_501',
        'overview': '관리자가 관제 대시보드에 접근하기 위해 로그인하는 웹 화면',
        'menu': '(관리자 웹) 로그인',
        # ⚠ 유일하게 4줄입니다. ❹ 예외를 남길 여유가 있어 그대로 뒀습니다.
        'callouts': [
            ' 이메일 입력창: 관리자 계정 이메일 입력',
            ' 비밀번호 입력창: 마스킹 처리 입력',
            ' 로그인 버튼: 인증 성공 시 ADMIN_DASH_01 이동',
            ' 관리자 권한이 아니면 접근 불가 안내 노출',
            '',   # ➎ 없음
        ],
        'after': 15,
        'png': 'ADMIN_LOGIN_01',
        'web': True,
    },
    {
        'file': 'slide21.xml',
        'id': 'ADMIN_DASH_01',
        'name': '관리자 관제 대시보드',
        'usecase': 'MLCM_501',
        'overview': '관리자가 전체 사용자의 위험도 분포를 요약 조회하고 '
                    '고위험군을 우선 식별하는 웹 화면',
        'menu': '(관리자 웹) 관제 대시보드',
        'callouts': [
            ' 위험도 분포 요약: 안정·주의·심각 인원수 집계',
            ' 대상자 목록: 심각·주의 우선 정렬, 평가일시·점수',
            ' 대상자 상세: 기간별 감정 스코어·라이프로그 차트',
            ' 위기 사건 조회: 긴급 상담 연결 노출 이력 확인',
            ' 관리자 권한 계정만 접근 가능',
        ],
        'after': 15,
        'png': 'ADMIN_DASH_01',
        'web': True,
    },
]


# 와이어프레임 그림 도형의 자리. slide15 기준값입니다.
#   off (5135035, 0)  ext (2379765, 5150055)  비율 0.462 = 폰 화면
PHONE_OFF = (5135035, 0)
PHONE_EXT = (2379765, 5150055)

# ⚠ 관리자 웹 시안은 **가로형(1280x800, 비율 1.60)** 입니다. 폰 프레임에 그대로
#   넣으면 세로로 찌그러집니다. 오른쪽 패널(x 2738000~9906000, y 0~5150055)
#   안에 비율을 지켜 가운데 배치합니다.
WEB_EXT = (4800000, 3000000)
WEB_OFF = (2738000 + (7168000 - 4800000) // 2,
           (5150055 - 3000000) // 2)


def esc(text):
    """XML 특수문자. 화면개요에 & 가 들어갈 수 있습니다."""
    return (text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def set_runs(xml, updates):
    """{인덱스: 새 글자} 로 <a:t> 내용을 바꿉니다. 서식은 건드리지 않습니다."""
    out, idx = [], 0
    pos = 0
    for m in re.finditer(r'(<a:t>)([^<]*)(</a:t>)', xml):
        out.append(xml[pos:m.start()])
        body = esc(updates[idx]) if idx in updates else m.group(2)
        out.append(m.group(1) + body + m.group(3))
        pos = m.end()
        idx += 1
    out.append(xml[pos:])
    return ''.join(out), idx


def main():
    if not DECK.exists():
        raise SystemExit(f'파일이 없습니다: {DECK}')
    backup = DECK.with_suffix('.pptx.bak')
    shutil.copy2(DECK, backup)

    # ---- 1. 글자 교체 -------------------------------------------------
    from zipfile import ZipFile, ZIP_DEFLATED
    src = ZipFile(DECK)
    items = {n: src.read(n) for n in src.namelist()}
    infos = {n: src.getinfo(n) for n in src.namelist()}
    src.close()

    for sc in SCREENS:
        part = f'ppt/slides/{sc["file"]}'
        xml = items[part].decode('utf-8')

        updates = {}
        for i, text in zip(I_CALLOUT, sc['callouts']):
            updates[i] = text
        if sc['callouts'][4] == '':
            updates[I_MARK5] = ''        # ➎ 기호도 같이 지웁니다

        updates[I_SCREEN_ID[0]] = sc['id']
        updates[I_SCREEN_ID[1]] = ''
        updates[I_SCREEN_ID[2]] = ''
        updates[I_NAME] = sc['name']
        updates[I_USECASE[0]] = sc['usecase']
        updates[I_USECASE[1]] = ''
        updates[I_OVERVIEW] = sc['overview']
        updates[I_MENU] = sc['menu']

        new_xml, n = set_runs(xml, updates)
        if n != 26:
            raise SystemExit(f'{sc["file"]}: <a:t> 가 26개가 아닙니다 ({n}개). '
                             '원본 구조가 바뀌었으니 인덱스 표를 다시 만드세요.')

        # ---- 와이어프레임 시안 교체 ------------------------------------
        # 복제본은 원본과 같은 media 를 가리킵니다. 그대로 두면 화면 ID 는
        # MAIN_EMERGENCY_01 인데 그림은 설정 화면인 슬라이드가 됩니다.
        png = Path(f'docs/design/{sc["png"]}.png')
        if not png.exists():
            raise SystemExit(f'시안이 없습니다: {png}')
        media = f'ppt/media/image{100 + SCREENS.index(sc)}.png'
        items[media] = png.read_bytes()

        rels_part = f'ppt/slides/_rels/{sc["file"]}.rels'
        rels_xml = items[rels_part].decode('utf-8')
        embed = re.search(r'r:embed="([^"]+)"', new_xml).group(1)
        rels_xml = re.sub(
            r'(<Relationship Id="' + embed + r'"[^>]*Target=")[^"]+(")',
            lambda m: m.group(1) + '../media/' + Path(media).name + m.group(2),
            rels_xml)
        items[rels_part] = rels_xml.encode('utf-8')

        if sc.get('web'):
            # 가로형 시안. 폰 프레임 그대로 두면 찌그러집니다.
            new_xml = new_xml.replace(
                f'<a:off x="{PHONE_OFF[0]}" y="{PHONE_OFF[1]}"/>',
                f'<a:off x="{WEB_OFF[0]}" y="{WEB_OFF[1]}"/>')
            new_xml = new_xml.replace(
                f'<a:ext cx="{PHONE_EXT[0]}" cy="{PHONE_EXT[1]}"/>',
                f'<a:ext cx="{WEB_EXT[0]}" cy="{WEB_EXT[1]}"/>')

        items[part] = new_xml.encode('utf-8')
        shape = '웹 가로' if sc.get('web') else '폰'
        print(f'  {sc["file"]:12s} -> {sc["id"]:20s} 시안 {sc["png"]}.png ({shape})')

    # ---- 2. 표시 순서 --------------------------------------------------
    pres = items['ppt/presentation.xml'].decode('utf-8')
    rels = items['ppt/_rels/presentation.xml.rels'].decode('utf-8')
    rid_of = {t: i for i, t in
              re.findall(r'Id="([^"]+)"[^>]*Target="(slides/slide\d+\.xml)"', rels)}

    entries = re.findall(r'<p:sldId id="\d+" r:id="[^"]+"/>', pres)
    by_rid = {re.search(r'r:id="([^"]+)"', e).group(1): e for e in entries}

    order = [e for e in entries]
    # 붙여둔 6장을 일단 떼고, 뒤에서부터 제자리에 꽂습니다.
    for sc in SCREENS:
        order.remove(by_rid[rid_of[f'slides/{sc["file"]}']])

    # ⚠ `after` 가 같은 것끼리는 **역순으로** 꽂아야 합니다. 같은 자리에
    #   연달아 insert 하면 나중 것이 앞으로 밀려 순서가 뒤집힙니다.
    #   (SETTING_02·EMERGENCY·ADMIN_LOGIN·DASH 넷이 전부 after=15 입니다)
    for _, sc in sorted(enumerate(SCREENS), key=lambda p: (-p[1]['after'], -p[0])):
        order.insert(sc['after'], by_rid[rid_of[f'slides/{sc["file"]}']])

    pres = re.sub(r'<p:sldIdLst>.*?</p:sldIdLst>',
                  '<p:sldIdLst>' + ''.join(order) + '</p:sldIdLst>',
                  pres, flags=re.S)
    items['ppt/presentation.xml'] = pres.encode('utf-8')

    # ---- 3. 다시 쓰기 --------------------------------------------------
    # ⚠ `infos` 가 아니라 `items` 를 돌아야 합니다. infos 에는 **원본 파트만**
    #   있어서, infos 를 돌면 새로 넣은 media 가 통째로 빠집니다. 그러면
    #   rels 는 있는데 파일이 없어 PowerPoint 가 「그림을 표시할 수 없습니다」
    #   를 그립니다. 실제로 한 번 겪었습니다.
    for name in items:
        if name not in infos:
            print(f'  + 새 파트 {name}')
    with ZipFile(DECK, 'w', ZIP_DEFLATED) as z:
        for name in items:
            z.writestr(infos.get(name, name), items[name])

    # ---- 4. 이미지 참조가 실제로 해석되는지 -----------------------------
    with ZipFile(DECK) as z:
        names = set(z.namelist())
        for sc in SCREENS:
            rels = z.read(f'ppt/slides/_rels/{sc["file"]}.rels').decode('utf-8')
            for target in re.findall(r'Target="\.\./media/([^"]+)"', rels):
                if f'ppt/media/{target}' not in names:
                    raise SystemExit(f'{sc["file"]}: media/{target} 가 없습니다')
    print('  이미지 참조 검증 통과')

    print(f'\n완료. 원본 백업: {backup}')


if __name__ == '__main__':
    main()
