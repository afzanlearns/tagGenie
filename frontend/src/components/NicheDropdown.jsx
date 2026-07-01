import { useState, useRef, useEffect } from 'react'

export default function NicheDropdown({ niches, activeNiche, onSwitch }) {
  const [open, setOpen] = useState(false)
  const [focusedIdx, setFocusedIdx] = useState(-1)
  const ref = useRef(null)
  const listRef = useRef(null)

  const selected = niches.find(n => n.niche_id === activeNiche)

  useEffect(() => {
    if (!open) { setFocusedIdx(-1); return }
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  useEffect(() => {
    if (!open || focusedIdx < 0 || !listRef.current) return
    const el = listRef.current.children[focusedIdx]
    if (el) el.scrollIntoView({ block: 'nearest' })
  }, [focusedIdx, open])

  const handleKeyDown = (e) => {
    if (!open) {
      if (e.key === 'Enter' || e.key === ' ' || e.key === 'ArrowDown') {
        e.preventDefault(); setOpen(true); setFocusedIdx(0)
      }
      return
    }
    switch (e.key) {
      case 'Escape': setOpen(false); break
      case 'ArrowDown': e.preventDefault(); setFocusedIdx(i => Math.min(i + 1, niches.length - 1)); break
      case 'ArrowUp': e.preventDefault(); setFocusedIdx(i => Math.max(i - 1, 0)); break
      case 'Enter':
      case ' ':
        e.preventDefault()
        if (focusedIdx >= 0 && focusedIdx < niches.length) {
          onSwitch(niches[focusedIdx].niche_id)
          setOpen(false)
        }
        break
      case 'Tab': setOpen(false); break
    }
  }

  return (
    <div ref={ref} style={{ position: 'relative', userSelect: 'none' }} onKeyDown={handleKeyDown}>
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
        className="text-xs px-2 py-1 border"
        style={{
          backgroundColor: 'transparent',
          borderColor: 'var(--border-light)',
          color: 'var(--text)',
          borderRadius: 0,
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          minWidth: 140,
          fontFamily: 'inherit',
        }}
      >
        <span style={{ flex: 1, textAlign: 'left' }}>{selected?.display_name || selected?.niche_id || activeNiche}</span>
        <span style={{ color: 'var(--text-muted)', fontSize: 10 }}>▾</span>
      </button>
      {open && (
        <div
          ref={listRef}
          role="listbox"
          tabIndex={-1}
          style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            right: 0,
            backgroundColor: 'var(--surface)',
            border: '1px solid var(--border)',
            zIndex: 100,
            maxHeight: 260,
            overflowY: 'auto',
            marginTop: 2,
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
          }}
        >
          {niches.map((n, i) => (
            <div
              key={n.niche_id}
              role="option"
              aria-selected={n.niche_id === activeNiche}
              onClick={() => { onSwitch(n.niche_id); setOpen(false) }}
              onMouseEnter={() => setFocusedIdx(i)}
              className="text-xs px-3 py-2"
              style={{
                backgroundColor:
                  n.niche_id === activeNiche ? 'var(--accent)'
                  : focusedIdx === i ? 'var(--surface-2)'
                  : 'transparent',
                color:
                  n.niche_id === activeNiche ? '#fff'
                  : 'var(--text)',
                cursor: 'pointer',
                transition: 'background-color 0.1s',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                opacity: 1,
                filter: 'none',
              }}
            >
              {n.display_name || n.niche_id}
            </div>
          ))}
          {niches.length === 0 && (
            <div className="text-xs px-3 py-2" style={{ color: 'var(--text-muted)' }}>
              No niches available
            </div>
          )}
        </div>
      )}
    </div>
  )
}
