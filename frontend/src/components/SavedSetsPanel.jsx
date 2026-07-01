import { useState, useEffect } from 'react'
import { api } from '../api'

export default function SavedSetsPanel({ currentUser, onRestore }) {
  const [sets, setSets] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (currentUser?.is_guest) {
      setLoading(false)
      return
    }
    api('/api/saved-sets')
      .then(data => setSets(data.saved_sets || []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [currentUser])

  const handleDelete = async (id) => {
    try {
      await api(`/api/saved-sets/${id}`, { method: 'DELETE' })
      setSets(prev => prev.filter(s => s.id !== id))
    } catch (e) {
      console.error(e)
    }
  }

  if (currentUser?.is_guest) {
    return (
      <div className="text-xs py-8 text-center" style={{ color: 'var(--text-tertiary)' }}>
        Sign up or log in to save recommendation sets permanently.
      </div>
    )
  }

  if (loading) {
    return <div className="text-xs py-4" style={{ color: 'var(--text-tertiary)' }}>Loading saved sets...</div>
  }

  if (sets.length === 0) {
    return (
      <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
        No saved recommendation sets yet. Generate recommendations and save them for later reference.
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium" style={{ color: 'var(--text)' }}>SAVED RECOMMENDATION SETS ({sets.length})</span>
      </div>
      <div className="space-y-2">
        {sets.map(s => (
          <div key={s.id} className="border px-4 py-3 flex items-center justify-between" style={{ borderColor: 'var(--border)' }}>
            <div className="min-w-0 flex-1">
              <div className="text-sm font-medium" style={{ color: 'var(--text)' }}>{s.name}</div>
              <div className="text-xs mt-0.5" style={{ color: 'var(--text-tertiary)' }}>
                {s.topic} · {s.product} · {s.platform} · {s.tag_count} tags
              </div>
              <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                Confidence: {s.confidence?.toFixed(0)}% · {new Date(s.created_at).toLocaleDateString()}
              </div>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0 ml-3">
              <button
                onClick={() => onRestore && onRestore(s)}
                className="text-xs px-2 py-1"
                style={{ backgroundColor: 'transparent', border: '1px solid #333', color: 'var(--text-secondary)', cursor: 'pointer' }}
              >
                RESTORE
              </button>
              <button
                onClick={() => handleDelete(s.id)}
                className="text-xs px-2 py-1"
                style={{ backgroundColor: 'transparent', border: '1px solid #333', color: 'var(--text-tertiary)', cursor: 'pointer' }}
              >
                DELETE
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
