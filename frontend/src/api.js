// Thin fetch wrapper. Non-2xx responses throw ApiError carrying the parsed
// body (409 conflict bodies drive the diff/retry dialog).
export class ApiError extends Error {
  constructor(status, body) {
    super(body?.detail || `请求失败（HTTP ${status}）`);
    this.status = status;
    this.body = body || {};
  }
}

async function request(method, path, body, isForm) {
  const init = { method, headers: {} };
  if (body !== undefined) {
    if (isForm) init.body = body; // FormData sets multipart boundary itself
    else {
      init.headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(body);
    }
  }
  const res = await fetch(path, init);
  if (res.status === 204) return null;
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) throw new ApiError(res.status, data);
  return data;
}

export const api = {
  listMedia: () => request("GET", "/api/media"),
  uploadMedia: (formData) => request("POST", "/api/media", formData, true),
  deleteMedia: (id) => request("DELETE", `/api/media/${id}`),
  quoteText: (id, start, end) =>
    request("GET", `/api/media/${id}/quote-text?start=${start}&end=${end}`),

  listEvents: () => request("GET", "/api/events"),
  getEvent: (id) => request("GET", `/api/events/${id}`),
  createEvent: (payload) => request("POST", "/api/events", payload),
  updateEvent: (id, payload) => request("PUT", `/api/events/${id}`, payload),
  deleteEvent: (id) => request("DELETE", `/api/events/${id}`),

  listReleases: () => request("GET", "/api/releases"),
  getRelease: (id) => request("GET", `/api/releases/${id}`),
  getLatestRelease: () => request("GET", "/api/releases/latest"),
  publishRelease: (payload) => request("POST", "/api/releases", payload),
};
