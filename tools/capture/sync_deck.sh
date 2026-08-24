#!/usr/bin/env bash
# 빌드한 발표자료를 documents/ 로 옮깁니다.
#
# ⚠ **그냥 cp 하지 마세요.** 2026.08.24 에 PM 이 PowerPoint 로 직접 고친
#   PPTX 를 제가 재생성본으로 덮어써서 그 수정이 사라졌습니다. 커밋 전이라
#   git 으로도 복구가 안 됐습니다.
#
#   이 스크립트는 덮어쓰기 전에 **대상 파일이 마지막 커밋과 다른지** 봅니다.
#   다르면 누군가 손으로 고친 것이므로 멈추고 물어봅니다.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
SRC="${1:?사용법: sync_deck.sh <빌드한.pptx> [빌드한.pdf]}"
PDF="${2:-}"
DST="$REPO/documents/최종발표자료_귀기울임.pptx"
DST_PDF="$REPO/documents/최종발표자료_귀기울임.pdf"

cd "$REPO"
if ! git diff --quiet HEAD -- "$DST" 2>/dev/null; then
  echo "⚠ 멈춤 — documents/ 의 PPTX 가 마지막 커밋과 다릅니다."
  echo "   누군가 PowerPoint 로 직접 고쳤을 수 있습니다. 덮어쓰면 그 수정이 사라집니다."
  echo
  echo "   먼저 확인하세요:"
  echo "     1) 손으로 고친 내용이 있으면 build_deck.js 에 옮겨 넣고 다시 빌드"
  echo "     2) 없으면  git checkout -- '$DST'  로 되돌린 뒤 이 스크립트를 다시 실행"
  exit 1
fi

cp "$SRC" "$DST"
[ -n "$PDF" ] && cp "$PDF" "$DST_PDF"
echo "✓ 반영했습니다 — $(basename "$DST")"
