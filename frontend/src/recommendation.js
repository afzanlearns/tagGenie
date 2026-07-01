export function getRecommendationLabel(tag) {
  if (tag == null) return ''
  if (typeof tag === 'string') return tag
  if (tag && typeof tag.tag === 'string') return tag.tag
  if (tag && typeof tag.name === 'string') return tag.name
  return ''
}

export function getRecommendationType(tag) {
  if (tag == null) return 'keyword'
  if (typeof tag === 'string') return 'keyword'
  if (tag && typeof tag.type === 'string') return tag.type
  return 'keyword'
}

export function getCategory(tag) {
  const label = getRecommendationLabel(tag)
  if (!label) return 'Other'
  const type = getRecommendationType(tag)
  if (type === 'hashtag') return 'Hashtag'
  const t = label.toLowerCase()
  if (t.endsWith('industry') || t.includes('sector') || t.includes('market') || t.includes('supply chain')) return 'Industry'
  if (t.includes('brand') || t.endsWith('pro') || t.includes('product')) return 'Brand'
  if (t.includes('lover') || t.includes('enthusiast') || t.includes('community') || t.includes('farmer') || t.includes('buyer') || t.includes('professional')) return 'Audience'
  if (t.includes('trend') || t.includes('innovation') || t.includes('future') || t.includes('best') || t.includes('top')) return 'Topic'
  if (t.includes('roast') || t.includes('brew') || t.includes('process') || t.includes('grade') || t.includes('certification')) return 'Process'
  return 'Industry'
}

export function formatScore(v) {
  if (v == null || typeof v !== 'number') return '—'
  return v.toFixed(0)
}

export function formatScoreOne(v) {
  if (v == null || typeof v !== 'number') return '—'
  return v.toFixed(1)
}

export function safeNumber(v, fallback = 0) {
  if (v == null || typeof v !== 'number') return fallback
  return v
}
