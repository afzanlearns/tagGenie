import { useState, useEffect } from 'react'

const STAGES = [
  'Building candidate set...',
  'Analyzing semantic relevance...',
  'Checking trends...',
  'Estimating competition...',
  'Ranking results...',
  'Rendering dashboard...',
]

export default function PipelineStages({ active }) {
  const [current, setCurrent] = useState(0)

  useEffect(() => {
    if (!active) {
      setCurrent(0)
      return
    }
    const timer = setInterval(() => {
      setCurrent(prev => Math.min(prev + 1, STAGES.length - 1))
    }, 2000)
    return () => clearInterval(timer)
  }, [active])

  if (!active) return null

  return (
    <div className="border p-6 mb-4" style={{ borderColor: 'var(--border)' }}>
      <div className="flex items-center gap-3 mb-4">
        <div className="w-2 h-2 rounded-full" style={{ backgroundColor: 'var(--accent)', animation: 'pulse 1s infinite' }} />
        <span className="text-xs font-medium" style={{ color: 'var(--text)' }}>ANALYZING</span>
        <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{current + 1} / {STAGES.length}</span>
      </div>
      <div className="space-y-1">
        {STAGES.map((stage, i) => (
          <div key={i} className="flex items-center gap-2 text-xs py-0.5">
            <span style={{
              color: i < current ? '#6a6' : i === current ? 'var(--accent)' : 'var(--border-light)',
              transition: 'color 0.3s',
            }}>
              {i < current ? '✓' : i === current ? '→' : '○'}
            </span>
            <span style={{
              color: i <= current ? '#ccc' : 'var(--text-muted)',
              transition: 'color 0.3s',
            }}>
              {stage}
            </span>
          </div>
        ))}
      </div>
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
      `}</style>
    </div>
  )
}
