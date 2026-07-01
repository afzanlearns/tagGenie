import { safeNumber } from '../recommendation'

export default function AnalyticsCards({ results }) {
  if (!results) return null

  const analytics = results.analytics || {}
  const ranked = results.ranked_tags || []
  const gaps = results.gap_tags || []
  const highComp = results.high_competition_tags || []
  const hiddenGems = results.hidden_gems || []

  const cards = [
    { label: 'RECOMMENDATIONS', value: ranked.length, sub: results.platform },
    { label: 'AVG RELEVANCE', value: safeNumber(analytics?.avg_relevance).toFixed(0), sub: '/100' },
    { label: 'AVG TREND', value: safeNumber(analytics?.avg_trend).toFixed(0), sub: '/100' },
    { label: 'AVG COMPETITION', value: safeNumber(analytics?.avg_competition).toFixed(0), sub: '/100' },
    { label: 'AVG PLATFORM FIT', value: safeNumber(analytics?.avg_platform_fit).toFixed(0), sub: '/100' },
    { label: 'AVG FINAL SCORE', value: safeNumber(analytics?.avg_final_score).toFixed(0), sub: '/100' },
    { label: 'BLUE OCEAN', value: gaps.length, sub: 'opportunities' },
    { label: 'HIGH COMPETITION', value: highComp.length, sub: 'avoid' },
    { label: 'HIDDEN GEMS', value: hiddenGems.length, sub: 'long-tail' },
    { label: 'UNIQUE CATEGORIES', value: analytics?.unique_categories || 0, sub: 'types' },
    { label: 'DIVERSITY', value: `${safeNumber(analytics?.diversity).toFixed(0)}%`, sub: 'spread' },
    { label: 'CONFIDENCE', value: safeNumber(results.confidence).toFixed(0), sub: '%' },
  ]

  return (
    <div className="mb-6">
      <div className="text-xs font-medium mb-3" style={{ color: 'var(--text-tertiary)' }}>ANALYTICS SUMMARY</div>
      <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
        {cards.map(c => (
          <div key={c.label} className="border p-3" style={{ borderColor: 'var(--border)' }}>
            <div className="text-xs mb-0.5" style={{ color: 'var(--text-tertiary)' }}>{c.label}</div>
            <div className="text-lg font-bold" style={{ color: 'var(--text)' }}>{c.value}</div>
            {c.sub && <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{c.sub}</div>}
          </div>
        ))}
      </div>
    </div>
  )
}
