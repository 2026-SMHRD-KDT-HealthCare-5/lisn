# 화면 시안 (docs/design)

화면설계서에 넣을 신규 화면 시안입니다. **코드로 만들고 PNG 로 굽습니다.**

```
docs/design/
├── MAIN_EMERGENCY_01.png     완성 시안 (780×1688 = 390×844 @2x)
└── src/
    └── MAIN_EMERGENCY_01.html  원본 HTML. 수정은 여기서 하고 다시 렌더한다
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

| 화면 | 상태 |
|---|---|
| `MAIN_EMERGENCY_01` 긴급 상담 연결 | ✅ 완료 |
| `MAIN_LOGIN_02` 비밀번호 재설정 | 대기 |
| `MAIN_SETTING_02` 계정 관리·회원 탈퇴 | 대기 |
| `MAIN_REPORT_01` 정서 리포트 | 대기 |
| `ADMIN_LOGIN_01` 관리자 로그인 (웹) | 대기 |
| `ADMIN_DASH_01` 관리자 관제 (웹) | 대기 |

명세는 [`../review/화면설계서_개정안.md`](../review/화면설계서_개정안.md) Part B 참조.

## 미결

- 상단 `마음이 ♥` 의 하트를 텍스트로 둘지 이모지(💙)로 둘지. 원본 시안은 이모지, 현재 시안은 텍스트 + 포인트 색. 아이콘을 전부 SVG 로 통일했으므로 하트도 SVG 로 맞추는 방안이 있음
- **PPTX 에 슬라이드를 새로 추가하는 것은 미검증**입니다. slide XML · rels · presentation.xml · [Content_Types].xml 네 곳을 등록해야 합니다. 기존 슬라이드를 복제해 이미지만 교체하는 방식이 안전하나 확인이 필요합니다. 현재는 **PNG 만 제공하고 배치는 함은선 님이** 하는 것을 전제로 합니다.
