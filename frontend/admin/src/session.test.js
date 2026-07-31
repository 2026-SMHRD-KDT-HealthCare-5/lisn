import assert from 'node:assert/strict'
import test from 'node:test'

const values = new Map()
globalThis.sessionStorage = {
  getItem: (key) => values.get(key) ?? null,
  setItem: (key, value) => values.set(key, value),
  removeItem: (key) => values.delete(key),
}

const { clearSession, readSession, saveAdminSession } = await import('./session.js')

test.beforeEach(() => {
  values.clear()
})

test('ADMIN 세션만 저장하고 복원한다', () => {
  const session = {
    access_token: 'token',
    expires_at: '2099-01-01T00:00:00Z',
    user: { role: 'ADMIN', name: '관리자' },
  }

  saveAdminSession(session)

  assert.deepEqual(readSession(), session)
})

test('일반 사용자 계정은 관리자 세션으로 저장하지 않는다', () => {
  assert.throws(
    () =>
      saveAdminSession({
        access_token: 'token',
        expires_at: '2099-01-01T00:00:00Z',
        user: { role: 'USER' },
      }),
    /관리자 권한/,
  )
  assert.equal(readSession(), null)
})

test('만료된 세션은 즉시 폐기한다', () => {
  sessionStorage.setItem(
    'lisn_admin_session',
    JSON.stringify({
      access_token: 'expired-token',
      expires_at: '2020-01-01T00:00:00Z',
      user: { role: 'ADMIN' },
    }),
  )

  assert.equal(readSession(), null)
  assert.equal(sessionStorage.getItem('lisn_admin_session'), null)
  clearSession()
})
