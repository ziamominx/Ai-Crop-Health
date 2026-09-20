/* API client — all application data flows through the FastAPI backend.
   localStorage is used ONLY for the harmless UI language preference. */
const BASE = import.meta.env.VITE_API_BASE || ''

let authToken = null
let onUnauthorized = null

export function setAuthToken(token) { authToken = token }
export function getAuthToken() { return authToken }
export function setUnauthorizedHandler(fn) { onUnauthorized = fn }

async function request(method, path, { body, form, headers = {}, raw = false } = {}) {
  const finalHeaders = { ...headers }
  if (authToken) finalHeaders['Authorization'] = `Bearer ${authToken}`
  if (body !== undefined) finalHeaders['Content-Type'] = 'application/json'

  let res
  try {
    res = await fetch(`${BASE}${path}`, {
      method,
      headers: finalHeaders,
      body: form ? form : body !== undefined ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new ApiError('NETWORK_ERROR', 'Cannot reach the Agricure server.', 0)
  }

  if (res.status === 401 && onUnauthorized) onUnauthorized()
  if (raw) {
    if (!res.ok) throw new ApiError('REQUEST_FAILED', `Request failed (${res.status})`, res.status)
    return res
  }
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const detail = data.detail
    const message = typeof detail === 'string'
      ? detail
      : Array.isArray(detail)
        ? detail.map(d => d.msg || JSON.stringify(d)).join(', ')
        : `Request failed (${res.status})`
    throw new ApiError('REQUEST_FAILED', message, res.status)
  }
  return data
}

export class ApiError extends Error {
  constructor(code, message, status) {
    super(message)
    this.code = code
    this.status = status
  }
}

export const api = {
  // auth
  register: (payload) => request('POST', '/api/auth/register', { body: payload }),
  login: (email, password) => request('POST', '/api/auth/login', { body: { email, password } }),
  me: () => request('GET', '/api/auth/me'),
  mode: () => request('GET', '/api/auth/mode'),
  // farms + weather
  farms: () => request('GET', '/api/farms'),
  createFarm: (payload) => request('POST', '/api/farms', { body: payload }),
  weather: (location) => request('GET', `/api/weather?location=${encodeURIComponent(location)}`),
  // sensors
  addSensorReading: (payload) => request('POST', '/api/sensors/readings', { body: payload }),
  farmSensors: (farmId) => request('GET', `/api/farms/${farmId}/sensors`),
  // reports
  submitReport: (formData) => request('POST', '/api/reports', { form: formData }),
  myReports: () => request('GET', '/api/reports'),
  allReports: () => request('GET', '/api/reports/all'),
  allReportsGrouped: () => request('GET', '/api/reports/all/grouped'),
  reportDetail: (id) => request('GET', `/api/reports/${id}`),
  analyzeReport: (id) => request('POST', `/api/reports/${id}/analyze`),
  // verification + feedback
  verifyReport: (id, payload) => request('POST', `/api/verify/${id}`, { body: payload }),
  feedback: () => request('GET', '/api/verify/feedback'),
  // referrals
  referrals: () => request('GET', '/api/referrals'),
  myReferrals: () => request('GET', '/api/referrals/mine'),
  createReferral: (payload) => request('POST', '/api/referrals', { body: payload }),
  setReferralStatus: (id, payload) => request('PATCH', `/api/referrals/${id}/status`, { body: payload }),
  // notifications
  notifications: () => request('GET', '/api/notifications'),
  unreadCount: () => request('GET', '/api/notifications/unread-count'),
  markAllRead: () => request('POST', '/api/notifications/read-all'),
  // analytics
  dashboard: () => request('GET', '/api/analytics/dashboard'),
  hotspots: () => request('GET', '/api/analytics/hotspots'),
  agentActivity: () => request('GET', '/api/analytics/agent-activity'),
  diseaseDistribution: () => request('GET', '/api/analytics/disease-distribution'),
  // model
  modelVersions: () => request('GET', '/api/model/versions'),
  modelStatus: () => request('GET', '/api/model/status'),
  queueRetraining: () => request('POST', '/api/model/retraining/queue', { body: {} }),
  // admin
  adminStats: () => request('GET', '/api/admin/stats'),
  // read-only snapshot of every table, fetched with the JWT (never a token in a URL)
  databaseViewHtml: async (limit = 200) => {
    const res = await request('GET', `/api/admin/database-view?limit=${limit}`, { raw: true })
    return res.text()
  },
  adminUsers: () => request('GET', '/api/admin/users'),
  adminSetUserActive: (id, isActive) => request('PATCH', `/api/admin/users/${id}/active?is_active=${isActive}`),
  auditLogs: () => request('GET', '/api/admin/audit-logs'),
  // exports (authenticated fetch + client-side download; a plain window.open
  // cannot send the Authorization header, so it would 401)
  exportUrl: (kind) => `${BASE}/api/export/${kind}`,
  exportCsv: async (kind) => {
    const res = await request('GET', `/api/export/${kind}`, { raw: true })
    const blob = await res.blob()
    const cd = res.headers.get('Content-Disposition') || ''
    const m = /filename="?([^";]+)"?/.exec(cd)
    return { blob, filename: m ? m[1] : `agricure_${kind}.csv` }
  },
}
