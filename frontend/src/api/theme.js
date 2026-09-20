/* Design tokens — extracted verbatim from the original Agricure prototype. */
export const C = {
  ink: '#14231a',
  forest: '#1f3d2b',
  forestDark: '#132920',
  moss: '#4f7942',
  mossLight: '#7fa869',
  wheat: '#d8a53d',
  wheatDeep: '#b9852a',
  cream: '#faf6ec',
  creamDeep: '#f1ead8',
  soil: '#6b4226',
  white: '#ffffff',
  red: '#b8402a',
  amber: '#a56c17',
  green: '#3d7a4c',
  line: 'rgba(20,35,26,0.12)',
}

export const FONTS = `
@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Inter:wght@300;400;500;600;700&family=Noto+Sans+Devanagari:wght@400;600;700&family=Noto+Sans+Kannada:wght@400;600;700&display=swap');
.ag-root{ --font-display: 'Instrument Serif', serif; --font-body: 'Inter', sans-serif; }
.ag-root[data-lang="hi"], .ag-root[data-lang="mr"]{ --font-display: 'Noto Sans Devanagari', sans-serif; --font-body: 'Noto Sans Devanagari', sans-serif; }
.ag-root[data-lang="kn"]{ --font-display: 'Noto Sans Kannada', sans-serif; --font-body: 'Noto Sans Kannada', sans-serif; }
.ag-display{ font-family: var(--font-display); }
.ag-body{ font-family: var(--font-body); }
.ag-fade{ animation: agFadeIn .5s ease both; }
@keyframes agFadeIn{ from{opacity:0; transform:translateY(10px);} to{opacity:1; transform:translateY(0);} }
.ag-rows{
  background-image: repeating-linear-gradient(115deg, rgba(255,255,255,0.05) 0px, rgba(255,255,255,0.05) 2px, transparent 2px, transparent 26px);
}
@media (prefers-reduced-motion: reduce){ .ag-fade{ animation:none; } }
`

/* Demo geospatial coordinates (approximate, visual purposes only) */
export const LOCATION_COORDS = {
  Nashik: { x: 42, y: 28, lat: 19.9975, lon: 73.7898 },
  Pune: { x: 46, y: 52, lat: 18.5204, lon: 73.8567 },
  Ahmednagar: { x: 55, y: 44, lat: 19.0948, lon: 74.748 },
  Nagpur: { x: 82, y: 30, lat: 21.1458, lon: 79.0882 },
  Kolhapur: { x: 34, y: 78, lat: 16.705, lon: 74.2433 },
}

export function riskColor(risk) {
  if (risk === 'High') return C.red
  if (risk === 'Moderate') return C.amber
  return C.green
}
