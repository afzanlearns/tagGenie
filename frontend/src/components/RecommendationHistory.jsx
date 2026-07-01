const STORAGE_KEY = 'taggenie_history'

export function loadHistory() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
  } catch {
    return []
  }
}

export function saveEntry(entry) {
  const entries = loadHistory()
  const filtered = entries.filter(e => e.topic !== entry.topic || e.platform !== entry.platform)
  const updated = [{ ...entry, timestamp: Date.now() }, ...filtered].slice(0, 20)
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated))
  } catch {}
  return updated
}

export function clearHistory() {
  localStorage.removeItem(STORAGE_KEY)
}

export default function RecommendationHistory({ entries, onRestore, onClear }) {
  if (!entries || entries.length === 0) {
    return (
      <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
        No search history yet. Generate recommendations to build your history.
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium" style={{ color: 'var(--text)' }}>RECENT SEARCHES</span>
        <button
          onClick={onClear}
          className="text-xs px-2 py-0.5"
          style={{ backgroundColor: 'transparent', border: '1px solid #333', color: 'var(--text-tertiary)', cursor: 'pointer' }}
        >
          CLEAR
        </button>
      </div>
      <div className="space-y-1 max-h-60 overflow-y-auto">
        {entries.map((e, i) => (
          <div
            key={i}
            className="flex items-center justify-between px-3 py-2 cursor-pointer text-xs"
            style={{ borderBottom: '1px solid #141414' }}
            onClick={() => onRestore && onRestore(e)}
          >
            <div className="min-w-0">
              <div className="truncate" style={{ color: 'var(--text)' }}>{e.topic}</div>
              <div style={{ color: 'var(--text-tertiary)' }}>
                {e.product} · {e.platform} · {e.tags || 0} tags
              </div>
            </div>
            <span className="text-xs flex-shrink-0 ml-2" style={{ color: 'var(--text-muted)' }}>
              {new Date(e.timestamp).toLocaleDateString()}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
