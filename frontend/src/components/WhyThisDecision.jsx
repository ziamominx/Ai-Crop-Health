import { C } from '../api/theme.js'
import { Pill } from './ui.jsx'
import { BrainCog, CheckCircle2 } from '../api/icons.jsx'

/* "Why did Agricure make this decision?" — generated from actual stored
   inputs (agent decision + risk factors + environmental values), not hardcoded. */
export function WhyThisDecision({ report, t }) {
  const d = report.agent_decision
  if (!d) return null
  const factors = Array.isArray(d.factors) ? d.factors : []

  const envRows = [
    { label: t('weatherTemp'), value: report.temperature != null ? `${report.temperature.toFixed(1)}°C` : '—' },
    { label: t('weatherHumidity'), value: report.humidity != null ? `${report.humidity.toFixed(0)}%` : '—' },
    { label: t('weatherRain'), value: report.rainfall != null ? `${report.rainfall.toFixed(1)} mm` : '—' },
    { label: t('soilMoistureLabel'), value: report.soil_moisture != null ? `${report.soil_moisture.toFixed(0)}%` : '—' },
    { label: t('leafWetnessLabel'), value: report.leaf_wetness != null ? `${report.leaf_wetness.toFixed(0)} h` : '—' },
    { label: t('trapCountLabel'), value: report.pest_count != null ? `${report.pest_count}` : '—' },
  ]

  return (
    <div className="rounded-2xl p-5 mb-6" style={{ background: C.creamDeep, border: `1px solid ${C.line}` }}>
      <h4 className="ag-display text-lg mb-1 flex items-center gap-2" style={{ color: C.forest }}>
        <BrainCog size={18} color={C.moss} /> {t('whyTitle')}
      </h4>
      <p className="text-xs mb-4" style={{ color: 'rgba(20,35,26,0.5)' }}>{t('whyNotePrototype')}</p>

      {/* risk contributors — straight from the risk engine output */}
      <p className="text-xs font-semibold mb-2" style={{ color: 'rgba(20,35,26,0.55)' }}>{t('whyRiskFactors')}</p>
      <ul className="space-y-1 mb-4">
        {factors.map((f, i) => (
          <li key={i} className="flex gap-2 text-sm">
            <CheckCircle2 size={15} color={C.green} className="flex-shrink-0 mt-0.5" />
            <span>{f}</span>
          </li>
        ))}
      </ul>

      {/* environmental values from the report row */}
      <p className="text-xs font-semibold mb-2" style={{ color: 'rgba(20,35,26,0.55)' }}>{t('whyEnvironmental')}</p>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mb-4">
        {envRows.map((row) => (
          <div key={row.label} className="rounded-lg px-3 py-2" style={{ background: C.white, border: `1px solid ${C.line}` }}>
            <div className="text-xs" style={{ color: 'rgba(20,35,26,0.5)' }}>{row.label}</div>
            <div className="text-sm font-semibold">{row.value}</div>
          </div>
        ))}
      </div>

      {/* nearby reports + decision */}
      <div className="flex flex-wrap items-center gap-2 mb-3">
        <span className="text-sm">{t('whyNearby')}:</span>
        <Pill color={C.amber}>{report.nearby_similar}</Pill>
        <span className="text-sm ml-2">{t('whyRiskScore')}:</span>
        <Pill color={d.spread_risk === 'High' ? C.red : d.spread_risk === 'Moderate' ? C.amber : C.green}>
          {d.spread_risk_score}/100
        </Pill>
        <span className="text-sm ml-2">{t('whyPriority')}:</span>
        <Pill color={C.forest}>{d.priority}</Pill>
      </div>

      <div className="rounded-lg p-3 text-sm" style={{ background: C.white, border: `1px solid ${C.line}` }}>
        <p className="text-xs font-semibold mb-1" style={{ color: 'rgba(20,35,26,0.55)' }}>{t('whyAgentDecision')}</p>
        <p className="font-semibold mb-1" style={{ color: C.forest }}>{d.decision}</p>
        <p className="text-sm" style={{ color: 'rgba(20,35,26,0.75)' }}>{d.reason}</p>
        <p className="text-sm mt-2"><span className="font-semibold">{t('actionsLabel')}: </span>{d.recommended_action}</p>
        <div className="flex flex-wrap gap-2 mt-2">
          {d.officer_verification_needed && <Pill color={C.amber}>{t('whyOfficerReviewNeeded')}</Pill>}
          {d.lab_referral_recommended && <Pill color={C.amber}>{t('whyLabRecommended')}</Pill>}
          {d.regional_alert && <Pill color={C.red}>{t('whyRegionalAlert')}</Pill>}
        </div>
      </div>
    </div>
  )
}
