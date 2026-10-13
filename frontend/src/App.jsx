import { useEffect, useState } from 'react'
import { BellRing, Gauge, Map, X } from 'lucide-react'
import { useLiveFeed } from './hooks/useLiveFeed'
import AssessmentView from './components/AssessmentView'
import MonitorView from './components/MonitorView'

export default function App() {
  const { mines, alerts, connected, lastTick, freshAlert, dismissFresh } = useLiveFeed()
  const [tab, setTab] = useState('assessment')
  const [selectedId, setSelectedId] = useState(null)

  useEffect(() => {
    if (!selectedId && mines.length) setSelectedId(mines[0].id)
  }, [mines, selectedId])

  useEffect(() => {
    if (!freshAlert) return
    const t = setTimeout(dismissFresh, 7000)
    return () => clearTimeout(t)
  }, [freshAlert, dismissFresh])

  return (
    <div className="app">
      <nav className="topnav">
        <div className="brand">⛰️ RockGuard <span>Early Warning</span></div>
        <div className="tabs">
          <button className={tab === 'assessment' ? 'on' : ''} onClick={() => setTab('assessment')}><Gauge size={15} /> Assessment</button>
          <button className={tab === 'monitor' ? 'on' : ''} onClick={() => setTab('monitor')}><Map size={15} /> Live Monitor</button>
        </div>
        <div className="status"><span className={`live-dot ${connected ? 'on' : ''}`} />{connected ? 'Live' : 'Offline'}</div>
      </nav>

      {tab === 'assessment' ? (
        <AssessmentView mines={mines} lastTick={lastTick} selectedId={selectedId} setSelectedId={setSelectedId} />
      ) : (
        <MonitorView
          mines={mines}
          alerts={alerts}
          connected={connected}
          lastTick={lastTick}
          selectedId={selectedId}
          setSelectedId={setSelectedId}
          openAssessment={() => setTab('assessment')}
        />
      )}

      {freshAlert && (
        <div className={`toast toast-${freshAlert.severity}`}>
          <BellRing size={16} />
          <div>
            <b>{freshAlert.mine_name}</b>
            <div>{freshAlert.message} · {freshAlert.score.toFixed(1)}%</div>
          </div>
          <button className="icon-btn" onClick={dismissFresh} aria-label="Dismiss"><X size={14} /></button>
        </div>
      )}
    </div>
  )
}
