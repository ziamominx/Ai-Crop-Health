/* Static demo API — the GitHub Pages build has no Python backend, so this module
   answers every /api/* request from a bundled dataset.

   The dataset is NOT fabricated: fixtures.json was produced by
   scripts/export_static_demo.py, which seeded the real demo database and ran the
   project's own heuristic CV inference, risk engine and decision engine over
   each demo photo. Everything you see here is genuine stored output of that run.

   What this mode cannot do is analyse a brand-new photo (that needs the real
   inference service), so live uploads are refused with a clear message and the
   UI hides the upload control. Writes (reports, verifications, referrals,
   notifications) are kept in memory for the session and are plainly labelled as
   demo, since there is no database behind a static site. */

import fixtures from './fixtures.json'

export const IS_STATIC_DEMO = true

const BASE = (import.meta.env.BASE_URL || '/').replace(/\/$/, '')
const asset = (p) => (p && p.startsWith('/') ? `${BASE}${p}` : p)

const PASSWORD_FOR_ROLE = { FARMER: 'demo1234', OFFICER: 'officer1234', ADMIN: 'admin1234' }
const TOKEN_PREFIX = 'static-demo:'

const clone = (v) => JSON.parse(JSON.stringify(v))

// ---------------------------------------------------------------- in-memory store
let nextIds = { report: 1000, referral: 1000, notification: 1000, sensor: 1000, audit: 1000 }

const store = {
  users: clone(fixtures.users),
  farms: clone(fixtures.farms),
  reports: clone(fixtures.reports),
  referrals: clone(fixtures.referrals),
  notifications: clone(fixtures.notifications),
  sensors: clone(fixtures.sensor_readings),
  models: clone(fixtures.model_versions),
  feedback: [],
  audit: [],
  demoPhotos: clone(fixtures.demo_photos),
}

// Bundled photos live under the Pages base path, and story them with the real
// asset prefix so <img src> resolves on GitHub Pages.
for (const report of store.reports) report.image_url = asset(report.image_url)
for (const key of Object.keys(store.demoPhotos)) {
  store.demoPhotos[key].image_url = asset(store.demoPhotos[key].image_url)
}

/* A reconstructed audit trail for the bundled reports. These events really did
   happen during the export run — only the actor name is generic. */
function seedAuditTrail() {
  const rows = []
  for (const r of store.reports) {
    const farmer = store.users.find((u) => u.id === r.farmer_id)
    const at = (offset) => new Date(new Date(r.created_at).getTime() + offset).toISOString()
    rows.push({ id: nextIds.audit++, user_id: r.farmer_id, user_name: farmer?.name || null,
      action: 'REPORT_SUBMITTED', entity_type: 'report', entity_id: r.id, metadata: { crop: r.crop }, created_at: r.created_at })
    rows.push({ id: nextIds.audit++, user_id: null, user_name: 'agent', action: 'AI_ANALYSIS_PERFORMED',
      entity_type: 'report', entity_id: r.id,
      metadata: { disease: r.disease, confidence: r.confidence, model: r.model_version }, created_at: at(600) })
    rows.push({ id: nextIds.audit++, user_id: null, user_name: 'agent', action: 'AGENT_DECISION_GENERATED',
      entity_type: 'report', entity_id: r.id,
      metadata: { risk: r.risk_level, score: r.risk_score, decision: r.agent_decision?.decision }, created_at: at(900) })
  }
  return rows.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
}
store.audit = seedAuditTrail()

// ---------------------------------------------------------------- session
let current = null   // { user, token }

if (typeof sessionStorage !== 'undefined') {
  try {
    const raw = sessionStorage.getItem('agricure_static_session')
    if (raw) current = JSON.parse(raw)
  } catch { /* ignore */ }
}
const persist = () => {
  try {
    if (current) sessionStorage.setItem('agricure_static_session', JSON.stringify(current))
    else sessionStorage.removeItem('agricure_static_session')
  } catch { /* ignore */ }
}

export function staticDemoToken() { return current?.token || null }

// ---------------------------------------------------------------- helpers
const json = (data, status = 200) =>
  new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } })
const fail = (status, detail) => json({ detail }, status)
const csv = (filename, body) => new Response(body, {
  status: 200,
  headers: { 'Content-Type': 'text/csv', 'Content-Disposition': `attachment; filename="${filename}"` },
})
const csvCell = (v) => {
  if (v === null || v === undefined) return ''
  const s = String(v)
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}
const toCsv = (header, rows) =>
  [header.join(','), ...rows.map((r) => r.map(csvCell).join(','))].join('\n') + '\n'
const byNewest = (a, b) => new Date(b.created_at) - new Date(a.created_at)
const publicUser = (u) => ({
  id: u.id, name: u.name, email: u.email, role: u.role,
  phone: u.phone, language: u.language, created_at: u.created_at,
})
const notifyUser = (userId, type, title, message, reportId = null) => {
  store.notifications.unshift({
    id: nextIds.notification++, user_id: userId, report_id: reportId, type, title,
    message, is_read: false, created_at: new Date().toISOString(),
  })
}
const audit = (action, entityType, entityId, metadata = {}) => {
  store.audit.unshift({
    id: nextIds.audit++, user_id: current?.user?.id ?? null,
    user_name: current?.user?.name ?? 'agent', action, entity_type: entityType,
    entity_id: entityId, metadata, created_at: new Date().toISOString(),
  })
}

function requireRole(roles) {
  if (!current) return fail(401, 'Not authenticated')
  if (roles && !roles.includes(current.user.role)) return fail(403, 'Not authorized for this action.')
  return null
}

function officerId() {
  return store.users.find((u) => u.role === 'OFFICER')?.id ?? null
}

// Reports whose analysis is "still running" (playback of the agent loop)
const pendingUntil = new Map()

function finalizeReport(report) {
  const key = `${report.crop}:${report.demo_variant || 'diseased'}`
  const source = store.demoPhotos[key]
  if (!source) return report
  Object.assign(report, {
    disease: source.disease, is_healthy: source.is_healthy, confidence: source.confidence,
    severity: source.severity, risk_level: source.risk_level, risk_score: source.risk_score,
    risk_factors: source.risk_factors, model_version: source.model_version,
    is_demo_inference: source.is_demo_inference, low_confidence: source.low_confidence,
    followup_days: source.followup_days, status: 'ANALYZED',
    agent_decision: clone(source.agent_decision), recommendations: clone(source.recommendations),
    activity: clone(source.activity), nearby_similar: source.nearby_similar,
    updated_at: new Date().toISOString(),
  })
  delete report.demo_variant
  pendingUntil.delete(report.id)

  const farmer = store.users.find((u) => u.id === report.farmer_id)
  notifyUser(report.farmer_id, report.is_healthy ? 'RESULT' : 'HIGH_RISK',
    report.is_healthy ? 'Healthy crop check' : 'AI assessment ready',
    report.is_healthy
      ? `Your ${report.crop} check is ready: looks healthy.`
      : `Your ${report.crop} check is ready: potential ${report.disease}, spread risk ${report.risk_level}.`,
    report.id)
  audit('AI_ANALYSIS_PERFORMED', 'report', report.id,
    { disease: report.disease, confidence: report.confidence, model: report.model_version })
  audit('AGENT_DECISION_GENERATED', 'report', report.id,
    { risk: report.risk_level, score: report.risk_score, farmer: farmer?.name })
  return report
}

function getReport(id) {
  const report = store.reports.find((r) => r.id === Number(id))
  if (report && report.status === 'PENDING' && (pendingUntil.get(report.id) || 0) <= Date.now()) {
    finalizeReport(report)
  }
  return report
}

const reportList = () => [...store.reports].sort(byNewest)

function groupedReports() {
  const groups = {}
  for (const r of reportList()) {
    const g = groups[r.farmer_id] || (groups[r.farmer_id] = {
      farmer_id: r.farmer_id, farmer_name: r.farmer_name, farmer_email: null,
      sample_count: 0, reports: [],
    })
    g.sample_count += 1
    g.reports.push({
      id: r.id, crop: r.crop, disease: r.disease, is_healthy: r.is_healthy,
      confidence: r.confidence, severity: r.severity, risk_level: r.risk_level,
      risk_score: r.risk_score, status: r.status, location: r.location, farm_name: r.farm_name,
      image_url: r.image_url, model_version: r.model_version,
      is_demo_inference: r.is_demo_inference, officer_verified: r.officer_verified,
      created_at: r.created_at,
    })
  }
  for (const g of Object.values(groups)) {
    g.farmer_email = store.users.find((u) => u.id === g.farmer_id)?.email || null
  }
  return Object.values(groups).sort((a, b) => b.sample_count - a.sample_count)
}

function hotspots() {
  const grouped = {}
  for (const r of reportList()) {
    const key = r.location || 'Unknown'
    ;(grouped[key] = grouped[key] || []).push(r)
  }
  const out = Object.entries(grouped).map(([location, items]) => {
    const high = items.filter((r) => r.risk_level === 'High').length
    const counts = {}
    for (const r of items) if (r.disease) counts[r.disease] = (counts[r.disease] || 0) + 1
    const dominant = Object.entries(counts).sort((a, b) => b[1] - a[1])[0]
    const riskCounts = {}
    for (const r of items) riskCounts[r.risk_level] = (riskCounts[r.risk_level] || 0) + 1
    const dominantRisk = Object.entries(riskCounts).sort((a, b) => b[1] - a[1])[0]
    const count = items.length
    return {
      location, report_count: count, high_risk_count: high,
      dominant_disease: dominant ? dominant[0] : null,
      dominant_risk: dominantRisk ? dominantRisk[0] : null,
      is_potential_hotspot: count >= 3 && high >= Math.max(1, Math.floor(count / 3)),
    }
  })
  return out.sort((a, b) => b.report_count - a.report_count)
}

function dashboard() {
  const reports = store.reports
  return {
    total_reports: reports.length,
    high_risk: reports.filter((r) => r.risk_level === 'High').length,
    moderate_risk: reports.filter((r) => r.risk_level === 'Moderate').length,
    low_risk: reports.filter((r) => r.risk_level === 'Low').length,
    pending_verification: reports.filter((r) => !r.officer_verified && r.status === 'ANALYZED').length,
    open_referrals: store.referrals.filter((r) => r.status !== 'RESOLVED').length,
    recent_reports: reportList().slice(0, 15),
  }
}

function adminStats() {
  const active = store.models.find((m) => m.status === 'ACTIVE') || store.models[0] || null
  return {
    total_farmers: store.users.filter((u) => u.role === 'FARMER').length,
    total_officers: store.users.filter((u) => u.role === 'OFFICER').length,
    total_reports: store.reports.length,
    high_risk_reports: store.reports.filter((r) => r.risk_level === 'High').length,
    pending_referrals: store.referrals.filter((r) => r.status !== 'RESOLVED').length,
    feedback_count: store.feedback.length,
    retraining_queue: store.feedback.filter((f) => f.in_retraining_queue).length,
    model: active,
  }
}

/* Read-only snapshot of the bundled dataset — the same idea as the backend's
   /api/admin/database-view, rendered from the in-memory store. */
function databaseViewHtml(limit = 200) {
  const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]))
  const tables = {
    users: store.users, farms: store.farms, crop_reports: store.reports,
    referrals: store.referrals, notifications: store.notifications,
    sensor_readings: store.sensors, model_versions: store.models,
    model_feedback: store.feedback, audit_logs: store.audit,
  }
  const counts = Object.entries(tables)
    .map(([name, rows]) => `<li><b>${name}</b><span>${rows.length}</span></li>`).join('')
  const sections = Object.entries(tables).map(([name, rows]) => {
    if (!rows.length) return `<h2>${name} <em>0 rows</em></h2><p class="empty">No rows.</p>`
    const cols = [...new Set(rows.flatMap((r) => Object.keys(r)))]
    const shown = rows.slice(0, limit)
    const head = cols.map((c) => `<th>${esc(c)}</th>`).join('')
    const body = shown.map((row) => `<tr>${cols.map((c) => {
      const v = row[c]
      if (c === 'image_url' && v) return `<td><img src="${esc(v)}" alt="sample" loading="lazy"></td>`
      if (c === 'image_path') return `<td class="dim">${esc(v)}</td>`
      if (v && typeof v === 'object') return `<td class="dim">${esc(JSON.stringify(v))}</td>`
      if (v === null || v === undefined) return '<td class="dim">NULL</td>'
      if (typeof v === 'boolean') return `<td>${v ? 'true' : 'false'}</td>`
      return `<td>${esc(v)}</td>`
    }).join('')}</tr>`).join('')
    return `<h2>${name} <em>${rows.length} rows</em></h2>
      <div class="wrap"><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`
  }).join('')

  return `<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Agricure — database view (static demo)</title>
<style>
 body{margin:0;font:14px/1.5 ui-sans-serif,system-ui,Segoe UI,sans-serif;background:#f7f4ea;color:#14231a}
 header{background:#123524;color:#fff;padding:16px 22px}
 header h1{margin:0;font-size:18px} header p{margin:6px 0 0;opacity:.85;font-size:12px}
 main{display:flex;align-items:flex-start;gap:18px;padding:18px}
 aside{position:sticky;top:18px;background:#fff;border:1px solid #e3ddc9;border-radius:12px;padding:10px;min-width:190px}
 aside ul{list-style:none;margin:0;padding:0}
 aside li{display:flex;justify-content:space-between;gap:10px;padding:5px 8px;border-radius:6px;font-size:12px}
 aside li span{color:#6b7568}
 aside li:hover{background:#f2f6ef}
 section{flex:1;min-width:0}
 h2{font-size:14px;margin:22px 0 8px;display:flex;gap:8px;align-items:baseline}
 h2 em{font-style:normal;font-size:11px;color:#6b7568;font-weight:400}
 .wrap{overflow:auto;max-height:420px;background:#fff;border:1px solid #e3ddc9;border-radius:10px}
 table{border-collapse:collapse;font-size:12px;width:100%}
 th{position:sticky;top:0;background:#f2f6ef;text-align:left;padding:7px 9px;border-bottom:1px solid #e3ddc9;white-space:nowrap}
 td{padding:6px 9px;border-bottom:1px solid #f0ece0;vertical-align:top;max-width:320px;overflow:hidden;text-overflow:ellipsis}
 td img{height:44px;width:44px;object-fit:cover;border-radius:6px;display:block}
 .dim{color:#9aa394}.empty{color:#9aa394;font-size:12px}
</style></head><body>
<header><h1>Agricure — database view</h1>
<p>Static demo (GitHub Pages): this is the bundled sample dataset — ${store.reports.length} crop reports,
${store.users.length} users, ${store.audit.length} audit entries.
Run the FastAPI backend locally for the live database.</p></header>
<main><aside><ul>${counts}</ul></aside><section>${sections}</section></main>
</body></html>`
}

// ---------------------------------------------------------------- routing
function route(method, path, url, init) {
  const body = init.body

  // ---- auth
  if (path === '/api/auth/mode') {
    const farmer = store.users.find((u) => u.role === 'FARMER')
    const officer = store.users.find((u) => u.role === 'OFFICER')
    const admin = store.users.find((u) => u.role === 'ADMIN')
    return json({
      demo_mode: true, demo_farmer_email: farmer?.email, demo_officer_email: officer?.email,
      demo_admin_email: admin?.email, ai_mode: 'HEURISTIC_CV', static_demo: true,
    })
  }

  if (path === '/api/auth/login' && method === 'POST') {
    const payload = JSON.parse(body || '{}')
    const user = store.users.find((u) => u.email.toLowerCase() === String(payload.email || '').toLowerCase())
    if (!user) return fail(401, 'Incorrect email or password.')
    const expected = PASSWORD_FOR_ROLE[user.role]
    if (payload.password !== expected) {
      return fail(401, `Incorrect email or password. (Static demo passwords: farmer demo1234 · officer officer1234 · admin admin1234)`)
    }
    const token = `${TOKEN_PREFIX}${user.id}`
    current = { user: publicUser(user), token }
    persist()
    audit('USER_LOGIN', 'user', user.id, { role: user.role, mode: 'static demo' })
    return json({ access_token: token, token_type: 'bearer', user: current.user })
  }

  if (path === '/api/auth/register' && method === 'POST') {
    return fail(403, 'Registration needs the FastAPI backend and PostgreSQL — this published build is a read-only static demo. Use one of the demo logins instead.')
  }

  if (path === '/api/auth/me') {
    const denied = requireRole(null)
    if (denied) return denied
    return json(current.user)
  }

  // ---- public demo assets are static; everything below needs a session
  const denied = requireRole(null)
  if (denied) return denied
  const role = current.user.role
  const isStaff = role === 'OFFICER' || role === 'ADMIN'

  // ---- farms / weather / sensors
  if (path === '/api/farms' && method === 'GET') {
    const farms = role === 'FARMER'
      ? store.farms.filter((f) => f.farmer_id === current.user.id)
      : store.farms
    return json(farms)
  }
  if (path === '/api/farms' && method === 'POST') {
    const payload = JSON.parse(body || '{}')
    if (role !== 'FARMER') return fail(403, 'Only farmers can add farms.')
    const farm = {
      id: Math.max(0, ...store.farms.map((f) => f.id)) + 1,
      farmer_id: current.user.id, farm_name: payload.farm_name, location: payload.location,
      latitude: payload.latitude ?? 19.9975, longitude: payload.longitude ?? 73.7898,
      district: payload.district ?? payload.location, state: payload.state ?? 'Maharashtra',
      created_at: new Date().toISOString(),
    }
    store.farms.push(farm)
    audit('FARM_CREATED', 'farm', farm.id, { farm_name: farm.farm_name })
    return json(farm, 201)
  }
  if (path === '/api/weather') {
    const location = url.searchParams.get('location') || 'your area'
    const base = { Nashik: [27, 78, 4], Pune: [28, 71, 2], Ahmednagar: [30, 62, 0],
      Nagpur: [32, 58, 1], Kolhapur: [26, 84, 9] }[location] || [28, 74, 3]
    return json({
      temperature: base[0], humidity: base[1], rainfall_24h: base[2],
      mode: 'STATIC_DEMO', retrieved_at: new Date().toISOString(),
      source: 'Bundled sample weather — run the backend for live/DEMO_WEATHER values',
    })
  }
  if (method === 'POST' && path === '/api/sensors/readings') {
    const payload = JSON.parse(body || '{}')
    const reading = {
      id: nextIds.sensor++, farm_id: payload.farm_id, trap_type: payload.trap_type ?? null,
      temperature: payload.temperature ?? null, humidity: payload.humidity ?? null,
      soil_moisture: payload.soil_moisture ?? null, leaf_wetness: payload.leaf_wetness ?? null,
      pest_count: payload.pest_count ?? null, recorded_at: new Date().toISOString(),
    }
    store.sensors.unshift(reading)
    return json(reading, 201)
  }
  const sensorMatch = /^\/api\/farms\/(\d+)\/sensors$/.exec(path)
  if (sensorMatch) {
    const farmId = Number(sensorMatch[1])
    return json(store.sensors.filter((s) => s.farm_id === farmId)
      .sort((a, b) => new Date(b.recorded_at) - new Date(a.recorded_at)).slice(0, 30))
  }

  // ---- reports
  if (method === 'POST' && path === '/api/reports') {
    if (role !== 'FARMER') return fail(403, 'Only farmers can submit crop reports.')
    const form = body
    const crop = String(form.get('crop') || '')
    const file = form.get('image')
    const filename = (file && file.name) || ''
    const match = /^demo-(.+)\.jpg$/i.exec(filename)

    if (!match) {
      return fail(503, 'Analysing a newly uploaded photo needs the FastAPI backend (the published build is a static demo). Use “Use a demo photo”, or run the backend locally to analyse your own images.')
    }
    const stem = match[1].toLowerCase()          // e.g. tomato or tomato-healthy
    const variant = stem.endsWith('-healthy') ? 'healthy' : 'diseased'
    const cropKey = Object.keys(store.demoPhotos)
      .find((k) => k.toLowerCase() === `${stem.replace('-healthy', '')}:${variant}`)
    const template = store.demoPhotos[cropKey]
    if (!template) return fail(404, `No bundled sample for ${crop}.`)

    const now = new Date().toISOString()
    const report = {
      id: nextIds.report++, farmer_id: current.user.id,
      farm_id: Number(form.get('farm_id')) || store.farms.find((f) => f.farmer_id === current.user.id)?.id || null,
      crop, image_url: template.image_url, image_path: null,
      disease: null, is_healthy: false, confidence: 0, severity: 'Low',
      risk_level: 'Low', risk_score: 0, risk_factors: [], model_version: null,
      is_demo_inference: false,
      temperature: null, humidity: null, rainfall: null,
      soil_moisture: form.get('soil_moisture') ? Number(form.get('soil_moisture')) : null,
      leaf_wetness: form.get('leaf_wetness') ? Number(form.get('leaf_wetness')) : null,
      pest_count: form.get('pest_count') ? Number(form.get('pest_count')) : null,
      location: store.farms.find((f) => f.id === Number(form.get('farm_id')))?.location ?? null,
      status: 'PENDING', officer_verified: false, low_confidence: false, followup_days: 7,
      created_at: now, updated_at: now,
      farmer_name: current.user.name,
      farm_name: store.farms.find((f) => f.id === Number(form.get('farm_id')))?.farm_name ?? null,
      agent_decision: null, recommendations: [], activity: [
        { id: 1, stage: 'PERCEPTION', message: 'Crop image received', created_at: now },
      ],
      nearby_similar: template.nearby_similar || 0,
      demo_variant: variant,
    }
    store.reports.unshift(report)
    // Play back the agent loop so the pipeline animation is visible, exactly as
    // the backend's async pipeline does.
    pendingUntil.set(report.id, Date.now() + 1100)
    audit('REPORT_SUBMITTED', 'report', report.id, { crop, sample: 'bundled demo photo' })
    return json(report, 201)
  }

  if (method === 'GET' && path === '/api/reports') {
    const rows = role === 'FARMER'
      ? reportList().filter((r) => r.farmer_id === current.user.id)
      : reportList()
    return json(rows)
  }
  if (method === 'GET' && path === '/api/reports/all') return json(reportList().slice(0, 100))
  if (method === 'GET' && path === '/api/reports/all/grouped') {
    const staffOnly = requireRole(['OFFICER', 'ADMIN'])
    if (staffOnly) return staffOnly
    return json(groupedReports())
  }
  const analyzeMatch = /^\/api\/reports\/(\d+)\/analyze$/.exec(path)
  if (analyzeMatch && method === 'POST') {
    const report = getReport(analyzeMatch[1])
    if (!report) return fail(404, 'Report not found.')
    pendingUntil.set(report.id, 0)
    finalizeReport(report)
    return json(report)
  }
  const reportMatch = /^\/api\/reports\/(\d+)$/.exec(path)
  if (reportMatch && method === 'GET') {
    const report = getReport(reportMatch[1])
    if (!report) return fail(404, 'Report not found.')
    if (role === 'FARMER' && report.farmer_id !== current.user.id) return fail(403, 'Not your report.')
    return json(report)
  }

  // ---- verification + feedback
  const verifyMatch = /^\/api\/verify\/(\d+)$/.exec(path)
  if (verifyMatch && method === 'POST') {
    const staffOnly = requireRole(['OFFICER', 'ADMIN'])
    if (staffOnly) return staffOnly
    const report = store.reports.find((r) => r.id === Number(verifyMatch[1]))
    if (!report) return fail(404, 'Report not found.')
    const payload = JSON.parse(body || '{}')
    const predicted = report.disease
    const corrected = payload.corrected_disease || null
    const wasCorrect = !corrected || corrected === predicted

    store.feedback.unshift({
      id: store.feedback.length + 1, report_id: report.id, crop: report.crop,
      predicted_disease: predicted, actual_disease: wasCorrect ? predicted : corrected,
      was_correct: wasCorrect, officer_name: current.user.name,
      model_version: report.model_version, in_retraining_queue: false,
      created_at: new Date().toISOString(),
    })
    if (!wasCorrect) { report.disease = corrected; report.status = 'CORRECTED' }
    else report.status = 'VERIFIED'
    report.officer_verified = true
    report.low_confidence = false
    report.updated_at = new Date().toISOString()

    if (payload.lab_sample_requested) {
      notifyUser(report.farmer_id, 'REFERRAL', 'Lab sample requested',
        'An agriculture officer has requested a lab sample for this report.', report.id)
    }
    notifyUser(report.farmer_id, 'VERIFICATION', 'Report reviewed by an officer',
      `Your ${report.crop} report was verified by ${current.user.name}`
      + (wasCorrect ? ' — AI assessment confirmed.' : ` — diagnosis corrected to ${corrected}.`),
      report.id)
    audit('OFFICER_VERIFICATION', 'report', report.id, { correct: wasCorrect, corrected_to: corrected })
    if (!wasCorrect) audit('DIAGNOSIS_CORRECTED', 'report', report.id, { from: predicted, to: corrected })
    return json({ detail: 'Verification stored.', was_correct: wasCorrect, status: report.status })
  }
  if (method === 'GET' && path === '/api/verify/feedback') {
    const staffOnly = requireRole(['OFFICER', 'ADMIN'])
    if (staffOnly) return staffOnly
    return json(store.feedback)
  }

  // ---- referrals
  if (method === 'GET' && path === '/api/referrals') {
    const staffOnly = requireRole(['OFFICER', 'ADMIN'])
    if (staffOnly) return staffOnly
    return json([...store.referrals].sort(byNewest))
  }
  if (method === 'GET' && path === '/api/referrals/mine') {
    return json(store.referrals.filter((r) => r.farmer_id === current.user.id).sort(byNewest))
  }
  if (method === 'POST' && path === '/api/referrals') {
    if (role !== 'FARMER') return fail(403, 'Only farmers can request a referral.')
    const payload = JSON.parse(body || '{}')
    const report = store.reports.find((r) => r.id === Number(payload.report_id))
    if (!report || report.farmer_id !== current.user.id) return fail(404, 'Report not found.')
    const referral = {
      id: nextIds.referral++, report_id: report.id, farmer_id: current.user.id,
      officer_id: null, reason: payload.reason, status: 'PENDING',
      created_at: new Date().toISOString(), resolved_at: null,
      farmer_name: current.user.name, crop: report.crop, disease: report.disease,
      location: report.location,
    }
    store.referrals.unshift(referral)
    for (const officer of store.users.filter((u) => u.role === 'OFFICER')) {
      notifyUser(officer.id, 'REFERRAL', 'New referral request',
        `${current.user.name} requested: ${payload.reason} (${report.crop}, ${report.disease || 'healthy'}).`,
        report.id)
    }
    audit('REFERRAL_CREATED', 'referral', referral.id, { reason: payload.reason })
    return json(referral, 201)
  }
  const referralStatusMatch = /^\/api\/referrals\/(\d+)\/status$/.exec(path)
  if (referralStatusMatch && method === 'PATCH') {
    const staffOnly = requireRole(['OFFICER', 'ADMIN'])
    if (staffOnly) return staffOnly
    const referral = store.referrals.find((r) => r.id === Number(referralStatusMatch[1]))
    if (!referral) return fail(404, 'Referral not found.')
    const payload = JSON.parse(body || '{}')
    referral.status = payload.status
    if (payload.officer_id) referral.officer_id = payload.officer_id
    else if (role === 'OFFICER' && !referral.officer_id) referral.officer_id = current.user.id
    if (payload.status === 'RESOLVED') referral.resolved_at = new Date().toISOString()
    notifyUser(referral.farmer_id, 'REFERRAL', `Referral ${String(payload.status).toLowerCase()}`,
      `Your referral was marked ${payload.status}.`, referral.report_id)
    audit(payload.status === 'RESOLVED' ? 'REFERRAL_RESOLVED' : 'REFERRAL_UPDATED',
      'referral', referral.id, { status: payload.status })
    return json(referral)
  }

  // ---- notifications
  if (method === 'GET' && path === '/api/notifications') {
    return json(store.notifications.filter((n) => n.user_id === current.user.id).slice(0, 50))
  }
  if (method === 'GET' && path === '/api/notifications/unread-count') {
    return json({ count: store.notifications.filter((n) => n.user_id === current.user.id && !n.is_read).length })
  }
  if (method === 'POST' && path === '/api/notifications/read-all') {
    for (const n of store.notifications) if (n.user_id === current.user.id) n.is_read = true
    return json({ detail: 'All notifications marked read.' })
  }
  const notifReadMatch = /^\/api\/notifications\/(\d+)\/read$/.exec(path)
  if (notifReadMatch && method === 'POST') {
    const n = store.notifications.find((x) => x.id === Number(notifReadMatch[1]))
    if (n) n.is_read = true
    return json({ detail: 'Marked read.' })
  }

  // ---- analytics
  const staffOnly = () => requireRole(['OFFICER', 'ADMIN'])
  if (method === 'GET' && path === '/api/analytics/dashboard') {
    const deniedStaff = staffOnly(); if (deniedStaff) return deniedStaff
    return json(dashboard())
  }
  if (method === 'GET' && path === '/api/analytics/hotspots') {
    const deniedStaff = staffOnly(); if (deniedStaff) return deniedStaff
    return json(hotspots())
  }
  if (method === 'GET' && path === '/api/analytics/agent-activity') {
    const deniedStaff = staffOnly(); if (deniedStaff) return deniedStaff
    const feed = []
    for (const r of reportList().slice(0, 60)) {
      for (const a of r.activity || []) {
        feed.push({
          id: `${r.id}-${a.id}`, report_id: r.id, crop: r.crop, disease: r.disease,
          stage: a.stage, message: a.message, created_at: a.created_at,
        })
      }
    }
    return json(feed.sort((a, b) => new Date(b.created_at) - new Date(a.created_at)).slice(0, 60))
  }
  if (method === 'GET' && path === '/api/analytics/disease-distribution') {
    const deniedStaff = staffOnly(); if (deniedStaff) return deniedStaff
    const counts = {}
    for (const r of store.reports) {
      const label = r.disease || 'Healthy'
      counts[label] = (counts[label] || 0) + 1
    }
    return json(Object.entries(counts).sort((a, b) => b[1] - a[1])
      .map(([label, count]) => ({ label, count })))
  }

  // ---- model
  if (method === 'GET' && path === '/api/model/versions') {
    const deniedStaff = staffOnly(); if (deniedStaff) return deniedStaff
    return json([...store.models].sort(byNewest))
  }
  if (method === 'GET' && path === '/api/model/status') {
    const deniedStaff = staffOnly(); if (deniedStaff) return deniedStaff
    const active = store.models.find((m) => m.status === 'ACTIVE') || store.models[0] || null
    return json({
      ai_mode: 'HEURISTIC_CV', model_version: active?.version || 'heuristic-cv-v1',
      real_model_available: false,
      demo_note: 'A rule-based computer-vision model analysed the images for this published '
        + 'dataset. It is a real image analysis of the stored photos, not a trained CNN — '
        + 'no trained crop-disease weights ship with this demo.',
    })
  }
  if (method === 'POST' && path === '/api/model/retraining/queue') {
    const deniedStaff = staffOnly(); if (deniedStaff) return deniedStaff
    const rows = store.feedback.filter((f) => !f.in_retraining_queue)
    if (!rows.length) return json({ queued: 0, detail: 'Nothing new to queue.' })
    for (const row of rows) row.in_retraining_queue = true
    const version = `retrain-${new Date().toISOString().slice(0, 10).replace(/-/g, '')}`
    if (!store.models.some((m) => m.version === version)) {
      store.models.unshift({
        id: Math.max(0, ...store.models.map((m) => m.id)) + 1, version,
        model_name: 'Agricure Crop Disease Model', status: 'QUEUED',
        training_samples: rows.length, accuracy: null,
        notes: 'Created by retraining queue (static demo — no automatic retraining)',
        created_at: new Date().toISOString(),
      })
    }
    audit('RETRAINING_QUEUED', 'model_feedback', null, { count: rows.length })
    return json({ queued: rows.length, detail: 'Queued for the next model retraining cycle.' })
  }

  // ---- admin
  if (path.startsWith('/api/admin/')) {
    const adminOnly = requireRole(['ADMIN'])
    if (adminOnly) return adminOnly
    if (path === '/api/admin/stats') return json(adminStats())
    if (path === '/api/admin/users') return json([...store.users].sort(byNewest).map(publicUser))
    if (path === '/api/admin/audit-logs') return json(store.audit.slice(0, 100))
    if (path === '/api/admin/database-view') {
      audit('DATABASE_VIEWED', 'system', null, { mode: 'static demo' })
      return new Response(databaseViewHtml(Number(url.searchParams.get('limit')) || 200), {
        status: 200, headers: { 'Content-Type': 'text/html; charset=utf-8' },
      })
    }
    const activeMatch = /^\/api\/admin\/users\/(\d+)\/active$/.exec(path)
    if (activeMatch && method === 'PATCH') {
      const user = store.users.find((u) => u.id === Number(activeMatch[1]))
      if (!user) return fail(404, 'User not found.')
      user.is_active = url.searchParams.get('is_active') === 'true'
      audit('USER_ACCESS_CHANGED', 'user', user.id, { is_active: user.is_active })
      return json(publicUser(user))
    }
  }

  // ---- CSV exports (generated in the browser from the bundled dataset)
  if (path.startsWith('/api/export/')) {
    const deniedStaff = staffOnly(); if (deniedStaff) return deniedStaff
    const kind = path.split('/').pop()
    if (kind === 'reports') {
      return csv('agricure_reports.csv', toCsv(
        ['id', 'farmer', 'farm', 'crop', 'disease', 'confidence', 'severity', 'risk_level',
          'risk_score', 'location', 'status', 'officer_verified', 'model_version', 'created_at'],
        reportList().map((r) => [r.id, r.farmer_name, r.farm_name, r.crop, r.disease ?? 'Healthy',
          r.confidence, r.severity, r.risk_level, r.risk_score, r.location, r.status,
          r.officer_verified, r.model_version, r.created_at])))
    }
    if (kind === 'feedback') {
      return csv('agricure_model_feedback.csv', toCsv(
        ['id', 'report_id', 'crop', 'predicted_disease', 'actual_disease', 'was_correct',
          'officer_name', 'model_version', 'in_retraining_queue', 'created_at'],
        store.feedback.map((f) => [f.id, f.report_id, f.crop, f.predicted_disease,
          f.actual_disease, f.was_correct, f.officer_name, f.model_version,
          f.in_retraining_queue, f.created_at])))
    }
    if (kind === 'referrals') {
      return csv('agricure_referrals.csv', toCsv(
        ['id', 'report_id', 'farmer_name', 'crop', 'disease', 'reason', 'status', 'created_at', 'resolved_at'],
        store.referrals.map((r) => [r.id, r.report_id, r.farmer_name, r.crop, r.disease,
          r.reason, r.status, r.created_at, r.resolved_at])))
    }
    if (kind === 'sensors') {
      return csv('agricure_sensor_readings.csv', toCsv(
        ['id', 'farm_id', 'trap_type', 'temperature', 'humidity', 'soil_moisture',
          'leaf_wetness', 'pest_count', 'recorded_at'],
        store.sensors.map((s) => [s.id, s.farm_id, s.trap_type, s.temperature, s.humidity,
          s.soil_moisture, s.leaf_wetness, s.pest_count, s.recorded_at])))
    }
    return fail(404, 'Unknown export.')
  }

  return fail(404, `Static demo has no route for ${method} ${path}`)
}

/** Install the interceptor. Called before the app renders when in static mode. */
export function installStaticDemoApi() {
  if (typeof window === 'undefined' || window.__agricureStaticDemoInstalled) return
  window.__agricureStaticDemoInstalled = true
  const realFetch = window.fetch.bind(window)

  window.fetch = (input, init = {}) => {
    const raw = typeof input === 'string' ? input : input?.url || ''
    let url
    try {
      url = new URL(raw, window.location.origin)
    } catch {
      return realFetch(input, init)
    }
    if (!url.pathname.startsWith('/api/')) return realFetch(input, init)
    try {
      return Promise.resolve(route((init.method || 'GET').toUpperCase(), url.pathname, url, init))
    } catch (err) {
      return Promise.resolve(fail(500, `Static demo error: ${err.message}`))
    }
  }
}
