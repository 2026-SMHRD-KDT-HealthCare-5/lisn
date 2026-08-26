const pptxgen = require('pptxgenjs');
const path = require('path');
const fs = require('fs');

// ⚠ 예전에는 이 값이 특정 PC 의 절대경로(C:\project\LISN 등)로 박혀
//   있었습니다. 다른 PC 에서 돌리면 그대로 깨집니다 — 스크립트 위치
//   기준 상대경로로 고쳤습니다(2026.08.25).
const REPO = path.resolve(__dirname, '..', '..');
const DESIGN = path.join(REPO, 'docs', 'design');

// 시연영상 — tools/capture/build_video.sh 의 출력.
const VIDEO_DIR = path.join(REPO, 'tools', 'capture', '.cache', 'video');
const VIDEO_PATH = path.join(VIDEO_DIR, 'lisn_demo_3min.mp4');
const VIDEO_COVER = 'data:image/png;base64,' +
  fs.readFileSync(path.join(VIDEO_DIR, 'poster.png')).toString('base64');

// ---- 디자인 토큰 — docs/design/brand.json 이 정본입니다 ----
const BRAND = JSON.parse(fs.readFileSync(path.join(REPO, 'docs', 'design', 'brand.json'), 'utf8'));
const D = BRAND.deck;
const DARK = D.darkBg;
const LIGHT = D.lightBg;
const TXT1 = D.textPrimary;
const TXT2 = D.textSecondary;
const TXT_FAINT = D.textFaint;
const TXT_MUTED = D.textMuted;
const GOLD = D.gold;
const GOLD_DARK = D.goldDark;
const GOLD_LIGHT = D.goldLight;
const LINE = D.line;
const WHITE = D.white;
const DARK_BODY = 'AEB6C2';
const DARK_MUTED = '8891A0';
const DARK_LINE = '2E3A47';
const GHOST_NUM = '242F3B';

const FONT = BRAND.font.family;
const FONT_BLACK = BRAND.font.familyBlack;
const FONT_LIGHT = BRAND.font.familyLight;
const SERIF = BRAND.font.serif;
// NanumMyeongjo 에 bold:true 를 얹으면 PowerPoint 가 합성(faux) 볼드를 만드는데, 이 과정이
// 공백 글자 폭까지 늘려서 여러 단어 제목의 단어 사이가 벌어집니다(2026.08.26 실측,
// docs/design/brand.json _serifBold 참조). 볼드가 필요하면 이 패밀리명을 직접 씁니다.
const SERIF_BOLD = BRAND.font.serifBold;

// ============================================================================
// 2026.08.26 — 전면 재구성. 팀이 받은 참고 자료(다른 두 팀의 최종발표자료·
// 최종보고서 PDF) 세 건을 대조한 결과, 같은 기관(스마트인재개발원) 소속
// 서로 무관한 팀 전부가 같은 5단 목차를 씁니다:
//   01 프로젝트 개요 · 02 팀 구성 및 역할 · 03 프로젝트 수행 절차 및 방법 ·
//   04 프로젝트 수행 경과 · 05 자체 평가 의견
// 이전 버전은 "문제와 해결 · 설계와 구현 · 성과와 확장"이라는 스타트업
// 피치 구조였습니다 — 기관 표준 양식이 아니었습니다. 전면 재구성했습니다.
//
// 기존 슬라이드 내용(아키텍처·AI 설계·위기탐지·성과지표·관제·보안·확장)은
// 전부 "04 프로젝트 수행 경과"로 그대로 옮겼습니다 — 내용 손실 없습니다.
// 새로 쓴 건 01 프로젝트 개요의 "서비스 필요성"(자체 리서치가 아니라
// docs/extracted/프로젝트_기획서_귀기울임.txt 에 이미 있던, 팀이 직접
// 인용한 통계입니다 — 발표자료에 한 번도 포팅되지 않았을 뿐입니다),
// 02 팀 구성 및 역할, 03 프로젝트 수행 절차 및 방법(일정·방법론·AI
// 검증 26회·위기탐지 설계 과정), 05 자체 평가 의견입니다.
// ============================================================================

async function main() {
  const pres = new pptxgen();
  pres.layout = 'LAYOUT_WIDE';
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

  let pageNo = 0;
  function pageNum(s, dark) {
    pageNo += 1;
    s.addText(String(pageNo).padStart(2, '0'), {
      x: W - 1.0, y: H - 0.5, w: 0.6, h: 0.32, fontFace: FONT_LIGHT, fontSize: 10,
      color: dark ? DARK_MUTED : TXT_MUTED, align: 'right',
    });
  }

  // NanumMyeongjo(Bold)의 스페이스(U+0020) 글리치 폭이 한 글자 폭에 가까울 만큼
  // 넓습니다(2026.08.26 실측 — 볼드 합성 문제가 아니라 이 폰트 자체의 스페이스
  // 메트릭입니다. 숫자만 있는 문자열엔 안 보이지만 여러 단어 제목에서 단어 사이가
  // 비정상적으로 벌어집니다). 단어는 SERIF_BOLD 로, 그 사이 공백만 FONT(Noto
  // Sans KR)로 갈라 정상 폭 스페이스를 씁니다.
  function serifTitleRuns(text, fontSize, color) {
    return text.split(' ').flatMap((w, i) => {
      const run = { text: w, options: { fontFace: SERIF_BOLD, fontSize, color } };
      if (i === 0) return [run];
      return [{ text: ' ', options: { fontFace: FONT, fontSize, color } }, run];
    });
  }

  function sectionCover(s, no, ko, kicker, subtitle) {
    s.background = { color: DARK };
    s.addText(no, {
      x: 8.6, y: -0.35, w: 4.4, h: 2.6, fontFace: SERIF_BOLD, fontSize: 150,
      color: GHOST_NUM, align: 'right', margin: 0,
    });
    s.addText(kicker, {
      x: 0.9, y: 2.62, w: 8, h: 0.4, fontFace: FONT, fontSize: 13, bold: true,
      color: GOLD_LIGHT, charSpacing: 2, margin: 0,
    });
    s.addText(serifTitleRuns(ko, 46, WHITE), {
      x: 0.87, y: 3.0, w: 10, h: 1.1, margin: 0,
    });
    s.addShape('line', { x: 0.9, y: 4.15, w: 2.3, h: 0, line: { color: GOLD, width: 1.5 } });
    s.addText(subtitle, {
      x: 0.9, y: 4.32, w: 10, h: 0.4, fontFace: FONT_LIGHT, fontSize: 13, color: DARK_BODY, margin: 0,
    });
    pageNum(s, true);
  }

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
      { text: '귀기울임', options: { fontFace: SERIF_BOLD, fontSize: 64, color: WHITE, breakLine: false } },
      { text: '   LISN', options: { fontFace: FONT, fontSize: 22, bold: true, color: GOLD_LIGHT, charSpacing: 3 } },
    ], { x: 0.85, y: 2.55, w: 11, h: 1.4, margin: 0 });

    hr(s, 0.9, 3.9, 12.0, true);

    s.addText('멀티모달 라이프로그 감정 분석 기반 맞춤형 LLM 케어 및 모니터링 시스템', {
      x: 0.9, y: 4.15, w: 10, h: 0.5, fontFace: FONT_LIGHT, fontSize: 16, color: DARK_BODY,
    });

    s.addText('최종 발표', { x: 0.9, y: 5.65, w: 3, h: 0.35, fontFace: FONT_LIGHT, fontSize: 12, color: DARK_MUTED, margin: 0 });

    const members = [['이응균', 'PM'], ['김건영', 'AI/DATA'], ['윤일준', '백엔드/DB'], ['함은선', '프론트엔드']];
    let mx = 0.9;
    const mw = 2.8;
    members.forEach(([n, r]) => {
      s.addText([
        { text: n + ' ', options: { fontFace: FONT, fontSize: 13, bold: true, color: WHITE } },
        { text: r, options: { fontFace: FONT_LIGHT, fontSize: 11, color: DARK_MUTED } },
      ], { x: mx, y: 6.0, w: mw, h: 0.35, margin: 0 });
      mx += mw;
    });
  }

  // ============================================================
  // 2. 목차 — 기관 표준 5단 구조
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

    const items = [
      ['01', '프로젝트 개요', '서비스 필요성 · 서비스 개념 · 차별성'],
      ['02', '팀 구성 및 역할', '4인 역할 분담'],
      ['03', '수행 절차 및 방법', '일정 · 개발 방법론 · AI 모델링 · 위기 탐지 설계'],
      ['04', '수행 경과', '아키텍처 · 시연 · 관제 · 보안 · 실측 지표'],
      ['05', '자체 평가 의견', '잘된 점 · 부족한 점 · 다음 단계'],
    ];
    let y = 1.55;
    const rh = 0.98;
    items.forEach(([no, t, dsc]) => {
      s.addText(no, { x: 0.62, y, w: 1.0, h: rh, fontFace: SERIF, fontSize: 26, color: GOLD, valign: 'middle', margin: 0 });
      s.addText(t, { x: 1.8, y, w: 4.6, h: rh, fontFace: FONT, fontSize: 19, bold: true, color: WHITE, valign: 'middle', margin: 0 });
      s.addText(dsc, { x: 5.9, y, w: 6.5, h: rh, fontFace: FONT_LIGHT, fontSize: 12, color: DARK_MUTED, valign: 'middle', margin: 0 });
      hr(s, 0.62, y + rh, 12.1, true);
      y += rh;
    });
    pageNum(s, true);
  }

  // ============================================================
  // [섹션 표지] 01 프로젝트 개요
  // ============================================================
  {
    const s = pres.addSlide();
    sectionCover(s, '01', '프로젝트 개요', '첫 번째', '서비스 필요성 · 서비스 개념 · 차별성');
  }

  // ============================================================
  // 서비스 필요성 — docs/extracted/프로젝트_기획서_귀기울임.txt 인용
  // (기획서에 이미 있던 통계입니다. 새로 만든 수치가 아닙니다.)
  // ============================================================
  {
    const s = bgSlide(false);
    header(s, '서비스 필요성', '프로젝트 개요', false);

    const stats = [
      ['46.3%', '심각한 스트레스 경험률(36.0%→46.3%)', '보건복지부·국립정신건강센터, 2024 국민 정신건강 지식 및 태도 조사'],
      ['40.2%', '수일간 지속되는 우울감 경험률(30.0%→40.2%)', '〃 — 정신건강 지원 서비스 인지도는 오히려 감소'],
      ['3,924명', '2024년 고독사 사망자 · 전년 대비 7.2% 증가', '보건복지부, 2024년도 고독사 발생 실태조사(2025.11)'],
      ['36.1%', '국내 1인가구 비율(804만 5천 가구) · 인간관계 만족도 51.1%', '국가데이터처, 2025 통계로 보는 1인가구'],
    ];
    const cw = 2.94, ch = 1.7, x0 = 0.62, y0 = 1.35;
    stats.forEach((t, i) => {
      const x = x0 + i * cw;
      if (i > 0) s.addShape('line', { x, y: y0 + 0.12, w: 0, h: ch - 0.3, line: { color: LINE, width: 1 } });
      s.addText(t[0], { x: x + 0.16, y: y0, w: cw - 0.32, h: 0.6, fontFace: SERIF_BOLD, fontSize: 25, color: GOLD, margin: 0 });
      s.addText(t[1], { x: x + 0.16, y: y0 + 0.62, w: cw - 0.32, h: 0.65, fontFace: FONT_LIGHT, fontSize: 10, color: TXT1, margin: 0, lineSpacingMultiple: 1.2 });
      s.addText(t[2], { x: x + 0.16, y: y0 + 1.28, w: cw - 0.3, h: 0.4, fontFace: FONT_LIGHT, fontSize: 7.5, italic: true, color: TXT_MUTED, margin: 0, lineSpacingMultiple: 1.1 });
    });
    hr(s, 0.62, y0 + ch, 12.1, false);

    s.addText('정부는 이 문제를 정책 목표로 삼고 있습니다', {
      x: 0.62, y: y0 + ch + 0.22, w: 11.4, h: 0.35, fontFace: FONT, fontSize: 14, bold: true, color: DARK, margin: 0,
    });
    s.addText('「제1차 고독사 예방 기본계획(2023~2027)」 — 2027년까지 고독사 발생률 20% 감축 목표. 2026년 보건복지부 R&D 예산은 전년 대비 12.6% 증가한 1조 652억 원으로, AI·디지털 헬스케어 투자가 지속 확대되고 있습니다.', {
      x: 0.62, y: y0 + ch + 0.6, w: 11.4, h: 0.7, fontFace: FONT_LIGHT, fontSize: 11.5, color: TXT2, lineSpacingMultiple: 1.35, margin: 0,
    });

    hr(s, 0.62, y0 + ch + 1.45, 12.1, false);
    s.addText([
      { text: '문제는 "자각"입니다. ', options: { bold: true, color: DARK } },
      { text: '정서적 이상 징후는 본인이 자각하기 어렵고, 자각하지 못하는 사용자는 앱을 열지도 않습니다. 지원 서비스 인지도가 감소하는데 스트레스·우울감 경험률은 느는 이 간극을, 사용자가 앱을 열길 기다리지 않는 구조로 좁히려 합니다.', options: { color: TXT2 } },
    ], { x: 0.62, y: y0 + ch + 1.68, w: 11.4, h: 0.9, fontFace: FONT, fontSize: 12, lineSpacingMultiple: 1.35, margin: 0 });
    pageNum(s, false);
  }

  // ============================================================
  // 서비스 개념 — 무엇을, 누구를 위해, 어떻게
  // ============================================================
  {
    const s = bgSlide(false);
    header(s, '서비스 개념', '프로젝트 개요', false);

    s.addText('스마트워치·스마트폰의 라이프로그로 정서 변화를 조기에 감지하고, 필요하면 시스템이 먼저 다가가는 정서 케어 서비스', {
      x: 0.62, y: 1.3, w: 12.1, h: 0.5, fontFace: FONT, fontSize: 15, bold: true, color: DARK, margin: 0,
    });
    s.addText('※ 정신건강 상태를 진단하거나 의학적으로 확정하지 않습니다. 행동·생체 패턴 변화를 관찰해 정서적 위험 징후의 가능성을 조기에 포착하고, 적절한 케어·상담 연계를 지원하는 모니터링 보조 도구입니다.', {
      x: 0.62, y: 1.82, w: 12.1, h: 0.4, fontFace: FONT_LIGHT, fontSize: 10, italic: true, color: TXT_MUTED, margin: 0,
    });
    hr(s, 0.62, 2.35, 12.1, false);

    const steps = [
      ['01', '자동 수집', 'Health Connect·앱 사용 시간을 앱이 자동으로 읽어 보냅니다. 사용자가 따로 입력할 것이 없습니다.'],
      ['02', '이탈 판단', '사용자 본인의 평소(14일)와 비교해 이탈을 봅니다. 감정을 분류하는 것이 아니라, 그 사람 기준의 변화를 봅니다.'],
      ['03', '선제 접촉', '콘텐츠 추천에서 그치지 않고, 변화가 지속되면 시스템이 먼저 말을 겁니다. 감시가 아닌 관심으로 접근합니다.'],
    ];
    const cw = 3.87, gap = 0.24, x0 = 0.62, cy = 2.75;
    steps.forEach(([no, h, b], i) => {
      const x = x0 + i * (cw + gap);
      if (i > 0) {
        s.addShape('line', { x: x - gap / 2, y: cy, w: 0, h: 3.0, line: { color: LINE, width: 1 } });
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
  // 차별성
  // ============================================================
  {
    const s = bgSlide(true);
    header(s, '앱을 열기 전에 먼저 닿는 구조', '프로젝트 개요 · 차별성', true);

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
    s.addText([
      { text: '연속 이탈 3일 → 조건 6개 검사 → 첫 발화 생성 → 세션 생성 → FCM 푸시 · 홈 카드 · ', options: { breakLine: true } },
      { text: '배너로 먼저 말을 겁니다.' },
    ], {
      x: 6.9, y: 2.62, w: 5.83, h: 0.7, fontFace: FONT_LIGHT, fontSize: 11.5, color: DARK_BODY, margin: 0, lineSpacingMultiple: 1.3,
    });

    s.addText("'감시'가 아닌 '관심'으로 접근", {
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
  // [섹션 표지] 02 팀 구성 및 역할
  // ============================================================
  {
    const s = pres.addSlide();
    sectionCover(s, '02', '팀 구성 및 역할', '두 번째', '4인 · 6주 · 기업주제(라라랩스)');
  }

  // ============================================================
  // 팀 구성 및 역할
  // ============================================================
  {
    const s = bgSlide(false);
    header(s, '4인, 각자의 영역에서 전체를 관통', '팀 구성 및 역할', false);

    const roles = [
      ['이응균', 'PM · 기획 · 문서', '요구사항정의서·데이터베이스요구사항분석서 등 5종 산출물 총괄. 기업 브리프 대조·발표 방어 자료 작성.'],
      ['김건영', 'AI · 모델링', '개인 기준선 이탈 탐지 모델링. 26회 검증 시도 끝에 학습된 집계 채택. 위기 판정 프롬프트·평가셋 설계.'],
      ['윤일준', '백엔드 · DB', 'FastAPI 34개 엔드포인트, PostgreSQL 9테이블 스키마 정본 관리. Health Connect 연동·클라우드 배포(NCP).'],
      ['함은선', '프론트엔드 · UI', 'Flutter 앱 13개 화면·관리자 관제 웹 2개 화면. 화면설계서 기준 전체 UI 구현 및 API 연동.'],
    ];
    let y = 1.35;
    const rh = 1.32;
    hr(s, 0.62, y, 12.1, false);
    roles.forEach(([n, role, detail]) => {
      s.addText(n, { x: 0.62, y, w: 1.7, h: rh, fontFace: SERIF, fontSize: 20, color: GOLD, valign: 'middle', margin: 0 });
      s.addText(role, { x: 2.5, y, w: 3.6, h: rh, fontFace: FONT, fontSize: 13, bold: true, color: DARK, valign: 'middle', margin: 0, lineSpacingMultiple: 1.2 });
      s.addText(detail, { x: 6.3, y, w: 6.2, h: rh, fontFace: FONT_LIGHT, fontSize: 11, color: TXT2, valign: 'middle', margin: 0, lineSpacingMultiple: 1.3 });
      hr(s, 0.62, y + rh, 12.1, false);
      y += rh;
    });

    s.addText('전원이 교내 공용 PostgreSQL 인스턴스에 접속해 동일한 스키마로 개발 — 통합 테스트 시점의 스키마 불일치를 방지했습니다.', {
      x: 0.62, y: y + 0.2, w: 12.1, h: 0.4, fontFace: FONT_LIGHT, fontSize: 10.5, italic: true, color: TXT_MUTED, margin: 0,
    });
    pageNum(s, false);
  }

  // ============================================================
  // [섹션 표지] 03 프로젝트 수행 절차 및 방법
  // ============================================================
  {
    const s = pres.addSlide();
    sectionCover(s, '03', '수행 절차 및 방법', '세 번째', '일정 · 개발 방법론 · AI 모델링 · 위기 탐지 설계');
  }

  // ============================================================
  // 프로젝트 일정
  // ============================================================
  {
    const s = bgSlide(false);
    header(s, '6주 일정 (2026.07.17 ~ 08.28)', '수행 절차 및 방법', false);

    const weeks = [
      ['1주', '요구사항정의', '기업 브리프 대조 · DB 스키마 설계 · 산출물 5종 초안'],
      ['2~3주', '핵심 기능 구현', 'Health Connect 연동 · 서버 API · 위기 탐지 1차(키워드)'],
      ['4주', 'AI 모델링 · 문서 개정', '개인 기준선 이탈 탐지 26회 검증 · 산출물 개정 마감(8/11)'],
      ['5주', '통합·클라우드 배포', 'NCP 배포 · 회귀 테스트 348건 · 위기 판정 2단계 완성'],
      ['6주', '실측·발표 준비', '평가셋 211건 채점 · 시연영상 제작 · 최종발표자료'],
    ];
    let y = 1.4;
    const rh = 0.98;
    hr(s, 0.62, y, 12.1, false);
    weeks.forEach(([w, h, b]) => {
      s.addText(w, { x: 0.62, y, w: 1.3, h: rh, fontFace: SERIF, fontSize: 16, color: GOLD, valign: 'middle', margin: 0 });
      s.addText(h, { x: 2.1, y, w: 4.3, h: rh, fontFace: FONT, fontSize: 13, bold: true, color: DARK, valign: 'middle', margin: 0 });
      s.addText(b, { x: 6.5, y, w: 6.0, h: rh, fontFace: FONT_LIGHT, fontSize: 10.5, color: TXT2, valign: 'middle', margin: 0, lineSpacingMultiple: 1.25 });
      hr(s, 0.62, y + rh, 12.1, false);
      y += rh;
    });
    s.addText('⚠ 8/11 문서 개정 마감 이후에도 8/24~8/25에 학습 모델 도입·앱 사용 로그 구현이 이어졌습니다 — 마감 이후의 개선도 실제 서비스에 반영돼 있습니다.', {
      x: 0.62, y: y + 0.15, w: 12.1, h: 0.4, fontFace: FONT_LIGHT, fontSize: 9.5, italic: true, color: TXT_MUTED, margin: 0,
    });
    pageNum(s, false);
  }

  // ============================================================
  // 개발 방법론
  // ============================================================
  {
    const s = bgSlide(false);
    header(s, '개발 방법론', '수행 절차 및 방법', false);

    const methods = [
      ['스키마 정본 하나', 'db/schema.sql 이 유일한 정본입니다. 모델은 이 DDL의 매핑일 뿐이고, Base.metadata.create_all()·alembic 을 쓰지 않습니다 — 정본이 둘이면 문서와 코드가 반드시 갈립니다.'],
      ['문서 검사기 4종', '같은 수치가 문서마다 다르게 적히는 것을 사람이 세지 않고 기계가 대조합니다(check_docs·check_numbers·check_dup·check_screens). 실제로 API 30→33건, 테이블 8→9개가 이렇게 잡혔습니다.'],
      ['브랜치 · 병합 규율', '팀원별 브랜치(함은선·backend·docs) → main. 산출물 HWP·PPTX는 바이너리라 브랜치가 갈리면 병합이 안 돼, 문서 작업은 main에서 바로 커밋·푸시합니다.'],
      ['화면설계서가 정본', '앱이 화면설계서를 참조하지 않고 만들어진 결함을 8/02 전수 대조로 6건 발견·수정했습니다. 어긋나면 앱을 고치는 쪽입니다.'],
    ];
    let y = 1.35;
    const rh = 1.28;
    hr(s, 0.62, y, 12.1, false);
    methods.forEach(([h, b]) => {
      s.addText(h, { x: 0.62, y, w: 3.3, h: rh, fontFace: FONT, fontSize: 13.5, bold: true, color: GOLD_DARK, valign: 'middle', margin: 0 });
      s.addText(b, { x: 4.15, y, w: 8.35, h: rh, fontFace: FONT_LIGHT, fontSize: 11, color: TXT2, valign: 'middle', margin: 0, lineSpacingMultiple: 1.3 });
      hr(s, 0.62, y + rh, 12.1, false);
      y += rh;
    });
    pageNum(s, false);
  }

  // ============================================================
  // AI 모델링 과정 — 26회 검증
  // ============================================================
  {
    const s = bgSlide(false);
    header(s, 'AI 모델링 과정', '수행 절차 및 방법', false);

    s.addText('개인 기준선 이탈 지표를 하나의 점수로 합치는 방법을 정하기까지, 여섯 각도로 스물여섯 차례 검증했습니다.', {
      x: 0.62, y: 1.32, w: 12.1, h: 0.5, fontFace: FONT, fontSize: 13.5, color: DARK, margin: 0, lineSpacingMultiple: 1.3,
    });
    hr(s, 0.62, 1.9, 12.1, false);

    const rows = [
      ['채택', '학습된 집계(로지스틱 회귀)', 'AUC 0.609', GOLD_DARK],
      ['비교', 'Isolation Forest(전역 · 개인별)', '0.473 · 0.494', TXT_FAINT],
      ['비교', 'ElasticNet · 상호작용 모델', '+0.005(ns) · −0.034', TXT_FAINT],
      ['비교', '추세 검정 → 3일 앞 예측', '전부 0.5 미만', TXT_FAINT],
      ['기준', '현재 규칙(상위 3개 평균 ÷ 4.0)', '0.491', TXT_MUTED],
    ];
    let y = 2.1;
    const rh2 = 0.62;
    rows.forEach(([tag, h, v, c]) => {
      s.addText(tag, { x: 0.62, y, w: 1.0, h: rh2, fontFace: FONT, fontSize: 10.5, bold: true, color: c, valign: 'middle', margin: 0 });
      s.addText(h, { x: 1.7, y, w: 7.0, h: rh2, fontFace: FONT_LIGHT, fontSize: 12, color: TXT1, valign: 'middle', margin: 0 });
      // ⚠ SERIF(NanumMyeongjo) 로 공백·가운뎃점이 섞인 문자열을 그리면
      //   그 문자들이 깨진 네모(tofu)로 나옵니다(2026.08.26 실측 — "0.473
      //   □·□0.494" 처럼). 숫자 하나만 있는 다른 자리(성과 지표 타일 등)는
      //   문제없지만, 여기처럼 공백·가운뎃점이 낀 값은 FONT(Noto Sans KR)
      //   로 그립니다.
      s.addText(v, { x: 8.9, y, w: 3.3, h: rh2, fontFace: FONT, fontSize: 14, bold: true, color: c, valign: 'middle', margin: 0 });
      hr(s, 0.62, y + rh2, 12.1, false);
      y += rh2;
    });

    hr(s, 0.62, y + 0.15, 12.1, false);
    s.addText('「더 해볼 게 없어서」가 아니라 「재봤더니 근거가 없어서」 유지합니다.', {
      x: 0.62, y: y + 0.35, w: 11.4, h: 0.4, fontFace: FONT, fontSize: 12.5, bold: true, color: DARK, margin: 0,
    });
    s.addText('참가자 분할 GroupKFold(5) + 중첩 교차검증 · 부트스트랩 2000회 · LifeSnaps 62명 4086표본. 3일 앞 예측이 안 된다는 것도 중요한 발견입니다 — 선제 접촉은 "곧 나빠질 사람을 미리 찾는다"가 아니라 "지금 평소와 다른 사람에게 먼저 말을 건다"입니다.', {
      x: 0.62, y: y + 0.78, w: 11.4, h: 0.7, fontFace: FONT_LIGHT, fontSize: 10.5, color: TXT2, lineSpacingMultiple: 1.3, margin: 0,
    });
    pageNum(s, false);
  }

  // ============================================================
  // 위기 탐지 설계 과정
  // ============================================================
  {
    const s = bgSlide(false);
    header(s, '위기 탐지 설계', '수행 절차 및 방법', false);

    const design = [
      ['설계 결정 1', '키워드 규칙은 서버 안에', 'AI 서버·외부 LLM이 죽어도 위기 탐지가 멈추면 안 됩니다(NFR-DV-003). 로컬 함수라 공급자와 무관하게 동작합니다.'],
      ['설계 결정 2', '판정·응답 생성은 병렬로', '순차 호출이면 왕복이 두 번 쌓여 3초 응답 요건을 못 지킵니다. asyncio.gather로 동시에 보냅니다.'],
      ['설계 결정 3', '스트리밍은 쓰지 않는다', 'CRITICAL로 확정되면 만들어 둔 응답을 버려야 하는데, 스트리밍으로 이미 흘려보낸 글자는 되돌릴 수 없습니다.'],
    ];
    let y = 1.35;
    const rh = 1.55;
    design.forEach(([tag, h, b], i) => {
      if (i > 0) hr(s, 0.62, y, 12.1, false);
      s.addText(tag, { x: 0.62, y: y + 0.12, w: 1.9, h: 0.35, fontFace: FONT, fontSize: 11, bold: true, color: GOLD_DARK, margin: 0 });
      s.addText(h, { x: 2.6, y: y + 0.08, w: 4.4, h: 0.5, fontFace: FONT, fontSize: 13.5, bold: true, color: DARK, margin: 0, lineSpacingMultiple: 1.15 });
      s.addText(b, { x: 7.15, y, w: 5.35, h: rh, fontFace: FONT_LIGHT, fontSize: 11, color: TXT2, valign: 'middle', margin: 0, lineSpacingMultiple: 1.3 });
      y += rh;
    });
    hr(s, 0.62, y, 12.1, false);

    s.addText('그 결과 — 재현율 0.081 → 0.946', {
      x: 0.62, y: y + 0.2, w: 11.4, h: 0.4, fontFace: FONT, fontSize: 13, bold: true, color: DARK, margin: 0,
    });
    s.addText('키워드 단독 재현율 0.081(직접 표현만 잡음) → 문맥 판정 결합 후 0.946. 정신건강 서비스라 경고색은 쓰지 않고, 데이터가 3일 미만이면 422로 끊어 편차 0을 "정상"으로 적재하지 않습니다.', {
      x: 0.62, y: y + 0.6, w: 11.4, h: 0.6, fontFace: FONT_LIGHT, fontSize: 10.5, color: TXT2, lineSpacingMultiple: 1.3, margin: 0,
    });
    pageNum(s, false);
  }

  // ============================================================
  // [섹션 표지] 04 프로젝트 수행 경과
  // ============================================================
  {
    const s = pres.addSlide();
    sectionCover(s, '04', '수행 경과', '네 번째', '아키텍처 · 시연 · 관제 · 보안 · 실측 지표');
  }

  // ============================================================
  // 서버 분리 (아키텍처)
  // ============================================================
  {
    const s = bgSlide(false);
    header(s, '서버 분리', '수행 경과 · 아키텍처', false);

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
    [[3.67, 4.9, '걸음·수면·심박·앱 사용 push'], [8.52, 9.75, '내부 통신']].forEach(([ax1, ax2, label]) => {
      s.addShape('line', { x: ax1, y: boxY + boxH / 2, w: ax2 - ax1, h: 0, line: { color: GOLD, width: 1.5 } });
      s.addText(label, { x: ax1 - 0.3, y: boxY - 0.3, w: (ax2 - ax1) + 0.6, h: 0.28, fontFace: FONT_LIGHT, fontSize: 8.5, color: TXT_MUTED, align: 'center', margin: 0 });
    });
    s.addText('☁ 클라우드 배포: NCP + Docker Compose · HTTPS(Let\u2019s Encrypt) · FCM 실키 적용', {
      x: 0.62, y: 3.08, w: 12.1, h: 0.24, fontFace: FONT_LIGHT, fontSize: 9, color: GOLD_DARK, align: 'right', margin: 0,
    });
    hr(s, 0.62, 3.35, 12.1, false);
    s.addText([
      { text: '위기 키워드 필터는 비즈니스 서버 안에 둡니다.  ', options: { bold: true, color: DARK } },
      { text: 'AI 서버가 죽어도 탐지가 멈추면 안 되기 때문입니다.', options: { color: TXT2 } },
    ], { x: 0.62, y: 3.55, w: 12.1, h: 0.4, fontFace: FONT, fontSize: 13, margin: 0 });

    s.addText('앱이 먼저 보내고, 서버는 끌어오지 않습니다', {
      x: 0.62, y: 4.2, w: 11.4, h: 0.35, fontFace: FONT, fontSize: 14, bold: true, color: DARK, margin: 0,
    });
    hr(s, 0.62, 4.62, 12.1, false);

    const cards = [
      ['자동 수집', 'Health Connect · 앱 사용 로그를 앱이 직접 읽어 push / 닫혀 있어도 WorkManager가 15분마다 백그라운드로 전송'],
      ['개인정보 최소화', '앱 사용 지표는 패키지명 없이 화면 시간 · 전환 횟수 등 집계값만 전달'],
    ];
    const cardY0 = 4.85, cardH = 1.05;
    cards.forEach(([h, b], i) => {
      const y = cardY0 + i * (cardH + 0.1);
      s.addText(h, { x: 0.62, y, w: 7.3, h: 0.3, fontFace: FONT, fontSize: 12.5, bold: true, color: GOLD_DARK, margin: 0 });
      s.addText(b, { x: 0.62, y: y + 0.32, w: 7.3, h: 0.7, fontFace: FONT_LIGHT, fontSize: 10.5, color: TXT2, margin: 0, lineSpacingMultiple: 1.25 });
    });

    const imgH = 1.95, imgW = imgH * (530 / 755), imgX = 9.25, imgY = 4.78;
    s.addImage({
      path: img('DEMO_VIDEO_LIFELOG_01'), x: imgX, y: imgY, w: imgW, h: imgH,
      shadow: { type: 'outer', color: '1A1F2B', opacity: 0.35, blur: 10, offset: 4, angle: 90 },
    });
    s.addText('Health Connect로 모은 심박 · 수면 데이터가 실제 화면에 그대로 보입니다.', {
      x: imgX - 0.55, y: imgY + imgH + 0.14, w: imgW + 1.1, h: 0.55, fontFace: FONT_LIGHT, fontSize: 8, color: TXT_MUTED, align: 'center', margin: 0, lineSpacingMultiple: 1.2,
    });
    pageNum(s, false);
  }

  // ============================================================
  // AI 설계 결과
  // ============================================================
  {
    const s = bgSlide(false);
    header(s, '감정 분류 대신 개인 기준선 이탈 탐지', '수행 경과 · AI', false);

    const steps = [
      ['1', '학습된 집계로 교체', '「상위 3개 평균 ÷ 4.0」이라는 임의 집계식을 입력은 늘리지 않으며 로지스틱 회귀로 교체'],
      ['2', 'AUC 0.609 달성', '기존 규칙 0.491 → 학습된 집계 0.609. 이득 +0.115[+0.056,+0.176]. 62명·4086표본, 참가자 분할 + 중첩 교차검증'],
      ['3', '다른 방법도 비교', 'Isolation Forest(전역 0.473·개인별 0.494) 등 6종을 같은 조건에서 유의미한 결과 도출'],
    ];
    let y = 1.35;
    const rh = 0.72;
    steps.forEach(([no, h, b]) => {
      s.addText(no, { x: 0.62, y, w: 0.55, h: rh, fontFace: SERIF, fontSize: 20, color: GOLD, valign: 'middle', margin: 0 });
      s.addText(h, { x: 1.25, y, w: 3.6, h: rh, fontFace: FONT, fontSize: 14, bold: true, color: DARK, valign: 'middle', margin: 0 });
      s.addText(b, { x: 5.0, y, w: 7.7, h: rh, fontFace: FONT_LIGHT, fontSize: 11.5, color: TXT2, valign: 'middle', margin: 0, lineSpacingMultiple: 1.3 });
      hr(s, 0.62, y + rh, 12.1, false);
      y += rh;
    });

    y += 0.25;
    const gh = 2.1;
    s.addShape('line', { x: 0.62, y, w: 0, h: gh, line: { color: GOLD, width: 4 } });
    s.addText('감정을 분류하는 게 아닙니다', {
      x: 0.9, y, w: 7.0, h: 0.4, fontFace: FONT, fontSize: 15, bold: true, color: DARK, margin: 0,
    });
    s.addText('바뀐 것은 지표를 합치는 방식뿐입니다. 개인 기준선 대비 이탈 지표 7개를 하나의 점수로 합치는 방법을 데이터로 골랐을 뿐이고, 감정 코드는 여전히 이탈 정도를 표시하는 산출값입니다. model_version 이 hybrid- 로 시작하면 이 집계가 관여한 것이고, rule- 이면 기존 규칙 그대로입니다.', {
      x: 0.9, y: y + 0.42, w: 7.0, h: 1.15, fontFace: FONT_LIGHT, fontSize: 11.5, color: TXT2, lineSpacingMultiple: 1.35, margin: 0,
    });
    s.addText('※ 같은 데이터로 70%를 보고한 선행연구를 재현하니, 그 지표의 기준선이 66.7%였습니다 — ai/train/eval_replicate_paper.py', {
      x: 0.9, y: y + 1.62, w: 7.0, h: 0.3, fontFace: FONT_LIGHT, fontSize: 9, italic: true, color: TXT_MUTED, margin: 0,
    });

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
  // 위기 탐지 2단계 결과
  // ============================================================
  {
    const s = bgSlide(false);
    header(s, '위기 탐지 2단계 구조', '수행 경과 · AI', false);

    const stages = [
      ['1차', '키워드 규칙', '독립적인 위기 탐지로, 외부 API에 문제가 발생하여도 정상적으로 기능합니다', '단독 재현율', '0.081'],
      ['2차', 'LLM 문맥 판정', '문장 맥락까지 읽어 더 정밀하게 판정합니다', '최종 재현율', '0.946'],
    ];
    const cw = 5.87, x0 = 0.62, y0 = 1.35;
    stages.forEach(([no, h, b, statL, statV], i) => {
      const x = x0 + i * (cw + 0.36);
      if (i > 0) {
        s.addShape('line', { x: x - 0.18, y: y0, w: 0, h: 2.55, line: { color: LINE, width: 1 } });
        s.addShape(pres.ShapeType.rightArrow, {
          x: x - 0.18 - 0.095, y: y0 + 2.115, w: 0.19, h: 0.17,
          fill: { color: GOLD }, line: { type: 'none' },
        });
      }
      s.addText(no, { x, y: y0, w: 1.2, h: 0.35, fontFace: FONT, fontSize: 12.5, bold: true, color: GOLD_DARK, margin: 0 });
      s.addText(h, { x, y: y0 + 0.35, w: cw, h: 0.5, fontFace: FONT, fontSize: 19, bold: true, color: DARK, margin: 0 });
      s.addText(b, { x, y: y0 + 0.95, w: cw - 0.2, h: 0.6, fontFace: FONT_LIGHT, fontSize: 12, color: TXT2, lineSpacingMultiple: 1.3, margin: 0 });
      s.addText(statL, { x, y: y0 + 1.62, w: cw, h: 0.3, fontFace: FONT_LIGHT, fontSize: 10.5, color: TXT_MUTED, margin: 0 });
      s.addText(statV, { x, y: y0 + 1.9, w: cw, h: 0.6, fontFace: SERIF_BOLD, fontSize: 30, color: GOLD, margin: 0 });
    });

    hr(s, 0.62, 4.15, 12.1, false);
    s.addText('위기를 놓치지 않기 위한 노력', {
      x: 0.62, y: 4.35, w: 11.4, h: 0.35, fontFace: FONT, fontSize: 14.5, bold: true, color: DARK, margin: 0,
    });
    hr(s, 0.62, 4.78, 12.1, false);

    const cards = [
      ['위로보다 안전', 'CRITICAL이면 답변 대신 상담 연결 화면을 보여줍니다. 판정과 응답 생성을 병렬로 처리하되 스트리밍은 쓰지 않아, 판정 전에 흘려보낸 글자가 없습니다.'],
      ['경고색 대신 배치', '빨강 · 주황은 불안을 키워 회피를 부릅니다. 주목도는 색이 아니라 화면 배치로 만들었습니다.'],
      ['모른다 ≠ 괜찮다', '데이터가 3일 미만이면 422로 끊습니다. 편차 0을 정상으로 적재하면 위험을 놓칩니다.'],
    ];
    const ccw = 3.9, ccx0 = 0.62, cardY = 4.98;
    cards.forEach(([h, b], i) => {
      const x = ccx0 + i * (ccw + 0.03);
      if (i > 0) s.addShape('line', { x: x - 0.03, y: cardY, w: 0, h: 1.55, line: { color: LINE, width: 1 } });
      s.addText(h, { x: x + 0.12, y: cardY, w: ccw - 0.2, h: 0.32, fontFace: FONT, fontSize: 12.5, bold: true, color: GOLD_DARK, margin: 0 });
      s.addText(b, { x: x + 0.12, y: cardY + 0.36, w: ccw - 0.28, h: 1.2, fontFace: FONT_LIGHT, fontSize: 10.5, color: TXT2, margin: 0, lineSpacingMultiple: 1.28 });
    });
    pageNum(s, false);
  }

  // ============================================================
  // 3분 시연 영상
  // ============================================================
  {
    const s = bgSlide(false);
    header(s, '3분으로 보는 귀기울임', '수행 경과 · 시연', false);
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
  // 관리자 관제 웹
  // ============================================================
  {
    const s = bgSlide(false);
    header(s, '위험한 사람부터 보이는 관제 화면', '수행 경과 · 관제', false);

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
  // 보안 설계
  // ============================================================
  {
    const s = bgSlide(false);
    header(s, '"전부 암호화" 대신 위험도 기반', '수행 경과 · 보안', false);

    s.addText('데이터가 민감할수록 보호가 강해집니다. 테이블 9곳에 같은 방식을 쓰지 않습니다.', {
      x: 0.62, y: 1.35, w: 7.0, h: 0.4, fontFace: FONT, fontSize: 12.5, bold: true, color: DARK, margin: 0,
    });

    const tiers = [
      { w: 3.5, fill: GOLD_DARK, transparency: 0, textColor: WHITE, subColor: 'F7EDD9',
        label: '비밀번호 · 대화', detail: 'bcrypt 비가역 해시 · 저장 전 PII 마스킹' },
      { w: 5.25, fill: GOLD, transparency: 55, textColor: DARK, subColor: DARK,
        label: '연락처', detail: 'AES-256-GCM 컬럼 단위 암호화 (USERS.phone)' },
      { w: 7.0, fill: GOLD, transparency: 85, textColor: DARK, subColor: DARK,
        label: '라이프로그 측정치 · 전체 테이블', detail: 'HTTPS/TLS 전송 구간 보호 · UUID v4(9곳 전부, 열거 공격 방지) · 클라우드 배포 시 DB 볼륨 암호화' },
    ];
    const pyCenterX = 0.62 + 7.0 / 2, bh = 0.78, step = 0.92;
    let ty = 1.85;
    tiers.forEach((t) => {
      const tx = pyCenterX - t.w / 2;
      s.addShape('roundRect', { x: tx, y: ty, w: t.w, h: bh, rectRadius: 0.08, fill: { color: t.fill, transparency: t.transparency }, line: { type: 'none' } });
      s.addText(t.label, { x: tx + 0.22, y: ty + 0.1, w: t.w - 0.44, h: 0.3, fontFace: FONT, fontSize: 12.5, bold: true, color: t.textColor, margin: 0 });
      s.addText(t.detail, { x: tx + 0.22, y: ty + 0.4, w: t.w - 0.44, h: 0.34, fontFace: FONT_LIGHT, fontSize: 9, color: t.subColor, margin: 0, lineSpacingMultiple: 1.15 });
      ty += step;
    });
    const pyramidBottom = ty - step + bh;

    const rightH = pyramidBottom - 1.35;
    s.addShape('line', { x: 7.9, y: 1.35, w: 0, h: rightH, line: { color: GOLD, width: 1.5 } });
    s.addText([
      { text: '왜 전 컬럼 암호화를 하지 않았나', options: { fontFace: FONT, fontSize: 13, bold: true, color: DARK, breakLine: true, paraSpaceAfter: 12 } },
      { text: '라이프로그 측정치를 컬럼 암호화하면 서비스가 동작하지 않습니다. 기간별 집계와 복합 인덱스가 핵심 동작인데, 암호화하면 범위 조회 불가.', options: { color: TXT2, breakLine: true, paraSpaceAfter: 12 } },
      { text: '유출 시 즉각적 2차 피해에 취약한 항목(연락처)만 컬럼 암호화하고, 측정치는 전송 구간 보호와 접근통제로 지킵니다.', options: { color: TXT2 } },
    ], {
      x: 8.15, y: 1.35, w: 4.55, h: rightH,
      fontFace: FONT_LIGHT, fontSize: 10.5, valign: 'middle', lineSpacingMultiple: 1.3, margin: 0,
    });

    const boxY = pyramidBottom + 0.35;
    hr(s, 0.62, boxY, 12.1, false);
    s.addText([
      { text: '"보안 요구를 기능 제약과 함께 설계"', options: { bold: true, color: DARK } },
      { text: '했습니다. 마스킹은 저장 전에 하며, 원문은 어디에도 남지 않고, 외부 LLM에도 마스킹된 텍스트만 전송됩니다.', options: { color: TXT2 } },
    ], { x: 0.62, y: boxY + 0.22, w: 12.1, h: 0.9, fontFace: FONT, fontSize: 12, lineSpacingMultiple: 1.35, margin: 0 });
    pageNum(s, false);
  }

  // ============================================================
  // 실측 성과 지표
  // ============================================================
  {
    const s = bgSlide(true);
    header(s, '실측으로 증명된 수치', '수행 경과 · 성과', true);

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
      s.addText(t[0], { x: x + 0.16, y, w: cw - 0.32, h: 0.65, fontFace: SERIF_BOLD, fontSize: 26, color: WHITE, margin: 0 });
      s.addText(t[1], { x: x + 0.16, y: y + 0.68, w: cw - 0.32, h: 0.75, fontFace: FONT_LIGHT, fontSize: 9.5, color: DARK_MUTED, margin: 0, lineSpacingMultiple: 1.25 });
    });
    const tilesBottom = y0 + ch * 2;
    hr(s, 0.62, tilesBottom, 12.1, true);

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
  // [섹션 표지] 05 자체 평가 의견
  // ============================================================
  {
    const s = pres.addSlide();
    sectionCover(s, '05', '자체 평가 의견', '다섯 번째', '잘된 점 · 부족한 점 · 다음 단계');
  }

  // ============================================================
  // 자체 평가 의견
  // ============================================================
  {
    const s = bgSlide(false);
    header(s, '잘된 점과 부족한 점', '자체 평가 의견', false);

    s.addText('잘된 점', { x: 0.62, y: 1.35, w: 5.8, h: 0.35, fontFace: FONT, fontSize: 14, bold: true, color: GOLD_DARK, margin: 0 });
    hr(s, 0.62, 1.78, 5.8, false);
    const good = [
      ['검증 없이 채택 안 함', '학습 모델 채택에 26회, 위기 판정 개선에 4회차 재측정. "동작한다"가 아니라 "재봤더니 낫다"만 반영했습니다.'],
      ['문서-구현 갭 스스로 해소', '요구사항 갭 9건 전부 해소. 마지막 갭(채팅 위기가 관제에 안 뜨던 것)은 발표 준비 중 직접 찾았습니다.'],
      ['정본을 하나로', '색·글꼴·스키마 값을 여러 곳에 반복 적지 않아, 나중에 값이 갈리는 사고 자체를 구조로 막았습니다.'],
    ];
    let gy = 2.0;
    good.forEach(([h, b]) => {
      s.addText(h, { x: 0.62, y: gy, w: 5.8, h: 0.35, fontFace: FONT, fontSize: 11.5, bold: true, color: DARK, margin: 0 });
      s.addText(b, { x: 0.62, y: gy + 0.35, w: 5.8, h: 0.85, fontFace: FONT_LIGHT, fontSize: 10, color: TXT2, margin: 0, lineSpacingMultiple: 1.25 });
      gy += 1.35;
    });

    s.addShape('line', { x: 6.75, y: 1.35, w: 0, h: gy - 1.5, line: { color: LINE, width: 1 } });

    s.addText('부족한 점', { x: 7.05, y: 1.35, w: 5.6, h: 0.35, fontFace: FONT, fontSize: 14, bold: true, color: TXT_FAINT, margin: 0 });
    hr(s, 7.05, 1.78, 5.6, false);
    const bad = [
      ['실기기 검증 남음', 'Health Connect·FCM 모두 에뮬레이터·자격증명 초기화까지만 확인했습니다. 실기기 하나면 반나절 안에 끝나는 검증인데, 확보하지 못했습니다.'],
      ['평가셋 holdout 없음', '재현율 0.946은 이 211건 안에서의 값입니다. 라벨링에 관여하지 않은 사람이 새로 쓴 문장으로 재검증하는 게 다음 단계입니다.'],
      ['AI 모델 표본 수 적음', '이 분야 표본 중앙값이 60.5명인데 저희는 62명입니다. 42편 중 외부 검증은 1편뿐이라는 것도 함께 봐야 할 맥락입니다.'],
    ];
    let by = 2.0;
    bad.forEach(([h, b]) => {
      s.addText(h, { x: 7.05, y: by, w: 5.6, h: 0.35, fontFace: FONT, fontSize: 11.5, bold: true, color: DARK, margin: 0 });
      s.addText(b, { x: 7.05, y: by + 0.35, w: 5.6, h: 0.85, fontFace: FONT_LIGHT, fontSize: 10, color: TXT2, margin: 0, lineSpacingMultiple: 1.25 });
      by += 1.35;
    });

    hr(s, 0.62, Math.max(gy, by) + 0.05, 12.1, false);
    s.addText('부족한 점을 먼저 찾아 적었다는 것 자체가, "확인되지 않은 걸 확인됐다고 말하지 않는다"는 이 프로젝트의 원칙이 발표자료 작성에도 그대로 적용됐다는 뜻입니다.', {
      x: 0.62, y: Math.max(gy, by) + 0.25, w: 12.1, h: 0.6, fontFace: FONT_LIGHT, fontSize: 11, italic: true, color: TXT_MUTED, lineSpacingMultiple: 1.3, margin: 0,
    });
    pageNum(s, false);
  }

  // ============================================================
  // 확장 가능한 부분 (다음 단계)
  // ============================================================
  {
    const s = bgSlide(false);
    header(s, '확장 가능한 부분', '자체 평가 의견 · 다음 단계', false);

    const rows = [
      ['실기기 검증', '검증 예정', 'Health Connect·앱 사용 로그 모두 에뮬레이터 워커 동작까지 확인했고, 실기기만 확보되면 바로 검증합니다.'],
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
  // 감사합니다
  // ============================================================
  {
    const s = bgSlide(true);
    s.addText('귀기울임', {
      x: 0, y: 2.7, w: W, h: 1.0, fontFace: SERIF_BOLD, fontSize: 52, color: WHITE, align: 'center', margin: 0,
    });
    s.addText('감사합니다', {
      x: 0, y: 3.65, w: W, h: 0.6, fontFace: FONT, fontSize: 20, color: DARK_BODY, align: 'center', margin: 0,
    });
    s.addShape('line', { x: W / 2 - 1.2, y: 4.5, w: 2.4, h: 0, line: { color: GOLD, width: 1.5 } });
    s.addText('귀기울임 — 먼저 다가가는 정서 케어', {
      x: 0, y: 4.7, w: W, h: 0.4, fontFace: FONT_LIGHT, fontSize: 13, color: DARK_MUTED, align: 'center', margin: 0,
    });

    hr(s, W / 2 - 6, 5.75, 12, true);
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
