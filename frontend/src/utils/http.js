const VITE_API_URL = (
  import.meta.env.VITE_API_URL ||
  (import.meta.env.PROD ? 'https://api.echura.app' : '')
).replace(/\/$/, '')

export function apiUrl(path) {
  if (!path) return ''
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path
  }
  const cleanPath = path.startsWith('/') ? path : `/${path}`
  return VITE_API_URL ? `${VITE_API_URL}${cleanPath}` : cleanPath
}

export async function readJsonResponse(response) {
  const text = await response.text()

  if (!text || !text.trim()) {
    return {}
  }

  try {
    return JSON.parse(text)
  } catch {
    return { detail: text }
  }
}
