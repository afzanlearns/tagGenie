import { useState } from 'react'

export default function FeedbackSimulator({ tags, platform }) {
  const [feedbackSent, setFeedbackSent] = useState(false)
  const [message, setMessage] = useState('')

  const simFeedback = async () => {
    if (!tags || tags.length === 0) return
    const selectedTags = tags.slice(0, 3).map(t => t.tag)
    const engagement = {
      likes: Math.floor(Math.random() * 200) + 10,
      shares: Math.floor(Math.random() * 50) + 1,
      comments: Math.floor(Math.random() * 30) + 1,
    }

    try {
      const res = await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          post_id: `sim_${Date.now()}`,
          platform,
          tags_used: selectedTags,
          engagement,
        }),
      })
      if (res.ok) {
        setFeedbackSent(true)
        setMessage(
          `Simulated post with tags [${selectedTags.join(', ')}] — Likes: ${engagement.likes}, Shares: ${engagement.shares}, Comments: ${engagement.comments}`
        )
      } else {
        setMessage(`Error: ${res.status}`)
      }
    } catch (e) {
      setMessage(`Error: ${e.message}`)
    }
  }

  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <span className="text-xs px-2 py-0.5" style={{ backgroundColor: '#1C1C1C', color: '#888' }}>
          SIMULATED
        </span>
        <span className="text-xs" style={{ color: '#555' }}>
          Send synthetic engagement data to trigger the feedback loop
        </span>
      </div>
      <p className="text-xs mb-4" style={{ color: '#666' }}>
        This posts the top 3 tags as a simulated social post with random engagement metrics.
        The nightly feedback job will use this data to adjust platform weights.
      </p>
      <button
        onClick={simFeedback}
        className="px-4 py-2 text-xs font-medium"
        style={{
          backgroundColor: 'transparent',
          color: 'var(--text)',
          border: '1px solid #333',
          cursor: 'pointer',
        }}
      >
        SIMULATE POST
      </button>
      {feedbackSent && (
        <div className="mt-3 text-xs" style={{ color: '#6a6' }}>{message}</div>
      )}
      {message && !feedbackSent && (
        <div className="mt-3 text-xs" style={{ color: 'var(--accent)' }}>{message}</div>
      )}
    </div>
  )
}
