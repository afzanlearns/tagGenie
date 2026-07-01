import { useState, useEffect } from 'react'
import { api } from '../api'
const COMPARISON_TAGS = [
  { tg: 'fleet safety', tgScore: 92, bl: 'fleet', blScore: 45, gap: true },
  { tg: 'predictive maintenance', tgScore: 88, bl: 'safety', blScore: 38, gap: false },
  { tg: 'driver coaching', tgScore: 85, bl: 'dashcams', blScore: 42, gap: true },
  { tg: 'telematics integration', tgScore: 81, bl: 'ai', blScore: 36, gap: false },
  { tg: 'route optimization', tgScore: 78, bl: 'telematics', blScore: 34, gap: false },
]

export default function Landing({ onEnter }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showSignup, setShowSignup] = useState(false)
  const [signupMsg, setSignupMsg] = useState('')
  const [evalData, setEvalData] = useState(null)
  const [theme, setTheme] = useState(() => localStorage.getItem('taggenie-theme') || 'dark')

  useEffect(() => {
    fetch('/api/evaluation-summary')
      .then(r => r.json())
      .then(data => setEvalData(data))
      .catch(() => {})
  }, [])

  const handleSignup = async () => {
    setSignupMsg('')
    try {
      const data = await api('/api/auth/signup', {
        method: 'POST',
        body: { email, password },
      })
      localStorage.setItem('taggenie_token', data.access_token)
      setSignupMsg('Account created!')
      onEnter()
    } catch (e) {
      setSignupMsg(e.message)
    }
  }

  const handleLogin = async () => {
    setSignupMsg('')
    try {
      const data = await api('/api/auth/login', {
        method: 'POST',
        body: { email, password },
      })
      localStorage.setItem('taggenie_token', data.access_token)
      onEnter()
    } catch (e) {
      setSignupMsg(e.message)
    }
  }

  const handleGuestMode = async () => {
    try {
      const data = await api('/api/auth/guest')
      localStorage.setItem('taggenie_token', data.access_token)
      localStorage.setItem('taggenie_guest', 'true')
      onEnter()
    } catch (e) {
      setSignupMsg(`Guest mode unavailable: ${e.message}`)
    }
  }

  return (
    <div className="min-h-screen" data-theme={theme} style={{ backgroundColor: 'var(--canvas)', color: 'var(--text)', fontFamily: 'var(--font)' }}>
      <header className="border-b px-6 py-4" style={{ borderColor: 'var(--border)' }}>
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-lg tracking-tight" style={{ color: 'var(--text)' }}>TagGenie</h1>
            <p className="text-xs mt-0.5" style={{ color: 'var(--text-secondary)' }}>Distribution Intelligence Engine</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => {
                const next = theme === 'dark' ? 'light' : 'dark'
                setTheme(next)
                localStorage.setItem('taggenie-theme', next)
              }}
              className="text-sm px-2 py-1"
              style={{ background: 'none', border: '1px solid var(--border)', color: 'var(--text-secondary)', cursor: 'pointer', borderRadius: 4 }}
              title="Toggle theme"
            >
              {theme === 'dark' ? '☀' : '☾'}
            </button>
            <button
              onClick={() => setShowSignup(true)}
              className="text-xs px-4 py-2 font-medium"
              style={{
                backgroundColor: 'var(--accent)',
                color: 'var(--text)',
                border: 'none',
                cursor: 'pointer',
              }}
            >
              SIGN UP
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-16">
        {/* Positioning */}
        <div className="text-center mb-16">
          <h2 className="text-3xl mb-4" style={{ color: 'var(--text)', lineHeight: 1.3 }}>
            The tags that win aren't the ones you guess.
            <br />
            They're the ones the data picks.
          </h2>
          <p className="text-sm max-w-2xl mx-auto" style={{ color: 'var(--text-secondary)', lineHeight: 1.6 }}>
            TagGenie ranks distribution tags by trend momentum, competitive density, and platform fit — 
            replacing guesswork with a repeatable scoring engine that learns from real engagement data.
            Works across industries. One scoring endpoint. Configurable per niche.
          </p>
        </div>

        {/* Side-by-side comparison */}
        <div className="border mb-16" style={{ borderColor: 'var(--border)' }}>
          <div className="grid grid-cols-2 gap-0">
            <div className="border-r" style={{ borderColor: 'var(--border)' }}>
              <div className="px-6 py-3 border-b text-xs" style={{ borderColor: 'var(--border)', backgroundColor: 'var(--surface-3)', color: 'var(--accent)' }}>
                TAGGENIE
              </div>
              {COMPARISON_TAGS.map((item, i) => (
                <div key={i} className="px-6 py-3 flex items-center justify-between border-b text-xs" style={{ borderColor: 'var(--border-light)' }}>
                  <div className="flex items-center gap-2">
                    {item.gap && <span className="text-xs" style={{ color: 'var(--accent)' }}>◆</span>}
                    <span style={{ color: 'var(--text)' }}>{item.tg}</span>
                  </div>
                  <span style={{ color: 'var(--text-muted)' }}>{item.tgScore}</span>
                </div>
              ))}
            </div>
            <div>
              <div className="px-6 py-3 border-b text-xs" style={{ borderColor: 'var(--border)', backgroundColor: 'var(--surface-3)', color: 'var(--text-tertiary)' }}>
                TF-IDF BASELINE
              </div>
              {COMPARISON_TAGS.map((item, i) => (
                <div key={i} className="px-6 py-3 flex items-center justify-between border-b text-xs" style={{ borderColor: 'var(--border-light)' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>{item.bl}</span>
                  <span style={{ color: 'var(--text-muted)' }}>{item.blScore}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="px-6 py-3 text-xs" style={{ color: 'var(--text-tertiary)', backgroundColor: 'var(--surface-3)' }}>
            <span style={{ color: 'var(--accent)' }}>◆</span> Blue ocean gap — high reach, low competition (TagGenie only)
          </div>
        </div>

        {/* Precision lift — dynamic from evaluation harness */}
        <div className="border mb-16 p-8 text-center" style={{ borderColor: 'var(--border)' }}>
          <span className="text-4xl font-bold" style={{ color: 'var(--accent)' }}>
            {evalData ? `+${evalData.best_lift_pct.toFixed(1)}%` : '—'}
          </span>
          <p className="text-sm mt-2" style={{ color: 'var(--text-secondary)' }}>
            precision@5 lift over naive TF-IDF keyword extraction<br />
            <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
              — evaluated on held-out Reddit posts across {evalData?.results?.length || 3} industries —
            </span>
          </p>
          {evalData?.results && (
            <div className="mt-4 max-w-md mx-auto">
              <table className="w-full text-xs" style={{ color: 'var(--text-tertiary)' }}>
                <thead>
                  <tr className="border-b" style={{ borderColor: 'var(--border)' }}>
                    <th className="text-left py-1">Niche</th>
                    <th className="text-right py-1">TG P@5</th>
                    <th className="text-right py-1">BL P@5</th>
                    <th className="text-right py-1">Lift</th>
                  </tr>
                </thead>
                <tbody>
                  {evalData.results.map(r => (
                    <tr key={r.niche} className="border-b" style={{ borderColor: 'var(--border-light)' }}>
                      <td className="py-1">{r.niche}</td>
                      <td className="text-right py-1" style={{ color: 'var(--text)' }}>{r.tg_p5}</td>
                      <td className="text-right py-1">{r.bl_p5}</td>
                      <td className="text-right py-1" style={{ color: r.lift_p5.startsWith('+') ? '#6a6' : 'var(--accent)' }}>{r.lift_p5}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Feature summary */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-16">
          <div className="border p-6" style={{ borderColor: 'var(--border)' }}>
            <div className="text-xs font-medium mb-2" style={{ color: 'var(--text)' }}>Multi-Niche</div>
            <p className="text-xs" style={{ color: 'var(--text-tertiary)', lineHeight: 1.6 }}>
              Works for telematics, B2B SaaS, fintech, or any industry. Add a niche by creating a config directory — no code changes.
            </p>
          </div>
          <div className="border p-6" style={{ borderColor: 'var(--border)' }}>
            <div className="text-xs font-medium mb-2" style={{ color: 'var(--text)' }}>Self-Learning</div>
            <p className="text-xs" style={{ color: 'var(--text-tertiary)', lineHeight: 1.6 }}>
              Thompson Sampling adjusts platform weights nightly from real engagement data. The more you use it, the better it gets.
            </p>
          </div>
          <div className="border p-6" style={{ borderColor: 'var(--border)' }}>
            <div className="text-xs font-medium mb-2" style={{ color: 'var(--text)' }}>No Hallucinations</div>
            <p className="text-xs" style={{ color: 'var(--text-tertiary)', lineHeight: 1.6 }}>
              LLM used only for topic expansion and rationale — never for scoring math. Every score is deterministic and auditable.
            </p>
          </div>
        </div>

        {/* CTA / Signup */}
        <div className="border p-8 max-w-lg mx-auto" style={{ borderColor: 'var(--border)' }}>
          {!showSignup ? (
            <div className="text-center">
              <p className="text-sm mb-4" style={{ color: 'var(--text-secondary)' }}>
                Try it with a demo topic — no account needed.
              </p>
              <button
                onClick={() => setShowSignup(true)}
                className="px-8 py-3 text-sm font-medium"
                style={{
                  backgroundColor: 'var(--accent)',
                  color: 'var(--text)',
                  border: 'none',
                  cursor: 'pointer',
                }}
              >
                TRY TAGGENIE
              </button>
              <button
                onClick={handleGuestMode}
                className="px-8 py-3 text-sm font-medium ml-3"
                style={{
                  backgroundColor: 'transparent',
                  color: 'var(--text-muted)',
                  border: '1px solid var(--border)',
                  cursor: 'pointer',
                }}
              >
                TRY AS GUEST
              </button>
            </div>
          ) : (
            <div>
              <div className="flex gap-2 mb-4">
                <button
                  onClick={() => setShowSignup(false)}
                  className="text-xs px-3 py-1"
                  style={{ backgroundColor: 'transparent', border: '1px solid var(--border)', color: 'var(--text-tertiary)', cursor: 'pointer' }}
                >
                  ← BACK
                </button>
              </div>
              <div className="mb-4">
                <label className="block text-xs mb-1.5" style={{ color: 'var(--text-tertiary)' }}>EMAIL</label>
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  className="w-full px-3 py-2 text-sm border focus:outline-none"
                  style={{ backgroundColor: 'transparent', borderColor: 'var(--border)', color: 'var(--text)' }}
                  placeholder="you@example.com"
                />
              </div>
              <div className="mb-4">
                <label className="block text-xs mb-1.5" style={{ color: 'var(--text-tertiary)' }}>PASSWORD</label>
                <input
                  type="password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  className="w-full px-3 py-2 text-sm border focus:outline-none"
                  style={{ backgroundColor: 'transparent', borderColor: 'var(--border)', color: 'var(--text)' }}
                  placeholder="Min 8 characters"
                />
              </div>
              <div className="flex gap-2">
                <button
                  onClick={handleSignup}
                  className="px-6 py-2 text-xs font-medium"
                  style={{
                    backgroundColor: 'var(--accent)',
                    color: 'var(--text)',
                    border: 'none',
                    cursor: 'pointer',
                  }}
                >
                  CREATE ACCOUNT
                </button>
                <button
                  onClick={handleLogin}
                  className="px-6 py-2 text-xs font-medium"
                  style={{
                    backgroundColor: 'transparent',
                    color: 'var(--text-muted)',
                    border: '1px solid var(--border)',
                    cursor: 'pointer',
                  }}
                >
                  LOG IN
                </button>
              </div>
              {signupMsg && (
                <div className="mt-3 text-xs" style={{ color: signupMsg === 'Account created!' ? '#6a6' : 'var(--accent)' }}>
                  {signupMsg}
                </div>
              )}
            </div>
          )}
        </div>
      </main>

      <footer className="border-t px-6 py-6" style={{ borderColor: 'var(--border)' }}>
        <div className="max-w-6xl mx-auto text-xs text-center" style={{ color: 'var(--text-muted)' }}>
          TagGenie v3.0 — Distribution Intelligence Engine
        </div>
      </footer>
    </div>
  )
}
