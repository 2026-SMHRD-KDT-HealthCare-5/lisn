// react-icons 컴포넌트를 pptxgenjs 가 받는 PNG data URI 로 바꿉니다.
//
// ⚠ 이 파일은 build_deck.js 가 요구하는데(require('./icons')) 저장소에
//   커밋이 안 돼 있었습니다(2026.08.25 발견). 이전 세션이 만들어 썼지만
//   git 에는 없었습니다 — 그래서 build_deck.js 를 이 PC 에서 그대로
//   돌리면 "Cannot find module './icons'" 로 죽습니다. 다시 만들었습니다.
//
// react-icons 는 React 컴포넌트라 SVG 마크업으로만 존재합니다.
// pptxgenjs 의 addImage 는 SVG data URI 를 못 받고(PowerPoint 호환성
// 문제로 PNG 를 기대합니다) 그래서 SVG → PNG 래스터화가 필요합니다.
//
//   React 컴포넌트 → (react-dom/server) → SVG 문자열
//                  → (sharp)            → PNG 버퍼 → base64 data URI

const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const sharp = require('sharp');

/**
 * @param {Function} Component react-icons 아이콘 컴포넌트 (예: Fi.FiWatch)
 * @param {string} colorHex    6자리 hex, # 없이 (예: '5A6BE0')
 * @param {number} size        출력 PNG 한 변 픽셀
 * @returns {Promise<string>}  "data:image/png;base64,..." 형태
 */
async function iconPng(Component, colorHex, size = 256) {
  const svg = renderToStaticMarkup(
    React.createElement(Component, { size, color: '#' + colorHex })
  );
  const png = await sharp(Buffer.from(svg)).resize(size, size).png().toBuffer();
  return 'data:image/png;base64,' + png.toString('base64');
}

module.exports = { iconPng };
