// The "visual example" half of each lesson page (design doc 2.2): small figures the learner can
// poke at while reading. They reuse the game's own canvas and panels, so the pictures in the
// lessons are exactly the pictures the game will show.

import { useMemo, useState } from 'react'
import type { LessonFigure } from '../../api/types'
import { QueuePanel, StackPanel, VisitedStrip } from '../../components/DataStructures'
import { GraphCanvas, type EdgeMark, type NodeMark } from '../../components/GraphCanvas'
import { Icon } from '../../components/Icon'
import { adjacency, bfsTrace, dfsOrder, bfsOrder, dfsTrace, edgeId, listJoin, type GraphSpec } from '../../engine/graph'
import { narrate } from '../../engine/tracer'
import { addMark, traceVisuals } from '../shared'

export function LessonFigureView({ fig }: { fig: LessonFigure }) {
  switch (fig.kind) {
    case 'graph': return <GraphsFigure fig={fig} />
    case 'neighbours': return <NeighboursFigure g={fig.graphs[0]} />
    case 'representation': return <RepresentationFigure fig={fig} />
    case 'stack': return <ToyFigure mode="stack" />
    case 'queue': return <ToyFigure mode="queue" />
    case 'trace': return fig.algorithm === 'bfs' ? <BfsStepper g={fig.graphs[0]} start={fig.start!} /> : <DfsStepper g={fig.graphs[0]} start={fig.start!} />
    case 'orders': return <OrdersFigure g={fig.graphs[0]} start={fig.start!} />
  }
}

function highlightMarks(g: GraphSpec, ids: string[]) {
  const nodes = new Set(g.nodes.map((n) => n.id))
  const edges = new Set(g.edges.map(([u, v]) => edgeId(g, u, v)))
  const nodeMarks: Record<string, NodeMark[]> = {}
  const edgeMarks: Record<string, EdgeMark[]> = {}
  for (const id of ids) {
    if (nodes.has(id)) nodeMarks[id] = ['selected']
    else if (edges.has(id)) edgeMarks[id] = ['selected']
  }
  return { nodeMarks, edgeMarks }
}

function GraphsFigure({ fig }: { fig: LessonFigure }) {
  return (
    <div className={`fig-graphs n${fig.graphs.length}`}>
      {fig.graphs.map((g, i) => {
        const { nodeMarks, edgeMarks } = highlightMarks(g, fig.highlight)
        return (
          <figure key={g.id}>
            <GraphCanvas graph={g} nodeMarks={nodeMarks} edgeMarks={edgeMarks} maxHeight={300}
              ariaLabel={fig.captions[i] ?? undefined} />
            {fig.captions[i] && <figcaption>{fig.captions[i]}</figcaption>}
          </figure>
        )
      })}
    </div>
  )
}

/** Tap a vertex: its neighbours and edges light up, and its degree is counted. */
function NeighboursFigure({ g }: { g: GraphSpec }) {
  const adj = useMemo(() => adjacency(g), [g])
  const [sel, setSel] = useState<string | null>(null)
  const nodeMarks: Record<string, NodeMark[]> = {}
  const edgeMarks: Record<string, EdgeMark[]> = {}
  if (sel) {
    nodeMarks[sel] = ['selected']
    for (const n of adj[sel]) {
      nodeMarks[n] = ['correct']
      edgeMarks[edgeId(g, sel, n)] = ['correct']
    }
  }
  return (
    <div className="stack-v">
      <GraphCanvas graph={g} nodeMarks={nodeMarks} edgeMarks={edgeMarks} onNodeClick={(id) => setSel(id)} maxHeight={300}
        ariaLabel="Graph: select a vertex to see its neighbours" />
      <div className="fig-readout" aria-live="polite">
        {sel ? (
          <>
            <span className="chip brand">{sel}</span>
            <span>Neighbours: <b>{listJoin(adj[sel]) || 'none'}</b></span>
            <span className="chip chalk">degree {adj[sel].length}</span>
          </>
        ) : <span className="muted"><Icon name="arrowRight" size={14} /> Tap any vertex.</span>}
      </div>
    </div>
  )
}

/** One graph, written down as a list and/or a matrix. Hovering anything lights up its row. */
function RepresentationFigure({ fig }: { fig: LessonFigure }) {
  const [directed, setDirected] = useState(false)
  const g = directed && fig.graphs[1] ? fig.graphs[1] : fig.graphs[0]
  const adj = useMemo(() => adjacency(g), [g])
  const ids = g.nodes.map((n) => n.id)
  const [focus, setFocus] = useState<string | null>(null)
  const nodeMarks: Record<string, NodeMark[]> = {}
  const edgeMarks: Record<string, EdgeMark[]> = {}
  if (focus) {
    nodeMarks[focus] = ['hover']
    for (const n of adj[focus]) edgeMarks[edgeId(g, focus, n)] = ['hover']
  }
  const showList = fig.views.includes('list')
  const showMatrix = fig.views.includes('matrix')

  return (
    <div className="stack-v">
      {fig.graphs[1] && (
        <div className="tabs" style={{ maxWidth: 260 }}>
          <button className={!directed ? 'active' : ''} onClick={() => { setDirected(false); setFocus(null) }}>Undirected</button>
          <button className={directed ? 'active' : ''} onClick={() => { setDirected(true); setFocus(null) }}>Directed</button>
        </div>
      )}
      <div className="fig-rep">
        <GraphCanvas graph={g} nodeMarks={nodeMarks} edgeMarks={edgeMarks} maxHeight={240}
          onNodeHover={setFocus} onNodeClick={(id) => setFocus(id)} />
        <div className="stack-v" style={{ gap: 14 }}>
          {showList && (
            <div className="list-view" aria-label="Adjacency list">
              {ids.map((r) => (
                <div key={r} className={`lrow ${focus === r ? 'hl' : ''}`} onMouseEnter={() => setFocus(r)} onMouseLeave={() => setFocus(null)}
                  onClick={() => setFocus(r)}>
                  <span className="k">{r}</span><span className="faint">→</span>
                  <span className="v">{adj[r].length ? adj[r].map((n) => <span key={n}>{n}</span>) : <span className="faint">∅</span>}</span>
                </div>
              ))}
            </div>
          )}
          {showMatrix && (
            <div style={{ overflowX: 'auto' }}>
              <table className="matrix" aria-label="Adjacency matrix">
                <thead><tr><th />{ids.map((c) => <th key={c} scope="col">{c}</th>)}</tr></thead>
                <tbody>
                  {ids.map((r) => (
                    <tr key={r} onMouseEnter={() => setFocus(r)} onMouseLeave={() => setFocus(null)}>
                      <th scope="row" className={focus === r ? 'hl' : ''}>{r}</th>
                      {ids.map((c) => {
                        const one = adj[r].includes(c)
                        return <td key={c} className={[one && 'one', focus === r && 'hl-row'].filter(Boolean).join(' ')}>{one ? 1 : 0}</td>
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="faint tiny" style={{ marginTop: 6 }}>Row = from, column = to.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

const LETTERS = 'ABCDEFGH'

/** Push/pop (or enqueue/dequeue) letters to feel the difference between LIFO and FIFO. */
function ToyFigure({ mode }: { mode: 'stack' | 'queue' }) {
  const [items, setItems] = useState<string[]>([])
  const [n, setN] = useState(0)
  const [note, setNote] = useState<string | null>(null)
  const next = LETTERS[n % LETTERS.length]
  const full = items.length >= 5
  const stack = mode === 'stack'

  const add = () => {
    setItems((xs) => [...xs, next])
    setN((k) => k + 1)
    setNote(`${stack ? 'Pushed' : 'Enqueued'} ${next} ${stack ? 'onto the top' : 'at the back'}.`)
  }
  const remove = () => {
    if (!items.length) return
    const out = stack ? items[items.length - 1] : items[0]
    setItems((xs) => (stack ? xs.slice(0, -1) : xs.slice(1)))
    setNote(stack ? `Popped ${out}: it was the last one in.` : `Dequeued ${out}: it had waited longest.`)
  }

  return (
    <div className="stack-v">
      {stack ? <StackPanel items={items} title="Stack" plain /> : <QueuePanel items={items} title="Queue (front → back)" />}
      <div className="controls" style={{ marginTop: 0 }}>
        <button className="btn primary" onClick={add} disabled={full}>
          <Icon name={stack ? 'arrowUp' : 'arrowRight'} /> {stack ? 'Push' : 'Enqueue'} {next}
        </button>
        <button className="btn" onClick={remove} disabled={!items.length}>{stack ? 'Pop' : 'Dequeue'}</button>
        <span className="spacer" />
        <button className="btn ghost sm" onClick={() => { setItems([]); setN(0); setNote(null) }} aria-label="Reset"><Icon name="restart" size={16} /> Reset</button>
      </div>
      <p className="small muted" aria-live="polite" style={{ minHeight: 21 }}>
        {note ?? (stack ? 'Push a few letters, then pop. Which one comes off?' : 'Enqueue a few letters, then dequeue. Which one leaves?')}
      </p>
    </div>
  )
}

function StepControls({ i, last, setI }: { i: number; last: number; setI: (f: (x: number) => number) => void }) {
  return (
    <div className="controls" style={{ marginTop: 8 }}>
      <button className="btn sm" onClick={() => setI(() => 0)} aria-label="Back to start"><Icon name="restart" size={16} /></button>
      <button className="btn sm" onClick={() => setI((x) => Math.max(0, x - 1))} disabled={i === 0} aria-label="Previous step"><Icon name="prev" size={16} /></button>
      <button className="btn sm primary" onClick={() => setI((x) => Math.min(last, x + 1))} disabled={i === last}>
        Next step <Icon name="next" size={16} />
      </button>
      <span className="stat" style={{ marginLeft: 'auto' }}>Step <b>{i + 1}</b>/{last + 1}</span>
    </div>
  )
}

function DfsStepper({ g, start }: { g: GraphSpec; start: string }) {
  const events = useMemo(() => dfsTrace(g, start), [g, start])
  const [i, setI] = useState(0)
  const vis = traceVisuals(g, events, i, start)
  const ev = events[i]
  const n = narrate(g, events, i)
  const nodeMarks = { ...vis.nodeMarks }
  if (ev.kind === 'backtrack') addMark(nodeMarks, [ev.node], 'deadend')
  return (
    <div className="stack-v" style={{ gap: 10 }}>
      <GraphCanvas graph={g} nodeMarks={nodeMarks} edgeMarks={vis.edgeMarks} thread={vis.thread} badges={vis.badges} maxHeight={260}
        ariaLabel={`DFS step ${i + 1}: ${n.title}`} />
      <StepControls i={i} last={events.length - 1} setI={setI} />
      <div className={`fig-narration ${ev.kind === 'backtrack' ? 'warn' : ''}`} aria-live="polite">
        <b>{n.title}.</b> {n.body}
      </div>
      <div className="fig-panels">
        <StackPanel items={ev.stack} title="Stack" deadEnd={false} />
        <VisitedStrip order={ev.visited} total={g.nodes.length} />
      </div>
    </div>
  )
}

function BfsStepper({ g, start }: { g: GraphSpec; start: string }) {
  const steps = useMemo(() => bfsTrace(g, start), [g, start])
  const adj = useMemo(() => adjacency(g), [g])
  const [i, setI] = useState(0)
  const discoveries = steps.slice(0, i + 1).filter((s) => s.kind === 'discover')
  const now = steps[i]
  const nodeMarks: Record<string, NodeMark[]> = {}
  const edgeMarks: Record<string, EdgeMark[]> = {}
  for (const s of discoveries) {
    nodeMarks[s.node] = ['visited']
    if (s.from) edgeMarks[edgeId(g, s.from, s.node)] = ['traversed']
  }
  const processing = now.kind === 'dequeue' ? now.node : now.kind === 'discover' ? now.from : null
  if (processing) addMark(nodeMarks, [processing], 'hint')
  if (now.kind === 'discover') addMark(nodeMarks, [now.node], 'current')
  const badges = Object.fromEntries(discoveries.map((s, k) => [s.node, { text: k + 1, tone: 'chalk' as const }]))
  let title: string
  let body: string
  if (now.kind === 'complete') {
    title = 'BFS complete'
    body = 'The queue is empty and every reachable vertex has been processed. BFS is finished.'
  } else if (now.kind === 'dequeue') {
    const unvisited = adj[now.node].filter((n) => !now.visited.includes(n))
    title = `Dequeue ${now.node}`
    body = `${now.node} leaves the front of the queue. ${unvisited.length
      ? `Now examine its unvisited neighbours, ${listJoin(unvisited)}, in alphabetical order.`
      : 'It has no unvisited neighbours, so no new vertices are added.'}`
  } else {
    title = `Visit ${now.node}`
    body = now.from
      ? `${now.node} is an unvisited neighbour of ${now.from} (level ${now.level}). Mark it visited and enqueue it at the back.`
      : `Start at ${now.node}: mark it visited and enqueue it.`
  }
  return (
    <div className="stack-v" style={{ gap: 10 }}>
      <GraphCanvas graph={g} nodeMarks={nodeMarks} edgeMarks={edgeMarks} badges={badges} maxHeight={260}
        ariaLabel={`BFS step ${i + 1}: ${title}`} />
      <StepControls i={i} last={steps.length - 1} setI={setI} />
      <div className="fig-narration" aria-live="polite"><b>{title}.</b> {body}</div>
      <div className="fig-panels">
        <QueuePanel items={now.queue} title="Queue (front → back)" />
        <VisitedStrip order={now.visited} total={g.nodes.length} />
      </div>
      <p className="faint tiny">Blue ring = the vertex being processed. A dequeue does not add another visit.</p>
    </div>
  )
}

/** The same graph twice, numbered in DFS order and in BFS order. */
function OrdersFigure({ g, start }: { g: GraphSpec; start: string }) {
  const orders = [
    { name: 'DFS', sub: 'stack: newest first', order: dfsOrder(g, start), color: 'var(--thread)', tone: 'gold' as const },
    { name: 'BFS', sub: 'queue: oldest first', order: bfsOrder(g, start), color: 'var(--hint)', tone: 'chalk' as const },
  ]
  return (
    <div className="fig-graphs n2">
      {orders.map((o) => (
        <figure key={o.name}>
          <div className="row small" style={{ justifyContent: 'center', marginBottom: 4 }}>
            <b style={{ color: o.color }}>{o.name}</b><span className="faint">{o.sub}</span>
          </div>
          <GraphCanvas graph={g} maxHeight={240}
            badges={Object.fromEntries(o.order.map((v, k) => [v, { text: k + 1, tone: o.tone }]))}
            ariaLabel={`${o.name} visits ${o.order.join(', ')}`} />
          <figcaption className="mono">{o.order.join(' → ')}</figcaption>
        </figure>
      ))}
    </div>
  )
}
