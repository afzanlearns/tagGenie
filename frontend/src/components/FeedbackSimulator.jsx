import { useState } from 'react'
import { api } from '../api'
import { getRecommendationLabel } from '../recommendation'

export default function FeedbackSimulator({ tags, platform, niche = 'gps-telematics' }) {
  const [feedbackSent, setFeedbackSent] = useState(false)
  const [message, setMessage] = useState('')

  const simFeedback = async () => {
    if (!tags || tags.length === 0) return
    const selectedTags = tags.slice(0, 3).map(t => getRecommendationLabel(t))
    const engagement = {
      likes: Math.floor(Math.random() * 200) + 10,
      shares: Math.floor(Math.random() * 50) + 1,
      comments: Math.floor(Math.random() * 30) + 1,
    }

    try {
      await api('/api/feedback', {
        method: 'POST',
        body: {
          post_id: `sim_${Date.now()}`,
          platform,
          niche,
          tags_used: selectedTags,
          engagement,
        },
      })
      setFeedbackSent(true)
      setMessage(
        `Simulated post with tags [${selectedTags.join(', ')}] — Likes: ${engagement.likes}, Shares: ${engagement.shares}, Comments: ${engagement.comments}`
      )
    } catch (e) {
      setMessage(`Error: ${e.message}`)
    }
  }

  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <span className="text-xs px-2 py-0.5" style={{ backgroundColor: 'var(--border)', color: 'var(--text-secondary)' }}>
          SIMULATED
        </span>
        <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
          Send synthetic engagement data to trigger the feedback loop
        </span>
      </div>
      <p className="text-xs mb-4" style={{ color: 'var(--text-muted)' }}>
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
