import type { ReactNode } from 'react'
import { Icon } from './Icon'
import type { Feedback } from '../engine/tracer'

export function Stars({ count, max = 3, size = 16, pop = false }: { count: number; max?: number; size?: number; pop?: boolean }) {
  return (
    <span className={`stars ${pop ? 'pop' : ''}`} role="img" aria-label={`${count} of ${max} stars`}>
      {Array.from({ length: max }, (_, i) => (
        <Icon key={i} name="star" size={size} filled className={i < count ? 'on' : ''} />
      ))}
    </span>
  )
}

/** Ratio-against-limit meter: track is a lighter step of the fill's own hue. */
export function Meter({ value, color = 'var(--brand)', target, size = '', label }: {
  value: number
  color?: string
  target?: number
  size?: '' | 'thin' | 'thick'
  label: string
}) {
  const pct = Math.max(0, Math.min(1, value)) * 100
  return (
    <div className={`meter ${size}`} style={{ ['--meter' as string]: color }} role="meter" aria-label={label}
      aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(pct)}>
      <div className="fill" style={{ width: `${pct}%` }} />
      {target !== undefined && <div className="target" style={{ left: `calc(${target * 100}% - 1px)` }} title={`Target ${Math.round(target * 100)}%`} />}
    </div>
  )
}

export function masteryStatus(value: number, evidence: number) {
  if (evidence === 0) return { label: 'Not started', icon: 'minus', color: 'var(--ink-3)' }
  if (value >= 0.7) return { label: 'Mastered', icon: 'check', color: 'var(--chalk)' }
  if (value >= 0.4) return { label: 'Developing', icon: 'trend', color: 'var(--status-dev)' }
  return { label: 'Needs revision', icon: 'undo', color: 'var(--danger)' }
}

export function FeedbackBox({ fb, children }: { fb: Feedback | null; children?: ReactNode }) {
  if (!fb) return null
  const icon = fb.tone === 'good' ? 'check' : fb.tone === 'warn' ? 'x' : fb.tone === 'hint' ? 'bulb' : 'eye'
  return (
    <div className={`feedback ${fb.tone}`} role="status" aria-live="polite" key={`${fb.title}-${fb.tier}`}>
      <div className="ic"><Icon name={icon} /></div>
      <div style={{ flex: 1 }}>
        <div className="t">
          {fb.title}
          {fb.tier > 0 && (
            <span className="tier-dots" title={`Scaffolding level ${fb.tier} of 3`} aria-label={`Hint level ${fb.tier} of 3`}>
              {[1, 2, 3].map((t) => <i key={t} className={t <= fb.tier ? 'on' : ''} />)}
            </span>
          )}
        </div>
        {fb.body && <div className="b">{fb.body}</div>}
        {children}
      </div>
    </div>
  )
}

export const BLOOM_COLORS: Record<string, string> = {
  Explain: 'chip brand',
  Apply: 'chip gold',
  'Apply / Analyse': 'chip gold',
  Evaluate: 'chip chalk',
}

export function avatarColor(seed: string): string {
  const hues = [258, 35, 160, 210, 340, 120, 15]
  let h = 0
  for (const c of seed) h = (h * 31 + c.charCodeAt(0)) >>> 0
  return `hsl(${hues[h % hues.length]} 55% 48%)`
}

/** Renders the tiny subset of markdown used in prompts: **bold** and *italic*. */
export function Md({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g)
  return (
    <>
      {parts.map((p, i) =>
        p.startsWith('**') ? <strong key={i}>{p.slice(2, -2)}</strong>
          : p.startsWith('*') && p.length > 2 ? <em key={i}>{p.slice(1, -1)}</em>
            : <span key={i}>{p}</span>,
      )}
    </>
  )
}
