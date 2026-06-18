import { useState, useEffect } from 'react'

const DEMO_TOPICS = [
  {
    topic: 'AI dashcams for fleet safety',
    product: 'Vignan Dashcam AI',
    platform: 'LinkedIn',
  },
  {
    topic: 'real-time GPS telematics for last-mile delivery',
    product: 'AjnaView GPS Suite',
    platform: 'Instagram',
  },
  {
    topic: 'predictive maintenance for commercial fleets',
    product: 'FleetPredict Pro',
    platform: 'X',
  },
]

const STAGES = [
  { key: 'expand', label: 'Topic Expansion' },
  { key: 'score', label: 'Scoring & Ranking' },
  { key: 'baseline', label: 'Baseline Comparison' },
  { key: 'gaps', label: 'Gap Finder' },
  { key: 'rationale', label: 'Rationale Generation' },
  { key: 'feedback', label: 'Simulated Feedback' },
  { key: 'weights', label: 'Weight Shift' },
]

export default function DemoMode({ onDemoScore, onDemoSelect, enabled, onToggle }) {
  const [selectedIdx, setSelectedIdx] = useState(null)
  const [stageIndex, setStageIndex] = useState(-1)
  const [running, setRunning] = useState(false)
  const [stageMessages, setStageMessages] = useState([])
  const [results, setResults] = useState(null)

  const startDemo = async (idx) => {
    const demo = DEMO_TOPICS[idx]
    setSelectedIdx(idx)
    setRunning(true)
    setStageMessages([])
    setResults(null)
    setStageIndex(0)
    onDemoSelect(demo.topic, demo.product, demo.platform)
  }

  useEffect(() => {
    if (!running || stageIndex < 0) return

    const messages = []
    const advanceStage = () => {
      if (stageIndex >= STAGES.length) {
        setRunning(false)
        return
      }
      const stage = STAGES[stageIndex]
      let msg = ''

      switch (stage.key) {
        case 'expand':
          msg = 'Expanding topic with Groq LLM — generating related industry terms, jargon, and adjacent concepts.'
          break
        case 'score':
          msg = 'Scoring candidate tags against Reach, Competition, and Confidence axes using platform-specific weights.'
          break
        case 'baseline':
          msg = 'Running naive TF-IDF baseline for side-by-side comparison — no trend data, no competition scoring.'
          break
        case 'gaps':
          msg = 'Gap Finder scanning for Blue Ocean opportunities — high reach, low competition = first-mover advantage.'
          break
        case 'rationale':
          msg = 'Generating per-tag rationale via Groq LLM — explaining WHY each tag ranks where it does.'
          break
        case 'feedback':
          msg = 'Simulating post engagement — synthetic likes, shares, comments logged to feedback database for the nightly recompute.'
          break
        case 'weights':
          msg = 'Nightly weight shift: platform weights adjusted by ±10% based on tag engagement vs. platform average.'
          break
      }

      setStageMessages(prev => [...prev, { label: stage.label, msg }])

      if (stage.key === 'score' || stage.key === 'baseline') {
        const timer = setTimeout(async () => {
          try {
            const demo = DEMO_TOPICS[selectedIdx]
            const res = await fetch('/api/score', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                topic: demo.topic,
                product: demo.product,
                platform: demo.platform,
                include_baseline: true,
              }),
            })
            const data = await res.json()
            setResults(data)
          } catch (e) {
            setStageMessages(prev => [...prev, { label: 'ERROR', msg: e.message }])
          }
          setStageIndex(prev => prev + 1)
        }, 1500)
        return () => clearTimeout(timer)
      }

      const timer = setTimeout(() => {
        setStageIndex(prev => prev + 1)
      }, 1500)
      return () => clearTimeout(timer)
    }

    advanceStage()
  }, [running, stageIndex, selectedIdx])

  if (!enabled) return null

  return (
    <div className="border p-6 mt-4" style={{ borderColor: 'var(--accent)' }}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="text-xs px-2 py-0.5" style={{ backgroundColor: 'var(--accent)', color: 'var(--text)' }}>
            DEMO MODE
          </span>
          <span className="text-xs" style={{ color: '#555' }}>
            Select a pre-loaded topic to auto-run the full pipeline
          </span>
        </div>
        <button
          onClick={onToggle}
          className="text-xs px-3 py-1"
          style={{ backgroundColor: 'transparent', border: '1px solid #333', color: '#555', cursor: 'pointer' }}
        >
          DISABLE
        </button>
      </div>

      {!running && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
          {DEMO_TOPICS.map((demo, i) => (
            <button
              key={i}
              onClick={() => startDemo(i)}
              className="text-left p-4 border text-xs"
              style={{
                borderColor: '#1C1C1C',
                backgroundColor: 'transparent',
                color: 'var(--text)',
                cursor: 'pointer',
              }}
            >
              <div className="font-medium mb-1">{demo.topic}</div>
              <div style={{ color: '#555' }}>
                {demo.product} · {demo.platform}
              </div>
            </button>
          ))}
        </div>
      )}

      {stageMessages.length > 0 && (
        <div className="border-t pt-4" style={{ borderColor: '#1C1C1C' }}>
          <div className="text-xs font-medium mb-3" style={{ color: 'var(--text)' }}>
            PIPELINE PROGRESS
          </div>
          {stageMessages.map((s, i) => (
            <div key={i} className="flex items-start gap-3 mb-2" style={{ animation: 'none' }}>
              <span className="text-xs flex-shrink-0 mt-0.5" style={{ color: 'var(--accent)' }}>
                [{i + 1}/{STAGES.length}]
              </span>
              <div>
                <span className="text-xs font-medium" style={{ color: 'var(--text)' }}>{s.label}</span>
                <span className="text-xs ml-2" style={{ color: '#555' }}>{s.msg}</span>
              </div>
            </div>
          ))}
          {running && (
            <div className="text-xs mt-2" style={{ color: '#444' }}>
              Running stage {stageIndex + 1} of {STAGES.length}...
            </div>
          )}
          {!running && stageIndex >= STAGES.length && (
            <div className="text-xs mt-3" style={{ color: '#6a6' }}>
              Pipeline complete. All {STAGES.length} stages executed.
            </div>
          )}
        </div>
      )}

      {results && !running && (
        <div className="border-t mt-4 pt-4" style={{ borderColor: '#1C1C1C' }}>
          <div className="text-xs font-medium mb-2" style={{ color: 'var(--text)' }}>
            SCORED RESULTS
          </div>
          <div className="text-xs" style={{ color: '#555' }}>
            {results.ranked_tags?.length || 0} ranked tags · {results.gap_tags?.length || 0} gap tags · Confidence: {results.confidence}% · {results.baseline_tags?.length || 0} baseline tags
          </div>
          {results.timings && (
            <div className="text-xs mt-1" style={{ color: '#444' }}>
              Response time: {results.timings.total}s (scoring: {results.timings.scoring_total}s, baseline: {results.timings.baseline}s)
            </div>
          )}
        </div>
      )}
    </div>
  )
}
