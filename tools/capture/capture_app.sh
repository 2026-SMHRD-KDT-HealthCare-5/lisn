#!/usr/bin/env bash
#
# 앱 화면 녹화 — 시연영상 컷 1 (선제 접촉)
#
#   앱이 꺼진 상태 → 푸시 도착 → 알림 확인 → 탭 → 홈 카드 → 답장하기
#                → 이어받은 대화 화면
#
# ⚠ **답장 타이핑은 여기서 안 합니다.** 에뮬레이터에 한글 IME 가 없어
#   `adb shell input text` 로 한글을 넣을 수 없습니다. 외부 IME APK 설치는
#   하지 않습니다. 그 부분은 사람이 호스트 키보드로 직접 치면서 찍으세요 —
#   에뮬레이터는 물리 키보드 입력을 받습니다.
#
# ⚠ `screenrecord` 는 **최대 180초**이고 소리를 담지 않습니다.
#
# ⚠ **경로 함정.** 이 스크립트는 `MSYS_NO_PATHCONV=1` 로 돌려야 합니다
#   (안 그러면 `/sdcard/...` 가 윈도우 경로로 바뀌어 adb 가 실패). 그런데
#   그러면 **유닉스 경로가 윈도우 바이너리에 그대로 전달**됩니다. adb 와
#   ffmpeg 둘 다 윈도우 바이너리이므로, 넘기는 경로는 전부 `cygpath -w`
#   로 바꿔야 합니다. 2026.08.22 에 여기서 두 번 날렸습니다.
#
# 사용:
#   MSYS_NO_PATHCONV=1 bash capture_app.sh
#   → cuts/cut1_outreach.mp4
#
set -uo pipefail

ADB="/c/Users/HOME/AppData/Local/Android/Sdk/platform-tools/adb.exe"
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/cuts"
FF="$(cat /tmp/ffmpeg_path)"
DEV="/sdcard/cut1.mp4"

mkdir -p "$OUT"
OUT_WIN="$(cygpath -w "$OUT")"
RAW_WIN="${OUT_WIN}\\_cut1_raw.mp4"
FINAL_WIN="${OUT_WIN}\\cut1_outreach.mp4"

say() { printf '  %s\n' "$*"; }

# ── 준비 --------------------------------------------------------------
say "터치 피드백 켜기"
"$ADB" shell settings put system show_touches 1

say "알림 그림자 정리"
"$ADB" shell cmd statusbar collapse
"$ADB" shell service call notification 1 >/dev/null 2>&1 || true

# ⚠ **force-stop 만 하고 끝내면 푸시가 안 옵니다.** 강제 종료된 앱은
#   Android 의 stopped state 에 들어가, 사용자가 직접 실행하기 전까지
#   **FCM 메시지를 받지 못합니다.** 2026.08.22 에 알림이 통째로 안 와서
#   「No notifications」만 찍혔습니다.
#
# ⚠ **홈 버튼만 눌러서도 안 됩니다.** 앱이 직전 화면(예: 대화 화면)에
#   머물러 있어서 알림을 눌러도 홈이 아니라 그 화면이 되살아나고,
#   선제 접촉 카드가 영상에 안 나옵니다.
#
#   그래서 **종료 → 한 번 띄워 홈에 세움 → 백그라운드** 순서로 갑니다.
say "앱을 홈 화면 상태로 초기화"
"$ADB" shell am force-stop com.lisn.maeume
sleep 1
"$ADB" shell monkey -p com.lisn.maeume -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1
sleep 12   # 스플래시 · 자동 로그인 · 홈 로딩
say "백그라운드로"
"$ADB" shell input keyevent KEYCODE_HOME
sleep 2

# ── 녹화 시작 ---------------------------------------------------------
say "녹화 시작"
"$ADB" shell screenrecord --bit-rate 8M --time-limit 90 "$DEV" &
REC_PID=$!
sleep 3   # 인코더가 뜨는 시간

# ── 1. 푸시 도착 ------------------------------------------------------
say "선제 접촉 알림 발송"
( cd /c/project/LISN/backend && PYTHONUTF8=1 \
  /c/project/LISN/.venv/Scripts/python.exe ../tools/demo_notify.py >/dev/null 2>&1 )
sleep 4   # 알림이 도착하는 시간

# ── 2. 알림 그림자 내리기 ---------------------------------------------
# ⚠ **헤드업 배너를 노리지 마세요.** 배너는 몇 초 만에 사라지고,
#   사라진 자리를 맹목적으로 누르면 엉뚱한 화면이 열립니다
#   (2026.08.22 에 Google 설정 마법사가 열렸습니다). 그림자를 내려
#   **보이는 상태에서** 누르는 편이 확실합니다.
say "알림 그림자 내리기"
"$ADB" shell input swipe 540 10 540 900 400
sleep 3   # 알림 문구를 읽을 시간

# ── 3. 알림 탭 → 앱 --------------------------------------------------
say "알림 탭"
"$ADB" shell input tap 540 760
sleep 7   # 앱이 앞으로 나오고 홈이 그려지는 시간

# ── 4. 홈의 선제 접촉 카드 --------------------------------------------
say "카드 전문 노출"
sleep 4   # 첫 마디를 읽을 시간

# ── 5. 답장하기 ------------------------------------------------------
say "답장하기 탭"
"$ADB" shell input tap 925 1061
sleep 6   # 대화 화면 · 이어받은 첫 마디

say "대화 화면 유지"
sleep 2

# ── 마무리 ------------------------------------------------------------
say "녹화 종료 대기"
"$ADB" shell pkill -SIGINT screenrecord 2>/dev/null || true
wait $REC_PID 2>/dev/null || true
sleep 3   # 파일이 닫히는 시간

say "기기에서 가져오기"
"$ADB" pull "$DEV" "$RAW_WIN" >/dev/null
"$ADB" shell rm -f "$DEV"

if [ ! -s "$OUT/_cut1_raw.mp4" ]; then
  say "[!] 기기에서 가져온 파일이 없습니다. 중단합니다."
  exit 1
fi

say "mp4 로 다시 인코딩 (편집기 호환)"
"$FF" -y -i "$RAW_WIN" -c:v libx264 -preset slow -crf 20 \
      -pix_fmt yuv420p -movflags +faststart "$FINAL_WIN" 2>&1 | tail -2
rm -f "$OUT/_cut1_raw.mp4"

say "완료 → $OUT/cut1_outreach.mp4"
