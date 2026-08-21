/**
 * 관제 웹 화면 녹화 — 시연영상 컷 4
 *
 * 왜 Playwright 인가
 *   브라우저 화면은 `adb screenrecord` 로 못 잡습니다. 데스크톱 캡처
 *   (ffmpeg gdigrab)는 되지만 **조작을 스크립트로 할 수 없어** 마우스를
 *   손으로 움직여야 하고, 창 위치가 바뀌면 좌표가 다 어긋납니다.
 *
 *   Playwright 는 조작과 녹화를 같이 합니다. 뷰포트가 고정이라 몇 번
 *   다시 찍어도 같은 화면이 나옵니다.
 *
 * ⚠ Playwright 녹화에는 **마우스 커서가 안 찍힙니다.** 그래서 커서를
 *   페이지에 직접 그려 넣습니다(_installCursor). 안 그리면 클릭이 저절로
 *   일어나는 것처럼 보여서 「조작하는 영상」이 아니라 「화면이 바뀌는
 *   영상」이 됩니다.
 *
 * 사용:
 *   node capture_admin.js
 *   → out/admin-cut4.webm
 *
 * 전제: 관리자 웹(5173)과 백엔드(8000)가 떠 있어야 합니다.
 */

const { chromium } = require('playwright');
const path = require('path');

const URL = 'http://localhost:5173';
const EMAIL = 'admin@lisn-test.example';
const PASSWORD = 'rldnfdla';
const OUT = path.join(__dirname, 'out');

// 1280x720 — 발표 슬라이드에 그대로 얹을 수 있는 16:9.
const VIEWPORT = { width: 1280, height: 720 };

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/**
 * 가짜 커서를 페이지에 심습니다. 실제 마우스 좌표를 따라다니게 만들어,
 * `page.mouse.move()` 가 영상에 보이게 합니다.
 */
async function installCursor(page) {
  await page.addInitScript(() => {
    window.__installCursor = () => {
      if (document.getElementById('__cursor')) return;
      const c = document.createElement('div');
      c.id = '__cursor';
      c.style.cssText = [
        'position:fixed', 'left:0', 'top:0', 'width:22px', 'height:22px',
        'z-index:2147483647', 'pointer-events:none',
        'transition:transform .08s linear',
      ].join(';');
      // 화살표 커서를 SVG 로. 흰 테두리를 둘러 밝은 배경에서도 보입니다.
      c.innerHTML =
        '<svg viewBox="0 0 24 24" width="22" height="22">' +
        '<path d="M5 2 L5 19 L9.5 14.5 L12.5 21.5 L15.5 20 L12.5 13.5 L19 13.5 Z" ' +
        'fill="#1B2547" stroke="#fff" stroke-width="1.4"/></svg>';
      document.body.appendChild(c);
      document.addEventListener('mousemove', (e) => {
        c.style.transform = `translate(${e.clientX}px, ${e.clientY}px)`;
      }, true);
    };
    document.addEventListener('DOMContentLoaded', () => window.__installCursor());
  });
}

/** 사람이 움직이는 것처럼 여러 단계로 나눠 이동한 뒤 누릅니다. */
async function moveAndClick(page, selectorOrPos, { steps = 22, pause = 380 } = {}) {
  let x, y;
  if (typeof selectorOrPos === 'string') {
    const el = page.locator(selectorOrPos).first();
    await el.waitFor({ state: 'visible', timeout: 10000 });
    await el.scrollIntoViewIfNeeded();
    const box = await el.boundingBox();
    x = box.x + box.width / 2;
    y = box.y + box.height / 2;
  } else {
    ({ x, y } = selectorOrPos);
  }
  await page.mouse.move(x, y, { steps });
  await sleep(pause);
  await page.mouse.click(x, y);
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: VIEWPORT,
    recordVideo: { dir: OUT, size: VIEWPORT },
    locale: 'ko-KR',
    timezoneId: 'Asia/Seoul',
    deviceScaleFactor: 1,
  });
  const page = await context.newPage();
  await installCursor(page);

  await page.goto(URL, { waitUntil: 'networkidle' });
  await page.evaluate(() => window.__installCursor && window.__installCursor());
  await page.mouse.move(VIEWPORT.width / 2, VIEWPORT.height - 80);
  await sleep(1200);

  // ── 로그인 (ASCII 라 타이핑에 문제가 없습니다)
  await moveAndClick(page, 'input[type=email]');
  await page.keyboard.type(EMAIL, { delay: 55 });
  await sleep(350);
  await moveAndClick(page, 'input[type=password]');
  await page.keyboard.type(PASSWORD, { delay: 70 });
  await sleep(500);
  await moveAndClick(page, 'button[type=submit]');
  await page.waitForLoadState('networkidle');
  await sleep(2500);

  // ── 위험도 분포 — 3·3·3 을 읽을 시간을 줍니다
  await page.mouse.move(300, 300, { steps: 18 });
  await sleep(2200);
  await page.mouse.move(900, 300, { steps: 18 });
  await sleep(1800);

  // 「미평가 N명」 안내로 커서를 옮겨 시선을 끕니다.
  const notice = page.getByText('미평가', { exact: false }).first();
  if (await notice.count()) {
    const b = await notice.boundingBox();
    if (b) {
      await page.mouse.move(b.x + 40, b.y + b.height / 2, { steps: 20 });
      await sleep(2600);
    }
  }

  // ── 대상자 조회 — 위험도순 정렬
  await moveAndClick(page, 'a[href="#people"]');
  await page.waitForLoadState('networkidle');
  await sleep(2600);
  await page.mouse.wheel(0, 260);
  await sleep(2000);

  // ── 위기 사건 이력 — 컷 2의 그 발화가 여기 올라와 있다
  await moveAndClick(page, 'a[href="#events"]');
  await page.waitForLoadState('networkidle');
  await sleep(2200);

  // 「모델」 칸의 chat-crisis 행으로 커서를 옮깁니다. 이 영상의 요점입니다.
  const chatRow = page.getByText(/chat-crisis/).first();
  if (await chatRow.count()) {
    await chatRow.scrollIntoViewIfNeeded();
    const b = await chatRow.boundingBox();
    if (b) {
      await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2, { steps: 26 });
      await sleep(3800);
    }
  } else {
    console.warn('[!] chat-crisis 행이 없습니다 — 앱에서 위기 발화를 한 번 하고 다시 찍으세요.');
    await sleep(1500);
  }

  await sleep(1200);
  await context.close();
  await browser.close();

  console.log('완료 → ' + OUT);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
