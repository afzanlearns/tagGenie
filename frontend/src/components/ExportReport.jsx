import { getRecommendationLabel, getRecommendationType, safeNumber } from '../recommendation'
import { api } from '../api'

export default function ExportReport({ results, topic, product, platform, currentUser }) {
  if (!results) return null

  const sanitize = (v) => `"${String(v == null ? '' : v).replace(/"/g, '""')}"`

  const buildReport = () => ({
    exportedAt: new Date().toISOString(),
    topic,
    product,
    platform,
    niche: results.niche,
    confidence: results.confidence,
    fallback_mode: results.fallback_mode,
    recommendations: (results.ranked_tags || []).map(t => ({
      tag: getRecommendationLabel(t),
      type: getRecommendationType(t),
      category: t?.category || '',
      confidence_band: t?.confidence_band || '',
      semantic_relevance: safeNumber(t?.semantic_relevance),
      trend_score: safeNumber(t?.trend_score),
      competition_score: safeNumber(t?.competition_score),
      platform_fit: safeNumber(t?.platform_fit),
      history_confidence: safeNumber(t?.history_confidence),
      final_score: safeNumber(t?.final_score),
      opportunity_score: safeNumber(t?.opportunity_score),
      is_blue_ocean: !!t?.is_blue_ocean,
      is_hidden_gem: !!t?.is_hidden_gem,
      is_high_competition: !!t?.is_high_competition,
      explanation: t?.explanation || '',
    })),
    blueOcean: (results.gap_tags || []).map(g => ({
      tag: getRecommendationLabel(g),
      opportunity_score: safeNumber(g?.opportunity_score),
      semantic_relevance: safeNumber(g?.semantic_relevance),
      trend_score: safeNumber(g?.trend_score),
      competition_score: safeNumber(g?.competition_score),
      reason: g?.reason || '',
    })),
    highCompetition: (results.high_competition_tags || []).map(h => ({
      tag: getRecommendationLabel(h),
      competition_score: safeNumber(h?.competition_score),
    })),
    hiddenGems: (results.hidden_gems || []).map(h => ({
      tag: getRecommendationLabel(h),
      semantic_relevance: safeNumber(h?.semantic_relevance),
      competition_score: safeNumber(h?.competition_score),
      trend_score: safeNumber(h?.trend_score),
    })),
    rejectedCandidates: (results.rejected_candidates || []).map(r => ({
      tag: getRecommendationLabel(r),
      reason: r?.reason || '',
    })),
    analytics: results.analytics || {},
    mix_summary: results.mix_summary || {},
    timings: results.timings || {},
  })

  const exportJSON = () => {
    const blob = new Blob([JSON.stringify(buildReport(), null, 2)], { type: 'application/json' })
    downloadBlob(blob, `taggenie-report-${Date.now()}.json`)
  }

  const exportCSV = () => {
    const headers = ['Rank', 'Tag', 'Type', 'Category', 'Band', 'Relevance', 'Trend', 'Competition', 'Platform Fit', 'Confidence', 'Final Score', 'Blue Ocean', 'Hidden Gem', 'Explanation']
    const rows = (results.ranked_tags || []).map((t, i) => [
      i + 1,
      sanitize(getRecommendationLabel(t)),
      getRecommendationType(t),
      t?.category || '',
      t?.confidence_band || '',
      safeNumber(t?.semantic_relevance),
      safeNumber(t?.trend_score),
      safeNumber(t?.competition_score),
      safeNumber(t?.platform_fit),
      safeNumber(t?.history_confidence),
      safeNumber(t?.final_score),
      t?.is_blue_ocean ? 'Yes' : 'No',
      t?.is_hidden_gem ? 'Yes' : 'No',
      sanitize(t?.explanation),
    ])
    const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    downloadBlob(blob, `taggenie-report-${Date.now()}.csv`)
  }

  const exportPDF = async () => {
    const report = buildReport()
    const html = `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>TagGenie Report</title>
<style>
body { font-family: -apple-system, sans-serif; padding: 20px; color: #222; }
h1 { font-size: 18px; margin-bottom: 4px; }
.meta { font-size: 12px; color: #666; margin-bottom: 20px; }
table { width: 100%; border-collapse: collapse; font-size: 11px; margin-bottom: 20px; }
th, td { padding: 6px 8px; text-align: left; border-bottom: 1px solid #ddd; }
th { background: #f5f5f5; font-weight: 600; }
.section { font-size: 14px; font-weight: 600; margin: 16px 0 8px; }
</style></head><body>
<h1>TagGenie Intelligence Report</h1>
<div class="meta">Topic: ${sanitize(topic)} | Product: ${sanitize(product)} | Platform: ${platform} | Niche: ${results.niche} | Confidence: ${results.confidence}% | ${new Date().toISOString().slice(0, 10)}</div>

<div class="section">Recommendations</div>
<table><tr><th>#</th><th>Tag</th><th>Category</th><th>Band</th><th>Rel</th><th>Trend</th><th>Comp</th><th>Plat</th><th>Score</th></tr>
${report.recommendations.map((r, i) => `<tr><td>${i + 1}</td><td>${sanitize(r.tag)}</td><td>${r.category}</td><td>${r.confidence_band}</td><td>${r.semantic_relevance.toFixed(0)}</td><td>${r.trend_score.toFixed(0)}</td><td>${r.competition_score.toFixed(0)}</td><td>${r.platform_fit.toFixed(0)}</td><td>${r.final_score.toFixed(0)}</td></tr>`).join('')}
</table>

${report.blueOcean.length ? `<div class="section">Blue Ocean Opportunities</div>
<table><tr><th>Tag</th><th>Opportunity</th><th>Rel</th><th>Trend</th><th>Comp</th></tr>
${report.blueOcean.map(g => `<tr><td>${sanitize(g.tag)}</td><td>${g.opportunity_score.toFixed(0)}</td><td>${g.semantic_relevance.toFixed(0)}</td><td>${g.trend_score.toFixed(0)}</td><td>${g.competition_score.toFixed(0)}</td></tr>`).join('')}
</table>` : ''}

${report.analytics ? `<div class="section">Analytics</div>
<table><tr><th>Metric</th><th>Value</th></tr>
<tr><td>Average Relevance</td><td>${report.analytics.avg_relevance?.toFixed(0) || '—'}</td></tr>
<tr><td>Average Trend</td><td>${report.analytics.avg_trend?.toFixed(0) || '—'}</td></tr>
<tr><td>Average Competition</td><td>${report.analytics.avg_competition?.toFixed(0) || '—'}</td></tr>
<tr><td>Average Platform Fit</td><td>${report.analytics.avg_platform_fit?.toFixed(0) || '—'}</td></tr>
<tr><td>Average Final Score</td><td>${report.analytics.avg_final_score?.toFixed(0) || '—'}</td></tr>
<tr><td>Diversity</td><td>${report.analytics.diversity?.toFixed(0) || '—'}%</td></tr>
<tr><td>Total Evaluated</td><td>${report.analytics.total_candidates_evaluated || 0}</td></tr>
</table>` : ''}
</body></html>`

    const blob = new Blob([html], { type: 'text/html' })
    downloadBlob(blob, `taggenie-report-${Date.now()}.html`)
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
      <button onClick={exportPDF} className="text-xs px-2 py-1" style={{ backgroundColor: 'transparent', border: '1px solid #333', color: '#888', cursor: 'pointer' }}>
        HTML
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
