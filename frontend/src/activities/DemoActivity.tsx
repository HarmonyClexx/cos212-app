// Gagné event 4 / Merrill demonstration: watch DFS step by step before doing it yourself.

import { useEffect, useMemo, useReducer, useRef, useState } from 'react'
import { useSubmitActivity } from '../api/hooks'
import { StackPanel, VisitedStrip } from '../components/DataStructures'
import { GraphCanvas } from '../components/GraphCanvas'
import { Icon } from '../components/Icon'
import { FeedbackBox } from '../components/bits'
import { adjacency, dfsTrace } from '../engine/graph'
import { demoCheckpoints, demoTransition, initialDemoState, type DemoAction, type DemoState } from '../engine/demo'
import { narrate } from '../engine/tracer'
import { addMark, traceVisuals, type ActivityProps } from './shared'

export function DemoActivity({ activity, onReward }: ActivityProps) {
  const g = activity.config.graph!
  const start = activity.config.start!
  const events = useMemo(() => dfsTrace(g, start), [g, start])
  const checkpoints = useMemo(() => demoCheckpoints(g, events), [g, events])
  const [state, dispatch] = useReducer(
    (s: DemoState, a: DemoAction) => demoTransition(g, events, checkpoints, s, a),
    initialDemoState,
  )
  const { i, playing, seenEnd, pending, feedback } = state
  const [speed, setSpeed] = useState(1)
  const predictionHeading = useRef<HTMLHeadingElement>(null)
  const predictionFeedback = useRef<HTMLDivElement>(null)
  const submit = useSubmitActivity(activity.id)
  const last = events.length - 1

  useEffect(() => {
    if (!playing) return
    const t = setTimeout(() => dispatch({ type: 'next', automaticAt: i }), 1700 / speed)
    return () => clearTimeout(t)
  }, [playing, i, speed])

  useEffect(() => {
    if (pending !== null) predictionHeading.current?.focus()
    else if (feedback) predictionFeedback.current?.focus()
  }, [pending, feedback])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target
      if (!(target instanceof HTMLElement) || target.closest('input,select,textarea,[contenteditable],dialog')) return
      if (e.altKey || e.ctrlKey || e.metaKey) return
      if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
        e.preventDefault()
        dispatch({ type: e.key === 'ArrowRight' ? 'next' : 'previous' })
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const vis = traceVisuals(g, events, i, start)
  const ev = events[i]
  const n = narrate(g, events, i)
  const isBack = ev.kind === 'backtrack'
  const nodeMarks = { ...vis.nodeMarks }
  if (isBack) addMark(nodeMarks, [ev.node], 'deadend')

  const focusBack = activity.config.focus === 'backtracking'
  const current = ev.stack.at(-1)
  const neighbours = current ? adjacency(g)[current] : []

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

        {pending !== null && (
          <section className="card flat demo-prediction" aria-label="DFS prediction">
            <h3 ref={predictionHeading} tabIndex={-1}>Predict the next action from {current}</h3>
            <p className="small muted">Ungraded practice: choose a prediction or skip and reveal. Neither changes your score or rewards.</p>
            <div className="controls">
              {neighbours.map((node) => (
                <button key={node} className="btn" onClick={() => dispatch({ type: 'answer', node })}>Visit {node}</button>
              ))}
              <button className="btn" onClick={() => dispatch({ type: 'answer', node: null })}>Backtrack (pop)</button>
              <button className="btn primary" onClick={() => dispatch({ type: 'reveal' })}>Skip / reveal</button>
            </div>
          </section>
        )}
        <div ref={predictionFeedback} tabIndex={feedback ? -1 : undefined}>
          <FeedbackBox fb={feedback} />
        </div>
        <div className="controls">
          <button className="btn" onClick={() => dispatch({ type: 'restart' })} aria-label="Back to start"><Icon name="restart" /></button>
          <button className="btn" onClick={() => dispatch({ type: 'previous' })} disabled={i === 0} aria-label="Previous step"><Icon name="prev" /></button>
          <button className="btn primary" onClick={() => dispatch({ type: 'play' })} disabled={pending !== null} style={{ minWidth: 110 }}>
            <Icon name={playing ? 'pause' : 'play'} /> {playing ? 'Pause' : i >= last ? 'Replay' : 'Play'}
          </button>
          <button className="btn" onClick={() => dispatch({ type: 'next' })} disabled={i === last || pending !== null} aria-label="Next step"><Icon name="next" /></button>
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
        <p className="faint tiny" style={{ marginTop: 8 }}>Tip: use ← and → to step. At a prediction, answer or Skip / reveal to continue. Play resumes autoplay.</p>
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
