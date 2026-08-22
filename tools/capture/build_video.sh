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
#  효과 — 기본 켜짐. `EFFECTS=0` 으로 끌 수 있습니다.
#
#  ⚠ **화려한 트랜지션은 넣지 않습니다.** 정신건강 서비스라 화면 자체가
#    차분한 톤인데, 큐브 회전이나 화이트플래시 같은 트랜지션을 얹으면
#    화면 설계 원칙(경고색·과장된 강조 금지)과 어긋납니다. 그래서
#    **매끄러움**만 더합니다 — 크로스페이드, 자막 페이드인, 화면 페이드인뿐입니다.
#
#  ⚠ Ken Burns 줌(정지 컷의 미세한 확대)은 넣었다가 뺐습니다. UI
#    스크린샷에 줌을 넣으니 「화면이 스스로 커지는」 위화감이 났습니다 —
#    사진에는 자연스러운 기법이 캡처 화면에는 안 맞았습니다. `still()`
#    함수 주석 참고.
# ---------------------------------------------------------------------------
EFFECTS="${EFFECTS:-1}"
XFADE=0.6   # 컷 사이 크로스페이드 길이(초)
CAP_FADE=0.5   # 자막 한 줄이 페이드인하는 시간(초)
FOOT_FADE=0.35  # 화면(폰/데스크톱) 자체가 페이드인하는 시간(초)

# ---------------------------------------------------------------------------
#  카드 (타이틀 · 마무리)
# ---------------------------------------------------------------------------
card() {  # card <출력> <초> <윗줄> <큰줄> <아랫줄>
  local out="$1" sec="$2" kicker="$3" big="$4" sub="$5"
  local fa=""
  if [ "$EFFECTS" = "1" ]; then
    fa=":alpha='min(1,t/${CAP_FADE})'"
  fi
  "$FF" -y -f lavfi -i "color=c=${BG}:s=${W}x${H}:d=${sec}:r=${FPS}" \
    -vf "drawtext=fontfile='${FONT_B}':text='${kicker}':fontsize=34:fontcolor=${INDIGO}:x=(w-text_w)/2:y=380${fa},drawtext=fontfile='${FONT_B}':text='${big}':fontsize=96:fontcolor=${NAVY}:x=(w-text_w)/2:y=450${fa},drawtext=fontfile='${FONT_R}':text='${sub}':fontsize=38:fontcolor=${MUTED}:x=(w-text_w)/2:y=600${fa}" \
    -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p "$out" 2>/dev/null
}

# 캡션 템플릿 — @자리@ 를 나중에 치환합니다.
#
# ⚠ **네 줄이 시차를 두고 순서대로 페이드인합니다**(0, 0.08, 0.16, 0.24초
#   지연). 한꺼번에 팝업되는 것보다 훨씬 자연스럽습니다 — 다만 차이가
#   커지면 산만해지므로 0.08초 간격을 넘기지 마세요.
if [ "$EFFECTS" = "1" ]; then
  TXT="drawtext=fontfile=@B@:text=@NO@:fontsize=30:fontcolor=@I@:x=170:y=360:alpha='min(1,t/${CAP_FADE})',drawtext=fontfile=@B@:text=@T@:fontsize=76:fontcolor=@N@:x=170:y=410:alpha='min(1,(t-0.08)/${CAP_FADE})',drawtext=fontfile=@R@:text=@L1@:fontsize=34:fontcolor=@M@:x=170:y=540:alpha='min(1,(t-0.16)/${CAP_FADE})',drawtext=fontfile=@R@:text=@L2@:fontsize=34:fontcolor=@M@:x=170:y=592:alpha='min(1,(t-0.24)/${CAP_FADE})'"
else
  TXT="drawtext=fontfile=@B@:text=@NO@:fontsize=30:fontcolor=@I@:x=170:y=360,drawtext=fontfile=@B@:text=@T@:fontsize=76:fontcolor=@N@:x=170:y=410,drawtext=fontfile=@R@:text=@L1@:fontsize=34:fontcolor=@M@:x=170:y=540,drawtext=fontfile=@R@:text=@L2@:fontsize=34:fontcolor=@M@:x=170:y=592"
fi

captions() {  # captions <번호> <제목> <설명1> <설명2>
  local t="$TXT"
  t="${t//@B@/\'${FONT_B}\'}"; t="${t//@R@/\'${FONT_R}\'}"
  t="${t//@I@/${INDIGO}}"; t="${t//@N@/${NAVY}}"; t="${t//@M@/${MUTED}}"
  t="${t//@NO@/\'$1\'}"; t="${t//@T@/\'$2\'}"
  t="${t//@L1@/\'$3\'}"; t="${t//@L2@/\'$4\'}"
  printf '%s' "$t"
}

# 화면(폰/데스크톱) 레이어 자체를 배경색에서 스르륵 떠오르게 합니다.
# ⚠ 알파 채널이 있는 포맷으로 먼저 바꿔야 fade 의 alpha=1 옵션이 먹습니다.
footfade() {
  if [ "$EFFECTS" = "1" ]; then
    printf ',format=yuva420p,fade=t=in:st=0:d=%s:alpha=1' "$FOOT_FADE"
  fi
}

# ---------------------------------------------------------------------------
#  앱 컷 — 세로 영상을 오른쪽에, 설명을 왼쪽에
# ---------------------------------------------------------------------------
phone() {  # phone <입력> <출력> <목표초> <번호> <제목> <설명1> <설명2>
  local in="$1" out="$2" want="$3" no="$4" title="$5" l1="$6" l2="$7"
  local d factor cap ff
  d="$(dur "$in")"
  factor="$(awk -v a="$want" -v b="$d" 'BEGIN{printf "%.4f", a/b}')"
  cap="$(captions "$no" "$title" "$l1" "$l2")"
  ff="$(footfade)"
  say "  ${no} ${title} — ${d}s → ${want}s (x${factor})"
  "$FF" -y -i "$in" -f lavfi -i "color=c=${BG}:s=${W}x${H}:r=${FPS}" \
    -filter_complex "[0:v]setpts=${factor}*PTS,scale=-2:940,fps=${FPS}${ff}[ph];[1:v]trim=duration=${want},setpts=PTS-STARTPTS[bg];[bg][ph]overlay=x=1240:y=70:shortest=1[v0];[v0]${cap}[v]" \
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
#
#  ⚠ **Ken Burns 줌을 넣었다가 뺐습니다**(2026.08.22). UI 스크린샷은
#    사진과 달라서, 줌이 들어가면 「화면이 스스로 확대되는」 부자연스러운
#    느낌이 났습니다 — 실제로 "박스가 조금씩 커져" 라는 지적을 받았습니다.
#    Ken Burns 은 사진에는 자연스럽지만 UI 캡처에는 위화감을 만듭니다.
#    지금은 등장할 때의 페이드인(footfade)만 남기고 그 뒤로는 진짜 정지입니다.
# ---------------------------------------------------------------------------
still() {  # still <png> <출력> <초> <번호> <제목> <설명1> <설명2>
  local img="$1" out="$2" sec="$3" no="$4" title="$5" l1="$6" l2="$7"
  local cap ff
  cap="$(captions "$no" "$title" "$l1" "$l2")"
  ff="$(footfade)"
  say "  ${no} ${title} — 정지 ${sec}s"
  "$FF" -y -loop 1 -t "${sec}" -i "$img" -f lavfi -i "color=c=${BG}:s=${W}x${H}:r=${FPS}" \
    -filter_complex "[0:v]scale=-2:940,fps=${FPS}${ff}[ph];[1:v]trim=duration=${sec},setpts=PTS-STARTPTS[bg];[bg][ph]overlay=x=1240:y=70:shortest=1[v0];[v0]${cap}[v]" \
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
  local ff fa=""
  ff="$(footfade)"
  if [ "$EFFECTS" = "1" ]; then
    fa=":alpha='min(1,t/${CAP_FADE})'"
  fi
  say "  ${no} ${title} — $(dur "$in")s"
  "$FF" -y -i "$in" -f lavfi -i "color=c=${BG}:s=${W}x${H}:r=${FPS}" \
    -filter_complex "[0:v]scale=1500:-2,fps=${FPS}${ff}[sc];[1:v]trim=duration=999,setpts=PTS-STARTPTS[bg];[bg][sc]overlay=x=(W-w)/2:y=28:shortest=1[v0];[v0]drawtext=fontfile='${FONT_B}':text='${no}  ${title}':fontsize=42:fontcolor=${NAVY}:x=(w-text_w)/2:y=900${fa},drawtext=fontfile='${FONT_R}':text='${l1}':fontsize=29:fontcolor=${MUTED}:x=(w-text_w)/2:y=958${fa}[v]" \
    -map "[v]" -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p "$out" 2>/dev/null
}

# ---------------------------------------------------------------------------
#  내레이션 얹기 — ElevenLabs (Sarah, eleven_multilingual_v2)
#
#  ⚠ **기본은 무음입니다.** 2026.08.22 에 Sarah 로 내레이션을 붙였다가
#    "일단 영상만 두고 직접 녹음 하는게 낫겠다"로 결정이 바뀌었습니다.
#    합성음보다 사람 목소리가 낫다는 판단입니다 — Windows TTS 는 "기괴하다",
#    ElevenLabs Sarah 는 원고를 목표 시간의 절반 이하로 읽어 화면만 남는
#    여백이 20초대까지 생겼습니다.
#
#    `NARRATE=1 bash build_video.sh` 로 다시 켤 수 있습니다 —
#    `gen_elevenlabs.py` 가 이미 만들어 둔 `tts/*.mp3` 를 그대로 씁니다.
#
#  ⚠ **NARRATE=1 이면 크로스페이드가 꺼집니다.** xfade 로 이으면 전환마다
#    영상이 0.6초씩 짧아지는데, 오디오는 그대로 이어 붙이면 그만큼씩 밀려
#    누적 어긋남이 생깁니다(전환 6번이면 3.6초). 오디오가 있을 때는 안전한
#    하드컷(concat)으로 돌아갑니다 — 아래 조립 단계 참고.
# ---------------------------------------------------------------------------
NARRATE="${NARRATE:-0}"
LEAD=0.7
mux() {  # mux <파트mp4> <음성이름>
  local v="$1" name="$2" tmp="${1%.mp4}_a.mp4"
  local mp3="$D/tts/$2.mp3"
  if [ "$NARRATE" != "1" ]; then
    return
  fi
  if [ ! -f "$HERE/tts/$2.mp3" ]; then
    say "  (음성 없음: $2 — 무음으로 둡니다)"
    return
  fi
  local ms; ms="$(awk -v a="$LEAD" 'BEGIN{printf "%d", a*1000}')"
  "$FF" -y -i "$v" -i "$mp3" \
    -filter_complex "[1:a]adelay=${ms}|${ms},aresample=48000,apad[a]" \
    -map 0:v -map "[a]" -shortest -c:v copy -c:a aac -b:a 160k "$tmp" 2>/dev/null
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

# ---------------------------------------------------------------------------
#  조립 — 크로스페이드(EFFECTS=1·NARRATE=0) 또는 하드컷(그 외)
# ---------------------------------------------------------------------------
say "이어붙이기"
PARTS=(00_title 01 02 02b 03 04 99_outro)
DURS=(9 44 33 14 36 "$(dur "$P/04.mp4")" 10)

if [ "$EFFECTS" = "1" ] && [ "$NARRATE" != "1" ]; then
  say "  크로스페이드 조립 (${XFADE}s)"
  INPUTS=()
  for part in "${PARTS[@]}"; do INPUTS+=(-i "$P/$part.mp4"); done

  FILTER=""
  prevlabel="0:v"
  cumsum=0
  n=${#PARTS[@]}
  for ((k = 0; k < n - 1; k++)); do
    cumsum="$(awk -v c="$cumsum" -v d="${DURS[$k]}" 'BEGIN{printf "%.3f", c+d}')"
    offset="$(awk -v c="$cumsum" -v x="$XFADE" -v m="$((k + 1))" 'BEGIN{printf "%.3f", c-(m*x)}')"
    nextlabel="v$((k + 1))"
    FILTER+="[${prevlabel}][$((k + 1)):v]xfade=transition=fade:duration=${XFADE}:offset=${offset}[${nextlabel}];"
    prevlabel="${nextlabel}"
  done
  FILTER="${FILTER%;}"

  "$FF" -y "${INPUTS[@]}" -filter_complex "$FILTER" -map "[${prevlabel}]" \
    -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p "$OUT/lisn_demo_3min.mp4" 2>/dev/null
else
  say "  하드컷 조립 (concat)"
  {
    for part in "${PARTS[@]}"; do echo "file '${part}.mp4'"; done
  } > "$HERE/parts/list.txt"
  "$FF" -y -f concat -safe 0 -i "$P/list.txt" -c copy "$OUT/lisn_demo_3min.mp4" 2>/dev/null
fi

say "완료 → $OUT/lisn_demo_3min.mp4  ($(dur "$OUT/lisn_demo_3min.mp4")s)"
