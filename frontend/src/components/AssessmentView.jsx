import { useCallback, useEffect, useState } from 'react'
import { X } from 'lucide-react'
import { api, downloadBlob } from '../api'
import MapCanvas from './MapCanvas'
import MineSelect from './MineSelect'
import NewAssessmentModal from './NewAssessmentModal'
import { RiskDetails, RiskSummary } from './RiskCard'

export default function AssessmentView({ mines, lastTick, selectedId, setSelectedId }) {
  const [assessment, setAssessment] = useState(null)
  const [custom, setCustom] = useState(null) // { input, result }
  const [modalOpen, setModalOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const load = useCallback(() => {
    if (!selectedId) return
    api.assessment(selectedId).then(setAssessment).catch((e) => setError(String(e)))
  }, [selectedId])

  useEffect(load, [load, lastTick]) // refresh whenever the agent publishes a new tick

  const selectMine = (id) => {
    setCustom(null)
    setSelectedId(id)
  }

  const shown = custom?.result || assessment

  const generateReport = async () => {
    setBusy(true)
    try {
      if (custom) downloadBlob(await api.customReport(custom.input), 'rockfall_report_custom.pdf')
      else downloadBlob(await api.mineReport(selectedId), `rockfall_report_${selectedId}.pdf`)
    } catch (e) {
      setError(String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="assessment-view">
      <div className="map-bg">
        <MapCanvas mines={mines} selectedId={selectedId} interactive={false} />
        <div className="map-veil" />
      </div>

      <div className="content">
        <header className="page-title">
          <h1>Risk Assessment Dashboard</h1>
          <p>Real-time Geological Hazard Analysis</p>
        </header>

        <MineSelect mines={mines} value={custom ? null : selectedId} onChange={selectMine} />

        {error && <div className="error" onClick={() => setError('')}>{error}</div>}

        {custom && (
          <div className="custom-chip">
            Showing custom assessment <button onClick={() => setCustom(null)}><X size={12} /> back to live mines</button>
          </div>
        )}

        {shown ? (
          <>
            <RiskSummary a={shown} />
            <RiskDetails a={shown} />
            <div className="actions">
              <button className="btn btn-light" onClick={() => setModalOpen(true)}>New Assessment</button>
              <button className="btn btn-primary" onClick={generateReport} disabled={busy}>
                {busy ? 'Generating…' : 'Generate Report'}
              </button>
            </div>
          </>
        ) : (
          <div className="card loading">Connecting to the prediction service…</div>
        )}
      </div>

      {modalOpen && (
        <NewAssessmentModal
          onClose={() => setModalOpen(false)}
          onResult={(input, result) => {
            setCustom({ input, result })
            setModalOpen(false)
            window.scrollTo({ top: 0, behavior: 'smooth' })
          }}
        />
      )}
    </div>
  )
}
