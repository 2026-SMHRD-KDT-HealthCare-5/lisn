import { useEffect, useState } from 'react'
import {
  fetchDashboard,
  fetchEmergencyEvents,
  fetchUsers,
  login,
} from './api.js'
import { clearSession, readSession, saveAdminSession } from './session.js'

/**
 * 관리자 웹의 서비스명은 **귀기울임(LISN)** 입니다.
 *
 * '마음이'를 쓰지 않습니다. 그건 사용자 앱 안의 캐릭터 명칭이고(SD-03 확정),
 * 여기는 캐릭터가 등장하지 않는 관제 도구입니다. 사용자도 대상자가 아니라
 * 팀 담당자입니다. 산출물 5종과 발표자료도 전부 '귀기울임(LISN)'을 씁니다.
 */
function Brand({ admin = false }) {
  return (
    <div className="brand">
      귀기울임 <span>LISN</span>
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

const RISK_LABEL = { NORMAL: '안정', CAUTION: '주의', CRITICAL: '심각' }
const RISK_TONE = { NORMAL: 'mint', CAUTION: 'blue', CRITICAL: 'peach' }

function stamp(value) {
  if (!value) return '—'
  const d = new Date(value)
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  return d.getMonth() + 1 + '.' + d.getDate() + ' ' + hh + ':' + mm
}

function LoadingPanel() {
  return (
    <div className="empty-dashboard">
      <p>불러오는 중...</p>
    </div>
  )
}

function NoticePanel({ text }) {
  return (
    <div className="empty-dashboard">
      <div className="empty-icon">⌁</div>
      <p>{text}</p>
    </div>
  )
}

/**
 * ❶ 위험도 분포 — MLCM_501 2단계
 *
 * 분포는 사람 수 기준이다. 사용자별 최신 평가 1건만 세므로 자주 측정한
 * 사용자가 분포를 왜곡하지 않는다.
 */
function OverviewTab({ token }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let alive = true
    fetchDashboard(token)
      .then((result) => alive && setData(result))
      .catch((e) => alive && setError(e.message))
    return () => {
      alive = false
    }
  }, [token])

  if (error) return <NoticePanel text={error} />
  if (!data) return <LoadingPanel />

  const cards = [
    ['안정 대상자', data.distribution.normal, 'mint'],
    ['주의 대상자', data.distribution.caution, 'blue'],
    ['심각 대상자', data.distribution.critical, 'peach'],
  ]
  const notEvaluated = data.total_users - data.evaluated_users

  return (
    <>
      <div className="metric-grid">
        {cards.map(([label, value, tone]) => (
          <article className="metric-card" key={label}>
            <div>
              <small>{label}</small>
              <strong>{value}</strong>
            </div>
            <span className={tone}>
              {data.evaluated_users
                ? Math.round((value / data.evaluated_users) * 100) + '%'
                : '—'}
            </span>
          </article>
        ))}
      </div>
      <p className="hint">
        전체 {data.total_users}명 중 {data.evaluated_users}명 평가 완료 · 기준
        시각 {stamp(data.generated_at)}
      </p>
      {notEvaluated > 0 && (
        <p className="hint">
          미평가 {notEvaluated}명은 아직 라이프로그가 쌓이지 않은
          대상자입니다. 위험이 없다는 뜻이 아니므로 「대상자 조회」에서 함께
          확인하세요.
        </p>
      )}
    </>
  )
}

/** 검색어 입력이 멎을 때까지 기다린다. 글자마다 요청하면 관제 목록처럼
 *  응답이 큰 조회에서 앞선 요청이 뒤늦게 도착해 결과가 뒤집힌다. */
function useDebounced(value, delay = 250) {
  const [settled, setSettled] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setSettled(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])
  return settled
}

/** ❷ 대상자 목록 — 심각 → 주의 → 안정 순으로 내려온다 */
function PeopleTab({ token }) {
  const [rows, setRows] = useState(null)
  const [error, setError] = useState('')
  const [filter, setFilter] = useState('')
  const [keyword, setKeyword] = useState('')
  const query = useDebounced(keyword)
  const searching = query.trim().length > 0

  useEffect(() => {
    let alive = true
    setRows(null)
    setError('')
    fetchUsers(token, { riskLevel: filter || undefined, query })
      .then((result) => alive && setRows(result))
      .catch((e) => alive && setError(e.message))
    return () => {
      alive = false
    }
  }, [token, filter, query])

  return (
    <>
      <div className="filter-row">
        {['', 'CRITICAL', 'CAUTION', 'NORMAL'].map((level) => (
          <button
            key={level || 'ALL'}
            className={filter === level ? 'chip active' : 'chip'}
            onClick={() => setFilter(level)}
          >
            {level ? RISK_LABEL[level] : '전체'}
          </button>
        ))}

        <div className="search-box">
          <span aria-hidden="true">⌕</span>
          <input
            type="search"
            value={keyword}
            maxLength={100}
            placeholder="이름 또는 이메일"
            aria-label="대상자 검색"
            onChange={(event) => setKeyword(event.target.value)}
          />
          {keyword && (
            <button
              type="button"
              className="search-clear"
              aria-label="검색어 지우기"
              onClick={() => setKeyword('')}
            >
              ×
            </button>
          )}
        </div>
      </div>

      {rows && rows.length > 0 && (
        <p className="hint">
          {searching
            ? `"${query.trim()}" 검색 결과 ${rows.length}명`
            : `${rows.length}명`}
          {filter && ` · ${RISK_LABEL[filter]} 필터 적용 중`}
        </p>
      )}

      {error ? (
        <NoticePanel text={error} />
      ) : !rows ? (
        <LoadingPanel />
      ) : rows.length === 0 ? (
        /* 검색 결과 없음과 필터 결과 없음을 구분한다. 같은 문구를 쓰면
           검색어를 고쳐야 하는지 필터를 풀어야 하는지 알 수 없다. */
        <NoticePanel
          text={
            searching
              ? `"${query.trim()}"에 해당하는 대상자가 없습니다.` +
                (filter ? ` ${RISK_LABEL[filter]} 필터를 풀고 다시 찾아보세요.` : '')
              : '해당하는 대상자가 없습니다.'
          }
        />
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>이름</th>
              <th>이메일</th>
              <th>위험도</th>
              <th>감정</th>
              <th>평가 시각</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.user_id}>
                <td>{row.name}</td>
                <td className="muted">{row.email}</td>
                <td>
                  {/* 평가 이력이 없으면 '안정'이 아니라 '미평가'다.
                      없는 것을 정상으로 표시하면 위험을 놓친다. */}
                  <span
                    className={row.risk_level ? RISK_TONE[row.risk_level] : 'muted'}
                  >
                    {row.risk_level ? RISK_LABEL[row.risk_level] : '미평가'}
                  </span>
                </td>
                <td className="muted">{row.emotion_code ?? '—'}</td>
                <td className="muted">{stamp(row.evaluated_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  )
}

/** ❹ 위기 사건 이력 — MLCM_510 */
function EventsTab({ token }) {
  const [rows, setRows] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let alive = true
    fetchEmergencyEvents(token)
      .then((result) => alive && setRows(result))
      .catch((e) => alive && setError(e.message))
    return () => {
      alive = false
    }
  }, [token])

  if (error) return <NoticePanel text={error} />
  if (!rows) return <LoadingPanel />
  if (rows.length === 0)
    return <NoticePanel text="기록된 위기 사건이 없습니다." />

  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>이름</th>
          <th>감정</th>
          <th>위험 점수</th>
          <th>판정 시각</th>
          <th>모델</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.score_id}>
            <td>{row.name}</td>
            <td>{row.emotion_code}</td>
            <td>{Number(row.risk_score).toFixed(1)}</td>
            <td className="muted">{stamp(row.evaluated_at)}</td>
            {/* rule-placeholder 면 모델 결과가 아니다. 화면에서 구분돼야
                이 수치를 성능 근거로 쓰는 사고를 막는다. */}
            <td className="muted">{row.model_version}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

const TABS = [
  [
    'dashboard',
    '관제 대시보드',
    '전체 대상자의 최근 정서 위험 신호를 확인합니다.',
  ],
  [
    'people',
    '대상자 조회',
    '위험도로 좁히거나 이름·이메일로 검색합니다.',
  ],
  ['events', '위기 사건 이력', 'CRITICAL 로 판정된 기록입니다.'],
]

function Dashboard({ session, onLogout }) {
  const [tab, setTab] = useState('dashboard')
  const token = session.access_token
  const active = TABS.find(([key]) => key === tab)

  return (
    <div className="dashboard-layout">
      <aside>
        <Brand />
        <nav>
          {TABS.map(([key, label]) => (
            <a
              key={key}
              className={tab === key ? 'active' : undefined}
              href={'#' + key}
              onClick={() => setTab(key)}
            >
              {label}
            </a>
          ))}
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
            <h1>{active[1]}</h1>
            <p>{active[2]}</p>
          </div>
          <button className="logout-button" onClick={onLogout}>
            로그아웃
          </button>
        </header>
        {tab === 'dashboard' && <OverviewTab token={token} />}
        {tab === 'people' && <PeopleTab token={token} />}
        {tab === 'events' && <EventsTab token={token} />}
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
