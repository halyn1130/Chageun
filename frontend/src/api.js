const TOKEN_KEY = 'chageun_access_token'

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function readResponse(response) {
  if (response.status === 204) return null
  const text = await response.text()
  let data
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = text
  }
  if (!response.ok) {
    const detail = data?.detail || data?.error
    const message = (Array.isArray(detail) ? detail.map(item => item.msg).filter(Boolean).join(' · ') : typeof detail === 'string' ? detail : '') || (typeof data === 'string' ? data : '') || `요청을 처리하지 못했어요. (${response.status})`
    throw new ApiError(message, response.status)
  }
  return data
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

export async function api(path, options = {}) {
  const { method = 'GET', body, params, signal } = options
  const url = new URL(`/api${path}`, window.location.origin)
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, String(value))
    }
  }
  const headers = {}
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  if (body !== undefined && !(body instanceof FormData)) headers['Content-Type'] = 'application/json'
  let response
  try {
    response = await fetch(url, {
      method,
      headers,
      body: body === undefined ? undefined : body instanceof FormData ? body : JSON.stringify(body),
      credentials: 'include',
      signal,
    })
  } catch (error) {
    if (error.name === 'AbortError') throw error
    throw new ApiError('API 서버에 연결할 수 없어요. 서버 실행 상태를 확인해 주세요.', 0)
  }
  try {
    return await readResponse(response)
  } catch (error) {
    if (error.status === 401) {
      clearToken()
      window.dispatchEvent(new Event('chageun:unauthorized'))
    }
    throw error
  }
}

async function auth(path, options = {}) {
  let response
  try {
    response = await fetch(`/auth${path}`, { credentials: 'include', ...options })
  } catch {
    throw new ApiError('인증 서버에 연결할 수 없어요.', 0)
  }
  return readResponse(response)
}

export async function login(username, password) {
  const data = await auth('/api/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ username, password }),
  })
  // Java returns a JWT for the FastAPI Bearer contract and also keeps its session cookie.
  if (data?.access_token) localStorage.setItem(TOKEN_KEY, data.access_token)
  return data
}

export async function signup(username, password) {
  await auth('/api/signup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ username, password }),
  })
}

export async function checkAuth() {
  try {
    return await auth('/api/auth/check')
  } catch (error) {
    if (error.status === 401) return null
    throw error
  }
}

export async function logout() {
  clearToken()
  // The Java endpoint redirects to /login. Following it may return the Vite HTML page.
  await fetch('/auth/api/logout', { method: 'POST', credentials: 'include' }).catch(() => {})
}
