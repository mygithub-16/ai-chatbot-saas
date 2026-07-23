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
