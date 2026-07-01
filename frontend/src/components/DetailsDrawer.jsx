import MetricBar from './MetricBar'
import { getRecommendationLabel, getRecommendationType, formatScoreOne, safeNumber } from '../recommendation'

export default function DetailsDrawer({ tag, onClose }) {
  if (!tag) return null

  const label = getRecommendationLabel(tag)
  const type = getRecommendationType(tag)
  const finalScore = safeNumber(tag?.final_score)
  const explanation = tag?.explanation || ''

  const metrics = [
    { label: 'Semantic Relevance', value: safeNumber(tag?.semantic_relevance) },
    { label: 'Trend Momentum', value: safeNumber(tag?.trend_score) },
    { label: 'Competition Level', value: safeNumber(tag?.competition_score) },
    { label: 'Platform Fit', value: safeNumber(tag?.platform_fit) },
    { label: 'History Confidence', value: safeNumber(tag?.history_confidence) },
  ]

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      right: 0,
      width: '360px',
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

      <div className="mb-6">
        <div className="text-lg font-bold" style={{ color: 'var(--text)' }}>
          {type === 'hashtag' ? '#' : ''}{label}
        </div>
        {type && (
          <span className="text-xs px-1.5 py-0.5 mt-1 inline-block" style={{ backgroundColor: '#141414', color: '#888', border: '1px solid #2A2A2A' }}>
            {type.toUpperCase()}
          </span>
        )}
      </div>

      <div className="space-y-3 mb-6">
        {metrics.map(m => (
          <MetricBar key={m.label} label={m.label} value={m.value} size="md" />
        ))}
      </div>

      <div className="mb-6">
        <div className="text-xs font-medium mb-2" style={{ color: '#555' }}>FINAL SCORE</div>
        <div className="text-2xl font-bold" style={{ color: 'var(--accent)' }}>
          {formatScoreOne(finalScore)}
        </div>
      </div>

      {explanation && (
        <div>
          <div className="text-xs font-medium mb-2" style={{ color: '#555' }}>EXPLANATION</div>
          <p className="text-xs leading-relaxed" style={{ color: '#888' }}>
            {explanation}
          </p>
        </div>
      )}
    </div>
  )
}
