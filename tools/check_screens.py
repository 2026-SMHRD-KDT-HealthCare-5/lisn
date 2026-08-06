# -*- coding: utf-8 -*-
"""화면설계서 15화면 ↔ 앱·관리자웹 전수 대조

```powershell
python tools/check_screens.py
```

## 왜 만들었나

**화면설계서가 정본**인데(2026.07.30 결정) 대조를 사람이 눈으로 했습니다.
그래서 8/02 에 「전부 맞다」로 닫은 뒤 **두 건이 어긋난 채 나흘을 갔습니다.**

    PL-26        화면설계서는 「체수분」인데 앱은 「근육량」
    MAIN_LIFELOG_01 ❶  「최종 동기화 시각 표시」가 통째로 없음

둘 다 **사람 눈으로는 넘어가기 쉬운 형태**입니다. 앞엣것은 칸이 네 개
있으니 맞아 보이고, 뒤엣것은 기간 전환이 있으니 ❶ 이 된 것처럼 보입니다.

## 무엇을 하나

명세의 **화면설명 항목(❶❷❸…)에서 핵심어를 뽑아** 대응 파일에 있는지
봅니다. 절반 이상 못 찾으면 확인 후보로 올립니다.

⚠ **없다고 곧 결함은 아닙니다.** 다른 말로 구현했을 수 있습니다 —
「마스킹 처리」는 `obscureText: true` 입니다. **찾을 자리를 좁히는 것**이
목적이고, 판정은 사람이 합니다.

실측(2026.08.06) — 확인 후보 15건 중 **진짜 갭 2건**. 나머지는 표현 차이
였습니다. 그래도 **13건을 읽는 비용이 2건을 놓치는 비용보다 쌉니다.**

## 화면을 추가하면 MAP 에 넣으세요

여기 없는 화면은 **조용히 건너뜁니다.** 빠뜨리면 검사한 줄 알고 넘어갑니다.
"""
import io
import re
import sys
import pathlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
ROOT = pathlib.Path('.')
APP = ROOT / 'frontend' / 'app' / 'lib'
ADMIN = ROOT / 'frontend' / 'admin' / 'src'

# 화면 ID → 대응 파일들
MAP = {
    'MAIN_LOGIN_01': ['screens/login_screen.dart'],
    'MAIN_LOGIN_02': ['screens/password_reset_screen.dart'],
    'MAIN_JOIN_01': ['screens/join_screen.dart'],
    'MAIN_JOIN_02': ['screens/join_screen.dart'],
    'MAIN_JOIN_03': ['screens/join_screen.dart'],
    'MAIN_CHAT_01': ['screens/chat_screen.dart'],
    'MAIN_CHAT_02': ['screens/chat_screen.dart', 'screens/chat_history_screen.dart'],
    'MAIN_HOME_01': ['screens/home_screen.dart', 'screens/main_shell.dart'],
    'MAIN_LIFELOG_01': ['screens/lifelog_screen.dart'],
    'MAIN_REPORT_01': ['screens/report_screen.dart'],
    'MAIN_SETTING_01': ['screens/settings_screen.dart'],
    'MAIN_SETTING_02': ['screens/account_screen.dart'],
    'MAIN_EMERGENCY_01': ['screens/emergency_screen.dart'],
}
ADMIN_MAP = {
    'ADMIN_LOGIN_01': ['App.jsx', 'session.js'],
    'ADMIN_DASH_01': ['App.jsx', 'Report.jsx', 'labels.js'],
}

# 명세 항목에서 뽑을 핵심어 — 화면에 실제로 뜨거나 코드에 나올 말만.
STOP = re.compile(r'^(및|또는|등|표시|입력|버튼|화면|이동|확인|제공|가능|처리|안내)$')


def keywords(text):
    text = re.sub(r'\([^)]*\)', ' ', text)
    ws = re.findall(r'[가-힣A-Za-z_][가-힣A-Za-z_0-9]{1,}', text)
    return [w for w in ws if len(w) >= 2 and not STOP.match(w)]


spec = pathlib.Path('docs/extracted/화면설계서_귀기울임.txt').read_text(encoding='utf-8')
blocks = re.split(r'===== \[slide \d+\] =====', spec)

total_missing = 0
for blk in blocks:
    m = re.search(r'화면 ID\s*([A-Z_0-9 ]+?)\s*화면이름', blk)
    if not m:
        continue
    sid = m.group(1).replace(' ', '')
    files = MAP.get(sid) or ADMIN_MAP.get(sid)
    if not files:
        continue
    base = APP if sid in MAP else ADMIN
    body = ''
    for f in files:
        p = base / f
        if p.exists():
            body += p.read_text(encoding='utf-8')
        else:
            print(f'⚠ {sid}: {f} 없음')
    d = re.search(r'화면설명\s*(.+?)\s*화면 ID', blk, re.S)
    if not d:
        continue
    items = re.findall(r'([❶-❽])\s*([^❶-❽]{4,90}?)(?=\s*[❶-❽]|$)', d.group(1))

    miss = []
    for num, txt in items:
        txt = re.sub(r'\s+', ' ', txt).strip()
        kws = keywords(txt)
        if not kws:
            continue
        hit = sum(1 for k in kws if k in body)
        if hit / len(kws) < 0.4:
            miss.append((num, txt[:56], [k for k in kws if k not in body][:5]))
    if miss:
        total_missing += len(miss)
        print(f'\n## {sid}  ({", ".join(files)})')
        for num, txt, gone in miss:
            print(f'  {num} {txt}')
            print(f'      못 찾은 말: {", ".join(gone)}')

print(f'\n=== 확인 후보 {total_missing}건')
