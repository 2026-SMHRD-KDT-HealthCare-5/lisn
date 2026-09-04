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
// 서로 무관한 팀 전부가 같은 5단 목차를 씁니다(팀 구성 순서는 팀마다 다름):
//   01 프로젝트 개요 · 02 프로젝트 수행 절차 및 방법 · 03 프로젝트 수행 경과 ·
//   04 자체 평가 의견 · 05 팀 구성 및 역할
// 이전 버전은 "문제와 해결 · 설계와 구현 · 성과와 확장"이라는 스타트업
// 피치 구조였습니다 — 기관 표준 양식이 아니었습니다. 전면 재구성했습니다.
//
// 기존 슬라이드 내용(아키텍처·AI 설계·위기탐지·성과지표·관제·보안·확장)은
// 전부 "02 프로젝트 수행 경과"로 그대로 옮겼습니다 — 내용 손실 없습니다.
// 새로 쓴 건 01 프로젝트 개요의 "서비스 필요성"(자체 리서치가 아니라
// docs/extracted/프로젝트_기획서_귀기울임.txt 에 이미 있던, 팀이 직접
// 인용한 통계입니다 — 발표자료에 한 번도 포팅되지 않았을 뿐입니다),
// 팀 구성 및 역할, 02 프로젝트 수행 절차 및 방법(일정·방법론·AI
// 검증 26회·위기탐지 설계 과정), 04 자체 평가 의견입니다.
//
// 2026.08.26 저녁 — PM 지시로 "팀 구성 및 역할"을 02번(둘째)에서
// 05번(다섯째, 감사합니다 바로 앞)으로 옮겼습니다. 섹션 번호·목차·
// kicker 순서 표시("두 번째" 등)만 갱신했고, 다른 4개 섹션 순서와
// 내용은 그대로입니다.
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

  // PM 이 PowerPoint 에서 직접 줄바꿈(Enter)을 넣어둔 자리를 재생성 후에도
  // 그대로 유지하기 위한 헬퍼입니다. pptxgenjs 는 문자열 안의 개행을 인식하지
  // 않고, 런(run) 배열에서 breakLine:true 를 준 런 다음에만 단락을 끊습니다.
  function detailWithBreak(before, after) {
    return [
      { text: before, options: { breakLine: true } },
      { text: after },
    ];
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
      ['02', '수행 절차 및 방법', '일정 · 개발 방법론 · 데이터 · AI 모델링 · 위기 탐지 설계'],
      ['03', '수행 경과', '아키텍처 · 화면 · 시연 · 관제 · 보안 · 실측 지표'],
      ['04', '자체 평가 의견', '트러블 슈팅 · 다음 단계'],
      ['05', '팀 구성 및 역할', '4인 역할 분담'],
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
    s.addText('「제1차 고독사 예방 기본계획(2023~2027)」은 2027년까지 고독사 발생률 20% 감축을 목표로 합니다. 2026년 보건복지부 R&D 예산은 전년 대비 12.6% 증가한 1조 652억 원으로, AI·디지털 헬스케어 투자가 지속 확대되고 있습니다.', {
      x: 0.62, y: y0 + ch + 0.6, w: 11.4, h: 0.7, fontFace: FONT_LIGHT, fontSize: 11.5, color: TXT2, lineSpacingMultiple: 1.35, margin: 0,
    });

    hr(s, 0.62, y0 + ch + 1.45, 12.1, false);
    s.addText([
      { text: '문제는 자각입니다. ', options: { bold: true, color: DARK } },
      { text: '정서적 이상 징후는 본인이 자각하기 어렵고, 자각하지 못하는 사용자는 앱을 열지도 않습니다. 지원 서비스 인지도가 감소하는데 스트레스·우울감 경험률은 늘어나는 이 간극을, 사용자가 앱을 열길 기다리지 않는 구조로 좁히려 합니다.', options: { color: TXT2 } },
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
    header(s, '차별성', '프로젝트 개요 · 차별성', true);

    hr(s, 0.62, 1.55, 5.75, true);
    s.addText('기존 서비스', { x: 0.62, y: 1.68, w: 5.75, h: 0.32, fontFace: FONT, fontSize: 12.5, bold: true, color: DARK_MUTED, margin: 0 });
    s.addText('감지 → 사용자가 앱을 열어야 확인', {
      x: 0.62, y: 2.05, w: 5.75, h: 0.55, fontFace: FONT, fontSize: 16, color: WHITE, bold: true, margin: 0,
    });
    s.addText('위기일수록 타인의 힘이 필요하기 마련이지만, 스스로 모든 것을 직접 해야합니다.', {
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
  // [섹션 표지] 02 프로젝트 수행 절차 및 방법
  // ============================================================
  {
    const s = pres.addSlide();
    sectionCover(s, '02', '수행 절차 및 방법', '두 번째', '일정 · 개발 방법론 · 데이터 · AI 모델링 · 위기 탐지 설계');
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
    s.addText('⚠ 8/11 문서 개정 마감 이후에도 8/24~8/25에 학습 모델 도입·앱 사용 로그 구현이 이어졌고, 마감 이후의 개선도 실제 서비스에 반영돼 있습니다.', {
      x: 0.62, y: y + 0.15, w: 12.1, h: 0.4, fontFace: FONT_LIGHT, fontSize: 9.5, italic: true, color: TXT_MUTED, margin: 0,
    });
    pageNum(s, false);
  }

  // ============================================================
  // 개발 방법론
  //   ⚠ 2026-09-04 재작성. 이전 판은 「스키마 정본 일원화 · 문서 정합성
  //     자동 검증 · 브랜치 정책 · 화면설계서 UI 검증」 네 항목이었는데,
  //     방법론(개발을 어떤 방식으로 진행했는가)이 아니라 정합성 관리
  //     실무 나열에 가까웠습니다. 원칙 → 구조 → 강제 → 운영 순으로
  //     다시 세웠습니다.
  //   ⚠ 이전 판의 「API 30→33」은 8/06 시점 기록이라 덱의 다른 곳(34개)과
  //     어긋났습니다. 시점이 붙지 않은 수치는 뺐습니다.
  // ============================================================
  {
    const s = bgSlide(false);
    header(s, '개발 방법론', '수행 절차 및 방법', false);

    s.addText([
      { text: '문서를 정본으로 두고, 문서와 구현이 일치하는지를 사람이 아니라 검사 도구가 확인합니다. ',
        options: { bold: true, color: DARK } },
      { text: '4인이 각자 구현하면 같은 값이 문서마다 달라지는데, 그 대조를 사람이 기억으로 하면 반드시 새어 나갑니다.',
        options: { color: TXT2 } },
    ], { x: 0.62, y: 1.3, w: 12.1, h: 0.52, fontFace: FONT, fontSize: 12.5, margin: 0, lineSpacingMultiple: 1.35 });

    const methods = [
      ['원칙', '문서가 정본이다',
       '요구사항정의서와 화면설계서가 정본이고 구현이 그것을 따릅니다. 어긋나면 문서가 아니라 앱을 고칩니다. 8/02 전수 대조에서 6건을 발견해 정합하였습니다.'],
      ['구조', '정본은 하나만 둔다',
       '스키마는 db/schema.sql 하나입니다. ORM 모델은 그 DDL 의 매핑일 뿐이고 create_all 과 alembic 을 쓰지 않습니다. 정본이 둘이 되면 산출 문서와 대조할 기준이 사라집니다.'],
      ['강제', '세는 일은 사람이 하지 않는다',
       '검사 도구 4종(check_docs · check_numbers · check_dup · check_screens)이 문서 간 수치와 문서↔구현을 대조합니다. 회귀 테스트 348건이 그 상태를 유지합니다.'],
      ['운영', '바이너리는 병합되지 않는다',
       '팀원별 브랜치를 main 으로 병합하되, HWP·PPTX 산출물은 바이너리라 브랜치가 갈리면 병합할 수 없습니다. 문서 작업만 main 에서 직접 커밋합니다.'],
    ];

    let y = 2.02;
    const rh = 1.16;
    hr(s, 0.62, y, 12.1, false);
    methods.forEach(([tag, h, b]) => {
      s.addText(tag, { x: 0.62, y, w: 0.9, h: rh, fontFace: FONT, fontSize: 10.5, bold: true, color: GOLD, valign: 'middle', margin: 0 });
      s.addText(h, { x: 1.6, y, w: 3.0, h: rh, fontFace: FONT, fontSize: 13, bold: true, color: DARK, valign: 'middle', margin: 0, lineSpacingMultiple: 1.15 });
      s.addText(b, { x: 4.85, y, w: 7.87, h: rh, fontFace: FONT_LIGHT, fontSize: 10.5, color: TXT2, valign: 'middle', margin: 0, lineSpacingMultiple: 1.3 });
      hr(s, 0.62, y + rh, 12.1, false);
      y += rh;
    });

    s.addText('명명된 방법론을 도입하는 것보다, 어긋남이 생기는 자리를 찾아 그 자리마다 검사를 두는 편이 4인 6주 규모에 맞았습니다.', {
      x: 0.62, y: y + 0.2, w: 12.1, h: 0.4, fontFace: FONT_LIGHT, fontSize: 10.5, color: TXT_MUTED, margin: 0,
    });
    pageNum(s, false);
  }

  // ============================================================
  // 데이터 확보
  //   ⚠ 기업 브리프 원문이 「데이터 확보 — 오픈 데이터 활용」을 지정했습니다.
  //     「기업이 데이터를 안 줘서 못 했다」로 읽히는 문장을 쓰지 마세요 —
  //     사실과 다르고 브리프를 안 읽은 것으로 보입니다.
  //     근거: docs/검증/기업과제_대조_방어_20260825.md
  // ============================================================
  {
    const s = bgSlide(false);
    header(s, '데이터 확보', '수행 절차 및 방법 · 데이터', false);

    s.addText('기업 브리프가 「오픈 데이터 활용」을 지정했습니다. 공개 데이터셋 3종을 받아 라벨 적합성을 각각 확인하고 한 종을 채택했습니다.', {
      x: 0.62, y: 1.28, w: 12.1, h: 0.4, fontFace: FONT_LIGHT, fontSize: 11.5,
      color: TXT2, margin: 0, lineSpacingMultiple: 1.3,
    });

    const cols = [
      ['데이터셋', 0.62, 2.75],
      ['확보 범위', 3.45, 2.6],
      ['라벨', 6.15, 3.15],
      ['판정', 9.4, 3.32],
    ];
    let y = 1.9;
    cols.forEach(([h, x, w]) => {
      s.addText(h, { x, y, w, h: 0.32, fontFace: FONT, fontSize: 11, bold: true, color: TXT_MUTED, margin: 0 });
    });
    y += 0.36;
    hr(s, 0.62, y, 12.1, false);
    y += 0.12;

    const rows = [
      ['GLOBEM', 'INS-W 공개 샘플 4종\n(수면 · 걸음수)', '우울 척도(dep_endterm)\n감정 라벨 없음', '감정 분류로 치환 불가', false],
      ['PMData', 'Fitbit 수면 JSON\n(deep · light · rem · wake)', '감정 라벨 없음', '표본 규모 부족 · 미채택', false],
      ['LifeSnaps RAIS', '62명 · 4,086표본', 'SEMA MOOD ·\nTENSE/ANXIOUS', '채택 — 학습·검증 정본', true],
    ];
    rows.forEach(([a, b, c, d, pick]) => {
      const rh = 1.02;
      if (pick) {
        s.addShape('rect', { x: 0.5, y: y - 0.06, w: 12.34, h: rh, fill: { color: 'F1EADD' }, line: { color: 'FFFFFF', width: 0 } });
        s.addShape('line', { x: 0.5, y: y - 0.06, w: 0, h: rh, line: { color: GOLD, width: 3 } });
      }
      s.addText(a, { x: 0.62, y, w: 2.75, h: rh - 0.1, fontFace: FONT, fontSize: 12.5, bold: true, color: DARK, valign: 'middle', margin: 0 });
      s.addText(b, { x: 3.45, y, w: 2.6, h: rh - 0.1, fontFace: FONT_LIGHT, fontSize: 10, color: TXT2, valign: 'middle', margin: 0, lineSpacingMultiple: 1.25 });
      s.addText(c, { x: 6.15, y, w: 3.15, h: rh - 0.1, fontFace: FONT_LIGHT, fontSize: 10, color: TXT2, valign: 'middle', margin: 0, lineSpacingMultiple: 1.25 });
      s.addText(d, { x: 9.4, y, w: 3.32, h: rh - 0.1, fontFace: FONT, fontSize: 10.5, bold: pick, color: pick ? GOLD_DARK : TXT2, valign: 'middle', margin: 0, lineSpacingMultiple: 1.25 });
      y += rh;
      hr(s, 0.62, y - 0.06, 12.1, false);
    });

    s.addText('AI Hub 는 내국인 안심존 접근 제한으로 사용하지 못해 위 3종으로 대체했습니다.', {
      x: 0.62, y: y + 0.16, w: 12.1, h: 0.36, fontFace: FONT_LIGHT, fontSize: 10.5,
      color: TXT_MUTED, margin: 0,
    });
    pageNum(s, false);
  }

  // ============================================================
  // 전처리
  // ============================================================
  {
    const s = bgSlide(false);
    header(s, '전처리', '수행 절차 및 방법 · 데이터', false);

    const steps = [
      ['원천 파싱', '수면 단계 · 걸음수 ·\n심박 · HRV · 체성분'],
      ['개인 기준선', '참가자별 평소 분포를\n먼저 세웁니다'],
      ['이탈 지표 7개', '평소 대비 오늘의\n편차를 수치화'],
      ['학습 행렬', '결측은 0이 아니라\nnull 로 유지'],
    ];
    const bw = 2.86, bh = 1.42, gap = 0.22;
    steps.forEach(([t, d], i) => {
      const x = 0.62 + i * (bw + gap);
      s.addShape('rect', { x, y: 1.5, w: bw, h: bh, fill: { color: WHITE }, line: { color: LINE, width: 1 } });
      s.addShape('line', { x, y: 1.5, w: bw, h: 0, line: { color: GOLD, width: 3 } });
      s.addText(t, { x: x + 0.18, y: 1.66, w: bw - 0.36, h: 0.34, fontFace: FONT, fontSize: 12.5, bold: true, color: DARK, margin: 0 });
      s.addText(d, { x: x + 0.18, y: 2.04, w: bw - 0.36, h: 0.72, fontFace: FONT_LIGHT, fontSize: 9.5, color: TXT2, margin: 0, lineSpacingMultiple: 1.25 });
      if (i < steps.length - 1) {
        s.addText('→', { x: x + bw, y: 1.5, w: gap, h: bh, fontFace: FONT, fontSize: 13, color: TXT_MUTED, align: 'center', valign: 'middle', margin: 0 });
      }
    });

    let y = 3.28;
    const notes = [
      ['스크린타임을 일부러 뺐습니다', 'GLOBEM 에는 screen.csv 가 있지만 쓰지 않았습니다. LISN 은 폰 사용량을 수집하지 않으므로, 그 피처로 학습하면 배포 시 그 자리가 비어 성능이 나오지 않습니다. 서비스가 만들 수 있는 피처만 씁니다.'],
      ['결측을 0 으로 채우지 않습니다', '「0걸음」과 「측정 안 됨」은 다른 사건입니다. 실측치가 3일치 미만이면 판정을 422 로 끊어, 편차 0 을 「정상」으로 적재하지 않습니다.'],
    ];
    hr(s, 0.62, y, 12.1, false);
    y += 0.16;
    notes.forEach(([h, b]) => {
      s.addText(h, { x: 0.62, y, w: 3.5, h: 0.7, fontFace: FONT, fontSize: 12, bold: true, color: DARK, valign: 'top', margin: 0, lineSpacingMultiple: 1.2 });
      s.addText(b, { x: 4.3, y, w: 8.42, h: 0.86, fontFace: FONT_LIGHT, fontSize: 10.5, color: TXT2, valign: 'top', margin: 0, lineSpacingMultiple: 1.35 });
      y += 1.0;
      hr(s, 0.62, y - 0.1, 12.1, false);
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
      // ⚠ 0.609 에는 반드시 「참가자 내부」를 붙입니다(상위 CLAUDE.md 절대규칙 2).
      //   전체 AUC 는 0.546 이라, 조건 없는 0.609 는 방어할 수 없습니다.
      ['채택', '학습된 집계(로지스틱 회귀)', '참가자 내부 AUC 0.609', GOLD_DARK],
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
    s.addText('이상 감지를 위한 과정', {
      x: 0.62, y: y + 0.35, w: 11.4, h: 0.4, fontFace: FONT, fontSize: 12.5, bold: true, color: DARK, margin: 0,
    });
    s.addText('참가자 분할 GroupKFold(5) + 중첩 교차검증으로 과적합 방지 · 부트스트랩 2000회 · LifeSnaps 62명 4086표본.', {
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
      s.addText(tag, { x: 0.62, y, w: 1.9, h: rh, fontFace: FONT, fontSize: 11, bold: true, color: GOLD_DARK, valign: 'middle', margin: 0 });
      s.addText(h, { x: 2.6, y, w: 4.4, h: rh, fontFace: FONT, fontSize: 13.5, bold: true, color: DARK, valign: 'middle', margin: 0, lineSpacingMultiple: 1.15 });
      s.addText(b, { x: 7.15, y, w: 5.35, h: rh, fontFace: FONT_LIGHT, fontSize: 11, color: TXT2, valign: 'middle', margin: 0, lineSpacingMultiple: 1.3 });
      y += rh;
    });
    hr(s, 0.62, y, 12.1, false);

    // 2026-09-04 — 「재현율 0.081 → 0.946 · 경고색 · 3일 미만 422」 요약 문단을
    //   여기서 뺐습니다. 세 항목이 전부 슬라이드 19(위기 탐지 2단계 구조)에
    //   다시 나옵니다. 02 는 설계 결정, 03 은 결과와 수치로 역할을 가릅니다.
    s.addText('세 결정 모두 「응답 품질보다 안전을 먼저」라는 한 기준에서 나왔습니다. 결과 수치는 수행 경과에서 제시합니다.', {
      x: 0.62, y: y + 0.24, w: 11.4, h: 0.4, fontFace: FONT_LIGHT, fontSize: 11,
      color: TXT_MUTED, margin: 0,
    });
    pageNum(s, false);
  }

  // ============================================================
  // [섹션 표지] 03 프로젝트 수행 경과
  // ============================================================
  {
    const s = pres.addSlide();
    sectionCover(s, '03', '수행 경과', '세 번째', '아키텍처 · 화면 · 시연 · 관제 · 보안 · 실측 지표');
  }

  // ============================================================
  // 시스템 아키텍처 — 다이어그램 1장
  //   그림은 docs/design/src/ARCH_SYSTEM_01.html 을 Edge 헤드리스로 구운 것이다.
  //   HTML 을 고쳤으면 다시 굽고 나서 이 스크립트를 돌릴 것 —
  //   PNG 는 빌드 산출물이 아니라 입력이다.
  //     msedge --headless=new --disable-gpu --hide-scrollbars
  //            --force-device-scale-factor=2 --window-size=1600,790
  //            --virtual-time-budget=4000
  //            --screenshot=docs/design/ARCH_SYSTEM_01.png <html>
  // ============================================================
  {
    const s = bgSlide(false);
    header(s, '시스템 아키텍처', '수행 경과 · 아키텍처', false);

    // 3200x1580 (비율 2.025). 폭을 본문에 맞추고 높이를 비율로 잡는다.
    const iw = 12.1, ih = iw * (1580 / 3200);
    s.addImage({ path: img('ARCH_SYSTEM_01'), x: 0.62, y: 1.42, w: iw, h: ih });
    pageNum(s, false);
  }

  // ============================================================
  // 배포 구성 — 컨테이너 · 데이터 계층
  //   수치 재현:
  //     테이블  grep -icE '^\s*CREATE TABLE' db/schema.sql              → 9
  //     API     grep -rhoE '@router\.(get|post|put|patch|delete)' backend/app/api/ | wc -l → 34
  //     인덱스  grep -icE '^\s*CREATE( UNIQUE)? INDEX' db/schema.sql    → 8
  //   컨테이너 구성: infra/docker-compose.yml
  // ============================================================
  {
    const s = bgSlide(false);
    header(s, '배포 구성', '수행 경과 · 아키텍처', false);

    // --- 컨테이너 4종 : nginx 만 외부에 열려 있습니다 ---
    s.addText('컨테이너 4종 · NCP VM 1대', {
      x: 0.62, y: 1.32, w: 6.0, h: 0.32, fontFace: FONT, fontSize: 13, bold: true, color: DARK, margin: 0,
    });

    const conts = [
      ['nginx 1.27', '80 · 443 공개', 'Let’s Encrypt 자동 갱신 등록', true],
      ['backend', '8000 내부', 'FastAPI 비즈니스 서버', false],
      ['ai-server', '8001 내부', 'FastAPI 추론 서버', false],
      ['postgres 17', '5432 내부', '볼륨으로 데이터 보존', false],
    ];
    let cy = 1.74;
    conts.forEach(([n, port, desc, open]) => {
      s.addShape('rect', {
        x: 0.62, y: cy, w: 6.0, h: 0.74,
        fill: { color: open ? 'F1EADD' : WHITE }, line: { color: open ? GOLD : LINE, width: open ? 2 : 1 },
      });
      s.addText(n, { x: 0.82, y: cy + 0.12, w: 2.1, h: 0.3, fontFace: FONT, fontSize: 12, bold: true, color: DARK, margin: 0 });
      s.addText(port, {
        x: 0.82, y: cy + 0.44, w: 2.1, h: 0.26, fontFace: FONT_LIGHT, fontSize: 9.5,
        color: open ? GOLD_DARK : TXT_MUTED, margin: 0,
      });
      s.addText(desc, { x: 3.05, y: cy + 0.26, w: 3.4, h: 0.4, fontFace: FONT_LIGHT, fontSize: 10, color: TXT2, valign: 'middle', margin: 0 });
      cy += 0.82;
    });

    s.addText('외부로 여는 포트는 nginx 의 80 · 443 둘뿐입니다. DB · 두 서버는 컨테이너 네트워크 안에만 있어 인터넷에서 직접 닿지 않습니다.', {
      x: 0.62, y: cy + 0.08, w: 6.0, h: 0.6, fontFace: FONT_LIGHT, fontSize: 9.5,
      color: TXT_MUTED, margin: 0, lineSpacingMultiple: 1.3,
    });

    // --- 가동 확인 (2026.09.04 실측) ---
    //   curl https://101.79.24.15.nip.io/health      → {"status":"ok"}
    //   curl https://101.79.24.15.nip.io/health/db   → {"status":"ok","database":"connected"}
    //   openssl s_client … | openssl x509 -dates     → notAfter Nov 22 2026
    s.addShape('rect', { x: 0.62, y: cy + 0.78, w: 6.0, h: 1.32, fill: { color: 'F1EADD' }, line: { color: GOLD, width: 1 } });
    s.addText('가동 확인 · 2026.09.04', {
      x: 0.82, y: cy + 0.9, w: 5.6, h: 0.28, fontFace: FONT, fontSize: 11, bold: true, color: GOLD_DARK, margin: 0,
    });
    s.addText([
      { text: 'https://101.79.24.15.nip.io', options: { bold: true, color: DARK } },
      { text: '   · /health 200  · /health/db connected', options: { color: TXT2 } },
    ], { x: 0.82, y: cy + 1.2, w: 5.6, h: 0.3, fontFace: FONT, fontSize: 10, margin: 0 });
    s.addText('HTTPS 인증서 2026.11.22 까지 유효 · 컨테이너 4종 모두 restart 정책으로 재기동 시 자동 복구', {
      x: 0.82, y: cy + 1.5, w: 5.6, h: 0.5, fontFace: FONT_LIGHT, fontSize: 9,
      color: TXT2, margin: 0, lineSpacingMultiple: 1.25,
    });

    // --- 데이터 계층 ---
    s.addText('데이터 계층', {
      x: 7.0, y: 1.32, w: 5.72, h: 0.32, fontFace: FONT, fontSize: 13, bold: true, color: DARK, margin: 0,
    });

    const stats = [['9', '테이블'], ['34', 'REST API'], ['8', '인덱스']];
    stats.forEach(([v, l], i) => {
      const x = 7.0 + i * 1.95;
      s.addText(v, { x, y: 1.74, w: 1.8, h: 0.62, fontFace: SERIF_BOLD, fontSize: 34, color: GOLD, margin: 0 });
      s.addText(l, { x, y: 2.4, w: 1.8, h: 0.28, fontFace: FONT_LIGHT, fontSize: 10, color: TXT_MUTED, margin: 0 });
    });

    hr(s, 7.0, 2.86, 5.72, false);
    const dnotes = [
      ['UUID v4 · TIMESTAMPTZ · JSONB', '전 테이블 공통 표준. 시각 컬럼에 tz 를 빠뜨리면 tz-aware 값을 넣는 순간 드라이버가 죽습니다.'],
      ['(user_id, collected_at DESC)', '라이프로그는 기간별 조회가 핵심 동작이라 복합 인덱스를 먼저 설계했습니다.'],
      ['탈퇴 시 CASCADE', '회원 삭제가 하위 기록까지 함께 지웁니다.'],
    ];
    let dy = 3.02;
    dnotes.forEach(([h, b]) => {
      s.addText(h, { x: 7.0, y: dy, w: 5.72, h: 0.28, fontFace: FONT, fontSize: 11, bold: true, color: DARK, margin: 0 });
      s.addText(b, { x: 7.0, y: dy + 0.28, w: 5.72, h: 0.62, fontFace: FONT_LIGHT, fontSize: 9.5, color: TXT2, margin: 0, lineSpacingMultiple: 1.3 });
      dy += 0.98;
    });

    // --- 심사용 테스트 계정 ---
    //   ⚠ 이 두 줄만 채우고 다시 생성하세요. 계정은 운영 DB 에 직접 만듭니다 —
    //     docs/가이드/심사용_계정_발급.md 절차를 그대로 따르면 됩니다.
    //     빈 문자열이면 이 상자를 통째로 건너뜁니다(빈 칸이 찍히는 것보다 낫습니다).
    // 자격증명은 소스에 두지 않는다 — 이 저장소는 공개다.
    //   tools/capture/demo_account.json (gitignore 대상) 에서 읽는다:
    //     { "id": "demo.admin@lisn-test.example", "pw": "..." }
    //   파일이 없으면 빈 값이 되어 아래 상자를 통째로 건너뛴다.
    //   심사 제출본을 만들 때만 그 파일을 두고 빌드하세요.
    let DEMO_ID = '', DEMO_PW = '';
    try {
      const a = JSON.parse(require('fs').readFileSync(
        require('path').join(__dirname, 'demo_account.json'), 'utf8'));
      DEMO_ID = a.id || ''; DEMO_PW = a.pw || '';
    } catch (e) { /* 파일 없음 — 계정 상자 생략 */ }
    if (DEMO_ID && DEMO_PW) {
      s.addShape('rect', { x: 7.0, y: 6.06, w: 5.72, h: 0.84, fill: { color: 'F1EADD' }, line: { color: GOLD, width: 1 } });
      s.addText('심사용 계정', {
        x: 7.2, y: 6.16, w: 5.32, h: 0.26, fontFace: FONT, fontSize: 11, bold: true, color: GOLD_DARK, margin: 0,
      });
      s.addText([
        { text: DEMO_ID, options: { bold: true, color: DARK } },
        { text: '   ·   ', options: { color: TXT_MUTED } },
        { text: DEMO_PW, options: { bold: true, color: DARK } },
      ], { x: 7.2, y: 6.44, w: 5.32, h: 0.26, fontFace: FONT, fontSize: 10, margin: 0 });
      s.addText('관제 웹 로그인용. 앱은 demo.crisis@lisn-test.example · 같은 비밀번호', {
        x: 7.2, y: 6.68, w: 5.32, h: 0.22, fontFace: FONT_LIGHT, fontSize: 8.5, color: TXT2, margin: 0,
      });
    }

    pageNum(s, false);
  }

  // ============================================================
  // 라이브러리 — 계층별 채택과 이유
  //   근거: frontend/app/pubspec.yaml · backend/requirements.txt ·
  //         frontend/admin/package.json (실제 의존성만 적습니다)
  // ============================================================
  {
    const s = bgSlide(false);
    header(s, '라이브러리', '수행 경과 · 아키텍처', false);

    const cols = [
      ['앱 — Flutter', [
        ['health 13.3.1', 'Health Connect 래퍼. HealthKit 도 감싸지만 iOS 는 장비·계정 문제로 제외'],
        ['workmanager', '앱이 꺼져 있어도 15분 주기로 깨어나 수집'],
        ['firebase_messaging', '선제 접촉 푸시 발송'],
        ['flutter_secure_storage', 'JWT 를 평문 저장하지 않음'],
        ['url_launcher', '109 직통 연결'],
      ]],
      ['서버 — FastAPI', [
        ['fastapi · uvicorn', '비동기 I/O 로 LLM 대기와 시계열 적재를 동시에 감당'],
        ['sqlalchemy · asyncpg', '비동기 드라이버. schema.sql 이 정본이고 ORM 은 매핑'],
        ['bcrypt · pyjwt', '비밀번호 단방향 해시 · 세션 토큰'],
        ['openai', '페르소나 대화 · 위기 문맥 판정'],
        ['firebase-admin', 'FCM 서버 발송'],
      ]],
      ['관제 웹 — React', [
        ['react 19 · vite', '화면 2개 규모라 번들러와 런타임만 둠'],
        ['라우터 미도입', '화면이 둘이라 상태로 전환. 의존성을 늘리지 않음'],
        ['상태관리 미도입', '전역 상태가 세션 하나뿐이라 Context 로 충분'],
        ['차트 미도입', '위험도 분포는 막대 폭 계산으로 직접 그림'],
        ['fetch 직접 호출', 'HTTP 클라이언트를 따로 두지 않음'],
      ]],
    ];

    const cw = 3.86, cgap = 0.26;
    cols.forEach(([title, items], ci) => {
      const x = 0.62 + ci * (cw + cgap);
      s.addShape('line', { x, y: 1.45, w: cw, h: 0, line: { color: GOLD, width: 3 } });
      s.addText(title, {
        x, y: 1.58, w: cw, h: 0.36, fontFace: FONT, fontSize: 13.5, bold: true, color: DARK, margin: 0,
      });
      let y = 2.06;
      items.forEach(([n, why]) => {
        s.addText(n, { x, y, w: cw, h: 0.28, fontFace: FONT, fontSize: 11, bold: true, color: DARK, margin: 0 });
        s.addText(why, {
          x, y: y + 0.28, w: cw, h: 0.52, fontFace: FONT_LIGHT, fontSize: 9.5,
          color: TXT2, margin: 0, lineSpacingMultiple: 1.25,
        });
        y += 0.86;
      });
    });

    hr(s, 0.62, 6.5, 12.1, false);
    s.addText('관제 웹의 「미도입」은 빠뜨린 것이 아니라 화면 2개 규모에 맞춘 결정입니다. 의존성이 늘면 그만큼 갱신·취약점 대응 부담이 따라옵니다.', {
      x: 0.62, y: 6.66, w: 12.1, h: 0.4, fontFace: FONT_LIGHT, fontSize: 10.5,
      color: TXT_MUTED, margin: 0,
    });
    pageNum(s, false);
  }

  // ============================================================
  // AI 설계 결과
  // ============================================================
  {
    const s = bgSlide(false);
    header(s, 'AI 설계 결과', '수행 경과 · AI', false);

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
    s.addText('감정 분류 결과', {
      x: 0.9, y, w: 7.0, h: 0.4, fontFace: FONT, fontSize: 15, bold: true, color: DARK, margin: 0,
    });
    s.addText('바뀐 것은 지표를 합치는 방식뿐입니다. 개인 기준선 대비 이탈 지표 7개를 하나의 점수로 합치는 방법을 데이터로 골랐을 뿐이고, 감정 코드는 여전히 이탈 정도를 표시하는 산출값입니다. model_version 이 hybrid- 로 시작하면 이 집계가 관여한 것이고, rule- 이면 기존 규칙 그대로입니다.', {
      x: 0.9, y: y + 0.42, w: 7.0, h: 1.15, fontFace: FONT_LIGHT, fontSize: 11.5, color: TXT2, lineSpacingMultiple: 1.35, margin: 0,
    });
    s.addText('※ 같은 데이터로 70%를 보고한 선행연구를 재현하니, 그 지표의 기준선이 66.7%였습니다(ai/train/eval_replicate_paper.py).', {
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
      ['위로보다 안전', 'CRITICAL 이면 답변 대신 상담 연결 화면을 보여줍니다. 판정 전에 화면으로 흘러나간 글자가 하나도 없습니다.'],
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
  // 앱 화면 — 핵심 기능 6종
  //   화면명은 화면설계서(정본)의 「화면이름」을 그대로 씁니다.
  //   docs/extracted/화면설계서_귀기울임.txt 에서 확인했습니다.
  //   시안 PNG 는 780x1688(비율 0.462) 이라 폭에서 6장이 딱 맞습니다.
  // ============================================================
  function screenGrid(s, items, gap) {
    const x0 = 0.62, total = 12.1;
    const n = items.length;
    const iw = (total - gap * (n - 1)) / n;
    const ih = iw / 0.462;
    const y0 = 1.5;
    items.forEach(([id, name, desc], i) => {
      const x = x0 + i * (iw + gap);
      s.addShape('rect', {
        x: x - 0.015, y: y0 - 0.015, w: iw + 0.03, h: ih + 0.03,
        fill: { color: WHITE }, line: { color: LINE, width: 1 },
      });
      s.addImage({ path: img(id), x, y: y0, w: iw, h: ih });
      s.addText(name, {
        x, y: y0 + ih + 0.1, w: iw, h: 0.3, fontFace: FONT, fontSize: 10.5,
        bold: true, color: DARK, align: 'center', margin: 0,
      });
      s.addText(desc, {
        x, y: y0 + ih + 0.42, w: iw, h: 0.5, fontFace: FONT_LIGHT, fontSize: 8.5,
        color: TXT2, align: 'center', margin: 0, lineSpacingMultiple: 1.25,
      });
    });
  }

  {
    const s = bgSlide(false);
    header(s, '앱 화면', '수행 경과 · 화면', false);
    screenGrid(s, [
      ['MAIN_HOME_01', '메인 홈 대시보드', '오늘의 마음 상태 · 라이프로그 요약'],
      ['MAIN_CHAT_01', '챗봇 성격 선택', 'F형 공감 · T형 조언 중 선택'],
      ['MAIN_CHAT_02', '실시간 대화', '대화와 기록 조회를 한 화면에서'],
      ['MAIN_EMERGENCY_01', '긴급 상담 연결', 'CRITICAL 판정 시 109 직통'],
      ['MAIN_LIFELOG_01', '라이프로그 조회', '활동량 · 수면 · 심박 · HRV 추이'],
      ['MAIN_REPORT_01', '정서 리포트', '기간별 감정 추이와 PDF 내보내기'],
    ], 0.16);
    pageNum(s, false);
  }

  // ============================================================
  // 앱 화면 — 가입 · 설정 7종
  // ============================================================
  {
    const s = bgSlide(false);
    header(s, '가입 · 설정', '수행 경과 · 화면', false);
    screenGrid(s, [
      ['MAIN_LOGIN_01', '로그인', '자체 인증 · JWT 세션'],
      ['MAIN_LOGIN_02', '비밀번호 재설정', '메일 인증 후 재설정'],
      ['MAIN_JOIN_01', '약관 동의', '필수 · 선택 항목 분리'],
      ['MAIN_JOIN_02', '정보 입력', '신체 정보는 선택 입력'],
      ['MAIN_JOIN_03', '웨어러블 연동', 'Health Connect 권한 설정'],
      ['MAIN_SETTING_01', '설정', '알림 · 연동 · 개인정보'],
      ['MAIN_SETTING_02', '계정 관리', '탈퇴 시 CASCADE 삭제'],
    ], 0.14);
    pageNum(s, false);
  }

  // ============================================================
  // 3분 시연 영상
  // ============================================================
  {
    const s = bgSlide(false);
    header(s, '시연 영상', '수행 경과 · 시연', false);
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
    header(s, '관제 화면', '수행 경과 · 관제', false);

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
    header(s, '보안 설계', '수행 경과 · 보안', false);

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
      { text: '보안 요구를 기능 제약과 함께 설계', options: { bold: true, color: DARK } },
      { text: '했습니다. 마스킹은 저장 전에 하며, 원문은 어디에도 남지 않고, 외부 LLM에도 마스킹된 텍스트만 전송됩니다.', options: { color: TXT2 } },
    ], { x: 0.62, y: boxY + 0.22, w: 12.1, h: 0.9, fontFace: FONT, fontSize: 12, lineSpacingMultiple: 1.35, margin: 0 });
    pageNum(s, false);
  }

  // ============================================================
  // 실측 성과 지표
  // ============================================================
  {
    const s = bgSlide(true);
    header(s, '성과 지표', '수행 경과 · 성과', true);

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
      { text: '문서 정합성 자동 검증은 ', options: { bold: true, color: WHITE } },
      { text: '같은 수치가 문서마다 달라지는 문제를 사람이 아닌 도구가 대조합니다    ·    ', options: { color: DARK_MUTED } },
      { text: 'db/schema.sql 정본은 ', options: { bold: true, color: WHITE } },
      { text: '드리프트 테스트가 모델과 어긋나면 실패합니다', options: { color: DARK_MUTED } },
    ], { x: 0.62, y: tilesBottom + 0.25, w: 12.1, h: 0.6, fontFace: FONT_LIGHT, fontSize: 10.5, lineSpacingMultiple: 1.35, margin: 0 });

    s.addText('※ 재현율은 8/05 0.793 → 8/12 0.946으로 올랐습니다. 팀이 확정한 라벨 기준을 프롬프트에 반영하고, 판정 모델을 gpt-5.6 → gpt-5.4로 교체했습니다(미탐 23 → 6건, 지연 최댓값 절반 이하).', {
      x: 0.62, y: 6.6, w: 12.1, h: 0.32, fontFace: FONT_LIGHT, fontSize: 9, italic: true, color: DARK_MUTED, margin: 0,
    });
    pageNum(s, true);
  }

  // ============================================================
  // [섹션 표지] 04 자체 평가 의견
  // ============================================================
  {
    const s = pres.addSlide();
    sectionCover(s, '04', '자체 평가 의견', '네 번째', '트러블 슈팅 · 다음 단계');
  }

  // ============================================================
  // 자체 평가 의견
  // ============================================================
  {
    const s = bgSlide(false);
    header(s, '트러블 슈팅', '자체 평가 의견', false);

    s.addText('해결', { x: 0.62, y: 1.35, w: 5.8, h: 0.35, fontFace: FONT, fontSize: 14, bold: true, color: GOLD_DARK, margin: 0 });
    hr(s, 0.62, 1.78, 5.8, false);
    const good = [
      ['검증 없이 채택 안 함', '학습 모델 채택에 26회, 위기 판정 개선에 4회차 재측정.'],
      ['문서-구현 갭 해소', '요구사항 9건 전부 해소. 채팅 위기 관제 누락 건 해소.'],
      ['정본을 하나로', '다양한 환경에서 작업하더라도 일관성 있는 결과물 산출'],
    ];
    let gy = 2.0;
    // ⚠ 마지막 행("정본을 하나로")의 설명 글상자만 PM 이 PowerPoint 에서
    // 0.85in → 0.67in 으로 직접 줄여뒀습니다(2026.08.26). 그대로 유지합니다.
    good.forEach(([h, b], i) => {
      const detailH = i === good.length - 1 ? 0.67 : 0.85;
      s.addText(h, { x: 0.62, y: gy, w: 5.8, h: 0.35, fontFace: FONT, fontSize: 11.5, bold: true, color: DARK, margin: 0 });
      s.addText(b, { x: 0.62, y: gy + 0.35, w: 5.8, h: detailH, fontFace: FONT_LIGHT, fontSize: 10, color: TXT2, margin: 0, lineSpacingMultiple: 1.25 });
      gy += 1.35;
    });

    s.addShape('line', { x: 6.75, y: 1.35, w: 0, h: gy - 1.5, line: { color: LINE, width: 1 } });

    s.addText('미해결', { x: 7.05, y: 1.35, w: 5.6, h: 0.35, fontFace: FONT, fontSize: 14, bold: true, color: TXT_FAINT, margin: 0 });
    hr(s, 7.05, 1.78, 5.6, false);
    const bad = [
      ['실기기 검증 남음', 'Health Connect·FCM 모두 에뮬레이터·자격증명 초기화까지만 확인했습니다. 실기기 하나면 반나절 안에 끝나는 검증인데, 확보하지 못했습니다.'],
      ['평가셋 holdout 없음', '재현율 0.946은 이 211건 안에서의 값입니다. 라벨을 만든 사람과 평가 문장을 쓴 사람이 겹칩니다.'],
      ['AI 모델 표본 수 적음', '이 분야 표본 중앙값이 60.5명인데 저희는 62명입니다. 42편 중 외부 검증은 1편뿐이라는 것도 함께 봐야 할 맥락입니다.'],
    ];
    let by = 2.0;
    bad.forEach(([h, b]) => {
      s.addText(h, { x: 7.05, y: by, w: 5.6, h: 0.35, fontFace: FONT, fontSize: 11.5, bold: true, color: DARK, margin: 0 });
      s.addText(b, { x: 7.05, y: by + 0.35, w: 5.6, h: 0.85, fontFace: FONT_LIGHT, fontSize: 10, color: TXT2, margin: 0, lineSpacingMultiple: 1.25 });
      by += 1.35;
    });

    hr(s, 0.62, Math.max(gy, by) + 0.05, 12.1, false);
    // 2026.08.27 PM 손수정 — 마무리 문장 삭제. 구분선(hr)은 유지합니다.
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
      ['평가셋 확장', '다음 단계', '라벨링에 관여하지 않은 사람이 새로 쓴 문장을 더해 일반화를 재검증합니다.'],
      ['AI 모델 표본 확대', '다음 단계', '표본을 늘려 재검증하고, 참가자 수에 따른 성능 변화를 함께 봅니다.'],
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
  // [섹션 표지] 05 팀 구성 및 역할
  // ============================================================
  {
    const s = pres.addSlide();
    sectionCover(s, '05', '팀 구성 및 역할', '다섯 번째', '4인 · 6주 · 기업주제(라라랩스)');
  }

  // ============================================================
  // 팀 구성 및 역할
  // ============================================================
  {
    const s = bgSlide(false);
    header(s, '역할 분담', '팀 구성 및 역할', false);

    // ⚠ 아래 세 detail 은 PM 이 PowerPoint 에서 직접 줄바꿈 위치를 잡아둔
    // 자리입니다(2026.08.26 — documents/ 의 손수정을 detailWithBreak 로 포팅).
    // 재구성하더라도 이 줄바꿈 지점을 건드리지 마세요.
    const roles = [
      ['이응균', 'PM', '기획서·요구사항정의서·데이터베이스요구사항분석서 등 5종 산출물 및 프로젝트 총괄.'],
      ['김건영', 'AI · 모델링', detailWithBreak('개인 기준선 이탈 탐지 모델링. 26회 검증 시도 끝에 학습된 집계 채택. 위기 판정 프롬프트·', '평가셋 설계.')],
      ['윤일준', '백엔드 · DB', detailWithBreak('FastAPI 34개 엔드포인트, PostgreSQL 9테이블 스키마 정본 관리. Health Connect 연동·', '클라우드 배포(NCP).')],
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

    s.addText('전원이 교내 공용 PostgreSQL 인스턴스에 접속해 동일한 스키마로 개발했고, 통합 테스트 시점의 스키마 불일치를 방지했습니다.', {
      x: 0.62, y: y + 0.2, w: 12.1, h: 0.4, fontFace: FONT_LIGHT, fontSize: 10.5, italic: true, color: TXT_MUTED, margin: 0,
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
    s.addText('먼저 다가가는 정서 케어', {
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
