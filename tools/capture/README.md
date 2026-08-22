# 시연영상 화면 녹화

`docs/가이드/시연_대본.md` 의 컷을 **사람 손 없이** 찍기 위한 스크립트입니다.
같은 컷을 몇 번이고 똑같이 다시 찍을 수 있습니다 — 대본이 바뀌거나 화면을
고치면 다시 돌리세요.

| 스크립트 | 무엇을 찍나 | 어떻게 |
|---|---|---|
| `capture_app.sh` | 선제 접촉 (앱) | `adb screenrecord` + 스크립트 조작 |
| `capture_cut23.sh` | 성격 선택·대화 / 라이프로그·리포트 | 같음 (`2` 또는 `3` 인자) |
| `capture_admin.js` | 관제 웹 | Playwright (조작 + 녹화 동시에) |
| `build_video.sh` | **위를 이어 3분 완성본** | ffmpeg |
| `type_unicode.ps1` | (실패 기록) 한글 입력 시도 | 아래 참고 |

```bash
MSYS_NO_PATHCONV=1 bash tools/capture/capture_app.sh
MSYS_NO_PATHCONV=1 bash tools/capture/capture_cut23.sh 2
MSYS_NO_PATHCONV=1 bash tools/capture/capture_cut23.sh 3
node tools/capture/capture_admin.js
bash tools/capture/build_video.sh          # → final/lisn_demo_3min.mp4
```

## 왜 도구가 두 개인가

**브라우저 화면은 `adb screenrecord` 로 못 잡습니다.** 데스크톱 캡처
(ffmpeg `gdigrab`)로 잡을 수는 있지만 **조작을 스크립트로 못 해서** 마우스를
손으로 움직여야 하고, 창 위치가 바뀌면 좌표가 전부 어긋납니다.

Playwright 는 조작과 녹화를 함께 합니다. 뷰포트가 1280×720 로 고정이라
몇 번을 다시 찍어도 같은 화면이 나옵니다.

## 준비

```powershell
winget install --id Gyan.FFmpeg -e
```

```powershell
npm install playwright
npx playwright install chromium
```

`ffmpeg.exe` 경로를 `/tmp/ffmpeg_path` 에 한 줄로 적어 두면 두 스크립트가
읽어 갑니다(PATH 에 없어도 됩니다).

## 앱 — 컷 1

```bash
MSYS_NO_PATHCONV=1 bash tools/capture/capture_app.sh
```

서버 셋과 에뮬레이터가 떠 있어야 하고, 앱에 FCM 토큰이 등록돼 있어야 합니다.

## 관제 웹 — 컷 4

```bash
node tools/capture/capture_admin.js
```

백엔드(8000)와 관리자 웹(5173)이 떠 있어야 합니다.

⚠ **컷 2(위기 발화)를 먼저 찍고 오세요.** 이 스크립트는 위기 사건 이력에서
`chat-crisis-*` 행에 커서를 세웁니다. 그 행이 없으면 경고를 찍고 넘어갑니다.

---

## ⚠ 여기서 실제로 겪은 함정들

같은 데를 다시 밟기 쉬워서 남깁니다.

### 앱

- **`force-stop` 만 하면 푸시가 안 옵니다.** 강제 종료된 앱은 Android 의
  stopped state 에 들어가, 사용자가 직접 실행하기 전까지 **FCM 을 받지
  못합니다.** 알림이 통째로 안 와서 「No notifications」만 찍혔습니다.
  → **종료 → 한 번 띄워 홈에 세움 → 백그라운드** 순서로 갑니다.
- **홈 버튼만 눌러서도 안 됩니다.** 앱이 직전 화면(예: 대화 화면)에 머물러
  있어서, 알림을 눌러도 홈이 아니라 **그 화면이 되살아납니다.** 선제 접촉
  카드가 영상에 안 나옵니다.
- **헤드업 배너를 노리지 마세요.** 몇 초 만에 사라지고, 사라진 자리를
  맹목적으로 누르면 엉뚱한 화면이 열립니다(Google 설정 마법사가 열렸습니다).
  알림 그림자를 내려 **보이는 상태에서** 누르세요.
- **시스템 알림을 미리 지우세요.** 「Set a screen lock」·「Physical keyboards
  configured」가 우리 알림 밑에 같이 찍힙니다. `Clear all` 로 안 지워지면
  **개별로 오른쪽으로 밀어** 지웁니다.
- **같은 알림을 여러 번 보내면 묶입니다.** 「2 ⌄」로 접혀서 문구가 잘립니다.
  찍기 전에 알림을 비우세요.
- **`screenrecord` 는 30초 언저리에서 끊길 수 있습니다.** `--time-limit 90`
  을 줘도 그렇습니다. 흐름을 그 안에 담도록 대기 시간을 조절하세요.
### ⚠ 한글 입력은 자동화가 **안 됩니다** — 세 가지를 다 해봤습니다

| 시도 | 결과 |
|---|---|
| `adb shell input text` | **ASCII 만** 들어갑니다 |
| 기기 IME 교체 | 에뮬레이터에 한글 IME 가 **없습니다**(LatinIME · 음성 둘뿐) |
| 호스트 키보드 유니코드 주입 (`type_unicode.ps1`) | **글자가 깨집니다** |

마지막 것은 두 단계로 막혔습니다.

1. `SetForegroundWindow` 가 **조용히 실패**합니다. Windows 는 포그라운드가
   아닌 프로세스의 창 끌어오기를 거부합니다. `AttachThreadInput` 으로
   우회하면 포커스는 갑니다(스크립트에 넣어 뒀습니다).
2. 포커스가 가도 **에뮬레이터가 유니코드를 안 받습니다.** `KEYEVENTF_UNICODE`
   로 보낸 글자를 **스캔코드로 해석**해서, 「요즘 잠이 잘 안 와요」가 `cc` 로
   들어갔습니다.

**그래서 한글이 필요한 장면은 두 길뿐입니다.**

- **빠른 답장 칩을 누릅니다.** 칩이 한글을 입력창에 넣어 줍니다 —
  `capture_cut23.sh` 가 이 방법을 씁니다. 대화 컷은 이걸로 전부 됩니다.
- **위기 발화만은 사람이 칩니다.** 칩에 위기 문장이 있을 리 없으니
  자동화할 방법이 없습니다. 에뮬레이터는 물리 키보드를 받으므로 한글 IME 로
  그냥 치면 됩니다.

⚠ 외부 IME APK 를 받아 설치하지 마세요.

### 경로 (Git Bash + 윈도우 바이너리)

**이게 제일 많이 물렸습니다.** `adb` 와 `ffmpeg` 은 둘 다 윈도우 바이너리인데
Git Bash 에서 부릅니다.

- 그냥 부르면 MSYS 가 `/sdcard/x.png` 를 `C:\Program Files\Git\sdcard\x.png`
  로 바꿔 버립니다 → `MSYS_NO_PATHCONV=1` 이 필요합니다.
- 그런데 그러면 **목적지 유닉스 경로도 변환되지 않아** 윈도우 바이너리가
  파일을 못 씁니다. `cygpath -w` 로 직접 바꿔 넘겨야 합니다.
- 두 함정이 반대 방향이라 하나만 고치면 다른 쪽이 깨집니다.

### 관제 웹

- **Playwright 녹화에는 마우스 커서가 안 찍힙니다.** 그대로 두면 클릭이
  저절로 일어나는 것처럼 보입니다 — 「조작하는 영상」이 아니라 「화면이
  바뀌는 영상」이 됩니다. 그래서 커서를 페이지에 그려 넣습니다.
- Vite 는 `localhost`(IPv6)에만 붙고 `127.0.0.1` 에는 안 붙을 수 있습니다.

---

## 3분 완성본

`build_video.sh` 가 컷들을 1920×1080 캔버스에 얹어 이어붙입니다.

- **세로·가로가 섞여 있습니다.** 앱은 9:16, 관제 웹은 16:9 라 앱 컷은
  오른쪽에 세우고 왼쪽에 설명을 답니다.
- **앱 컷은 실제보다 빠릅니다.** 에뮬레이터 인코더가 못 따라가 45초 조작이
  32초로 기록됩니다. `setpts` 로 늘려 되돌립니다 — 화면이 거의 정지라
  프레임이 빠져도 눈에 안 띕니다.
- **긴급 상담 화면은 정지 컷**입니다. 위기 판정이 있어야 뜨는 화면인데
  한글을 못 쳐서, `SCREEN=emergency` 로 실제 화면을 띄워 캡처했습니다.
  화면 자체는 진짜지만 **「방금 판정이 나서 전환됐다」고 말하면 안 됩니다.**
  자막도 「위기가 확인되면 …합니다」라는 동작 설명으로 썼습니다.

## 결과물

`out/` 에 webm 원본, `cuts/` 에 편집기·PowerPoint 에서 바로 쓰는 mp4
(H.264 · yuv420p)가 들어갑니다. 둘 다 **소리가 없습니다** — 나레이션은
편집에서 얹으세요.
