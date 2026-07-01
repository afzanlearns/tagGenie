import MetricBar from './MetricBar'
import { getRecommendationLabel, getRecommendationType, formatScoreOne, safeNumber, confidenceBand, competitionLevel } from '../recommendation'

export default function DetailsDrawer({ tag, onClose }) {
  if (!tag) return null

  const label = getRecommendationLabel(tag)
  const type = getRecommendationType(tag)
  const cat = tag?.category || 'Keyword'
  const finalScore = safeNumber(tag?.final_score)
  const band = confidenceBand(finalScore)
  const semRel = safeNumber(tag?.semantic_relevance)
  const trend = safeNumber(tag?.trend_score)
  const comp = safeNumber(tag?.competition_score)
  const plat = safeNumber(tag?.platform_fit)
  const histConf = safeNumber(tag?.history_confidence)
  const compLevel = competitionLevel(comp)
  const explanation = tag?.explanation || ''
  const oppScore = safeNumber(tag?.opportunity_score)
  const isBlueOcean = !!tag?.is_blue_ocean
  const isHiddenGem = !!tag?.is_hidden_gem

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      right: 0,
      width: '380px',
      height: '100vh',
      backgroundColor: '#0A0A0A',
      borderLeft: '1px solid #1C1C1C',
      zIndex: 100,
      overflowY: 'auto',
      padding: '20px',
    }}>
      <div className="flex items-center justify-between mb-6">
        <span className="text-xs font-medium" style={{ color: '#555' }}>RECOMMENDATION DETAILS</span>
        <button
          onClick={onClose}
          className="text-xs px-2 py-1"
          style={{ backgroundColor: 'transparent', border: '1px solid #333', color: '#888', cursor: 'pointer' }}
        >
          ✕
        </button>
      </div>

      <div className="mb-4">
        <div className="text-lg font-bold" style={{ color: 'var(--text)' }}>
          {type === 'hashtag' ? '#' : ''}{label}
        </div>
        <div className="flex items-center gap-2 mt-2">
          {cat && (
            <span className="text-xs px-1.5 py-0.5" style={{ backgroundColor: '#141414', color: '#888', border: '1px solid #2A2A2A' }}>
              {cat}
            </span>
          )}
          {type && (
            <span className="text-xs px-1.5 py-0.5" style={{ backgroundColor: '#141414', color: '#888', border: '1px solid #2A2A2A' }}>
              {type.toUpperCase()}
            </span>
          )}
          <span className="text-xs px-1.5 py-0.5" style={{
            backgroundColor: `${band.color}22`,
            color: band.color,
            border: `1px solid ${band.color}44`,
          }}>
            {band.label}
          </span>
        </div>
        {(isBlueOcean || isHiddenGem) && (
          <div className="flex items-center gap-2 mt-2">
            {isBlueOcean && (
              <span className="text-xs" style={{ color: 'var(--accent)' }}>◆ Blue Ocean Opportunity</span>
            )}
            {isHiddenGem && (
              <span className="text-xs" style={{ color: '#8bc34a' }}>◇ Hidden Gem</span>
            )}
          </div>
        )}
      </div>

      <div className="space-y-3 mb-4">
        <MetricBar label="Final Score" value={finalScore} size="md" />
        <MetricBar label="Semantic Relevance" value={semRel} size="md" />
        <MetricBar label="Trend Momentum" value={trend} size="md" />
        <MetricBar label="Competition" value={comp} size="md" color={compLevel.color} />
        <MetricBar label="Platform Fit" value={plat} size="md" />
        <MetricBar label="History Confidence" value={histConf} size="md" />
        {oppScore > 0 && (
          <MetricBar label="Opportunity Score" value={oppScore} size="md" color="var(--accent)" />
        )}
      </div>

      {explanation && (
        <div className="mb-4">
          <div className="text-xs font-medium mb-2" style={{ color: '#555' }}>WHY RECOMMENDED</div>
          <p className="text-xs leading-relaxed" style={{ color: '#888', whiteSpace: 'pre-wrap' }}>
            {explanation}
          </p>
        </div>
      )}
    </div>
  )
}
