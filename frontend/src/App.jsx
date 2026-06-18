import { useState, useEffect } from 'react'
import InputPanel from './components/InputPanel'
import ResultsTable from './components/ResultsTable'
import GapFinder from './components/GapFinder'
import FeedbackSimulator from './components/FeedbackSimulator'
import ComparisonView from './components/ComparisonView'
import DemoMode from './components/DemoMode'

const PLATFORMS = ['LinkedIn', 'Instagram', 'X', 'TikTok']

export default function App() {
  const [topic, setTopic] = useState('')
  const [product, setProduct] = useState('')
  const [platform, setPlatform] = useState('LinkedIn')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [tab, setTab] = useState('results')
  const [demoMode, setDemoMode] = useState(false)

  const handleScore = async () => {
    if (!topic.trim() || !product.trim()) return
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/score', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic: topic.trim(), product: product.trim(), platform, include_baseline: true }),
      })
      if (!res.ok) throw new Error(`Server error: ${res.status}`)
      const data = await res.json()
      setResults(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleDemoSelect = (demoTopic, demoProduct, demoPlatform) => {
    setTopic(demoTopic)
    setProduct(demoProduct)
    setPlatform(demoPlatform)
  }

  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--canvas)', color: 'var(--text)', fontFamily: 'var(--font)' }}>
      <header className="border-b px-6 py-4" style={{ borderColor: '#1C1C1C' }}>
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-lg tracking-tight" style={{ color: 'var(--text)' }}>TagGenie</h1>
            <p className="text-xs mt-0.5" style={{ color: '#555' }}>Distribution Intelligence Engine</p>
          </div>
          {results && (
            <div className="flex items-center gap-3 text-xs" style={{ color: '#666' }}>
              <span>Confidence: {results.confidence}%</span>
              {results.fallback_mode && (
                <span style={{ color: 'var(--accent)' }}>FALLBACK</span>
              )}
            </div>
          )}
          <button
            onClick={() => setDemoMode(!demoMode)}
            className="text-xs px-3 py-1"
            style={{
              backgroundColor: demoMode ? 'var(--accent)' : 'transparent',
              color: demoMode ? 'var(--text)' : '#555',
              border: `1px solid ${demoMode ? 'var(--accent)' : '#333'}`,
              cursor: 'pointer',
            }}
          >
            {demoMode ? 'DEMO ON' : 'DEMO MODE'}
          </button>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        <InputPanel
          topic={topic} setTopic={setTopic}
          product={product} setProduct={setProduct}
          platform={platform} setPlatform={setPlatform}
          platforms={PLATFORMS}
          onScore={handleScore}
          loading={loading}
        />

        <DemoMode
          enabled={demoMode}
          onToggle={() => setDemoMode(false)}
          onDemoSelect={handleDemoSelect}
          onDemoScore={handleScore}
        />

        {error && (
          <div className="mt-4 px-4 py-3 border" style={{ borderColor: 'var(--accent)', color: 'var(--accent)' }}>
            {error}
          </div>
        )}

        {results && (
          <div className="mt-8">
            <div className="flex gap-0 border-b" style={{ borderColor: '#1C1C1C' }}>
              <button
                onClick={() => setTab('results')}
                className={`px-4 py-2 text-xs ${tab === 'results' ? 'border' : ''}`}
                style={{
                  borderColor: tab === 'results' ? '#333' : 'transparent',
                  borderBottom: 'none',
                  color: tab === 'results' ? 'var(--text)' : '#555',
                }}
              >
                RANKED TAGS ({results.ranked_tags.length})
              </button>
              <button
                onClick={() => setTab('gaps')}
                className={`px-4 py-2 text-xs ${tab === 'gaps' ? 'border' : ''}`}
                style={{
                  borderColor: tab === 'gaps' ? '#333' : 'transparent',
                  borderBottom: 'none',
                  color: tab === 'gaps' ? 'var(--text)' : '#555',
                }}
              >
                BLUE OCEAN ({results.gap_tags.length})
              </button>
              <button
                onClick={() => setTab('feedback')}
                className={`px-4 py-2 text-xs ${tab === 'feedback' ? 'border' : ''}`}
                style={{
                  borderColor: tab === 'feedback' ? '#333' : 'transparent',
                  borderBottom: 'none',
                  color: tab === 'feedback' ? 'var(--text)' : '#555',
                }}
              >
                FEEDBACK SIM
              </button>
              <button
                onClick={() => setTab('comparison')}
                className={`px-4 py-2 text-xs ${tab === 'comparison' ? 'border' : ''}`}
                style={{
                  borderColor: tab === 'comparison' ? '#333' : 'transparent',
                  borderBottom: 'none',
                  color: tab === 'comparison' ? 'var(--text)' : '#555',
                }}
              >
                COMPARISON
              </button>
            </div>

            <div className="border border-t-0 p-6" style={{ borderColor: '#1C1C1C' }}>
              {tab === 'results' && <ResultsTable tags={results.ranked_tags} />}
              {tab === 'gaps' && <GapFinder gaps={results.gap_tags} />}
              {tab === 'feedback' && <FeedbackSimulator tags={results.ranked_tags} platform={platform} />}
              {tab === 'comparison' && <ComparisonView tagGenieTags={results.ranked_tags} baselineTags={results.baseline_tags || []} gapTags={results.gap_tags} />}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
