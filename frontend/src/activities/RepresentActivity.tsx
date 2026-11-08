// Objective 2 lesson: one graph, three linked views. Hovering anything highlights the
// corresponding row of the adjacency list and the row/column of the matrix.

import { useMemo, useState } from 'react'
import { useSubmitActivity } from '../api/hooks'
import { GraphCanvas, type EdgeMark, type NodeMark } from '../components/GraphCanvas'
import { Icon } from '../components/Icon'
import { adjacency } from '../engine/graph'
import type { ActivityProps } from './shared'

type Focus = { type: 'node'; id: string } | { type: 'edge'; u: string; v: string } | null

const CHECKS = [
  { id: 'node', text: 'Hover a vertex and find its row' },
  { id: 'edge', text: 'Hover an edge and find both its matrix cells' },
  { id: 'directed', text: 'Switch to directed' },
  { id: 'asym', text: 'Hover a directed edge — spot the lonely 1' },
]

export function RepresentActivity({ activity, onReward }: ActivityProps) {
  const [directed, setDirected] = useState(false)
  const g = directed ? activity.config.directed_graph! : activity.config.graph!
  const adj = useMemo(() => adjacency(g), [g])
  const ids = g.nodes.map((n) => n.id)
  const [focus, setFocus] = useState<Focus>(null)
  const [done, setDone] = useState<Set<string>>(new Set())
  const submit = useSubmitActivity(activity.id)
  const tick = (id: string) => setDone((d) => (d.has(id) ? d : new Set([...d, id])))

  const onNode = (id: string | null) => {
    setFocus(id ? { type: 'node', id } : null)
    if (id) tick('node')
  }
  const onEdge = (eid: string | null) => {
    if (!eid) return setFocus(null)
    const [u, v] = eid.split(/->|-/)
    setFocus({ type: 'edge', u, v })
    tick(directed ? 'asym' : 'edge')
  }

  const nodeMarks: Record<string, NodeMark[]> = {}
  const edgeMarks: Record<string, EdgeMark[]> = {}
  const rowHl = new Set<string>()
  const cellHl = new Set<string>()
  if (focus?.type === 'node') {
    nodeMarks[focus.id] = ['hover']
    rowHl.add(focus.id)
    for (const n of adj[focus.id]) cellHl.add(`${focus.id}${n}`)
  } else if (focus?.type === 'edge') {
    nodeMarks[focus.u] = ['hover']
    nodeMarks[focus.v] = ['hover']
    edgeMarks[directed ? `${focus.u}->${focus.v}` : [focus.u, focus.v].sort().join('-')] = ['hover']
    rowHl.add(focus.u)
    cellHl.add(`${focus.u}${focus.v}`)
    if (!directed) { rowHl.add(focus.v); cellHl.add(`${focus.v}${focus.u}`) }
  }
  const hlNbr = (row: string, n: string) => focus?.type === 'edge' && ((row === focus.u && n === focus.v) || (!directed && row === focus.v && n === focus.u))

  return (
    <div className="stack-v" style={{ gap: 18 }}>
      <div className="act-grid wide-side">
        <div className="stage">
          <div className="stage-head">
            <div className="prompt" style={{ flex: 1 }}>Hover (or tap) the drawing — watch the list and matrix.</div>
            <div className="tabs" style={{ width: 240 }}>
              <button className={!directed ? 'active' : ''} onClick={() => { setDirected(false); setFocus(null) }}>Undirected</button>
              <button className={directed ? 'active' : ''} onClick={() => { setDirected(true); setFocus(null); tick('directed') }}>Directed</button>
            </div>
          </div>
          <GraphCanvas graph={g} nodeMarks={nodeMarks} edgeMarks={edgeMarks}
            onNodeHover={onNode} onEdgeHover={onEdge} onNodeClick={(id) => onNode(id)} onEdgeClick={(id) => onEdge(id)} maxHeight={360} />
        </div>
        <div className="stack-v">
          <div className="card flat">
            <div className="card-title"><Icon name="layers" size={18} /> Adjacency list</div>
            <div className="list-view">
              {ids.map((r) => (
                <div key={r} className={`lrow ${rowHl.has(r) ? 'hl' : ''}`} onMouseEnter={() => onNode(r)} onMouseLeave={() => onNode(null)}>
                  <span className="k">{r}</span><span className="faint">→</span>
                  <span className="v">{adj[r].length ? adj[r].map((n) => <span key={n} className={hlNbr(r, n) ? 'hl' : ''}>{n}</span>) : <span className="faint">∅</span>}</span>
                </div>
              ))}
            </div>
            <p className="faint tiny" style={{ marginTop: 8 }}>Each row lists the vertices you can reach in one step.</p>
          </div>
        </div>
      </div>

      <div className="act-grid wide-side">
        <div className="card flat" style={{ overflowX: 'auto' }}>
          <div className="card-title"><Icon name="table" size={18} /> Adjacency matrix <span className="faint small">row → column</span></div>
          <table className="matrix" aria-label="Adjacency matrix">
            <thead><tr><th />{ids.map((c) => <th key={c} scope="col" className={rowHl.has(c) && !directed ? 'hl' : ''}>{c}</th>)}</tr></thead>
            <tbody>
              {ids.map((r) => (
                <tr key={r}>
                  <th scope="row" className={rowHl.has(r) ? 'hl' : ''}>{r}</th>
                  {ids.map((c) => {
                    const one = adj[r].includes(c)
                    return <td key={c} className={[one && 'one', cellHl.has(`${r}${c}`) && 'hl', rowHl.has(r) && 'hl-row'].filter(Boolean).join(' ')}>{one ? 1 : 0}</td>
                  })}
                </tr>
              ))}
            </tbody>
          </table>
          <p className="small muted" style={{ marginTop: 10 }}>
            {directed
              ? 'Directed: an arrow u → v sets only M[u][v]. The matrix is no longer a mirror image.'
              : 'Undirected: every edge sets two cells, so the matrix is symmetric about its diagonal.'}
          </p>
        </div>
        <div className="card flat">
          <div className="card-title"><Icon name="target" size={18} /> Spot it <span className="faint small">{done.size}/{CHECKS.length}</span></div>
          <ul className="checklist">
            {CHECKS.map((c) => <li key={c.id} className={done.has(c.id) ? 'done' : ''}><span className="box">{done.has(c.id) && <Icon name="check" size={14} />}</span>{c.text}</li>)}
          </ul>
          <button className="btn gold block" style={{ marginTop: 14 }} disabled={done.size < CHECKS.length || submit.isPending}
            onClick={() => submit.mutate({ data: { explored: [...done] } }, { onSuccess: ({ reward }) => onReward(reward, { graded: false, subtitle: 'Next: build these yourself.' }) })}>
            <Icon name="check" /> Got it
          </button>
        </div>
      </div>
    </div>
  )
}
