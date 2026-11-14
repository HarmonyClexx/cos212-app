import { adjacency, listJoin, type GraphSpec, type TraceEvent } from './graph'
import type { Feedback } from './tracer'

export function demoCheckpoints(g: GraphSpec, events: TraceEvent[]): number[] {
  const adj = adjacency(g)
  const indices = events.map((_, i) => i).slice(1)
  const visits = indices.filter((i) => events[i].kind === 'visit' && events[i - 1].stack.length > 1)
  const ordered = visits.find((i) => {
    const before = events[i - 1]
    return adj[before.stack.at(-1)!].filter((n) => !before.visited.includes(n)).length > 1
  }) ?? visits[0]
  const backtrack = indices.find((i) => events[i].kind === 'backtrack')
  const visited = indices.find((i) => {
    if (i === ordered || events[i].kind !== 'visit') return false
    const before = events[i - 1]
    return adj[before.stack.at(-1)!].some((n) => before.visited.includes(n) && !before.stack.includes(n))
  })
  return [...new Set([ordered, backtrack, visited].filter((i): i is number => i !== undefined))].sort((a, b) => a - b)
}

export interface DemoState {
  i: number
  playing: boolean
  seenEnd: boolean
  pending: number | null
  revealed: number[]
  feedback: Feedback | null
}

export const initialDemoState: DemoState = {
  i: 0, playing: false, seenEnd: false, pending: null, revealed: [], feedback: null,
}

export type DemoAction =
  | { type: 'next'; automaticAt?: number }
  | { type: 'previous' }
  | { type: 'restart'; play?: boolean }
  | { type: 'play' }
  | { type: 'answer'; node: string | null }
  | { type: 'reveal' }

export function demoTransition(g: GraphSpec, events: TraceEvent[], checkpoints: number[], s: DemoState, a: DemoAction): DemoState {
  const last = events.length - 1
  switch (a.type) {
    case 'restart':
      return { ...initialDemoState, seenEnd: s.seenEnd, playing: a.play ?? false }
    case 'previous':
      return { ...s, i: Math.max(0, s.i - 1), playing: false, pending: null, feedback: null }
    case 'play':
      if (s.pending !== null) return s
      if (s.i === last) return { ...initialDemoState, seenEnd: s.seenEnd, playing: true }
      return { ...s, playing: !s.playing }
    case 'next': {
      // Ignore timers from a step that has since been changed manually.
      if (a.automaticAt !== undefined && (!s.playing || a.automaticAt !== s.i)) return s
      if (s.pending !== null || s.i === last) return s
      const i = s.i + 1
      if (checkpoints.includes(i) && !s.revealed.includes(i)) {
        return { ...s, playing: false, pending: i, feedback: null }
      }
      return { ...s, i, playing: s.playing && i < last, seenEnd: s.seenEnd || i === last, feedback: null }
    }
    case 'answer':
    case 'reveal': {
      if (s.pending === null) return s
      const i = s.pending, ev = events[i], before = events[i - 1]
      const current = before.stack.at(-1)!
      const correct = a.type === 'answer' && (ev.kind === 'visit' ? a.node === ev.node : a.node === null)
      const skipped = adjacency(g)[current].filter((n) => before.visited.includes(n))
      const body = ev.kind === 'visit'
        ? `${skipped.length ? `Ignore already-visited neighbours ${listJoin(skipped)}. ` : ''}${ev.node} is the alphabetically first unvisited neighbour of ${current}. Push ${ev.node}; add it once to the visited marks and first-visit order.`
        : `Every neighbour of ${current} is already visited. Pop ${current}; ${ev.stack.length ? `${ev.stack.at(-1)} is now current` : 'the empty stack means DFS is complete'}. The visited marks and first-visit order stay unchanged.`
      return {
        ...s, i, playing: false, pending: null, revealed: [...s.revealed, i], seenEnd: s.seenEnd || i === last,
        feedback: { tier: 0, tone: a.type === 'reveal' ? 'info' : correct ? 'good' : 'warn',
          title: a.type === 'reveal' ? 'Step revealed' : correct ? 'That matches the DFS rule' : 'Compare your prediction with the DFS rule',
          body },
      }
    }
  }
}
