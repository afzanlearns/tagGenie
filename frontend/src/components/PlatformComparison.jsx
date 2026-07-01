import { useState, useEffect } from 'react'
import { api } from '../api'
import { getRecommendationLabel, formatScore, safeNumber } from '../recommendation'

const ALL_PLATFORMS = ['LinkedIn', 'Instagram', 'X', 'TikTok']

export default function PlatformComparison({ topic, product, niche, onSelectTag }) {
  const [results, setResults] = useState({})
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!topic || !product) return
    let cancelled = false
    setLoading(true)

    Promise.all(ALL_PLATFORMS.map(p =>
      api('/api/score', {
        method: 'POST',
        body: { topic, product, platform: p, niche, include_baseline: false },
      }).then(r => ({ platform: p, data: r }))
    )).then(all => {
      if (cancelled) return
      const byPlatform = {}
      all.forEach(({ platform, data }) => { byPlatform[platform] = data })
      setResults(byPlatform)
      setLoading(false)
    }).catch(() => {
      if (!cancelled) setLoading(false)
    })

    return () => { cancelled = true }
  }, [topic, product, niche])

  if (!topic || !product) {
    return <div className="text-xs" style={{ color: '#555' }}>Enter a topic and product to compare platforms.</div>
  }

  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <span className="text-xs font-medium" style={{ color: 'var(--text)' }}>PLATFORM COMPARISON</span>
        <span className="text-xs" style={{ color: '#555' }}>
          Same topic, ranked differently per platform
        </span>
      </div>

      {loading && (
        <div className="text-xs py-4" style={{ color: '#555' }}>
          Scoring across all platforms...
        </div>
      )}

      <div className="grid grid-cols-4 gap-0 border" style={{ borderColor: '#1C1C1C' }}>
        {ALL_PLATFORMS.map((platform, pi) => {
          const data = results[platform]
          const tags = data?.ranked_tags || []
          return (
            <div key={platform} className={pi < 3 ? 'border-r' : ''} style={{ borderColor: '#1C1C1C' }}>
              <div className="px-3 py-2 border-b text-xs font-medium" style={{ borderColor: '#1C1C1C', backgroundColor: '#0F0F0F', color: 'var(--text)' }}>
                {platform}
              </div>
              {tags.slice(0, 8).map((t, i) => {
                const label = getRecommendationLabel(t)
                const finalScore = safeNumber(t?.final_score)
                return (
                  <div
                    key={i}
                    className="px-3 py-2 flex items-center justify-between cursor-pointer"
                    style={{ borderBottom: '1px solid #141414' }}
                    onClick={() => onSelectTag && onSelectTag(t)}
                  >
                    <div className="flex items-center gap-1.5 min-w-0">
                      <span className="text-xs" style={{ color: '#444' }}>{i + 1}</span>
                      <span className="text-xs truncate" style={{ color: 'var(--text)' }}>{label}</span>
                    </div>
                    <span className="text-xs flex-shrink-0 ml-1" style={{ color: '#555' }}>
                      {formatScore(finalScore)}
                    </span>
                  </div>
                )
              })}
              {tags.length === 0 && !loading && (
                <div className="px-3 py-4 text-xs" style={{ color: '#444' }}>No results</div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
