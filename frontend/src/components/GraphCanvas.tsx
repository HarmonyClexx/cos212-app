import { useEffect, useId, useMemo, useRef, useState, type KeyboardEvent } from 'react'
import { edgeId, type GraphSpec } from '../engine/graph'

export type NodeMark =
  | 'visited' | 'current' | 'stack' | 'hint' | 'selected' | 'correct' | 'wrong' | 'missing'
  | 'fog' | 'goal' | 'dim' | 'start' | 'deadend' | 'hover' | 'shake'
export type EdgeMark = 'traversed' | 'selected' | 'correct' | 'wrong' | 'missing' | 'fog' | 'dim' | 'hover' | 'highlight'

export interface Flash {
  node: string
  kind: 'good' | 'bad'
  nonce: number
}

interface Props {
  graph: GraphSpec
  nodeMarks?: Record<string, (NodeMark | false | undefined)[] | undefined>
  edgeMarks?: Record<string, (EdgeMark | false | undefined)[] | undefined>
  /** Ordered path drawn as Ariadne's golden thread (i.e. the DFS stack). */
  thread?: string[]
  badges?: Record<string, { text: string | number; tone?: 'gold' | 'chalk' } | undefined>
  labels?: Record<string, string>
  hiddenNodes?: Set<string>
  hiddenEdges?: Set<string>
  flash?: Flash | null
  onNodeClick?: (id: string) => void
  onEdgeClick?: (id: string) => void
  onNodeHover?: (id: string | null) => void
  onEdgeHover?: (id: string | null) => void
  nodeClickable?: (id: string) => boolean
  ariaLabel?: string
  maxHeight?: number
}

const R = 5.4
const PAD = 7

function seg(ax: number, ay: number, bx: number, by: number, trimA: number, trimB: number) {
  const dx = bx - ax
  const dy = by - ay
  const len = Math.hypot(dx, dy) || 1
  const ux = dx / len
  const uy = dy / len
  return { x1: ax + ux * trimA, y1: ay + uy * trimA, x2: bx - ux * trimB, y2: by - uy * trimB, len }
}

interface Ghost {
  key: string
  u: string
  v: string
}

export function GraphCanvas({
  graph, nodeMarks = {}, edgeMarks = {}, thread = [], badges = {}, labels = {}, hiddenNodes, hiddenEdges,
  flash, onNodeClick, onEdgeClick, onNodeHover, onEdgeHover, nodeClickable, ariaLabel, maxHeight = 460,
}: Props) {
  const uid = useId().replace(/:/g, '')
  const pos = useMemo(() => Object.fromEntries(graph.nodes.map((n) => [n.id, n])), [graph])
  const box = useMemo(() => {
    const xs = graph.nodes.map((n) => n.x)
    const ys = graph.nodes.map((n) => n.y)
    const minX = Math.min(...xs) - R - PAD
    const minY = Math.min(...ys) - R - PAD
    return { minX, minY, w: Math.max(...xs) - minX + R + PAD, h: Math.max(...ys) - minY + R + PAD }
  }, [graph])

  // Thread segments that were just removed animate "winding back" for a moment.
  const prevThread = useRef<string[]>(thread)
  const [ghosts, setGhosts] = useState<Ghost[]>([])
  useEffect(() => {
    const prev = prevThread.current
    let common = 0
    while (common < prev.length && common < thread.length && prev[common] === thread[common]) common++
    // Segment i joins prev[i-1] -> prev[i]; every segment past the shared prefix was removed.
    const removed: Ghost[] = []
    const stamp = Date.now()
    for (let i = Math.max(1, common); i < prev.length; i++) {
      removed.push({ key: `g${stamp}-${i}`, u: prev[i - 1], v: prev[i] })
    }
    prevThread.current = thread
    if (removed.length) {
      setGhosts((g) => [...g, ...removed])
      // Deliberately not cancelled on re-render: rapid pushes/pops must not strand a ghost.
      setTimeout(() => setGhosts((g) => g.filter((x) => !removed.includes(x))), 600)
    }
  }, [thread])

  const edgeList = graph.edges.map(([u, v]) => ({ u, v, id: edgeId(graph, u, v) }))

  const markerFor = (marks: (EdgeMark | false | undefined)[]) => {
    if (marks.includes('wrong')) return 'danger'
    if (marks.includes('correct') || marks.includes('missing') || marks.includes('traversed')) return 'chalk'
    if (marks.includes('selected') || marks.includes('hover')) return 'brand'
    if (marks.includes('highlight')) return 'hint'
    return 'default'
  }

  const keyActivate = (fn: () => void) => (e: KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      fn()
    }
  }

  return (
    <svg
      className="gc"
      viewBox={`${box.minX} ${box.minY} ${box.w} ${box.h}`}
      style={{ maxHeight }}
      role="group"
      aria-label={ariaLabel ?? `${graph.directed ? 'Directed' : 'Undirected'} graph with ${graph.nodes.length} vertices`}
    >
      <defs>
        {['default', 'brand', 'chalk', 'danger', 'hint'].map((m) => (
          <marker key={m} id={`${uid}-arrow-${m}`} viewBox="0 0 6 6" refX="5.4" refY="3" markerWidth="3.4" markerHeight="3.4"
            markerUnits="userSpaceOnUse" orient="auto">
            <path d="M0,0 L6,3 L0,6 z" className={`gc-arrow-${m}`} />
          </marker>
        ))}
      </defs>

      <g>
        {edgeList.map(({ u, v, id }) => {
          if (hiddenEdges?.has(id)) return null
          const a = pos[u]
          const b = pos[v]
          const s = seg(a.x, a.y, b.x, b.y, R, graph.directed ? R + 0.6 : R)
          const marks = edgeMarks[id] ?? []
          const clickable = !!onEdgeClick
          return (
            <g
              key={id}
              className={['gc-edge', clickable && 'clickable', ...marks].filter(Boolean).join(' ')}
              onClick={clickable ? () => onEdgeClick(id) : undefined}
              onMouseEnter={onEdgeHover ? () => onEdgeHover(id) : undefined}
              onMouseLeave={onEdgeHover ? () => onEdgeHover(null) : undefined}
              role={clickable ? 'button' : undefined}
              tabIndex={clickable ? 0 : undefined}
              aria-label={clickable ? `Edge ${graph.directed ? `${u} to ${v}` : `${u}–${v}`}` : undefined}
              aria-pressed={clickable ? marks.includes('selected') : undefined}
              onKeyDown={clickable ? keyActivate(() => onEdgeClick(id)) : undefined}
            >
              <line className="vis" x1={s.x1} y1={s.y1} x2={s.x2} y2={s.y2}
                markerEnd={graph.directed ? `url(#${uid}-arrow-${markerFor(marks)})` : undefined} />
              <line className="hit" x1={s.x1} y1={s.y1} x2={s.x2} y2={s.y2} />
            </g>
          )
        })}
      </g>

      <g className="gc-thread" aria-hidden="true">
        {thread.slice(1).map((v, i) => {
          const a = pos[thread[i]]
          const b = pos[v]
          if (!a || !b) return null
          const len = Math.hypot(b.x - a.x, b.y - a.y)
          return (
            <line key={`${i}:${thread[i]}>${v}`} className="grow" x1={a.x} y1={a.y} x2={b.x} y2={b.y}
              style={{ ['--len' as string]: len }} />
          )
        })}
        {ghosts.map((g) => {
          const a = pos[g.u]
          const b = pos[g.v]
          if (!a || !b) return null
          const len = Math.hypot(b.x - a.x, b.y - a.y)
          return <line key={g.key} className="ghost" x1={a.x} y1={a.y} x2={b.x} y2={b.y} style={{ ['--len' as string]: len }} />
        })}
      </g>

      <g>
        {graph.nodes.map((n) => {
          if (hiddenNodes?.has(n.id)) return null
          const marks = (nodeMarks[n.id] ?? []).filter(Boolean) as NodeMark[]
          const clickable = !!onNodeClick && (nodeClickable ? nodeClickable(n.id) : true)
          const badge = badges[n.id]
          const label = labels[n.id] ?? n.id
          const status = marks.filter((m) => ['visited', 'current', 'selected', 'correct', 'wrong'].includes(m)).join(', ')
          return (
            <g
              key={n.id}
              className={['gc-node', clickable && 'clickable', ...marks].join(' ')}
              onClick={clickable ? () => onNodeClick!(n.id) : undefined}
              onMouseEnter={onNodeHover ? () => onNodeHover(n.id) : undefined}
              onMouseLeave={onNodeHover ? () => onNodeHover(null) : undefined}
              role={clickable ? 'button' : undefined}
              tabIndex={clickable ? 0 : undefined}
              aria-label={marks.includes('fog') ? 'Unexplored room' : `Vertex ${label}${status ? `, ${status}` : ''}`}
              onKeyDown={clickable ? keyActivate(() => onNodeClick!(n.id)) : undefined}
            >
              <circle className="halo" cx={n.x} cy={n.y} r={R} />
              <circle className="body" cx={n.x} cy={n.y} r={R} />
              <circle className="ring" cx={n.x} cy={n.y} r={R + 1.6} />
              <text className="label" x={n.x} y={n.y + 0.2}>{label}</text>
              {flash && flash.node === n.id && (
                <circle key={flash.nonce} className={flash.kind === 'good' ? 'flash-good' : 'flash-bad'} cx={n.x} cy={n.y} r={R} />
              )}
              {badge && (
                <g className={`gc-badge ${badge.tone ?? ''}`}>
                  <circle cx={n.x + R * 0.82} cy={n.y - R * 0.82} r={2.3} />
                  <text x={n.x + R * 0.82} y={n.y - R * 0.82 + 0.1}>{badge.text}</text>
                </g>
              )}
            </g>
          )
        })}
      </g>
    </svg>
  )
}
