#!/usr/bin/env bash
#
# 컷들을 이어 3분짜리 시연영상으로 만듭니다.
#
# ⚠ **경로는 `cygpath -m` 로 넘깁니다.** `C:/Users/...` 형태라 백슬래시
#   이스케이프 지옥을 피할 수 있고 윈도우 ffmpeg 이 그대로 받습니다.
#
# ⚠ **세로·가로가 섞여 있습니다.** 앱은 9:16, 관제 웹은 16:9 입니다.
#   1920x1080 캔버스에 얹고, 앱 컷은 오른쪽에 세워 왼쪽에 설명을 답니다.
#
# ⚠ **앱 컷은 실제보다 빠릅니다.** 에뮬레이터 인코더가 못 따라가 프레임이
#   빠져서, 45초 조작이 32초로 기록됩니다. setpts 로 늘려 원래 속도에
#   가깝게 되돌립니다. 화면이 거의 정지 상태라 프레임이 빠져도 눈에
#   띄지 않습니다.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
D="$(cygpath -m "$HERE")"
FF="$(cat /tmp/ffmpeg_path)"
FP="$(dirname "$FF")/ffprobe.exe"
mkdir -p "$HERE/final" "$HERE/parts"
P="$D/parts"
OUT="$D/final"

# ffmpeg drawtext 는 경로의 콜론을 escape 해야 합니다.
FONT_B="C\\:/Windows/Fonts/malgunbd.ttf"
FONT_R="C\\:/Windows/Fonts/malgun.ttf"

NAVY="0x172147"
INDIGO="0x647BEC"
MUTED="0x7C86A5"
BG="0xF4F6FD"

W=1920; H=1080; FPS=30

say() { printf '  %s\n' "$*"; }
dur() { "$FP" -v error -show_entries format=duration -of csv=p=0 "$1"; }

# ---------------------------------------------------------------------------
#  카드 (타이틀 · 마무리)
# ---------------------------------------------------------------------------
card() {  # card <출력> <초> <윗줄> <큰줄> <아랫줄>
  local out="$1" sec="$2" kicker="$3" big="$4" sub="$5"
  "$FF" -y -f lavfi -i "color=c=${BG}:s=${W}x${H}:d=${sec}:r=${FPS}" \
    -vf "drawtext=fontfile='${FONT_B}':text='${kicker}':fontsize=34:fontcolor=${INDIGO}:x=(w-text_w)/2:y=380,drawtext=fontfile='${FONT_B}':text='${big}':fontsize=96:fontcolor=${NAVY}:x=(w-text_w)/2:y=450,drawtext=fontfile='${FONT_R}':text='${sub}':fontsize=38:fontcolor=${MUTED}:x=(w-text_w)/2:y=600" \
    -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p "$out" 2>/dev/null
}

TXT='drawtext=fontfile=@B@:text=@NO@:fontsize=30:fontcolor=@I@:x=170:y=360,drawtext=fontfile=@B@:text=@T@:fontsize=76:fontcolor=@N@:x=170:y=410,drawtext=fontfile=@R@:text=@L1@:fontsize=34:fontcolor=@M@:x=170:y=540,drawtext=fontfile=@R@:text=@L2@:fontsize=34:fontcolor=@M@:x=170:y=592'

captions() {  # captions <번호> <제목> <설명1> <설명2>
  local t="$TXT"
  t="${t//@B@/\'${FONT_B}\'}"; t="${t//@R@/\'${FONT_R}\'}"
  t="${t//@I@/${INDIGO}}"; t="${t//@N@/${NAVY}}"; t="${t//@M@/${MUTED}}"
  t="${t//@NO@/\'$1\'}"; t="${t//@T@/\'$2\'}"
  t="${t//@L1@/\'$3\'}"; t="${t//@L2@/\'$4\'}"
  printf '%s' "$t"
}

# ---------------------------------------------------------------------------
#  앱 컷 — 세로 영상을 오른쪽에, 설명을 왼쪽에
# ---------------------------------------------------------------------------
phone() {  # phone <입력> <출력> <목표초> <번호> <제목> <설명1> <설명2>
  local in="$1" out="$2" want="$3" no="$4" title="$5" l1="$6" l2="$7"
  local d factor cap
  d="$(dur "$in")"
  factor="$(awk -v a="$want" -v b="$d" 'BEGIN{printf "%.4f", a/b}')"
  cap="$(captions "$no" "$title" "$l1" "$l2")"
  say "  ${no} ${title} — ${d}s → ${want}s (x${factor})"
  "$FF" -y -i "$in" -f lavfi -i "color=c=${BG}:s=${W}x${H}:r=${FPS}" \
    -filter_complex "[0:v]setpts=${factor}*PTS,scale=-2:940,fps=${FPS}[ph];[1:v]trim=duration=${want},setpts=PTS-STARTPTS[bg];[bg][ph]overlay=x=1240:y=70:shortest=1[v0];[v0]${cap}[v]" \
    -map "[v]" -t "${want}" -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p "$out" 2>/dev/null
}

# ---------------------------------------------------------------------------
#  정지 화면 구간 — 긴급 상담 연결
#
#  ⚠ **녹화가 아니라 캡처입니다.** 이 화면은 위기 판정이 확정돼야 뜨는데,
#    한글을 못 쳐서(에뮬레이터에 한글 IME 없음) 위기 발화를 자동으로 만들 수
#    없습니다. 그래서 `SCREEN=emergency` 로 **실제 화면을 띄워 캡처**했습니다.
#
#    화면 자체는 진짜입니다. 다만 **「방금 판정이 나서 전환됐다」고 말하면
#    안 됩니다.** 자막도 「위기가 확인되면 …합니다」라는 동작 설명으로 씁니다.
# ---------------------------------------------------------------------------
still() {  # still <png> <출력> <초> <번호> <제목> <설명1> <설명2>
  local img="$1" out="$2" sec="$3" no="$4" title="$5" l1="$6" l2="$7"
  local cap
  cap="$(captions "$no" "$title" "$l1" "$l2")"
  say "  ${no} ${title} — 정지 ${sec}s"
  "$FF" -y -loop 1 -t "${sec}" -i "$img" -f lavfi -i "color=c=${BG}:s=${W}x${H}:r=${FPS}" \
    -filter_complex "[0:v]scale=-2:940,fps=${FPS}[ph];[1:v]trim=duration=${sec},setpts=PTS-STARTPTS[bg];[bg][ph]overlay=x=1240:y=70:shortest=1[v0];[v0]${cap}[v]" \
    -map "[v]" -t "${sec}" -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p "$out" 2>/dev/null
}

# ---------------------------------------------------------------------------
#  관제 컷 — 가로라 화면을 채우고 아래에 띠 설명
#
#  ⚠ **자막을 화면 밑에 붙이지 마세요.** 처음에 1740px 로 키웠더니 스크린샷
#    아래끝(1008)과 자막(985)이 겹쳤고, 줄여도 아랫줄이 캔버스 바닥에
#    18px 까지 닿았습니다. 발표 화면에서는 잘려 보입니다.
#
#    1500px → 높이 843. y=28 이면 28~871 을 차지하고, 자막은 900·958 에
#    놓여 **위로 29px, 아래로 93px** 이 남습니다.
# ---------------------------------------------------------------------------
desktop() {  # desktop <입력> <출력> <번호> <제목> <설명>
  local in="$1" out="$2" no="$3" title="$4" l1="$5"
  say "  ${no} ${title} — $(dur "$in")s"
  "$FF" -y -i "$in" -f lavfi -i "color=c=${BG}:s=${W}x${H}:r=${FPS}" \
    -filter_complex "[0:v]scale=1500:-2,fps=${FPS}[sc];[1:v]trim=duration=999,setpts=PTS-STARTPTS[bg];[bg][sc]overlay=x=(W-w)/2:y=28:shortest=1[v0];[v0]drawtext=fontfile='${FONT_B}':text='${no}  ${title}':fontsize=42:fontcolor=${NAVY}:x=(w-text_w)/2:y=900,drawtext=fontfile='${FONT_R}':text='${l1}':fontsize=29:fontcolor=${MUTED}:x=(w-text_w)/2:y=958[v]" \
    -map "[v]" -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p "$out" 2>/dev/null
}

# ---------------------------------------------------------------------------
#  내레이션 얹기
#
#  ⚠ **구간마다 따로 얹고 나서 이어붙입니다.** 통짜 음성 하나를 만들어
#    맞추면, 구간 길이를 조금만 바꿔도 뒤가 전부 밀립니다.
#
#  ⚠ `adelay` 로 앞을 조금 비웁니다. 화면이 바뀌자마자 말이 시작되면
#    쫓기는 느낌이 납니다.
#  ⚠ `apad` + `-shortest` — 음성이 구간보다 짧으면 무음으로 채우고,
#    길면 잘라 냅니다. 밀려서 다음 구간과 겹치는 것이 제일 나쁩니다.
# ---------------------------------------------------------------------------
LEAD=0.7
mux() {  # mux <파트mp4> <wav이름>
  local v="$1" name="$2" wav="$D/tts/$2.wav" tmp="${1%.mp4}_a.mp4"
  if [ ! -f "$HERE/tts/$2.wav" ]; then
    say "  (음성 없음: $2 — 무음으로 둡니다)"
    return
  fi
  local ms; ms="$(awk -v a="$LEAD" 'BEGIN{printf "%d", a*1000}')"
  "$FF" -y -i "$v" -i "$wav"     -filter_complex "[1:a]adelay=${ms}|${ms},aresample=48000,apad[a]"     -map 0:v -map "[a]" -shortest -c:v copy -c:a aac -b:a 160k "$tmp" 2>/dev/null
  mv -f "$tmp" "$v"
}

# ===========================================================================
say "타이틀 · 마무리 카드"
card "$P/00_title.mp4" 9 "MULTIMODAL LIFELOG EMOTION CARE" "귀기울임" "먼저 말을 거는 정서 케어"
card "$P/99_outro.mp4" 10 "SMHRD KDT HEALTHCARE 5팀" "귀기울임 LISN" "감지한 것을 사람에게 닿게 합니다"

mux "$HERE/parts/00_title.mp4" "00"
mux "$HERE/parts/99_outro.mp4" "99"

say "앱 컷"
phone "$D/cuts/cut1_outreach.mp4" "$P/01.mp4" 44 "01" "먼저 말을 겁니다" \
  "수면 패턴이 5일째 무너진 것을 시스템이 먼저 알아챕니다." \
  "앱을 열지 않아도 알림으로 닿고, 첫 마디가 이미 준비돼 있습니다."
phone "$D/cuts/cut2_chat.mp4" "$P/02.mp4" 33 "02" "두 성격으로 듣습니다" \
  "공감형과 조언형 중에 고릅니다. 같은 말에 다르게 답합니다." \
  "위기 판정과 응답 생성을 병렬로 돌려 3초 안에 답합니다."

mux "$HERE/parts/01.mp4" "01"
mux "$HERE/parts/02.mp4" "02"

say "긴급 상담 연결"
still "$D/emg.png" "$P/02b.mp4" 14 "03" "위로가 위험을 덮지 않게" \
  "위기가 확인되면 만들어 둔 챗봇 답변을 버리고 사람에게 연결합니다." \
  "경고색을 쓰지 않았습니다 — 불안을 키우면 회피로 이어집니다."

phone "$D/cuts/cut3_report.mp4" "$P/03.mp4" 36 "04" "몸의 신호를 정서로" \
  "수면·활동량·심박이 개인 기준선에서 얼마나 벗어났는지 봅니다." \
  "데이터가 3일치 미만이면 '정상'이라고 하지 않습니다."

mux "$HERE/parts/02b.mp4" "02b"
mux "$HERE/parts/03.mp4" "03"

say "관제 컷"
desktop "$D/cuts/cut4_admin.mp4" "$P/04.mp4" "05" "관리자는 전체를 봅니다" \
  "위기 판정이 여기 기록됩니다 — 무엇이 판정했는지 「모델」 칸에 함께."

mux "$HERE/parts/04.mp4" "04"

say "이어붙이기"
cat > "$HERE/parts/list.txt" <<EOF
file '00_title.mp4'
file '01.mp4'
file '02.mp4'
file '02b.mp4'
file '03.mp4'
file '04.mp4'
file '99_outro.mp4'
EOF

"$FF" -y -f concat -safe 0 -i "$P/list.txt" -c copy "$OUT/lisn_demo_3min.mp4" 2>/dev/null
say "완료 → $OUT/lisn_demo_3min.mp4  ($(dur "$OUT/lisn_demo_3min.mp4")s)"
