import { AlertTriangle, BarChart3, Droplets, MapPin, Radio, Shield, TrendingUp, Bomb, Activity } from 'lucide-react'

const COMPONENTS = [
  ['geological', 'Geological'],
  ['environmental', 'Environmental'],
  ['seismic', 'Seismic'],
  ['human_impact', 'Human Impact'],
]

const REC_ICONS = { warning: AlertTriangle, sensor: Radio, chart: BarChart3, water: Droplets, blast: Bomb, crack: Activity }

function formatDate(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  return isNaN(d) ? iso : d.toLocaleDateString('en-GB')
}

export function RiskSummary({ a }) {
  const level = a.risk_level
  return (
    <div className="card summary-card">
      <div className="summary-head">
        <h2><Shield size={22} strokeWidth={2.2} /> {a.mine.name}</h2>
        <p><MapPin size={12} /> {a.mine.location}</p>
      </div>
      <div className="summary-body">
        <span className={`badge badge-${level.toLowerCase()}`}>{level} RISK</span>
        <div className="score">{a.overall_score.toFixed(1)}%</div>
        <div className="score-label">Overall Risk Score</div>
        <div className="progress"><div style={{ width: `${Math.min(a.overall_score, 100)}%` }} /></div>
        <div className="tiles">
          {COMPONENTS.map(([k, label]) => (
            <div className="tile" key={k} title={`Fuzzy AHP weight ${a.criteria[k].weight}`}>
              <strong>{a.components[k].toFixed(1)}</strong>
              <span>{label}</span>
            </div>
          ))}
        </div>
        <div className="model-line">
          Hybrid score · ML ensemble (RF + XGBoost + NB) {(a.ml_probability * 100).toFixed(1)}% · Fuzzy AHP {a.fahp_score.toFixed(1)}
        </div>
      </div>
    </div>
  )
}

export function RiskDetails({ a }) {
  const e = a.environment
  return (
    <>
      <div className="detail-grid">
        <div className="card panel">
          <h3><TrendingUp size={18} /> Risk Factors Analysis</h3>
          {a.risk_factors.map((f) => (
            <div className="row" key={f.key}>
              <div className="row-head"><span>{f.label}</span><span className="muted">{f.level}</span></div>
              <div className="bar"><div style={{ width: `${Math.round(f.risk * 100)}%` }} /></div>
            </div>
          ))}
        </div>
        <div className="card panel">
          <h3><Droplets size={18} /> Environmental Conditions</h3>
          <div className="row">
            <div className="row-head"><span>Annual Rainfall</span><span className="muted">{e.annual_rainfall} mm</span></div>
            <div className="bar"><div style={{ width: `${Math.min((e.annual_rainfall / 2500) * 100, 100)}%` }} /></div>
          </div>
          <div className="row">
            <div className="row-head"><span>Soil Moisture</span><span className="muted">{e.soil_moisture}%</span></div>
            <div className="bar"><div style={{ width: `${Math.min(e.soil_moisture, 100)}%` }} /></div>
          </div>
          <div className="row">
            <div className="row-head"><span>Pore Pressure</span><span className="muted">{e.pore_pressure} kPa</span></div>
            <div className="bar"><div style={{ width: `${Math.min((e.pore_pressure / 250) * 100, 100)}%` }} /></div>
          </div>
          <div className="row-head plain"><span>Soil Type</span><span className="muted">{e.soil_type}</span></div>
          <div className="row-head plain"><span>Last Blasting</span><span className="muted">{formatDate(e.last_blasting)}</span></div>
        </div>
      </div>
      <div className="card panel">
        <h3><AlertTriangle size={18} /> Recommendations</h3>
        {a.recommendations.map((r) => {
          const Icon = REC_ICONS[r.icon] || BarChart3
          return (
            <div className={`rec rec-${r.severity}`} key={r.title}>
              <div className="rec-title"><Icon size={14} /> {r.title}</div>
              <div className="rec-detail">{r.detail}</div>
            </div>
          )
        })}
      </div>
    </>
  )
}
