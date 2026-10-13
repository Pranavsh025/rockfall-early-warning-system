import { useEffect, useMemo, useState } from 'react'
import { Bar, CartesianGrid, ComposedChart, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, ReferenceLine } from 'recharts'
import { Activity, AlertTriangle, BellRing, CloudRain, Mountain, Radar } from 'lucide-react'
import { api, LEVEL_COLORS } from '../api'
import MapCanvas from './MapCanvas'

const timeAgo = (iso) => {
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000)
  if (s < 60) return `${Math.round(s)}s ago`
  if (s < 3600) return `${Math.round(s / 60)}m ago`
  return `${Math.round(s / 3600)}h ago`
}

export default function MonitorView({ mines, alerts, connected, lastTick, selectedId, setSelectedId, openAssessment }) {
  const [rain, setRain] = useState([])
  const [detail, setDetail] = useState(null)
  const selected = mines.find((m) => m.id === selectedId)

  useEffect(() => {
    if (selectedId) api.rainfall(selectedId).then(setRain).catch(() => {})
  }, [selectedId])

  useEffect(() => {
    if (selectedId) api.assessment(selectedId).then(setDetail).catch(() => {})
  }, [selectedId, lastTick])

  const stats = useMemo(() => ({
    total: mines.length,
    high: mines.filter((m) => m.risk_level === 'HIGH' || m.risk_level === 'CRITICAL').length,
    avg: mines.length ? mines.reduce((s, m) => s + m.overall_score, 0) / mines.length : 0,
    alerts24: alerts.filter((a) => Date.now() - new Date(a.timestamp) < 864e5).length,
  }), [mines, alerts])

  const history = (detail?.history || []).map((h) => ({
    t: new Date(h.t).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
    score: h.score,
  }))

  return (
    <div className="monitor-view">
      <header className="page-title compact">
        <h1>Live Mine Monitor</h1>
        <p>
          <span className={`live-dot ${connected ? 'on' : ''}`} /> Monitoring agent {connected ? 'online' : 'reconnecting…'}
          {lastTick && <> · last update {lastTick.toLocaleTimeString()}</>}
        </p>
      </header>

      <div className="kpis">
        <div className="card kpi"><Mountain size={18} /><div><strong>{stats.total}</strong><span>Mines monitored</span></div></div>
        <div className="card kpi"><AlertTriangle size={18} color={LEVEL_COLORS.HIGH} /><div><strong>{stats.high}</strong><span>High / critical risk</span></div></div>
        <div className="card kpi"><Activity size={18} /><div><strong>{stats.avg.toFixed(1)}%</strong><span>Average risk</span></div></div>
        <div className="card kpi"><BellRing size={18} /><div><strong>{stats.alerts24}</strong><span>Alerts (24 h)</span></div></div>
      </div>

      <div className="monitor-grid">
        <div className="card map-card">
          <MapCanvas mines={mines} selectedId={selectedId} onSelect={setSelectedId} />
          <div className="legend">
            {Object.entries(LEVEL_COLORS).map(([k, c]) => <span key={k}><i style={{ background: c }} />{k}</span>)}
            <span className="muted">Zoom in to see slope zones</span>
          </div>
        </div>

        <div className="card panel alerts-panel">
          <h3><Radar size={18} /> Live Risk Alerts</h3>
          <div className="alert-list">
            {alerts.length === 0 && <p className="muted small">No alerts yet — the agent checks every few seconds.</p>}
            {alerts.map((a) => (
              <button key={a.id} className={`alert alert-${a.severity}`} onClick={() => setSelectedId(a.mine_id)}>
                <div className="alert-top">
                  <b>{a.mine_name}</b>
                  <span className="muted">{timeAgo(a.timestamp)}</span>
                </div>
                <div>{a.message}</div>
                <div className="muted small">
                  {a.score.toFixed(1)}% · driver: {a.driver} · {a.action}
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="monitor-grid lower">
        <div className="card panel">
          <h3><CloudRain size={18} /> Rainfall Trend — {selected?.name || '…'}</h3>
          <ResponsiveContainer width="100%" height={240}>
            <ComposedChart data={rain} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
              <CartesianGrid stroke="#e6d8c6" vertical={false} />
              <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#7a5c41' }} />
              <YAxis tick={{ fontSize: 11, fill: '#7a5c41' }} unit=" mm" width={64} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="rainfall" name="Rainfall" fill="#c98a5b" radius={[4, 4, 0, 0]} />
              <Line dataKey="normal" name="Long-term normal" stroke="#5c3317" strokeWidth={2} dot={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>

        <div className="card panel">
          <h3><Activity size={18} /> Risk Score — live</h3>
          {detail && (
            <div className="mini-summary">
              <span className={`badge badge-${detail.risk_level.toLowerCase()}`}>{detail.risk_level}</span>
              <strong>{detail.overall_score.toFixed(1)}%</strong>
              <button className="btn btn-light small" onClick={openAssessment}>Open full assessment</button>
            </div>
          )}
          <ResponsiveContainer width="100%" height={190}>
            <LineChart data={history} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid stroke="#e6d8c6" vertical={false} />
              <XAxis dataKey="t" tick={{ fontSize: 10, fill: '#7a5c41' }} minTickGap={30} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: '#7a5c41' }} />
              <Tooltip />
              <ReferenceLine y={60} stroke={LEVEL_COLORS.HIGH} strokeDasharray="4 4" />
              <ReferenceLine y={35} stroke={LEVEL_COLORS.MODERATE} strokeDasharray="4 4" />
              <Line dataKey="score" stroke="#5c3317" strokeWidth={2} dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
