import { useState } from 'react'
import ScoreBar from './ScoreBar'
import DetailsDrawer from './DetailsDrawer'

function guessCategory(tag) {
  const t = tag.toLowerCase()
  if (tag.type === 'hashtag') return 'Hashtag'
  if (t.endsWith('industry') || t.includes('sector') || t.includes('market') || t.includes('supply chain')) return 'Industry'
  if (t.includes('brand') || t.endsWith('pro') || t.includes('product')) return 'Brand'
  if (t.includes('lover') || t.includes('enthusiast') || t.includes('community') || t.includes('farmer') || t.includes('buyer') || t.includes('professional')) return 'Audience'
  if (t.includes('trend') || t.includes('innovation') || t.includes('future') || t.includes('best') || t.includes('top')) return 'Topic'
  if (t.includes('roast') || t.includes('brew') || t.includes('process') || t.includes('grade') || t.includes('certification')) return 'Process'
  return 'Industry'
}

export default function ResultsTable({ tags }) {
  const [selectedTag, setSelectedTag] = useState(null)

  if (!tags || tags.length === 0) {
    return <div className="text-xs py-4" style={{ color: '#555' }}>No tags to display.</div>
  }

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs" style={{ borderCollapse: 'collapse', fontFamily: 'var(--font)' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #1C1C1C' }}>
              <th className="text-left py-2 pr-3" style={{ color: '#555', fontWeight: 400 }}>#</th>
              <th className="text-left py-2 pr-3" style={{ color: '#555', fontWeight: 400 }}>TAG</th>
              <th className="text-left py-2 pr-3" style={{ color: '#555', fontWeight: 400 }}>CATEGORY</th>
              <th className="text-right py-2 pr-3" style={{ color: '#555', fontWeight: 400 }}>FINAL</th>
              <th className="text-right py-2 pr-3" style={{ color: '#555', fontWeight: 400 }}>REL</th>
              <th className="text-right py-2 pr-3" style={{ color: '#555', fontWeight: 400 }}>TREND</th>
              <th className="text-right py-2 pr-3" style={{ color: '#555', fontWeight: 400 }}>COMP</th>
              <th className="text-right py-2 pr-3" style={{ color: '#555', fontWeight: 400 }}>PLAT</th>
              <th className="text-left py-2" style={{ color: '#555', fontWeight: 400 }}>SCORE</th>
            </tr>
          </thead>
          <tbody>
            {tags.map((tag, i) => {
              const cat = guessCategory(tag)
              return (
                <tr
                  key={i}
                  className="cursor-pointer"
                  style={{ borderBottom: '1px solid #141414' }}
                  onClick={() => setSelectedTag(tag)}
                  onMouseEnter={e => e.currentTarget.style.backgroundColor = '#0D0D0D'}
                  onMouseLeave={e => e.currentTarget.style.backgroundColor = 'transparent'}
                >
                  <td className="py-2.5 pr-3" style={{ color: '#444' }}>{i + 1}</td>
                  <td className="py-2.5 pr-3" style={{ color: 'var(--text)', fontWeight: i === 0 ? 700 : 400 }}>
                    {tag.final_score > 70 && (
                      <span style={{ color: 'var(--accent)' }}>● </span>
                    )}
                    {tag.tag}
                  </td>
                  <td className="py-2.5 pr-3">
                    <span className="text-xs px-1.5 py-0.5" style={{ backgroundColor: '#141414', color: '#888', border: '1px solid #2A2A2A', fontSize: '10px' }}>
                      {cat}
                    </span>
                  </td>
                  <td className="py-2.5 pr-3 text-right" style={{ fontVariantNumeric: 'tabular-nums' }}>
                    {tag.final_score.toFixed(1)}
                  </td>
                  <td className="py-2.5 pr-3 text-right" style={{ color: '#888', fontVariantNumeric: 'tabular-nums' }}>
                    {(tag.semantic_relevance || 0).toFixed(0)}
                  </td>
                  <td className="py-2.5 pr-3 text-right" style={{ color: '#888', fontVariantNumeric: 'tabular-nums' }}>
                    {(tag.trend_score || 0).toFixed(0)}
                  </td>
                  <td className="py-2.5 pr-3 text-right" style={{ color: '#888', fontVariantNumeric: 'tabular-nums' }}>
                    {(tag.competition_score || 0).toFixed(0)}
                  </td>
                  <td className="py-2.5 pr-3 text-right" style={{ color: '#888', fontVariantNumeric: 'tabular-nums' }}>
                    {(tag.platform_fit || 0).toFixed(0)}
                  </td>
                  <td className="py-2.5">
                    <ScoreBar value={tag.final_score} max={100} />
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <div className="mt-2 flex gap-4 text-xs" style={{ color: '#555' }}>
        <span>REL = semantic relevance</span>
        <span>TREND = trend momentum</span>
        <span>COMP = competition</span>
        <span>PLAT = platform fit</span>
        <span className="ml-auto" style={{ color: '#444' }}>Click any row for details</span>
      </div>

      {selectedTag && (
        <DetailsDrawer tag={selectedTag} onClose={() => setSelectedTag(null)} />
      )}
    </div>
  )
}
