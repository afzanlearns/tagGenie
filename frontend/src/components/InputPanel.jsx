import PipelineStages from './PipelineStages'

export default function InputPanel({ topic, setTopic, product, setProduct, platform, setPlatform, platforms, onScore, loading }) {
  return (
    <div className="border p-6" style={{ borderColor: 'var(--border)' }}>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
        <div>
          <label className="block text-xs mb-1.5" style={{ color: 'var(--text-tertiary)' }}>TOPIC</label>
          <input
            type="text"
            value={topic}
            onChange={e => setTopic(e.target.value)}
            placeholder="e.g., AI dashcams for fleet safety"
            className="w-full px-3 py-2 text-sm border focus:outline-none"
            style={{
              backgroundColor: 'transparent',
              borderColor: 'var(--border-light)',
              color: 'var(--text)',
            }}
            onKeyDown={e => e.key === 'Enter' && onScore()}
          />
        </div>
        <div>
          <label className="block text-xs mb-1.5" style={{ color: 'var(--text-tertiary)' }}>PRODUCT</label>
          <input
            type="text"
            value={product}
            onChange={e => setProduct(e.target.value)}
            placeholder="e.g., Vignan Dashcam AI"
            className="w-full px-3 py-2 text-sm border focus:outline-none"
            style={{
              backgroundColor: 'transparent',
              borderColor: 'var(--border-light)',
              color: 'var(--text)',
            }}
            onKeyDown={e => e.key === 'Enter' && onScore()}
          />
        </div>
        <div>
          <label className="block text-xs mb-1.5" style={{ color: 'var(--text-tertiary)' }}>PLATFORM</label>
          <select
            value={platform}
            onChange={e => setPlatform(e.target.value)}
            className="w-full px-3 py-2 text-sm border focus:outline-none appearance-none"
            style={{
              backgroundColor: 'var(--canvas)',
              borderColor: 'var(--border-light)',
              color: 'var(--text)',
              borderRadius: '0',
            }}
          >
            {platforms.map(p => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        </div>
      </div>
      <button
        onClick={onScore}
        disabled={loading || !topic.trim() || !product.trim()}
        className="px-6 py-2 text-xs font-medium disabled:opacity-30"
        style={{
          backgroundColor: 'var(--accent)',
          color: 'var(--text)',
          border: 'none',
          cursor: loading ? 'wait' : 'pointer',
        }}
      >
        {loading ? 'SCORING...' : 'GENERATE TAGS'}
      </button>
      <PipelineStages active={loading} />
    </div>
  )
}
