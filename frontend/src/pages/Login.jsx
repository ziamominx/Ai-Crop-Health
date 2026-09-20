import { useEffect, useState } from 'react'
import { C } from '../api/theme.js'
import { Pill } from '../components/ui.jsx'
import { useAuth } from '../hooks/useAuth.jsx'
import { useLanguage } from '../hooks/useLanguage.jsx'
import { api } from '../api/client.js'

export function Login({ role, onBack, onDone, onRoleChange }) {
  const setRoleSwap = onRoleChange || (() => {})
  const { t } = useLanguage()
  const { login, register } = useAuth()
  const [mode, setMode] = useState('login')
  const [form, setForm] = useState({ name: '', email: '', password: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [demoInfo, setDemoInfo] = useState(null)

  useEffect(() => {
    api.mode().then(setDemoInfo).catch(() => setDemoInfo(null))
  }, [])

  const roleKey = role // 'farmer' | 'official' | 'admin'
  const demoEmail = demoInfo
    ? (roleKey === 'farmer' ? demoInfo.demo_farmer_email
      : roleKey === 'admin' ? demoInfo.demo_admin_email
      : demoInfo.demo_officer_email)
    : null
  const demoPass = roleKey === 'farmer' ? 'demo1234' : roleKey === 'admin' ? 'admin1234' : 'officer1234'

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      if (mode === 'login') {
        await login(form.email, form.password)
      } else {
        await register({
          name: form.name, email: form.email, password: form.password,
          role: roleKey === 'farmer' ? 'FARMER' : 'OFFICER', language: 'en',
        })
      }
      onDone()
    } catch (err) {
      setError(err.message || t('loginErr'))
    } finally {
      setBusy(false)
    }
  }

  const autofill = () => {
    if (!demoEmail) return
    setForm({ name: '', email: demoEmail, password: demoPass })
  }

  return (
    <div className="min-h-screen w-full flex items-center justify-center p-6" style={{ background: C.forest }}>
      <div className="ag-fade w-full max-w-sm rounded-2xl overflow-hidden" style={{ background: C.white }}>
        <div className="px-6 py-5 flex items-center justify-between" style={{ background: C.forest }}>
          <span className="ag-display text-xl text-white">{t('appName')}</span>
          <button onClick={onBack} className="text-white/80 text-sm">{t('backHome')}</button>
        </div>
        <div className="p-6">
          <Pill color={roleKey === 'farmer' ? C.moss : roleKey === 'admin' ? C.forestDark : C.forest}>
            {roleKey === 'farmer' ? t('loginFarmerTag') : roleKey === 'admin' ? t('loginAdminTag') : t('loginOfficialTag')}
          </Pill>
          <h2 className="ag-display text-2xl mt-3" style={{ color: C.forest }}>
            {mode === 'login' ? t('loginTitle') : t('registerTitle')}
          </h2>
          <p className="ag-body text-sm mt-1 mb-5" style={{ color: 'rgba(20,35,26,0.6)' }}>
            {roleKey === 'farmer' ? t('loginSubFarmer') : roleKey === 'admin' ? t('loginSubAdmin') : t('loginSubOfficial')}
          </p>

          {mode === 'register' && roleKey === 'admin' && (
            <p className="text-xs mb-4" style={{ color: C.amber }}>{t('adminRegisterNote')}</p>
          )}

          {demoInfo?.demo_mode && demoEmail && (
            <div className="flex items-center justify-between gap-2 rounded-lg px-3 py-2 mb-4 text-xs" style={{ background: '#fff7d6', border: '1px dashed #cbb148' }}>
              <span>
                {t('demoLabel')} <strong>{demoEmail}</strong>
              </span>
              <button type="button" onClick={autofill} className="underline font-semibold" style={{ color: C.forest }}>{t('autofill')}</button>
            </div>
          )}

          {error && <p className="text-xs font-semibold mb-3" style={{ color: C.red }}>{error}</p>}

          <form onSubmit={submit} className="ag-body space-y-3">
            {mode === 'register' && (
              <div>
                <label className="text-xs font-semibold block mb-1">{t('nameLabel')}</label>
                <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full rounded-lg px-3 py-2 text-sm" style={{ border: `1px solid ${C.line}` }} />
              </div>
            )}
            <div>
              <label className="text-xs font-semibold block mb-1">{t('emailLabel')}</label>
              <input type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="w-full rounded-lg px-3 py-2 text-sm" style={{ border: `1px solid ${C.line}` }} placeholder="you@example.com" />
            </div>
            <div>
              <label className="text-xs font-semibold block mb-1">{t('passwordLabel')}</label>
              <input type="password" required minLength={8} value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                className="w-full rounded-lg px-3 py-2 text-sm" style={{ border: `1px solid ${C.line}` }} placeholder="********" />
            </div>
            <button type="submit" disabled={busy || (mode === 'register' && roleKey === 'admin')}
              className="w-full rounded-lg py-2.5 font-semibold text-sm mt-2"
              style={{ background: C.forest, color: 'white', opacity: busy ? 0.7 : 1 }}>
              {busy ? '…' : (mode === 'login'
                ? (roleKey === 'farmer' ? t('submitFarmer') : roleKey === 'admin' ? t('submitAdmin') : t('submitOfficial'))
                : t('registerTitle'))}
            </button>
          </form>

          {roleKey !== 'admin' && (
            <button onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError('') }}
              className="w-full text-center text-xs mt-4 underline" style={{ color: 'rgba(20,35,26,0.6)' }}>
              {mode === 'login' ? t('registerLink') : t('loginLink')}
            </button>
          )}

          {/* quick role switcher */}
          <div className="flex items-center justify-center gap-3 mt-4 text-xs">
            {['farmer', 'official', 'admin'].map((r) => (
              <button key={r}
                onClick={() => { setRoleSwap(r); setError(''); setMode('login') }}
                className="underline"
                style={{ color: r === roleKey ? C.forest : 'rgba(20,35,26,0.45)', fontWeight: r === roleKey ? 700 : 400 }}>
                {r === 'farmer' ? t('panelFarmerT') : r === 'official' ? t('panelOfficialT') : t('nav_admin')}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
