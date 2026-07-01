import { useState } from 'react'
import ScoreBar from './ScoreBar'
import DetailsDrawer from './DetailsDrawer'
import { getRecommendationLabel, getRecommendationType, getCategory, formatScore, formatScoreOne, safeNumber, confidenceBand, qualityLabelColor } from '../recommendation'

export default function ResultsTable({ tags }) {
  const [selectedTag, setSelectedTag] = useState(null)

  if (!tags || tags.length === 0) {
    return <div className="text-xs py-4" style={{ color: 'var(--text-tertiary)' }}>No tags to display.</div>
  }

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs" style={{ borderCollapse: 'collapse', fontFamily: 'var(--font)' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #1C1C1C' }}>
              <th className="text-left py-2 pr-3" style={{ color: 'var(--text-tertiary)', fontWeight: 400 }}>#</th>
              <th className="text-left py-2 pr-3" style={{ color: 'var(--text-tertiary)', fontWeight: 400 }}>TAG</th>
              <th className="text-left py-2 pr-3" style={{ color: 'var(--text-tertiary)', fontWeight: 400 }}>CATEGORY</th>
              <th className="text-left py-2 pr-3" style={{ color: 'var(--text-tertiary)', fontWeight: 400 }}>QUALITY</th>
              <th className="text-left py-2 pr-3" style={{ color: 'var(--text-tertiary)', fontWeight: 400 }}>BAND</th>
              <th className="text-right py-2 pr-3" style={{ color: 'var(--text-tertiary)', fontWeight: 400 }}>FINAL</th>
              <th className="text-right py-2 pr-3" style={{ color: 'var(--text-tertiary)', fontWeight: 400 }}>REL</th>
              <th className="text-right py-2 pr-3" style={{ color: 'var(--text-tertiary)', fontWeight: 400 }}>TREND</th>
              <th className="text-right py-2 pr-3" style={{ color: 'var(--text-tertiary)', fontWeight: 400 }}>COMP</th>
              <th className="text-left py-2" style={{ color: 'var(--text-tertiary)', fontWeight: 400 }}>PLAT</th>
            </tr>
          </thead>
          <tbody>
            {tags.map((tag, i) => {
              const label = getRecommendationLabel(tag)
              const type = getRecommendationType(tag)
              const cat = getCategory(tag)
              const finalScore = safeNumber(tag?.final_score)
              const band = confidenceBand(finalScore)
              const semRel = safeNumber(tag?.semantic_relevance)
              const trend = safeNumber(tag?.trend_score)
              const comp = safeNumber(tag?.competition_score)
              const plat = safeNumber(tag?.platform_fit)
              const qualities = Array.isArray(tag?.quality_labels) ? tag.quality_labels : []
              return (
                <tr
                  key={i}
                  className="cursor-pointer"
                  style={{ borderBottom: '1px solid #141414' }}
                  onClick={() => setSelectedTag(tag)}
                  onMouseEnter={e => e.currentTarget.style.backgroundColor = 'var(--surface)'}
                  onMouseLeave={e => e.currentTarget.style.backgroundColor = 'transparent'}
                >
                  <td className="py-2.5 pr-3" style={{ color: 'var(--text-muted)' }}>{i + 1}</td>
                  <td className="py-2.5 pr-3" style={{ color: 'var(--text)', fontWeight: i === 0 ? 700 : 400 }}>
                    {tag?.is_blue_ocean && (
                      <span style={{ color: 'var(--accent)' }}>● </span>
                    )}
                    {type === 'hashtag' ? '#' : ''}{label}
                  </td>
                  <td className="py-2.5 pr-3">
                    <span className="text-xs px-1.5 py-0.5" style={{ backgroundColor: 'var(--surface-2)', color: 'var(--text-secondary)', border: '1px solid #2A2A2A', fontSize: '10px' }}>
                      {cat}
                    </span>
                  </td>
                  <td className="py-2.5 pr-3">
                    <div className="flex flex-wrap gap-0.5" style={{ maxWidth: '120px' }}>
                      {qualities.slice(0, 2).map((q, qi) => (
                        <span key={qi} className="text-xs px-1 py-0.5" style={{
                          backgroundColor: `${qualityLabelColor(q)}22`,
                          color: qualityLabelColor(q),
                          border: `1px solid ${qualityLabelColor(q)}44`,
                          fontSize: '9px',
                          lineHeight: '1.2',
                        }}>
                          {q}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="py-2.5 pr-3">
                    <span className="text-xs px-1.5 py-0.5" style={{
                      backgroundColor: `${band.color}22`,
                      color: band.color,
                      border: `1px solid ${band.color}44`,
                      fontSize: '10px',
                    }}>
                      {band.label}
                    </span>
                  </td>
                  <td className="py-2.5 pr-3 text-right" style={{ fontVariantNumeric: 'tabular-nums' }}>
                    {formatScoreOne(finalScore)}
                  </td>
                  <td className="py-2.5 pr-3 text-right" style={{ color: 'var(--text-secondary)', fontVariantNumeric: 'tabular-nums' }}>
                    {formatScore(semRel)}
                  </td>
                  <td className="py-2.5 pr-3 text-right" style={{ color: 'var(--text-secondary)', fontVariantNumeric: 'tabular-nums' }}>
                    {formatScore(trend)}
                  </td>
                  <td className="py-2.5 pr-3 text-right" style={{ color: 'var(--text-secondary)', fontVariantNumeric: 'tabular-nums' }}>
                    {formatScore(comp)}
                  </td>
                  <td className="py-2.5">
                    <ScoreBar value={plat} max={100} />
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <div className="mt-2 flex gap-4 text-xs" style={{ color: 'var(--text-tertiary)' }}>
        <span>REL = relevance</span>
        <span>TREND = momentum</span>
        <span>COMP = competition</span>
        <span>PLAT = platform fit</span>
        <span className="ml-auto" style={{ color: 'var(--text-muted)' }}>Click any row for details</span>
      </div>

      {selectedTag && (
        <DetailsDrawer tag={selectedTag} onClose={() => setSelectedTag(null)} />
      )}
    </div>
  )
}
