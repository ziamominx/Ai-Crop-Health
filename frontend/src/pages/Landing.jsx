import { useEffect, useState } from 'react'
import { C } from '../api/theme.js'
import {
  ArrowRight, BrainCog, Camera, ChevronRight, ClipboardList, Database, Landmark,
  Languages, Menu, Sprout, User, X,
} from '../api/icons.jsx'
import { Sparkles } from '../api/icons.jsx'
import { LANG_OPTIONS } from '../i18n/translations.js'
import { useLanguage } from '../hooks/useLanguage.jsx'
import {
  CountUp, GlowBlobs, MagneticButton, Marquee, MaskedLines, Parallax, Reveal, ScrollCue,
} from '../components/motion.jsx'

const AGENT_LOOP_MARQUEE = [
  'AI CROP HEALTH', 'EARLY WARNING', 'PERCEPTION', 'STATE / MEMORY', 'REASONING',
  'DECISION', 'ACTION', 'FEEDBACK', 'LEARNING', 'हिंदी', 'मराठी', 'ಕನ್ನಡ',
]

export function Landing({ onOpenLogin }) {
  const { lang, setLang, t } = useLanguage()
  const [menuOpen, setMenuOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const stats = [
    { icon: Sprout, value: 5, label: t('statCrops') },
    { icon: Languages, value: 4, label: t('statLanguages') },
    { icon: BrainCog, value: 7, label: t('statAgentStages') },
    { icon: Database, value: 13, label: t('statTables') },
  ]

  return (
    <div>
      <nav
        className="w-full flex items-center justify-between px-6 md:px-12 py-5 sticky top-0 z-50 transition-all duration-500"
        style={{
          background: scrolled ? 'rgba(19,41,32,0.92)' : C.forest,
          backdropFilter: scrolled ? 'blur(14px)' : 'none',
          boxShadow: scrolled ? '0 12px 40px -24px rgba(0,0,0,0.6)' : 'none',
        }}
      >
        <div className="flex items-center gap-2">
          <Sprout color={C.wheat} size={22} />
          <span className="ag-display text-xl text-white">{t('appName')}</span>
        </div>
        <div className="hidden md:flex items-center gap-3">
          <button onClick={() => setLang(null)} className="ag-underline text-white/70 hover:text-white text-sm flex items-center gap-1">
            <Languages size={15} /> {LANG_OPTIONS.find((l) => l.code === lang)?.native}
          </button>
          <button onClick={() => onOpenLogin('farmer')} className="ag-underline text-sm text-white/85 hover:text-white px-4 py-2">{t('nav_farmer')}</button>
          <button onClick={() => onOpenLogin('official')} className="ag-underline text-sm text-white/85 hover:text-white px-4 py-2">{t('nav_official')}</button>
          <MagneticButton
            onClick={() => onOpenLogin('admin')}
            className="text-sm rounded-full px-4 py-2 font-semibold"
            style={{ background: C.wheat, color: C.forestDark }}
          >
            {t('nav_admin')}
          </MagneticButton>
        </div>
        <button className="md:hidden text-white" onClick={() => setMenuOpen((v) => !v)} aria-label="Menu">
          {menuOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </nav>

      {menuOpen && (
        <div className="ag-panel md:hidden flex flex-col gap-2 px-6 py-4 sticky top-[68px] z-40" style={{ background: C.forestDark }}>
          <button onClick={() => setLang(null)} className="text-white/85 text-left py-2 flex items-center gap-2">
            <Languages size={16} /> {t('appName')} · {LANG_OPTIONS.find((l) => l.code === lang)?.native}
          </button>
          <button onClick={() => onOpenLogin('farmer')} className="text-white/85 text-left py-2">{t('nav_farmer')}</button>
          <button onClick={() => onOpenLogin('official')} className="text-white/85 text-left py-2">{t('nav_official')}</button>
          <button onClick={() => onOpenLogin('admin')} className="text-left py-2 font-semibold rounded-lg px-3" style={{ background: C.wheat, color: C.forestDark }}>{t('nav_admin')}</button>
        </div>
      )}

      {/* ---------------- Hero ---------------- */}
      <section
        className="ag-rows relative w-full px-6 md:px-12 pt-16 pb-20 md:pt-24 md:pb-28 overflow-hidden"
        style={{ background: `linear-gradient(180deg, ${C.forest}, ${C.forestDark})` }}
      >
        <GlowBlobs
          blobs={[
            { size: 420, top: '-12%', left: '-6%', color: 'rgba(216,165,61,0.42)' },
            { size: 520, top: '18%', right: '-10%', color: 'rgba(79,121,66,0.5)', slow: true },
            { size: 340, bottom: '-24%', left: '38%', color: 'rgba(127,168,105,0.32)', slow: true },
          ]}
        />

        <Parallax strength={26} className="relative max-w-3xl mx-auto text-center">
          <span
            className="inline-block mb-5 text-xs tracking-widest uppercase ag-reveal is-in"
            style={{ color: C.wheat, animation: 'agFadeUp .9s cubic-bezier(.22,1,.36,1) both' }}
          >
            {t('heroEyebrow')}
          </span>

          <h1 className="ag-display text-white leading-tight text-4xl md:text-6xl">
            <MaskedLines lines={[t('heroLine1')]} />
            <MaskedLines
              lines={[t('heroLine2')]}
              delay={220}
              lineClassName="italic"
              className="block"
            />
          </h1>

          <p
            className="ag-body mt-6 text-white/70 max-w-xl mx-auto text-sm md:text-base ag-reveal is-in"
            style={{ animation: 'agFadeUp 1s cubic-bezier(.22,1,.36,1) .4s both' }}
          >
            {t('heroSub')}
          </p>

          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3 ag-stagger">
            <MagneticButton
              onClick={() => onOpenLogin('farmer')}
              className="ag-body inline-flex items-center gap-2 rounded-full px-7 py-3 font-semibold"
              style={{ background: C.wheat, color: C.forestDark }}
            >
              {t('heroCtaFarmer')} <ArrowRight size={16} />
            </MagneticButton>
            <MagneticButton
              onClick={() => onOpenLogin('official')}
              className="ag-body inline-flex items-center gap-2 rounded-full px-7 py-3 font-semibold border border-white/40 text-white hover:bg-white/10"
              style={{ background: 'transparent' }}
            >
              <Landmark size={16} /> {t('heroCtaOfficial')}
            </MagneticButton>
          </div>

          <ScrollCue label={t('scrollCue')} />
        </Parallax>
      </section>

      {/* ---------------- Marquee band ---------------- */}
      <Marquee
        items={AGENT_LOOP_MARQUEE}
        className="ag-display text-2xl md:text-4xl py-6"
        style={{ background: C.creamDeep, color: C.forest, borderBottom: `1px solid ${C.line}` }}
        duration={38}
      />

      {/* ---------------- Stats strip ---------------- */}
      <section className="px-6 md:px-12 py-14 max-w-5xl mx-auto">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {stats.map((s, i) => (
            <Reveal key={s.label} variant="scale" delay={i * 90}>
              <div
                className="ag-lift rounded-2xl px-4 py-6 text-center h-full"
                style={{ background: C.white, border: `1px solid ${C.line}` }}
              >
                <s.icon size={20} color={C.moss} className="mx-auto mb-3" />
                <div className="ag-display text-4xl" style={{ color: C.forest }}>
                  <CountUp value={s.value} />
                </div>
                <div className="ag-body text-xs mt-1 tracking-wide" style={{ color: 'rgba(20,35,26,0.55)' }}>
                  {s.label}
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ---------------- How it works ---------------- */}
      <section className="px-6 md:px-12 py-16 max-w-5xl mx-auto">
        <Reveal variant="left">
          <span className="text-xs tracking-widest uppercase" style={{ color: C.wheatDeep }}>{t('howEyebrow')}</span>
        </Reveal>
        <div className="grid md:grid-cols-3 gap-6 mt-6">
          {[
            { icon: Camera, t: t('how1t'), d: t('how1d') },
            { icon: Sparkles, t: t('how2t'), d: t('how2d') },
            { icon: ClipboardList, t: t('how3t'), d: t('how3d') },
          ].map((s, i) => (
            <Reveal key={i} delay={i * 120} variant="up">
              <div
                className="ag-lift group rounded-xl p-6 h-full"
                style={{ background: C.white, border: `1px solid ${C.line}` }}
              >
                <span className="inline-flex transition-transform duration-500 group-hover:-translate-y-1 group-hover:scale-110">
                  <s.icon size={22} color={C.moss} />
                </span>
                <h3 className="ag-display text-xl mt-4" style={{ color: C.forest }}>{s.t}</h3>
                <p className="ag-body text-sm mt-2" style={{ color: 'rgba(20,35,26,0.6)' }}>{s.d}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ---------------- Two ways in ---------------- */}
      <section className="px-6 md:px-12 py-16 max-w-5xl mx-auto">
        <Reveal variant="left">
          <span className="text-xs tracking-widest uppercase" style={{ color: C.wheatDeep }}>{t('panelsEyebrow')}</span>
        </Reveal>
        <div className="grid md:grid-cols-2 gap-6 mt-6">
          <Reveal variant="left" delay={60}>
            <div className="ag-lift relative overflow-hidden rounded-2xl p-7 h-full" style={{ background: C.forest }}>
              <GlowBlobs blobs={[{ size: 260, bottom: '-40%', right: '-15%', color: 'rgba(216,165,61,0.35)' }]} />
              <div className="relative">
                <User color={C.wheat} size={26} />
                <h3 className="ag-display text-2xl text-white mt-4">{t('panelFarmerT')}</h3>
                <p className="ag-body text-white/70 text-sm mt-2 mb-6">{t('panelFarmerD')}</p>
                <MagneticButton
                  onClick={() => onOpenLogin('farmer')}
                  className="ag-body inline-flex items-center gap-2 rounded-full px-5 py-2.5 font-semibold"
                  style={{ background: C.wheat, color: C.forestDark }}
                >
                  {t('continueLabel')} <ChevronRight size={16} />
                </MagneticButton>
              </div>
            </div>
          </Reveal>

          <Reveal variant="right" delay={140}>
            <div className="ag-lift relative overflow-hidden rounded-2xl p-7 h-full" style={{ background: C.creamDeep, border: `1px solid ${C.line}` }}>
              <GlowBlobs blobs={[{ size: 240, top: '-30%', right: '-10%', color: 'rgba(79,121,66,0.28)' }]} />
              <div className="relative">
                <Landmark color={C.forest} size={26} />
                <h3 className="ag-display text-2xl mt-4" style={{ color: C.forest }}>{t('panelOfficialT')}</h3>
                <p className="ag-body text-sm mt-2 mb-6" style={{ color: 'rgba(20,35,26,0.65)' }}>{t('panelOfficialD')}</p>
                <MagneticButton
                  onClick={() => onOpenLogin('official')}
                  className="ag-body inline-flex items-center gap-2 rounded-full px-5 py-2.5 font-semibold"
                  style={{ background: C.forest, color: 'white' }}
                >
                  {t('continueLabel')} <ChevronRight size={16} />
                </MagneticButton>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      <Reveal variant="blur">
        <footer className="text-center py-8 text-xs" style={{ color: 'rgba(20,35,26,0.4)' }}>
          {t('appName')} · AI Crop Health & Early Warning Agent
        </footer>
      </Reveal>
    </div>
  )
}
