// Storyboard Frame 1: interactive canvas + inspector panel. Click vertices and edges to reveal
// what they are; a discovery checklist turns "reading definitions" into exploration.

import { useMemo, useState } from 'react'
import { useSubmitActivity } from '../api/hooks'
import { Checklist, useChecklistHint } from '../components/Checklist'
import { GraphCanvas, type EdgeMark, type NodeMark } from '../components/GraphCanvas'
import { Icon } from '../components/Icon'
import { HintButton } from '../components/bits'
import { adjacency, listJoin } from '../engine/graph'
import type { ActivityProps } from './shared'

type Sel = { type: 'node'; id: string } | { type: 'edge'; id: string } | null

const CHECKS = [
  { id: 'vertex', text: 'Inspect a vertex' },
  { id: 'edge', text: 'Inspect an edge' },
  { id: 'directed', text: 'Switch to the directed version' },
  { id: 'directed-edge', text: 'Inspect a directed edge' },
  { id: 'degree', text: 'Find the vertex with the highest degree' },
]

export function InspectActivity({ activity, onReward }: ActivityProps) {
  const undirected = activity.config.graph!
  const directed = activity.config.directed_graph!
  const [isDirected, setIsDirected] = useState(false)
  const [sel, setSel] = useState<Sel>(null)
  const [found, setFound] = useState<Set<string>>(new Set())
  const submit = useSubmitActivity(activity.id)

  const g = isDirected ? directed : undirected
  const adj = useMemo(() => adjacency(g), [g])
  const undirAdj = useMemo(() => adjacency(undirected), [undirected])
  const maxDeg = Math.max(...Object.values(undirAdj).map((v) => v.length))

  const discover = (...ids: string[]) => setFound((f) => new Set([...f, ...ids]))

  const pickNode = (id: string) => {
    setSel({ type: 'node', id })
    discover('vertex')
    if (!isDirected && undirAdj[id].length === maxDeg) discover('degree')
  }
  const pickEdge = (id: string) => {
    setSel({ type: 'edge', id })
    discover(isDirected ? 'directed-edge' : 'edge')
  }
  const toggle = (d: boolean) => {
    setIsDirected(d)
    setSel(null)
    if (d) discover('directed')
  }

  const nodeMarks: Record<string, NodeMark[]> = {}
  const edgeMarks: Record<string, EdgeMark[]> = {}
  if (sel?.type === 'node') {
    nodeMarks[sel.id] = ['selected']
    for (const n of adj[sel.id]) nodeMarks[n] = ['hint']
  }
  if (sel?.type === 'edge') {
    edgeMarks[sel.id] = ['selected']
    for (const n of sel.id.split(/->|-/)) nodeMarks[n] = ['hint']
  }

  const allDone = CHECKS.every((c) => found.has(c.id))

  // Free hints for the next discovery: a tip, then (for the degree hunt) a ring on the answer.
  const hint = useChecklistHint(CHECKS, found, (id) => (id === 'degree' ? 2 : 1))
  const busiest = Object.keys(undirAdj).filter((n) => undirAdj[n].length === maxDeg)
  const tips: Record<string, string> = {
    vertex: 'Click any circle on the graph. The Inspector on the right explains what it is.',
    edge: isDirected ? 'Switch back to Undirected (above the graph), then click one of the lines.' : 'Click one of the lines joining two circles — not a circle this time.',
    directed: 'Use the Undirected / Directed switch above the graph.',
    'directed-edge': isDirected ? 'Click one of the arrows, and notice which way it points.' : 'Switch to Directed first, then click one of the arrows.',
    degree: isDirected ? 'Degree is counted on the undirected graph: switch back to Undirected first.'
      : hint.level >= 2 ? `I've ringed it: ${busiest.join(' and ')} has the most lines meeting at it. Click it to see its degree.`
        : 'A vertex’s degree is the number of lines touching it. Click the vertex where the most lines meet.',
  }
  const tabsCue = hint.level > 0 && (
    hint.next === 'directed' || (hint.next === 'edge' && isDirected) || (hint.next === 'degree' && isDirected)
    || (hint.next === 'directed-edge' && !isDirected))
  if (hint.next === 'degree' && hint.level >= 2 && !isDirected) for (const n of busiest) nodeMarks[n] = [...(nodeMarks[n] ?? []), 'hint']

  return (
    <div className="act-grid wide-side">
      <div className="stage">
        <div className="stage-head">
          <div className="prompt" style={{ flex: 1 }}>Click any <b>vertex</b> (circle) or <b>edge</b> (line) to inspect it.</div>
          <div className={`tabs ${tabsCue ? 'nudge' : ''}`} role="tablist" aria-label="Graph type" style={{ width: 240 }}>
            <button role="tab" aria-selected={!isDirected} className={!isDirected ? 'active' : ''} onClick={() => toggle(false)}>Undirected</button>
            <button role="tab" aria-selected={isDirected} className={isDirected ? 'active' : ''} onClick={() => toggle(true)}>Directed</button>
          </div>
        </div>
        <GraphCanvas graph={g} nodeMarks={nodeMarks} edgeMarks={edgeMarks} onNodeClick={pickNode} onEdgeClick={pickEdge} />
      </div>

      <div className="stack-v">
        <div className="card flat" aria-live="polite">
          <div className="card-title"><Icon name="eye" size={18} /> Inspector</div>
          {!sel && <p className="muted small">Nothing selected yet. Click part of the graph.</p>}
          {sel?.type === 'node' && (
            <div className="stack-v" style={{ gap: 8 }}>
              <div className="row"><span className="chip brand">Vertex</span><h3>{sel.id}</h3></div>
              <p className="small muted">A <b>vertex</b> (or node) is a single item in a graph — a room in the labyrinth.</p>
              {!isDirected ? (
                <>
                  <div className="small"><b>Degree:</b> {adj[sel.id].length} — the number of edges touching {sel.id}.</div>
                  <div className="small"><b>Neighbours:</b> {listJoin(adj[sel.id])}</div>
                </>
              ) : (
                <>
                  <div className="small"><b>Out-degree:</b> {adj[sel.id].length} {adj[sel.id].length ? `→ ${listJoin(adj[sel.id])}` : ''}</div>
                  <div className="small"><b>In-degree:</b> {g.edges.filter(([, v]) => v === sel.id).length}{' '}
                    {g.edges.filter(([, v]) => v === sel.id).length ? `← ${listJoin(g.edges.filter(([, v]) => v === sel.id).map(([u]) => u))}` : ''}</div>
                  <p className="small faint">In a directed graph, we count arrows leaving and arriving separately.</p>
                </>
              )}
            </div>
          )}
          {sel?.type === 'edge' && (() => {
            const [u, v] = sel.id.split(/->|-/)
            return (
              <div className="stack-v" style={{ gap: 8 }}>
                <div className="row"><span className="chip brand">{isDirected ? 'Directed edge' : 'Edge'}</span><h3>{isDirected ? `${u} → ${v}` : `${u} – ${v}`}</h3></div>
                {isDirected
                  ? <p className="small muted">A <b>directed edge</b> is a one-way street: you may travel from <b>{u}</b> to <b>{v}</b>, but <b>not</b> back.</p>
                  : <p className="small muted">An <b>edge</b> connects two vertices. In an undirected graph it works both ways: {u} and {v} are <b>adjacent</b> (neighbours).</p>}
              </div>
            )
          })()}
        </div>

        <div className="card flat">
          <div className="card-title"><Icon name="target" size={18} /> Discoveries <span className="faint small">{found.size}/{CHECKS.length}</span></div>
          <Checklist items={CHECKS} done={found} tipFor={hint.level ? hint.next : null} tip={hint.next ? tips[hint.next] : undefined} />
          {!allDone && (
            <div className="row" style={{ marginTop: 12 }}>
              <HintButton small level={hint.level} max={hint.max} onClick={hint.ask} nudge={hint.nudge} label="Stuck? Hint" />
            </div>
          )}
          <button className="btn gold block" style={{ marginTop: 14 }} disabled={!allDone || submit.isPending}
            onClick={() => submit.mutate({ data: { discovered: [...found] } }, { onSuccess: ({ reward }) => onReward(reward, { graded: false, subtitle: 'You know your vertices from your edges.' }) })}>
            <Icon name="check" /> Finish exploring
          </button>
        </div>
      </div>
    </div>
  )
}
