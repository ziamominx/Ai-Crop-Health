import { C } from '../api/theme.js'
import { Activity } from '../api/icons.jsx'

const STAGE_COLORS = {
  PERCEPTION: C.moss,
  MEMORY: C.soil,
  REASONING: C.wheatDeep,
  DECISION: C.red,
  ACTION: C.green,
  FEEDBACK: C.forest,
  LEARNING: '#5b5ea6',
}

/* "AI Agent Activity" — visible PERCEPTION→LEARNING trace (viva evidence). */
export function AgentActivity({ items, t }) {
  return (
    <div className="rounded-2xl p-5 mb-6" style={{ background: C.forestDark }}>
      <p className="ag-display text-lg mb-1 flex items-center gap-2 text-white">
        <Activity size={18} color={C.wheat} /> {t('agentActivityTitle')}
      </p>
      <p className="text-xs mb-3" style={{ color: 'rgba(255,255,255,0.55)' }}>
        PERCEPTION → STATE/MEMORY → REASONING → DECISION → ACTION → FEEDBACK → LEARNING
      </p>
      {!items || items.length === 0 ? (
        <p className="text-xs" style={{ color: 'rgba(255,255,255,0.45)' }}>{t('agentActivityEmpty')}</p>
      ) : (
        <ol className="space-y-1.5">
          {items.map((a, i) => (
            <li
              key={a.id}
              className="ag-row-in flex items-start gap-2 text-xs rounded px-1 -mx-1 transition-colors duration-300 hover:bg-white/5"
              style={{ animationDelay: `${Math.min(i * 70, 900)}ms` }}
            >
              <span
                className="rounded px-1.5 py-0.5 font-bold flex-shrink-0"
                style={{ background: `${STAGE_COLORS[a.stage] || C.moss}33`, color: STAGE_COLORS[a.stage] || C.moss }}
              >
                {t(`stage_${a.stage}`) || a.stage}
              </span>
              <span style={{ color: 'rgba(255,255,255,0.85)' }}>{a.message}</span>
              <span className="ml-auto flex-shrink-0" style={{ color: 'rgba(255,255,255,0.4)' }}>
                {new Date(a.created_at).toLocaleTimeString()}
              </span>
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}
