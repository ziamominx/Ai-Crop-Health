import { useCallback, useEffect, useRef, useState } from 'react'
import { C, riskColor } from '../api/theme.js'
import {
  AlertTriangle, Bell, BrainCog, Bug, Camera, CheckCircle2, Clock, CloudRain, Droplets,
  FlaskConical, ImagePlus, LogOut, MapPin, Plus, RefreshCw, ShieldCheck, Sparkles, Sprout,
  Stethoscope, ThermometerSun, Upload, Wifi, X,
} from '../api/icons.jsx'
import { ErrorBox, Pill } from '../components/ui.jsx'
import { AgentActivity } from '../components/AgentActivity.jsx'
import { AnalysisProgress, Reveal } from '../components/motion.jsx'
import { WhyThisDecision } from '../components/WhyThisDecision.jsx'
import { api } from '../api/client.js'
import { useLanguage } from '../hooks/useLanguage.jsx'
import { useAuth } from '../hooks/useAuth.jsx'
import { CROPS, LOCATIONS, REFERRAL_REASONS, TRAP_TYPES } from '../i18n/translations.js'

const TREATMENT_MAP = {
  'Early Blight': { category: 'Fungicide (protectant)', timing: 'Spray in the early morning or evening, not in direct sun', phi: '7 days', note: 'Rotate fungicide groups each season to avoid resistance.' },
  'Late Blight': { category: 'Fungicide (systemic)', timing: 'Apply before rain if forecast; reapply after heavy rain', phi: '7–10 days', note: 'Destroy infected debris away from the field — do not compost.' },
  'Leaf Curl Virus': { category: 'No direct chemical cure — control the whitefly vector', timing: 'Use yellow sticky traps; treat only the vector as per label', phi: 'As per vector treatment label', note: 'Remove and destroy infected plants to stop virus spread.' },
  'Yellow Rust': { category: 'Fungicide (triazole group)', timing: 'Apply at first sign of yellow stripes on leaves', phi: '21–35 days (cereal-specific)', note: 'Check resistant wheat varieties for your next sowing.' },
  'Powdery Mildew': { category: 'Fungicide (sulfur-based or systemic)', timing: 'Apply when white powdery patches first appear', phi: 'As per label', note: 'Improve row spacing to reduce humidity around plants.' },
  'Bollworm Damage': { category: 'Insecticide (as per IPM ladder) or Bt-based biopesticide', timing: 'Spray in the evening when pollinators are less active', phi: 'As per label', note: 'Install pheromone traps to monitor moth activity first.' },
  'Blast': { category: 'Fungicide (systemic, rice-specific)', timing: 'Apply at boot-leaf stage if disease pressure is high', phi: '21 days', note: 'Avoid excess nitrogen fertilizer — it increases blast risk.' },
  'Bacterial Leaf Blight': { category: 'Copper-based bactericide', timing: 'Apply at first yellowing of leaf margins', phi: 'As per label', note: 'Avoid working in wet fields — this spreads bacteria on tools and hands.' },
  'Purple Blotch': { category: 'Fungicide (protectant)', timing: 'Begin spraying at first purple lesions on leaves', phi: '7–14 days', note: 'Avoid overhead irrigation late in the day.' },
}
const GENERIC_SAFETY = [
  'Always read and follow the product label before use',
  'Wear gloves, a mask, and full sleeves while spraying',
  'Do not spray in windy conditions or right before rain',
  'Keep children and animals away from treated fields',
  'Wash hands and equipment thoroughly after use',
]

/* Real demo photos (Wikimedia Commons, CC-licensed — see public/demo-photos/CREDITS.txt).
   Each crop has a diseased sample and a healthy sample so both outcomes can be shown.
   BASE_URL keeps these working when the app is served from a sub-path (GitHub Pages). */
const ASSET_BASE = (import.meta.env.BASE_URL || '/').replace(/\/$/, '')
const demoPhotoFor = (crop, healthy = false) =>
  `${ASSET_BASE}/demo-photos/${String(crop).toLowerCase()}${healthy ? '-healthy' : ''}.jpg`
/* The published GitHub Pages build ships without the backend, so it can play back
   a bundled demo photo but cannot analyse a brand-new upload. */
const STATIC_DEMO = import.meta.env.VITE_STATIC_DEMO === 'true'
const demoVariantName = (file) => (file?.name || '').endsWith('-healthy.jpg') ? 'healthy' : 'diseased'

export function FarmerPage({ onLogout }) {
  const { t } = useLanguage()
  const { user, logout } = useAuth()

  const [farms, setFarms] = useState([])
  const [farmId, setFarmId] = useState('')
  const [showFarmForm, setShowFarmForm] = useState(false)
  const [farmForm, setFarmForm] = useState({ farm_name: '', location: LOCATIONS[0] })
  const [farmError, setFarmError] = useState('')

  const [crop, setCrop] = useState(CROPS[0])
  const [photoFile, setPhotoFile] = useState(null)
  const [photoUrl, setPhotoUrl] = useState(null)
  const [demoHealthy, setDemoHealthy] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [result, setResult] = useState(null)
  const [history, setHistory] = useState([])
  const [needPhotoWarn, setNeedPhotoWarn] = useState(false)
  const [submitError, setSubmitError] = useState('')
  const fileRef = useRef(null)

  const [trapType, setTrapType] = useState(TRAP_TYPES[0])
  const [trapCount, setTrapCount] = useState('')
  const [soilMoisture, setSoilMoisture] = useState('')
  const [leafWetness, setLeafWetness] = useState('')

  const [referralReason, setReferralReason] = useState(REFERRAL_REASONS[0])
  const [referralSentFor, setReferralSentFor] = useState(null)
  const [referrals, setReferrals] = useState([])

  const [notifs, setNotifs] = useState([])
  const [notifOpen, setNotifOpen] = useState(false)

  const loadCore = useCallback(async () => {
    try {
      const [f, h, r] = await Promise.all([api.farms(), api.myReports(), api.myReferrals()])
      setFarms(f)
      setHistory(h)
      setReferrals(r)
      if (f.length && !farmId) setFarmId(String(f[0].id))
    } catch (err) {
      setSubmitError(err.message)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => { loadCore() }, [loadCore])
  useEffect(() => {
    if (!notifOpen) return
    api.notifications().then(setNotifs).catch(() => {})
  }, [notifOpen])

  const createFarm = async (e) => {
    e.preventDefault()
    setFarmError('')
    try {
      const farm = await api.createFarm(farmForm)
      setFarms([...farms, farm])
      setFarmId(String(farm.id))
      setShowFarmForm(false)
      setFarmForm({ farm_name: '', location: LOCATIONS[0] })
    } catch (err) {
      setFarmError(err.message)
    }
  }

  const handleFile = (e) => {
    const file = e.target.files && e.target.files[0]
    if (!file) return
    setNeedPhotoWarn(false)
    setResult(null)
    setSubmitError('')
    setPhotoFile(file)
    setPhotoUrl(URL.createObjectURL(file))
  }

  const useDemoPhoto = async () => {
    setNeedPhotoWarn(false)
    setResult(null)
    setSubmitError('')
    // Alternate between the diseased and healthy sample on each press.
    let wantHealthy = photoFile?.name?.startsWith('demo-') ? !demoHealthy : false
    try {
      // Fetch the real demo photo for the selected crop and attach it as the upload.
      let res = await fetch(demoPhotoFor(crop, wantHealthy))
      if (!res.ok && wantHealthy) {
        // No healthy sample for this crop — fall back to the diseased one
        wantHealthy = false
        res = await fetch(demoPhotoFor(crop, false))
      }
      if (!res.ok) throw new Error('demo photo missing')
      const blob = await res.blob()
      const file = new File([blob], `demo-${crop.toLowerCase()}${wantHealthy ? '-healthy' : ''}.jpg`, { type: 'image/jpeg' })
      setPhotoFile(file)
      setPhotoUrl(URL.createObjectURL(blob))
      setDemoHealthy(wantHealthy)
    } catch {
      setSubmitError(t('loadFailed'))
    }
  }

  const resetUpload = () => {
    setPhotoFile(null); setPhotoUrl(null); setResult(null)
    setNeedPhotoWarn(false); setSubmitError(''); setReferralSentFor(null)
    if (fileRef.current) fileRef.current.value = ''
  }

  const analyse = async () => {
    if (!photoUrl) { setNeedPhotoWarn(true); return }
    if (!farmId) { setFarmError(t('addFarm')); return }
    setAnalyzing(true)
    setResult(null)
    setSubmitError('')
    try {
      const fd = new FormData()
      fd.append('crop', crop)
      fd.append('farm_id', farmId)
      if (photoFile) fd.append('image', photoFile)
      if (trapCount) fd.append('pest_count', trapCount)
      if (soilMoisture) fd.append('soil_moisture', soilMoisture)
      if (leafWetness) fd.append('leaf_wetness', leafWetness)
      fd.append('trap_type', trapType)

      const startedAt = Date.now()
      let report = await api.submitReport(fd)
      // Poll while the agent pipeline runs (perception → decision → action)
      for (let i = 0; i < 40 && report.status === 'PENDING'; i++) {
        await new Promise((r) => setTimeout(r, 300))
        report = await api.reportDetail(report.id)
      }
      // The pipeline can finish in a few hundred ms on a local demo machine.
      // Hold the UI just long enough for the agent-loop animation to be seen —
      // this only paces the display, it never alters the stored result.
      const MIN_PIPELINE_MS = 1250
      const remaining = MIN_PIPELINE_MS - (Date.now() - startedAt)
      if (remaining > 0) await new Promise((r) => setTimeout(r, remaining))
      setResult(report)
      setHistory([report, ...history])
      loadCore()
    } catch (err) {
      setSubmitError(err.message || t('submitReportFailed'))
    } finally {
      setAnalyzing(false)
    }
  }

  const requestReferral = async () => {
    try {
      const ref = await api.createReferral({ report_id: result.id, reason: referralReason })
      setReferralSentFor(result.id)
      setReferrals([ref, ...referrals])
    } catch (err) {
      setSubmitError(err.message)
    }
  }

  const openReferralFor = (rid) => referrals.find((r) => r.report_id === rid && r.status !== 'RESOLVED')

  const unread = notifs.filter((n) => !n.is_read).length
  const highRiskHistory = history.filter((h) => h.risk_level === 'High')

  return (
    <div className="min-h-screen">
      {/* ---- Header ---- */}
      <div className="flex items-center justify-between px-6 py-4" style={{ background: C.forest }}>
        <div className="flex items-center gap-2">
          <Sprout color={C.wheat} size={20} />
          <span className="ag-display text-lg text-white">{t('appName')}</span>
          <Pill color={C.wheat}>{t('nav_farmer')}</Pill>
        </div>
        <div className="flex items-center gap-4">
          <div className="relative">
            <button onClick={() => setNotifOpen((v) => !v)} className="text-white/90 relative">
              <Bell size={19} />
              {unread > 0 && (
                <span className="absolute -top-1.5 -right-1.5 w-4 h-4 rounded-full text-[10px] flex items-center justify-center font-bold" style={{ background: C.wheat, color: C.forestDark }}>
                  {unread}
                </span>
              )}
            </button>
            {notifOpen && (
              <div className="absolute right-0 mt-2 w-80 rounded-xl shadow-lg z-10 overflow-hidden" style={{ background: C.white, border: `1px solid ${C.line}` }}>
                <div className="px-4 py-2.5 flex items-center justify-between" style={{ background: C.creamDeep }}>
                  <span className="text-xs font-semibold" style={{ color: C.forest }}>{t('notifTitle')}</span>
                  <div className="flex items-center gap-2">
                    <button onClick={() => api.markAllRead().then(() => setNotifs(notifs.map((n) => ({ ...n, is_read: true })))).catch(() => {})}
                      className="text-xs underline" style={{ color: C.forest }}>{t('markAllRead')}</button>
                    <button onClick={() => setNotifOpen(false)}><X size={14} color={C.forest} /></button>
                  </div>
                </div>
                <div className="max-h-72 overflow-y-auto">
                  {notifs.length === 0 ? (
                    <p className="text-xs px-4 py-4" style={{ color: 'rgba(20,35,26,0.5)' }}>{t('notifEmpty')}</p>
                  ) : notifs.map((n) => (
                    <div key={n.id} className="px-4 py-2.5 text-xs border-b" style={{ borderColor: C.line, opacity: n.is_read ? 0.6 : 1 }}>
                      <div className="flex items-start gap-2">
                        {n.type === 'HIGH_RISK' ? <AlertTriangle size={13} color={C.red} className="flex-shrink-0 mt-0.5" />
                          : n.type === 'VERIFICATION' ? <ShieldCheck size={13} color={C.green} className="flex-shrink-0 mt-0.5" />
                          : <Bell size={13} color={C.moss} className="flex-shrink-0 mt-0.5" />}
                        <div>
                          <div className="font-semibold">{n.title}</div>
                          <div style={{ color: 'rgba(20,35,26,0.6)' }}>{n.message}</div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
          <button onClick={() => { logout(); onLogout() }} className="text-white/85 text-sm flex items-center gap-1">
            <LogOut size={15} /> {t('logout')}
          </button>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-5 py-8">
        <h2 className="ag-display text-2xl" style={{ color: C.forest }}>
          {t('fGreeting')}, {user?.name}
        </h2>
        <p className="ag-body text-sm mb-6" style={{ color: 'rgba(20,35,26,0.6)' }}>{t('fSubGreeting')}</p>

        {/* ---- New crop check ---- */}
        <div className="rounded-2xl p-6 mb-6" style={{ background: C.white, border: `1px solid ${C.line}` }}>
          <h3 className="ag-display text-xl" style={{ color: C.forest }}>{t('uploadTitle')}</h3>
          <p className="ag-body text-sm mb-4" style={{ color: 'rgba(20,35,26,0.6)' }}>{t('uploadDesc')}</p>

          <div className="grid sm:grid-cols-2 gap-3 mb-4">
            <div>
              <label className="text-xs font-semibold block mb-1">{t('cropLabel')}</label>
              <select value={crop} onChange={(e) => setCrop(e.target.value)} className="w-full rounded-lg px-3 py-2 text-sm" style={{ border: `1px solid ${C.line}` }}>
                {CROPS.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold block mb-1">{t('farmLabel')}</label>
              <div className="flex gap-2">
                <select value={farmId} onChange={(e) => setFarmId(e.target.value)} className="flex-1 rounded-lg px-3 py-2 text-sm" style={{ border: `1px solid ${C.line}` }}>
                  {farms.length === 0 && <option value="">—</option>}
                  {farms.map((f) => <option key={f.id} value={f.id}>{f.farm_name} · {f.location}</option>)}
                </select>
                <button onClick={() => setShowFarmForm((v) => !v)} title={t('addFarm')}
                  className="rounded-lg px-3 text-sm font-semibold" style={{ background: C.creamDeep, color: C.forest }}>
                  <Plus size={15} />
                </button>
              </div>
            </div>
          </div>

          {showFarmForm && (
            <form onSubmit={createFarm} className="rounded-xl p-4 mb-4 grid sm:grid-cols-2 gap-3" style={{ background: C.creamDeep, border: `1px solid ${C.line}` }}>
              <div>
                <label className="text-xs font-semibold block mb-1">{t('farmNameLabel')}</label>
                <input required value={farmForm.farm_name} onChange={(e) => setFarmForm({ ...farmForm, farm_name: e.target.value })}
                  className="w-full rounded-lg px-3 py-2 text-sm" style={{ border: `1px solid ${C.line}` }} />
              </div>
              <div>
                <label className="text-xs font-semibold block mb-1">{t('locationLabel')}</label>
                <select value={farmForm.location} onChange={(e) => setFarmForm({ ...farmForm, location: e.target.value })}
                  className="w-full rounded-lg px-3 py-2 text-sm" style={{ border: `1px solid ${C.line}` }}>
                  {LOCATIONS.map((l) => <option key={l} value={l}>{l}</option>)}
                </select>
              </div>
              {farmError && <div className="sm:col-span-2"><ErrorBox message={farmError} /></div>}
              <button type="submit" className="sm:col-span-2 rounded-lg py-2 text-sm font-semibold" style={{ background: C.forest, color: 'white' }}>
                {t('saveFarm')}
              </button>
            </form>
          )}

          {/* ---- Sensors (optional) ---- */}
          <div className="rounded-xl p-4 mb-4" style={{ background: C.creamDeep, border: `1px solid ${C.line}` }}>
            <p className="text-sm font-semibold flex items-center gap-2 mb-1" style={{ color: C.forest }}><Wifi size={15} /> {t('sensorTitle')}</p>
            <p className="text-xs mb-3" style={{ color: 'rgba(20,35,26,0.6)' }}>{t('sensorDesc')}</p>
            <div className="grid sm:grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold block mb-1 flex items-center gap-1"><Bug size={12} /> {t('trapTypeLabel')}</label>
                <select value={trapType} onChange={(e) => setTrapType(e.target.value)} className="w-full rounded-lg px-3 py-2 text-sm" style={{ border: `1px solid ${C.line}` }}>
                  {TRAP_TYPES.map((tt) => <option key={tt} value={tt}>{tt}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs font-semibold block mb-1">{t('trapCountLabel')}</label>
                <input type="number" min="0" value={trapCount} onChange={(e) => setTrapCount(e.target.value)} placeholder="0"
                  className="w-full rounded-lg px-3 py-2 text-sm" style={{ border: `1px solid ${C.line}` }} />
              </div>
              <div>
                <label className="text-xs font-semibold block mb-1">{t('soilMoistureLabel')}</label>
                <input type="number" min="0" max="100" value={soilMoisture} onChange={(e) => setSoilMoisture(e.target.value)} placeholder="—"
                  className="w-full rounded-lg px-3 py-2 text-sm" style={{ border: `1px solid ${C.line}` }} />
              </div>
              <div>
                <label className="text-xs font-semibold block mb-1">{t('leafWetnessLabel')}</label>
                <input type="number" min="0" max="24" value={leafWetness} onChange={(e) => setLeafWetness(e.target.value)} placeholder="—"
                  className="w-full rounded-lg px-3 py-2 text-sm" style={{ border: `1px solid ${C.line}` }} />
              </div>
            </div>
          </div>

          {/* ---- Photo ---- */}
          {!photoUrl ? (
            <div className="rounded-xl border-2 border-dashed p-8 text-center" style={{ borderColor: '#9fb3c4' }}>
              <ImagePlus className="mx-auto mb-3" color={C.moss} size={30} />
              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                {!STATIC_DEMO && (
                  <label className="ag-body cursor-pointer inline-flex items-center gap-2 rounded-full px-5 py-2.5 font-semibold text-sm" style={{ background: C.moss, color: 'white' }}>
                    <Upload size={15} /> {t('uploadBtn')}
                    <input ref={fileRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={handleFile} />
                  </label>
                )}
                <button onClick={useDemoPhoto} className="ag-body inline-flex items-center gap-2 rounded-full px-5 py-2.5 font-semibold text-sm" style={{ background: STATIC_DEMO ? C.moss : 'transparent', color: STATIC_DEMO ? 'white' : C.ink, border: `1px solid ${C.line}` }}>
                  <Camera size={15} /> {t('demoPhotoBtn')}
                </button>
              </div>
              {STATIC_DEMO && (
                <p className="ag-body text-xs mt-4 mx-auto max-w-md" style={{ color: 'rgba(20,35,26,0.6)' }}>
                  {t('staticUploadNote')}
                </p>
              )}
              {needPhotoWarn && <p className="text-xs mt-3 font-semibold" style={{ color: C.red }}>{t('needPhoto')}</p>}
            </div>
          ) : (
            <div>
              <div className="ag-zoom rounded-xl overflow-hidden mb-4 relative" style={{ aspectRatio: '4/3', background: C.creamDeep, border: `1px solid ${C.line}` }}>
                <img src={photoUrl} alt="crop" className="w-full h-full object-cover" />
                <span className="absolute bottom-2 left-2 text-xs px-2 py-1 rounded-md" style={{ background: 'rgba(255,255,255,0.9)', color: C.forest }}>
                  {photoFile?.name?.startsWith('demo-') ? `Demo photo — ${crop} (${photoFile.name.endsWith('-healthy.jpg') ? t('demoHealthyTag') : t('demoDiseasedTag')})` : crop}
                </span>
                <button onClick={resetUpload} className="absolute top-2 right-2 text-xs px-2 py-1 rounded-md" style={{ background: 'rgba(255,255,255,0.9)', color: C.forest }}>
                  <X size={13} className="inline" />
                </button>
              </div>
              <button onClick={analyse} disabled={analyzing || !farmId}
                className="ag-body w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-full px-6 py-2.5 font-semibold text-sm"
                style={{ background: C.forest, color: 'white', opacity: analyzing || !farmId ? 0.7 : 1 }}>
                {analyzing ? <RefreshCw size={15} className="animate-spin" /> : <Sparkles size={15} />}
                {analyzing ? t('analyzing') : t('analyzeBtn')}
              </button>
            </div>
          )}

          {/* ---- Live agent pipeline while the report is analysed ---- */}
          {analyzing && (
            <div className="ag-panel mt-4">
              <p className="text-xs font-semibold mb-2 flex items-center gap-2" style={{ color: C.forest }}>
                <RefreshCw size={13} className="animate-spin" /> {t('analyzing')}
              </p>
              <AnalysisProgress
                stages={[
                  t('stage_PERCEPTION'),
                  t('stage_MEMORY'),
                  t('stage_REASONING'),
                  t('stage_DECISION'),
                  t('stage_ACTION'),
                  t('stage_LEARNING'),
                ]}
              />
            </div>
          )}

          {submitError && <div className="mt-3"><ErrorBox message={submitError} onRetry={analyse} retryLabel={t('retry')} /></div>}
        </div>

        {/* ---- Result ---- */}
        {result && (
          <div className="ag-panel rounded-2xl p-6 mb-6" style={{ background: C.white, border: `1px solid ${C.line}` }}>
            <h3 className="ag-display text-xl mb-4" style={{ color: C.forest }}>{t('resultTitle')}</h3>

            {result.is_demo_inference ? (
              <div className="rounded-lg p-2.5 text-xs font-semibold mb-4 flex items-center gap-2" style={{ background: '#fff3dc', color: C.amber, border: '1px dashed #cbb148' }}>
                <AlertTriangle size={14} /> {t('demoInferenceBadge')}
              </div>
            ) : String(result.model_version || '').startsWith('heuristic') ? (
              <div className="rounded-lg p-2.5 text-xs font-semibold mb-4 flex items-center gap-2" style={{ background: C.creamDeep, color: C.forest, border: `1px dashed ${C.line}` }}>
                <BrainCog size={14} /> {t('heuristicBadge')}
              </div>
            ) : (
              <div className="rounded-lg p-2.5 text-xs font-semibold mb-4 flex items-center gap-2" style={{ background: '#e9f5ec', color: C.green, border: `1px solid ${C.line}` }}>
                <CheckCircle2 size={14} /> {t('realModelBadge')} · {result.model_version}
              </div>
            )}

            <div className="flex flex-wrap gap-2 mb-4">
              <div className="text-xs px-3 py-1.5 rounded-lg" style={{ background: C.creamDeep }}><ThermometerSun size={12} className="inline mr-1" />{t('weatherTemp')} {result.temperature?.toFixed(1)}°C</div>
              <div className="text-xs px-3 py-1.5 rounded-lg" style={{ background: C.creamDeep }}><Droplets size={12} className="inline mr-1" />{t('weatherHumidity')} {result.humidity?.toFixed(0)}%</div>
              <div className="text-xs px-3 py-1.5 rounded-lg" style={{ background: C.creamDeep }}><CloudRain size={12} className="inline mr-1" />{t('weatherRain')} {result.rainfall?.toFixed(1)}mm</div>
            </div>

            <div className="grid sm:grid-cols-2 gap-3 mb-4">
              <div className="flex justify-between border-b py-2 text-sm" style={{ borderColor: C.line }}>
                <span style={{ color: 'rgba(20,35,26,0.55)' }}>{t('diagnosisLabel')}</span>
                <strong>{result.is_healthy ? t('healthy') : result.disease}</strong>
              </div>
              <div className="flex justify-between border-b py-2 text-sm" style={{ borderColor: C.line }}>
                <span style={{ color: 'rgba(20,35,26,0.55)' }}>{t('confidenceLabel')}</span>
                <strong>{result.confidence?.toFixed(0)}%</strong>
              </div>
              <div className="flex justify-between border-b py-2 text-sm" style={{ borderColor: C.line }}>
                <span style={{ color: 'rgba(20,35,26,0.55)' }}>{t('severityLabel')}</span>
                <Pill color={riskColor(result.severity)}>{t(`severity_${result.severity}`)}</Pill>
              </div>
              <div className="flex justify-between border-b py-2 text-sm" style={{ borderColor: C.line }}>
                <span style={{ color: 'rgba(20,35,26,0.55)' }}>{t('riskLabel')}</span>
                <Pill color={riskColor(result.risk_level)}>{t(`severity_${result.risk_level}`)} · {result.risk_score}/100</Pill>
              </div>
            </div>

            {/* officer status */}
            <div className="flex flex-wrap items-center gap-2 mb-4 text-xs">
              {result.officer_verified ? (
                <span className="flex items-center gap-1" style={{ color: C.green }}><ShieldCheck size={14} /> {t('verifiedNote')}</span>
              ) : result.low_confidence ? (
                <span className="flex items-center gap-1" style={{ color: C.amber }}><AlertTriangle size={14} /> {t('lowConfNote')}</span>
              ) : (
                <span style={{ color: 'rgba(20,35,26,0.55)' }}><Clock size={13} className="inline mr-1" />{t('pending')}</span>
              )}
              {openReferralFor(result.id) && (
                <Pill color={C.forest}>{t('referralStatus')}: {openReferralFor(result.id).status}</Pill>
              )}
            </div>

            {/* recommendations from the agent */}
            {!result.is_healthy && (result.recommendations || []).length > 0 && (
              <div className="mb-4">
                <p className="text-xs font-semibold mb-2" style={{ color: 'rgba(20,35,26,0.55)' }}>{t('actionsLabel')}</p>
                <ul className="space-y-1.5">
                  {result.recommendations.map((rec) => (
                    <li key={rec.id} className="flex gap-2 text-sm">
                      <CheckCircle2 size={16} color={C.green} className="flex-shrink-0 mt-0.5" />
                      <span>{rec.recommendation}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {!result.is_healthy && (
              <div className="flex items-center gap-2 mt-3 text-xs" style={{ color: 'rgba(20,35,26,0.55)' }}>
                <Clock size={14} /> {t('followupLabel')} {result.followup_days} {t('days')}
              </div>
            )}

            {(result.nearby_similar || 0) > 0 && !result.is_healthy && (
              <div className="flex items-center gap-2 mt-3 text-xs rounded-lg p-2.5" style={{ background: '#fff3dc', color: C.amber }}>
                <Bug size={14} className="flex-shrink-0" /> {result.nearby_similar} {t('communityNote')}
              </div>
            )}
          </div>
        )}

        {/* ---- Why this decision ---- */}
        {result && (
          <Reveal variant="up-sm"><WhyThisDecision report={result} t={t} /></Reveal>
        )}

        {/* ---- AI Agent Activity ---- */}
        {result && (
          <Reveal variant="up-sm" delay={80}><AgentActivity items={result.activity} t={t} /></Reveal>
        )}

        {/* ---- Treatment & safe use ---- */}
        {result && !result.is_healthy && TREATMENT_MAP[result.disease] && (
          <div className="ag-fade rounded-2xl p-6 mb-6" style={{ background: C.white, border: `1px solid ${C.line}` }}>
            <h3 className="ag-display text-xl mb-1 flex items-center gap-2" style={{ color: C.forest }}><FlaskConical size={20} color={C.moss} /> {t('treatmentTitle')}</h3>
            <div className="grid sm:grid-cols-2 gap-3 my-4">
              <div className="flex justify-between border-b py-2 text-sm" style={{ borderColor: C.line }}>
                <span style={{ color: 'rgba(20,35,26,0.55)' }}>{t('treatmentCategory')}</span>
                <strong className="text-right">{TREATMENT_MAP[result.disease].category}</strong>
              </div>
              <div className="flex justify-between border-b py-2 text-sm" style={{ borderColor: C.line }}>
                <span style={{ color: 'rgba(20,35,26,0.55)' }}>{t('treatmentPhi')}</span>
                <strong>{TREATMENT_MAP[result.disease].phi}</strong>
              </div>
            </div>
            <p className="text-sm mb-3"><span className="font-semibold">{t('treatmentTiming')}: </span>{TREATMENT_MAP[result.disease].timing}</p>
            <p className="text-sm mb-4"><span className="font-semibold">{t('treatmentNote')}: </span>{TREATMENT_MAP[result.disease].note}</p>
            <p className="text-xs font-semibold mb-2 flex items-center gap-1" style={{ color: 'rgba(20,35,26,0.55)' }}><ShieldCheck size={13} /> {t('safetyTitle')}</p>
            <ul className="space-y-1.5 mb-4">
              {GENERIC_SAFETY.map((s, i) => (
                <li key={i} className="flex gap-2 text-sm">
                  <CheckCircle2 size={15} color={C.green} className="flex-shrink-0 mt-0.5" />
                  <span>{s}</span>
                </li>
              ))}
            </ul>
            <div className="rounded-lg p-3 text-xs" style={{ background: C.creamDeep, color: 'rgba(20,35,26,0.65)' }}>
              {t('labelDisclaimer')}
            </div>
          </div>
        )}

        {/* ---- Referral request ---- */}
        {result && !result.is_healthy && (
          <div className="ag-fade rounded-2xl p-6 mb-6" style={{ background: C.forest }}>
            <h3 className="ag-display text-xl mb-1 flex items-center gap-2 text-white"><Stethoscope size={20} color={C.wheat} /> {t('referralTitle')}</h3>
            <p className="text-sm mb-4 text-white/70">{t('referralDesc')}</p>
            {referralSentFor === result.id || openReferralFor(result.id) ? (
              <div className="rounded-lg p-3 text-sm flex items-center gap-2" style={{ background: 'rgba(255,255,255,0.12)', color: C.wheat }}>
                <CheckCircle2 size={16} /> {t('referralSent')}
              </div>
            ) : (
              <div className="flex flex-col sm:flex-row gap-3">
                <select value={referralReason} onChange={(e) => setReferralReason(e.target.value)} className="flex-1 rounded-lg px-3 py-2 text-sm">
                  {REFERRAL_REASONS.map((r) => <option key={r} value={r}>{r}</option>)}
                </select>
                <button onClick={requestReferral} className="ag-body inline-flex items-center justify-center gap-2 rounded-full px-5 py-2.5 font-semibold text-sm" style={{ background: C.wheat, color: C.forestDark }}>
                  <FlaskConical size={15} /> {t('referralBtn')}
                </button>
              </div>
            )}
          </div>
        )}

        {/* ---- History ---- */}
        <div className="rounded-2xl p-6" style={{ background: C.white, border: `1px solid ${C.line}` }}>
          <h3 className="ag-display text-xl mb-4" style={{ color: C.forest }}>{t('historyTitle')}</h3>
          {history.length === 0 ? (
            <p className="text-sm" style={{ color: 'rgba(20,35,26,0.5)' }}>{t('historyEmpty')}</p>
          ) : (
            <div className="space-y-2">
              {history.map((h, i) => (
                <button key={h.id} onClick={() => { setResult(h); window.scrollTo({ top: 0, behavior: 'smooth' }) }}
                  className="ag-row-in group w-full flex items-center justify-between text-sm py-2 border-b text-left transition-transform duration-500 hover:translate-x-1"
                  style={{ borderColor: C.line, animationDelay: `${Math.min(i * 60, 700)}ms` }}>
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-md flex items-center justify-center transition-transform duration-500 group-hover:scale-110" style={{ background: C.creamDeep }}>
                      <Sprout size={16} color={C.moss} />
                    </div>
                    <div>
                      <div className="font-medium">{h.crop} · {h.is_healthy ? t('healthy') : h.disease}</div>
                      <div className="text-xs" style={{ color: 'rgba(20,35,26,0.45)' }}>
                        {new Date(h.created_at).toLocaleString()} · {h.farm_name || h.location}
                      </div>
                    </div>
                  </div>
                  <Pill color={riskColor(h.risk_level)}>{t(`severity_${h.risk_level}`)}</Pill>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
