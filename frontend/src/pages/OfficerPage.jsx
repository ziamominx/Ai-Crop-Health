import { Fragment, useCallback, useEffect, useState } from 'react'
import { C, LOCATION_COORDS, riskColor } from '../api/theme.js'
import {
  AlertTriangle, BrainCog, Bug, CheckCircle2, Database, Download, FlaskConical,
  HistoryIcon, Landmark, LogOut, Map2, MapPin, RefreshCw, ShieldCheck, Sparkles,
  Stethoscope, TrendingUp, X,
} from '../api/icons.jsx'
import { ErrorBox, LoadingBox, Pill, StatCard } from '../components/ui.jsx'
import { api } from '../api/client.js'
import { useLanguage } from '../hooks/useLanguage.jsx'
import { DISEASE_MAP } from '../i18n/translations.js'

export function OfficerPage({ onLogout }) {
  const { t } = useLanguage()
  const [tab, setTab] = useState('dashboard')
  const [error, setError] = useState('')

  const [stats, setStats] = useState(null)
  const [hotspots, setHotspots] = useState([])
  const [reports, setReports] = useState([])
  const [referrals, setReferrals] = useState([])
  const [feedback, setFeedback] = useState([])
  const [versions, setVersions] = useState([])
  const [modelStatus, setModelStatus] = useState(null)
  const [activity, setActivity] = useState([])
  const [loading, setLoading] = useState(true)
  const [retrainQueued, setRetrainQueued] = useState(false)

  const [correctingId, setCorrectingId] = useState(null)
  const [correctionChoice, setCorrectionChoice] = useState('')
  const [remarks, setRemarks] = useState('')
  const [labRequested, setLabRequested] = useState(false)
  const [correctingReport, setCorrectingReport] = useState(null)

  const loadAll = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [s, hs, reps, refs, act] = await Promise.all([
        api.dashboard(), api.hotspots(), api.allReports(), api.referrals(), api.agentActivity(),
      ])
      setStats(s); setHotspots(hs); setReports(reps); setReferrals(refs); setActivity(act)
      const [fb, vs, ms] = await Promise.all([api.feedback(), api.modelVersions(), api.modelStatus()])
      setFeedback(fb); setVersions(vs); setModelStatus(ms)
    } catch (err) {
      setError(err.message || t('loadFailed'))
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => { loadAll() }, [loadAll])

  const verify = async (report, correctedDisease) => {
    setError('')
    try {
      await api.verifyReport(report.id, {
        corrected_disease: correctedDisease || null,
        remarks: remarks || null,
        lab_sample_requested: labRequested,
      })
      setCorrectingId(null); setCorrectingReport(null); setRemarks(''); setLabRequested(false)
      loadAll()
    } catch (err) {
      setError(err.message)
    }
  }

  const setRefStatus = async (ref, status) => {
    try {
      await api.setReferralStatus(ref.id, { status })
      loadAll()
    } catch (err) {
      setError(err.message)
    }
  }

  const queueRetrain = async () => {
    try {
      await api.queueRetraining()
      setRetrainQueued(true)
      loadAll()
      setTimeout(() => setRetrainQueued(false), 4000)
    } catch (err) {
      setError(err.message)
    }
  }

  const exportCsv = async (kind) => {
    setError('')
    try {
      const { blob, filename } = await api.exportCsv(kind)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch (err) {
      setError(err.message || 'Export failed.')
    }
  }

  /* map data derived from backend hotspots (not frontend aggregation) */
  const mapData = Object.keys(LOCATION_COORDS).map((loc) => {
    const h = hotspots.find((x) => x.location === loc)
    return {
      loc, ...LOCATION_COORDS[loc],
      count: h?.report_count || 0,
      dominant: h?.dominant_risk || null,
      disease: h?.dominant_disease || null,
      hotspot: h?.is_potential_hotspot || false,
    }
  })

  const diseaseCounts = stats ? [] : []
  const topDiseases = (stats?.recent_reports || []).length >= 0
    ? Object.entries(
        (reports || []).reduce((acc, r) => {
          const key = r.is_healthy ? t('healthy') : (r.disease || t('healthy'))
          acc[key] = (acc[key] || 0) + 1
          return acc
        }, {})
      ).sort((a, b) => b[1] - a[1]).slice(0, 5)
    : []

  const pendingVerify = (reports || []).filter((r) => !r.officer_verified && r.status !== 'PENDING')
  const openReferrals = (referrals || []).filter((r) => r.status !== 'RESOLVED')

  return (
    <div className="min-h-screen">
      <div className="flex items-center justify-between px-6 py-4" style={{ background: C.forest }}>
        <div className="flex items-center gap-2">
          <Landmark color={C.wheat} size={20} />
          <span className="ag-display text-lg text-white">{t('appName')}</span>
          <Pill color={C.wheat}>{t('nav_official')}</Pill>
        </div>
        <button onClick={onLogout} className="text-white/85 text-sm flex items-center gap-1"><LogOut size={15} /> {t('logout')}</button>
      </div>

      <div className="max-w-5xl mx-auto px-5 py-8">
        <h2 className="ag-display text-2xl" style={{ color: C.forest }}>{t('officerHeading')}</h2>
        <p className="ag-body text-sm mb-2" style={{ color: 'rgba(20,35,26,0.6)' }}>{t('officerSub')}</p>
        <p className="ag-body text-xs mb-4 flex items-center gap-1" style={{ color: 'rgba(20,35,26,0.45)' }}><Database size={12} /> {t('dbNote')}</p>

        {/* tabs */}
        <div className="flex flex-wrap gap-2 mb-6" key={`tabs-${tab}`}>
          {['dashboard', 'referrals', 'feedback', 'model'].map((tabName) => (
            <button key={tabName} onClick={() => setTab(tabName)}
              className="ag-magnetic rounded-full px-4 py-1.5 text-sm font-semibold transition-all duration-500 hover:-translate-y-0.5 hover:shadow-lg"
              style={tab === tabName
                ? { background: C.forest, color: 'white', boxShadow: '0 10px 26px -14px rgba(19,41,32,.7)' }
                : { border: `1px solid ${C.line}`, color: 'rgba(20,35,26,0.65)' }}>
              {t(`tab${tabName.charAt(0).toUpperCase()}${tabName.slice(1)}`)}
            </button>
          ))}
        </div>

        {error && <div className="mb-4"><ErrorBox message={error} onRetry={loadAll} retryLabel={t('refresh')} /></div>}
        {loading && <LoadingBox>{t('loadingReports') || 'Loading…'}</LoadingBox>}

        {/* ================= DASHBOARD TAB ================= */}
        {tab === 'dashboard' && !loading && (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3 mb-6">
              <StatCard label={t('statTotal')} value={stats?.total_reports ?? 0} />
              <StatCard label={t('statHigh')} value={stats?.high_risk ?? 0} color={C.red} />
              <StatCard label={t('statMod')} value={stats?.moderate_risk ?? 0} color={C.amber} />
              <StatCard label={t('statLow')} value={stats?.low_risk ?? 0} color={C.green} />
              <StatCard label={t('statPendingVerify')} value={stats?.pending_verification ?? 0} color={C.forest} />
              <StatCard label={t('statReferrals')} value={stats?.open_referrals ?? 0} color={C.wheatDeep} />
            </div>

            <div className="flex flex-wrap gap-2 mb-6">
              <button onClick={loadAll} className="ag-body inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold" style={{ border: `1px solid ${C.line}` }}>
                <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> {t('refresh')}
              </button>
              <button onClick={() => exportCsv('reports')} className="ag-body inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold" style={{ background: C.moss, color: 'white' }}>
                <Download size={14} /> {t('exportBtn')} — {t('tblCrop')}
              </button>
              <button onClick={() => exportCsv('sensors')} className="ag-body inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold" style={{ border: `1px solid ${C.line}` }}>
                <Download size={14} /> {t('tblSensor')}
              </button>
            </div>

            <div className="grid md:grid-cols-2 gap-4 mb-6">
              <div className="rounded-xl p-5" style={{ background: C.white, border: `1px solid ${C.line}` }}>
                <p className="text-xs font-semibold mb-3" style={{ color: 'rgba(20,35,26,0.55)' }}>{t('topDiseases')}</p>
                {topDiseases.length === 0 ? <p className="text-sm" style={{ color: 'rgba(20,35,26,0.4)' }}>—</p> : topDiseases.map(([d, n]) => (
                  <div key={d} className="flex justify-between text-sm py-1.5 border-b" style={{ borderColor: C.line }}>
                    <span>{d}</span><strong>{n}</strong>
                  </div>
                ))}
              </div>
              <div className="rounded-xl p-5" style={{ background: C.white, border: `1px solid ${C.line}` }}>
                <p className="text-xs font-semibold mb-3" style={{ color: 'rgba(20,35,26,0.55)' }}>{t('hotspots')}</p>
                {hotspots.length === 0 ? <p className="text-sm" style={{ color: 'rgba(20,35,26,0.4)' }}>—</p> : hotspots.slice(0, 6).map((h) => (
                  <div key={h.location} className="flex justify-between text-sm py-1.5 border-b" style={{ borderColor: C.line }}>
                    <span className="flex items-center gap-1"><MapPin size={12} /> {h.location}
                      {h.is_potential_hotspot && <Pill color={C.red}>{t('potentialHotspot')}</Pill>}
                    </span>
                    <strong>{h.report_count}</strong>
                  </div>
                ))}
              </div>
            </div>

            {/* hotspot map */}
            <div className="rounded-xl p-5 mb-6" style={{ background: C.white, border: `1px solid ${C.line}` }}>
              <p className="text-xs font-semibold mb-1 flex items-center gap-1.5" style={{ color: 'rgba(20,35,26,0.55)' }}><Map2 size={14} /> {t('mapTitle')}</p>
              <p className="text-xs mb-3" style={{ color: 'rgba(20,35,26,0.4)' }}>{t('mapNote')}</p>
              <div className="rounded-lg overflow-hidden relative" style={{ background: '#e8f0e4', border: `1px solid ${C.line}`, aspectRatio: '4/3' }}>
                <svg viewBox="0 0 100 100" className="w-full h-full">
                  <rect x="0" y="0" width="100" height="100" fill="#e8f0e4" />
                  <path d="M20 15 L70 8 L88 22 L92 40 L80 55 L82 72 L60 92 L38 88 L25 70 L10 60 L12 35 Z" fill="#d7e6cf" stroke="#b6cbab" strokeWidth="0.6" />
                  {mapData.map((m) => {
                    const r = 2.5 + Math.min(6, m.count * 1.4)
                    const col = m.dominant === 'High' ? C.red : m.dominant === 'Moderate' ? C.amber : m.dominant === 'Low' ? C.green : '#9fb3a3'
                    return (
                      <g key={m.loc}>
                        {m.count > 0 && (
                          <circle cx={m.x} cy={m.y} r={r + 3} fill={col} opacity="0.18">
                            {m.hotspot && (
                              <animate attributeName="r" values={`${r + 3};${r + 8};${r + 3}`} dur="2.4s" repeatCount="indefinite" />
                            )}
                            {m.hotspot && (
                              <animate attributeName="opacity" values="0.28;0.06;0.28" dur="2.4s" repeatCount="indefinite" />
                            )}
                          </circle>
                        )}
                        <circle cx={m.x} cy={m.y} r={r} fill={col} opacity="0.85" stroke="white" strokeWidth="0.6" />
                        <text x={m.x} y={m.y - r - 2.5} fontSize="3.4" textAnchor="middle" fill={C.ink} fontWeight="600">{m.loc}</text>
                        {m.count > 0 && <text x={m.x} y={m.y + 1.2} fontSize="3" textAnchor="middle" fill="white" fontWeight="700">{m.count}</text>}
                        {m.hotspot && (
                          <text x={m.x} y={m.y + r + 5} fontSize="2.6" textAnchor="middle" fill={C.red} fontWeight="700">★ {t('potentialHotspot')}</text>
                        )}
                      </g>
                    )
                  })}
                </svg>
              </div>
              <div className="flex flex-wrap gap-3 mt-3 text-xs">
                <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: C.red }} /> {t('severity_High')}</span>
                <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: C.amber }} /> {t('severity_Moderate')}</span>
                <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: C.green }} /> {t('severity_Low')}</span>
              </div>
            </div>

            {/* agent activity feed */}
            <div className="rounded-xl p-5 mb-6" style={{ background: C.forestDark }}>
              <p className="ag-display text-lg mb-3 flex items-center gap-2 text-white"><Sparkles size={16} color={C.wheat} /> {t('agentActivityTitle')}</p>
              <ol className="space-y-1.5">
                {activity.slice(0, 12).map((a) => (
                  <li key={a.id} className="flex items-start gap-2 text-xs">
                    <span className="rounded px-1.5 py-0.5 font-bold flex-shrink-0" style={{ background: 'rgba(216,165,61,0.2)', color: C.wheat }}>
                      {t(`stage_${a.stage}`) || a.stage}
                    </span>
                    <span style={{ color: 'rgba(255,255,255,0.85)' }}>{a.message}</span>
                    <span className="ml-auto flex-shrink-0" style={{ color: 'rgba(255,255,255,0.4)' }}>{new Date(a.created_at).toLocaleTimeString()}</span>
                  </li>
                ))}
                {activity.length === 0 && <li className="text-xs" style={{ color: 'rgba(255,255,255,0.45)' }}>{t('agentActivityEmpty')}</li>}
              </ol>
            </div>

            {/* recent reports table */}
            <div className="rounded-xl p-5" style={{ background: C.white, border: `1px solid ${C.line}` }}>
              <p className="text-xs font-semibold mb-3" style={{ color: 'rgba(20,35,26,0.55)' }}>{t('recentReports')}</p>
              {reports.length === 0 ? (
                <p className="text-sm" style={{ color: 'rgba(20,35,26,0.5)' }}>{t('noReports')}</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left" style={{ color: 'rgba(20,35,26,0.5)' }}>
                        <th className="py-2 pr-3 font-medium">{t('tblFarmer')}</th>
                        <th className="py-2 pr-3 font-medium">{t('tblCrop')}</th>
                        <th className="py-2 pr-3 font-medium">{t('tblIssue')}</th>
                        <th className="py-2 pr-3 font-medium">{t('tblSeverity')}</th>
                        <th className="py-2 pr-3 font-medium">{t('tblRisk')}</th>
                        <th className="py-2 pr-3 font-medium">{t('tblStatus')}</th>
                        <th className="py-2 pr-3 font-medium">{t('tblAction')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {reports.slice(0, 15).map((r) => (
                        <Fragment key={r.id}>
                          <tr style={{ borderTop: `1px solid ${C.line}` }}>
                            <td className="py-2 pr-3">{r.farmer_name || '—'}</td>
                            <td className="py-2 pr-3">{r.crop}</td>
                            <td className="py-2 pr-3">
                              {r.is_healthy ? t('healthy') : r.disease}
                              {r.is_demo_inference && <Pill color={C.amber}>DEMO</Pill>}
                            </td>
                            <td className="py-2 pr-3">{t(`severity_${r.severity}`)}</td>
                            <td className="py-2 pr-3"><Pill color={riskColor(r.risk_level)}>{t(`severity_${r.risk_level}`)}</Pill></td>
                            <td className="py-2 pr-3">
                              {r.officer_verified ? <span style={{ color: C.green }}>{t('verified')}</span>
                                : <span style={{ color: C.amber }}>{t('pending')}</span>}
                            </td>
                            <td className="py-2 pr-3">
                              {!r.officer_verified && r.status !== 'PENDING' && (
                                <div className="flex items-center gap-2">
                                  <button onClick={() => verify(r, null)} className="text-xs font-semibold underline" style={{ color: C.forest }}>{t('agreeBtn')}</button>
                                  <button onClick={() => { setCorrectingId(r.id); setCorrectionChoice((DISEASE_MAP[r.crop] || [])[0] || ''); setCorrectingReport(r) }}
                                    className="text-xs font-semibold underline" style={{ color: C.amber }}>{t('correctBtn')}</button>
                                </div>
                              )}
                            </td>
                          </tr>
                          {correctingId === r.id && (
                            <tr style={{ background: C.creamDeep }}>
                              <td colSpan={7} className="py-2 px-3">
                                <div className="flex flex-wrap items-center gap-2">
                                  <span className="text-xs font-semibold">{t('selectActualLabel')}</span>
                                  <select value={correctionChoice} onChange={(e) => setCorrectionChoice(e.target.value)}
                                    className="rounded-lg px-2 py-1 text-xs" style={{ border: `1px solid ${C.line}` }}>
                                    {(DISEASE_MAP[r.crop] || []).map((d) => <option key={d} value={d}>{d}</option>)}
                                  </select>
                                  <input value={remarks} onChange={(e) => setRemarks(e.target.value)} placeholder={t('remarksLabel')}
                                    className="rounded-lg px-2 py-1 text-xs flex-1 min-w-[140px]" style={{ border: `1px solid ${C.line}` }} />
                                  <label className="text-xs flex items-center gap-1">
                                    <input type="checkbox" checked={labRequested} onChange={(e) => setLabRequested(e.target.checked)} />
                                    {t('requestLabSample')}
                                  </label>
                                  <button onClick={() => verify(r, correctionChoice)} className="text-xs font-semibold rounded-full px-3 py-1.5" style={{ background: C.forest, color: 'white' }}>{t('verifyBtn')}</button>
                                  <button onClick={() => setCorrectingId(null)} className="text-xs underline" style={{ color: 'rgba(20,35,26,0.5)' }}><X size={12} /></button>
                                </div>
                              </td>
                            </tr>
                          )}
                        </Fragment>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </>
        )}

        {/* ================= REFERRALS TAB ================= */}
        {tab === 'referrals' && !loading && (
          <div className="rounded-xl p-5" style={{ background: C.white, border: `1px solid ${C.line}` }}>
            <p className="text-xs font-semibold mb-3 flex items-center gap-1.5" style={{ color: 'rgba(20,35,26,0.55)' }}><Stethoscope size={14} /> {t('referralQueueTitle')}</p>
            {referrals.length === 0 ? (
              <p className="text-sm" style={{ color: 'rgba(20,35,26,0.5)' }}>{t('referralEmpty')}</p>
            ) : (
              <div className="space-y-2">
                {referrals.map((r) => (
                  <div key={r.id} className="flex flex-wrap items-center justify-between gap-2 text-sm py-2 border-b" style={{ borderColor: C.line }}>
                    <div>
                      <div className="font-medium">{r.farmer_name} · {r.crop}{r.disease ? ` · ${r.disease}` : ''}</div>
                      <div className="text-xs" style={{ color: 'rgba(20,35,26,0.5)' }}><MapPin size={11} className="inline mr-1" />{r.location} — {r.reason}</div>
                    </div>
                    {r.status === 'RESOLVED' ? (
                      <Pill color={C.green}>{t('resolvedStatus')}</Pill>
                    ) : (
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <Pill color={C.amber}>{r.status}</Pill>
                        {r.status === 'PENDING' && (
                          <button onClick={() => setRefStatus(r, 'IN_PROGRESS')} className="text-xs font-semibold underline" style={{ color: C.forest }}>{t('officerReview')}</button>
                        )}
                        <button onClick={() => setRefStatus(r, 'RESOLVED')} className="text-xs font-semibold underline" style={{ color: C.forest }}>{t('resolveBtn')}</button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ================= FEEDBACK TAB ================= */}
        {tab === 'feedback' && !loading && (
          <>
            <div className="rounded-xl p-5 mb-6" style={{ background: C.forest }}>
              <p className="text-sm font-semibold mb-1 flex items-center gap-2 text-white"><BrainCog size={16} color={C.wheat} /> {t('modelLoopTitle')}</p>
              <p className="text-xs mb-4 text-white/65">{t('modelLoopDesc')}</p>
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <HistoryIcon size={16} color={C.wheat} />
                  <span className="text-white text-sm"><strong>{feedback.length}</strong> {t('correctionsLabel')}</span>
                </div>
                <button onClick={queueRetrain} disabled={retrainQueued}
                  className="ag-body inline-flex items-center gap-2 rounded-full px-4 py-2 text-xs font-semibold"
                  style={{ background: C.wheat, color: C.forestDark, opacity: retrainQueued ? 0.7 : 1 }}>
                  {retrainQueued ? <RefreshCw size={13} className="animate-spin" /> : <TrendingUp size={13} />}
                  {t('retrainBtn')}
                </button>
              </div>
              {retrainQueued && <p className="text-xs mt-2 text-white/80">{t('retrainingMsg')}</p>}
              <button onClick={() => exportCsv('feedback')} className="text-xs underline mt-3 flex items-center gap-1" style={{ color: C.wheat }}>
                <Download size={12} /> {t('exportBtn')}
              </button>
            </div>
            <div className="rounded-xl p-5" style={{ background: C.white, border: `1px solid ${C.line}` }}>
              {feedback.length === 0 ? (
                <p className="text-sm" style={{ color: 'rgba(20,35,26,0.5)' }}>{t('referralEmpty')}</p>
              ) : (
                <div className="space-y-2">
                  {feedback.map((f) => (
                    <div key={f.id} className="flex flex-wrap items-center justify-between gap-2 text-sm py-2 border-b" style={{ borderColor: C.line }}>
                      <div>
                        <div className="font-medium">
                          #{f.report_id} {f.crop} — {t('feedbackPredicted')}: {f.predicted_disease || t('healthy')} · {t('feedbackActual')}: {f.actual_disease || t('healthy')}
                        </div>
                        <div className="text-xs" style={{ color: 'rgba(20,35,26,0.5)' }}>{f.officer_name} · {new Date(f.created_at).toLocaleString()}</div>
                      </div>
                      <div className="flex items-center gap-2">
                        {f.was_correct ? <Pill color={C.green}>{t('feedbackCorrect')}</Pill> : <Pill color={C.red}>{t('feedbackCorrected')}</Pill>}
                        {f.in_retraining_queue && <Pill color={C.forest}>{t('feedbackQueue')}</Pill>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}

        {/* ================= MODEL TAB ================= */}
        {tab === 'model' && !loading && (
          <>
            <div className="rounded-xl p-5 mb-6" style={{ background: C.white, border: `1px solid ${C.line}` }}>
              <p className="text-xs font-semibold mb-3" style={{ color: 'rgba(20,35,26,0.55)' }}>{t('modelStatusTitle')}</p>
              {modelStatus && (
                <div className="grid sm:grid-cols-2 gap-3">
                  <div className="flex justify-between border-b py-2 text-sm" style={{ borderColor: C.line }}>
                    <span style={{ color: 'rgba(20,35,26,0.55)' }}>{t('modelVersion')}</span>
                    <strong>{modelStatus.model_version}</strong>
                  </div>
                  <div className="flex justify-between border-b py-2 text-sm" style={{ borderColor: C.line }}>
                    <span style={{ color: 'rgba(20,35,26,0.55)' }}>{t('modelStatus')}</span>
                    <Pill color={modelStatus.ai_mode === 'REAL_MODEL' ? C.green : C.amber}>
                      {modelStatus.ai_mode === 'REAL_MODEL' ? t('realInferenceBadge') : 'DEMO'}
                    </Pill>
                  </div>
                </div>
              )}
              <p className="text-xs mt-3" style={{ color: 'rgba(20,35,26,0.5)' }}>{modelStatus?.demo_note}</p>
            </div>
            <div className="rounded-xl p-5" style={{ background: C.white, border: `1px solid ${C.line}` }}>
              <p className="text-xs font-semibold mb-3" style={{ color: 'rgba(20,35,26,0.55)' }}>{t('modelVersion')}</p>
              {versions.map((v) => (
                <div key={v.id} className="flex flex-wrap justify-between gap-2 text-sm py-2 border-b" style={{ borderColor: C.line }}>
                  <span><strong>{v.version}</strong> · {v.model_name}</span>
                  <span className="flex items-center gap-2">
                    <Pill color={v.status === 'ACTIVE' ? C.green : C.amber}>{v.status}</Pill>
                    {v.accuracy != null && <span className="text-xs">{t('modelAccuracy')}: {(v.accuracy * 100).toFixed(1)}%</span>}
                  </span>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
