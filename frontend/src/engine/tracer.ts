// Interactive DFS tracing session: state machine + misconception-aware scaffolding.
//
// Mirrors backend/app/engine/replay.py. Feedback is progressive (Design doc 2.6):
//   tier 1 - a short nudge, tier 2 - a detailed explanation plus a visual clue,
//   tier 3 - the learner may ask to be shown the step.

import { adjacency, dfsTrace, listJoin, type GraphSpec, type TraceEvent } from './graph'

export type MistakeKind =
  | 'wrong_order'
  | 'not_adjacent'
  | 'already_visited'
  | 'should_backtrack'
  | 'premature_backtrack'

export type TraceAction =
  | { kind: 'visit'; node: string }
  | { kind: 'backtrack' }
  | { kind: 'hint' }
  | { kind: 'reveal' }

export interface Feedback {
  tone: 'good' | 'hint' | 'warn' | 'info'
  title: string
  body?: string
  highlight?: string[] // nodes to ring in blue
  tier: number
}

export interface TraceState {
  events: TraceEvent[]
  required: number[] // indices of events the learner must perform
  pos: number // next index into `required`
  shown: number // index of the event currently displayed (lags behind during auto-backtrack animation)
  wrongOnStep: number
  tier: number
  log: TraceAction[]
  mistakes: number
  hints: number
  reveals: number
  combo: number
  bestCombo: number
  feedback: Feedback | null
  flash: { node: string; kind: 'good' | 'bad' } | null
}

export function initTrace(g: GraphSpec, start: string, autoBacktrack: boolean): TraceState {
  const events = dfsTrace(g, start)
  const required = events.map((_, i) => i).filter((i) => i > 0 && !(autoBacktrack && events[i].kind === 'backtrack'))
  return {
    events, required, pos: 0, shown: 0, wrongOnStep: 0, tier: 0, log: [],
    mistakes: 0, hints: 0, reveals: 0, combo: 0, bestCombo: 0, feedback: null, flash: null,
  }
}

export const isDone = (s: TraceState) => s.pos >= s.required.length

/** The event index whose state the learner is reasoning about for the next step. */
export const contextIndex = (s: TraceState) => (isDone(s) ? s.events.length - 1 : s.required[s.pos] - 1)

function ctx(g: GraphSpec, s: TraceState) {
  const prev = s.events[contextIndex(s)]
  const current = prev.stack[prev.stack.length - 1]
  const adj = adjacency(g)
  const unvisited = (adj[current] ?? []).filter((n) => !prev.visited.includes(n))
  const below = prev.stack[prev.stack.length - 2]
  const expected = s.events[s.required[s.pos]]
  return { prev, current, unvisited, below, expected, adj }
}

export function classify(g: GraphSpec, s: TraceState, a: TraceAction): MistakeKind {
  const { prev, current, expected, adj } = ctx(g, s)
  if (a.kind === 'backtrack') return 'premature_backtrack'
  const node = a.kind === 'visit' ? a.node : ''
  if (expected.kind === 'backtrack') return 'should_backtrack'
  if (prev.visited.includes(node)) return 'already_visited'
  if (!adj[current].includes(node)) return 'not_adjacent'
  return 'wrong_order'
}

function mistakeFeedback(g: GraphSpec, s: TraceState, kind: MistakeKind, node: string | null, tier: number): Feedback {
  const { current, unvisited, below } = ctx(g, s)
  const u = listJoin(unvisited)
  const deep = tier >= 2
  const base = { tone: 'warn' as const, tier }
  switch (kind) {
    case 'wrong_order':
      return deep
        ? { ...base, title: `Use the tie-break rule`, highlight: [current, ...unvisited],
            body: `From ${current}, the unvisited neighbours are ${u}. When there's a choice, DFS always takes the alphabetically first one.` }
        : { ...base, title: `${node} is a neighbour — but is it the first choice?`,
            body: 'DFS has a tie-break rule. Which unvisited neighbour comes first alphabetically?' }
    case 'not_adjacent':
      return deep
        ? { ...base, title: `Stay on the edges`, highlight: [current, ...unvisited],
            body: `You're standing on ${current}. You can only walk along an edge to ${unvisited.length ? u : 'one of its neighbours'}.` }
        : { ...base, title: `There's no edge from ${current} to ${node}`,
            body: 'DFS moves one corridor at a time, along an edge from the current vertex.' }
    case 'already_visited':
      return deep
        ? { ...base, title: 'Chalk marks mean “been here”', highlight: [current, ...unvisited],
            body: `${node} is already visited. In a graph with cycles, re-entering visited vertices would loop forever — the visited set is what stops that.` }
        : { ...base, title: `${node} already has a chalk mark`, body: 'DFS never visits a vertex twice.' }
    case 'should_backtrack':
      return deep
        ? { ...base, title: `${current} is a dead end`, highlight: [current],
            body: `Every neighbour of ${current} is visited. Pop ${current} off the stack to wind the thread back to ${below ?? 'the start'}.` }
        : { ...base, title: 'No unvisited neighbours found.',
            body: `Look closely at ${current}'s neighbours. What action must DFS take?` }
    case 'premature_backtrack':
      return deep
        ? { ...base, title: 'Not a dead end yet', highlight: [current, ...unvisited],
            body: `${current} still has unvisited ${unvisited.length > 1 ? 'neighbours' : 'neighbour'}: ${u}. DFS only backtracks when there's nowhere new to go.` }
        : { ...base, title: 'Hold the thread!', body: `${current} still has somewhere new to explore.` }
  }
}

/** Hint requested without a mistake: progressively more specific. */
function hintFeedback(g: GraphSpec, s: TraceState, tier: number): Feedback {
  const { current, unvisited, expected } = ctx(g, s)
  if (tier <= 1) {
    return { tone: 'hint', tier, title: `Look at ${current}`, highlight: [current],
             body: 'You are on the vertex at the top of the stack. Which of its neighbours have no chalk mark yet?' }
  }
  if (expected.kind === 'backtrack') {
    return { tone: 'hint', tier, title: `${current} has nowhere new to go`, highlight: [current],
             body: `All of ${current}'s neighbours are visited, so it's a dead end. Backtrack.` }
  }
  return { tone: 'hint', tier, title: `Unvisited neighbours: ${listJoin(unvisited)}`, highlight: [current, ...unvisited],
           body: 'Take the alphabetically first one.' }
}

const PRAISE = ['Spot on!', 'Deeper we go.', 'Exactly.', 'Nice — DFS approves.', 'Perfect step.', 'Following the thread.']

function praise(s: TraceState, e: TraceEvent): Feedback {
  if (e.kind === 'backtrack') {
    const top = e.stack[e.stack.length - 1]
    return { tone: 'good', tier: 0, title: `Backtracked from ${e.node}`,
             body: top ? `Thread wound back to ${top}.` : 'The stack is empty — every reachable vertex is explored.' }
  }
  const combo = s.combo + 1
  return { tone: 'good', tier: 0, title: combo >= 3 ? `${combo} in a row!` : PRAISE[s.pos % PRAISE.length],
           body: `${e.node} is pushed on the stack and chalk-marked.` }
}

export function applyAction(g: GraphSpec, s: TraceState, a: TraceAction): TraceState {
  if (isDone(s)) return s
  const log = [...s.log, a]

  if (a.kind === 'hint') {
    const tier = Math.min(3, Math.max(s.tier, s.wrongOnStep) + 1)
    return { ...s, log, hints: s.hints + 1, tier, feedback: hintFeedback(g, s, tier) }
  }

  const expected = s.events[s.required[s.pos]]
  const advance = (extra: Partial<TraceState>): TraceState => ({
    ...s, ...extra, log, pos: s.pos + 1, wrongOnStep: 0, tier: 0,
    flash: expected.kind === 'visit' ? { node: expected.node, kind: 'good' } : null,
  })

  if (a.kind === 'reveal') {
    return advance({
      reveals: s.reveals + 1, combo: 0,
      feedback: { tone: 'info', tier: 3, title: expected.kind === 'visit' ? `DFS visits ${expected.node}` : `DFS backtracks from ${expected.node}`,
                  body: 'Watch the stack change — then try the next step yourself.' },
    })
  }

  const correct = a.kind === 'backtrack' ? expected.kind === 'backtrack' : expected.kind === 'visit' && a.node === expected.node
  if (correct) {
    const combo = s.combo + 1
    return advance({ combo, bestCombo: Math.max(s.bestCombo, combo), feedback: praise(s, expected) })
  }

  const kind = classify(g, s, a)
  const wrong = s.wrongOnStep + 1
  const tier = Math.min(3, Math.max(wrong, s.tier))
  return {
    ...s, log, mistakes: s.mistakes + 1, wrongOnStep: wrong, tier, combo: 0,
    feedback: mistakeFeedback(g, s, kind, a.kind === 'visit' ? a.node : null, tier),
    flash: a.kind === 'visit' ? { node: a.node, kind: 'bad' } : null,
  }
}

/** Preview of the server's star rule, for the live HUD. */
export function previewStars(s: TraceState): number {
  if (!isDone(s)) return 0
  const total = s.required.length
  const correct = s.pos - s.reveals
  const score = Math.max(0, Math.min(1, (correct - 0.25 * s.mistakes - 0.15 * s.hints) / total))
  if (s.mistakes === 0 && s.hints === 0 && s.reveals === 0) return 3
  return s.reveals === 0 && score >= 0.7 ? 2 : 1
}

/** Narration for the watch-only demos. */
export function narrate(g: GraphSpec, events: TraceEvent[], i: number): { title: string; body: string } {
  const e = events[i]
  const adj = adjacency(g)
  if (e.kind === 'visit') {
    const before = i > 0 ? events[i - 1].visited : []
    const nbrs = adj[e.node]
    const fresh = nbrs.filter((n) => !e.visited.includes(n))
    const why = i === 0 ? `We start at ${e.node}.` : `${e.node} was the first unvisited neighbour of ${e.stack[e.stack.length - 2]}${
      before.length && adj[e.stack[e.stack.length - 2]].filter((n) => !before.includes(n)).length > 1 ? ' (alphabetically)' : ''}.`
    return {
      title: `Visit ${e.node}`,
      body: `${why} Push it on the stack and chalk-mark it. Its neighbours: ${listJoin(nbrs) || 'none'}${
        fresh.length ? ` — still unvisited: ${listJoin(fresh)}.` : ' — all already visited.'}`,
    }
  }
  const top = e.stack[e.stack.length - 1]
  return {
    title: `Dead end at ${e.node} — backtrack`,
    body: top
      ? `${e.node} has no unvisited neighbours. Pop it off the stack; the thread winds back to ${top}, the most recent junction.`
      : `${e.node} was the start and it's fully explored. The stack is empty, so DFS is finished.`,
  }
}
