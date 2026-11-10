import type { Activity, Reward } from '../api/types'
import type { EdgeMark, NodeMark } from '../components/GraphCanvas'
import { edgeId, type GraphSpec, type TraceEvent } from '../engine/graph'

export interface RewardMeta {
  graded: boolean
  title?: string
  subtitle?: string
}

export interface ActivityProps {
  activity: Activity
  onReward: (reward: Reward, meta: RewardMeta) => void
}

/** Visual state of a DFS trace at event index `shown`. */
export function traceVisuals(g: GraphSpec, events: TraceEvent[], shown: number, start: string) {
  const ev = events[shown]
  const parents: Record<string, string> = {}
  for (let i = 1; i <= shown; i++) {
    const e = events[i]
    if (e.kind === 'visit') parents[e.node] = e.stack[e.stack.length - 2]
  }
  const current = ev.stack[ev.stack.length - 1]
  const nodeMarks: Record<string, NodeMark[]> = {}
  for (const n of g.nodes) {
    const marks: NodeMark[] = []
    if (ev.visited.includes(n.id)) marks.push('visited')
    if (ev.stack.includes(n.id)) marks.push('stack')
    if (n.id === current) marks.push('current')
    if (n.id === start) marks.push('start')
    nodeMarks[n.id] = marks
  }
  const edgeMarks: Record<string, EdgeMark[]> = {}
  for (const [child, parent] of Object.entries(parents)) edgeMarks[edgeId(g, parent, child)] = ['traversed']
  const badges = Object.fromEntries(ev.visited.map((n, i) => [n, { text: i + 1, tone: 'chalk' as const }]))
  return { ev, current, nodeMarks, edgeMarks, badges, thread: ev.stack }
}

export function addMark<T extends string>(marks: Record<string, T[]>, ids: string[] | undefined, mark: T) {
  for (const id of ids ?? []) marks[id] = [...(marks[id] ?? []), mark]
}
