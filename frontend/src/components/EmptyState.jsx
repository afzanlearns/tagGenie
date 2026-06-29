export default function EmptyState({ hasHistory, onDemoSelect }) {
  return (
    <div className="border p-8 mt-4 text-center" style={{ borderColor: '#1C1C1C' }}>
      <div className="text-lg mb-2" style={{ color: '#333' }}>◆</div>
      <h2 className="text-sm font-medium mb-2" style={{ color: 'var(--text)' }}>No recommendations generated yet</h2>
      <p className="text-xs mb-4 max-w-md mx-auto" style={{ color: '#555' }}>
        Enter a topic and product above, then click <strong>Generate Tags</strong> to analyze how your content performs across platforms.
      </p>
      {!hasHistory && (
        <div className="flex items-center justify-center gap-2 text-xs" style={{ color: '#555' }}>
          <span>Try a demo:</span>
          <button
            onClick={() => onDemoSelect && onDemoSelect('AI dashcams for fleet safety', 'Vignan Dashcam AI', 'LinkedIn')}
            className="px-2 py-1" style={{ backgroundColor: 'transparent', border: '1px solid #333', color: '#888', cursor: 'pointer' }}
          >
            Fleet Safety
          </button>
          <button
            onClick={() => onDemoSelect && onDemoSelect('real-time GPS telematics', 'AjnaView GPS Suite', 'Instagram')}
            className="px-2 py-1" style={{ backgroundColor: 'transparent', border: '1px solid #333', color: '#888', cursor: 'pointer' }}
          >
            GPS Telematics
          </button>
        </div>
      )}
    </div>
  )
}
