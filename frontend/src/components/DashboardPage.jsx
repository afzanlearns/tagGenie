import { useState, useEffect } from 'react'
import { api } from '../api'

export default function DashboardPage({ currentUser }) {
  const [stats, setStats] = useState(null)
  const [settings, setSettings] = useState(null)

  useEffect(() => {
    if (currentUser?.is_guest) return
    api('/api/dashboard').then(setStats).catch(() => {})
    api('/api/settings').then(setSettings).catch(() => {})
  }, [currentUser])

  if (currentUser?.is_guest) {
    return (
      <div className="text-xs py-8 text-center" style={{ color: '#555' }}>
        Sign up or log in to access your dashboard with persistent statistics, history, and settings.
      </div>
    )
  }

  if (!stats) {
    return <div className="text-xs py-4" style={{ color: '#555' }}>Loading dashboard...</div>
  }

  const summaryCards = [
    { label: 'TOTAL NICHES', value: stats.total_niches },
    { label: 'RECOMMENDATIONS', value: stats.recommendations_generated },
    { label: 'SESSIONS', value: stats.total_sessions },
    { label: 'BLUE OCEAN FOUND', value: stats.blue_ocean_opportunities_found },
    { label: 'AVG CONFIDENCE', value: `${stats.average_confidence}%` },
    { label: 'MOST USED PLATFORM', value: stats.most_used_platform },
    { label: 'MOST USED NICHE', value: stats.most_used_niche },
  ]

  return (
    <div>
      <div className="text-xs font-medium mb-4" style={{ color: '#555' }}>USER DASHBOARD</div>

      <div className="grid grid-cols-3 md:grid-cols-4 gap-3 mb-6">
        {summaryCards.map(c => (
          <div key={c.label} className="border p-4" style={{ borderColor: '#1C1C1C' }}>
            <div className="text-xs mb-1" style={{ color: '#555' }}>{c.label}</div>
            <div className="text-lg font-bold" style={{ color: 'var(--text)' }}>{c.value}</div>
          </div>
        ))}
      </div>

      {stats.history_timeline && stats.history_timeline.length > 0 && (
        <div>
          <div className="text-xs font-medium mb-3" style={{ color: '#555' }}>RECENT ACTIVITY</div>
          <div className="space-y-1">
            {stats.history_timeline.map((h, i) => (
              <div key={i} className="flex items-center justify-between px-4 py-2 text-xs" style={{ borderBottom: '1px solid #141414' }}>
                <div className="min-w-0">
                  <span className="truncate" style={{ color: 'var(--text)' }}>{h.topic}</span>
                  <span className="ml-2" style={{ color: '#555' }}>· {h.platform}</span>
                </div>
                <div className="flex items-center gap-3 flex-shrink-0 ml-3">
                  <span style={{ color: '#555' }}>{h.tag_count} tags</span>
                  <span style={{ color: '#555' }}>{h.confidence?.toFixed(0)}%</span>
                  <span style={{ color: '#444' }}>{new Date(h.created_at).toLocaleDateString()}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
