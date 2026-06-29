const API_BASE = ''

function getToken() {
  return localStorage.getItem('taggenie_token')
}

export function isAuthenticated() {
  return !!getToken()
}

export function isGuest() {
  return !!localStorage.getItem('taggenie_guest')
}

export function getAuthHeaders() {
  const token = getToken()
  const headers = { 'Content-Type': 'application/json' }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return headers
}

export async function api(path, options = {}) {
  const { body, method = 'GET', ...rest } = options
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: getAuthHeaders(),
    body: body ? JSON.stringify(body) : undefined,
    ...rest,
  })

  if (res.status === 401) {
    localStorage.removeItem('taggenie_token')
    localStorage.removeItem('taggenie_guest')
    window.location.reload()
    throw new Error('Session expired. Please log in again.')
  }

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}))
    throw new Error(errData.detail || `Server error: ${res.status}`)
  }

  return res.json()
}
