/* Icon set — extracted verbatim from the original Agricure prototype. */
import React from 'react'

function makeIcon(inner) {
  return function IconCmp({ size = 18, color = 'currentColor', className = '', style, ...rest }) {
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className={className}
        style={style}
        dangerouslySetInnerHTML={{ __html: inner }}
        {...rest}
      />
    )
  }
}

export const Sprout = makeIcon(`<path d="M7 20h10"/><path d="M10 20c0-5-2-8-6-8 0 4 2 6 6 6"/><path d="M14 20c0-6 3-9 7-9 0 5-3 8-7 8"/><path d="M12 20v-6"/>`)
export const Camera = makeIcon(`<path d="M4 8h3l2-3h6l2 3h3a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1z"/><circle cx="12" cy="13" r="3.5"/>`)
export const Upload = makeIcon(`<path d="M12 16V4"/><path d="M7 9l5-5 5 5"/><path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/>`)
export const ShieldCheck = makeIcon(`<path d="M12 3l7 3v6c0 5-3 8-7 9-4-1-7-4-7-9V6z"/><path d="M9 12l2 2 4-4"/>`)
export const AlertTriangle = makeIcon(`<path d="M12 4L2 20h20L12 4z"/><path d="M12 10v4"/><path d="M12 17h.01"/>`)
export const MapPin = makeIcon(`<path d="M12 21s7-6.5 7-12a7 7 0 1 0-14 0c0 5.5 7 12 7 12z"/><circle cx="12" cy="9" r="2.5"/>`)
export const CloudRain = makeIcon(`<path d="M7 16a4 4 0 0 1 .3-8 5.5 5.5 0 0 1 10.6 1.5A3.5 3.5 0 0 1 17 16H7z"/><path d="M9 19l-1 2"/><path d="M13 19l-1 2"/><path d="M17 19l-1 2"/>`)
export const Droplets = makeIcon(`<path d="M12 3c3 4 6 7 6 10a6 6 0 0 1-12 0c0-3 3-6 6-10z"/>`)
export const ThermometerSun = makeIcon(`<path d="M10 14V5a2 2 0 1 1 4 0v9a4 4 0 1 1-4 0z"/><path d="M4 12h1"/><path d="M4.5 8.5l.8.5"/><path d="M4.5 15.5l.8-.5"/>`)
export const User = makeIcon(`<circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.5-6 8-6s8 2 8 6"/>`)
export const Landmark = makeIcon(`<path d="M3 21h18"/><path d="M5 21V10"/><path d="M9 21V10"/><path d="M15 21V10"/><path d="M19 21V10"/><path d="M3 10l9-6 9 6"/>`)
export const Menu = makeIcon(`<path d="M4 6h16"/><path d="M4 12h16"/><path d="M4 18h16"/>`)
export const X = makeIcon(`<path d="M5 5l14 14"/><path d="M19 5L5 19"/>`)
export const ArrowRight = makeIcon(`<path d="M4 12h16"/><path d="M13 5l7 7-7 7"/>`)
export const CheckCircle2 = makeIcon(`<circle cx="12" cy="12" r="9"/><path d="M8.5 12.5l2.5 2.5 5-5"/>`)
export const Clock = makeIcon(`<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/>`)
export const TrendingUp = makeIcon(`<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>`)
export const RefreshCw = makeIcon(`<path d="M21 12a9 9 0 1 1-3-6.7"/><path d="M21 3v6h-6"/>`)
export const LogOut = makeIcon(`<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5"/><path d="M21 12H9"/>`)
export const Languages = makeIcon(`<circle cx="12" cy="12" r="9"/><path d="M3 12h18"/><path d="M12 3c2.5 2.5 4 5.7 4 9s-1.5 6.5-4 9c-2.5-2.5-4-5.7-4-9s1.5-6.5 4-9z"/>`)
export const ChevronRight = makeIcon(`<path d="M9 6l6 6-6 6"/>`)
export const Sparkles = makeIcon(`<path d="M12 3l1.5 4.5L18 9l-4.5 1.5L12 15l-1.5-4.5L6 9l4.5-1.5z"/><path d="M19 15l.7 2 2 .7-2 .7-.7 2-.7-2-2-.7 2-.7z"/>`)
export const ClipboardList = makeIcon(`<rect x="6" y="4" width="12" height="17" rx="2"/><path d="M9 4V3a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v1"/><path d="M9 11h6"/><path d="M9 15h6"/><path d="M9 19h4"/>`)
export const ExternalLink = makeIcon(`<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><path d="M15 3h6v6"/><path d="M10 14L21 3"/>`)
export const Database = makeIcon(`<ellipse cx="12" cy="6" rx="7" ry="3"/><path d="M5 6v6c0 1.7 3.1 3 7 3s7-1.3 7-3V6"/><path d="M5 12v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6"/>`)
export const ImagePlus = makeIcon(`<rect x="3" y="4" width="14" height="14" rx="2"/><circle cx="8" cy="9" r="1.5"/><path d="M4 17l4-4 3 3 3-3 3 3"/><path d="M19 5v6"/><path d="M16 8h6"/>`)
export const Bug = makeIcon(`<rect x="8" y="7" width="8" height="12" rx="4"/><path d="M12 7V4"/><path d="M9 4l1.5 2"/><path d="M15 4l-1.5 2"/><path d="M8 11H4"/><path d="M8 15H4"/><path d="M16 11h4"/><path d="M16 15h4"/><path d="M9 19l-2 2"/><path d="M15 19l2 2"/>`)
export const Wifi = makeIcon(`<path d="M2 8.5a16 16 0 0 1 20 0"/><path d="M5.5 12.5a11 11 0 0 1 13 0"/><path d="M9 16.5a6 6 0 0 1 6 0"/><circle cx="12" cy="19.5" r="1"/>`)
export const Bell = makeIcon(`<path d="M6 9a6 6 0 1 1 12 0c0 4 1.5 5.5 2 6H4c.5-.5 2-2 2-6z"/><path d="M10 19a2 2 0 0 0 4 0"/>`)
export const FlaskConical = makeIcon(`<path d="M9 3h6"/><path d="M10 3v6l-5.5 9.5A1.5 1.5 0 0 0 5.8 21h12.4a1.5 1.5 0 0 0 1.3-2.5L14 9V3"/><path d="M7.5 15h9"/>`)
export const Stethoscope = makeIcon(`<path d="M5 4v6a5 5 0 0 0 10 0V4"/><path d="M7 4H3"/><path d="M11 4H7"/><path d="M15 10v2a6 6 0 0 0 12 0"/>`)
export const Map2 = makeIcon(`<path d="M3 6l6-2 6 2 6-2v14l-6 2-6-2-6 2z"/><path d="M9 4v14"/><path d="M15 6v14"/>`)
export const BrainCog = makeIcon(`<circle cx="12" cy="12" r="4"/><path d="M12 3v2"/><path d="M12 19v2"/><path d="M4.9 4.9l1.4 1.4"/><path d="M17.7 17.7l1.4 1.4"/><path d="M3 12h2"/><path d="M19 12h2"/><path d="M4.9 19.1l1.4-1.4"/><path d="M17.7 6.3l1.4-1.4"/>`)
export const HistoryIcon = makeIcon(`<path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 3v5h5"/><path d="M12 7v5l3.5 2"/>`)
export const Download = makeIcon(`<path d="M12 4v12"/><path d="M7 11l5 5 5-5"/><path d="M4 19h16"/>`)
export const Activity = makeIcon(`<path d="M22 12h-4l-3 8-6-16-3 8H2"/>`)
export const UsersIcon = makeIcon(`<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>`)
export const Bot = makeIcon(`<rect x="4" y="8" width="16" height="12" rx="2"/><path d="M12 8V4"/><circle cx="9" cy="14" r="1"/><circle cx="15" cy="14" r="1"/><path d="M9 18h6"/>`)
export const Plus = makeIcon(`<path d="M12 5v14"/><path d="M5 12h14"/>`)
