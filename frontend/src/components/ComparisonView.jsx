export default function ComparisonView({ tagGenieTags, baselineTags, gapTags }) {
  const gapSet = new Set((gapTags || []).map(g => g.tag))

  const maxRows = Math.max(tagGenieTags.length, baselineTags.length)

  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <span className="text-xs font-medium" style={{ color: 'var(--text)' }}>SIDE-BY-SIDE COMPARISON</span>
        <span className="text-xs" style={{ color: '#555' }}>
          TagGenie vs naive TF-IDF baseline — same topic, same platform
        </span>
      </div>

      <div className="grid grid-cols-2 gap-0 border" style={{ borderColor: '#1C1C1C' }}>
        <div className="border-r" style={{ borderColor: '#1C1C1C' }}>
          <div className="px-4 py-2 border-b" style={{ borderColor: '#1C1C1C', backgroundColor: '#0F0F0F' }}>
            <span className="text-xs font-medium" style={{ color: 'var(--accent)' }}>TAGGENIE</span>
            <span className="text-xs ml-2" style={{ color: '#555' }}>
              Trend + competition + confidence
            </span>
          </div>
          {Array.from({ length: maxRows }).map((_, i) => {
            const tag = tagGenieTags[i]
            return (
              <div
                key={`tg-${i}`}
                className="px-4 py-2.5 flex items-center justify-between"
                style={{ borderBottom: '1px solid #141414' }}
              >
                {tag ? (
                  <>
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="text-xs" style={{ color: '#444', flexShrink: 0 }}>
                        {i + 1}
                      </span>
                      {gapSet.has(tag.tag) && (
                        <span className="text-xs" style={{ color: 'var(--accent)', flexShrink: 0 }} title="Blue ocean gap">
                          ◆
                        </span>
                      )}
                      <span
                        className="text-sm truncate"
                        style={{
                          color: 'var(--text)',
                          fontWeight: i === 0 ? 700 : 400,
                        }}
                      >
                        {tag.type === 'hashtag' ? '#' : ''}{tag.tag}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0 ml-2">
                      <span className="text-xs" style={{ color: '#888' }}>
                        {tag.final_score.toFixed(0)}
                      </span>
                    </div>
                  </>
                ) : (
                  <div className="h-6" />
                )}
              </div>
            )
          })}
        </div>

        <div>
          <div className="px-4 py-2 border-b" style={{ borderColor: '#1C1C1C', backgroundColor: '#0F0F0F' }}>
            <span className="text-xs font-medium" style={{ color: '#888' }}>NAIVE BASELINE</span>
            <span className="text-xs ml-2" style={{ color: '#555' }}>
              TF-IDF keywords only
            </span>
          </div>
          {Array.from({ length: maxRows }).map((_, i) => {
            const tag = baselineTags[i]
            return (
              <div
                key={`bl-${i}`}
                className="px-4 py-2.5 flex items-center justify-between"
                style={{ borderBottom: '1px solid #141414' }}
              >
                {tag ? (
                  <>
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="text-xs" style={{ color: '#444', flexShrink: 0 }}>
                        {i + 1}
                      </span>
                      <span className="text-sm truncate" style={{ color: '#888' }}>
                        {tag.type === 'hashtag' ? '#' : ''}{tag.tag}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0 ml-2">
                      <span className="text-xs" style={{ color: '#666' }}>
                        {tag.score.toFixed(0)}
                      </span>
                    </div>
                  </>
                ) : (
                  <div className="h-6" />
                )}
              </div>
            )
          })}
        </div>
      </div>

      <div className="mt-4 flex items-center gap-4 text-xs" style={{ color: '#555' }}>
        <div className="flex items-center gap-1.5">
          <span style={{ color: 'var(--accent)' }}>◆</span>
          <span>Blue ocean gap detected</span>
        </div>
        <span>Gaps are unique to TagGenie — the baseline has no competitive awareness.</span>
      </div>
    </div>
  )
}
