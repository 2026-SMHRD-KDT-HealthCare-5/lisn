# -*- coding: utf-8 -*-
"""화면설계서 문안 교체 SD-A③~SD-A⑥ (2026.08.02 1회용)

문안 원문은 `docs/review/문서개정_체크리스트.md` 에 있습니다.

## 인덱스로 바꿉니다

`<a:t>` 등장 순서로 지정합니다. 문자열 매칭은 같은 낱말이 여러 번 나오는 곳에서
갈리지 않습니다. `<a:rPr>`(서식)은 건드리지 않으므로 폰트·크기가 유지됩니다.

## 콜아웃 번호는 본문 런에 그대로 넣어도 됩니다

마커 런과 본문 런의 서식이 **완전히 같습니다**(sz=1200, b=0, 맑은 고딕,
색 31333F). 그래서 `❻` 를 본문 문장 안에 끼워 넣어도 앞의 마커와 똑같이
보입니다. 실제로 `MAIN_JOIN_01` 이 원래부터 그렇게 쓰고 있었습니다.

## ⚠ 줄이 줄어드는 경우

한 줄을 없앨 때는 **마커 런과 본문 런을 둘 다** 빈 문자열로 만듭니다.
마커만 남기면 번호만 덩그러니 있는 줄이 생깁니다.
"""
import re
import shutil
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

DECK = Path('Documents/화면설계서_귀기울임.pptx')

PATCH = {
    # ── SD-A⑤ MAIN_HOME_01 ❶ 감정 이름 노출 제거 ─────────────────────
    # 감정 마스터에 「위기」·「절망」이 있어 그대로 띄우면 관찰이 아니라
    # 사람에 대한 판정으로 읽힙니다(02 「진단 금지」).
    'slide13.xml': {
        2: ' 오늘의 마음 상태: 상태 안내 문구와 정서 점수 표시',
    },

    # ── SD-A⑥① MAIN_SETTING_01 ❸ 페르소나 삭제 (5줄 → 4줄) ───────────
    'slide15.xml': {
        2: ' 웨어러블 연동: 기기명·연동 여부, 항목별 동의 개별 토글',
        4: ' 알림 설정: 맞춤 케어 알림 수신 토글',
        6: ' 계정 관리: 계정 관리·회원 탈퇴 화면(MAIN_SETTING_02) 이동',
        8: ' 로그아웃: 세션 무효화 후 로그인 화면(MAIN_LOGIN_01) 복귀',
        9: '',   # ❺ 마커
        10: '',  # ❺ 본문
    },

    # ── SD-A⑥② MAIN_CHAT_01 ❹ 최근 대화 배지 추가 (4줄) ──────────────
    # 첫 문단의 「-캐릭터 카드를 물리적으로(스와이프 형식) 선택하는 UI」는
    # 화면개요와 겹칩니다. 그 문단을 ❶ 로 당겨 쓰고 맨 뒤를 ❹ 로 씁니다.
    'slide11.xml': {
        1: '❶', 2: ' [F] 따스한 공감형 : 감정 경청 및 따뜻한 위로 중심',
        3: '', 4: '', 5: '', 6: '',
        7: '❷', 8: ' [T] 현실적인 조언형 : 객관적 상황 분석 및 문제 해결 중심',
        9: '', 10: '', 11: '', 12: '', 13: '',
        14: '❸', 15: ' 대화 시작: 실시간 대화 화면(MAIN_CHAT_02)으로 이동',
        16: '', 17: '', 18: '', 19: '', 20: '',
        21: '❹', 22: ' 최근 대화한 성격이 기본 표시되며 「최근 대화」 배지로 구분',
    },

    # ── SD-A④ ADMIN_DASH_01 대상자 검색 추가 (5줄 / 콜아웃 7개) ───────
    # 위험도 필터와 검색창은 화면에서 같은 줄에 있는 한 덩어리라 ❷~❸ 로 묶습니다.
    'slide21.xml': {
        4: '~❸ 조회 조건: 위험도 필터, 이름·이메일 검색',
        5: '❹', 6: ' 대상자 목록: 심각·주의 우선 정렬, 평가일시·점수',
        7: '❺', 8: ' 대상자 상세: 기간별 감정 스코어·라이프로그 차트',
        9: '❻', 10: ' 위기 사건 조회 · ❼ 관리자 권한 계정만 접근 가능',
    },

    # ── SD-A③ MAIN_JOIN_01 민감정보 동의 항목 분리 ────────────────────
    # ⚠ 체크리스트가 「무엇을 드러낼지」만 정하고 문안은 비워뒀습니다.
    #   개인정보보호법 제23조 제1항이 민감정보에 **별도 동의**를 요구하므로
    #   ❷~❹ 로 뭉쳐 있던 필수 동의를 항목별로 풀었습니다. 5줄 / 콜아웃 7개.
    'slide8.xml': {
        4: ' 서비스 이용약관 · ',
        5: '❸', 6: ' 개인정보 수집·이용 동의 (필수)',
        7: '❹', 8: ' 민감정보(생체·건강) 수집 동의: 별도 동의 (필수)',
        9: '❺', 10: ' 선택 동의 · ❻ 약관에 대한 상세내용',
        12: ' 필수 약관 모두 동의 시 기본정보 입력 단계로 이동',
        13: '', 14: '', 15: '', 16: '',
    },
}


def esc(t):
    return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def set_runs(xml, updates):
    out, pos, idx = [], 0, 0
    for m in re.finditer(r'(<a:t>)([^<]*)(</a:t>)', xml):
        out.append(xml[pos:m.start()])
        body = esc(updates[idx]) if idx in updates else m.group(2)
        out.append(m.group(1) + body + m.group(3))
        pos, idx = m.end(), idx + 1
    out.append(xml[pos:])
    return ''.join(out), idx


def main():
    shutil.copy2(DECK, DECK.with_suffix('.pptx.bak'))
    src = ZipFile(DECK)
    items = {n: src.read(n) for n in src.namelist()}
    infos = {n: src.getinfo(n) for n in src.namelist()}
    src.close()

    for slide, updates in PATCH.items():
        part = f'ppt/slides/{slide}'
        xml = items[part].decode('utf-8')
        before = re.findall(r'<a:t>([^<]*)</a:t>', xml)
        new_xml, n = set_runs(xml, updates)
        if max(updates) >= n:
            raise SystemExit(f'{slide}: 런이 {n}개인데 인덱스 {max(updates)} 를 씁니다')
        items[part] = new_xml.encode('utf-8')
        print(f'  {slide:13s} 런 {n}개 중 {len(updates)}개 교체')

    with ZipFile(DECK, 'w', ZIP_DEFLATED) as z:
        for n in items:
            z.writestr(infos.get(n, n), items[n])
    print('\n적용 완료')


if __name__ == '__main__':
    main()
