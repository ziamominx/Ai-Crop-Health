import { C } from '../api/theme.js'
import { AlertTriangle, RefreshCw } from '../api/icons.jsx'
import { CountUp, Reveal } from './motion.jsx'

export function Pill({ children, color }) {
  return (
    <span
      className="ag-body inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-semibold transition-transform duration-400 hover:scale-105"
      style={{ background: `${color}1a`, color, border: `1px solid ${color}55` }}
    >
      {children}
    </span>
  )
}

/* KPI card — count-up number + hover lift (used across officer/admin dashboards) */
export function StatCard({ label, value, color, delay = 0 }) {
  const numeric = typeof value === 'number'
  return (
    <Reveal variant="scale" delay={delay}>
      <div className="ag-lift rounded-xl p-4 text-center h-full" style={{ background: C.white, border: `1px solid ${C.line}` }}>
        <div className="ag-display text-3xl font-semibold" style={{ color: color || C.ink }}>
          {numeric ? <CountUp value={value} /> : value}
        </div>
        <div className="ag-body text-xs mt-1 tracking-wide" style={{ color: 'rgba(20,35,26,0.55)' }}>{label}</div>
      </div>
    </Reveal>
  )
}

/* API error state with retry — never silently fail backend operations. */
export function ErrorBox({ message, onRetry, retryLabel = 'Retry' }) {
  if (!message) return null
  return (
    <div className="rounded-lg p-3 text-sm flex items-center justify-between gap-3" style={{ background: '#fbeae6', color: C.red, border: '1px solid #e4b8ae' }}>
      <span className="flex items-center gap-2"><AlertTriangle size={15} className="flex-shrink-0" /> {message}</span>
      {onRetry && (
        <button onClick={onRetry} className="text-xs font-semibold underline flex items-center gap-1 flex-shrink-0" style={{ color: C.red }}>
          <RefreshCw size={12} /> {retryLabel}
        </button>
      )}
    </div>
  )
}

export function LoadingBox({ children }) {
  return (
    <div className="rounded-xl p-5 text-sm ag-body" style={{ background: C.white, border: `1px solid ${C.line}`, color: 'rgba(20,35,26,0.55)' }}>
      <RefreshCw size={14} className="inline animate-spin mr-2" />{children}
      <div className="ag-shimmer mt-3 h-2 rounded-full" />
    </div>
  )
}
