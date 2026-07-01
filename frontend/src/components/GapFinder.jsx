import MetricBar from './MetricBar'
import { getRecommendationLabel, getRecommendationType, safeNumber } from '../recommendation'

export default function GapFinder({ gaps }) {
  if (!gaps || gaps.length === 0) {
    return (
      <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
        No blue ocean opportunities detected for this query. All tags show moderate to high competition levels.
      </div>
    )
  }

  const sorted = [...gaps].sort((a, b) => safeNumber(b?.opportunity_score) - safeNumber(a?.opportunity_score))

  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <div className="w-2 h-2" style={{ backgroundColor: 'var(--accent)' }} />
        <span className="text-xs font-medium" style={{ color: 'var(--accent)' }}>
          {sorted.length} BLUE OCEAN OPPORTUNIT{sorted.length > 1 ? 'IES' : 'Y'}
        </span>
        <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
          High relevance, strong demand, low saturation — first-mover advantage
        </span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {sorted.map((gap, i) => {
          const label = getRecommendationLabel(gap)
          const type = getRecommendationType(gap)
          const semRel = safeNumber(gap?.semantic_relevance)
          const trend = safeNumber(gap?.trend_score)
          const comp = safeNumber(gap?.competition_score)
          const oppScore = safeNumber(gap?.opportunity_score)
          return (
            <div
              key={i}
              className="border p-4"
              style={{
                borderColor: i === 0 ? 'var(--accent)' : 'var(--border)',
                backgroundColor: i === 0 ? 'rgba(212,43,43,0.05)' : 'transparent',
              }}
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{i + 1}</span>
                    <div className="text-sm font-medium" style={{ color: i === 0 ? 'var(--accent)' : 'var(--text)' }}>
                      {type === 'hashtag' ? '#' : ''}{label}
                    </div>
                  </div>
                  <div className="text-xs mt-1" style={{ color: 'var(--text-tertiary)' }}>
                    {gap?.reason || `High relevance (${semRel.toFixed(0)}) + demand (${trend.toFixed(0)}) + low saturation (${comp.toFixed(0)})`}
                  </div>
                </div>
                <div className="text-right flex-shrink-0 ml-3">
                  <div className="text-lg font-bold" style={{ color: 'var(--accent)' }}>{oppScore.toFixed(0)}</div>
                  <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>OPPORTUNITY</div>
                </div>
              </div>
              <div className="space-y-1.5">
                <MetricBar label="Relevance" value={semRel} />
                <MetricBar label="Trend" value={trend} />
                <MetricBar label="Competition" value={comp} color="#555" />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
