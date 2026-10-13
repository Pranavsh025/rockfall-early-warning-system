import { useEffect, useRef, useState } from 'react'
import { api, wsUrl } from '../api'

/** Live mine summaries + alerts pushed by the backend monitoring agent. */
export function useLiveFeed() {
  const [mines, setMines] = useState([])
  const [alerts, setAlerts] = useState([])
  const [connected, setConnected] = useState(false)
  const [lastTick, setLastTick] = useState(null)
  const [freshAlert, setFreshAlert] = useState(null)
  const wsRef = useRef(null)

  useEffect(() => {
    api.mines().then(setMines).catch(() => {})
    api.alerts().then(setAlerts).catch(() => {})

    let closed = false
    let retry
    const connect = () => {
      const ws = new WebSocket(wsUrl('/ws/alerts'))
      wsRef.current = ws
      ws.onopen = () => setConnected(true)
      ws.onclose = () => {
        setConnected(false)
        if (!closed) retry = setTimeout(connect, 3000)
      }
      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data)
        if (msg.type === 'tick') {
          setMines(msg.mines)
          setLastTick(new Date())
        } else if (msg.type === 'alert') {
          setAlerts((a) => [msg.alert, ...a].slice(0, 100))
          setFreshAlert(msg.alert)
        }
      }
    }
    connect()
    return () => {
      closed = true
      clearTimeout(retry)
      wsRef.current?.close()
    }
  }, [])

  return { mines, alerts, connected, lastTick, freshAlert, dismissFresh: () => setFreshAlert(null) }
}
