# 화면 시안 (docs/design)

화면설계서에 넣을 신규 화면 시안입니다. **코드로 만들고 PNG 로 굽습니다.**

```
docs/design/
├── MAIN_*.png                앱 시안 4장 (780×1688 = 390×844 @2x)
├── ADMIN_*.png               관리자 웹 시안 2장 (1280×800)
└── src/
    ├── common.css              공통 팔레트·카드·폼 스타일
    └── *.html                  화면별 원본 HTML
```

## 왜 이 방식인가

화면설계서의 기존 시안 9장은 **고충실도 디자인**(마스코트 일러스트 포함)이고 Figma 등에서 뽑은 PNG 입니다. 신규 화면 6장도 같은 결로 맞춰야 하는데,

- **Figma REST API 는 읽기 전용**입니다. 노드 생성은 Plugin API 로만 되고 그건 Figma 안에서 실행돼야 해서 외부에서 만들 수 없습니다.
- 신규 6장은 전부 **폼·리스트·차트**라 마스코트가 필요 없습니다. 팔레트와 카드 스타일만 맞추면 기존 시안 옆에 놓아도 위화감이 없습니다.

## 만드는 방법

### 1. 팔레트는 기존 시안에서 직접 추출한다

눈대중으로 맞추면 미세하게 어긋납니다. PPTX 안의 PNG 를 꺼내 픽셀을 찍습니다.

```powershell
Add-Type -AssemblyName System.Drawing
$bmp = New-Object System.Drawing.Bitmap("image9.png")
$c = $bmp.GetPixel(10, 10)
"#{0:X2}{1:X2}{2:X2}" -f $c.R, $c.G, $c.B
```

추출 결과 (`image9.png` = 메인 홈 대시보드 기준):

| 용도 | 값 |
|---|---|
| 배경 | `#EDF2FF` |
| 카드 | `#FFFFFF` |
| 제목 텍스트 | `#24325F` |
| 보조 텍스트 | `#A8ACBA` |
| 포인트 (활성 아이콘) | `#8A9CF0` |
| 주행동 버튼 | `#5A6BE0` |
| 파스텔 민트 / 블루 / 피치 | `#EAF8F4` / `#EAF5FF` / `#FFF0E9` |

### 2. 캔버스는 390 × 844

기존 시안과 동일합니다. 관리자 웹 화면은 1280 × 800 으로 잡습니다 (앱과 달라 보이는 게 정상).

### 3. 폰트는 Pretendard 를 CDN 으로 부른다

시안의 둥근 한글 서체가 Pretendard 계열입니다. 설치하지 않고 웹폰트로 불러도 **PNG 로 구워지므로 어느 PC 에서 열어도 동일**합니다.

```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css">
```

### 4. 아이콘은 이모지 대신 인라인 SVG

**이모지는 OS 가 자기 색으로 렌더해서 팔레트 밖으로 튑니다.** SVG 로 그리고 `fill`·`stroke` 를 팔레트 값으로 고정하세요.

### 5. Edge 헤드리스로 렌더

이 PC 에는 Node·Python 이 없지만 Edge 는 있습니다.

```powershell
$edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
& $edge --headless=new --disable-gpu --hide-scrollbars `
        --force-device-scale-factor=2 --window-size=390,844 `
        --virtual-time-budget=4000 `
        --screenshot="out.png" "file:///.../src/화면.html"
```

- `--force-device-scale-factor=2` — 2배 해상도. 발표 화면에서 안 뭉갬
- `--virtual-time-budget=4000` — 웹폰트 로딩을 기다림. 없으면 폰트가 안 붙은 채 찍힘

## 디자인 규칙

- **경고색(빨강·주황)을 쓰지 않습니다.** 정신건강 위기 UI 에서 경고색은 불안을 키워 회피를 유발합니다. 주목도는 색이 아니라 구조로 만듭니다 — 하단 네비게이션 제거, 요소 최소화, 주행동 버튼에만 그림자.
- 문구는 진단·단정이 아닌 권유조로 씁니다. `MLCM_510` 및 `FR-AI-002`(진단 금지)의 요건입니다.

## 진행 현황

| 화면 | 캔버스 | 상태 |
|---|---|---|
| `MAIN_EMERGENCY_01` 긴급 상담 연결 | 390×844 | ✅ **완료 — 이걸 복사해서 시작하세요** |
| `MAIN_LOGIN_02` 비밀번호 재설정 | 390×844 | ✅ 완료 |
| `MAIN_SETTING_02` 계정 관리·회원 탈퇴 | 390×844 | ✅ 완료 |
| `MAIN_REPORT_01` 정서 리포트 | 390×844 | ✅ 완료 |
| `ADMIN_LOGIN_01` 관리자 로그인 | 1280×800 | ✅ 완료 |
| `ADMIN_DASH_01` 관리자 관제 | 1280×800 | ✅ 완료 |

명세는 [`../review/화면설계서_개정안.md`](../review/화면설계서_개정안.md) Part B 참조.

## 시안을 다시 렌더하는 절차

각 화면의 HTML을 수정한 뒤 같은 이름의 PNG로 다시 렌더합니다. 새 화면을 추가할 때는 `src/MAIN_EMERGENCY_01.html`을 복사하고 `common.css`의 공통 스타일을 재사용하세요.

```powershell
# 1. 복사
Copy-Item docs\design\src\MAIN_EMERGENCY_01.html docs\design\src\MAIN_REPORT_01.html

# 2. 내용 수정 (아래 화면별 구성 참고)

# 3. 렌더
$edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
& $edge --headless=new --disable-gpu --hide-scrollbars `
        --force-device-scale-factor=2 --window-size=390,844 `
        --virtual-time-budget=4000 `
        --screenshot="docs\design\MAIN_REPORT_01.png" `
        "file:///$((Get-Location).Path -replace '\\','/')/docs/design/src/MAIN_REPORT_01.html"
```

관리자 웹 2장은 `--window-size=1280,800` 으로 바꾸고, HTML 의 `html, body { width/height }` 도 함께 고치세요.

### 화면별 구성

각 화면의 항목(❶❷❸)은 [`../review/화면설계서_개정안.md`](../review/화면설계서_개정안.md) Part B 에 문장으로 정의돼 있습니다. 그대로 UI 요소로 옮기면 됩니다.

| 화면 | 주요 구성 | 참고 |
|---|---|---|
| `MAIN_LOGIN_02` | 이메일 입력 → 발송 안내 → 새 비밀번호 입력 | 폼. 카드 2개면 충분 |
| `MAIN_SETTING_02` | 계정 정보 · 비밀번호 변경 · 탈퇴 버튼 · 삭제 범위 안내 | 리스트 + 경고성 안내 카드 |
| `MAIN_REPORT_01` | 기간 선택 · 감정 추이 곡선 · 위험 단계 분포 · PDF 내보내기 | **차트는 인라인 SVG 로 직접 그리세요.** 라이브러리를 CDN 으로 불러오면 렌더 타이밍이 어긋납니다 |
| `ADMIN_LOGIN_01` | 웹 중앙 정렬 로그인 폼 | 앱과 달라 보이는 게 정상 |
| `ADMIN_DASH_01` | 위험도 분포 요약 3칸 · 대상자 테이블 · 상세 패널 | 웹이라 여백과 밀도가 앱과 다름 |

### 주의

- **차트를 이미지로 넣지 마세요.** SVG 로 그리면 팔레트가 정확히 맞고 수정도 쉽습니다
- 리포트·대시보드의 숫자는 **그럴듯한 더미**를 넣되, `schema.sql` 의 값 범위를 지키세요 (`emotion_score` 0~100, `risk_level` 3종 등). 범위를 벗어난 값이 시안에 있으면 심사에서 지적됩니다
- 관리자 화면에 **실명을 넣지 마세요.** 위험도 목록은 `user_id` 앞 8자리 정도로 표기하는 편이 개인정보 설계와 일관됩니다

## 미결

- 상단 `마음이 ♥` 의 하트를 텍스트로 둘지 이모지(💙)로 둘지. 원본 시안은 이모지, 현재 시안은 텍스트 + 포인트 색. 아이콘을 전부 SVG 로 통일했으므로 하트도 SVG 로 맞추는 방안이 있음
- **PPTX 에 슬라이드를 새로 추가하는 것은 미검증**입니다. slide XML · rels · presentation.xml · [Content_Types].xml 네 곳을 등록해야 합니다. 기존 슬라이드를 복제해 이미지만 교체하는 방식이 안전하나 확인이 필요합니다. 현재는 **PNG 만 제공하고 배치는 함은선 님이** 하는 것을 전제로 합니다.
