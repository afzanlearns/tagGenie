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
  if (tag == null) return 'Other'
  if (tag && typeof tag.category === 'string' && tag.category) return tag.category
  const label = getRecommendationLabel(tag)
  if (!label) return 'Other'
  const type = getRecommendationType(tag)
  if (type === 'hashtag') return 'Hashtag'
  return 'Keyword'
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

export function confidenceBand(score) {
  if (score >= 90) return { label: 'Excellent', color: '#4caf50' }
  if (score >= 80) return { label: 'Very Strong', color: '#8bc34a' }
  if (score >= 70) return { label: 'Strong', color: '#d42b2b' }
  if (score >= 60) return { label: 'Moderate', color: '#b8860b' }
  return { label: 'Weak', color: '#555' }
}

export function competitionLevel(score) {
  if (score >= 75) return { label: 'Very High', color: '#d42b2b' }
  if (score >= 55) return { label: 'High', color: '#b8860b' }
  if (score >= 35) return { label: 'Moderate', color: '#888' }
  return { label: 'Low', color: '#6a6' }
}

export function qualityLabelColor(label) {
  const colors = {
    'Excellent Match': '#4caf50',
    'Strong Match': '#8bc34a',
    'Trending': '#d42b2b',
    'Rising': '#b8860b',
    'Low Competition': '#6a6',
    'Moderate Competition': '#888',
    'Platform Favorite': '#4caf50',
    'Platform Friendly': '#8bc34a',
    'Blue Ocean': '#d42b2b',
    'Hidden Gem': '#8bc34a',
    'Professional Term': '#4caf50',
    'Creator Friendly': '#b8860b',
    'Emerging': '#4caf50',
  }
  return colors[label] || '#555'
}

export function copyToClipboard(text) {
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text).catch(() => {})
  }
}
