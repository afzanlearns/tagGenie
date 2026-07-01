import MetricBar from './MetricBar'
import { getRecommendationLabel, getRecommendationType, safeNumber } from '../recommendation'

const getReason = (gap) => {
  const semRel = safeNumber(gap?.semantic_relevance)
  const trend = safeNumber(gap?.trend_score)
  const comp = safeNumber(gap?.competition_score)
  const isHashtag = getRecommendationType(gap) === 'hashtag'
  return gap?.reason || `${isHashtag ? '#' : 'kw'} High relevance (${semRel.toFixed(0)}) + trend (${trend.toFixed(0)}) + low saturation (${comp.toFixed(0)}) — blue ocean`
}

export default function GapFinder({ gaps }) {
  if (!gaps || gaps.length === 0) {
    return (
      <div className="text-xs" style={{ color: '#555' }}>
        No blue ocean gaps detected for this query. All tags show moderate to high competition levels.
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <div className="w-2 h-2" style={{ backgroundColor: 'var(--accent)' }} />
        <span className="text-xs font-medium" style={{ color: 'var(--accent)' }}>
          {gaps.length} BLUE OCEAN OPPORTUNIT{gaps.length > 1 ? 'IES' : 'Y'}
        </span>
        <span className="text-xs" style={{ color: '#555' }}>
          High relevance, high trend, low competition — first-mover advantage
        </span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {gaps.map((gap, i) => {
          const semRel = safeNumber(gap?.semantic_relevance)
          const trend = safeNumber(gap?.trend_score)
          const comp = safeNumber(gap?.competition_score)
          const oppScore = (semRel * trend * (100 - comp) / 10000).toFixed(0)
          const label = getRecommendationLabel(gap)
          const type = getRecommendationType(gap)
          return (
            <div
              key={i}
              className="border p-4"
              style={{
                borderColor: i === 0 ? 'var(--accent)' : '#1C1C1C',
                backgroundColor: i === 0 ? 'rgba(212,43,43,0.05)' : 'transparent',
              }}
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div
                    className="text-sm font-medium"
                    style={{ color: i === 0 ? 'var(--accent)' : 'var(--text)' }}
                  >
                    {type === 'hashtag' ? '#' : ''}{label}
                  </div>
                  <div className="text-xs mt-1" style={{ color: '#555' }}>{getReason(gap)}</div>
                </div>
                <div className="text-right flex-shrink-0 ml-3">
                  <div className="text-lg font-bold" style={{ color: 'var(--accent)' }}>{oppScore}</div>
                  <div className="text-xs" style={{ color: '#555' }}>OPPORTUNITY</div>
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
