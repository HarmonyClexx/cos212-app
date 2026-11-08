// Objective 5 / Frame 4 (second half): side-by-side replay of DFS and BFS on the same graph.

import { useEffect, useMemo, useState } from 'react'
import { useSubmitActivity } from '../api/hooks'
import { QueuePanel, StackPanel } from '../components/DataStructures'
import { GraphCanvas, type EdgeMark, type NodeMark } from '../components/GraphCanvas'
import { Icon } from '../components/Icon'
import { FeedbackBox } from '../components/bits'
import { bfsSteps, dfsTrace, edgeId } from '../engine/graph'
import { traceVisuals, type ActivityProps } from './shared'

export function CompareActivity({ activity, onReward }: ActivityProps) {
  const g = activity.config.graph!
  const start = activity.config.start!
  const goal = activity.config.goal!
  const dfs = useMemo(() => dfsTrace(g, start), [g, start])
  const visitIdx = useMemo(() => dfs.map((e, i) => (e.kind === 'visit' ? i : -1)).filter((i) => i >= 0), [dfs])
  const bfs = useMemo(() => bfsSteps(g, start), [g, start])
  const N = g.nodes.length
  const [k, setK] = useState(1)
  const [playing, setPlaying] = useState(false)
  const [answer, setAnswer] = useState<number | null>(null)
  const submit = useSubmitActivity(activity.id)

  useEffect(() => {
    if (!playing) return
    if (k >= N) { setPlaying(false); return }
    const t = setTimeout(() => setK((x) => x + 1), 1100)
    return () => clearTimeout(t)
  }, [playing, k, N])

  const dvis = traceVisuals(g, dfs, visitIdx[k - 1], start)
  const dfsGoalAt = dfs.filter((e) => e.kind === 'visit').findIndex((e) => e.node === goal) + 1
  const bfsGoalAt = bfs.findIndex((s) => s.node === goal) + 1

  const bSeen = bfs.slice(0, k)
  const bNow = bfs[k - 1]
  const bNodeMarks: Record<string, NodeMark[]> = {}
  const bEdgeMarks: Record<string, EdgeMark[]> = {}
  for (const s of bSeen) {
    bNodeMarks[s.node] = ['visited']
    if (s.from) bEdgeMarks[edgeId(g, s.from, s.node)] = ['traversed']
  }
  bNodeMarks[bNow.node] = ['visited', 'current']
  if (bNow.from) bNodeMarks[bNow.from] = [...(bNodeMarks[bNow.from] ?? []), 'hint']
  const bBadges = Object.fromEntries(bSeen.map((s, i) => [s.node, { text: i + 1, tone: 'chalk' as const }]))

  const dNodeMarks = { ...dvis.nodeMarks }
  if (k < dfsGoalAt) dNodeMarks[goal] = [...(dNodeMarks[goal] ?? []), 'goal']
  if (k < bfsGoalAt) bNodeMarks[goal] = [...(bNodeMarks[goal] ?? []), 'goal']

  const level = bNow.level
  const seenEnd = k >= N

  return (
    <div className="stack-v" style={{ gap: 16 }}>
      <div className="stage">
        <div className="stage-head">
          <div className="prompt" style={{ flex: 1 }}>Both explorers start at <b>{start}</b>. Who reaches <span style={{ color: 'var(--danger)' }}>{goal}</span> first?</div>
          <span className="stat">Vertices visited: <b>{k}</b>/{N}</span>
        </div>
        <div className="controls" style={{ marginTop: 0 }}>
          <button className="btn primary" onClick={() => { if (k >= N) setK(1); setPlaying((p) => !p) }} style={{ minWidth: 110 }}>
            <Icon name={playing ? 'pause' : 'play'} /> {playing ? 'Pause' : k >= N ? 'Replay' : 'Race'}
          </button>
          <button className="btn" onClick={() => setK((x) => Math.max(1, x - 1))} aria-label="Previous"><Icon name="prev" /></button>
          <button className="btn" onClick={() => setK((x) => Math.min(N, x + 1))} aria-label="Next"><Icon name="next" /></button>
          <input className="scrubber" type="range" min={1} max={N} value={k} onChange={(e) => { setPlaying(false); setK(Number(e.target.value)) }}
            aria-label="Step" style={{ flex: 1, minWidth: 160 }} />
        </div>
      </div>

      <div className="compare-grid">
        <div className="stage">
          <div className="stage-head">
            <h3 style={{ flex: 1 }}><span style={{ color: 'var(--thread)' }}>DFS</span> · deep first</h3>
            {k >= dfsGoalAt && <span className="chip gold found">Found {goal} at #{dfsGoalAt}</span>}
          </div>
          <GraphCanvas graph={g} nodeMarks={dNodeMarks} edgeMarks={dvis.edgeMarks} thread={dvis.thread} badges={dvis.badges} maxHeight={330} />
          <div style={{ marginTop: 10 }}><StackPanel items={dvis.ev.stack} title="Stack (LIFO)" /></div>
        </div>
        <div className="stage">
          <div className="stage-head">
            <h3 style={{ flex: 1 }}><span style={{ color: 'var(--hint)' }}>BFS</span> · wide first</h3>
            <span className="chip hint">Level {level}</span>
            {k >= bfsGoalAt && <span className="chip gold found">Found {goal} at #{bfsGoalAt}</span>}
          </div>
          <GraphCanvas graph={g} nodeMarks={bNodeMarks} edgeMarks={bEdgeMarks} badges={bBadges} maxHeight={330} />
          <div style={{ marginTop: 10 }}><QueuePanel items={bNow.queue} /></div>
          <p className="faint tiny" style={{ marginTop: 8 }}>Blue ring = the vertex BFS is expanding. It discovers <em>all</em> its neighbours before moving on.</p>
        </div>
      </div>

      <div className="card">
        <div className="card-title"><Icon name="sparkles" size={18} /> Think about it</div>
        {!seenEnd ? <p className="muted small">Finish the race first.</p> : (
          <div className="stack-v">
            <p>Here DFS found {goal} after {dfsGoalAt} visits and BFS after {bfsGoalAt}. Does that mean DFS is always faster?</p>
            <div className="options">
              {['Yes — diving deep always finds things sooner', 'No — it depends where the target is. If it were close to the start, BFS would find it first.'].map((o, i) => (
                <button key={i} className={`option ${answer === i ? (i === 1 ? 'correct' : 'wrong') : ''}`} onClick={() => setAnswer(i)}>
                  <span className="key">{String.fromCharCode(65 + i)}</span>{o}
                </button>
              ))}
            </div>
            {answer !== null && (
              <FeedbackBox fb={answer === 1
                ? { tone: 'good', tier: 0, title: 'Exactly.', body: `${goal} sits at the bottom of the first branch DFS tries, so DFS got lucky. Target D instead and BFS finds it at #4 while DFS needs #8. BFS reaches vertices in order of distance — DFS reaches them in order of branch.` }
                : { tone: 'warn', tier: 1, title: 'Not quite.', body: 'Try target D in your head: BFS reaches it at step 4 (level 1). When does DFS get there?' }} />
            )}
            <button className="btn gold" style={{ alignSelf: 'flex-start' }} disabled={answer !== 1 || submit.isPending}
              onClick={() => submit.mutate({ data: { reflected: true } }, { onSuccess: ({ reward }) => onReward(reward, { graded: false, subtitle: 'Deep vs wide: you have seen both.' }) })}>
              <Icon name="check" /> Finish
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
