import { useState } from 'react'
import ScoreBar from './ScoreBar'
import DetailsDrawer from './DetailsDrawer'
import { getRecommendationLabel, getRecommendationType, getCategory, formatScore, formatScoreOne, safeNumber } from '../recommendation'

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
              const label = getRecommendationLabel(tag)
              const type = getRecommendationType(tag)
              const cat = getCategory(tag)
              const finalScore = safeNumber(tag?.final_score)
              const semRel = safeNumber(tag?.semantic_relevance)
              const trend = safeNumber(tag?.trend_score)
              const comp = safeNumber(tag?.competition_score)
              const plat = safeNumber(tag?.platform_fit)
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
                    {finalScore > 70 && (
                      <span style={{ color: 'var(--accent)' }}>● </span>
                    )}
                    {type === 'hashtag' ? '#' : ''}{label}
                  </td>
                  <td className="py-2.5 pr-3">
                    <span className="text-xs px-1.5 py-0.5" style={{ backgroundColor: '#141414', color: '#888', border: '1px solid #2A2A2A', fontSize: '10px' }}>
                      {cat}
                    </span>
                  </td>
                  <td className="py-2.5 pr-3 text-right" style={{ fontVariantNumeric: 'tabular-nums' }}>
                    {formatScoreOne(finalScore)}
                  </td>
                  <td className="py-2.5 pr-3 text-right" style={{ color: '#888', fontVariantNumeric: 'tabular-nums' }}>
                    {formatScore(semRel)}
                  </td>
                  <td className="py-2.5 pr-3 text-right" style={{ color: '#888', fontVariantNumeric: 'tabular-nums' }}>
                    {formatScore(trend)}
                  </td>
                  <td className="py-2.5 pr-3 text-right" style={{ color: '#888', fontVariantNumeric: 'tabular-nums' }}>
                    {formatScore(comp)}
                  </td>
                  <td className="py-2.5 pr-3 text-right" style={{ color: '#888', fontVariantNumeric: 'tabular-nums' }}>
                    {formatScore(plat)}
                  </td>
                  <td className="py-2.5">
                    <ScoreBar value={finalScore} max={100} />
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
