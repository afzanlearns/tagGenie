import MetricBar from './MetricBar'
import { getRecommendationLabel, getRecommendationType, formatScoreOne, safeNumber, confidenceBand, competitionLevel, qualityLabelColor, copyToClipboard } from '../recommendation'

function ContributionBar({ label, value, color, max }) {
  const pct = max > 0 ? (value / max) * 100 : 0
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs flex-shrink-0" style={{ color: '#555', width: '80px' }}>{label}</span>
      <div className="flex-1" style={{ backgroundColor: '#141414', height: '6px', position: 'relative' }}>
        <div style={{
          width: `${pct}%`,
          height: '100%',
          backgroundColor: color || '#555',
          transition: 'width 0.5s',
        }} />
      </div>
      <span className="text-xs flex-shrink-0 text-right" style={{ color: '#888', width: '24px', fontVariantNumeric: 'tabular-nums' }}>
        {value.toFixed(1)}
      </span>
    </div>
  )
}

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
  const breakdown = tag?.score_breakdown || {}
  const qualities = Array.isArray(tag?.quality_labels) ? tag.quality_labels : []
  const maxContrib = Math.max(
    safeNumber(breakdown?.semantic_contribution),
    safeNumber(breakdown?.trend_contribution),
    safeNumber(breakdown?.competition_contribution),
    safeNumber(breakdown?.platform_contribution),
    safeNumber(breakdown?.confidence_contribution),
    1
  )

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
        <div className="flex items-center gap-2">
          <button
            onClick={() => copyToClipboard(label)}
            className="text-xs px-2 py-1"
            style={{ backgroundColor: 'transparent', border: '1px solid #333', color: '#888', cursor: 'pointer' }}
            title="Copy tag name"
          >
            📋
          </button>
          <button
            onClick={onClose}
            className="text-xs px-2 py-1"
            style={{ backgroundColor: 'transparent', border: '1px solid #333', color: '#888', cursor: 'pointer' }}
          >
            ✕
          </button>
        </div>
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

      {qualities.length > 0 && (
        <div className="mb-4">
          <div className="text-xs font-medium mb-2" style={{ color: '#555' }}>QUALITY INDICATORS</div>
          <div className="flex flex-wrap gap-1.5">
            {qualities.map((q, qi) => (
              <span key={qi} className="text-xs px-2 py-0.5" style={{
                backgroundColor: `${qualityLabelColor(q)}22`,
                color: qualityLabelColor(q),
                border: `1px solid ${qualityLabelColor(q)}44`,
              }}>
                {q}
              </span>
            ))}
          </div>
        </div>
      )}

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

      {maxContrib > 0 && (
        <div className="mb-4">
          <div className="text-xs font-medium mb-2" style={{ color: '#555' }}>SCORE BREAKDOWN</div>
          <div className="space-y-1">
            <ContributionBar label="Semantic" value={safeNumber(breakdown?.semantic_contribution)} color="#d42b2b" max={maxContrib} />
            <ContributionBar label="Trend" value={safeNumber(breakdown?.trend_contribution)} color="#b8860b" max={maxContrib} />
            <ContributionBar label="Competition" value={safeNumber(breakdown?.competition_contribution)} color="#555" max={maxContrib} />
            <ContributionBar label="Platform" value={safeNumber(breakdown?.platform_contribution)} color="#4caf50" max={maxContrib} />
            <ContributionBar label="Confidence" value={safeNumber(breakdown?.confidence_contribution)} color="#8bc34a" max={maxContrib} />
          </div>
        </div>
      )}

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
