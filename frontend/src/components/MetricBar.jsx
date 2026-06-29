export default function MetricBar({ label, value, max = 100, color, size = 'sm' }) {
  const pct = Math.min((value / max) * 100, 100)
  const barColor = color || (pct >= 70 ? '#d42b2b' : pct >= 40 ? '#b8860b' : '#555')
  const h = size === 'sm' ? '6px' : '10px'

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs flex-shrink-0" style={{ color: '#555', width: '60px' }}>{label}</span>
      <div className="flex-1" style={{ backgroundColor: '#141414', height: h, position: 'relative' }}>
        <div style={{
          width: `${pct}%`,
          height: '100%',
          backgroundColor: barColor,
          transition: 'width 0.4s',
        }} />
      </div>
      <span className="text-xs flex-shrink-0 text-right" style={{ color: '#888', width: '28px', fontVariantNumeric: 'tabular-nums' }}>
        {value.toFixed(0)}
      </span>
    </div>
  )
}
