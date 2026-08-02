import assert from 'node:assert/strict'
import test from 'node:test'

globalThis.window = { location: { origin: 'http://localhost:5173' } }

const { fetchDashboard, setUnauthorizedHandler, ApiError } = await import('./api.js')

function stubFetch(status, body = {}) {
  globalThis.fetch = async () => ({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  })
}

test.afterEach(() => {
  setUnauthorizedHandler(null)
})

// ⚠ 이 처리가 없으면 탭을 열어둔 채 토큰이 만료됐을 때 모든 조회가 401 로
//   실패하면서 「불러오지 못했습니다」만 반복됩니다. 세션이 남아 있어 로그인
//   화면으로도 안 가므로 사용자는 서버가 죽은 줄 압니다.
test('401 이면 세션 만료 처리를 부른다', async () => {
  let called = 0
  setUnauthorizedHandler(() => {
    called += 1
  })
  stubFetch(401, { detail: '토큰이 만료되었습니다' })

  await assert.rejects(() => fetchDashboard('stale-token'), ApiError)
  assert.equal(called, 1)
})

// ⚠ 403 은 권한이 없는 것이라 재로그인해도 해결되지 않습니다. 여기서 세션을
//   버리면 일반 사용자 토큰으로 들어온 사람이 로그인 화면을 무한히 반복합니다.
test('403 은 세션을 버리지 않는다', async () => {
  let called = 0
  setUnauthorizedHandler(() => {
    called += 1
  })
  stubFetch(403, { detail: '관리자 권한이 필요합니다' })

  await assert.rejects(() => fetchDashboard('user-token'), ApiError)
  assert.equal(called, 0)
})

test('정상 응답은 만료 처리를 부르지 않는다', async () => {
  let called = 0
  setUnauthorizedHandler(() => {
    called += 1
  })
  stubFetch(200, { total_users: 3 })

  const body = await fetchDashboard('good-token')
  assert.equal(body.total_users, 3)
  assert.equal(called, 0)
})

test('핸들러가 없어도 401 에서 터지지 않는다', async () => {
  stubFetch(401, { detail: '토큰이 만료되었습니다' })
  await assert.rejects(() => fetchDashboard('stale-token'), ApiError)
})
