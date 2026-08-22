#!/usr/bin/env bash
#
# 컷 2 (성격 선택 → 대화) · 컷 3 (라이프로그 → 리포트) 녹화
#
# ⚠ **한글을 치지 않습니다.** 에뮬레이터는 유니코드 키 주입을 스캔코드로
#   해석해서 엉뚱한 글자가 들어갑니다(실측: 한글 → "cc"). 대신 대화 화면의
#   **빠른 답장 칩**을 누릅니다 — 칩이 한글을 입력창에 넣어 줍니다.
#
# 사용: MSYS_NO_PATHCONV=1 bash capture_cut23.sh <2|3>

set -uo pipefail
CUT="${1:-2}"

ADB="/c/Users/HOME/AppData/Local/Android/Sdk/platform-tools/adb.exe"
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/cuts"; mkdir -p "$OUT"
OUT_WIN="$(cygpath -w "$OUT")"
FF="$(cat /tmp/ffmpeg_path)"
DEV="/sdcard/cut.mp4"

say() { printf '  %s\n' "$*"; }

# 화면 좌표 (1080x1920)
TAB_HOME=135; TAB_CHAT=405; TAB_LIFE=675; TAB_Y=1725
CHIP1_X=363; CHIP_Y=1374
INPUT_X=450; INPUT_Y=1535; SEND_X=965
PERSONA_GO_X=535; PERSONA_GO_Y=1380

start_rec() {
  "$ADB" shell screenrecord --size 720x1280 --bit-rate 6M --time-limit 120 "$DEV" &
  REC_PID=$!
  sleep 3
}
stop_rec() {
  "$ADB" shell pkill -SIGINT screenrecord 2>/dev/null || true
  wait $REC_PID 2>/dev/null || true
  sleep 3
  "$ADB" pull "$DEV" "${OUT_WIN}\\_raw.mp4" >/dev/null
  "$ADB" shell rm -f "$DEV"
  "$FF" -y -i "${OUT_WIN}\\_raw.mp4" -c:v libx264 -preset slow -crf 20 \
        -pix_fmt yuv420p -movflags +faststart "${OUT_WIN}\\$1" 2>&1 | tail -1
  rm -f "$OUT/_raw.mp4"
  say "완료 → $OUT/$1"
}

reset_app() {
  "$ADB" shell am force-stop com.lisn.maeume
  sleep 1
  "$ADB" shell monkey -p com.lisn.maeume -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1
  sleep 12
}

"$ADB" shell settings put system show_touches 1

if [ "$CUT" = "2" ]; then
  say "컷 2 — 성격 선택 → 대화"
  reset_app
  "$ADB" shell input tap $TAB_CHAT $TAB_Y      # AI 챗봇 탭
  sleep 4

  start_rec
  sleep 2
  say "성격 카드 좌우로 넘기기"
  "$ADB" shell input swipe 750 1100 300 1100 400   # 다음 성격
  sleep 3
  "$ADB" shell input swipe 300 1100 750 1100 400   # 되돌아오기
  sleep 3

  say "이 성격으로 대화하기"
  "$ADB" shell input tap $PERSONA_GO_X $PERSONA_GO_Y
  sleep 7                                          # 인사말

  say "빠른 답장 칩 — 한글이 입력창에 들어갑니다"
  "$ADB" shell input tap $CHIP1_X $CHIP_Y
  sleep 3

  say "전송"
  "$ADB" shell input tap $SEND_X $INPUT_Y
  sleep 18                                         # LLM 응답
  sleep 3
  stop_rec "cut2_chat.mp4"

elif [ "$CUT" = "3" ]; then
  say "컷 3 — 라이프로그 → 리포트"
  reset_app

  start_rec
  sleep 2
  say "라이프로그 탭"
  "$ADB" shell input tap $TAB_LIFE $TAB_Y
  sleep 6
  "$ADB" shell input swipe 540 1400 540 800 400    # 아래로
  sleep 4
  "$ADB" shell input swipe 540 800 540 1400 400    # 위로
  sleep 3

  say "홈 → 자세히 보기(리포트)"
  "$ADB" shell input tap $TAB_HOME $TAB_Y
  sleep 5
  "$ADB" shell input tap 925 1230                  # 오늘의 마음 상태 · 자세히 보기
  sleep 8
  "$ADB" shell input swipe 540 1400 540 700 400
  sleep 5
  stop_rec "cut3_report.mp4"
fi
