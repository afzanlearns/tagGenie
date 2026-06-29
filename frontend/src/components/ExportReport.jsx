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
      recommendations: results.ranked_tags?.map(t => ({
        tag: t.tag,
        type: t.type,
        semantic_relevance: t.semantic_relevance,
        trend_score: t.trend_score,
        competition_score: t.competition_score,
        platform_fit: t.platform_fit,
        final_score: t.final_score,
        explanation: t.explanation,
      })) || [],
      blueOcean: results.gap_tags?.map(g => ({
        tag: g.tag,
        semantic_relevance: g.semantic_relevance,
        trend_score: g.trend_score,
        competition_score: g.competition_score,
        reason: g.reason,
      })) || [],
    }
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
    downloadBlob(blob, `taggenie-report-${Date.now()}.json`)
  }

  const exportCSV = () => {
    const headers = ['Rank', 'Tag', 'Type', 'Semantic Relevance', 'Trend Score', 'Competition', 'Platform Fit', 'Final Score', 'Explanation']
    const rows = (results.ranked_tags || []).map((t, i) => [
      i + 1, t.tag, t.type, t.semantic_relevance, t.trend_score,
      t.competition_score, t.platform_fit, t.final_score,
      `"${(t.explanation || '').replace(/"/g, '""')}"`,
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
