import { getRecommendationLabel, getRecommendationType, competitionLevel } from '../recommendation'

export default function HighCompetitionPanel({ tags }) {
  if (!tags || tags.length === 0) {
    return (
      <div className="text-xs" style={{ color: '#555' }}>
        No high competition tags detected. All candidates show moderate to low saturation levels.
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <span className="text-xs font-medium" style={{ color: '#d42b2b' }}>
          {tags.length} HIGH COMPETITION TAG{tags.length > 1 ? 'S' : ''}
        </span>
        <span className="text-xs" style={{ color: '#555' }}>
          Highly saturated terms — generally should be avoided
        </span>
      </div>
      <div className="space-y-2">
        {tags.map((tag, i) => {
          const label = getRecommendationLabel(tag)
          const type = getRecommendationType(tag)
          const comp = tag?.competition_score || 0
          const level = competitionLevel(comp)
          return (
            <div key={i} className="border px-4 py-3 flex items-center justify-between" style={{ borderColor: '#1C1C1C' }}>
              <div className="flex items-center gap-2 min-w-0">
                <span className="text-xs" style={{ color: '#444' }}>{i + 1}</span>
                <span className="text-xs truncate" style={{ color: 'var(--text)' }}>
                  {type === 'hashtag' ? '#' : ''}{label}
                </span>
              </div>
              <div className="flex items-center gap-3 flex-shrink-0 ml-3">
                <span className="text-xs px-1.5 py-0.5" style={{
                  backgroundColor: `${level.color}22`,
                  color: level.color,
                  border: `1px solid ${level.color}44`,
                  fontSize: '10px',
                }}>
                  {level.label}
                </span>
                <span className="text-xs" style={{ color: '#555' }}>Competition: {comp.toFixed(0)}</span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
