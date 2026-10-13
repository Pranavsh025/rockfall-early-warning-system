import { useEffect, useMemo, useRef, useState } from 'react'
import { Check, ChevronDown, Search } from 'lucide-react'
import { LEVEL_COLORS } from '../api'

/** Searchable dropdown to pick which mine to assess. */
export default function MineSelect({ mines, value, onChange }) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [active, setActive] = useState(0)
  const rootRef = useRef(null)
  const inputRef = useRef(null)

  const selected = mines.find((m) => m.id === value)
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return mines
    return mines.filter((m) =>
      [m.name, m.location, m.state, m.mineral].some((s) => s?.toLowerCase().includes(q)),
    )
  }, [mines, query])

  useEffect(() => {
    if (!open) return
    const close = (e) => !rootRef.current?.contains(e.target) && setOpen(false)
    document.addEventListener('mousedown', close)
    setActive(Math.max(0, filtered.findIndex((m) => m.id === value)))
    setTimeout(() => inputRef.current?.focus(), 0)
    return () => document.removeEventListener('mousedown', close)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  const pick = (m) => {
    onChange(m.id)
    setOpen(false)
    setQuery('')
  }

  const onKeyDown = (e) => {
    if (e.key === 'Escape') setOpen(false)
    else if (e.key === 'ArrowDown') { e.preventDefault(); setActive((i) => Math.min(i + 1, filtered.length - 1)) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActive((i) => Math.max(i - 1, 0)) }
    else if (e.key === 'Enter' && filtered[active]) { e.preventDefault(); pick(filtered[active]) }
  }

  return (
    <div className="mine-select" ref={rootRef}>
      <span className="mine-select-label">Select mine</span>
      <button type="button" className="mine-select-btn" onClick={() => setOpen((o) => !o)} aria-haspopup="listbox" aria-expanded={open}>
        {selected ? (
          <>
            <i className="dot" style={{ background: LEVEL_COLORS[selected.risk_level] }} />
            <span className="ms-name">{selected.name}</span>
            <span className="ms-meta">{selected.location}, {selected.state}</span>
          </>
        ) : (
          <span className="ms-meta">Loading mines…</span>
        )}
        <ChevronDown size={18} className={`ms-chevron ${open ? 'up' : ''}`} />
      </button>

      {open && (
        <div className="mine-select-panel" onKeyDown={onKeyDown}>
          <div className="ms-search">
            <Search size={15} />
            <input
              ref={inputRef}
              value={query}
              onChange={(e) => { setQuery(e.target.value); setActive(0) }}
              placeholder="Search by mine, district, state or mineral"
            />
          </div>
          <ul role="listbox">
            {filtered.length === 0 && <li className="ms-empty">No mine matches “{query}”</li>}
            {filtered.map((m, i) => (
              <li
                key={m.id}
                role="option"
                aria-selected={m.id === value}
                className={`${i === active ? 'active' : ''} ${m.id === value ? 'selected' : ''}`}
                onMouseEnter={() => setActive(i)}
                onClick={() => pick(m)}
              >
                <i className="dot" style={{ background: LEVEL_COLORS[m.risk_level] }} />
                <div className="ms-text">
                  <b>{m.name}</b>
                  <span>{m.location}, {m.state} · {m.mineral}</span>
                </div>
                <span className="ms-score" style={{ color: LEVEL_COLORS[m.risk_level] }}>
                  {m.overall_score.toFixed(1)}%
                  <small>{m.risk_level}</small>
                </span>
                {m.id === value ? <Check size={15} className="ms-check" /> : <span className="ms-check" />}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
