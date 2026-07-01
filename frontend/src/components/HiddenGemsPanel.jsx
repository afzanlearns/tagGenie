import MetricBar from './MetricBar'
import { getRecommendationLabel, getRecommendationType, safeNumber } from '../recommendation'

export default function HiddenGemsPanel({ gems }) {
  if (!gems || gems.length === 0) {
    return (
      <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
        No hidden gems detected. All tags show sufficient trend activity.
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <span className="text-xs font-medium" style={{ color: '#8bc34a' }}>
          {gems.length} HIDDEN GEM{gems.length > 1 ? 'S' : ''}
        </span>
        <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
          High relevance, low competition, lower trend — long-tail opportunities
        </span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {gems.map((gem, i) => {
          const label = getRecommendationLabel(gem)
          const type = getRecommendationType(gem)
          const semRel = safeNumber(gem?.semantic_relevance)
          const comp = safeNumber(gem?.competition_score)
          const trend = safeNumber(gem?.trend_score)
          return (
            <div key={i} className="border p-4" style={{ borderColor: 'var(--border)' }}>
              <div className="text-sm font-medium mb-2" style={{ color: 'var(--text)' }}>
                {type === 'hashtag' ? '#' : ''}{label}
              </div>
              <div className="text-xs mb-3" style={{ color: 'var(--text-tertiary)' }}>
                {gem?.reason || `${label}: high relevance (${semRel.toFixed(0)}) + low competition (${comp.toFixed(0)}) — long-tail`}
              </div>
              <div className="space-y-1.5">
                <MetricBar label="Relevance" value={semRel} />
                <MetricBar label="Competition" value={comp} color="#555" />
                <MetricBar label="Trend" value={trend} color="#b8860b" />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
