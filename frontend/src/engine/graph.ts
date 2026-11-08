// TypeScript twin of backend/app/engine. The browser uses it for instant feedback;
// the server re-grades everything, so the two must agree (alphabetical tie-break).

export interface GraphNode {
  id: string
  x: number
  y: number
}

export interface GraphSpec {
  id: string
  directed: boolean
  nodes: GraphNode[]
  edges: [string, string][]
}

export function adjacency(g: GraphSpec): Record<string, string[]> {
  const adj: Record<string, Set<string>> = {}
  for (const n of g.nodes) adj[n.id] = new Set()
  for (const [u, v] of g.edges) {
    adj[u].add(v)
    if (!g.directed) adj[v].add(u)
  }
  return Object.fromEntries(Object.entries(adj).map(([k, s]) => [k, [...s].sort()]))
}

export function edgeId(g: Pick<GraphSpec, 'directed'>, u: string, v: string): string {
  if (g.directed) return `${u}->${v}`
  return u < v ? `${u}-${v}` : `${v}-${u}`
}

export function nodeIds(g: GraphSpec): string[] {
  return g.nodes.map((n) => n.id)
}

export interface TraceEvent {
  kind: 'visit' | 'backtrack'
  node: string
  stack: string[]
  visited: string[] // in visit order
}

export function dfsTrace(g: GraphSpec, start: string): TraceEvent[] {
  const adj = adjacency(g)
  const visited = [start]
  const seen = new Set(visited)
  const stack = [start]
  const events: TraceEvent[] = [{ kind: 'visit', node: start, stack: [...stack], visited: [...visited] }]
  while (stack.length) {
    const top = stack[stack.length - 1]
    const next = adj[top].find((n) => !seen.has(n))
    if (next === undefined) {
      stack.pop()
      events.push({ kind: 'backtrack', node: top, stack: [...stack], visited: [...visited] })
    } else {
      seen.add(next)
      visited.push(next)
      stack.push(next)
      events.push({ kind: 'visit', node: next, stack: [...stack], visited: [...visited] })
    }
  }
  return events
}

export function dfsOrder(g: GraphSpec, start: string): string[] {
  return dfsTrace(g, start).filter((e) => e.kind === 'visit').map((e) => e.node)
}

export interface BfsStep {
  node: string // vertex visited (discovered) at this step
  from: string | null
  queue: string[] // queue after discovering `node`
  level: number
}

export function bfsSteps(g: GraphSpec, start: string): BfsStep[] {
  const adj = adjacency(g)
  const level: Record<string, number> = { [start]: 0 }
  const queue = [start]
  const steps: BfsStep[] = [{ node: start, from: null, queue: [...queue], level: 0 }]
  while (queue.length) {
    const cur = queue.shift()!
    for (const n of adj[cur]) {
      if (!(n in level)) {
        level[n] = level[cur] + 1
        queue.push(n)
        steps.push({ node: n, from: cur, queue: [...queue], level: level[n] })
      }
    }
  }
  return steps
}

export function bfsOrder(g: GraphSpec, start: string): string[] {
  return bfsSteps(g, start).map((s) => s.node)
}

export function listJoin(items: string[]): string {
  if (items.length <= 1) return items.join('')
  return `${items.slice(0, -1).join(', ')} and ${items[items.length - 1]}`
}
