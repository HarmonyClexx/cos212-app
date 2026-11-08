import { useEffect, useRef, useState } from 'react'
import { Icon } from './Icon'

/** The call stack, drawn bottom-up. Popped frames fly out so the learner *sees* backtracking. */
export function StackPanel({
  items, title = 'Call stack', deadEnd = false, onPop, popEnabled = false, popLabel = 'Backtrack (pop)',
}: {
  items: string[]
  title?: string
  deadEnd?: boolean
  onPop?: () => void
  popEnabled?: boolean
  popLabel?: string
}) {
  const prev = useRef(items)
  const [ghost, setGhost] = useState<{ node: string; key: number } | null>(null)
  useEffect(() => {
    const p = prev.current
    prev.current = items
    if (items.length < p.length) {
      const key = Date.now()
      setGhost({ node: p[p.length - 1], key })
      setTimeout(() => setGhost((g) => (g?.key === key ? null : g)), 450)
    }
  }, [items])

  return (
    <div className="ds-panel">
      <div className="ds-head">
        <div className="title"><span className="dot" style={{ background: 'var(--thread)' }} />{title}</div>
        <span className="faint tiny">{items.length} frame{items.length === 1 ? '' : 's'}</span>
      </div>
      <div className="stack-box" aria-live="polite" aria-label={`Stack, bottom to top: ${items.join(', ') || 'empty'}`}>
        {items.length === 0 && !ghost && <div className="stack-empty">Empty stack<br />— traversal complete —</div>}
        {items.map((n, i) => {
          const top = i === items.length - 1
          return (
            <div key={`${i}-${n}`} className={`frame ${top ? 'top' : ''} ${top && deadEnd ? 'deadend' : ''}`}>
              <span className="fn">dfs(</span>{n}<span className="fn">)</span>
              {top && <span className="tag">{deadEnd ? 'dead end' : 'top'}</span>}
              {i === 0 && !top && <span className="tag faint">bottom</span>}
            </div>
          )
        })}
        {ghost && (
          <div key={ghost.key} className="frame ghost" style={{ top: 10 }}>
            <span className="fn">dfs(</span>{ghost.node}<span className="fn">)</span><span className="tag">popped</span>
          </div>
        )}
      </div>
      {onPop && (
        <button className="btn gold block" onClick={onPop} disabled={!popEnabled}>
          <Icon name="arrowUp" /> {popLabel}
        </button>
      )}
    </div>
  )
}

export function QueuePanel({ items }: { items: string[] }) {
  return (
    <div className="ds-panel">
      <div className="ds-head">
        <div className="title"><span className="dot" style={{ background: 'var(--hint)' }} />Queue</div>
        <span className="faint tiny">front → back</span>
      </div>
      <div className="queue-box" aria-label={`Queue, front to back: ${items.join(', ') || 'empty'}`}>
        {items.length === 0 && <span className="faint small">empty</span>}
        {items.map((n, i) => (
          <div key={`${n}`} className={`frame ${i === 0 ? 'front' : ''}`}>{n}</div>
        ))}
      </div>
    </div>
  )
}

export function VisitedStrip({ order, total, title = 'Visited (chalk marks)' }: { order: string[]; total?: number; title?: string }) {
  return (
    <div className="ds-panel">
      <div className="ds-head">
        <div className="title"><span className="dot" style={{ background: 'var(--chalk)' }} />{title}</div>
        {total !== undefined && <span className="faint tiny">{order.length}/{total}</span>}
      </div>
      <div className="visited-strip" aria-label={`Visited in order: ${order.join(', ') || 'none yet'}`}>
        {order.length === 0 && <span className="faint small">Nothing yet</span>}
        {order.map((n, i) => (
          <span key={n} className="vchip"><span className="n">{i + 1}</span>{n}</span>
        ))}
      </div>
    </div>
  )
}
