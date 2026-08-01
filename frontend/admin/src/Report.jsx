/**
 * ❸ 대상자 상세 — MLCM_501 3·4단계 · ADMIN_DASH_01
 *
 * `GET /admin/users/{id}/report` 는 본인 조회(`GET /reports`)와 **같은 스키마**를
 * 돌려줍니다. 서버가 같은 함수를 쓰므로 여기서 다시 계산할 것이 없습니다.
 *
 * ⚠ **앱 `MAIN_REPORT_01` 과 같은 시각화 규격을 씁니다**(`MLCM_501` 4단계).
 *   스택이 달라 컴포넌트를 공유할 수는 없으므로 아래 셋을 맞춥니다.
 *     1. 감정 곡선은 **0~100 고정 축**. 데이터 범위로 정규화하지 않습니다
 *     2. 위험 단계 색은 안정 mint · 주의 blue · 심각 peach
 *     3. 점 색은 서버가 준 risk_level 로 칠합니다. 점수로 다시 판정하지 않습니다
 *   앱의 `report_screen.dart` 를 고치면 여기도 함께 보세요.
 */
import { useEffect, useState } from 'react'

import { fetchUserReport } from './api.js'
import { RISK_LABEL } from './labels.js'

/** 앱 `_TrendPainter._levelColor` 와 같은 값이어야 합니다. */
const LEVEL_COLOR = {
  NORMAL: '#5b8d83',
  CAUTION: '#6289b1',
  CRITICAL: '#987466',
}

const LINE = '#7890ef'

function stampDay(value) {
  if (!value) return '—'
  const d = new Date(value)
  return `${d.getMonth() + 1}.${d.getDate()}`
}

/**
 * ❷ 감정 변화 곡선.
 *
 * ⚠ y 축을 데이터 범위에 맞추지 마세요. 62~65 사이의 미미한 흔들림이 화면
 *   가득한 급등락으로 보입니다. 정서 상태를 읽는 화면에서 그건 오독을 만듭니다.
 */
function TrendChart({ points }) {
  if (points.length < 2) {
    return <p className="chart-empty">곡선을 그리려면 기록이 2일 이상 필요합니다.</p>
  }

  const w = 640
  const h = 150
  const pad = 8
  const x = (i) => (w * i) / (points.length - 1)
  const y = (score) => pad + (h - pad * 2) * (1 - Math.min(Math.max(score, 0), 100) / 100)

  const line = points.map((p, i) => `${i ? 'L' : 'M'}${x(i)},${y(p.emotion_score)}`).join(' ')
  const area = `${line} L${w},${h} L0,${h} Z`

  return (
    <>
      <svg
        className="trend-chart"
        viewBox={`0 0 ${w} ${h}`}
        preserveAspectRatio="none"
        role="img"
        aria-label={`감정 변화 곡선, ${points.length}개 지점`}
      >
        <defs>
          <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={LINE} stopOpacity="0.30" />
            <stop offset="100%" stopColor={LINE} stopOpacity="0" />
          </linearGradient>
        </defs>
        {/* 0·50·100 눈금. 고정 축임을 눈으로 알 수 있어야 합니다. */}
        {[0, 50, 100].map((v) => (
          <line key={v} x1="0" x2={w} y1={y(v)} y2={y(v)} stroke="#eef0f7" strokeWidth="1" />
        ))}
        <path d={area} fill="url(#trendFill)" />
        <path d={line} fill="none" stroke={LINE} strokeWidth="2.5" strokeLinecap="round" />
        {points.map((p, i) => (
          <circle
            key={p.evaluated_at + i}
            cx={x(i)}
            cy={y(p.emotion_score)}
            r="3.5"
            fill={LEVEL_COLOR[p.risk_level] ?? LEVEL_COLOR.CAUTION}
          />
        ))}
      </svg>
      <div className="chart-axis">
        <span>{stampDay(points[0].evaluated_at)}</span>
        <span className="muted">감정 스코어 0–100 고정 축</span>
        <span>{stampDay(points[points.length - 1].evaluated_at)}</span>
      </div>
    </>
  )
}

/** ❸ 위험 단계 분포 */
function Distribution({ distribution }) {
  const rows = [
    ['안정', distribution.normal, 'mint'],
    ['주의', distribution.caution, 'blue'],
    ['심각', distribution.critical, 'peach'],
  ]
  const total = rows.reduce((sum, [, n]) => sum + n, 0)

  return (
    <div className="dist-rows">
      {rows.map(([label, count, tone]) => (
        <div className="dist-row" key={label}>
          <span className="dist-label">{label}</span>
          <div className="dist-track">
            <div
              className={`dist-bar ${tone}`}
              style={{ width: total ? `${(count / total) * 100}%` : '0%' }}
            />
          </div>
          <span className={`dist-count ${tone}`}>{count}회</span>
        </div>
      ))}
    </div>
  )
}

/**
 * ❹ 라이프로그 결합.
 *
 * 감정 추이와 **같은 시간축**에 겹치는 것이 명세지만, 단위가 달라 한 좌표계에
 * 그리면 둘 다 못 읽습니다. 같은 기간의 요약값을 나란히 두는 것으로 갈음합니다.
 *
 * ⚠ 값이 없으면 0 이 아니라 「측정 안 됨」입니다. 0 으로 채우면 「안 걸었다」와
 *   「수집이 안 됐다」가 구분되지 않습니다.
 */
function LifelogSummary({ points }) {
  if (points.length === 0) {
    return <p className="chart-empty">같은 기간의 라이프로그 기록이 없습니다.</p>
  }

  const avg = (key) => {
    const values = points.map((p) => p[key]).filter((v) => v !== null && v !== undefined)
    if (values.length === 0) return null
    return values.reduce((a, b) => a + Number(b), 0) / values.length
  }

  const cells = [
    ['평균 수면', avg('total_sleep_min'), (v) => `${Math.floor(v / 60)}시간 ${Math.round(v % 60)}분`],
    ['평균 걸음', avg('steps'), (v) => `${Math.round(v).toLocaleString()}보`],
    ['평균 심박', avg('heart_rate'), (v) => `${Math.round(v)} bpm`],
    ['평균 HRV', avg('hrv'), (v) => `${v.toFixed(1)} ms`],
  ]

  return (
    <div className="lifelog-grid">
      {cells.map(([label, value, format]) => (
        <div className="lifelog-cell" key={label}>
          <small>{label}</small>
          <strong>{value === null ? '측정 안 됨' : format(value)}</strong>
        </div>
      ))}
    </div>
  )
}

/** 대상자 상세 패널. 목록에서 한 명을 고르면 열립니다. */
export default function UserReport({ token, user, onClose }) {
  const [report, setReport] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let alive = true
    setReport(null)
    setError('')
    fetchUserReport(token, user.user_id)
      .then((result) => alive && setReport(result))
      .catch((e) => alive && setError(e.message))
    return () => {
      alive = false
    }
  }, [token, user.user_id])

  return (
    <section className="detail-panel" aria-label={`${user.name} 상세`}>
      <header>
        <div>
          <strong>{user.name}</strong>
          <small className="muted">{user.email}</small>
        </div>
        <button type="button" className="chip" onClick={onClose}>
          닫기
        </button>
      </header>

      {error ? (
        <p className="chart-empty">{error}</p>
      ) : !report ? (
        <p className="chart-empty">불러오는 중...</p>
      ) : report.emotion_trend.length === 0 ? (
        /* 서버는 분석 이력이 없어도 200 에 빈 배열을 돌려줍니다.
           「위험이 없다」가 아니라 「아직 모른다」이므로 그대로 적습니다. */
        <p className="chart-empty">
          아직 분석된 기록이 없습니다. 라이프로그가 쌓이면 표시됩니다.
        </p>
      ) : (
        <>
          <h4>감정 변화</h4>
          <TrendChart points={report.emotion_trend} />

          <h4>위험 단계 분포</h4>
          <Distribution distribution={report.distribution} />

          <h4>라이프로그</h4>
          <LifelogSummary points={report.lifelog_trend} />

          <h4>종합</h4>
          {/* 서버가 만든 문구를 그대로 씁니다. 여기서 다시 쓰면 본인 화면과
              관리자 화면의 표현이 갈립니다(FR-AI-002 진단 금지도 서버 책임). */}
          <p className="summary-text">{report.summary}</p>

          <p className="hint">
            최근 판정 {report.emotion_trend.length}회 ·{' '}
            {stampDay(report.date_from)} ~ {stampDay(report.date_to)}
            {user.risk_level && ` · 현재 ${RISK_LABEL[user.risk_level]}`}
          </p>
        </>
      )}
    </section>
  )
}
