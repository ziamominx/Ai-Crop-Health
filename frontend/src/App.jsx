import { useEffect, useState } from 'react'
import { C, FONTS } from './api/theme.js'
import { Sprout } from './api/icons.jsx'
import { LANG_OPTIONS } from './i18n/translations.js'
import { AuthProvider, useAuth } from './hooks/useAuth.jsx'
import { LanguageProvider, useLanguage } from './hooks/useLanguage.jsx'
import { AppErrorBoundary } from './components/AppErrorBoundary.jsx'
import { CursorAura, ScrollProgress } from './components/motion.jsx'
import { Landing } from './pages/Landing.jsx'
import { Login } from './pages/Login.jsx'
import { FarmerPage } from './pages/FarmerPage.jsx'
import { OfficerPage } from './pages/OfficerPage.jsx'
import { AdminPage } from './pages/AdminPage.jsx'

function Shell() {
  const { lang, setLang, langReady, t } = useLanguage()
  const { user, logout } = useAuth()
  const [screen, setScreen] = useState('lang') // lang | landing | login
  const [role, setRole] = useState('farmer')

  // A logged-in user lands straight in their workspace; logout returns to landing.
  useEffect(() => {
    if (user) setScreen(user.role === 'ADMIN' ? 'admin' : user.role === 'OFFICER' ? 'officer' : 'farmer')
    else if (langReady) setScreen('landing')
  }, [user, langReady])

  if (screen === 'lang' || !langReady) {
    return (
      <div className="ag-screen min-h-screen w-full flex items-center justify-center p-6" style={{ background: C.forest }}>
        <div className="ag-fade w-full max-w-md rounded-2xl p-8 text-center" style={{ background: C.white }}>
          <div className="mx-auto mb-4 w-14 h-14 rounded-full flex items-center justify-center" style={{ background: C.forest }}>
            <Sprout color={C.wheat} size={28} />
          </div>
          <h1 className="ag-display text-3xl mb-2" style={{ color: C.forest }}>Agricure</h1>
          <p className="ag-body text-sm mb-1" style={{ color: 'rgba(20,35,26,0.6)' }}>Choose your language</p>
          <p className="ag-body text-xs mb-6" style={{ color: 'rgba(20,35,26,0.45)' }}>अपनी भाषा चुनें · तुमची भाषा निवडा · ನಿಮ್ಮ ಭಾಷೆ ಆಯ್ಕೆಮಾಡಿ</p>
          <div className="grid grid-cols-2 gap-3">
            {LANG_OPTIONS.map((l) => (
              <button key={l.code}
                onClick={() => { setLang(l.code); setScreen('landing') }}
                className="ag-body rounded-xl py-4 px-3 text-left transition-transform hover:-translate-y-0.5"
                style={{ border: `1.5px solid ${C.line}`, background: C.cream }}>
                <div className="ag-display text-xl" style={{ color: C.forest }}>{l.native}</div>
                <div className="text-xs mt-0.5" style={{ color: 'rgba(20,35,26,0.5)' }}>{l.sub}</div>
              </button>
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (user && screen === 'farmer') return <FarmerPage onLogout={() => { logout(); setScreen('landing') }} />
  if (user && screen === 'officer') return <OfficerPage onLogout={() => { logout(); setScreen('landing') }} />
  if (user && screen === 'admin') return <AdminPage onLogout={() => { logout(); setScreen('landing') }} />

  if (screen === 'login') {
    return (
      <div className="ag-screen">
        <Login role={role}
          onRoleChange={(r) => setRole(r)}
          onBack={() => setScreen('landing')}
          onDone={() => { /* auth effect switches the screen */ }} />
      </div>
    )
  }

  return (
    <div className="ag-screen">
      <Landing onOpenLogin={(r) => { setRole(r); setScreen('login') }} />
    </div>
  )
}

export default function AgricureApp() {
  return (
    <div className="ag-root ag-body ag-grain min-h-screen w-full" data-lang="en" style={{ background: C.cream, color: C.ink }}>
      <style>{FONTS}</style>
      {/* fixed-position flourish: kept outside any animated wrapper so it is
          never clipped or re-parented */}
      <ScrollProgress />
      <CursorAura />
      <AppErrorBoundary>
        <LanguageProvider>
          <AuthProvider>
            <LangWrapper />
          </AuthProvider>
        </LanguageProvider>
      </AppErrorBoundary>
    </div>
  )
}

/* Keeps data-lang on the root so the Devanagari/Kannada font rules apply. */
function LangWrapper() {
  const { lang, t } = useLanguage()
  return (
    <>
      <LangRoot lang={lang} />
      {import.meta.env.VITE_STATIC_DEMO === 'true' && <StaticDemoBanner t={t} />}
    </>
  )
}

/* Shown only in the published GitHub Pages build, which has no backend.
   It says plainly what is real (bundled analyses produced by the project's own
   inference) and what needs the API (uploading a new photo). */
function StaticDemoBanner({ t }) {
  const [open, setOpen] = useState(true)
  if (!open) return null
  return (
    <div className="ag-static-banner" role="status">
      <span className="ag-static-dot" aria-hidden="true" />
      <span className="ag-static-text">
        <strong>{t('staticDemoTitle')}</strong> {t('staticDemoBody')}
      </span>
      <button type="button" onClick={() => setOpen(false)} aria-label={t('close')}>×</button>
    </div>
  )
}

function LangRoot({ lang }) {
  // set the attribute on the actual root div via effect
  useEffect(() => {
    document.querySelector('.ag-root')?.setAttribute('data-lang', lang || 'en')
  }, [lang])
  return <Shell />
}
