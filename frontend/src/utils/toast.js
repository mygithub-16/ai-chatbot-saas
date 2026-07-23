export function emitToast({ title, message = '', tone = 'info', duration = 3600 }) {
  if (typeof window === 'undefined') return

  window.dispatchEvent(
    new CustomEvent('app-toast', {
      detail: {
        id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
        title,
        message,
        tone,
        duration,
      },
    }),
  )
}

