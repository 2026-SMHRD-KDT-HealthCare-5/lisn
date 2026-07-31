const SESSION_KEY = 'lisn_admin_session'

export function readSession() {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY)
    if (!raw) return null
    const session = JSON.parse(raw)
    if (
      session.user?.role !== 'ADMIN' ||
      !session.access_token ||
      new Date(session.expires_at).getTime() <= Date.now()
    ) {
      clearSession()
      return null
    }
    return session
  } catch {
    clearSession()
    return null
  }
}

export function saveAdminSession(session) {
  if (session.user?.role !== 'ADMIN') {
    throw new Error('관리자 권한이 없는 계정입니다.')
  }
  sessionStorage.setItem(SESSION_KEY, JSON.stringify(session))
}

export function clearSession() {
  sessionStorage.removeItem(SESSION_KEY)
}
