export default function AnalyticsCards({ results }) {
  if (!results || !results.ranked_tags) return null

  const tags = results.ranked_tags
  const gaps = results.gap_tags || []

  const avgRel = tags.reduce((s, t) => s + (t.semantic_relevance || 0), 0) / tags.length
  const avgTrend = tags.reduce((s, t) => s + (t.trend_score || 0), 0) / tags.length
  const avgComp = tags.reduce((s, t) => s + (t.competition_score || 0), 0) / tags.length
  const avgPlat = tags.reduce((s, t) => s + (t.platform_fit || 0), 0) / tags.length
  const platformDist = {}
  tags.forEach(t => {
    const p = t.platform_fit >= 60 ? 'Strong' : t.platform_fit >= 30 ? 'Moderate' : 'Weak'
    platformDist[p] = (platformDist[p] || 0) + 1
  })

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
