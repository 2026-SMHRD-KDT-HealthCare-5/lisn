const pptxgen = require('pptxgenjs');
const { iconPng } = require('./icons');
const Fi = require('react-icons/fi');
const path = require('path');

const REPO = 'C:\\project\\LISN';
const DESIGN = path.join(REPO, 'docs', 'design');

// 시연영상 — tools/capture/build_video.sh 의 출력. 2026.08.22 제작본.
// 다시 만들려면 그 스크립트를 다시 돌리면 됩니다(같은 경로에 씀).
const VIDEO_DIR = 'C:\\Users\\HOME\\AppData\\Local\\Temp\\claude\\C--project-LISN\\fda14023-1984-4212-8502-e63cf816ef36\\scratchpad\\video\\final';
const VIDEO_PATH = path.join(VIDEO_DIR, 'lisn_demo_3min.mp4');
const fs = require('fs');
// pptxgenjs 의 addMedia 는 cover 에 base64 데이터 URI를 요구합니다 —
// path 옵션과 달리 파일 경로를 안 읽습니다. 'lacks a base64 header' 로
// 실패한 뒤 알았습니다.
const VIDEO_COVER = 'data:image/png;base64,' +
  fs.readFileSync(path.join(VIDEO_DIR, 'poster.png')).toString('base64');

// ---- 색 토큰 — docs/design/brand.json 이 정본입니다 ----
// ⚠ 여기에 값을 직접 적지 마세요. 시연영상(tools/capture/build_video.sh)도
//   같은 파일을 읽습니다. 2026.08.22 이전에는 양쪽이 값을 따로 갖고 있어
//   남색·인디고·회색·글꼴이 전부 어긋나 있었습니다.
const BRAND = JSON.parse(fs.readFileSync(path.join(REPO, 'docs', 'design', 'brand.json'), 'utf8'));
const C = BRAND.color;
const NAVY = C.navy;
const NAVY_DARK = C.navyDark;
const INDIGO = C.indigo;
const INDIGO_LT = C.indigoLt;
const WHITE = C.white;
const MUTED = C.muted;
const BG_TINT = C.bg;
const MINT_BG = C.mintBg;
const MINT = C.mint;
const BLUE_BG = C.blueBg;
const BLUE = C.blue;
const PEACH_BG = C.peachBg;
const PEACH = C.peach;
const LINE = C.line;

// ---------------------------------------------------------------------------
// 폰트 — Noto Sans KR
//
// ⚠ **윈도우 기본 탑재가 아닙니다.** 이 PC 에는 있지만 다른 PC 에서 PPTX 를
//   열면 대체 폰트로 바뀌어 레이아웃이 밀립니다. pptxgenjs 는 폰트 임베딩을
//   못 하므로 파일만으로는 해결되지 않습니다.
//
//   대응 두 가지 —
//     ① **발표·배포는 PDF 로.** PDF 는 폰트가 박혀 나가 어느 PC 든 동일합니다
//     ② 다른 PC 에서 편집하려면 그 PC 에 Noto Sans KR 을 설치
//        (무료 · https://fonts.google.com/noto/specimen/Noto+Sans+KR)
//
//   설치가 어려우면 아래 세 상수를 'Malgun Gothic' 으로 바꾸면 됩니다.
//   윈도우 기본 폰트라 어디서든 열리지만, 자간이 헐거워 본문이 한 줄씩
//   더 밀립니다.
//
// 맑은 고딕과 달리 웨이트가 여섯이라 **크기를 안 키우고도 위계**가 만들어집니다.
//   Black    — 표지·대형 숫자처럼 한 장에 하나뿐인 자리
//   Bold     — 슬라이드 제목 · 카드 제목
//   Regular  — 본문
//   DemiLight— 보조 설명 · 캡션. 회색만으로 누르는 것보다 덜 탁합니다
// ---------------------------------------------------------------------------
const FONT = BRAND.font.family;
const FONT_BLACK = BRAND.font.familyBlack;
const FONT_LIGHT = BRAND.font.familyLight;

async function main() {
  const pres = new pptxgen();
  pres.layout = 'LAYOUT_WIDE'; // 13.3 x 7.5
  pres.defineLayout({ name: 'WIDE', width: 13.333, height: 7.5 });
  pres.layout = 'WIDE';

  const W = 13.333, H = 7.5;

  // preload icons
  const icon = {};
  const need = [
    ['watch', Fi.FiWatch, INDIGO], ['trend', Fi.FiTrendingUp, INDIGO], ['chat', Fi.FiMessageCircle, INDIGO],
    ['shield', Fi.FiShield, INDIGO], ['lock', Fi.FiLock, INDIGO], ['users', Fi.FiUsers, WHITE],
    ['phone', Fi.FiSmartphone, INDIGO], ['server', Fi.FiServer, WHITE], ['db', Fi.FiDatabase, WHITE],
    ['check', Fi.FiCheckCircle, MINT], ['eyeoff', Fi.FiEyeOff, BLUE], ['clock', Fi.FiClock, PEACH],
    ['bar', Fi.FiBarChart2, INDIGO], ['layers', Fi.FiLayers, WHITE], ['target', Fi.FiTarget, INDIGO],
    ['bellslash', Fi.FiBellOff, MUTED], ['code', Fi.FiCode, WHITE], ['smile', Fi.FiSmile, MINT],
    ['pause', Fi.FiPauseCircle, PEACH], ['mappin', Fi.FiMapPin, BLUE],
    ['watch_navy', Fi.FiWatch, NAVY], ['trend_navy', Fi.FiTrendingUp, NAVY], ['chat_navy', Fi.FiMessageCircle, NAVY],
    ['users_navy', Fi.FiUsers, NAVY], ['server_navy', Fi.FiServer, NAVY], ['db_navy', Fi.FiDatabase, NAVY],
    ['home_ico', Fi.FiHome, INDIGO], ['grid', Fi.FiGrid, INDIGO], ['send', Fi.FiSend, WHITE],
    ['arrowright', Fi.FiArrowRight, MUTED], ['arrowright_w', Fi.FiArrowRight, WHITE],
    ['x', Fi.FiX, PEACH], ['flag', Fi.FiFlag, INDIGO],
  ];
  for (const [k, comp, color] of need) icon[k] = await iconPng(comp, color, 256);

  const img = (name) => path.join(DESIGN, name + '.png');

  // ================= helpers =================
  function bgSlide(dark) {
    const s = pres.addSlide();
    s.background = { color: dark ? NAVY_DARK : WHITE };
    return s;
  }

  function kicker(s, text, dark) {
    s.addText(text.toUpperCase(), {
      x: 0.6, y: 0.42, w: 8, h: 0.35, fontFace: FONT, fontSize: 12, bold: true,
      color: dark ? INDIGO_LT : INDIGO, charSpacing: 2,
    });
  }

  function title(s, text, dark, y = 0.72, size = 30) {
    s.addText(text, {
      x: 0.6, y, w: 12.2, h: 0.9, fontFace: FONT, fontSize: size, bold: true,
      color: dark ? WHITE : NAVY, margin: 0,
    });
  }

  // 페이지 번호는 **자동으로 셉니다.** 전에는 pageNum(s, 7, ...) 처럼 손으로
  // 박혀 있어서, 슬라이드를 중간에 하나 끼우면 그 뒤가 전부 어긋났습니다.
  // 섹션 표지를 넣으면서 실제로 밟을 뻔한 함정입니다.
  let pageNo = 0;
  function pageNum(s, dark) {
    pageNo += 1;
    s.addText(String(pageNo).padStart(2, '0'), {
      x: W - 1.0, y: H - 0.55, w: 0.6, h: 0.35, fontFace: FONT_LIGHT, fontSize: 10,
      color: dark ? 'A9B3D6' : 'B7BCCB', align: 'right',
    });
    s.addText('귀기울임 LISN', {
      x: 0.6, y: H - 0.55, w: 4, h: 0.35, fontFace: FONT_LIGHT, fontSize: 10,
      color: dark ? 'A9B3D6' : 'B7BCCB',
    });
  }

  /// 섹션 표지 — 예시 데크 둘 다 쓰는 방식입니다(번호 배지 + 섹션명).
  ///
  /// 발표 중 **지금 어디인지**를 알려주는 자리라 정보를 넣지 않습니다.
  /// 7분 안에 넘겨야 하므로 3~5초짜리 숨 고르는 장으로만 씁니다.
  function sectionCover(s, no, ko, en) {
    s.background = { color: NAVY_DARK };
    // 표지·종료와 같은 동심원 모티프를 옅게 깔아 한 벌로 묶습니다.
    soundRings(s, W - 1.6, H - 1.2, {
      count: 4, startD: 1.4, step: 1.5, color: INDIGO_LT, width: 1.2,
      transparencyStart: 55, transparencyStep: 12,
    });
    s.addShape('ellipse', { x: 0.9, y: 2.75, w: 1.5, h: 1.5, fill: { color: INDIGO }, line: { type: 'none' } });
    s.addText(no, {
      x: 0.9, y: 2.75, w: 1.5, h: 1.5, fontFace: FONT_BLACK, fontSize: 30, bold: true,
      color: WHITE, align: 'center', valign: 'middle', margin: 0,
    });
    s.addText(en.toUpperCase(), {
      x: 2.75, y: 2.9, w: 8, h: 0.35, fontFace: FONT, fontSize: 12, bold: true,
      color: INDIGO_LT, charSpacing: 2, margin: 0,
    });
    s.addText(ko, {
      x: 2.75, y: 3.3, w: 9.5, h: 0.75, fontFace: FONT_BLACK, fontSize: 34, bold: true,
      color: WHITE, margin: 0,
    });
    // 표지에도 번호를 붙입니다. 빼면 인쇄된 번호와 실제 장수가 어긋나
    // 「13쪽 보세요」가 안 통합니다.
    pageNum(s, true);
  }

  // 동심원 — "귀기울임"의 브랜드 모티프. 소리가 퍼져나가는 파동을 그립니다.
  // 시작·종료 슬라이드에서 같은 형태를 반복해 통일감을 줍니다.
  function soundRings(s, cx, cy, opts = {}) {
    const count = opts.count || 5;
    const startD = opts.startD || 1.5;
    const step = opts.step || 1.65;
    const color = opts.color || INDIGO_LT;
    const width = opts.width || 1.5;
    let trans = opts.transparencyStart != null ? opts.transparencyStart : 18;
    const transStep = opts.transparencyStep || 15;
    for (let i = 0; i < count; i++) {
      const d = startD + step * i;
      s.addShape('ellipse', {
        x: cx - d / 2, y: cy - d / 2, w: d, h: d,
        fill: { type: 'none' },
        line: { color, width, transparency: Math.min(trans, 90) },
      });
      trans += transStep;
    }
    // 발신점 — 파동이 시작되는 자리
    s.addShape('ellipse', {
      x: cx - 0.09, y: cy - 0.09, w: 0.18, h: 0.18,
      fill: { color }, line: { type: 'none' },
    });
  }

  function iconCircle(s, x, y, d, bg, iconKey, iconScale = 0.55) {
    s.addShape('ellipse', { x, y, w: d, h: d, fill: { color: bg }, line: { type: 'none' } });
    const isz = d * iconScale;
    s.addImage({ data: icon[iconKey], x: x + (d - isz) / 2, y: y + (d - isz) / 2, w: isz, h: isz });
  }

  function card(s, x, y, w, h, opts = {}) {
    s.addShape('roundRect', {
      x, y, w, h, rectRadius: 0.09,
      fill: { color: opts.fill || WHITE },
      line: opts.line === false ? { type: 'none' } : { color: LINE, width: 1 },
      shadow: opts.shadow === false ? undefined : {
        type: 'outer', color: '1B2547', opacity: 0.10, blur: 10, offset: 3, angle: 90,
      },
    });
  }

  // ============================================================
  // 1. TITLE
  // ============================================================
  {
    const s = bgSlide(true);
    // 겹친 원 — 슬라이드 경계 안에 완전히 담기도록 좌표를 맞춥니다(우상단 코너에 밀착).
    s.addShape('ellipse', { x: W - 6.5, y: 0, w: 6.5, h: 6.5, fill: { color: NAVY }, line: { type: 'none' } });
    s.addShape('ellipse', { x: W - 5.1, y: 0.5, w: 4.6, h: 4.6, fill: { color: '2C3A6B' }, line: { type: 'none' } });

    s.addText('스마트인재개발원 KDT 헬스케어 5팀 · 기업주제(라라랩스)', {
      x: 0.9, y: 1.65, w: 9, h: 0.4, fontFace: FONT, fontSize: 13, color: INDIGO_LT, bold: true, charSpacing: 1,
    });
    // 표지 제호만 Black. 한 장에 하나뿐인 자리라 여기서만 씁니다.
    s.addText('귀기울임', {
      x: 0.85, y: 2.15, w: 10, h: 1.5, fontFace: FONT_BLACK, fontSize: 60, bold: true, color: WHITE, margin: 0,
    });
    s.addText('LISN', {
      x: 0.92, y: 3.35, w: 6, h: 0.5, fontFace: FONT, fontSize: 18, color: INDIGO_LT, bold: true, charSpacing: 4,
    });
    s.addText('멀티모달 라이프로그 감정 분석 기반 맞춤형 LLM 케어 및 모니터링 시스템', {
      x: 0.92, y: 4.0, w: 8.6, h: 0.6, fontFace: FONT_LIGHT, fontSize: 16, color: 'D7DCF5',
    });

    s.addShape('line', { x: 0.92, y: 4.85, w: 3.2, h: 0, line: { color: '3E4A7A', width: 1 } });

    s.addText('최종 발표', { x: 0.92, y: 5.05, w: 3, h: 0.4, fontFace: FONT_LIGHT, fontSize: 12, color: 'A9B3D6' });
    s.addText('2026. 08. 28', { x: 0.92, y: 5.4, w: 4, h: 0.5, fontFace: FONT, fontSize: 22, bold: true, color: WHITE });

    const members = ['이응균 · PM', '김건영 · AI/DATA', '윤일준 · 백엔드/DB', '함은선 · 프론트엔드'];
    let mx = 0.92;
    members.forEach((m) => {
      s.addText(m, {
        x: mx, y: 6.55, w: 2.85, h: 0.4, fontFace: FONT_LIGHT, fontSize: 11.5, color: 'C7CDEA',
      });
      mx += 2.9;
    });
  }

  // ============================================================
  // 2. 목차
  // ============================================================
  {
    const s = bgSlide(true);
    kicker(s, 'Contents', true);
    title(s, '목차', true, 0.85, 34);

    // ⚠ **실제 슬라이드 순서와 같아야 합니다.** 섹션 표지를 넣으면서
    //   목차와 본문이 어긋나면 발표 중에 그대로 드러납니다.
    //
    // 5섹션 → 3섹션으로 줄였습니다(2026.08.22). 발표 10분 중 시연영상이
    // 3분이라 말할 시간이 7분뿐인데, 섹션 표지 5장이 25초를 먹었습니다.
    const items = [
      ['01', '문제와 해결', '왜 귀기울임인가 · 먼저 다가간다는 것'],
      ['02', '어떻게 만들었나', '아키텍처 · AI 판단 방식 · 안전 설계 · 보안'],
      ['03', '성과와 한계', '실측 지표 · 관제 화면 · 못 한 것'],
    ];
    // 3개로 줄면서 여백이 생겨 항목을 키웠습니다. 마지막 항목이
    // 푸터(H-0.55)를 넘지 않는지가 유일한 제약입니다.
    let y = 2.25;
    items.forEach(([no, t, d], i) => {
      s.addText(no, { x: 0.9, y, w: 1.2, h: 0.95, fontFace: FONT_BLACK, fontSize: 30, bold: true, color: INDIGO_LT, margin: 0 });
      s.addText(t, { x: 2.35, y: y + 0.03, w: 6.0, h: 0.55, fontFace: FONT, fontSize: 23, bold: true, color: WHITE, margin: 0 });
      s.addText(d, { x: 2.35, y: y + 0.58, w: 8.5, h: 0.4, fontFace: FONT_LIGHT, fontSize: 12.5, color: 'A9B3D6', margin: 0 });
      if (i < items.length - 1) s.addShape('line', { x: 0.9, y: y + 1.12, w: 9.6, h: 0, line: { color: '333F6E', width: 0.75 } });
      y += 1.28;
    });
    pageNum(s, true);
  }

  // ============================================================
  // [섹션 표지] 01 문제와 답
  // ============================================================
  {
    const s = pres.addSlide();
    sectionCover(s, '01', '문제와 해결', 'Problem & Answer');
  }

  // ============================================================
  // [병합] 문제 정의 + 프로젝트 개요  (구 3·4번)
  // ============================================================
  // 7분 발표라 두 장을 한 장으로 합쳤습니다(2026.08.22).
  //
  // 문제 3가지 중 **②「앱을 열어야 시작된다」만 남깁니다.** 나머지 둘은
  // 다음 장(선제 접촉)을 이해하는 데 필요 없고, ②만이 차별점의 전제입니다.
  // 대신 「관찰 → 판단 → 접촉」 3단계를 같은 장 아래쪽에 붙여, 문제와 답을
  // 한 화면에서 잇습니다.
  {
    const s = bgSlide(false);
    kicker(s, 'Problem & Answer', false);
    title(s, '데이터는 쌓이는데, 사용자는 앱을 열지 않습니다', false);

    // 위: 문제 — 한 문장으로 압축
    card(s, 0.6, 1.85, 12.1, 1.25, { fill: BG_TINT, line: false, shadow: false });
    iconCircle(s, 1.0, 2.15, 0.65, WHITE, 'eyeoff', 0.55);
    s.addText('걸음·수면·심박은 매일 기록되지만, 케어로 이어지려면 사용자가 앱을 열어야 합니다.', {
      x: 1.95, y: 2.0, w: 10.4, h: 0.45, fontFace: FONT, fontSize: 15.5, bold: true, color: NAVY, margin: 0,
    });
    s.addText('그런데 정작 힘든 순간에는 사용자가 앱을 열 힘조차 없습니다. 감지해 놓고도 사용자를 기다리는 구조가 문제입니다.', {
      x: 1.95, y: 2.48, w: 10.4, h: 0.45, fontFace: FONT_LIGHT, fontSize: 12.5, color: MUTED, margin: 0,
    });

    // 아래: 답 — 3단계
    s.addText('그래서 «관찰 → 판단 → 선제 접촉»으로 설계했습니다', {
      x: 0.6, y: 3.35, w: 12.1, h: 0.45, fontFace: FONT, fontSize: 15, bold: true, color: NAVY, margin: 0,
    });

    const steps = [
      ['01', 'watch', '자동 수집', 'Health Connect로 걸음·수면·심박·HRV를 앱이 읽어 서버로 보냅니다. 사용자가 입력할 것이 없습니다.'],
      ['02', 'trend', '평소와 얼마나 다른가', '그 사람 본인의 평소(14일)와 비교해 징후를 봅니다. 감정을 분류하지 않습니다.'],
      ['03', 'chat', '선제 접촉', '콘텐츠 추천에서 그치지 않고, 필요하면 시스템이 먼저 말을 거는 선제 접촉까지 이어집니다.'],
    ];
    const cw = 3.85, gap = 0.3, x0 = 0.6, cy = 3.95;
    steps.forEach(([no, ic, h, b], i) => {
      const x = x0 + i * (cw + gap);
      card(s, x, cy, cw, 2.45, { fill: WHITE });
      iconCircle(s, x + 0.32, cy + 0.3, 0.62, [MINT_BG, BLUE_BG, PEACH_BG][i], ic);
      s.addText(no, { x: x + 1.1, y: cy + 0.3, w: 0.9, h: 0.62, fontFace: FONT, fontSize: 13, bold: true, color: INDIGO_LT, valign: 'middle', margin: 0 });
      s.addText(h, { x: x + 0.32, y: cy + 1.05, w: cw - 0.64, h: 0.42, fontFace: FONT, fontSize: 15.5, bold: true, color: NAVY, margin: 0 });
      s.addText(b, { x: x + 0.32, y: cy + 1.5, w: cw - 0.64, h: 0.85, fontFace: FONT_LIGHT, fontSize: 11, color: MUTED, margin: 0, lineSpacingMultiple: 1.3 });
      if (i < 2) s.addImage({ data: icon['arrowright'], x: x + cw + 0.02, y: cy + 0.45, w: 0.26, h: 0.26 });
    });
    pageNum(s, false);
  }

  // ============================================================
  // 5. 핵심 차별점 — 선제 접촉
  // ============================================================
  {
    const s = bgSlide(true);
    kicker(s, 'Key Differentiator', true);
    title(s, '사용자가 앱을 열기 전에, 먼저 다가갑니다', true);

    // left: 기존 서비스
    s.addShape('roundRect', { x: 0.6, y: 1.95, w: 5.8, h: 2.5, rectRadius: 0.09, fill: { color: '2A3564' }, line: { type: 'none' } });
    s.addText('기존 서비스', { x: 0.95, y: 2.15, w: 4, h: 0.4, fontFace: FONT, fontSize: 13, bold: true, color: 'A9B3D6' });
    s.addText('감지 → 사용자가 앱을 열어야 확인 → 끝', {
      x: 0.95, y: 2.6, w: 5.1, h: 0.8, fontFace: FONT, fontSize: 15, color: WHITE, bold: true,
    });
    s.addText('위기일수록 앱을 열 힘이 없는데, 확인 자체를 사용자에게 맡깁니다.', {
      x: 0.95, y: 3.35, w: 5.1, h: 0.9, fontFace: FONT_LIGHT, fontSize: 11.5, color: 'C7CDEA',
    });

    // right: 귀기울임
    s.addShape('roundRect', { x: 6.9, y: 1.95, w: 5.85, h: 2.5, rectRadius: 0.09, fill: { color: INDIGO }, line: { type: 'none' } });
    s.addText('귀기울임', { x: 7.25, y: 2.15, w: 4, h: 0.4, fontFace: FONT, fontSize: 13, bold: true, color: 'E3E7FF' });
    s.addText('감지 → 시스템이 먼저 말을 겁니다', {
      x: 7.25, y: 2.6, w: 5.3, h: 0.8, fontFace: FONT, fontSize: 15, color: WHITE, bold: true,
    });
    s.addText('연속 이탈 3일 → 조건 6개 검사 → 첫 발화 생성 → 세션 선생성 → FCM 푸시 · 홈 카드 · 배너로 먼저 말을 겁니다', {
      x: 7.25, y: 3.35, w: 5.3, h: 0.9, fontFace: FONT_LIGHT, fontSize: 11.5, color: 'EAEEFF',
    });

    // guardrails row
    s.addText('"감시 아닌가요?" — 그래서 장치를 마련했습니다', {
      x: 0.6, y: 4.75, w: 8, h: 0.4, fontFace: FONT, fontSize: 14, bold: true, color: WHITE,
    });
    const guards = [
      ['bellslash', '옵트인', '케어 알림은 콘텐츠 알림과 따로 동의받습니다'],
      ['clock', '빈도 상한', '쿨다운 3일 · 하루 1회 · 09~21시'],
      ['pause', '겹침 방지', '같은 날 콘텐츠 알림이 있으면 보류합니다'],
      ['flag', '근거 제시', '왜 말을 걸었는지 첫 마디에 담습니다'],
    ];
    const gw = 2.95, gx0 = 0.6;
    guards.forEach(([ic, h, b], i) => {
      const x = gx0 + i * (gw + 0.13);
      s.addShape('roundRect', { x, y: 5.3, w: gw, h: 1.65, rectRadius: 0.08, fill: { color: '2A3564' }, line: { type: 'none' } });
      iconCircle(s, x + 0.22, 5.5, 0.5, '384280', ic, 0.55);
      s.addText(h, { x: x + 0.22, y: 6.08, w: gw - 0.4, h: 0.32, fontFace: FONT, fontSize: 12.5, bold: true, color: WHITE, margin: 0 });
      s.addText(b, { x: x + 0.22, y: 6.4, w: gw - 0.4, h: 0.5, fontFace: FONT_LIGHT, fontSize: 9.5, color: 'B9C0E6', margin: 0, lineSpacingMultiple: 1.15 });
    });
    pageNum(s, true);
  }

  // ============================================================
  // 5b. 3분 시연 영상
  //
  // 직전 슬라이드가 "먼저 다가갑니다"라는 주장이라면, 여기는 그 증거입니다.
  // 주장 → 증명 → 02장의 구현 방식 순서로 놓았습니다.
  //
  // ⚠ PowerPoint 재생 전용입니다. PDF 로 내보내면 영상이 정지 이미지(커버)로만
  //   보입니다 — 발표는 PPTX 로, 배포용 PDF 는 이 장이 그림 한 장으로 남습니다.
  // ============================================================
  {
    const s = bgSlide(false);
    kicker(s, 'Live Demo', false);
    title(s, '3분으로 보는 귀기울임', false);
    s.addText('클릭하면 재생됩니다', {
      x: 0.6, y: 1.32, w: 8, h: 0.35, fontFace: FONT_LIGHT, fontSize: 12, color: MUTED, margin: 0,
    });

    // 16:9 원본을 그대로 유지합니다. 페이지 번호(H-0.55)와 겹치지 않도록
    // 여유를 두고 크기를 잡았습니다.
    const vw = 8.6, vh = (vw * 9) / 16;
    const vx = (W - vw) / 2, vy = 1.85;
    s.addShape('roundRect', {
      x: vx - 0.06, y: vy - 0.06, w: vw + 0.12, h: vh + 0.12, rectRadius: 0.08,
      fill: { color: WHITE }, line: { color: LINE, width: 1 },
      shadow: { type: 'outer', color: '1B2547', opacity: 0.12, blur: 18, offset: 5, angle: 90 },
    });
    s.addMedia({
      type: 'video', path: VIDEO_PATH, cover: VIDEO_COVER,
      x: vx, y: vy, w: vw, h: vh,
    });
    pageNum(s, false);
  }

  // ============================================================
  // [섹션 표지] 02 어떻게 만들었나
  // ============================================================
  {
    const s = pres.addSlide();
    sectionCover(s, '02', '어떻게 만들었나', 'How We Built It');
  }

  // ============================================================
  // 6. 시스템 아키텍처
  // ============================================================
  {
    const s = bgSlide(false);
    kicker(s, 'Architecture', false);
    title(s, '왜 서버를 둘로 나눴나', false);

    const boxY = 2.5, boxH = 1.5;
    const boxes = [
      { x: 0.6, w: 3.0, title: 'Flutter 앱', sub: '사용자 · 관리자 웹', ic: 'phone', bg: NAVY },
      { x: 4.85, w: 3.6, title: '비즈니스 서버', sub: 'FastAPI · 인증·대화·위기키워드·정책', ic: 'server_navy', bg: WHITE },
      { x: 9.7, w: 3.05, title: 'AI 추론 서버', sub: 'FastAPI · 개인 기준선 이탈 탐지', ic: 'db_navy', bg: WHITE },
    ];
    boxes.forEach((b) => {
      if (b.bg === NAVY) {
        s.addShape('roundRect', { x: b.x, y: boxY, w: b.w, h: boxH, rectRadius: 0.1, fill: { color: NAVY }, line: { type: 'none' } });
        iconCircle(s, b.x + 0.28, boxY + 0.28, 0.55, '33407A', 'phone', 0.55);
        s.addText(b.title, { x: b.x + 0.28, y: boxY + 0.92, w: b.w - 0.5, h: 0.35, fontFace: FONT, fontSize: 14.5, bold: true, color: WHITE, margin: 0 });
      } else {
        card(s, b.x, boxY, b.w, boxH, { fill: WHITE });
        iconCircle(s, b.x + 0.28, boxY + 0.28, 0.55, BLUE_BG, b.ic, 0.55);
        s.addText(b.title, { x: b.x + 0.28, y: boxY + 0.92, w: b.w - 0.5, h: 0.35, fontFace: FONT, fontSize: 14.5, bold: true, color: NAVY, margin: 0 });
      }
    });
    // arrows between
    [[3.6, 4.85], [8.45, 9.7]].forEach(([ax1, ax2]) => {
      s.addImage({ data: icon['arrowright'], x: ax1 + (ax2 - ax1) / 2 - 0.15, y: boxY + boxH / 2 - 0.15, w: 0.3, h: 0.3 });
    });
    s.addText('걸음·수면·심박 push', { x: 3.62, y: boxY - 0.32, w: 1.25, h: 0.3, fontFace: FONT_LIGHT, fontSize: 8.5, color: MUTED, align: 'center' });
    s.addText('내부 통신', { x: 8.5, y: boxY - 0.32, w: 1.15, h: 0.3, fontFace: FONT_LIGHT, fontSize: 8.5, color: MUTED, align: 'center' });

    s.addText([
      { text: '위기 키워드 필터는 비즈니스 서버 안에 둡니다.  ', options: { bold: true, color: NAVY } },
      { text: 'AI 서버가 죽어도 탐지가 멈추면 안 되기 때문입니다.', options: { color: MUTED } },
    ], { x: 0.6, y: 4.45, w: 12.1, h: 0.5, fontFace: FONT, fontSize: 13.5, margin: 0 });

    card(s, 0.6, 4.95, 12.1, 1.5, { fill: BG_TINT, line: false, shadow: false });
    s.addText('앱이 먼저 보내고, 서버는 끌어오지 않습니다', {
      x: 0.95, y: 5.12, w: 11.4, h: 0.38, fontFace: FONT, fontSize: 14.5, bold: true, color: NAVY,
    });
    // ⚠ **WorkManager 15분 주기를 반드시 남깁니다.** 이게 없으면
    //   「앱을 안 여는 사람은 데이터가 안 오는 것 아니냐」에 답할 근거가
    //   사라집니다 — 선제 접촉이라는 차별점의 전제를 무너뜨리는 질문입니다.
    s.addText('Health Connect는 Android 단말 안의 권한 모델이라 서버가 가질 OAuth 토큰이 없습니다. 그래서 앱이 읽어 push하고, 앱을 열지 않아도 WorkManager가 15분 주기로 백그라운드 전송합니다. 서버가 안 가져오는 것이 아니라, 가져올 수가 없습니다.', {
      x: 0.95, y: 5.5, w: 11.4, h: 0.85, fontFace: FONT_LIGHT, fontSize: 11.5, color: MUTED, lineSpacingMultiple: 1.3,
    });

    // 기술 스택은 별도 장을 두지 않고 여기 한 줄로 흡수했습니다(2026.08.22).
    // 이름 나열은 심사위원이 읽으면 되는 정보라 말할 시간을 쓰지 않습니다.
    s.addText([
      { text: 'STACK   ', options: { bold: true, color: INDIGO, charSpacing: 1 } },
      { text: 'Flutter · Health Connect · WorkManager   |   FastAPI · SQLAlchemy · PostgreSQL 17   |   React · Vite   |   OpenAI API   |   인프라: 로컬 데모', options: { color: MUTED } },
    ], { x: 0.6, y: 6.6, w: 12.1, h: 0.35, fontFace: FONT_LIGHT, fontSize: 10, margin: 0 });
    pageNum(s, false);
  }

  // ============================================================
  // 7. AI 설계 여정
  // ============================================================
  {
    const s = bgSlide(false);
    kicker(s, 'AI Design Journey', false);
    title(s, '감정 분류 모델은 검증하고 접었습니다', false);

    const steps = [
      ['시도', '감정 라벨이 붙은 데이터로 분류 모델을 학습하려 했습니다', MINT_BG, MINT],
      ['검증', '국내 라벨 데이터셋을 구하지 못해 공개 데이터(GLOBEM)로 검증했더니 ROC-AUC 0.528, 무작위 수준이었습니다', PEACH_BG, PEACH],
      ['전환', '개인 기준선 이탈 탐지로 방향을 바꿨습니다 — 중앙값·MAD robust z, 지표 7개 중 2개 이상 이탈', BLUE_BG, BLUE],
    ];
    const cw = 3.85, gap = 0.3, x0 = 0.6, y0 = 2.15;
    steps.forEach(([h, b, bg, fg], i) => {
      const x = x0 + i * (cw + gap);
      card(s, x, y0, cw, 2.15, { fill: WHITE });
      // 단계 색은 **숫자 배지**가 지고 갑니다. 카드 위에 색 띠를 두르면
      // 어느 발표자료에나 있는 장식이 되고, 색이 무엇을 뜻하는지도 흐려집니다.
      s.addShape('ellipse', { x: x + 0.3, y: y0 + 0.28, w: 0.46, h: 0.46, fill: { color: bg }, line: { type: 'none' } });
      s.addText(String(i + 1), {
        x: x + 0.3, y: y0 + 0.28, w: 0.46, h: 0.46, fontFace: FONT, fontSize: 13, bold: true,
        color: fg, align: 'center', valign: 'middle', margin: 0,
      });
      s.addText(h, { x: x + 0.9, y: y0 + 0.28, w: cw - 1.2, h: 0.46, fontFace: FONT, fontSize: 17, bold: true, color: NAVY, valign: 'middle', margin: 0 });
      s.addText(b, { x: x + 0.3, y: y0 + 0.92, w: cw - 0.6, h: 1.1, fontFace: FONT_LIGHT, fontSize: 11.5, color: MUTED, lineSpacingMultiple: 1.3 });
      if (i < 2) s.addImage({ data: icon['arrowright'], x: x + cw + 0.02, y: y0 + 0.95, w: 0.26, h: 0.26 });
    });

    card(s, 0.6, 4.75, 12.1, 1.85, { fill: NAVY, line: false, shadow: false });
    s.addText('"감정을 분석·분류합니다"라고 말하지 않는 이유', {
      x: 0.95, y: 4.95, w: 11.4, h: 0.4, fontFace: FONT, fontSize: 14.5, bold: true, color: WHITE,
    });
    s.addText('감정 코드는 이탈 정도를 표시하는 규칙 기반 산출값입니다. 학습된 분류기가 정한 값이 아니라, 코드에서 model_version이 "rule-"로 시작하는 것이 그 표시입니다. 대신 그 사람 본인의 평소와 비교하는 개인 기준선 이탈 탐지로 실제 서비스를 완성했습니다.', {
      x: 0.95, y: 5.38, w: 11.4, h: 1.1, fontFace: FONT_LIGHT, fontSize: 12, color: 'C7CDEA', lineSpacingMultiple: 1.3,
    });
    pageNum(s, false);
  }

  // ============================================================
  // 8. 위기 탐지 2단계
  // ============================================================
  {
    const s = bgSlide(false);
    kicker(s, 'Crisis Detection', false);
    title(s, '위기 탐지는 2단계입니다', false);

    const stages = [
      ['1차', '키워드 규칙', '백엔드 내장', '외부 API가 죽어도 탐지가 멈추지 않습니다', '단독 재현율', '0.081', PEACH_BG, PEACH],
      ['2차', 'LLM 문맥 판정', '오탐 감소', '문장 맥락까지 읽어 더 정밀하게 판정합니다', '최종 재현율', '0.946', MINT_BG, MINT],
    ];
    const cw = 5.85, x0 = 0.6, y0 = 2.1;
    stages.forEach(([no, h, tag, b, statL, statV, bg, fg], i) => {
      const x = x0 + i * (cw + 0.3);
      card(s, x, y0, cw, 2.7, { fill: WHITE });
      iconCircle(s, x + 0.35, y0 + 0.32, 0.65, bg, i === 0 ? 'eyeoff' : 'chat_navy', 0.5);
      s.addText(no, { x: x + 1.2, y: y0 + 0.3, w: 1.5, h: 0.35, fontFace: FONT, fontSize: 12, bold: true, color: fg });
      s.addText(h, { x: x + 1.2, y: y0 + 0.6, w: cw - 1.5, h: 0.4, fontFace: FONT, fontSize: 18, bold: true, color: NAVY });
      s.addText(b, { x: x + 0.35, y: y0 + 1.25, w: cw - 0.7, h: 0.7, fontFace: FONT_LIGHT, fontSize: 12, color: MUTED, lineSpacingMultiple: 1.3 });
      s.addText(statL, { x: x + 0.35, y: y0 + 1.95, w: cw - 0.7, h: 0.3, fontFace: FONT_LIGHT, fontSize: 10.5, color: MUTED });
      s.addText(statV, { x: x + 0.35, y: y0 + 2.18, w: cw - 0.7, h: 0.5, fontFace: FONT, fontSize: 24, bold: true, color: fg, margin: 0 });
      if (i === 0) s.addImage({ data: icon['arrowright'], x: x + cw + 0.02, y: y0 + 1.25, w: 0.26, h: 0.26 });
    });

    // ── 구 「안전 설계 원칙」 4칸 중 **고유한 2칸만** 흡수했습니다(2026.08.22).
    //    「CRITICAL 답변 폐기」는 바로 아래 문단과, 「옵트인·빈도 상한」은
    //    선제 접촉 장의 4장치와 완전히 겹쳐서 뺐습니다. 같은 말을 두 번
    //    하는 데 7분 중 55초를 쓸 수 없습니다.
    card(s, 0.6, 4.9, 12.1, 1.85, { fill: BG_TINT, line: false, shadow: false });
    s.addText('정신건강 서비스라서 다르게 만든 것', {
      x: 0.95, y: 5.05, w: 11.4, h: 0.38, fontFace: FONT, fontSize: 14.5, bold: true, color: NAVY,
    });
    s.addText([
      { text: 'CRITICAL이면 이미 만든 답변도 버립니다. ', options: { bold: true, color: NAVY } },
      { text: '위기 판정과 응답 생성을 동시에 돌리지만, CRITICAL이면 만들어 둔 응답을 버립니다. 그래서 스트리밍을 쓰지 않습니다. 판정 전에 흘려보낸 글자는 되돌릴 수 없습니다.', options: { color: MUTED } },
    ], { x: 0.95, y: 5.45, w: 11.4, h: 0.5, fontFace: FONT_LIGHT, fontSize: 11.5, lineSpacingMultiple: 1.25, margin: 0 });
    s.addText([
      { text: '경고색은 쓰지 않습니다. ', options: { bold: true, color: NAVY } },
      { text: '빨강·주황은 불안을 키워 회피를 부릅니다.   ', options: { color: MUTED } },
      { text: '데이터가 없다고 "정상"이라 하지도 않습니다. ', options: { bold: true, color: NAVY } },
      { text: '3일 미만이면 422로 끊습니다. 편차 0을 정상으로 적재하면 위험을 놓칩니다.', options: { color: MUTED } },
    ], { x: 0.95, y: 6.02, w: 11.4, h: 0.6, fontFace: FONT_LIGHT, fontSize: 11.5, lineSpacingMultiple: 1.25, margin: 0 });
    pageNum(s, false);
  }

  // ============================================================
  // [섹션 표지] 03 성과와 한계
  // ============================================================
  {
    const s = pres.addSlide();
    sectionCover(s, '03', '성과와 한계', 'Results & Limits');
  }

  // ============================================================
  // 10. 성과 지표
  // ============================================================
  {
    const s = bgSlide(true);
    kicker(s, 'Results', true);
    title(s, '실측으로 증명한 것만 남겼습니다', true);

    // ⚠ **평가셋 타일에 「위기 111 · 비위기 100」을 반드시 남깁니다.**
    //   0.946 의 분모입니다. 이게 없으면 「0.946 이 몇 건 중 몇 건인가」
    //   「위기 사례가 몇 건인데요」에 답할 근거가 화면에서 사라지고,
    //   한계 장의 「미탐 6건」과 산술로 이어지지 않습니다(111×0.946≒105).
    const tiles = [
      ['0.946', '위기 판정 재현율'],
      ['0.921', '위기 판정 정밀도'],
      ['0.933', '위기 판정 F1-Score'],
      ['211건', '자체 평가셋 · 위기 111 · 비위기 100\n2인 교차 라벨링'],
      ['33개', '백엔드 API 엔드포인트'],
      ['9개', 'DB 테이블 · UUID·TIMESTAMPTZ'],
      ['319건', '회귀 테스트\n백엔드 118 · AI 22 · 앱 165 · 관리자 14'],
      ['2052ms', 'AI 챗봇 응답 지연 최댓값\n(예산 3000ms)'],
    ];
    const cw = 2.9, ch = 1.62, gx = 0.19, gy = 0.22, x0 = 0.6, y0 = 1.95;
    tiles.forEach((t, i) => {
      const col = i % 4, row = Math.floor(i / 4);
      const x = x0 + col * (cw + gx), y = y0 + row * (ch + gy);
      s.addShape('roundRect', { x, y, w: cw, h: ch, rectRadius: 0.09, fill: { color: '1E2A54' }, line: { type: 'none' } });
      s.addText(t[0], { x: x + 0.22, y: y + 0.14, w: cw - 0.4, h: 0.68, fontFace: FONT, fontSize: 24, bold: true, color: WHITE, margin: 0 });
      s.addText(t[1], { x: x + 0.22, y: y + 0.84, w: cw - 0.4, h: 0.68, fontFace: FONT_LIGHT, fontSize: 9, color: 'A9B3D6', margin: 0, lineSpacingMultiple: 1.2 });
    });

    // ── 구 「검증」 장에서 고유 자산만 흡수했습니다(2026.08.22).
    //    지표 숫자는 위 타일과 완전히 겹쳐서 뺐고, **실서버 관통 점검**과
    //    **문서 검사기·스키마 정본**만 남깁니다. 앞의 것은 「단위 테스트만
    //    돌린 것 아니냐」, 뒤의 것은 「수치 관리를 어떻게 했느냐」의 답입니다.
    s.addShape('roundRect', { x: 0.6, y: 5.7, w: 12.1, h: 0.72, rectRadius: 0.09, fill: { color: '1E2A54' }, line: { type: 'none' } });
    s.addText([
      { text: '실서버 관통 점검 ', options: { bold: true, color: WHITE } },
      { text: '13건 수정 뒤 실패 0건    ·    ', options: { color: 'A9B3D6' } },
      { text: '문서 검사기 4종 ', options: { bold: true, color: WHITE } },
      { text: '— 같은 수치가 문서마다 갈리는 것을 사람이 세지 않고 기계가 대조    ·    ', options: { color: 'A9B3D6' } },
      { text: 'db/schema.sql 정본 ', options: { bold: true, color: WHITE } },
      { text: '— 드리프트 테스트가 모델과 어긋나면 실패', options: { color: 'A9B3D6' } },
    ], { x: 0.95, y: 5.7, w: 11.4, h: 0.72, fontFace: FONT_LIGHT, fontSize: 10.5, valign: 'middle', margin: 0 });

    s.addText('※ 재현율은 8/05 0.793 → 8/12 0.946 — 팀이 확정한 라벨 기준을 프롬프트에 반영하고, 판정 모델을 gpt-5.6 → gpt-5.4로 교체(미탐 23 → 6건, 지연 최댓값 절반 이하)', {
      x: 0.6, y: 6.5, w: 12.1, h: 0.35, fontFace: FONT_LIGHT, fontSize: 9.5, italic: true, color: '8891BE',
    });
    pageNum(s, true);
  }

  // ============================================================
  // 12. 관리자 관제 웹
  // ============================================================
  {
    const s = bgSlide(false);
    kicker(s, 'Admin Console', false);
    title(s, '관리자는 위험한 사람부터 봅니다', false);

    s.addShape('roundRect', { x: 0.54, y: 2.1 - 0.06, w: 7.5 + 0.12, h: 4.69 + 0.12, rectRadius: 0.1, fill: { color: WHITE }, line: { color: LINE, width: 1 }, shadow: { type: 'outer', color: '1B2547', opacity: 0.12, blur: 12, offset: 4, angle: 90 } });
    s.addImage({ path: img('ADMIN_DASH_01'), x: 0.6, y: 2.1, w: 7.5, h: 4.6875 });

    const feats = [
      ['grid', '위험도 분포', '안정·주의·심각이 각각 몇 명인지 한눈에 봅니다'],
      ['users_navy', '목록 · 검색', '이름·이메일·상태로 즉시 필터링'],
      ['chat_navy', '상세 조회', '개인별 라이프로그 추이와 대화 이력을 확인합니다'],
      ['bar', '위기 이력', '판정 시점과 대응 이력을 시간순으로 따라갑니다'],
    ];
    let y = 2.15;
    feats.forEach(([ic, h, b]) => {
      iconCircle(s, 8.55, y, 0.55, BLUE_BG, ic, 0.5);
      s.addText(h, { x: 9.3, y: y - 0.02, w: 3.4, h: 0.35, fontFace: FONT, fontSize: 13.5, bold: true, color: NAVY, margin: 0 });
      s.addText(b, { x: 9.3, y: y + 0.34, w: 3.4, h: 0.6, fontFace: FONT_LIGHT, fontSize: 10.5, color: MUTED, margin: 0, lineSpacingMultiple: 1.25 });
      y += 1.15;
    });
    pageNum(s, false);
  }

  // ============================================================
  // 13. 보안 설계
  // ============================================================
  {
    const s = bgSlide(false);
    kicker(s, 'Security', false);
    title(s, '"전부 암호화"가 아니라 위험도 기반입니다', false);

    const rows = [
      ['전송 구간', 'HTTPS / TLS', '앱 ↔ 백엔드, 백엔드 ↔ AI 서버'],
      ['저장 매체', 'DB 볼륨 디스크 암호화', '클라우드 배포 시에만'],
      ['컬럼 단위', 'AES-256-GCM', 'USERS.phone (연락처만)'],
      ['비밀번호', 'bcrypt', '복호화하지 않음'],
      ['대화 저장', '정규식 PII 마스킹', '전화·주민번호·이메일을 저장 전에 마스킹'],
      ['식별자', 'UUID v4', '테이블 9곳 전부 — 열거 공격 방지'],
    ];
    let y = 2.05;
    const rh = 0.56;
    s.addShape('roundRect', { x: 0.6, y, w: 7.6, h: rh * rows.length, rectRadius: 0.08, fill: { color: WHITE }, line: { color: LINE, width: 1 } });
    rows.forEach(([a, b2, c], i) => {
      const ry = y + i * rh;
      if (i > 0) s.addShape('line', { x: 0.6, y: ry, w: 7.6, h: 0, line: { color: LINE, width: 0.75 } });
      s.addText(a, { x: 0.85, y: ry, w: 1.8, h: rh, fontFace: FONT_LIGHT, fontSize: 11.5, color: MUTED, valign: 'middle', margin: 0 });
      s.addText(b2, { x: 2.7, y: ry, w: 2.1, h: rh, fontFace: FONT, fontSize: 12.5, bold: true, color: INDIGO, valign: 'middle', margin: 0 });
      s.addText(c, { x: 4.85, y: ry, w: 3.25, h: rh, fontFace: FONT_LIGHT, fontSize: 10.5, color: MUTED, valign: 'middle', margin: 0, lineSpacingMultiple: 1.15 });
    });

    s.addShape('roundRect', { x: 8.5, y: 2.05, w: 4.2, h: rh * rows.length, rectRadius: 0.08, fill: { color: NAVY }, line: { type: 'none' } });
    s.addText('왜 전 컬럼 암호화를 하지 않았나', { x: 8.8, y: 2.28, w: 3.6, h: 0.4, fontFace: FONT, fontSize: 13, bold: true, color: WHITE });
    s.addText('라이프로그 측정치를 컬럼 암호화하면 서비스가 동작하지 않습니다. 기간별 집계와 복합 인덱스가 핵심 동작인데, 암호화하면 범위 조회를 할 수 없습니다.', {
      x: 8.8, y: 2.72, w: 3.6, h: 1.15, fontFace: FONT_LIGHT, fontSize: 10.5, color: 'C7CDEA', lineSpacingMultiple: 1.3,
    });
    s.addText('그래서 유출 시 즉각적 2차 피해가 나는 항목(연락처)만 컬럼 암호화하고, 측정치는 전송 구간 보호와 접근통제로 지킵니다.', {
      x: 8.8, y: 3.95, w: 3.6, h: 1.6, fontFace: FONT_LIGHT, fontSize: 10.5, color: 'C7CDEA', lineSpacingMultiple: 1.3,
    });

    card(s, 0.6, 5.75, 12.1, 1.2, { fill: BG_TINT, line: false, shadow: false });
    s.addText([
      { text: '"보안을 덜 했다"가 아니라 ', options: { color: MUTED } },
      { text: '"보안 요구를 기능 제약과 함께 설계했다"', options: { bold: true, color: NAVY } },
      { text: '입니다. 마스킹은 저장 전에 합니다 — 원문은 어디에도 남지 않고, 외부 LLM에도 마스킹된 텍스트만 전송됩니다.', options: { color: MUTED } },
    ], { x: 0.95, y: 5.75, w: 11.4, h: 1.2, fontFace: FONT, fontSize: 12, valign: 'middle', lineSpacingMultiple: 1.3, margin: 0 });
    pageNum(s, false);
  }

  // ============================================================
  // 16. 한계와 다음 단계
  // ============================================================
  {
    const s = bgSlide(false);
    kicker(s, 'Honest Status', false);
    title(s, '못 한 부분은 그대로 말씀드리겠습니다', false);

    const rows = [
      ['Health Connect 실기기 검증', '남음', '에뮬레이터에는 Health Connect가 없어 워커 동작만 확인했습니다.'],
      ['미수신 감지 스케줄러', '남음', 'NFR-DV-002 의 3시간 미갱신 감지입니다. 이걸 주기적으로 돌려 줄 주체를 아직 두지 않았습니다.'],
      ['iOS', '범위 제외', '기술적으로 불가능한 것은 아닙니다. macOS·Xcode·Apple 계정 등 장비와 일정 문제입니다.'],
      ['배포 인프라', '미정', '지금은 로컬 데모 구조입니다. 클라우드 배포는 다음 단계 과제입니다.'],
      ['평가셋 holdout', '없음', '0.946은 이 평가셋 211건에서 나온 값입니다. 새 문장으로는 다시 검증하지 않았습니다.'],
      ['놓친 6건', '분석 완료', '완곡·작별·신변 정리 표현에 몰려 있고, 문장 하나만으로는 사람도 라벨이 갈립니다.'],
    ];
    let y = 2.05;
    const rh = 0.78;
    rows.forEach(([a, tag, c], i) => {
      card(s, 0.6, y, 12.1, rh - 0.08, { fill: WHITE, shadow: false });
      s.addText(a, { x: 0.9, y, w: 3.1, h: rh - 0.08, fontFace: FONT, fontSize: 13, bold: true, color: NAVY, valign: 'middle', margin: 0 });
      const tagColor = tag === '분석 완료' ? MINT : (tag === '범위 제외' ? BLUE : PEACH);
      const tagBg = tag === '분석 완료' ? MINT_BG : (tag === '범위 제외' ? BLUE_BG : PEACH_BG);
      s.addShape('roundRect', { x: 4.05, y: y + (rh - 0.08) / 2 - 0.19, w: 1.15, h: 0.38, rectRadius: 0.19, fill: { color: tagBg }, line: { type: 'none' } });
      s.addText(tag, { x: 4.05, y: y + (rh - 0.08) / 2 - 0.19, w: 1.15, h: 0.38, fontFace: FONT, fontSize: 9.5, bold: true, color: tagColor, align: 'center', valign: 'middle', margin: 0 });
      s.addText(c, { x: 5.4, y, w: 7.1, h: rh - 0.08, fontFace: FONT_LIGHT, fontSize: 10.5, color: MUTED, valign: 'middle', margin: 0, lineSpacingMultiple: 1.2 });
      y += rh;
    });
    pageNum(s, false);
  }

  // ============================================================
  // 18. 감사합니다
  // ============================================================
  {
    const s = bgSlide(true);
    // 시작 슬라이드와 짝을 이루는 원 — 좌하단 코너 안에 완전히 담깁니다.
    s.addShape('ellipse', { x: 0, y: H - 6, w: 6, h: 6, fill: { color: NAVY }, line: { type: 'none' } });
    iconCircle(s, W / 2 - 0.55, 1.55, 1.1, '2C3A6B', 'chat', 0.5);
    s.addText('감사합니다', {
      x: 0, y: 3.0, w: W, h: 1.0, fontFace: FONT, fontSize: 40, bold: true, color: WHITE, align: 'center', margin: 0,
    });
    s.addText('귀기울임 — 먼저 다가가는 정서 케어', {
      x: 0, y: 3.85, w: W, h: 0.5, fontFace: FONT, fontSize: 15, color: INDIGO_LT, align: 'center',
    });
    s.addShape('line', { x: W / 2 - 1.4, y: 4.6, w: 2.8, h: 0, line: { color: '3E4A7A', width: 1 } });
    s.addText('스마트인재개발원 KDT 헬스케어 5팀 · 기업주제(라라랩스)', {
      x: 0, y: 4.85, w: W, h: 0.4, fontFace: FONT_LIGHT, fontSize: 12, color: 'A9B3D6', align: 'center',
    });

    // 팀 소개 슬라이드를 따로 두지 않고 여기로 흡수했습니다(2026.08.22).
    // 표지에 이미 같은 4인·역할이 있어, 별도 한 장에 30초를 쓸 이유가 없습니다.
    const team = [['이응균', 'PM · 기획 · 문서'], ['김건영', 'AI · DATA'], ['윤일준', '백엔드 · DB'], ['함은선', '프론트엔드']];
    const tw = 2.6, gap = 0.35, totalW = tw * 4 + gap * 3, tx0 = (W - totalW) / 2;
    team.forEach(([n, r], i) => {
      const x = tx0 + i * (tw + gap);
      s.addText(n, { x, y: 5.4, w: tw, h: 0.38, fontFace: FONT, fontSize: 14, bold: true, color: WHITE, align: 'center', margin: 0 });
      s.addText(r, { x, y: 5.78, w: tw, h: 0.35, fontFace: FONT_LIGHT, fontSize: 10.5, color: 'A9B3D6', align: 'center', margin: 0 });
    });
  }

  const outPath = path.join(__dirname, '귀기울임_최종발표_20260828.pptx');
  await pres.writeFile({ fileName: outPath });
  console.log('WROTE', outPath);
}

main().catch((e) => { console.error(e); process.exit(1); });
