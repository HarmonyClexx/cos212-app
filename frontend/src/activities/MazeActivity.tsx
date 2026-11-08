// Module 0 - problem-centred activation (Merrill; Gagné event 3).
// Learners explore a fog-of-war labyrinth with only a thread and chalk. Afterwards the map is
// revealed as a graph and each tool is named: rooms = vertices, corridors = edges,
// chalk = visited set, thread = stack. They did DFS before anyone said "DFS".

import { useMemo, useState } from 'react'
import { useSubmitActivity } from '../api/hooks'
import { GraphCanvas, type EdgeMark, type NodeMark } from '../components/GraphCanvas'
import { Icon } from '../components/Icon'
import { FeedbackBox } from '../components/bits'
import { adjacency, edgeId } from '../engine/graph'
import type { ActivityProps } from './shared'

export function MazeActivity({ activity, onReward }: ActivityProps) {
  const g = activity.config.graph!
  const start = activity.config.start!
  const goal = activity.config.goal!
  const adj = useMemo(() => adjacency(g), [g])
  const [path, setPath] = useState<string[]>([start])
  const [thread, setThread] = useState<string[]>([start])
  const [found, setFound] = useState(false)
  const [revealed, setRevealed] = useState(false)
  const [note, setNote] = useState<string>('You stand at the entrance. Corridors lead off into the dark…')
  const submit = useSubmitActivity(activity.id)

  const here = path[path.length - 1]
  const chalk = useMemo(() => new Set(path), [path])
  const revisits = path.length - chalk.size

  const move = (to: string) => {
    if (found || !adj[here].includes(to)) return
    const back = thread.length >= 2 && thread[thread.length - 2] === to
    const idx = thread.indexOf(to)
    const nextThread = back ? thread.slice(0, -1) : idx >= 0 ? thread.slice(0, idx + 1) : [...thread, to]
    setThread(nextThread)
    setPath((p) => [...p, to])
    if (to === goal) {
      setFound(true)
      setNote('You found the lair! The thread leads straight back to the entrance.')
      return
    }
    const fresh = adj[to].filter((n) => !chalk.has(n) && n !== to)
    if (back) setNote(`You follow your thread back to ${to}.`)
    else if (chalk.has(to)) setNote(`Chalk on the wall… you've been in this room before. Going round in circles?`)
    else if (fresh.length === 0) setNote('A dead end. Every door here leads somewhere you have already marked. Wind your thread back.')
    else setNote(`New room. You mark it with chalk. ${adj[to].length} door${adj[to].length === 1 ? '' : 's'} here.`)
  }

  // Fog of war: you see rooms you've been in, plus the doors out of them.
  const visible = new Set<string>()
  for (const n of chalk) {
    visible.add(n)
    for (const m of adj[n]) visible.add(m)
  }
  const hiddenNodes = revealed ? undefined : new Set(g.nodes.map((n) => n.id).filter((n) => !visible.has(n)))
  const hiddenEdges = revealed ? undefined : new Set(
    g.edges.filter(([u, v]) => !chalk.has(u) && !chalk.has(v)).map(([u, v]) => edgeId(g, u, v)),
  )

  const nodeMarks: Record<string, NodeMark[]> = {}
  const labels: Record<string, string> = {}
  for (const { id } of g.nodes) {
    const m: NodeMark[] = []
    if (chalk.has(id)) m.push('visited')
    else if (!revealed) { m.push('fog'); labels[id] = '?' }
    if (thread.includes(id)) m.push('stack')
    if (id === here && !revealed) m.push('current')
    if (id === goal && (chalk.has(id) || revealed)) m.push('goal')
    if (id === start) m.push('start')
    nodeMarks[id] = m
  }
  const edgeMarks: Record<string, EdgeMark[]> = {}
  for (const [u, v] of g.edges) if (!revealed && !(chalk.has(u) && chalk.has(v))) edgeMarks[edgeId(g, u, v)] = ['fog']

  const claim = () =>
    submit.mutate({ data: { path } }, {
      onSuccess: ({ reward }) => onReward(reward, { graded: false, subtitle: `You escaped in ${path.length - 1} moves. Now let's name what you just did.` }),
    })

  return (
    <div className="act-grid wide-side">
      <div className="stage maze-stage">
        <div className="stage-head">
          <div className="prompt" style={{ flex: 1 }}>
            {revealed ? 'The Labyrinth was a graph all along.' : found ? 'The lair! Now look at what you were holding…' : <>Find the Minotaur's lair. Click a <b>doorway</b> next to you to move.</>}
          </div>
          <div className="hud-row">
            <span className="stat"><Icon name="footprints" size={14} /> <b>{path.length - 1}</b> moves</span>
            <span className="stat"><Icon name="check" size={14} /> <b>{chalk.size}</b> rooms</span>
            {revisits > 0 && <span className="stat"><Icon name="repeat" size={14} /> <b>{revisits}</b> revisits</span>}
          </div>
        </div>
        <GraphCanvas
          graph={g}
          nodeMarks={nodeMarks}
          edgeMarks={edgeMarks}
          thread={thread}
          labels={revealed ? {} : labels}
          hiddenNodes={hiddenNodes}
          hiddenEdges={hiddenEdges}
          onNodeClick={move}
          nodeClickable={(id) => !found && adj[here].includes(id)}
          ariaLabel="The labyrinth. Rooms adjacent to you can be clicked."
          maxHeight={520}
        />
        <div style={{ marginTop: 12 }}>
          <FeedbackBox fb={{ tone: found ? 'good' : 'info', tier: 0, title: found ? 'The lair!' : `Room ${here}`, body: note }} />
        </div>
        {!found && (
          <div className="controls">
            <button className="btn ghost" onClick={() => { setPath([start]); setThread([start]); setNote('Back at the entrance. Try again.') }}>
              <Icon name="restart" /> Start over
            </button>
          </div>
        )}
      </div>

      <div className="stack-v">
        {!found ? (
          <div className="card flat">
            <div className="card-title"><Icon name="spool" size={18} /> Your tools</div>
            <ul className="checklist">
              <li className="done"><span className="box"><Icon name="check" size={14} /></span><span><b style={{ color: 'var(--thread)' }}>Golden thread</b> — unrolls behind you. Walk back along it and it winds up again.</span></li>
              <li className="done"><span className="box"><Icon name="check" size={14} /></span><span><b style={{ color: 'var(--chalk)' }}>Chalk</b> — every room you enter gets marked, so you'll know if you come back.</span></li>
            </ul>
            <p className="small muted" style={{ marginTop: 12 }}>
              Strategy tip from Ariadne: <em>take any corridor you haven't tried; at a dead end, follow your thread back to the last room with an untried door.</em>
            </p>
          </div>
        ) : (
          <div className="card flat">
            <div className="card-title"><Icon name="sparkles" size={18} /> What you just did</div>
            {!revealed ? (
              <>
                <p className="muted small">Those tools have names in computer science. Ready?</p>
                <button className="btn primary block" style={{ marginTop: 12 }} onClick={() => setRevealed(true)}>
                  <Icon name="eye" /> Reveal the map
                </button>
              </>
            ) : (
              <>
                <div className="reveal-map">
                  <div><div className="k"><Icon name="door" size={16} /> Rooms</div><div className="small muted">are <b>vertices</b> (nodes)</div></div>
                  <div><div className="k"><Icon name="nodes" size={16} /> Corridors</div><div className="small muted">are <b>edges</b></div></div>
                  <div><div className="k" style={{ color: 'var(--chalk)' }}><Icon name="check" size={16} /> Chalk</div><div className="small muted">is the <b>visited set</b></div></div>
                  <div><div className="k" style={{ color: 'var(--thread)' }}><Icon name="spool" size={16} /> Thread</div><div className="small muted">is the <b>stack</b></div></div>
                </div>
                <p className="small" style={{ marginTop: 12 }}>
                  Going deep and winding back at dead ends is <b>depth-first search</b>. The rest of this course makes that precise.
                </p>
                <button className="btn gold block" style={{ marginTop: 14 }} onClick={claim} disabled={submit.isPending}>
                  <Icon name="trophy" /> Claim your reward
                </button>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
