const pptxgen = require('pptxgenjs');
const path = require('path');
const fs = require('fs');

// ⚠ 예전에는 이 값이 특정 PC 의 절대경로(C:\project\LISN 등)로 박혀
//   있었습니다. 다른 PC 에서 돌리면 그대로 깨집니다 — 스크립트 위치
//   기준 상대경로로 고쳤습니다(2026.08.25).
const REPO = path.resolve(__dirname, '..', '..');
const DESIGN = path.join(REPO, 'docs', 'design');

// 시연영상 — tools/capture/build_video.sh 의 출력.
//
// ⚠ 용량이 커서(수 MB) 저장소에 커밋하지 않습니다(.gitignore 대상).
//   이 폴더가 비어 있으면 documents/최종발표자료_귀기울임.pptx 의
//   ppt/media/ 에서 media-*.mp4·image-*.png(포스터)를 꺼내 넣으세요 —
//   내용을 새로 만들 필요가 없다면 이게 가장 빠릅니다.
const VIDEO_DIR = path.join(REPO, 'tools', 'capture', '.cache', 'video');
const VIDEO_PATH = path.join(VIDEO_DIR, 'lisn_demo_3min.mp4');
// pptxgenjs 의 addMedia 는 cover 에 base64 데이터 URI를 요구합니다 —
// path 옵션과 달리 파일 경로를 안 읽습니다. 'lacks a base64 header' 로
// 실패한 뒤 알았습니다.
const VIDEO_COVER = 'data:image/png;base64,' +
  fs.readFileSync(path.join(VIDEO_DIR, 'poster.png')).toString('base64');

// ---- 디자인 토큰 — docs/design/brand.json 이 정본입니다 ----
// ⚠ 여기에 값을 직접 적지 마세요. 2026.08.22 이전에는 발표자료·영상이
//   색을 따로 갖고 있어 전부 어긋나 있었습니다.
//
// 2026.08.25 — 팀이 받은 참고 시안(다크 네이비 + 오프화이트 + 골드,
// 세리프 헤드라인)에 맞춰 전면 리디자인했습니다. brand.json 의
// color.*(navy/mint/peach)는 앱 UI 값이라 그대로 남겨두고, 발표자료는
// 새로 추가한 deck.* 토큰을 씁니다.
const BRAND = JSON.parse(fs.readFileSync(path.join(REPO, 'docs', 'design', 'brand.json'), 'utf8'));
const D = BRAND.deck;
const DARK = D.darkBg;
const LIGHT = D.lightBg;
const TXT1 = D.textPrimary;     // 라이트 배경의 본문 진한 톤
const TXT2 = D.textSecondary;   // 라이트 배경의 보조 설명
const TXT_FAINT = D.textFaint;
const TXT_MUTED = D.textMuted;
const GOLD = D.gold;
const GOLD_DARK = D.goldDark;
const GOLD_LIGHT = D.goldLight;
const LINE = D.line;
const WHITE = D.white;
// 다크 배경 위 텍스트 — 참고 시안에 정확한 값이 없어 같은 채도로 새로
// 골랐습니다. 흰 제목보다 한 단 낮은 밝기의 슬레이트그레이입니다.
const DARK_BODY = 'AEB6C2';
const DARK_MUTED = '8891A0';
const DARK_LINE = '2E3A47';   // 다크 배경 위 구분선(거의 안 보이되 존재)
const GHOST_NUM = '242F3B';   // 섹션 표지의 대형 유령 숫자(배경보다 한 단 밝음)

const FONT = BRAND.font.family;           // Noto Sans KR — 본문·일반 제목
const FONT_BLACK = BRAND.font.familyBlack;
const FONT_LIGHT = BRAND.font.familyLight; // 보조 설명
const SERIF = BRAND.font.serif;            // Nanum Myeongjo — 대형 헤드라인·강조 수치 전용

async function main() {
  const pres = new pptxgen();
  pres.layout = 'LAYOUT_WIDE'; // 13.3 x 7.5
  pres.defineLayout({ name: 'WIDE', width: 13.333, height: 7.5 });
  pres.layout = 'WIDE';

  const W = 13.333, H = 7.5;
  const img = (name) => path.join(DESIGN, name + '.png');

  // ================= helpers =================
  function bgSlide(dark) {
    const s = pres.addSlide();
    s.background = { color: dark ? DARK : LIGHT };
    return s;
  }

  // 본문 슬라이드 상단 — 왼쪽 큰 제목 · 오른쪽 섹션 라벨 · 전체폭 얇은 선.
  // 참고 시안 전 슬라이드가 공유하는 유일한 반복 요소입니다.
  function header(s, titleText, sectionLabel, dark) {
    s.addText(titleText, {
      x: 0.62, y: 0.42, w: 9.6, h: 0.62, fontFace: FONT, fontSize: 25, bold: true,
      color: dark ? WHITE : DARK, margin: 0,
    });
    if (sectionLabel) {
      s.addText(sectionLabel, {
        x: 9.9, y: 0.55, w: 2.83, h: 0.35, fontFace: FONT_LIGHT, fontSize: 11,
        color: dark ? DARK_MUTED : TXT_MUTED, align: 'right', margin: 0,
      });
    }
    s.addShape('line', {
      x: 0.62, y: 1.08, w: 12.1, h: 0,
      line: { color: dark ? DARK_LINE : DARK, width: 1 },
    });
  }

  // 페이지 번호는 **자동으로 셉니다.** 슬라이드를 중간에 끼워도 안 밀립니다.
  let pageNo = 0;
  function pageNum(s, dark) {
    pageNo += 1;
    s.addText(String(pageNo).padStart(2, '0'), {
      x: W - 1.0, y: H - 0.5, w: 0.6, h: 0.32, fontFace: FONT_LIGHT, fontSize: 10,
      color: dark ? DARK_MUTED : TXT_MUTED, align: 'right',
    });
  }

  // 섹션 표지 — 다크 배경 + 우상단 대형 유령 숫자 + 골드 킥커 + 세리프 헤드라인.
  function sectionCover(s, no, ko, kicker, subtitle) {
    s.background = { color: DARK };
    s.addText(no, {
      x: 8.6, y: -0.35, w: 4.4, h: 2.6, fontFace: SERIF, fontSize: 150, bold: true,
      color: GHOST_NUM, align: 'right', margin: 0,
    });
    s.addText(kicker, {
      x: 0.9, y: 2.62, w: 8, h: 0.4, fontFace: FONT, fontSize: 13, bold: true,
      color: GOLD_LIGHT, charSpacing: 2, margin: 0,
    });
    s.addText(ko, {
      x: 0.87, y: 3.0, w: 10, h: 1.1, fontFace: SERIF, fontSize: 46, bold: true,
      color: WHITE, margin: 0,
    });
    s.addShape('line', { x: 0.9, y: 4.15, w: 2.3, h: 0, line: { color: GOLD, width: 1.5 } });
    s.addText(subtitle, {
      x: 0.9, y: 4.32, w: 10, h: 0.4, fontFace: FONT_LIGHT, fontSize: 13, color: DARK_BODY, margin: 0,
    });
    pageNum(s, true);
  }

  // 얇은 가로 구분선 — 이 덱의 유일한 "장식"입니다.
  function hr(s, x, y, w, dark) {
    s.addShape('line', { x, y, w, h: 0, line: { color: dark ? DARK_LINE : LINE, width: 1 } });
  }

  // ============================================================
  // 1. TITLE
  // ============================================================
  {
    const s = bgSlide(true);
    s.addText('스마트인재개발원 KDT 헬스케어 5팀 · 기업주제(라라랩스)', {
      x: 0.9, y: 0.55, w: 9, h: 0.35, fontFace: FONT_LIGHT, fontSize: 12, color: DARK_MUTED,
    });
    s.addText('2026. 08. 28', {
      x: 0, y: 0.55, w: W - 0.9, h: 0.35, fontFace: FONT_LIGHT, fontSize: 12, color: DARK_MUTED, align: 'right',
    });

    s.addText([
      { text: '귀기울임', options: { fontFace: SERIF, fontSize: 64, bold: true, color: WHITE, breakLine: false } },
      { text: '   LISN', options: { fontFace: FONT, fontSize: 22, bold: true, color: GOLD_LIGHT, charSpacing: 3 } },
    ], { x: 0.85, y: 2.55, w: 11, h: 1.4, margin: 0 });

    hr(s, 0.9, 3.9, 12.0, true);

    s.addText('멀티모달 라이프로그 감정 분석 기반 맞춤형 LLM 케어 및 모니터링 시스템', {
      x: 0.9, y: 4.15, w: 10, h: 0.5, fontFace: FONT_LIGHT, fontSize: 16, color: DARK_BODY,
    });

    s.addText('최종 발표', { x: 0.9, y: 5.65, w: 3, h: 0.35, fontFace: FONT_LIGHT, fontSize: 12, color: DARK_MUTED });

    const members = [['이응균', 'PM'], ['김건영', 'AI/DATA'], ['윤일준', '백엔드/DB'], ['함은선', '프론트엔드']];
    let mx = 0.9;
    const mw = 2.8;
    members.forEach(([n, r], i) => {
      s.addText([
        { text: n + ' ', options: { fontFace: FONT, fontSize: 13, bold: true, color: WHITE } },
        { text: r, options: { fontFace: FONT_LIGHT, fontSize: 11, color: DARK_MUTED } },
      ], { x: mx, y: 6.0, w: mw, h: 0.35, margin: 0 });
      mx += mw;
    });
  }

  // ============================================================
  // 2. 목차
  // ============================================================
  {
    const s = bgSlide(true);
    s.addText('목차', {
      x: 0.62, y: 0.42, w: 6, h: 0.62, fontFace: FONT, fontSize: 25, bold: true, color: WHITE, margin: 0,
    });
    s.addText('귀기울임 LISN', {
      x: 9.9, y: 0.55, w: 2.83, h: 0.35, fontFace: FONT_LIGHT, fontSize: 11, color: DARK_MUTED, align: 'right', margin: 0,
    });
    hr(s, 0.62, 1.08, 12.1, true);

    // ⚠ **실제 슬라이드 순서와 같아야 합니다.**
    const items = [
      ['01', '문제와 해결', '감지하고도 놓치는 구조 · 먼저 다가가는 설계 · 3분 시연'],
      ['02', '설계와 구현', '서버 분리 · 이탈 탐지 · 위기 탐지 2단계'],
      ['03', '성과와 확장', '실측 지표 · 관제 화면 · 보안 설계 · 다음 단계'],
    ];
    let y = 1.85;
    const rh = 1.15;
    items.forEach(([no, t, dsc], i) => {
      s.addText(no, { x: 0.62, y, w: 1.1, h: rh, fontFace: SERIF, fontSize: 30, color: GOLD, valign: 'middle', margin: 0 });
      // ⚠ y+0.29 — 큰 번호(gold, 30pt, 행 중앙정렬)와 나란해지도록 손으로
      //   내린 값입니다(2026.08.25, PowerPoint 로 직접 조정). 원래 0.15
      //   였는데, 번호는 행 높이(1.15)에 valign:'middle' 이라 세로 중심이
      //   아래쪽인데 제목은 위쪽에 붙어 있어 붕 떠 보였습니다.
      s.addText(t, { x: 1.9, y: y + 0.29, w: 5.5, h: 0.5, fontFace: FONT, fontSize: 22, bold: true, color: WHITE, margin: 0 });
      s.addText(dsc, { x: 5.9, y, w: 6.5, h: rh, fontFace: FONT_LIGHT, fontSize: 12.5, color: DARK_MUTED, valign: 'middle', margin: 0 });
      hr(s, 0.62, y + rh, 12.1, true);
      y += rh;
    });
    pageNum(s, true);
  }

  // ============================================================
  // [섹션 표지] 01 문제와 해결
  // ============================================================
  {
    const s = pres.addSlide();
    sectionCover(s, '01', '문제와 해결', '첫 번째', '감지하고도 놓치는 구조 · 먼저 다가가는 설계 · 3분 시연');
  }

  // ============================================================
  // [병합] 문제 정의 + 프로젝트 개요
  // ============================================================
  {
    const s = bgSlide(false);
    header(s, '쌓이는 데이터, 열리지 않는 앱', '문제와 해결', false);

    // 위: 문제 — 한 문장으로 압축
    s.addText('걸음·수면·심박은 매일 기록되지만, 케어로 이어지려면 사용자가 앱을 열어야 합니다.', {
      x: 0.62, y: 1.32, w: 12.1, h: 0.4, fontFace: FONT, fontSize: 15, bold: true, color: DARK, margin: 0,
    });
    s.addText('그런데 정작 힘든 순간에는 사용자가 앱을 열 힘조차 없습니다. 감지해 놓고도 사용자를 기다리는 구조가 문제입니다.', {
      x: 0.62, y: 1.72, w: 12.1, h: 0.4, fontFace: FONT_LIGHT, fontSize: 12, color: TXT2, margin: 0,
    });
    hr(s, 0.62, 2.28, 12.1, false);

    // 아래: 답 — 3단계
    s.addText('그래서 «관찰 → 판단 → 선제 접촉»으로 설계했습니다', {
      x: 0.62, y: 2.5, w: 12.1, h: 0.4, fontFace: FONT, fontSize: 14.5, bold: true, color: DARK, margin: 0,
    });

    const steps = [
      ['01', '자동 수집', 'Health Connect·화면 사용 시간을 앱이 자동으로 읽어 보냅니다. 입력할 것이 없습니다.'],
      ['02', '평소와 얼마나 다른가', '그 사람 본인의 평소(14일)와 비교해 징후를 봅니다. 감정을 분류하지 않습니다.'],
      ['03', '선제 접촉', '콘텐츠 추천에서 그치지 않고, 필요하면 시스템이 먼저 말을 거는 선제 접촉까지 이어집니다.'],
    ];
    const cw = 3.87, gap = 0.24, x0 = 0.62, cy = 3.15;
    steps.forEach(([no, h, b], i) => {
      const x = x0 + i * (cw + gap);
      if (i > 0) {
        s.addShape('line', { x: x - gap / 2, y: cy, w: 0, h: 3.0, line: { color: LINE, width: 1 } });
        // ⚠ 바로 위 문장이 "«관찰 → 판단 → 선제 접촉»" 이라고 순서를 못박는데,
        //   지금까지는 세 칸이 그냥 나란히 놓여 화살표가 문장에만 있고
        //   그림에는 없었습니다. 번호가 있는 줄 높이에만 골드 화살표를 얹어
        //   "01 다음이 02" 라는 순서를 실제로 보여줍니다.
        s.addShape(pres.ShapeType.rightArrow, {
          x: x - gap / 2 - 0.095, y: cy + 0.17, w: 0.19, h: 0.17,
          fill: { color: GOLD }, line: { type: 'none' },
        });
      }
      s.addText(no, { x, y: cy, w: cw, h: 0.5, fontFace: SERIF, fontSize: 22, color: GOLD, margin: 0 });
      s.addText(h, { x, y: cy + 0.6, w: cw, h: 0.45, fontFace: FONT, fontSize: 15.5, bold: true, color: DARK, margin: 0 });
      s.addText(b, { x, y: cy + 1.12, w: cw - 0.15, h: 1.7, fontFace: FONT_LIGHT, fontSize: 11.5, color: TXT2, margin: 0, lineSpacingMultiple: 1.35 });
    });
    pageNum(s, false);
  }

  // ============================================================
  // 5. 핵심 차별점 — 선제 접촉
  // ============================================================
  {
    const s = bgSlide(true);
    header(s, '앱을 열기 전에 먼저 닿는 구조', '차별점', true);

    // 두 컬럼 비교 — 왼쪽 회색 톤(기존 서비스) · 오른쪽 골드 톤(귀기울임)
    hr(s, 0.62, 1.55, 5.75, true);
    s.addText('기존 서비스', { x: 0.62, y: 1.68, w: 5.75, h: 0.32, fontFace: FONT, fontSize: 12.5, bold: true, color: DARK_MUTED, margin: 0 });
    s.addText('감지 → 사용자가 앱을 열어야 확인 → 끝', {
      x: 0.62, y: 2.05, w: 5.75, h: 0.55, fontFace: FONT, fontSize: 16, color: WHITE, bold: true, margin: 0,
    });
    s.addText('위기일수록 앱을 열 힘이 없는데, 확인 자체를 사용자에게 맡깁니다.', {
      x: 0.62, y: 2.62, w: 5.75, h: 0.7, fontFace: FONT_LIGHT, fontSize: 11.5, color: DARK_BODY, margin: 0, lineSpacingMultiple: 1.3,
    });

    hr(s, 6.9, 1.55, 5.83, true);
    s.addShape('line', { x: 6.9, y: 1.55, w: 1.2, h: 0, line: { color: GOLD, width: 2 } });
    s.addText('귀기울임', { x: 6.9, y: 1.68, w: 5.83, h: 0.32, fontFace: FONT, fontSize: 12.5, bold: true, color: GOLD_LIGHT, margin: 0 });
    s.addText('감지 → 시스템이 먼저 말을 겁니다', {
      x: 6.9, y: 2.05, w: 5.83, h: 0.55, fontFace: FONT, fontSize: 16, color: WHITE, bold: true, margin: 0,
    });
    s.addText('연속 이탈 3일 → 조건 6개 검사 → 첫 발화 생성 → 세션 생성 → FCM 푸시 · 홈 카드 · 배너로 먼저 말을 겁니다', {
      x: 6.9, y: 2.62, w: 5.83, h: 0.7, fontFace: FONT_LIGHT, fontSize: 11.5, color: DARK_BODY, margin: 0, lineSpacingMultiple: 1.3,
    });

    // guardrails row
    s.addText('"감시 아닌가요?" — 그래서 장치를 마련했습니다', {
      x: 0.62, y: 4.15, w: 8, h: 0.4, fontFace: FONT, fontSize: 14, bold: true, color: WHITE, margin: 0,
    });
    hr(s, 0.62, 4.62, 12.1, true);
    const guards = [
      ['옵트인', '케어 알림은 콘텐츠 알림과 따로 동의받습니다'],
      ['빈도 상한', '쿨다운 3일 · 하루 1회 · 09~21시'],
      ['겹침 방지', '같은 날 콘텐츠 알림이 있으면 보류합니다'],
      ['근거 제시', '왜 말을 걸었는지 첫 마디에 담습니다'],
    ];
    const gw = 3.0, gx0 = 0.62;
    guards.forEach(([h, b], i) => {
      const x = gx0 + i * (gw + 0.03);
      if (i > 0) s.addShape('line', { x: x - 0.03, y: 4.9, w: 0, h: 1.6, line: { color: DARK_LINE, width: 1 } });
      s.addText(h, { x: x + 0.12, y: 4.9, w: gw - 0.2, h: 0.35, fontFace: FONT, fontSize: 13, bold: true, color: GOLD_LIGHT, margin: 0 });
      s.addText(b, { x: x + 0.12, y: 5.3, w: gw - 0.25, h: 0.9, fontFace: FONT_LIGHT, fontSize: 10.5, color: DARK_BODY, margin: 0, lineSpacingMultiple: 1.25 });
    });
    pageNum(s, true);
  }

  // ============================================================
  // 5b. 3분 시연 영상
  //
  // ⚠ PowerPoint 재생 전용입니다. PDF 로 내보내면 영상이 정지 이미지(커버)로만
  //   보입니다 — 발표는 PPTX 로, 배포용 PDF 는 이 장이 그림 한 장으로 남습니다.
  // ============================================================
  {
    const s = bgSlide(false);
    header(s, '3분으로 보는 귀기울임', '시연', false);
    s.addText('클릭하면 재생됩니다', {
      x: 0.62, y: 1.22, w: 8, h: 0.32, fontFace: FONT_LIGHT, fontSize: 12, color: TXT_MUTED, margin: 0,
    });

    const vw = 8.6, vh = (vw * 9) / 16;
    const vx = (W - vw) / 2, vy = 1.75;
    s.addShape('rect', {
      x: vx - 0.02, y: vy - 0.02, w: vw + 0.04, h: vh + 0.04,
      fill: { color: 'DBDFE2' }, line: { color: LINE, width: 1 },
    });
    s.addMedia({
      type: 'video', path: VIDEO_PATH, cover: VIDEO_COVER,
      x: vx, y: vy, w: vw, h: vh,
    });
    pageNum(s, false);
  }

  // ============================================================
  // [섹션 표지] 02 설계와 구현
  // ============================================================
  {
    const s = pres.addSlide();
    sectionCover(s, '02', '설계와 구현', '두 번째', '서버 분리 · 이탈 탐지 · 위기 탐지 2단계');
  }

  // ============================================================
  // 6. 시스템 아키텍처
  // ============================================================
  {
    const s = bgSlide(false);
    header(s, '둘로 나눈 서버', '아키텍처', false);

    const boxY = 1.75, boxH = 1.3;
    const boxes = [
      { x: 0.62, w: 3.05, title: 'Flutter 앱', sub: '사용자 · 관리자 웹', dark: true },
      { x: 4.9, w: 3.62, title: '비즈니스 서버', sub: 'FastAPI · 인증·대화·위기키워드·정책', dark: false },
      { x: 9.75, w: 2.97, title: 'AI 추론 서버', sub: 'FastAPI · 개인 기준선 이탈 탐지', dark: false },
    ];
    boxes.forEach((b) => {
      if (b.dark) {
        s.addShape('rect', { x: b.x, y: boxY, w: b.w, h: boxH, fill: { color: DARK }, line: { type: 'none' } });
        s.addText(b.title, { x: b.x + 0.25, y: boxY + 0.3, w: b.w - 0.5, h: 0.35, fontFace: FONT, fontSize: 14.5, bold: true, color: WHITE, margin: 0 });
        s.addText(b.sub, { x: b.x + 0.25, y: boxY + 0.72, w: b.w - 0.5, h: 0.45, fontFace: FONT_LIGHT, fontSize: 10, color: DARK_MUTED, margin: 0, lineSpacingMultiple: 1.2 });
      } else {
        s.addShape('rect', { x: b.x, y: boxY, w: b.w, h: boxH, fill: { color: WHITE }, line: { color: LINE, width: 1 } });
        s.addText(b.title, { x: b.x + 0.25, y: boxY + 0.3, w: b.w - 0.5, h: 0.35, fontFace: FONT, fontSize: 14.5, bold: true, color: DARK, margin: 0 });
        s.addText(b.sub, { x: b.x + 0.25, y: boxY + 0.72, w: b.w - 0.5, h: 0.45, fontFace: FONT_LIGHT, fontSize: 10, color: TXT_MUTED, margin: 0, lineSpacingMultiple: 1.2 });
      }
    });
    // 화살표 대신 얇은 골드 연결선 + 라벨
    [[3.67, 4.9, '걸음·수면·심박·앱 사용 push'], [8.52, 9.75, '내부 통신']].forEach(([ax1, ax2, label]) => {
      s.addShape('line', { x: ax1, y: boxY + boxH / 2, w: ax2 - ax1, h: 0, line: { color: GOLD, width: 1.5 } });
      s.addText(label, { x: ax1 - 0.3, y: boxY - 0.3, w: (ax2 - ax1) + 0.6, h: 0.28, fontFace: FONT_LIGHT, fontSize: 8.5, color: TXT_MUTED, align: 'center', margin: 0 });
    });

    hr(s, 0.62, 3.35, 12.1, false);
    s.addText([
      { text: '위기 키워드 필터는 비즈니스 서버 안에 둡니다.  ', options: { bold: true, color: DARK } },
      { text: 'AI 서버가 죽어도 탐지가 멈추면 안 되기 때문입니다.', options: { color: TXT2 } },
    ], { x: 0.62, y: 3.55, w: 12.1, h: 0.4, fontFace: FONT, fontSize: 13, margin: 0 });

    s.addText('앱이 먼저 보내고, 서버는 끌어오지 않습니다', {
      x: 0.62, y: 4.2, w: 11.4, h: 0.35, fontFace: FONT, fontSize: 14, bold: true, color: DARK, margin: 0,
    });
    // ⚠ **WorkManager 15분 주기를 반드시 남깁니다.**
    s.addText('Health Connect는 Android 단말 안의 권한 모델이라 서버가 가질 OAuth 토큰이 없습니다. 그래서 앱이 읽어 push하고, 앱을 열지 않아도 WorkManager가 15분 주기로 백그라운드 전송합니다. 서버가 안 가져오는 것이 아니라, 가져올 수가 없습니다. 앱 사용 지표도 같은 경로로 보냅니다 — 패키지명 없이 집계값만 씁니다.', {
      x: 0.62, y: 4.58, w: 11.6, h: 0.95, fontFace: FONT_LIGHT, fontSize: 11, color: TXT2, lineSpacingMultiple: 1.35, margin: 0,
    });

    hr(s, 0.62, 5.85, 12.1, false);
    // 기술 스택은 별도 장을 두지 않고 여기 한 줄로 흡수했습니다(2026.08.22).
    s.addText([
      { text: 'STACK   ', options: { bold: true, color: GOLD_DARK, charSpacing: 1 } },
      { text: 'Flutter · Health Connect · WorkManager   |   FastAPI · SQLAlchemy · PostgreSQL 17   |   React · Vite   |   OpenAI API   |   인프라: NCP + Docker Compose', options: { color: TXT_MUTED } },
    ], { x: 0.62, y: 6.05, w: 12.1, h: 0.35, fontFace: FONT_LIGHT, fontSize: 9.5, margin: 0 });
    pageNum(s, false);
  }

  // ============================================================
  // 7. AI 설계 여정
  // ============================================================
  {
    const s = bgSlide(false);
    header(s, '감정 분류 대신 개인 기준선 이탈 탐지', '설계와 구현', false);

    const steps = [
      ['1', '학습된 집계로 교체', '「상위 3개 평균 ÷ 4.0」이라는 임의 집계식을 로지스틱 회귀로 바꿨습니다. 입력은 하나도 늘리지 않았습니다'],
      ['2', '참가자 내부 AUC 0.609', '기존 규칙 0.491 → 학습된 집계 0.609. 이득 +0.115[+0.056,+0.176]. 62명·4086표본, 참가자 분할 + 중첩 교차검증'],
      ['3', '브리프 지정 방법도 비교', 'Isolation Forest(전역 0.473·개인별 0.494) 등 6종을 같은 조건에서 재보고, 저희 방식이 유의하게 나아 채택했습니다'],
    ];
    let y = 1.35;
    const rh = 0.72;
    steps.forEach(([no, h, b], i) => {
      s.addText(no, { x: 0.62, y, w: 0.55, h: rh, fontFace: SERIF, fontSize: 20, color: GOLD, valign: 'middle', margin: 0 });
      s.addText(h, { x: 1.25, y, w: 3.6, h: rh, fontFace: FONT, fontSize: 14, bold: true, color: DARK, valign: 'middle', margin: 0 });
      s.addText(b, { x: 5.0, y, w: 7.7, h: rh, fontFace: FONT_LIGHT, fontSize: 11.5, color: TXT2, valign: 'middle', margin: 0, lineSpacingMultiple: 1.3 });
      hr(s, 0.62, y + rh, 12.1, false);
      y += rh;
    });

    y += 0.25;
    // ⚠ 왼쪽(글)·오른쪽(차트) 2단으로 나눕니다. 위 3단계 표가 이미 이 네 숫자
    //   (0.491·0.473·0.494·0.609)를 문장 안에 흩어 놓고 있어, 막대그래프로
    //   한 번 더 나란히 보여주면 "재보고 골랐다"는 주장이 한눈에 들어옵니다.
    const gh = 2.1;
    s.addShape('line', { x: 0.62, y, w: 0.06, h: gh, line: { color: GOLD, width: 4 } });
    s.addText('감정을 분류하는 게 아닙니다', {
      x: 0.9, y, w: 7.0, h: 0.4, fontFace: FONT, fontSize: 15, bold: true, color: DARK, margin: 0,
    });
    s.addText('바뀐 것은 지표를 합치는 방식뿐입니다. 개인 기준선 대비 이탈 지표 7개를 하나의 점수로 합치는 방법을 데이터로 정한 것이고, 감정 코드는 여전히 이탈 정도를 표시하는 산출값입니다. model_version 이 hybrid- 로 시작하면 이 집계가 관여한 것이고, rule- 이면 기존 규칙 그대로입니다.', {
      x: 0.9, y: y + 0.42, w: 7.0, h: 1.15, fontFace: FONT_LIGHT, fontSize: 11.5, color: TXT2, lineSpacingMultiple: 1.35, margin: 0,
    });
    s.addText('※ 같은 데이터로 70%를 보고한 선행연구를 재현하니, 그 지표의 기준선이 66.7%였습니다 — ai/train/eval_replicate_paper.py', {
      x: 0.9, y: y + 1.62, w: 7.0, h: 0.3, fontFace: FONT_LIGHT, fontSize: 9, italic: true, color: TXT_MUTED, margin: 0,
    });

    // ── 참가자 내부 AUC 비교 — 3단계 표의 숫자를 그대로 시각화합니다.
    //   ⚠ 0 부터 그리지 않습니다. AUC 는 0.5 가 "무작위" 기준선이라 0~1
    //     전체를 쓰면 네 막대가 전부 절반 언저리에 뭉개져 차이가 안
    //     보입니다. 0.4~0.66 로 축을 좁혀 실제 격차를 드러냅니다 — 값
    //     라벨을 그대로 남겨 축을 좁힌 사실이 가려지지 않게 합니다.
    s.addChart(pres.ChartType.bar, [{
      name: '참가자 내부 AUC',
      labels: ['현재 규칙', 'Isolation Forest(전역)', 'Isolation Forest(개인별)', '학습된 집계(채택)'],
      values: [0.491, 0.473, 0.494, 0.609],
    }], {
      x: 8.3, y: y - 0.06, w: 4.35, h: gh + 0.12,
      barDir: 'bar',
      chartColors: [TXT_FAINT, TXT_FAINT, TXT_FAINT, GOLD],
      showTitle: true, title: '참가자 내부 AUC 비교',
      titleFontFace: FONT, titleFontSize: 10.5, titleColor: TXT1, titleBold: true,
      showValue: true, dataLabelPosition: 'outEnd',
      dataLabelFontFace: FONT, dataLabelFontSize: 9, dataLabelColor: TXT1,
      dataLabelFormatCode: '0.000',
      showLegend: false,
      catAxisLabelFontFace: FONT_LIGHT, catAxisLabelFontSize: 8.5, catAxisLabelColor: TXT2,
      catAxisLineShow: false,
      valAxisHidden: true,
      valAxisMinVal: 0.4, valAxisMaxVal: 0.66,
      valGridLine: { style: 'none' },
      catGridLine: { style: 'none' },
      chartArea: { fill: { color: LIGHT } },
      plotArea: { fill: { color: LIGHT } },
    });
    pageNum(s, false);
  }

  // ============================================================
  // 8. 위기 탐지 2단계
  // ============================================================
  {
    const s = bgSlide(false);
    header(s, '위기 탐지 2단계 구조', '설계와 구현', false);

    const stages = [
      ['1차', '키워드 규칙', '외부 API가 죽어도 탐지가 멈추지 않습니다', '단독 재현율', '0.081'],
      ['2차', 'LLM 문맥 판정', '문장 맥락까지 읽어 더 정밀하게 판정합니다', '최종 재현율', '0.946'],
    ];
    const cw = 5.87, x0 = 0.62, y0 = 1.35;
    stages.forEach(([no, h, b, statL, statV], i) => {
      const x = x0 + i * (cw + 0.36);
      if (i > 0) {
        s.addShape('line', { x: x - 0.18, y: y0, w: 0, h: 2.55, line: { color: LINE, width: 1 } });
        // ⚠ 두 재현율(0.081→0.946)이 "1차가 놓친 걸 2차가 잡는다"는 하나의
        //   파이프라인이라는 걸, 나란한 두 숫자만으로는 못 보여줬습니다.
        //   숫자 줄 높이에 화살표를 얹어 "1차 다음이 2차" 흐름을 보입니다
        //   (슬라이드 4 와 같은 화살표 처리 — 덱 안에서 일관되게).
        s.addShape(pres.ShapeType.rightArrow, {
          x: x - 0.18 - 0.095, y: y0 + 2.115, w: 0.19, h: 0.17,
          fill: { color: GOLD }, line: { type: 'none' },
        });
      }
      s.addText(no, { x, y: y0, w: 1.2, h: 0.35, fontFace: FONT, fontSize: 12.5, bold: true, color: GOLD_DARK, margin: 0 });
      s.addText(h, { x, y: y0 + 0.35, w: cw, h: 0.5, fontFace: FONT, fontSize: 19, bold: true, color: DARK, margin: 0 });
      s.addText(b, { x, y: y0 + 0.95, w: cw - 0.2, h: 0.6, fontFace: FONT_LIGHT, fontSize: 12, color: TXT2, lineSpacingMultiple: 1.3, margin: 0 });
      s.addText(statL, { x, y: y0 + 1.62, w: cw, h: 0.3, fontFace: FONT_LIGHT, fontSize: 10.5, color: TXT_MUTED, margin: 0 });
      s.addText(statV, { x, y: y0 + 1.9, w: cw, h: 0.6, fontFace: SERIF, fontSize: 30, bold: true, color: GOLD, margin: 0 });
    });

    hr(s, 0.62, 4.15, 12.1, false);
    // ── 「안전 설계 원칙」 중 고유한 2가지만 흡수했습니다(2026.08.22).
    s.addText('정신건강 서비스라서 다르게 만든 것', {
      x: 0.62, y: 4.35, w: 11.4, h: 0.35, fontFace: FONT, fontSize: 14.5, bold: true, color: DARK, margin: 0,
    });
    s.addText([
      { text: 'CRITICAL이면 이미 만든 답변도 버립니다. ', options: { bold: true, color: DARK } },
      { text: '위기 판정과 응답 생성을 동시에 돌리지만, CRITICAL이면 만들어 둔 응답을 버립니다. 그래서 스트리밍을 쓰지 않습니다. 판정 전에 흘려보낸 글자는 되돌릴 수 없습니다.', options: { color: TXT2 } },
    ], { x: 0.62, y: 4.78, w: 11.4, h: 0.5, fontFace: FONT_LIGHT, fontSize: 11.5, lineSpacingMultiple: 1.3, margin: 0 });
    s.addText([
      { text: '경고색은 쓰지 않습니다. ', options: { bold: true, color: DARK } },
      { text: '빨강·주황은 불안을 키워 회피를 부릅니다.   ', options: { color: TXT2 } },
      { text: '데이터가 없다고 "정상"이라 하지도 않습니다. ', options: { bold: true, color: DARK } },
      { text: '3일 미만이면 422로 끊습니다. 편차 0을 정상으로 적재하면 위험을 놓칩니다.', options: { color: TXT2 } },
    ], { x: 0.62, y: 5.32, w: 11.4, h: 0.6, fontFace: FONT_LIGHT, fontSize: 11.5, lineSpacingMultiple: 1.3, margin: 0 });
    pageNum(s, false);
  }

  // ============================================================
  // [섹션 표지] 03 성과와 확장
  // ============================================================
  {
    const s = pres.addSlide();
    sectionCover(s, '03', '성과와 확장', '세 번째', '실측 지표 · 관제 화면 · 보안 설계 · 다음 단계');
  }

  // ============================================================
  // 10. 성과 지표
  // ============================================================
  {
    const s = bgSlide(true);
    header(s, '실측으로 증명된 수치', '성과', true);

    // ⚠ **평가셋 타일에 「위기 111 · 비위기 100」을 반드시 남깁니다.**
    const tiles = [
      ['0.946', '위기 판정 재현율'],
      ['0.921', '위기 판정 정밀도'],
      ['0.933', '위기 판정 F1-Score'],
      ['211건', '자체 평가셋 · 위기 111 · 비위기 100 · 2인 교차 라벨링'],
      ['34개', '백엔드 API 엔드포인트'],
      ['9개', 'DB 테이블 · UUID·TIMESTAMPTZ'],
      ['348건', '회귀 테스트 · 백엔드 131 · AI 30 · 앱 173 · 관리자 14'],
      ['2052ms', 'AI 챗봇 응답 지연 최댓값(예산 3000ms)'],
    ];
    const cw = 2.94, ch = 1.55, x0 = 0.62, y0 = 1.35;
    tiles.forEach((t, i) => {
      const col = i % 4, row = Math.floor(i / 4);
      const x = x0 + col * cw, y = y0 + row * ch;
      if (col > 0) s.addShape('line', { x, y: y + 0.12, w: 0, h: ch - 0.3, line: { color: DARK_LINE, width: 1 } });
      s.addText(t[0], { x: x + 0.16, y, w: cw - 0.32, h: 0.65, fontFace: SERIF, fontSize: 26, bold: true, color: WHITE, margin: 0 });
      s.addText(t[1], { x: x + 0.16, y: y + 0.68, w: cw - 0.32, h: 0.75, fontFace: FONT_LIGHT, fontSize: 9.5, color: DARK_MUTED, margin: 0, lineSpacingMultiple: 1.25 });
    });
    // ⚠ 타일이 4열×2행입니다. 아래 구분선·문단은 "한 행 높이(ch)" 가 아니라
    //   "두 행 전체 높이(ch*2)" 뒤에 와야 합니다 — 처음엔 ch 하나만 더해서
    //   두 번째 행 타일의 설명 텍스트와 겹쳤습니다(2026.08.25 실측 발견).
    const tilesBottom = y0 + ch * 2;
    hr(s, 0.62, tilesBottom, 12.1, true);

    // ── 「검증」 장에서 고유 자산만 흡수했습니다.
    s.addText([
      { text: '실서버 관통 점검 ', options: { bold: true, color: WHITE } },
      { text: '13건 수정 뒤 실패 0건    ·    ', options: { color: DARK_MUTED } },
      { text: '문서 검사기 4종 ', options: { bold: true, color: WHITE } },
      { text: '— 같은 수치가 문서마다 갈리는 것을 사람이 세지 않고 기계가 대조    ·    ', options: { color: DARK_MUTED } },
      { text: 'db/schema.sql 정본 ', options: { bold: true, color: WHITE } },
      { text: '— 드리프트 테스트가 모델과 어긋나면 실패', options: { color: DARK_MUTED } },
    ], { x: 0.62, y: tilesBottom + 0.25, w: 12.1, h: 0.6, fontFace: FONT_LIGHT, fontSize: 10.5, lineSpacingMultiple: 1.35, margin: 0 });

    s.addText('※ 재현율은 8/05 0.793 → 8/12 0.946 — 팀이 확정한 라벨 기준을 프롬프트에 반영하고, 판정 모델을 gpt-5.6 → gpt-5.4로 교체(미탐 23 → 6건, 지연 최댓값 절반 이하)', {
      x: 0.62, y: 6.6, w: 12.1, h: 0.32, fontFace: FONT_LIGHT, fontSize: 9, italic: true, color: DARK_MUTED, margin: 0,
    });
    pageNum(s, true);
  }

  // ============================================================
  // 12. 관리자 관제 웹
  // ============================================================
  {
    const s = bgSlide(false);
    header(s, '위험한 사람부터 보이는 관제 화면', '관제', false);

    s.addShape('rect', { x: 0.6, y: 1.35, w: 7.5, h: 4.7, fill: { color: WHITE }, line: { color: LINE, width: 1 } });
    s.addImage({ path: img('ADMIN_DASH_01'), x: 0.6, y: 1.35, w: 7.5, h: 4.6875 });

    const feats = [
      ['위험도 분포', '안정·주의·심각이 각각 몇 명인지 한눈에 봅니다'],
      ['목록 · 검색', '이름·이메일·상태로 즉시 필터링'],
      ['상세 조회', '개인별 라이프로그 추이와 대화 이력을 확인합니다'],
      ['위기 이력', '판정 시점과 대응 이력을 시간순으로 따라갑니다'],
    ];
    let y = 1.4;
    feats.forEach(([h, b], i) => {
      if (i > 0) hr(s, 8.5, y, 4.2, false);
      y += i > 0 ? 0.2 : 0;
      s.addText(h, { x: 8.5, y, w: 4.2, h: 0.35, fontFace: FONT, fontSize: 14, bold: true, color: DARK, margin: 0 });
      s.addText(b, { x: 8.5, y: y + 0.4, w: 4.2, h: 0.6, fontFace: FONT_LIGHT, fontSize: 10.5, color: TXT2, margin: 0, lineSpacingMultiple: 1.3 });
      y += 1.15;
    });
    pageNum(s, false);
  }

  // ============================================================
  // 13. 보안 설계
  // ============================================================
  {
    const s = bgSlide(false);
    header(s, '"전부 암호화" 대신 위험도 기반', '보안', false);

    const rows = [
      ['전송 구간', 'HTTPS / TLS', '앱 ↔ 백엔드, 백엔드 ↔ AI 서버'],
      ['저장 매체', 'DB 볼륨 디스크 암호화', '클라우드 배포 시에만'],
      ['컬럼 단위', 'AES-256-GCM', 'USERS.phone (연락처만)'],
      ['비밀번호', 'bcrypt', '복호화하지 않음'],
      ['대화 저장', '정규식 PII 마스킹', '전화·주민번호·이메일을 저장 전에 마스킹'],
      ['식별자', 'UUID v4', '테이블 9곳 전부 — 열거 공격 방지'],
    ];
    let y = 1.35;
    const rh = 0.58;
    hr(s, 0.62, y, 7.4, false);
    rows.forEach(([a, b2, c]) => {
      s.addText(a, { x: 0.62, y, w: 1.7, h: rh, fontFace: FONT_LIGHT, fontSize: 11, color: TXT_MUTED, valign: 'middle', margin: 0 });
      s.addText(b2, { x: 2.35, y, w: 2.15, h: rh, fontFace: SERIF, fontSize: 13.5, color: DARK, valign: 'middle', margin: 0 });
      s.addText(c, { x: 4.55, y, w: 3.45, h: rh, fontFace: FONT_LIGHT, fontSize: 10.5, color: TXT2, valign: 'middle', margin: 0, lineSpacingMultiple: 1.15 });
      hr(s, 0.62, y + rh, 7.4, false);
      y += rh;
    });

    // 오른쪽 박스 — 세로 골드 선으로 왼쪽 표와 분리
    s.addShape('line', { x: 8.5, y: 1.35, w: 0, h: rh * rows.length, line: { color: GOLD, width: 1.5 } });
    s.addText([
      { text: '왜 전 컬럼 암호화를 하지 않았나', options: { fontFace: FONT, fontSize: 13, bold: true, color: DARK, breakLine: true, paraSpaceAfter: 12 } },
      { text: '라이프로그 측정치를 컬럼 암호화하면 서비스가 동작하지 않습니다. 기간별 집계와 복합 인덱스가 핵심 동작인데, 암호화하면 범위 조회를 할 수 없습니다.', options: { color: TXT2, breakLine: true, paraSpaceAfter: 12 } },
      { text: '그래서 유출 시 즉각적 2차 피해가 나는 항목(연락처)만 컬럼 암호화하고, 측정치는 전송 구간 보호와 접근통제로 지킵니다.', options: { color: TXT2 } },
    ], {
      x: 8.75, y: 1.35, w: 3.98, h: rh * rows.length,
      fontFace: FONT_LIGHT, fontSize: 10.5, valign: 'middle', lineSpacingMultiple: 1.3, margin: 0,
    });

    const boxY = 1.35 + rh * rows.length + 0.35;
    hr(s, 0.62, boxY, 12.1, false);
    s.addText([
      { text: '"보안을 덜 했다"가 아니라 ', options: { color: TXT2 } },
      { text: '"보안 요구를 기능 제약과 함께 설계했다"', options: { bold: true, color: DARK } },
      { text: '입니다. 마스킹은 저장 전에 합니다 — 원문은 어디에도 남지 않고, 외부 LLM에도 마스킹된 텍스트만 전송됩니다.', options: { color: TXT2 } },
    ], { x: 0.62, y: boxY + 0.22, w: 12.1, h: 0.9, fontFace: FONT, fontSize: 12, lineSpacingMultiple: 1.35, margin: 0 });
    pageNum(s, false);
  }

  // ============================================================
  // 16. 확장 가능한 부분 (다음 단계)
  // ============================================================
  {
    const s = bgSlide(false);
    header(s, '확장 가능한 부분', '다음 단계', false);

    const rows = [
      ['Health Connect·앱 사용 로그 실기기', '검증 예정', '에뮬레이터에서 워커 동작까지 확인했습니다. 실기기만 확보되면 바로 검증합니다.'],
      ['iOS 확장', '설계 반영', 'health 패키지가 HealthKit도 감쌉니다. 수집 계층을 그대로 재사용할 수 있게 설계했습니다.'],
      ['평가셋 확장', '다음 단계', '0.946은 평가셋 211건 기준입니다. 새 문장을 더해 일반화를 재검증합니다.'],
      ['AI 모델 표본 확대', '다음 단계', '이 분야 표본 중앙값이 60.5명인데 저희는 62명입니다. 표본을 더 늘려 재검증합니다.'],
      ['미탐 6건', '패턴 분석 완료', '완곡·작별·신변 정리 표현에 몰려 있습니다. 이 패턴군을 다음 개선 대상으로 잡았습니다.'],
    ];
    let y = 1.35;
    const rh = 0.87;
    hr(s, 0.62, y, 12.1, false);
    rows.forEach(([a, tag, c]) => {
      s.addText(a, { x: 0.62, y, w: 3.15, h: rh, fontFace: FONT, fontSize: 13, bold: true, color: DARK, valign: 'middle', margin: 0 });
      const tagColor = tag === '패턴 분석 완료' ? GOLD_DARK : (tag === '설계 반영' ? TXT2 : GOLD);
      s.addText(tag, { x: 3.95, y, w: 1.35, h: rh, fontFace: FONT, fontSize: 10.5, bold: true, color: tagColor, valign: 'middle', margin: 0 });
      s.addText(c, { x: 5.4, y, w: 7.1, h: rh, fontFace: FONT_LIGHT, fontSize: 10.5, color: TXT2, valign: 'middle', margin: 0, lineSpacingMultiple: 1.25 });
      hr(s, 0.62, y + rh, 12.1, false);
      y += rh;
    });
    pageNum(s, false);
  }

  // ============================================================
  // 18. 감사합니다
  // ============================================================
  {
    const s = bgSlide(true);
    s.addText('귀기울임', {
      x: 0, y: 2.7, w: W, h: 1.0, fontFace: SERIF, fontSize: 52, bold: true, color: WHITE, align: 'center', margin: 0,
    });
    s.addText('감사합니다', {
      x: 0, y: 3.65, w: W, h: 0.6, fontFace: FONT, fontSize: 20, color: DARK_BODY, align: 'center', margin: 0,
    });
    s.addShape('line', { x: W / 2 - 1.2, y: 4.5, w: 2.4, h: 0, line: { color: GOLD, width: 1.5 } });
    s.addText('귀기울임 — 먼저 다가가는 정서 케어', {
      x: 0, y: 4.7, w: W, h: 0.4, fontFace: FONT_LIGHT, fontSize: 13, color: DARK_MUTED, align: 'center', margin: 0,
    });

    hr(s, W / 2 - 6, 5.75, 12, true);
    // 팀 소개 슬라이드를 따로 두지 않고 여기로 흡수했습니다(2026.08.22).
    const team = [['이응균', 'PM · 기획 · 문서'], ['김건영', 'AI · DATA'], ['윤일준', '백엔드 · DB'], ['함은선', '프론트엔드']];
    const tw = 3.0, totalW = tw * 4, tx0 = (W - totalW) / 2;
    team.forEach(([n, r], i) => {
      const x = tx0 + i * tw;
      s.addText(n, { x, y: 6.0, w: tw, h: 0.38, fontFace: FONT, fontSize: 14, bold: true, color: WHITE, align: 'center', margin: 0 });
      s.addText(r, { x, y: 6.38, w: tw, h: 0.35, fontFace: FONT_LIGHT, fontSize: 10.5, color: DARK_MUTED, align: 'center', margin: 0 });
    });
    s.addText('스마트인재개발원 KDT 헬스케어 5팀 · 기업주제(라라랩스)', {
      x: 0, y: 6.95, w: W, h: 0.35, fontFace: FONT_LIGHT, fontSize: 10.5, color: DARK_MUTED, align: 'center', margin: 0,
    });
  }

  const outPath = path.join(__dirname, '귀기울임_최종발표_20260828.pptx');
  await pres.writeFile({ fileName: outPath });
  console.log('WROTE', outPath);
}

main().catch((e) => { console.error(e); process.exit(1); });
