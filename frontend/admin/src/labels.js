/**
 * 대상자 목록 문구 — MLCM_501 ❷
 *
 * ⚠ 인자로 받는 query·filter 는 **지금 화면에 그려진 목록을 만들어낸 조건**이어야
 *   한다. 살아 있는 입력값을 넘기면 다시 불러오는 동안 이전 목록 위에 새 조건이
 *   얹혀 `"하늘" 검색 결과 33명` 같은 없는 상태가 만들어진다.
 */

export const RISK_LABEL = { NORMAL: '안정', CAUTION: '주의', CRITICAL: '심각' }

/** 목록 위 건수 안내. 결과가 없으면 빈 문자열(줄 높이는 화면에서 유지한다). */
export function countLabel({ count, query = '', filter = '' }) {
  if (count === 0) return ''
  const q = query.trim()
  const head = q ? `"${q}" 검색 결과 ${count}명` : `${count}명`
  return filter ? `${head} · ${RISK_LABEL[filter]} 필터 적용 중` : head
}

/**
 * 결과가 없을 때의 안내.
 *
 * 검색 때문인지 필터 때문인지 구분해야 한다. 같은 문구를 쓰면 검색어를 고쳐야
 * 하는지 필터를 풀어야 하는지 알 수 없다.
 */
export function emptyLabel({ query = '', filter = '' }) {
  const q = query.trim()
  if (!q) return '해당하는 대상자가 없습니다.'
  const head = `"${q}"에 해당하는 대상자가 없습니다.`
  return filter ? `${head} ${RISK_LABEL[filter]} 필터를 풀고 다시 찾아보세요.` : head
}
