export default function MixSummary({ mix }) {
  if (!mix) return null

  const items = [
    { key: 'hashtags', label: 'Hashtags', color: '#d42b2b' },
    { key: 'products', label: 'Products', color: '#8bc34a' },
    { key: 'industry_terms', label: 'Industry Terms', color: '#4caf50' },
    { key: 'audience', label: 'Audience', color: '#b8860b' },
    { key: 'topics', label: 'Topics', color: 'var(--text-secondary)' },
    { key: 'brands', label: 'Brands', color: 'var(--text-tertiary)' },
    { key: 'keywords', label: 'Keywords', color: 'var(--text-muted)' },
  ]

  const total = items.reduce((s, item) => s + (mix[item.key] || 0), 0)
  if (total === 0) return null

  return (
    <div className="border p-4 mb-4" style={{ borderColor: 'var(--border)' }}>
      <div className="text-xs font-medium mb-3" style={{ color: 'var(--text-tertiary)' }}>RECOMMENDED MIX</div>
      <div className="flex flex-wrap gap-2">
        {items.filter(item => (mix[item.key] || 0) > 0).map(item => (
          <div key={item.key} className="flex items-center gap-1.5 text-xs px-2 py-1" style={{
            backgroundColor: `${item.color}18`,
            border: `1px solid ${item.color}33`,
            color: item.color,
          }}>
            <span className="font-medium">{mix[item.key]}</span>
            <span>{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
