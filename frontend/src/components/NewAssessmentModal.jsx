import { useState } from 'react'
import { X } from 'lucide-react'
import { api } from '../api'

const today = new Date().toISOString().slice(0, 10)

const NUMBER_FIELDS = [
  ['slope_angle', 'Slope angle', '°', 0, 90, 1],
  ['annual_rainfall', 'Annual rainfall', 'mm', 0, 6000, 10],
  ['soil_moisture', 'Soil moisture', '%', 0, 100, 0.1],
  ['pore_pressure', 'Pore pressure', 'kPa', 0, 500, 1],
  ['seismic_activity', 'Seismic activity', 'mag', 0, 9, 0.01],
  ['crack_width', 'Crack width', 'mm', 0, 200, 0.1],
  ['displacement_rate', 'Displacement rate', 'mm/day', 0, 100, 0.1],
  ['human_impact', 'Human impact', '0–10', 0, 10, 0.5],
]

export default function NewAssessmentModal({ onClose, onResult }) {
  const [form, setForm] = useState({
    mine_name: 'New Site',
    location: '',
    slope_angle: 45,
    vegetation: 'sparse',
    soil_type: 'mixed',
    annual_rainfall: 1200,
    soil_moisture: 28,
    pore_pressure: 90,
    seismic_activity: 1.5,
    crack_width: 8,
    displacement_rate: 2.5,
    human_impact: 4,
    last_blasting: today,
  })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.type === 'number' ? Number(e.target.value) : e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const input = { ...form, location: form.location || '—' }
      onResult(input, await api.predict(input))
    } catch (err) {
      setError(String(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <form className="modal card" onClick={(e) => e.stopPropagation()} onSubmit={submit}>
        <div className="modal-head">
          <h3>New Assessment</h3>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Close"><X size={18} /></button>
        </div>
        <p className="muted small">Enter field or sensor readings for a slope sector. The hybrid model (RF + XGBoost + Naïve Bayes fused with Fuzzy AHP) returns the risk score.</p>
        <div className="form-grid">
          <label>Site name<input value={form.mine_name} onChange={set('mine_name')} required /></label>
          <label>Location<input value={form.location} onChange={set('location')} placeholder="District" /></label>
          {NUMBER_FIELDS.map(([k, label, unit, min, max, step]) => (
            <label key={k}>{label} <em>{unit}</em>
              <input type="number" min={min} max={max} step={step} value={form[k]} onChange={set(k)} required />
            </label>
          ))}
          <label>Vegetation
            <select value={form.vegetation} onChange={set('vegetation')}>
              {['dense', 'moderate', 'sparse', 'barren'].map((v) => <option key={v}>{v}</option>)}
            </select>
          </label>
          <label>Soil type
            <select value={form.soil_type} onChange={set('soil_type')}>
              {['rocky', 'loamy', 'mixed', 'sandy', 'clay'].map((v) => <option key={v}>{v}</option>)}
            </select>
          </label>
          <label>Last blasting<input type="date" value={form.last_blasting} max={today} onChange={set('last_blasting')} /></label>
        </div>
        {error && <div className="error">{error}</div>}
        <div className="actions">
          <button type="button" className="btn btn-light" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" disabled={busy}>{busy ? 'Assessing…' : 'Run Assessment'}</button>
        </div>
      </form>
    </div>
  )
}
