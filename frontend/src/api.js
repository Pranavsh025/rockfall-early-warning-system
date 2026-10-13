const BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')

async function request(path, opts = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  })
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`)
  return res
}

export const api = {
  mines: () => request('/api/mines').then((r) => r.json()),
  assessment: (id) => request(`/api/mines/${id}/assessment`).then((r) => r.json()),
  rainfall: (id) => request(`/api/mines/${id}/rainfall`).then((r) => r.json()),
  alerts: () => request('/api/alerts').then((r) => r.json()),
  modelInfo: () => request('/api/model/info').then((r) => r.json()),
  predict: (body) => request('/api/predict', { method: 'POST', body: JSON.stringify(body) }).then((r) => r.json()),
  mineReport: (id) => request(`/api/mines/${id}/report`).then((r) => r.blob()),
  customReport: (body) => request('/api/report', { method: 'POST', body: JSON.stringify(body) }).then((r) => r.blob()),
}

export function wsUrl(path) {
  if (BASE) return BASE.replace(/^http/, 'ws') + path
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${window.location.host}${path}`
}

export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export const LEVEL_COLORS = {
  LOW: '#2f8f4e',
  MODERATE: '#d68a1a',
  HIGH: '#e03c31',
  CRITICAL: '#8e1b14',
}

export const levelForScore = (s) => (s >= 85 ? 'CRITICAL' : s >= 60 ? 'HIGH' : s >= 35 ? 'MODERATE' : 'LOW')
