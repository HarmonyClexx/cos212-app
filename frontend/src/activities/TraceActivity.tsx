// Storyboard Frames 3 & 4: "Start at Node A. Click the next node DFS will visit."
// The learner drives DFS; the stack, the visited set and the thread are externalised on screen
// (working-memory constraint from the UX analysis) and every slip gets tiered scaffolding.

import { useEffect, useMemo, useRef, useState } from 'react'
import { useSubmitActivity } from '../api/hooks'
import { StackPanel, VisitedStrip } from '../components/DataStructures'
import { GraphCanvas } from '../components/GraphCanvas'
import { Icon } from '../components/Icon'
import { FeedbackBox, HintButton } from '../components/bits'
import {
  applyAction, contextIndex, initTrace, isDone, type Feedback, type TraceAction, type TraceState,
} from '../engine/tracer'
import { useIdle } from '../lib/useIdle'
import { addMark, traceVisuals, type ActivityProps } from './shared'

const HINT_COST = 'Each hint costs a little: 3★ needs none, but 2★ stays in reach.'

export function TraceActivity({ activity, onReward }: ActivityProps) {
  const g = activity.config.graph!
  const start = activity.config.start!
  const auto = activity.config.auto_backtrack ?? true
  const assist = !auto && (activity.config.difficulty ?? 2) <= 2
  const [s, setS] = useState<TraceState>(() => initTrace(g, start, auto))
  const submit = useSubmitActivity(activity.id)
  const submitted = useRef(false)

  const target = contextIndex(s)
  const animating = s.shown < target
  const done = isDone(s)

  // Play out events the learner didn't have to click (auto-backtracks) one at a time.
  useEffect(() => {
    if (s.shown >= target) return
    const next = s.events[s.shown + 1]
    const t = setTimeout(() => setS((p) => ({ ...p, shown: p.shown + 1 })), next.kind === 'backtrack' ? 560 : 60)
    return () => clearTimeout(t)
  }, [s.shown, target, s.events])

  useEffect(() => {
    if (!done || animating || submitted.current) return
    submitted.current = true
    submit.mutate({ actions: s.log }, {
      onSuccess: ({ reward, result }) => {
        const r = result as { correct_steps: number; total_steps: number; mistakes: number; hints: number; reveals: number }
        onReward(reward, {
          graded: true,
          subtitle: `${r.correct_steps}/${r.total_steps} steps on your own · ${r.mistakes} mistake${r.mistakes === 1 ? '' : 's'} · ${r.hints} hint${r.hints === 1 ? '' : 's'}${r.reveals ? ` · ${r.reveals} shown` : ''}`,
        })
      },
      onError: () => { submitted.current = false },
    })
  }, [done, animating, s.log, submit, onReward])

  const act = (a: TraceAction) => {
    if (animating || done) return
    setS((p) => applyAction(g, p, a))
  }

  const vis = traceVisuals(g, s.events, s.shown, start)
  const expected = done ? null : s.events[s.required[s.pos]]
  const atDeadEnd = !animating && expected?.kind === 'backtrack'
  const showDeadEnd = !auto && atDeadEnd && (assist || s.wrongOnStep > 0)

  // Auto-backtrack narration while the animation plays
  const autoNote: Feedback | null = useMemo(() => {
    const e = s.events[s.shown]
    if (!auto || e.kind !== 'backtrack') return null
    const top = e.stack[e.stack.length - 1]
    return { tone: 'info', tier: 0, title: `${e.node} is a dead end — backtrack`,
             body: top ? `Popped ${e.node}. The thread winds back to ${top}.` : 'Stack empty: every reachable vertex is visited.' }
  }, [auto, s.events, s.shown])

  const assistNote: Feedback | null = showDeadEnd && s.wrongOnStep === 0
    ? { tone: 'info', tier: 0, title: 'No unvisited neighbours found.', body: `${vis.current} is a dead end. What action must DFS take?` }
    : null

  // Offer help rather than wait to be asked: after two slips on a step, or 20 s without a move.
  const idle = useIdle(20000, s.log.length, !done && !animating)
  const stuck = s.wrongOnStep >= 2 || idle
  const idleNote: Feedback | null = idle && (!s.feedback || s.feedback.tone === 'good')
    ? { tone: 'hint', tier: 0, title: 'Take your time — or take a hint',
        body: `Start from ${vis.current}, the vertex on top of the stack. Which of its neighbours has no chalk mark yet? If you're unsure, press Hint.` }
    : null

  const fb = (animating ? autoNote : null)
    ?? (s.feedback?.tone === 'good' && assistNote ? assistNote : null)
    ?? idleNote ?? s.feedback ?? assistNote

  const nodeMarks = { ...vis.nodeMarks }
  if (!animating) addMark(nodeMarks, s.feedback?.tone !== 'good' ? s.feedback?.highlight : undefined, 'hint')
  if (showDeadEnd) addMark(nodeMarks, [vis.current], 'deadend')

  const total = s.required.length
  const canReveal = !done && !animating && (s.wrongOnStep >= 3 || s.tier >= 3)
  const flash = s.flash ? { ...s.flash, nonce: s.log.length } : null

  return (
    <div className="act-grid">
      <div className="stage">
        <div className="stage-head">
          <div className="prompt" style={{ flex: 1, minWidth: 240 }}>
            {done ? 'Traversal complete!'
              : auto ? <>Start at <b>{start}</b>. Click the next vertex DFS will visit.</>
                : <>Click the next vertex DFS visits — or <b>Backtrack</b> at a dead end.</>}
          </div>
          <div className="hud-row">
            <span className="stat">Step <b>{Math.min(s.pos + 1, total)}</b>/{total}</span>
            <span className="stat"><Icon name="x" size={14} /> <b>{s.mistakes}</b></span>
            <span className="stat"><Icon name="bulb" size={14} /> <b>{s.hints}</b></span>
            {s.combo >= 2 && <span className="stat combo" key={s.combo}><Icon name="flame" size={14} /> <b>{s.combo}</b> streak</span>}
          </div>
        </div>

        <GraphCanvas
          graph={g}
          nodeMarks={nodeMarks}
          edgeMarks={vis.edgeMarks}
          thread={vis.thread}
          badges={vis.badges}
          flash={flash}
          onNodeClick={(id) => act({ kind: 'visit', node: id })}
          nodeClickable={() => !animating && !done}
          ariaLabel={`DFS practice graph. Current vertex ${vis.current ?? 'none'}.`}
        />

        <div className="legend" aria-hidden="true">
          <span><i className="lg-current" /> current</span>
          <span><i className="lg-visited" /> visited</span>
          <span><i className="lg-unvisited" /> unvisited</span>
          <span><i className="lg-thread" /> thread = stack</span>
          <span><i className="lg-hint" /> hint</span>
        </div>

        <div className="controls">
          <HintButton level={s.tier} max={3} onClick={() => act({ kind: 'hint' })} disabled={done || animating}
            nudge={stuck && !canReveal} cost={HINT_COST} />
          <button className="btn ghost" onClick={() => { submitted.current = false; setS(initTrace(g, start, auto)) }} disabled={submit.isPending}>
            <Icon name="restart" /> Restart
          </button>
          <span className="spacer" />
          {submit.isPending && <span className="faint small">Scoring your trace…</span>}
          {submit.isError && <span className="error-text">Couldn't save — check the server and press Restart.</span>}
        </div>
      </div>

      <div className="stack-v">
        {/* Feedback sits beside the graph, never below the fold: it's the core learning loop. */}
        {fb ? (
          <FeedbackBox fb={fb}>
            {canReveal && (
              <button className="btn sm hint" style={{ marginTop: 10 }} onClick={() => act({ kind: 'reveal' })}>
                <Icon name="eye" size={16} /> Show me this step
              </button>
            )}
          </FeedbackBox>
        ) : (
          <div className="feedback info"><div className="ic"><Icon name="info" /></div>
            <div><div className="t">Your move</div><div className="b">Stuck? Press <b>Hint</b> — each press goes a little further. After three tries or three hints, you can ask to be shown the step.</div></div>
          </div>
        )}
        <div className="card flat">
          <StackPanel
            items={vis.ev.stack}
            deadEnd={showDeadEnd}
            onPop={auto ? undefined : () => act({ kind: 'backtrack' })}
            popEnabled={!animating && !done}
          />
          {auto && <p className="faint tiny" style={{ marginTop: 8 }}>Backtracking is automatic here — you'll take control of it in “Dead Ends & the Thread”.</p>}
        </div>
        <div className="card flat"><VisitedStrip order={vis.ev.visited} total={g.nodes.length} /></div>
      </div>
    </div>
  )
}
