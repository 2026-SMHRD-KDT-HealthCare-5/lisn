const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
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
    let message = '로그인 요청을 처리하지 못했습니다.'
    try {
      const body = await response.json()
      if (typeof body.detail === 'string') message = body.detail
    } catch {
      // JSON이 아닌 오류 응답은 공통 문구를 사용한다.
    }
    throw new ApiError(message, response.status)
  }

  return response.json()
}
