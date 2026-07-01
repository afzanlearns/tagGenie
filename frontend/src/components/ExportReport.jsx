import { getRecommendationLabel, getRecommendationType, safeNumber } from '../recommendation'

export default function ExportReport({ results, topic, product, platform }) {
  if (!results) return null

  const exportJSON = () => {
    const report = {
      exportedAt: new Date().toISOString(),
      topic,
      product,
      platform,
      niche: results.niche,
      confidence: results.confidence,
      recommendations: (results.ranked_tags || []).map(t => ({
        tag: getRecommendationLabel(t),
        type: getRecommendationType(t),
        semantic_relevance: safeNumber(t?.semantic_relevance),
        trend_score: safeNumber(t?.trend_score),
        competition_score: safeNumber(t?.competition_score),
        platform_fit: safeNumber(t?.platform_fit),
        final_score: safeNumber(t?.final_score),
        explanation: t?.explanation || '',
      })),
      blueOcean: (results.gap_tags || []).map(g => ({
        tag: getRecommendationLabel(g),
        semantic_relevance: safeNumber(g?.semantic_relevance),
        trend_score: safeNumber(g?.trend_score),
        competition_score: safeNumber(g?.competition_score),
        reason: g?.reason || '',
      })),
    }
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
    downloadBlob(blob, `taggenie-report-${Date.now()}.json`)
  }

  const exportCSV = () => {
    const sanitize = (v) => `"${String(v == null ? '' : v).replace(/"/g, '""')}"`
    const headers = ['Rank', 'Tag', 'Type', 'Semantic Relevance', 'Trend Score', 'Competition', 'Platform Fit', 'Final Score', 'Explanation']
    const rows = (results.ranked_tags || []).map((t, i) => [
      i + 1,
      getRecommendationLabel(t),
      getRecommendationType(t),
      safeNumber(t?.semantic_relevance),
      safeNumber(t?.trend_score),
      safeNumber(t?.competition_score),
      safeNumber(t?.platform_fit),
      safeNumber(t?.final_score),
      sanitize(t?.explanation),
    ])
    const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    downloadBlob(blob, `taggenie-report-${Date.now()}.csv`)
  }

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs" style={{ color: '#555' }}>EXPORT</span>
      <button onClick={exportJSON} className="text-xs px-2 py-1" style={{ backgroundColor: 'transparent', border: '1px solid #333', color: '#888', cursor: 'pointer' }}>
        JSON
      </button>
      <button onClick={exportCSV} className="text-xs px-2 py-1" style={{ backgroundColor: 'transparent', border: '1px solid #333', color: '#888', cursor: 'pointer' }}>
        CSV
      </button>
    </div>
  )
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
