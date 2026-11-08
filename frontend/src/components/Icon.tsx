// Small hand-drawn icon set (24x24, stroked) - avoids an icon-library dependency.
import type { CSSProperties } from 'react'

const P: Record<string, JSX.Element> = {
  check: <path d="M5 12.5l4.5 4.5L19 7.5" />,
  x: <path d="M6 6l12 12M18 6L6 18" />,
  lock: <><rect x="5" y="11" width="14" height="10" rx="2.5" /><path d="M8 11V7.5a4 4 0 0 1 8 0V11" /></>,
  star: <path d="M12 2.8l2.8 5.9 6.4.8-4.7 4.4 1.2 6.4L12 17.2l-5.7 3.1 1.2-6.4-4.7-4.4 6.4-.8z" />,
  flame: <path d="M12 2.5c.8 3.6 5 5.3 5 10.6a5 5 0 0 1-10 0c0-2.4 1.3-3.9 2.4-4.9.2 1.8 1.2 2.9 2.4 3 0-3-1-5.6.2-8.7z" />,
  bolt: <path d="M13 2.5L4.5 13.5H11l-1 8 8.5-11H12z" />,
  bulb: <><path d="M9 18h6M10 21.5h4" /><path d="M12 2.5a6.5 6.5 0 0 0-3.8 11.8c.5.4.8.9.8 1.5V16h6v-.2c0-.6.3-1.1.8-1.5A6.5 6.5 0 0 0 12 2.5z" /></>,
  eye: <><path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z" /><circle cx="12" cy="12" r="3" /></>,
  play: <path d="M7 4.5l12 7.5-12 7.5z" />,
  pause: <path d="M8.5 5v14M15.5 5v14" />,
  next: <path d="M5.5 5l9 7-9 7zM18.5 5v14" />,
  prev: <path d="M18.5 5l-9 7 9 7zM5.5 5v14" />,
  restart: <><path d="M3.5 12a8.5 8.5 0 1 0 2.7-6.2L3.5 8.5" /><path d="M3.5 3.5v5h5" /></>,
  trophy: <><path d="M8 21h8M12 16.5V21M7 3.5h10v5a5 5 0 0 1-10 0z" /><path d="M17 5h3a3 3 0 0 1-3.5 4M7 5H4a3 3 0 0 0 3.5 4" /></>,
  map: <><path d="M9 3.5L3.5 6v14.5L9 18l6 2.5 5.5-2.5V3.5L15 6z" /><path d="M9 3.5V18M15 6v14.5" /></>,
  user: <><circle cx="12" cy="8" r="4" /><path d="M4 21a8 8 0 0 1 16 0" /></>,
  logout: <><path d="M9 21H5.5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2H9" /><path d="M16 17l5-5-5-5M21 12H9.5" /></>,
  sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></>,
  moon: <path d="M20.5 13A8.5 8.5 0 1 1 11 3.5a6.5 6.5 0 0 0 9.5 9.5z" />,
  arrowRight: <path d="M5 12h14M13 6l6 6-6 6" />,
  arrowUp: <path d="M12 19.5v-15M5.5 11L12 4.5 18.5 11" />,
  chevronLeft: <path d="M15 6l-6 6 6 6" />,
  chevronRight: <path d="M9 6l6 6-6 6" />,
  door: <><path d="M5.5 21V4a1 1 0 0 1 1-1h11a1 1 0 0 1 1 1v17M3 21h18" /><circle cx="15" cy="12.5" r=".6" fill="currentColor" /></>,
  nodes: <><circle cx="6" cy="6" r="2.6" /><circle cx="18" cy="6" r="2.6" /><circle cx="12" cy="18" r="2.6" /><path d="M8.6 6h6.8M7.2 8.3l3.6 7.4M16.8 8.3l-3.6 7.4" /></>,
  table: <><rect x="3" y="4" width="18" height="16" rx="2.5" /><path d="M3 10h18M3 15h18M9 4v16" /></>,
  dive: <><path d="M12 3v13M6.5 10.5L12 16l5.5-5.5" /><path d="M4.5 20.5h15" /></>,
  undo: <><path d="M9 14L4 9l5-5" /><path d="M4 9h10.5a6 6 0 0 1 0 12H11" /></>,
  split: <><path d="M12 3v6M12 9l-6 6v6M12 9l6 6v6" /><circle cx="12" cy="9" r="1.2" fill="currentColor" /></>,
  crown: <path d="M3.5 18.5h17M4.5 18.5L3 7.5l5 4 4-6.5 4 6.5 5-4-1.5 11" />,
  footprints: <><path d="M7.5 3.5c1.9 0 2.9 2 2.9 4.8s-1 5-2.9 5-2.9-2.2-2.9-5 1-4.8 2.9-4.8z" /><path d="M16.5 9.5c1.9 0 2.9 2 2.9 4.8s-1 5-2.9 5-2.9-2.2-2.9-5 1-4.8 2.9-4.8z" /></>,
  spool: <><ellipse cx="12" cy="5" rx="6" ry="2" /><ellipse cx="12" cy="19" rx="6" ry="2" /><path d="M6 5v14M18 5v14M7 9.5l10 2M7 13.5l10 2" /></>,
  anchor: <><circle cx="12" cy="5" r="2.2" /><path d="M12 7.2V21M5 13a7 7 0 0 0 14 0M8.5 11h7" /></>,
  repeat: <><path d="M17 2.5l3.5 3.5-3.5 3.5" /><path d="M3.5 11.5V10a4 4 0 0 1 4-4h13" /><path d="M7 21.5L3.5 18 7 14.5" /><path d="M20.5 12.5V14a4 4 0 0 1-4 4h-13" /></>,
  shield: <path d="M12 2.5l8 3v6c0 5-3.4 8.8-8 10.5-4.6-1.7-8-5.5-8-10.5v-6z" />,
  sword: <><path d="M14.5 17.5L3.5 6.5v-3h3l11 11" /><path d="M13 19.5l6.5-6.5M16.5 16.5l4 4" /></>,
  info: <><circle cx="12" cy="12" r="9.5" /><path d="M12 16.5v-5M12 7.5h.01" /></>,
  sparkles: <path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8zM19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z" />,
  target: <><circle cx="12" cy="12" r="9.5" /><circle cx="12" cy="12" r="5.5" /><circle cx="12" cy="12" r="1.5" /></>,
  trend: <path d="M3.5 17l6-6 4 4 7-7.5M15 7.5h5.5V13" />,
  dot: <circle cx="12" cy="12" r="4" fill="currentColor" />,
  minus: <path d="M5 12h14" />,
  layers: <><path d="M12 3l9 5-9 5-9-5z" /><path d="M3 13l9 5 9-5" /></>,
}

export type IconName = keyof typeof P

export function Icon({ name, size = 18, filled = false, style, className }: {
  name: string
  size?: number
  filled?: boolean
  style?: CSSProperties
  className?: string
}) {
  return (
    <svg
      width={size} height={size} viewBox="0 0 24 24" fill={filled ? 'currentColor' : 'none'}
      stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"
      aria-hidden="true" style={style} className={className}
    >
      {P[name] ?? P.dot}
    </svg>
  )
}

/** Brand mark: a spool with a thread running off it. */
export function Logo({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden="true">
      <rect x="3" y="3" width="26" height="26" rx="8" fill="currentColor" opacity=".16" />
      <circle cx="11" cy="11" r="3" fill="currentColor" />
      <circle cx="22" cy="14" r="2.4" fill="currentColor" opacity=".7" />
      <circle cx="14" cy="23" r="2.4" fill="currentColor" opacity=".7" />
      <path d="M11 11 L22 14 L14 23" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
