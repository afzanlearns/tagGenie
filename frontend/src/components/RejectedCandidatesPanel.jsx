import { getRecommendationLabel, getRecommendationType } from '../recommendation'

export default function RejectedCandidatesPanel({ candidates }) {
  if (!candidates || candidates.length === 0) {
    return (
      <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
        No candidates were rejected. All evaluated tags met minimum quality thresholds.
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <span className="text-xs font-medium" style={{ color: 'var(--text-tertiary)' }}>
          {candidates.length} REJECTED CANDIDATE{candidates.length > 1 ? 'S' : ''}
        </span>
        <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
          Tags evaluated but excluded — shows TagGenie actively filters
        </span>
      </div>
      <div className="space-y-2">
        {candidates.map((c, i) => {
          const label = getRecommendationLabel(c)
          const type = getRecommendationType(c)
          return (
            <div key={i} className="border px-4 py-3" style={{ borderColor: 'var(--border)' }}>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{i + 1}</span>
                <span className="text-xs" style={{ color: 'var(--text-tertiary)', textDecoration: 'line-through' }}>
                  {type === 'hashtag' ? '#' : ''}{label}
                </span>
              </div>
              <div className="text-xs ml-4" style={{ color: 'var(--text-muted)' }}>
                Rejected because: {c?.reason || 'Low overall score'}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
