import { safeNumber } from '../recommendation'

export default function AnalyticsCards({ results }) {
  if (!results || !results.ranked_tags) return null

  const tags = results.ranked_tags
  const gaps = results.gap_tags || []

  const avgRel = tags.reduce((s, t) => s + safeNumber(t?.semantic_relevance), 0) / tags.length
  const avgTrend = tags.reduce((s, t) => s + safeNumber(t?.trend_score), 0) / tags.length
  const avgComp = tags.reduce((s, t) => s + safeNumber(t?.competition_score), 0) / tags.length

  const cards = [
    { label: 'RECOMMENDATIONS', value: tags.length, sub: results.platform },
    { label: 'AVG RELEVANCE', value: avgRel.toFixed(0), sub: '/100' },
    { label: 'AVG TREND', value: avgTrend.toFixed(0), sub: '/100' },
    { label: 'AVG COMPETITION', value: avgComp.toFixed(0), sub: '/100 (lower=better)' },
    { label: 'BLUE OCEAN', value: gaps.length, sub: 'opportunities' },
    { label: 'CONFIDENCE', value: results.confidence.toFixed(0), sub: '%' },
  ]

  return (
    <div className="mb-6">
      <div className="text-xs font-medium mb-3" style={{ color: '#555' }}>ANALYTICS SUMMARY</div>
      <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
        {cards.map(c => (
          <div key={c.label} className="border p-3" style={{ borderColor: '#1C1C1C' }}>
            <div className="text-xs mb-0.5" style={{ color: '#555' }}>{c.label}</div>
            <div className="text-lg font-bold" style={{ color: 'var(--text)' }}>{c.value}</div>
            {c.sub && <div className="text-xs" style={{ color: '#555' }}>{c.sub}</div>}
          </div>
        ))}
      </div>
    </div>
  )
}
