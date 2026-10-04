// 后端 API 封装。失败时抛出带 message 的 Error；409 冲突携带 conflict 数据。
async function request(path, options = {}) {
  const res = await fetch(path, {
    headers: options.body && !(options.body instanceof FormData)
      ? { 'Content-Type': 'application/json' }
      : undefined,
    ...options,
  })
  if (res.status === 204) return null
  let data = null
  const text = await res.text()
  if (text) {
    try { data = JSON.parse(text) } catch { data = text }
  }
  if (!res.ok) {
    const err = new Error()
    err.status = res.status
    if (res.status === 409 && data && data.detail && data.detail.server_event) {
      err.message = data.detail.message
      err.conflict = data.detail
    } else {
      err.message = typeof data?.detail === 'string'
        ? data.detail
        : (typeof data === 'string' ? data : `请求失败（${res.status}）`)
    }
    throw err
  }
  return data
}

export const api = {
  listAudios: () => request('/api/audios'),
  getAudio: (id) => request(`/api/audios/${id}`),
  uploadAudio: (formData) => request('/api/audios', { method: 'POST', body: formData }),
  deleteAudio: (id) => request(`/api/audios/${id}`, { method: 'DELETE' }),
  streamUrl: (id) => `/api/audios/${id}/stream`,

  listEvents: () => request('/api/events'),
  getEvent: (id) => request(`/api/events/${id}`),
  createEvent: (payload) => request('/api/events', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  updateEvent: (id, payload) => request(`/api/events/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  }),
  deleteEvent: (id) => request(`/api/events/${id}`, { method: 'DELETE' }),

  listPublications: () => request('/api/publications'),
  getPublication: (id) => request(`/api/publications/${id}`),
  publish: (payload) => request('/api/publications', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
}

export function formatTime(sec) {
  if (sec == null || Number.isNaN(Number(sec))) return '--'
  const s = Number(sec)
  const m = Math.floor(s / 60)
  const rest = (s % 60).toFixed(1)
  return `${String(m).padStart(2, '0')}:${rest.padStart(4, '0')}`
}

export function formatBytes(n) {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(1)} MB`
}

export function formatDateTime(iso) {
  return iso ? iso.replace('T', ' ').replace(/\.\d+Z$/, ' UTC') : ''
}
