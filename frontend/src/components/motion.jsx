import { useEffect, useRef, useState } from 'react'
import { C } from '../api/theme.js'
import { useMagnetic, useParallax, useReveal, useScrollProgress } from '../hooks/useReveal.js'

const reduced = () =>
  typeof window !== 'undefined' &&
  window.matchMedia &&
  window.matchMedia('(prefers-reduced-motion: reduce)').matches

/* ------------------------------------------------------------------
   Reveal — fade/blur/rise once the element scrolls into view
   ------------------------------------------------------------------ */
export function Reveal({
  children, variant = 'up', delay = 0, as: Tag = 'div', className = '', style, ...rest
}) {
  const ref = useReveal()
  return (
    <Tag
      ref={ref}
      className={`ag-reveal ${className}`}
      data-variant={variant}
      style={{ transitionDelay: `${delay}ms`, ...style }}
      {...rest}
    >
      {children}
    </Tag>
  )
}

/* ------------------------------------------------------------------
   MaskedLines — display type that rises line-by-line behind a mask
   ------------------------------------------------------------------ */
export function MaskedLines({ lines = [], className = '', lineClassName = '', delay = 0, stagger = 110 }) {
  return (
    <span className={className}>
      {lines.map((line, i) => (
        <span key={i} className={`ag-line ${lineClassName}`}>
          <span style={{ animationDelay: `${delay + i * stagger}ms` }}>{line}</span>
        </span>
      ))}
    </span>
  )
}

/* ------------------------------------------------------------------
   Marquee — endless scrolling band (pauses on hover)
   ------------------------------------------------------------------ */
export function Marquee({ items = [], duration = 34, className = '', style, itemClassName = '' }) {
  const row = [...items, ...items] // two copies give a seamless -50% loop
  return (
    <div className={`ag-marquee ${className}`} style={style} aria-hidden="true">
      <div className="ag-marquee__track" style={{ animationDuration: `${duration}s` }}>
        {row.map((item, i) => (
          <span key={i} className={`ag-marquee__item ${itemClassName}`}>
            {item}
            <span className="ag-marquee__dot" />
          </span>
        ))}
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------
   CountUp — animated number, triggered when scrolled into view
   ------------------------------------------------------------------ */
export function CountUp({ value = 0, duration = 1300, suffix = '', prefix = '', className = '', style }) {
  const ref = useRef(null)
  const [shown, setShown] = useState(0)
  const target = Number(value) || 0

  useEffect(() => {
    const el = ref.current
    if (!el) return
    if (reduced() || typeof IntersectionObserver === 'undefined') {
      setShown(target)
      return
    }
    let raf = 0
    const io = new IntersectionObserver(
      (entries) => {
        if (!entries[0].isIntersecting) return
        io.disconnect()
        const start = performance.now()
        const tick = (now) => {
          const p = Math.min(1, (now - start) / duration)
          const eased = 1 - Math.pow(1 - p, 3)
          setShown(target * eased)
          if (p < 1) raf = requestAnimationFrame(tick)
        }
        raf = requestAnimationFrame(tick)
      },
      { threshold: 0.35 },
    )
    io.observe(el)
    return () => {
      io.disconnect()
      cancelAnimationFrame(raf)
    }
  }, [target, duration])

  const rounded = Number.isInteger(target) ? Math.round(shown) : shown.toFixed(1)
  return (
    <span ref={ref} className={className} style={style}>
      {prefix}{rounded}{suffix}
    </span>
  )
}

/* ------------------------------------------------------------------
   ScrollProgress — hairline gradient bar across the top
   ------------------------------------------------------------------ */
export function ScrollProgress() {
  const progress = useScrollProgress()
  return <div className="ag-progress" style={{ transform: `scaleX(${progress})` }} />
}

/* ------------------------------------------------------------------
   CursorAura — pointer-following glow + dot that swells over controls.
   The native cursor stays visible (safer on forms); this only adds light.
   ------------------------------------------------------------------ */
export function CursorAura() {
  const auraRef = useRef(null)
  const dotRef = useRef(null)

  useEffect(() => {
    const fine = window.matchMedia('(hover: hover) and (pointer: fine)').matches
    if (!fine || reduced()) return
    const aura = auraRef.current
    const dot = dotRef.current
    if (!aura || !dot) return

    let mx = window.innerWidth / 2
    let my = window.innerHeight / 2
    let ax = mx
    let ay = my
    let raf = 0
    let visible = false

    const onMove = (e) => {
      mx = e.clientX
      my = e.clientY
      if (!visible) {
        visible = true
        aura.classList.add('is-active')
      }
      dot.style.transform = `translate3d(${mx}px, ${my}px, 0) translate3d(-50%, -50%, 0)`
    }

    const onOver = (e) => {
      const hot = e.target?.closest?.(
        'a, button, [role="button"], input, select, textarea, .ag-lift, .ag-zoom, .ag-magnetic',
      )
      aura.classList.toggle('is-hot', Boolean(hot))
      dot.classList.toggle('is-hot', Boolean(hot))
    }

    const onLeave = () => {
      visible = false
      aura.classList.remove('is-active')
    }

    const loop = () => {
      ax += (mx - ax) * 0.12
      ay += (my - ay) * 0.12
      aura.style.transform = `translate3d(${ax.toFixed(2)}px, ${ay.toFixed(2)}px, 0) translate3d(-50%, -50%, 0)`
      raf = requestAnimationFrame(loop)
    }

    window.addEventListener('mousemove', onMove, { passive: true })
    window.addEventListener('mouseover', onOver, { passive: true })
    document.addEventListener('mouseleave', onLeave)
    raf = requestAnimationFrame(loop)

    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseover', onOver)
      document.removeEventListener('mouseleave', onLeave)
      cancelAnimationFrame(raf)
    }
  }, [])

  return (
    <>
      <div ref={auraRef} className="ag-aura" />
      <div ref={dotRef} className="ag-aura-dot" />
    </>
  )
}

/* ------------------------------------------------------------------
   GlowBlobs — soft drifting colour fields behind a section
   ------------------------------------------------------------------ */
export function GlowBlobs({ blobs = [] }) {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none" aria-hidden="true">
      {blobs.map((b, i) => (
        <span
          key={i}
          className={`ag-blob ${b.slow ? 'ag-blob--slow' : ''}`}
          style={{
            width: b.size, height: b.size, top: b.top, left: b.left, right: b.right, bottom: b.bottom,
            background: b.color, animationDelay: `${i * 1.7}s`,
          }}
        />
      ))}
    </div>
  )
}

/* ------------------------------------------------------------------
   ScrollCue — animated "scroll" hairline for the hero
   ------------------------------------------------------------------ */
export function ScrollCue({ label }) {
  return (
    <div className="ag-cue mt-12 text-white/70">
      <span />
      <span className="ag-body text-[10px] tracking-[0.25em] uppercase" style={{ }}>{label}</span>
    </div>
  )
}

/* ------------------------------------------------------------------
   MagneticButton — button that leans toward the cursor
   ------------------------------------------------------------------ */
export function MagneticButton({ children, className = '', strength = 7, style, ...rest }) {
  const ref = useMagnetic(strength)
  return (
    <button
      ref={ref}
      className={`ag-magnetic ag-sheen ${className}`}
      style={style}
      {...rest}
    >
      {children}
    </button>
  )
}

/* ------------------------------------------------------------------
   Parallax — wrapper that drifts on scroll
   ------------------------------------------------------------------ */
export function Parallax({ children, strength = 40, className = '' }) {
  const ref = useParallax(strength)
  return (
    <div ref={ref} className={className}>
      {children}
    </div>
  )
}

/* ------------------------------------------------------------------
   AnalysisProgress — the agent loop ticking while a report is analysed
   ------------------------------------------------------------------ */
export function AnalysisProgress({ stages = [], active = true, totalMs = 1200 }) {
  // Self-tuning: every stage completes inside `totalMs`, so the loop always
  // animates steadily whatever the backend latency happens to be. The panel is
  // replaced by the result as soon as the pipeline finishes.
  const [done, setDone] = useState(0)
  const step = Math.max(90, Math.round(totalMs / Math.max(1, stages.length)))

  useEffect(() => {
    if (!active) return
    if (reduced()) {
      setDone(stages.length)
      return
    }
    setDone(0)
    const id = setInterval(() => {
      setDone((n) => (n >= stages.length ? n : n + 1))
    }, step)
    return () => clearInterval(id)
  }, [active, stages.length, step])

  return (
    <div className="rounded-xl p-4" style={{ background: C.creamDeep, border: `1px solid ${C.line}` }}>
      <div className="space-y-2.5">
        {stages.map((stage, i) => (
          <div key={stage} className={`ag-step ${i < done ? 'is-done' : ''}`}>
            <div className="flex items-center justify-between text-xs mb-1">
              <span style={{ color: i < done ? C.forest : 'rgba(20,35,26,0.45)' }}>{stage}</span>
              {i < done && <span style={{ color: C.green }}>✓</span>}
            </div>
            <div className="ag-step__bar"><i /></div>
          </div>
        ))}
      </div>
    </div>
  )
}
