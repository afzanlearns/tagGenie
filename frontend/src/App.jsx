import { useState, useEffect } from 'react'
import InputPanel from './components/InputPanel'
import ResultsTable from './components/ResultsTable'
import GapFinder from './components/GapFinder'
import FeedbackSimulator from './components/FeedbackSimulator'
import ComparisonView from './components/ComparisonView'
import DemoMode from './components/DemoMode'
import AnalyticsCards from './components/AnalyticsCards'
import PlatformComparison from './components/PlatformComparison'
import RecommendationHistory, { loadHistory, saveEntry, clearHistory } from './components/RecommendationHistory'
import ExportReport from './components/ExportReport'
import EmptyState from './components/EmptyState'
import { api, isGuest } from './api'

function slugify(text) {
  if (!text) return 'untitled'
  let s = text.trim().toLowerCase()
  s = s.normalize('NFKD').replace(/[^\x00-\x7F]/g, '')
  s = s.replace(/[^a-z0-9_-]/g, '-')
  s = s.replace(/[-_]+/g, '-')
  s = s.replace(/^-+|-+$/g, '')
  return s || 'untitled'
}

const PLATFORMS = ['LinkedIn', 'Instagram', 'X', 'TikTok']

export default function App({ onLogout }) {
  const [topic, setTopic] = useState('')
  const [product, setProduct] = useState('')
  const [platform, setPlatform] = useState('LinkedIn')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [tab, setTab] = useState('results')
  const [demoMode, setDemoMode] = useState(false)
  const [historyEntries, setHistoryEntries] = useState(loadHistory)

  const [niches, setNiches] = useState([])
  const [activeNiche, setActiveNiche] = useState('gps-telematics')
  const [showNichePanel, setShowNichePanel] = useState(false)

  useEffect(() => {
    api('/api/niches')
      .then(data => {
        setNiches(data.niches || [])
        setActiveNiche(data.active || 'gps-telematics')
      })
      .catch(() => {})
  }, [])

  const handleNicheSwitch = async (nicheId) => {
    try {
      await api('/api/niches/switch', {
        method: 'POST',
        body: { niche_id: nicheId },
      })
      setActiveNiche(nicheId)
      setResults(null)
    } catch (e) {
      console.error(e)
    }
  }

  const handleScore = async () => {
    if (!topic.trim() || !product.trim()) return
    setLoading(true)
    setError(null)
    try {
      const data = await api('/api/score', {
        method: 'POST',
        body: {
          topic: topic.trim(),
          product: product.trim(),
          platform,
          niche: activeNiche,
          include_baseline: true,
        },
      })
      setResults(data)
      const updated = saveEntry({
        topic: topic.trim(),
        product: product.trim(),
        platform,
        niche: activeNiche,
        tags: data.ranked_tags?.length || 0,
      })
      setHistoryEntries(updated)
      setTab('results')
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

  const handleHistoryRestore = (entry) => {
    setTopic(entry.topic)
    setProduct(entry.product)
    setPlatform(entry.platform)
    if (entry.niche && entry.niche !== activeNiche) {
      handleNicheSwitch(entry.niche)
    }
    setTab('results')
  }

  const handleClearHistory = () => {
    clearHistory()
    setHistoryEntries([])
  }

  const currentNicheName = niches.find(n => n.niche_id === activeNiche)?.display_name || activeNiche

  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--canvas)', color: 'var(--text)', fontFamily: 'var(--font)' }}>
      <header className="border-b px-6 py-4" style={{ borderColor: '#1C1C1C' }}>
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div>
              <h1 className="text-lg tracking-tight" style={{ color: 'var(--text)' }}>TagGenie</h1>
              <p className="text-xs mt-0.5" style={{ color: '#555' }}>Distribution Intelligence Engine</p>
            </div>
            <div className="flex items-center gap-2 ml-6 pl-6 border-l" style={{ borderColor: '#1C1C1C' }}>
              <span className="text-xs" style={{ color: '#555' }}>NICHE</span>
              <select
                value={activeNiche}
                onChange={e => handleNicheSwitch(e.target.value)}
                className="text-xs px-2 py-1 border appearance-none focus:outline-none"
                style={{
                  backgroundColor: 'transparent',
                  borderColor: '#333',
                  color: 'var(--text)',
                  borderRadius: '0',
                }}
              >
                {niches.map(n => (
                  <option key={n.niche_id} value={n.niche_id}>{n.display_name}</option>
                ))}
              </select>
              <button
                onClick={() => setShowNichePanel(!showNichePanel)}
                className="text-xs px-2 py-1"
                style={{
                  backgroundColor: 'transparent',
                  border: '1px solid #333',
                  color: '#888',
                  cursor: 'pointer',
                }}
              >
                + CUSTOM
              </button>
            </div>
          </div>
          {results && (
            <div className="flex items-center gap-3 text-xs" style={{ color: '#666' }}>
              <span>Niche: {currentNicheName}</span>
              <span>Confidence: {results.confidence}%</span>
              {results.fallback_mode && (
                <span style={{ color: 'var(--accent)' }}>FALLBACK</span>
              )}
              <ExportReport results={results} topic={topic} product={product} platform={platform} />
            </div>
          )}
          <div className="flex items-center gap-2">
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
            {isGuest() && (
              <span
                className="text-xs px-2 py-0.5"
                style={{
                  backgroundColor: '#222',
                  color: '#aa6',
                  border: '1px solid #443',
                }}
              >
                GUEST
              </span>
            )}
            {onLogout && (
              <button
                onClick={onLogout}
                className="text-xs px-3 py-1"
                style={{
                  backgroundColor: 'transparent',
                  color: '#555',
                  border: '1px solid #333',
                  cursor: 'pointer',
                }}
              >
                {isGuest() ? 'LEAVE GUEST MODE' : 'LOG OUT'}
              </button>
            )}
          </div>
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
          activeNiche={currentNicheName}
        />

        {showNichePanel && (
          <CustomNichePanel
            onCreated={(newNiche) => {
              setNiches(prev => [...prev, newNiche])
              handleNicheSwitch(newNiche.niche_id)
              setShowNichePanel(false)
            }}
            onClose={() => setShowNichePanel(false)}
          />
        )}

        <DemoMode
          enabled={demoMode}
          onToggle={() => setDemoMode(false)}
          onDemoSelect={handleDemoSelect}
          onDemoScore={handleScore}
          activeNiche={activeNiche}
        />

        {error && (
          <div className="mt-4 px-4 py-3 border" style={{ borderColor: 'var(--accent)', color: 'var(--accent)' }}>
            {error}
          </div>
        )}

        {!results && !loading && !error && (
          <EmptyState
            hasHistory={historyEntries.length > 0}
            onDemoSelect={handleDemoSelect}
          />
        )}

        {results && (
          <div className="mt-8">
            <AnalyticsCards results={results} />

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
              <button
                onClick={() => setTab('platform')}
                className={`px-4 py-2 text-xs ${tab === 'platform' ? 'border' : ''}`}
                style={{
                  borderColor: tab === 'platform' ? '#333' : 'transparent',
                  borderBottom: 'none',
                  color: tab === 'platform' ? 'var(--text)' : '#555',
                }}
              >
                PLATFORMS
              </button>
              <button
                onClick={() => setTab('history')}
                className={`px-4 py-2 text-xs ${tab === 'history' ? 'border' : ''}`}
                style={{
                  borderColor: tab === 'history' ? '#333' : 'transparent',
                  borderBottom: 'none',
                  color: tab === 'history' ? 'var(--text)' : '#555',
                }}
              >
                HISTORY ({historyEntries.length})
              </button>
            </div>

            <div className="border border-t-0 p-6" style={{ borderColor: '#1C1C1C' }}>
              {tab === 'results' && <ResultsTable tags={results.ranked_tags} />}
              {tab === 'gaps' && <GapFinder gaps={results.gap_tags} />}
              {tab === 'feedback' && <FeedbackSimulator tags={results.ranked_tags} platform={platform} niche={activeNiche} />}
              {tab === 'comparison' && <ComparisonView tagGenieTags={results.ranked_tags} baselineTags={results.baseline_tags || []} gapTags={results.gap_tags} />}
              {tab === 'platform' && (
                <PlatformComparison
                  topic={topic}
                  product={product}
                  niche={activeNiche}
                  onSelectTag={(tag) => {}}
                />
              )}
              {tab === 'history' && (
                <RecommendationHistory
                  entries={historyEntries}
                  onRestore={handleHistoryRestore}
                  onClear={handleClearHistory}
                />
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

function CustomNichePanel({ onCreated, onClose }) {
  const [step, setStep] = useState('input')
  const [nicheId, setNicheId] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [description, setDescription] = useState('')
  const [postsText, setPostsText] = useState('')
  const [generating, setGenerating] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const [draft, setDraft] = useState(null)
  const [editCorpus, setEditCorpus] = useState('')
  const [editJargon, setEditJargon] = useState('')
  const [editTopics, setEditTopics] = useState('')

  const samplePosts = () => postsText
    .split('\n')
    .map(p => p.trim())
    .filter(p => p.length > 10)

  const handleGenerate = async () => {
    const posts = samplePosts()
    if (posts.length < 5) {
      setError(`Need at least 5 sample posts (got ${posts.length})`)
      return
    }
    setGenerating(true)
    setError('')
    try {
      const data = await api('/api/niches/generate-draft', {
        method: 'POST',
        body: {
          niche_id: slugify(nicheId),
          display_name: displayName.trim(),
          sample_posts: posts,
        },
      })
      const d = data.draft
      setDraft(d)
      setEditCorpus(d.corpus ? d.corpus.join('\n') : '')
      setEditJargon(JSON.stringify(d.jargon || {}, null, 2))
      setEditTopics(d.sample_topics ? d.sample_topics.join('\n') : '')
      setDescription(d.description || '')
      setStep('review')
    } catch (e) {
      setError(e.message)
    } finally {
      setGenerating(false)
    }
  }

  const handleSave = async () => {
    const corpus = editCorpus.split('\n').map(l => l.trim()).filter(l => l.length > 5)
    const topics = editTopics.split('\n').map(l => l.trim()).filter(l => l.length > 2)
    let jargon
    try {
      jargon = JSON.parse(editJargon)
    } catch {
      setError('Invalid JSON in jargon field')
      return
    }
    if (corpus.length < 3) {
      setError('Need at least 3 corpus entries')
      return
    }
    setSaving(true)
    setError('')
    try {
      const body = {
        niche_id: draft.niche_id,
        display_name: draft.display_name,
        description: description.trim(),
        sample_posts: draft.sample_posts,
        corpus,
        jargon,
        sample_topics: topics,
      }
      if (draft.profile) {
        body.profile = draft.profile
      }
      const data = await api('/api/niches/save-draft', {
        method: 'POST',
        body,
      })
      onCreated(data.niche)
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  if (step === 'review' && draft) {
    return (
      <div className="border p-6 mt-4" style={{ borderColor: 'var(--accent)' }}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <span className="text-xs px-2 py-0.5" style={{ backgroundColor: 'var(--accent)', color: 'var(--text)' }}>
              REVIEW NICHE: {draft.display_name}
            </span>
            <span className="text-xs" style={{ color: '#555' }}>
              Edit the auto-generated content before saving
            </span>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setStep('input')}
              className="text-xs px-3 py-1"
              style={{ backgroundColor: 'transparent', border: '1px solid #333', color: '#888', cursor: 'pointer' }}
            >
              ← BACK
            </button>
            <button
              onClick={onClose}
              className="text-xs px-3 py-1"
              style={{ backgroundColor: 'transparent', border: '1px solid #333', color: '#555', cursor: 'pointer' }}
            >
              CANCEL
            </button>
          </div>
        </div>

        <div className="mb-4">
          <label className="block text-xs mb-1.5" style={{ color: '#555' }}>DESCRIPTION</label>
          <input
            type="text"
            value={description}
            onChange={e => setDescription(e.target.value)}
            className="w-full px-3 py-2 text-sm border focus:outline-none"
            style={{ backgroundColor: 'transparent', borderColor: '#333', color: 'var(--text)' }}
          />
        </div>

        <div className="mb-4">
          <label className="block text-xs mb-1.5" style={{ color: '#555' }}>
            SAMPLE TOPICS (one per line)
          </label>
          <textarea
            value={editTopics}
            onChange={e => setEditTopics(e.target.value)}
            rows={3}
            className="w-full px-3 py-2 text-sm border focus:outline-none"
            style={{ backgroundColor: 'transparent', borderColor: '#333', color: 'var(--text)', resize: 'vertical' }}
          />
        </div>

        <div className="mb-4">
          <label className="block text-xs mb-1.5" style={{ color: '#555' }}>
            CORPUS / SEED POSTS (one per line, editable)
          </label>
          <textarea
            value={editCorpus}
            onChange={e => setEditCorpus(e.target.value)}
            rows={8}
            className="w-full px-3 py-2 text-sm border focus:outline-none font-mono"
            style={{ backgroundColor: 'transparent', borderColor: '#333', color: 'var(--text)', resize: 'vertical', fontSize: '11px' }}
          />
        </div>

        {draft.profile && (
          <VocabularyViewer profile={draft.profile} />
        )}

        <div className="flex items-center gap-3">
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-6 py-2 text-xs font-medium disabled:opacity-30"
            style={{
              backgroundColor: 'var(--accent)',
              color: 'var(--text)',
              border: 'none',
              cursor: saving ? 'wait' : 'pointer',
            }}
          >
            {saving ? 'SAVING...' : 'SAVE NICHE'}
          </button>
          <button
            onClick={() => setStep('input')}
            className="px-4 py-2 text-xs"
            style={{ backgroundColor: 'transparent', border: '1px solid #333', color: '#888', cursor: 'pointer' }}
          >
            REGENERATE
          </button>
          <span className="text-xs" style={{ color: '#555' }}>
            {editCorpus.split('\n').filter(l => l.trim().length > 5).length} corpus entries
          </span>
        </div>

        {draft._fallback && (
          <div className="mt-3 text-xs" style={{ color: '#aa6' }}>
            LLM unavailable, used heuristic fallback. Review the generated content carefully.
          </div>
        )}

        {error && (
          <div className="mt-3 text-xs" style={{ color: 'var(--accent)' }}>
            {error}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="border p-6 mt-4" style={{ borderColor: 'var(--accent)' }}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="text-xs px-2 py-0.5" style={{ backgroundColor: 'var(--accent)', color: 'var(--text)' }}>
            CREATE CUSTOM NICHE
          </span>
          <span className="text-xs" style={{ color: '#555' }}>
            Paste 5+ sample posts to generate a draft, then review before saving
          </span>
        </div>
        <button
          onClick={onClose}
          className="text-xs px-3 py-1"
          style={{ backgroundColor: 'transparent', border: '1px solid #333', color: '#555', cursor: 'pointer' }}
        >
          CLOSE
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
        <div>
          <label className="block text-xs mb-1.5" style={{ color: '#555' }}>NICHE ID</label>
          <input
            type="text"
            value={nicheId}
            onChange={e => setNicheId(e.target.value)}
            placeholder="e.g., my-industry"
            className="w-full px-3 py-2 text-sm border focus:outline-none"
            style={{ backgroundColor: 'transparent', borderColor: '#333', color: 'var(--text)' }}
          />
        </div>
        <div>
          <label className="block text-xs mb-1.5" style={{ color: '#555' }}>DISPLAY NAME</label>
          <input
            type="text"
            value={displayName}
            onChange={e => setDisplayName(e.target.value)}
            placeholder="e.g., My Industry"
            className="w-full px-3 py-2 text-sm border focus:outline-none"
            style={{ backgroundColor: 'transparent', borderColor: '#333', color: 'var(--text)' }}
          />
        </div>
        <div>
          <label className="block text-xs mb-1.5" style={{ color: '#555' }}>DESCRIPTION (optional)</label>
          <input
            type="text"
            value={description}
            onChange={e => setDescription(e.target.value)}
            placeholder="Brief description of the industry"
            className="w-full px-3 py-2 text-sm border focus:outline-none"
            style={{ backgroundColor: 'transparent', borderColor: '#333', color: 'var(--text)' }}
          />
        </div>
      </div>

      <div className="mb-4">
        <label className="block text-xs mb-1.5" style={{ color: '#555' }}>
          SAMPLE POSTS (one per line, minimum 5)
        </label>
        <textarea
          value={postsText}
          onChange={e => setPostsText(e.target.value)}
          placeholder="Paste one social media post per line from your industry"
          rows={8}
          className="w-full px-3 py-2 text-sm border focus:outline-none"
          style={{ backgroundColor: 'transparent', borderColor: '#333', color: 'var(--text)', resize: 'vertical' }}
        />
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="px-6 py-2 text-xs font-medium disabled:opacity-30"
          style={{
            backgroundColor: 'var(--accent)',
            color: 'var(--text)',
            border: 'none',
            cursor: generating ? 'wait' : 'pointer',
          }}
        >
          {generating ? 'GENERATING...' : 'GENERATE DRAFT'}
        </button>
        {samplePosts().length > 0 && (
          <span className="text-xs" style={{ color: '#555' }}>
            {samplePosts().length} posts
          </span>
        )}
      </div>

      {error && (
        <div className="mt-3 text-xs" style={{ color: 'var(--accent)' }}>
          {error}
        </div>
      )}
    </div>
  )
}

function VocabularyViewer({ profile }) {
  const categories = [
    { key: 'industry_terms', label: 'INDUSTRY TERMS' },
    { key: 'products', label: 'PRODUCTS' },
    { key: 'topics', label: 'TOPICS' },
    { key: 'hashtags', label: 'HASHTAGS' },
    { key: 'brands', label: 'BRANDS' },
    { key: 'audience', label: 'AUDIENCE' },
  ]

  return (
    <div className="mb-4">
      <label className="block text-xs mb-2" style={{ color: '#555' }}>
        INDUSTRY VOCABULARY PROFILE
      </label>
      <div className="grid grid-cols-2 gap-2">
        {categories.map(cat => {
          const terms = profile[cat.key] || []
          return (
            <div key={cat.key} className="border p-2" style={{ borderColor: '#1C1C1C' }}>
              <div className="text-xs mb-1" style={{ color: 'var(--accent)' }}>{cat.label}</div>
              <div className="text-xs" style={{ color: '#888', maxHeight: '120px', overflowY: 'auto' }}>
                {terms.length > 0
                  ? terms.map((t, i) => (
                      <span key={i} className="inline-block mr-1 mb-0.5 px-1.5 py-0.5"
                        style={{ backgroundColor: '#141414', color: '#ccc' }}>
                        {t}
                      </span>
                    ))
                  : <span style={{ color: '#444' }}>—</span>
                }
              </div>
            </div>
          )
        })}
      </div>
      {profile.synonyms && Object.keys(profile.synonyms).length > 0 && (
        <div className="mt-2 border p-2" style={{ borderColor: '#1C1C1C' }}>
          <div className="text-xs mb-1" style={{ color: 'var(--accent)' }}>SYNONYMS</div>
          <div className="text-xs" style={{ color: '#888' }}>
            {Object.entries(profile.synonyms).map(([key, vals]) => (
              <div key={key} className="mb-0.5">
                <span style={{ color: '#ccc' }}>{key}</span>
                <span style={{ color: '#555' }}> → {vals.join(', ')}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
