// Gagné event 4 / Merrill demonstration: watch DFS step by step before doing it yourself.

import { useEffect, useMemo, useState } from 'react'
import { useSubmitActivity } from '../api/hooks'
import { StackPanel, VisitedStrip } from '../components/DataStructures'
import { GraphCanvas } from '../components/GraphCanvas'
import { Icon } from '../components/Icon'
import { FeedbackBox } from '../components/bits'
import { dfsTrace } from '../engine/graph'
import { narrate } from '../engine/tracer'
import { addMark, traceVisuals, type ActivityProps } from './shared'

export function DemoActivity({ activity, onReward }: ActivityProps) {
  const g = activity.config.graph!
  const start = activity.config.start!
  const events = useMemo(() => dfsTrace(g, start), [g, start])
  const [i, setI] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(1)
  const [seenEnd, setSeenEnd] = useState(false)
  const submit = useSubmitActivity(activity.id)
  const last = events.length - 1

  useEffect(() => {
    if (!playing) return
    if (i >= last) { setPlaying(false); return }
    const t = setTimeout(() => setI((x) => x + 1), 1700 / speed)
    return () => clearTimeout(t)
  }, [playing, i, last, speed])

  useEffect(() => { if (i === last) setSeenEnd(true) }, [i, last])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement).tagName === 'INPUT') return
      if (e.key === 'ArrowRight') setI((x) => Math.min(last, x + 1))
      if (e.key === 'ArrowLeft') setI((x) => Math.max(0, x - 1))
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [last])

  const vis = traceVisuals(g, events, i, start)
  const ev = events[i]
  const n = narrate(g, events, i)
  const isBack = ev.kind === 'backtrack'
  const nodeMarks = { ...vis.nodeMarks }
  if (isBack) addMark(nodeMarks, [ev.node], 'deadend')

  const focusBack = activity.config.focus === 'backtracking'

  return (
    <div className="act-grid">
      <div className="stage">
        <div className="stage-head">
          <div className="prompt" style={{ flex: 1 }}>
            {focusBack ? 'Watch what happens at each dead end.' : 'Watch Ariadne’s rule: go deep, then back.'}
          </div>
          <span className="stat">Step <b>{i + 1}</b>/{events.length}</span>
        </div>
        <GraphCanvas graph={g} nodeMarks={nodeMarks} edgeMarks={vis.edgeMarks} thread={vis.thread} badges={vis.badges}
          ariaLabel={`DFS demonstration, step ${i + 1}: ${n.title}`} />

        <div className="controls">
          <button className="btn" onClick={() => setI(0)} aria-label="Back to start"><Icon name="restart" /></button>
          <button className="btn" onClick={() => setI((x) => Math.max(0, x - 1))} disabled={i === 0} aria-label="Previous step"><Icon name="prev" /></button>
          <button className="btn primary" onClick={() => { if (i >= last) setI(0); setPlaying((p) => !p) }} style={{ minWidth: 110 }}>
            <Icon name={playing ? 'pause' : 'play'} /> {playing ? 'Pause' : i >= last ? 'Replay' : 'Play'}
          </button>
          <button className="btn" onClick={() => setI((x) => Math.min(last, x + 1))} disabled={i === last} aria-label="Next step"><Icon name="next" /></button>
          <label className="row small muted" style={{ marginLeft: 6 }}>
            Speed
            <select className="input" style={{ height: 34, padding: '0 8px' }} value={speed} onChange={(e) => setSpeed(Number(e.target.value))}>
              <option value={0.5}>0.5×</option><option value={1}>1×</option><option value={2}>2×</option>
            </select>
          </label>
          <span className="spacer" />
          <button className="btn gold" disabled={!seenEnd || submit.isPending}
            title={seenEnd ? '' : 'Step through to the end first'}
            onClick={() => submit.mutate({ data: { watched: true } }, { onSuccess: ({ reward }) => onReward(reward, { graded: false, subtitle: 'Now try it yourself.' }) })}>
            <Icon name="check" /> I've got it
          </button>
        </div>
        <p className="faint tiny" style={{ marginTop: 8 }}>Tip: use ← and → to step.</p>
      </div>

      <div className="stack-v">
        <FeedbackBox fb={{ tone: isBack ? 'warn' : 'info', tier: 0, title: n.title, body: n.body }} />
        <div className="card flat"><StackPanel items={ev.stack} deadEnd={false} /></div>
        <div className="card flat"><VisitedStrip order={ev.visited} total={g.nodes.length} /></div>
        <div className="card flat small muted">
          <div className="card-title"><Icon name="info" size={16} /> The rule</div>
          <ol style={{ margin: 0, paddingLeft: 18, display: 'grid', gap: 6 }}>
            <li>Look at the vertex on <b style={{ color: 'var(--thread)' }}>top of the stack</b>.</li>
            <li>If it has an unvisited neighbour, visit the <b>alphabetically first</b> one: push it, chalk-mark it.</li>
            <li>Otherwise it's a <b style={{ color: 'var(--danger)' }}>dead end</b>: pop it (backtrack).</li>
            <li>Stop when the stack is empty.</li>
          </ol>
        </div>
      </div>
    </div>
  )
}
