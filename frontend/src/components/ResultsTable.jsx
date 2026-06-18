import ScoreBar from './ScoreBar'
import RationalePanel from './RationalePanel'

export default function ResultsTable({ tags }) {
  if (!tags || tags.length === 0) {
    return <div className="text-xs" style={{ color: '#555' }}>No tags to display.</div>
  }

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs" style={{ borderCollapse: 'collapse', fontFamily: 'var(--font)' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #1C1C1C' }}>
              <th className="text-left py-2 pr-4" style={{ color: '#555', fontWeight: 400 }}>#</th>
              <th className="text-left py-2 pr-4" style={{ color: '#555', fontWeight: 400 }}>TAG</th>
              <th className="text-left py-2 pr-4" style={{ color: '#555', fontWeight: 400 }}>TYPE</th>
              <th className="text-right py-2 pr-4" style={{ color: '#555', fontWeight: 400 }}>FINAL</th>
              <th className="text-right py-2 pr-4" style={{ color: '#555', fontWeight: 400 }}>REACH</th>
              <th className="text-right py-2 pr-4" style={{ color: '#555', fontWeight: 400 }}>COMP</th>
              <th className="text-left py-2" style={{ color: '#555', fontWeight: 400 }}>SCORE</th>
            </tr>
          </thead>
          <tbody>
            {tags.map((tag, i) => (
              <tr key={i} style={{ borderBottom: '1px solid #141414' }}>
                <td className="py-2.5 pr-4" style={{ color: '#444' }}>{i + 1}</td>
                <td className="py-2.5 pr-4" style={{ color: 'var(--text)', fontWeight: i === 0 ? 700 : 400 }}>
                  {tag.final_score > 70 && (
                    <span style={{ color: 'var(--accent)' }}>● </span>
                  )}
                  {tag.tag}
                </td>
                <td className="py-2.5 pr-4" style={{ color: '#555' }}>
                  {tag.type === 'hashtag' ? '#' : 'kw'}
                </td>
                <td className="py-2.5 pr-4 text-right" style={{ fontVariantNumeric: 'tabular-nums' }}>
                  {tag.final_score.toFixed(1)}
                </td>
                <td className="py-2.5 pr-4 text-right" style={{ color: '#888', fontVariantNumeric: 'tabular-nums' }}>
                  {tag.reach_score.toFixed(0)}
                </td>
                <td className="py-2.5 pr-4 text-right" style={{ color: '#888', fontVariantNumeric: 'tabular-nums' }}>
                  {tag.competition_score.toFixed(0)}
                </td>
                <td className="py-2.5">
                  <ScoreBar value={tag.final_score} max={100} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {tags.map((tag, i) => (
        <RationalePanel key={i} tag={tag.tag} rationale={tag.rationale} />
      ))}
    </div>
  )
}
