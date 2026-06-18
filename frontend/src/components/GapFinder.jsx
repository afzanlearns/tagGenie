const getReason = (gap) => {
  const isHashtag = gap.type === 'hashtag'
  return gap.reason || `${isHashtag ? '#' : 'kw'} High reach (${gap.reach_score.toFixed(0)}) + low saturation (${gap.competition_score.toFixed(0)}) — blue ocean opportunity`
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
          High reach, low competition — first-mover advantage
        </span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {gaps.map((gap, i) => (
          <div
            key={i}
            className="border p-4 flex items-start gap-3"
            style={{
              borderColor: i === 0 ? 'var(--accent)' : '#1C1C1C',
              backgroundColor: i === 0 ? 'rgba(212,43,43,0.05)' : 'transparent',
            }}
          >
            <div className="flex-shrink-0 w-1.5 h-1.5 mt-1.5" style={{ backgroundColor: i === 0 ? 'var(--accent)' : '#333' }} />
            <div className="flex-1 min-w-0">
              <div
                className="text-sm break-all"
                style={{
                  color: i === 0 ? 'var(--accent)' : 'var(--text)',
                  fontWeight: i === 0 ? 700 : 400,
                }}
              >
                {gap.type === 'hashtag' ? '#' : ''}{gap.tag}
              </div>
              <div className="text-xs mt-1" style={{ color: '#555' }}>{getReason(gap)}</div>
              <div className="flex gap-4 mt-2 text-xs" style={{ color: '#666' }}>
                <span>Reach: {gap.reach_score.toFixed(0)}</span>
                <span>Comp: {gap.competition_score.toFixed(0)}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
