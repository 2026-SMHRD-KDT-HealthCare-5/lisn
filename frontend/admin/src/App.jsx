import { useState } from 'react'
import { login } from './api.js'
import { clearSession, readSession, saveAdminSession } from './session.js'

function Brand({ admin = false }) {
  return (
    <div className="brand">
      마음이 <span>♥</span>
      {admin && <small>ADMIN</small>}
    </div>
  )
}

function FeatureCard({ title, children }) {
  return (
    <div className="feature-card">
      <strong>{title}</strong>
      <p>{children}</p>
    </div>
  )
}

function LoginPage({ onAuthenticated }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    if (loading) return
    setError('')
    setLoading(true)
    try {
      const session = await login(email, password)
      if (session.user?.role !== 'ADMIN') {
        setError('관리자 권한이 없는 계정입니다.')
        return
      }
      saveAdminSession(session)
      onAuthenticated(session)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="login-layout">
      <section className="login-visual">
        <Brand admin />
        <div className="visual-orb orb-one" />
        <div className="visual-orb orb-two" />
        <div className="hero-copy">
          <span className="eyebrow">LISN MONITORING</span>
          <h1>
            정서 위험 신호를
            <br />
            한눈에 살펴보세요
          </h1>
          <p>
            전체 대상자의 정서 위험도 흐름을 확인하고
            <br />
            도움이 필요한 대상을 빠르게 식별합니다.
          </p>
          <div className="feature-grid">
            <FeatureCard title="위험도 분포">안정·주의·심각 현황 요약</FeatureCard>
            <FeatureCard title="우선순위 목록">최근 평가 기반 대상자 정렬</FeatureCard>
            <FeatureCard title="상세 리포트">감정·라이프로그 통합 조회</FeatureCard>
          </div>
        </div>
        <span className="system-name">귀기울임(LISN) 관리자 관제 시스템</span>
      </section>

      <section className="login-panel">
        <form className="login-form" onSubmit={handleSubmit}>
          <h2>관리자 로그인</h2>
          <p className="form-description">
            관리자 권한이 있는 계정으로 로그인해주세요.
            <br />
            사용자 앱과 동일한 계정 인증 체계를 사용합니다.
          </p>
          <label htmlFor="email">이메일</label>
          <input
            id="email"
            type="email"
            autoComplete="username"
            placeholder="admin@example.com"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
          <label htmlFor="password">비밀번호</label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            placeholder="8자 이상 입력"
            minLength={8}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
          {error && (
            <div className="error-message" role="alert">
              {error}
            </div>
          )}
          <button type="submit" disabled={loading}>
            {loading ? '확인 중...' : '관제 대시보드로 이동'}
          </button>
          <div className="permission-note">
            <span>i</span>
            <p>
              <strong>권한 안내</strong>
              인증에 성공해도 관리자 권한이 없는 계정은 대시보드에 접근할
              수 없습니다.
            </p>
          </div>
          <small className="support">
            접근 문제가 지속되면 시스템 관리자에게 문의해주세요.
          </small>
        </form>
      </section>
    </main>
  )
}

function Dashboard({ session, onLogout }) {
  const cards = [
    ['안정 대상자', '—', '데이터 연결 대기', 'mint'],
    ['주의 대상자', '—', '데이터 연결 대기', 'blue'],
    ['심각 대상자', '—', '데이터 연결 대기', 'peach'],
  ]

  return (
    <div className="dashboard-layout">
      <aside>
        <Brand />
        <nav>
          <a className="active" href="#dashboard">
            관제 대시보드
          </a>
          <a href="#people">대상자 조회</a>
          <a href="#events">위기 사건 이력</a>
          <a href="#settings">시스템 설정</a>
        </nav>
        <div className="admin-profile">
          <span>AD</span>
          <div>
            <strong>{session.user.name}</strong>
            <small>ADMIN 권한</small>
          </div>
        </div>
      </aside>
      <section className="dashboard-main">
        <header>
          <div>
            <h1>관제 대시보드</h1>
            <p>전체 대상자의 최근 정서 위험 신호를 확인합니다.</p>
          </div>
          <button className="logout-button" onClick={onLogout}>
            로그아웃
          </button>
        </header>
        <div className="metric-grid">
          {cards.map(([label, value, caption, tone]) => (
            <article className="metric-card" key={label}>
              <div>
                <small>{label}</small>
                <strong>{value}</strong>
              </div>
              <span className={tone}>{caption}</span>
            </article>
          ))}
        </div>
        <div className="empty-dashboard">
          <div className="empty-icon">⌁</div>
          <h2>관리자 데이터 API 연결을 기다리고 있어요</h2>
          <p>
            로그인과 ADMIN 권한 검증은 완료됐습니다.
            <br />
            대상자·위험도·위기 사건 API가 구현되면 이 화면에 실제 데이터를
            연결합니다.
          </p>
        </div>
      </section>
    </div>
  )
}

export default function App() {
  const [session, setSession] = useState(readSession)

  function logout() {
    clearSession()
    setSession(null)
  }

  return session ? (
    <Dashboard session={session} onLogout={logout} />
  ) : (
    <LoginPage onAuthenticated={setSession} />
  )
}
