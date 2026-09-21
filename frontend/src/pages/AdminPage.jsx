import { useCallback, useEffect, useState } from 'react'
import { C, riskColor } from '../api/theme.js'
import {
  BrainCog, Database, ExternalLink, ImagePlus, LogOut, RefreshCw, ShieldCheck, Sprout, UsersIcon,
} from '../api/icons.jsx'
import { ErrorBox, LoadingBox, Pill, StatCard } from '../components/ui.jsx'
import { api } from '../api/client.js'
import { useLanguage } from '../hooks/useLanguage.jsx'

export function AdminPage({ onLogout }) {
  const { t } = useLanguage()
  const [tab, setTab] = useState('overview')
  const [stats, setStats] = useState(null)
  const [users, setUsers] = useState([])
  const [audit, setAudit] = useState([])
  const [grouped, setGrouped] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [live, setLive] = useState(true)
  const [lastSync, setLastSync] = useState(null)
  const [aiModeInfo, setAiModeInfo] = useState(null)
  const [aiModeBusy, setAiModeBusy] = useState(false)
  const [aiModeMsg, setAiModeMsg] = useState('')

  const loadAll = useCallback(async () => {
    setError('')
    try {
      const [s, u, a, g, am] = await Promise.all([
        api.adminStats(), api.adminUsers(), api.auditLogs(), api.allReportsGrouped(),
        api.aiMode(),
      ])
      setStats(s); setUsers(u); setAudit(a); setGrouped(g); setAiModeInfo(am)
      setLastSync(new Date())
    } catch (err) {
      setError(err.message || t('loadFailed'))
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => { loadAll() }, [loadAll])

  // Live view: refresh every 10 s while the tab is open (pause when hidden)
  useEffect(() => {
    if (!live) return
    const iv = setInterval(() => { if (!document.hidden) loadAll() }, 10000)
    return () => clearInterval(iv)
  }, [live, loadAll])

  /* Opens the read-only database page. The tab is opened synchronously (so the
     browser never blocks it as a popup), then pointed at a blob of the HTML we
     fetched with the JWT — the token is never placed in a URL. */
  const openDatabaseView = async () => {
    const tab = window.open('', '_blank')
    try {
      if (tab) {
        tab.document.write('<title>Loading database view…</title>'
          + '<body style="font-family:sans-serif;padding:40px;color:#1f3d2b">'
          + 'Loading the database view…</body>')
      }
      const html = await api.databaseViewHtml()
      const url = URL.createObjectURL(new Blob([html], { type: 'text/html' }))
      if (tab) tab.location.href = url
      else window.location.href = url
      setTimeout(() => URL.revokeObjectURL(url), 120000)
    } catch (err) {
      if (tab) tab.close()
      setError(err.message || t('loadFailed'))
    }
  }

  const switchAiMode = async (mode) => {
    setAiModeBusy(true); setAiModeMsg('')
    try {
      const info = await api.setAiMode(mode)
      setAiModeInfo(info)
      setAiModeMsg(t('aiModeSwitched'))
    } catch (err) {
      setError(err.message)
    } finally {
      setAiModeBusy(false)
    }
  }

  const toggleUser = async (u) => {
    try {
      await api.adminSetUserActive(u.id, !u.is_active)
      setUsers(users.map((x) => (x.id === u.id ? { ...x, is_active: !u.is_active } : x)))
    } catch (err) {
      setError(err.message)
    }
  }

  const m = stats?.model
  const totalSamples = grouped.reduce((n, g) => n + g.sample_count, 0)
  const sys = [
    { label: t('adminTotalFarmers'), value: stats?.total_farmers },
    { label: t('adminTotalOfficers'), value: stats?.total_officers },
    { label: t('adminTotalReports'), value: stats?.total_reports },
    { label: t('adminHighRisk'), value: stats?.high_risk_reports },
    { label: t('adminPendingReferrals'), value: stats?.pending_referrals },
    { label: t('adminFeedback'), value: stats?.feedback_count },
    { label: t('adminRetrainQueue'), value: stats?.retraining_queue },
  ]

  const tabLabels = [
    { id: 'overview', label: t('adminTabOverview') },
    { id: 'data', label: t('adminTabData') },
  ]

  return (
    <div className="min-h-screen">
      <div className="flex items-center justify-between px-6 py-4" style={{ background: C.forestDark }}>
        <div className="flex items-center gap-2">
          <ShieldCheck color={C.wheat} size={20} />
          <span className="ag-display text-lg text-white">{t('appName')}</span>
          <Pill color={C.wheat}>{t('loginAdminTag')}</Pill>
        </div>
        <button onClick={onLogout} className="text-white/85 text-sm flex items-center gap-1"><LogOut size={15} /> {t('logout')}</button>
      </div>

      <div className="max-w-5xl mx-auto px-5 py-8">
        <h2 className="ag-display text-2xl" style={{ color: C.forest }}>{t('adminHeading')}</h2>
        <p className="ag-body text-sm mb-4" style={{ color: 'rgba(20,35,26,0.6)' }}>{t('adminSub')}</p>

        {/* ---- Tabs ---- */}
        <div className="flex flex-wrap items-center gap-2 mb-6">
          {tabLabels.map((x) => (
            <button key={x.id} onClick={() => setTab(x.id)}
              className="rounded-full px-4 py-1.5 text-sm font-semibold"
              style={tab === x.id
                ? { background: C.forest, color: 'white' }
                : { background: C.creamDeep, color: C.forest }}>
              {x.label}
            </button>
          ))}
          <button onClick={openDatabaseView}
            title={t('adminDbViewHint')}
            className="ag-magnetic ag-sheen ml-auto rounded-full px-4 py-1.5 text-sm font-semibold flex items-center gap-1.5 transition-all duration-500 hover:-translate-y-0.5"
            style={{ border: `1px solid ${C.line}`, color: C.forest, background: C.white }}>
            <Database size={14} /> {t('adminOpenDbView')} <ExternalLink size={12} />
          </button>
        </div>

        {error && <div className="mb-4"><ErrorBox message={error} onRetry={loadAll} retryLabel={t('retry')} /></div>}
        {loading && <LoadingBox>Loading…</LoadingBox>}

        {!loading && tab === 'overview' && (
          <>
            {/* ---- AI Model card ---- */}
            <div className="rounded-2xl p-6 mb-6" style={{ background: C.forest }}>
              <p className="text-sm font-semibold mb-3 flex items-center gap-2 text-white"><BrainCog size={17} color={C.wheat} /> {t('adminModel')}</p>
              {m ? (
                <div className="grid sm:grid-cols-3 gap-3 text-sm text-white">
                  <div><span className="text-white/60 text-xs block">{t('modelName')}</span>{m.model_name}</div>
                  <div><span className="text-white/60 text-xs block">{t('modelVersion')}</span>{m.version}</div>
                  <div><span className="text-white/60 text-xs block">{t('modelStatus')}</span>
                    <Pill color={m.status === 'ACTIVE' ? C.green : m.status === 'DEMO' ? C.amber : C.wheatDeep}>{m.status}</Pill>
                  </div>
                  <div><span className="text-white/60 text-xs block">{t('modelSamples')}</span>{m.training_samples}</div>
                  <div><span className="text-white/60 text-xs block">{t('modelAccuracy')}</span>{m.accuracy != null ? `${(m.accuracy * 100).toFixed(1)}%` : '—'}</div>
                  <div><span className="text-white/60 text-xs block">{t('adminLastUpdated')}</span>{new Date(m.created_at).toLocaleString()}</div>
                </div>
              ) : (
                <p className="text-sm text-white/70">No model version registered.</p>
              )}
              {m?.notes && <p className="text-xs mt-3" style={{ color: 'rgba(255,255,255,0.55)' }}>{m.notes}</p>}
            </div>

            {/* ---- AI Inference Mode switcher ---- */}
            <div className="rounded-2xl p-6 mb-6" style={{ background: C.white, border: `1px solid ${C.line}` }}>
              <p className="text-sm font-semibold mb-1 flex items-center gap-2" style={{ color: C.forest }}><BrainCog size={17} style={{ color: C.moss }} /> {t('aiModeTitle')}</p>
              <p className="text-xs mb-4" style={{ color: 'rgba(20,35,26,0.55)' }}>{t('aiModeSub')}</p>
              <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {[
                  { id: 'HEURISTIC_CV', desc: 'Real on-device image analysis — no key needed', keyNeeded: false },
                  { id: 'GROK_VISION', desc: 'Real AI via the xAI Grok API — needs GROK_API_KEY', keyNeeded: true },
                  { id: 'DEMO_MODEL', desc: 'Simulated results, clearly labelled DEMO', keyNeeded: false },
                  { id: 'REAL_MODEL', desc: 'Trained Keras model from MODEL_PATH', keyNeeded: false },
                ].map((opt) => {
                  const active = aiModeInfo?.mode === opt.id
                  const disabled = aiModeBusy || (opt.keyNeeded && !aiModeInfo?.grok_available)
                  return (
                    <button key={opt.id} disabled={disabled} onClick={() => switchAiMode(opt.id)}
                      className="rounded-xl p-3 text-left transition-all duration-300 hover:-translate-y-0.5 disabled:opacity-50 disabled:hover:translate-y-0"
                      style={active
                        ? { background: C.forest, color: 'white' }
                        : { background: C.creamDeep, color: C.forest }}>
                      <div className="text-sm font-bold flex items-center justify-between gap-1">
                        {opt.id.replace('_', ' ')}
                        {active && <Pill color={C.wheat}>{t('aiModeActive')}</Pill>}
                      </div>
                      <div className="text-xs mt-1 leading-snug" style={{ color: active ? 'rgba(255,255,255,0.8)' : 'rgba(20,35,26,0.55)' }}>{opt.desc}</div>
                      {opt.keyNeeded && !aiModeInfo?.grok_available && (
                        <div className="text-xs mt-2 font-semibold" style={{ color: C.amber }}>{t('aiModeNeedsKey')}</div>
                      )}
                    </button>
                  )
                })}
              </div>
              <p className="text-xs mt-3" style={{ color: 'rgba(20,35,26,0.5)' }}>
                {t('aiModeEnv')}{aiModeInfo?.fallback_applied ? ` · ${t('aiModeFallback')} ${aiModeInfo.fallback_applied}` : ''}
              </p>
              {aiModeInfo?.grok_available === false && (
                <p className="text-xs mt-3" style={{ color: 'rgba(20,35,26,0.5)' }}>{t('aiModeAddKeyHint')}</p>
              )}
              {aiModeMsg && <p className="text-xs mt-2 font-semibold" style={{ color: C.green }}>{aiModeMsg}</p>}
            </div>

            {/* ---- System stats ---- */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
              {sys.map((s) => (
                <StatCard key={s.label} label={s.label} value={s.value ?? 0}
                  color={s.label === t('adminHighRisk') ? C.red : undefined} />
              ))}
            </div>

            {/* ---- Users ---- */}
            <div className="rounded-xl p-5 mb-6" style={{ background: C.white, border: `1px solid ${C.line}` }}>
              <p className="text-xs font-semibold mb-3 flex items-center gap-1.5" style={{ color: 'rgba(20,35,26,0.55)' }}><UsersIcon size={14} /> {t('adminUsers')}</p>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left" style={{ color: 'rgba(20,35,26,0.5)' }}>
                      <th className="py-2 pr-3 font-medium">{t('nameLabel')}</th>
                      <th className="py-2 pr-3 font-medium">{t('emailLabel')}</th>
                      <th className="py-2 pr-3 font-medium">{t('adminRole')}</th>
                      <th className="py-2 pr-3 font-medium">{t('adminActive')}</th>
                      <th className="py-2 pr-3 font-medium">{t('adminActions')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((u) => (
                      <tr key={u.id} style={{ borderTop: `1px solid ${C.line}` }}>
                        <td className="py-2 pr-3">{u.name}</td>
                        <td className="py-2 pr-3">{u.email}</td>
                        <td className="py-2 pr-3"><Pill color={u.role === 'ADMIN' ? C.forest : u.role === 'OFFICER' ? C.moss : C.wheatDeep}>{u.role}</Pill></td>
                        <td className="py-2 pr-3">{u.is_active ? '✓' : '✕'}</td>
                        <td className="py-2 pr-3">
                          <button onClick={() => toggleUser(u)} className="text-xs font-semibold underline" style={{ color: u.is_active ? C.red : C.green }}>
                            {u.is_active ? t('adminDeactivate') : t('adminActivate')}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* ---- Audit log ---- */}
            <div className="rounded-xl p-5" style={{ background: C.white, border: `1px solid ${C.line}` }}>
              <div className="flex items-center justify-between mb-3">
                <p className="text-xs font-semibold flex items-center gap-1.5" style={{ color: 'rgba(20,35,26,0.55)' }}><Database size={14} /> {t('adminAuditLog')}</p>
                <button onClick={openDatabaseView} className="ag-underline text-xs font-semibold flex items-center gap-1" style={{ color: C.moss }}>
                  {t('adminOpenDbView')} <ExternalLink size={11} />
                </button>
              </div>
              {audit.length === 0 ? (
                <p className="text-sm" style={{ color: 'rgba(20,35,26,0.5)' }}>{t('adminAuditEmpty')}</p>
              ) : (
                <ol className="space-y-1 text-xs">
                  {audit.slice(0, 30).map((row) => (
                    <li key={row.id} className="flex items-center gap-2 py-1 border-b" style={{ borderColor: C.line }}>
                      <span className="font-semibold" style={{ color: C.forest }}>{row.action}</span>
                      {row.user_name && <span style={{ color: 'rgba(20,35,26,0.5)' }}>by {row.user_name}</span>}
                      {row.entity_type && <span style={{ color: 'rgba(20,35,26,0.4)' }}>· {row.entity_type} #{row.entity_id}</span>}
                      <span className="ml-auto" style={{ color: 'rgba(20,35,26,0.4)' }}>{new Date(row.created_at).toLocaleString()}</span>
                    </li>
                  ))}
                </ol>
              )}
            </div>
          </>
        )}

        {!loading && tab === 'data' && (
          <>
            {/* ---- Live controls ---- */}
            <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
              <p className="text-sm flex items-center gap-2" style={{ color: 'rgba(20,35,26,0.6)' }}>
                <Database size={15} style={{ color: C.moss }} />
                {t('adminDataSub').replace('{n}', totalSamples)}
              </p>
              <div className="flex items-center gap-3">
                {lastSync && <span className="text-xs" style={{ color: 'rgba(20,35,26,0.45)' }}>{t('adminLastSync')}: {lastSync.toLocaleTimeString()}</span>}
                <button onClick={() => setLive((v) => !v)}
                  className="ag-sheen text-xs font-semibold rounded-full px-3 py-1.5 flex items-center gap-1.5 transition-transform duration-500 hover:-translate-y-0.5"
                  style={live ? { background: C.green, color: 'white' } : { background: C.creamDeep, color: C.forest }}>
                  {live ? (
                    <span className="ag-pulse w-2 h-2 rounded-full" style={{ background: 'white', color: 'white' }} />
                  ) : (
                    <span className="w-2 h-2 rounded-full" style={{ background: C.moss, opacity: 0.6 }} />
                  )}
                  {live ? t('adminLive') : t('adminPaused')}
                </button>
                <button onClick={loadAll} className="text-xs font-semibold rounded-full px-3 py-1.5 flex items-center gap-1.5" style={{ background: C.creamDeep, color: C.forest }}>
                  <RefreshCw size={13} /> {t('retry')}
                </button>
              </div>
            </div>

            {/* ---- Per-user sample groups ---- */}
            {grouped.length === 0 ? (
              <div className="rounded-xl p-6 text-sm" style={{ background: C.white, border: `1px solid ${C.line}`, color: 'rgba(20,35,26,0.5)' }}>
                {t('adminDataEmpty')}
              </div>
            ) : (
              <div className="space-y-5">
                {grouped.map((g, gi) => (
                  <div key={g.farmer_id}
                    className="ag-row-in ag-lift rounded-xl overflow-hidden"
                    style={{ background: C.white, border: `1px solid ${C.line}`, animationDelay: `${Math.min(gi * 80, 600)}ms` }}>
                    <div className="flex items-center justify-between px-4 py-3" style={{ background: C.creamDeep }}>
                      <div className="flex items-center gap-2 text-sm font-semibold" style={{ color: C.forest }}>
                        <UsersIcon size={15} /> {g.farmer_name}
                        <span className="font-normal text-xs" style={{ color: 'rgba(20,35,26,0.5)' }}>{g.farmer_email}</span>
                      </div>
                      <Pill color={C.forest}>{g.sample_count} {t('adminSamples')}</Pill>
                    </div>
                    <div className="divide-y" style={{ borderColor: C.line }}>
                      {g.reports.map((r, ri) => (
                        <div key={r.id}
                          className="ag-row-in flex items-center gap-3 px-4 py-3 transition-colors duration-300 hover:bg-black/[0.02]"
                          style={{ borderColor: C.line, animationDelay: `${Math.min(gi * 80 + ri * 40, 900)}ms` }}>
                          {/* stored sample image (served from the database/local storage) */}
                          <div className="ag-zoom w-14 h-14 rounded-lg overflow-hidden flex-shrink-0 flex items-center justify-center" style={{ background: C.creamDeep }}>
                            {r.image_url
                              ? <img src={r.image_url} alt={`${r.crop} sample`} className="w-full h-full object-cover"
                                  onError={(e) => { e.currentTarget.style.display = 'none' }} />
                              : <ImagePlus size={18} color={C.moss} />}
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="text-sm font-semibold" style={{ color: C.forest }}>
                              #{r.id} · {r.crop} — {r.is_healthy ? t('healthy') : r.disease}
                            </div>
                            <div className="text-xs" style={{ color: 'rgba(20,35,26,0.5)' }}>
                              {r.farm_name ? `${r.farm_name} · ` : ''}{r.location || '—'} · {new Date(r.created_at).toLocaleString()}
                            </div>
                            <div className="text-xs mt-0.5" style={{ color: 'rgba(20,35,26,0.45)' }}>
                              {t('confidenceLabel')} {r.confidence?.toFixed(0)}% · {r.model_version || '—'}
                              {r.is_demo_inference ? ` · ${t('adminDemoTag')}` : ''}
                              {r.officer_verified ? ` · ✓ ${t('adminVerifiedTag')}` : ''}
                            </div>
                          </div>
                          <div className="flex flex-col items-end gap-1 flex-shrink-0">
                            <Pill color={riskColor(r.risk_level)}>{t(`severity_${r.risk_level}`)} · {r.risk_score}</Pill>
                            <Pill color={r.status === 'VERIFIED' ? C.green : r.status === 'ANALYZED' ? C.moss : C.amber}>{r.status}</Pill>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
