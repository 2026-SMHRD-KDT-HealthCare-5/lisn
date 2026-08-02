// `import.meta.env` 는 **Vite 가 주입하는 값**이라 번들 밖(node --test)에서는
// undefined 입니다. `?.` 이 없으면 이 모듈을 테스트에서 import 하는 순간 죽습니다.
const API_BASE_URL =
  import.meta.env?.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'

/**
 * 토큰이 만료됐을 때 호출됩니다. App 이 등록합니다.
 *
 * ⚠ 이게 없으면 **24시간 뒤에 화면이 조용히 고장납니다.** 탭을 열어둔 채로
 *   토큰이 만료되면 모든 조회가 401 로 실패하는데, 화면에는
 *   「불러오지 못했습니다」만 뜹니다. 세션은 그대로 남아 있어 로그인
 *   화면으로도 안 가고, 사용자는 서버가 죽은 줄 압니다.
 *   `readSession()` 의 만료 검사는 **페이지를 새로 열 때만** 돕니다.
 *
 * ⚠ **403 은 여기 걸지 마세요.** 권한이 없는 것이라 재로그인해도 해결되지
 *   않습니다. 401(만료·무효)만 세션을 버립니다.
 */
let unauthorizedHandler = null

export function setUnauthorizedHandler(handler) {
  unauthorizedHandler = handler
}

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function readError(response, fallback) {
  let message = fallback
  try {
    const body = await response.json()
    if (typeof body.detail === 'string') message = body.detail
  } catch {
    // JSON이 아닌 오류 응답은 공통 문구를 사용한다.
  }
  return new ApiError(message, response.status)
}

async function request(path, { token, params, fallback } = {}) {
  const url = new URL(`${API_BASE_URL}${path}`, window.location.origin)
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value !== undefined && value !== null && value !== '') {
      url.searchParams.set(key, value)
    }
  }

  let response
  try {
    response = await fetch(url, {
      headers: {
        Accept: 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    })
  } catch {
    throw new ApiError('서버에 연결할 수 없습니다. 백엔드 실행 상태를 확인해주세요.')
  }

  if (!response.ok) {
    if (response.status === 401) unauthorizedHandler?.()
    throw await readError(response, fallback ?? '요청을 처리하지 못했습니다.')
  }
  return response.json()
}

export async function login(email, password) {
  let response
  try {
    response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email: email.trim(), password }),
    })
  } catch {
    throw new ApiError('서버에 연결할 수 없습니다. 백엔드 실행 상태를 확인해주세요.')
  }

  if (!response.ok) {
    throw await readError(response, '로그인 요청을 처리하지 못했습니다.')
  }

  return response.json()
}

// ---------------------------------------------------------------------------
//  관제 — MLCM_501 · MLCM_510
//
//  전부 role == ADMIN 이 필요하다. 토큰은 유효한데 권한이 없으면 403 이다
//  (401 이 아니다 — 재로그인시켜도 해결되지 않으므로 구분해야 한다).
// ---------------------------------------------------------------------------

/** ❶ 위험도 분포. 사람 수 기준이며 사용자별 최신 평가 1건만 센다. */
export function fetchDashboard(token) {
  return request('/admin/dashboard', {
    token,
    fallback: '관제 현황을 불러오지 못했습니다.',
  })
}

/**
 * ❷ 대상자 목록.
 *
 * 아직 평가 이력이 없는 사용자도 포함된다(risk_level=null).
 * 관리자 입장에서 "분석된 적 없는 사람"도 관리 대상이다.
 *
 * `query` 는 이름·이메일 부분 일치 검색이며 위험도 필터와 AND 로 걸린다.
 * 서버가 LIKE 메타문자를 이스케이프하므로 클라이언트에서 가공하지 않는다.
 *
 * ⚠ 연락처로는 검색할 수 없다. AES-256-GCM 컬럼 암호화라 같은 값도 암호문이
 *   매번 달라 부분 일치가 성립하지 않는다(02-F 3항 · 안건 4).
 */
export function fetchUsers(
  token,
  { riskLevel, query, limit = 50, offset = 0 } = {},
) {
  return request('/admin/users', {
    token,
    // request() 가 빈 문자열을 알아서 빼므로 공백만 남은 검색어는 전체 조회가 된다.
    params: { risk_level: riskLevel, q: query?.trim(), limit, offset },
    fallback: '대상자 목록을 불러오지 못했습니다.',
  })
}

/** ❸ 개인 리포트. 본인 조회와 같은 산출 로직을 쓴다. */
export function fetchUserReport(token, userId) {
  return request(`/admin/users/${userId}/report`, {
    token,
    fallback: '리포트를 불러오지 못했습니다.',
  })
}

/** ❹ 위기 이력 — MLCM_510. CRITICAL 판정 기록. */
export function fetchEmergencyEvents(token, { limit = 50 } = {}) {
  return request('/admin/emergency-events', {
    token,
    params: { limit },
    fallback: '위기 이력을 불러오지 못했습니다.',
  })
}
