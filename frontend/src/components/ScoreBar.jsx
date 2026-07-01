export default function ScoreBar({ value, max = 100 }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100))
  const isCritical = pct >= 75

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1" style={{ backgroundColor: 'var(--border)', borderRadius: '0' }}>
        <div
          className="h-full"
          style={{
            width: `${pct}%`,
            backgroundColor: isCritical ? 'var(--accent)' : 'var(--text)',
            borderRadius: '0',
            transition: 'width 0.3s ease',
          }}
        />
      </div>
      <span className="text-xs" style={{ color: isCritical ? 'var(--accent)' : 'var(--text-tertiary)' }}>
        {pct.toFixed(0)}
      </span>
    </div>
  )
}
