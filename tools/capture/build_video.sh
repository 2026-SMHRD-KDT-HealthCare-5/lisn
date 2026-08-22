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

# ⚠ **이 파일이 유일한 정본입니다.** 예전에는 스크래치패드에 사본을 두고
#   거기서 고친 뒤 저장소로 복사했는데, 두 사본이 갈라져 「어느 게 최신이지」가
#   반복됐습니다. 이제 저장소 파일만 고치고, 결과물 저장 위치만 넘깁니다.
#
#     OUT_ROOT=/경로 bash tools/capture/build_video.sh
#
#   OUT_ROOT 를 안 주면 이 스크립트 옆에 parts/·final/ 을 만듭니다.
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="${LISN_REPO:-$(cd "$HERE/../.." && pwd)}"
HERE="${OUT_ROOT:-$HERE}"
mkdir -p "$HERE"
D="$(cygpath -m "$HERE")"
FF="$(cat /tmp/ffmpeg_path)"
FP="$(dirname "$FF")/ffprobe.exe"
mkdir -p "$HERE/final" "$HERE/parts"
P="$D/parts"
OUT="$D/final"

# ---------------------------------------------------------------------------
#  색·글꼴은 docs/design/brand.json 이 정본입니다. 여기에 값을 적지 마세요.
#
#  ⚠ 2026.08.22 이전에는 이 파일이 자기 색(0x172147 등)과 Malgun Gothic 을
#    따로 갖고 있었습니다. 발표자료는 #24325F 와 Noto Sans KR 을 쓰는데
#    영상만 달라서, **한 슬라이드 안에서 색도 글씨체도 어긋나 보였습니다.**
#    같은 값을 두 곳에 적으면 반드시 갈라집니다 — 그래서 한 곳에서 읽습니다.
# ---------------------------------------------------------------------------
BRAND="$REPO/docs/design/brand.json"
tok() { python -c "import json,sys;print(json.load(open(sys.argv[1],encoding='utf-8'))$1)" "$BRAND"; }

NAVY="0x$(tok "['color']['navy']")"
INDIGO="0x$(tok "['color']['indigo']")"
MUTED="0x$(tok "['color']['muted']")"
BG="0x$(tok "['color']['bg']")"

# 정적 Noto Sans KR — 없으면 만듭니다(가변폰트 기본 굵기가 Thin 이라 그대로 못 씁니다)
W_TITLE="$(tok "['font']['weightTitle']")"
W_BODY="$(tok "['font']['weightBody']")"
FDIR="$REPO/tools/capture/fonts"
if [ ! -f "$FDIR/NotoSansKR-$W_TITLE.ttf" ] || [ ! -f "$FDIR/NotoSansKR-$W_BODY.ttf" ]; then
  say "정적 글꼴 생성 중 (처음 한 번)"
  python "$REPO/tools/capture/make_fonts.py"
fi
# ffmpeg drawtext 는 경로의 콜론을 escape 해야 합니다 (C:/... -> C\\:/...)
_fb="$(cygpath -m "$FDIR/NotoSansKR-$W_TITLE.ttf")"
_fr="$(cygpath -m "$FDIR/NotoSansKR-$W_BODY.ttf")"
FONT_B="${_fb/:/\\:}"
FONT_R="${_fr/:/\\:}"

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
  TXT="drawtext=fontfile=@B@:text=@NO@:fontsize=30:fontcolor=@I@:x=170:y=360:alpha='min(1,t/${CAP_FADE})',drawtext=fontfile=@B@:text=@T@:fontsize=76:fontcolor=@N@:x=170:y=410:alpha='min(1,(t-0.08)/${CAP_FADE})',drawtext=fontfile=@R@:text=@L1@:fontsize=30:fontcolor=@M@:x=170:y=540:alpha='min(1,(t-0.16)/${CAP_FADE})',drawtext=fontfile=@R@:text=@L2@:fontsize=30:fontcolor=@M@:x=170:y=586:alpha='min(1,(t-0.24)/${CAP_FADE})',drawtext=fontfile=@R@:text=@L3@:fontsize=30:fontcolor=@M@:x=170:y=632:alpha='min(1,(t-0.32)/${CAP_FADE})'"
else
  TXT="drawtext=fontfile=@B@:text=@NO@:fontsize=30:fontcolor=@I@:x=170:y=360,drawtext=fontfile=@B@:text=@T@:fontsize=76:fontcolor=@N@:x=170:y=410,drawtext=fontfile=@R@:text=@L1@:fontsize=30:fontcolor=@M@:x=170:y=540,drawtext=fontfile=@R@:text=@L2@:fontsize=30:fontcolor=@M@:x=170:y=586,drawtext=fontfile=@R@:text=@L3@:fontsize=30:fontcolor=@M@:x=170:y=632"
fi

# ⚠ 설명줄은 drawtext 라 **자동 줄바꿈이 없습니다.** phone/still 레이아웃은
#   왼쪽 x=170 ~ 폰 화면 시작 x=1240 까지 1070px 뿐이라, fontsize 30 기준
#   **한 줄 34자**를 넘기면 폰 화면 영역을 침범합니다. 넣기 전에 세세요.
#   (2026.08.22 에 cut1 자막이 이 폭을 넘겨 폰 화면을 침범한 걸 실제로 발견했습니다.)
#
# ⚠ **설명은 3줄입니다.** 원래 2줄이었는데, 「감지 → 선제 접촉 → 첫 마디」
#   처럼 앞뒤가 이어지는 설명을 두 줄에 욱여넣으니 주어·목적어가 잘려나가
#   번역투가 됐습니다. 줄을 늘리고 폰트를 34→30 으로 줄여 자리를 만들었습니다.
#   **한 줄에 한 가지만** 말하세요. 빈 줄이 필요하면 "" 를 넘기면 됩니다.
#
# ⚠ **번호가 붙는 소제목은 명사구로 끊습니다.** "01 먼저 말을 겁니다" 처럼
#   서술형으로 쓰면 번호와 따로 놀아서 목차처럼 훑히지 않습니다.
#   "01 수면 이상 감지 후 선제 접촉" 처럼 딱 끊으세요. 설명은 아래 3줄이 합니다.
#
# ⚠ **글자가 이 크기에서 깨지는지 반드시 검사하세요.** Malgun Gothic 은
#   29·30px 에서 「맡」의 ㅏ 세로획을 통째로 지웁니다(34px 부터 정상). 완성본을
#   눈으로 훑고도 못 봤고 사람이 지적해서 알았습니다. 자막을 고쳤으면:
#       python check_glyphs.py caption_lines.json
#   그래서 관제 컷은 「맡은」 대신 「담당」 을 씁니다 — 되돌리지 마세요.
captions() {  # captions <번호> <제목> <설명1> <설명2> <설명3>
  local t="$TXT"
  t="${t//@B@/\'${FONT_B}\'}"; t="${t//@R@/\'${FONT_R}\'}"
  t="${t//@I@/${INDIGO}}"; t="${t//@N@/${NAVY}}"; t="${t//@M@/${MUTED}}"
  t="${t//@NO@/\'$1\'}"; t="${t//@T@/\'$2\'}"
  t="${t//@L1@/\'$3\'}"; t="${t//@L2@/\'$4\'}"; t="${t//@L3@/\'$5\'}"
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
phone() {  # phone <입력> <출력> <목표초> <번호> <제목> <설명1> <설명2> <설명3>
  local in="$1" out="$2" want="$3" no="$4" title="$5" l1="$6" l2="$7" l3="$8"
  local d factor cap ff
  d="$(dur "$in")"
  factor="$(awk -v a="$want" -v b="$d" 'BEGIN{printf "%.4f", a/b}')"
  cap="$(captions "$no" "$title" "$l1" "$l2" "$l3")"
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
still() {  # still <png> <출력> <초> <번호> <제목> <설명1> <설명2> <설명3>
  local img="$1" out="$2" sec="$3" no="$4" title="$5" l1="$6" l2="$7" l3="$8"
  local cap ff
  cap="$(captions "$no" "$title" "$l1" "$l2" "$l3")"
  ff="$(footfade)"
  say "  ${no} ${title} — 정지 ${sec}s"
  "$FF" -y -loop 1 -t "${sec}" -i "$img" -f lavfi -i "color=c=${BG}:s=${W}x${H}:r=${FPS}" \
    -filter_complex "[0:v]scale=-2:940,fps=${FPS}${ff}[ph];[1:v]trim=duration=${sec},setpts=PTS-STARTPTS[bg];[bg][ph]overlay=x=1240:y=70:shortest=1[v0];[v0]${cap}[v]" \
    -map "[v]" -t "${sec}" -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p "$out" 2>/dev/null
}

# ---------------------------------------------------------------------------
#  관제 컷 — 가로 화면이라 위에 놓고 설명을 아래에 답니다
#
#  ⚠ **자막 규칙은 앱 컷과 같습니다.** 예전에는 이 컷만 번호와 제목을 한
#    덩어리로 묶어 **남색 42px 가운데 정렬**로 그렸습니다. 앱 컷은 번호가
#    인디고 30px, 제목이 남색 76px, 전부 x=170 좌측 정렬인데 말입니다.
#    한 영상 안에서 컷마다 색도 정렬도 달라 보였습니다(2026.08.22 지적).
#
#    지금은 같은 규칙을 씁니다 — 번호 30px 인디고 · 제목 76px 남색 ·
#    설명 30px 회색, 전부 **x=170 좌측**. y 좌표만 다릅니다. 가로 화면은
#    옆이 아니라 위에 놓이니 설명이 아래로 내려갈 수밖에 없습니다.
#
#  ⚠ **자막을 화면 밑에 붙이지 마세요.** 처음에 1740px 로 키웠더니 스크린샷
#    아래끝과 자막이 겹쳤습니다. 지금은 1330px(높이 748) 을 y=10 에 놓아
#    758 에서 끝내고, 자막이 800 부터 시작해 1008 에서 끝납니다 —
#    위로 42px, 아래로 72px 이 남습니다.
# ---------------------------------------------------------------------------
desktop() {  # desktop <입력> <출력> <번호> <제목> <설명1> <설명2>
  local in="$1" out="$2" no="$3" title="$4" l1="$5" l2="$6"
  local ff fa1="" fa2="" fa3="" fa4=""
  ff="$(footfade)"
  # 앱 컷과 똑같이 한 줄씩 시차를 두고 떠오르게 합니다
  if [ "$EFFECTS" = "1" ]; then
    fa1=":alpha='min(1,t/${CAP_FADE})'"
    fa2=":alpha='min(1,(t-0.08)/${CAP_FADE})'"
    fa3=":alpha='min(1,(t-0.16)/${CAP_FADE})'"
    fa4=":alpha='min(1,(t-0.24)/${CAP_FADE})'"
  fi
  say "  ${no} ${title} — $(dur "$in")s"
  "$FF" -y -i "$in" -f lavfi -i "color=c=${BG}:s=${W}x${H}:r=${FPS}"     -filter_complex "[0:v]scale=1330:-2,fps=${FPS}${ff}[sc];[1:v]trim=duration=999,setpts=PTS-STARTPTS[bg];[bg][sc]overlay=x=170:y=10:shortest=1[v0];[v0]drawtext=fontfile='${FONT_B}':text='${no}':fontsize=30:fontcolor=${INDIGO}:x=170:y=800${fa1},drawtext=fontfile='${FONT_B}':text='${title}':fontsize=76:fontcolor=${NAVY}:x=170:y=834${fa2},drawtext=fontfile='${FONT_R}':text='${l1}':fontsize=30:fontcolor=${MUTED}:x=170:y=940${fa3},drawtext=fontfile='${FONT_R}':text='${l2}':fontsize=30:fontcolor=${MUTED}:x=170:y=978${fa4}[v]"     -map "[v]" -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p "$out" 2>/dev/null
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
card "$P/00_title.mp4" 9 "MULTIMODAL LIFELOG EMOTION CARE" "귀기울임" "먼저 다가가는 정서 케어"
card "$P/99_outro.mp4" 10 "SMHRD KDT HEALTHCARE 5팀" "귀기울임 LISN" "감지에서 멈추지 않고 먼저 다가갑니다"

mux "$HERE/parts/00_title.mp4" "00"
mux "$HERE/parts/99_outro.mp4" "99"

say "앱 컷"
phone "$D/cuts/cut1_outreach.mp4" "$P/01.mp4" 44 "01" "수면 이상 감지 후 선제 접촉" \
  "사용자의 수면 패턴이 5일째 무너진 것을 먼저 알아챕니다." \
  "이상 징후가 발견되면 알림으로 선제 접촉을 합니다." \
  "앱을 열면 상태를 묻는 첫 마디가 대화를 시작합니다."
phone "$D/cuts/cut2_chat.mp4" "$P/02.mp4" 33 "02" "성격별 맞춤 응답 비교" \
  "사용자는 따스한 공감형과 현실적인 조언형 중에서 고릅니다." \
  "같은 말을 해도 성격에 따라 답이 달라집니다." \
  "위기 판정과 응답 생성을 동시에 돌려 3초 안에 답합니다."

mux "$HERE/parts/01.mp4" "01"
mux "$HERE/parts/02.mp4" "02"

say "긴급 상담 연결"
still "$D/emg.png" "$P/02b.mp4" 14 "03" "위기 발화 감지 후 상담 연결" \
  "위기가 확인되면 서버는 만들어 둔 챗봇 답변을 버립니다." \
  "위로를 건네는 대신 상담 연결 화면으로 넘어갑니다." \
  "경고색은 쓰지 않았습니다. 불안을 키우면 회피로 이어집니다."

phone "$D/cuts/cut3_report.mp4" "$P/03.mp4" 36 "04" "라이프로그 기반 정서 분석" \
  "앱은 사용자의 수면과 활동량, 심박을 함께 모읍니다." \
  "그 사람의 평소 기준선에서 얼마나 벗어났는지를 봅니다." \
  "데이터가 사흘치에 못 미치면 정상이라고 말하지 않습니다."

mux "$HERE/parts/02b.mp4" "02b"
mux "$HERE/parts/03.mp4" "03"

say "관제 컷"
desktop "$D/cuts/cut4_admin.mp4" "$P/04.mp4" "05" "이상 징후 사용자 우선 탐색" \
  "관리자는 담당 대상자의 위험도를 한 화면에서 봅니다." \
  "채팅에서 감지한 위기도 여기 쌓이고, 무엇이 판정했는지는 「모델」 칸에 남습니다."

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
