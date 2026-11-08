// Discovery checklist with an on-demand hint for the next unfinished task. Used by the
// exploratory lessons (Frame 1 inspector, representation views), where hints are free.

import { Fragment, useState } from 'react'
import { useIdle } from '../lib/useIdle'
import { Icon } from './Icon'

export interface CheckItem {
  id: string
  text: string
}

/**
 * Tracks which task the learner asked about and how far (level 1 = tip, level 2 = visual cue).
 * The hint follows the *next unfinished* task, so finishing one moves the help along with you.
 */
export function useChecklistHint(items: CheckItem[], done: Set<string>, levels: (id: string) => number) {
  const next = items.find((c) => !done.has(c.id))
  const [asked, setAsked] = useState<{ id: string; level: number } | null>(null)
  const level = next && asked?.id === next.id ? asked.level : 0
  const max = next ? levels(next.id) : 1
  const idle = useIdle(30000, done.size, !!next && level === 0)
  return {
    next: next?.id ?? null,
    level,
    max,
    nudge: idle,
    ask: () => next && setAsked({ id: next.id, level: Math.min(max, level + 1) }),
  }
}

export function Checklist({ items, done, tipFor, tip }: {
  items: CheckItem[]
  done: Set<string>
  tipFor: string | null
  tip?: string
}) {
  return (
    <ul className="checklist">
      {items.map((c) => (
        <Fragment key={c.id}>
          <li className={done.has(c.id) ? 'done' : ''}>
            <span className="box">{done.has(c.id) && <Icon name="check" size={14} />}</span>{c.text}
          </li>
          {tipFor === c.id && tip && <li className="tip" role="status"><Icon name="bulb" size={14} /> {tip}</li>}
        </Fragment>
      ))}
    </ul>
  )
}
