import { useState, type DragEvent } from 'react'
import type { Answer, GradeDetail, QuizItem } from '../../api/types'
import { GraphCanvas, type EdgeMark, type NodeMark } from '../../components/GraphCanvas'
import { Icon } from '../../components/Icon'
import { Md } from '../../components/bits'

export interface ItemProps<T> {
  item: QuizItem
  value: T
  onChange: (v: T) => void
  locked: boolean
  /** The correct answer, once revealed (formative after 3 tries, or summative review). */
  answer?: unknown
  detail?: GradeDetail
  /** Level-2 hint visual cue: vertices to ring in blue. */
  focus?: string[]
}

/** Node marks with the hint ring added to the focus vertices. */
function withFocus(marks: Record<string, NodeMark[]>, focus: string[] | undefined): Record<string, NodeMark[]> {
  if (!focus?.length) return marks
  const out = { ...marks }
  for (const id of focus) out[id] = [...(out[id] ?? []), 'hint']
  return out
}

export function emptyAnswer(item: QuizItem): Answer {
  switch (item.type) {
    case 'mcq':
    case 'graph_select':
      return [] as string[]
    case 'adjacency':
      return Object.fromEntries(item.graph!.nodes.map((n) => [n.id, [] as string[]]))
    case 'order':
      return [item.start!]
    case 'short_answer':
      return ''
  }
}

export function isAnswered(item: QuizItem, v: Answer | undefined): boolean {
  if (v === undefined) return false
  if (item.type === 'short_answer') return (v as string).trim().length > 0
  if (item.type === 'adjacency') return Object.values(v as Record<string, string[]>).some((r) => r.length > 0)
  if (item.type === 'order') return (v as string[]).length > 1
  return (v as unknown[]).length > 0
}

export function ItemView(props: ItemProps<Answer>) {
  const { item } = props
  return (
    <div className="item-card">
      <div className="item-prompt"><Md text={item.prompt} /></div>
      {item.type === 'mcq' && <Mcq {...(props as ItemProps<number[]>)} />}
      {item.type === 'graph_select' && <GraphSelect {...(props as ItemProps<string[]>)} />}
      {item.type === 'adjacency' && <AdjacencyBuilder {...(props as ItemProps<Record<string, string[]>>)} />}
      {item.type === 'order' && <OrderClicker {...(props as ItemProps<string[]>)} />}
      {item.type === 'short_answer' && <ShortAnswer {...(props as ItemProps<string>)} />}
    </div>
  )
}

function Mcq({ item, value, onChange, locked, answer, focus }: ItemProps<number[]>) {
  const correct = answer as number[] | undefined
  return (
    <div className="stack-v">
      {item.graph && <div className="panel"><GraphCanvas graph={item.graph} nodeMarks={withFocus({}, focus)} maxHeight={260} /></div>}
      <div className="options" role={item.multi ? 'group' : 'radiogroup'}>
        {item.options!.map((o, i) => {
          const sel = value.includes(i)
          const cls = correct ? (correct.includes(i) ? 'correct' : sel ? 'wrong' : '') : sel ? 'selected' : ''
          return (
            <button key={i} className={`option ${cls}`} disabled={locked} role={item.multi ? 'checkbox' : 'radio'} aria-checked={sel}
              onClick={() => onChange(item.multi ? (sel ? value.filter((x) => x !== i) : [...value, i]) : [i])}>
              <span className="key">{String.fromCharCode(65 + i)}</span><span><Md text={o} /></span>
              {correct?.includes(i) && <Icon name="check" style={{ marginLeft: 'auto', color: 'var(--chalk)' }} />}
            </button>
          )
        })}
      </div>
    </div>
  )
}

function GraphSelect({ item, value, onChange, locked, answer, detail, focus }: ItemProps<string[]>) {
  const g = item.graph!
  const correct = answer as string[] | undefined
  const extra = new Set(detail?.extra ?? [])
  const toggle = (id: string) => !locked && onChange(value.includes(id) ? value.filter((x) => x !== id) : [...value, id])
  const markFor = (id: string): string[] => {
    const sel = value.includes(id)
    if (correct) return [correct.includes(id) ? (sel ? 'correct' : 'missing') : sel ? 'wrong' : '']
    return [sel ? 'selected' : '', extra.has(id) ? 'wrong' : '']
  }
  const nodeMarks: Record<string, NodeMark[]> = {}
  const edgeMarks: Record<string, EdgeMark[]> = {}
  if (item.select === 'nodes') for (const n of g.nodes) nodeMarks[n.id] = markFor(n.id) as NodeMark[]
  else for (const [u, v] of g.edges) {
    const id = g.directed ? `${u}->${v}` : [u, v].sort().join('-')
    edgeMarks[id] = markFor(id) as EdgeMark[]
  }
  return (
    <div className="panel">
      <GraphCanvas graph={g} nodeMarks={withFocus(nodeMarks, focus)} edgeMarks={edgeMarks} maxHeight={320}
        onNodeClick={item.select === 'nodes' && !locked ? toggle : undefined}
        onEdgeClick={item.select === 'edges' && !locked ? toggle : undefined} />
      <div className="row small muted" style={{ marginTop: 6 }}>
        <Icon name="info" size={14} /> Tap {item.select === 'nodes' ? 'vertices' : 'edges'} to select or deselect.
        <span className="spacer" /><span>{value.length} selected</span>
      </div>
    </div>
  )
}

function AdjacencyBuilder({ item, value, onChange, locked, answer, detail, focus }: ItemProps<Record<string, string[]>>) {
  const g = item.graph!
  const ids = g.nodes.map((n) => n.id)
  const [held, setHeld] = useState<string | null>(null)
  const [over, setOver] = useState<string | null>(null)
  const shown = (answer as Record<string, string[]> | undefined) ?? value
  const wrong = new Set(detail?.wrong_rows ?? [])

  const add = (row: string, n: string) => {
    if (locked || row === n || value[row]?.includes(n)) return
    onChange({ ...value, [row]: [...(value[row] ?? []), n].sort() })
  }
  const remove = (row: string, n: string) => !locked && onChange({ ...value, [row]: value[row].filter((x) => x !== n) })
  const drop = (row: string) => (e: DragEvent) => {
    e.preventDefault()
    setOver(null)
    const n = e.dataTransfer.getData('text/plain')
    if (n) add(row, n)
  }

  return (
    <div className="adj-grid">
      <div className="panel">
        <GraphCanvas graph={g} nodeMarks={withFocus({}, focus)} maxHeight={300} />
        <div className="small muted center">{g.directed ? 'Directed — list out-neighbours only' : 'Undirected — edges go both ways'}</div>
      </div>
      <div className="stack-v">
        {!locked && (
          <div>
            <div className="small muted" style={{ marginBottom: 6 }}>Drag a vertex into a row — or tap it, then tap a row.</div>
            <div className="palette">
              {ids.map((n) => (
                <button key={n} className={`token ${held === n ? 'held' : ''}`} draggable
                  onDragStart={(e) => { e.dataTransfer.setData('text/plain', n); setHeld(null) }}
                  onClick={() => setHeld(held === n ? null : n)} aria-pressed={held === n}>{n}</button>
              ))}
            </div>
          </div>
        )}
        <div className="adj-rows">
          {ids.map((r) => (
            <div key={r}
              className={['adj-row', over === r && 'drop', wrong.has(r) && 'wrong', answer !== undefined && 'right'].filter(Boolean).join(' ')}
              onDragOver={(e) => { e.preventDefault(); setOver(r) }} onDragLeave={() => setOver(null)} onDrop={drop(r)}
              onClick={() => { if (held) { add(r, held) } }}
              role="group" aria-label={`Row ${r}: ${(shown[r] ?? []).join(', ') || 'empty'}`}>
              <span className="head">{r}</span><span className="arrow">→</span>
              <div className="cells">
                {(shown[r] ?? []).length === 0 && <span className="placeholder">{held ? `tap to add ${held}` : 'empty'}</span>}
                {(shown[r] ?? []).map((n) => (
                  <button key={n} className="token in-row" disabled={locked} onClick={(e) => { e.stopPropagation(); remove(r, n) }}
                    aria-label={`Remove ${n} from row ${r}`}>{n}{!locked && <Icon name="x" size={12} />}</button>
                ))}
              </div>
              {wrong.has(r) && <Icon name="x" style={{ color: 'var(--danger)' }} />}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function OrderClicker({ item, value, onChange, locked, answer, detail, focus }: ItemProps<string[]>) {
  const g = item.graph!
  const seq = (answer as string[] | undefined) ?? value
  const prefix = answer ? seq.length : detail?.correct_prefix
  const nodeMarks: Record<string, NodeMark[]> = {}
  seq.forEach((n, i) => {
    nodeMarks[n] = [prefix !== undefined ? (i < prefix ? 'correct' : 'wrong') : 'visited', i === seq.length - 1 && !answer ? 'current' : undefined] as NodeMark[]
  })
  const badges = Object.fromEntries(seq.map((n, i) => [n, { text: i + 1, tone: 'chalk' as const }]))
  return (
    <div className="stack-v">
      <div className="panel">
        <GraphCanvas graph={g} nodeMarks={withFocus(nodeMarks, focus)} badges={badges} maxHeight={320}
          onNodeClick={locked ? undefined : (id) => !value.includes(id) && onChange([...value, id])}
          nodeClickable={(id) => !value.includes(id)} />
      </div>
      <div className="row wrap">
        <div className="order-seq" aria-label="Your order">
          {seq.map((n, i) => <span key={n} className="vchip"><span className="n">{i + 1}</span>{n}</span>)}
          {seq.length < g.nodes.length && !locked && <span className="vchip pending"><span className="n">{seq.length + 1}</span>?</span>}
        </div>
        <span className="spacer" />
        {!locked && (
          <>
            <button className="btn sm" onClick={() => onChange(value.slice(0, Math.max(1, value.length - 1)))} disabled={value.length <= 1}><Icon name="undo" size={16} /> Undo</button>
            <button className="btn sm ghost" onClick={() => onChange([item.start!])} disabled={value.length <= 1}>Clear</button>
          </>
        )}
      </div>
      {detail?.looks_like && <div className="chip hint" style={{ alignSelf: 'flex-start' }}>That started to look like {detail.looks_like.toUpperCase()}</div>}
    </div>
  )
}

function ShortAnswer({ item, value, onChange, locked, answer, detail }: ItemProps<string>) {
  const words = value.trim() ? value.trim().split(/\s+/).length : 0
  const met = detail?.criteria
  const model = (answer as { model_answer?: string } | undefined)?.model_answer
  return (
    <div className="stack-v">
      <textarea className="input" value={value} onChange={(e) => onChange(e.target.value)} disabled={locked}
        placeholder="Write your explanation here…" aria-label="Your answer" maxLength={1200} />
      <div className="row small faint"><span>{words} word{words === 1 ? '' : 's'}</span></div>
      <div className="panel">
        <div className="small" style={{ fontWeight: 700, marginBottom: 8 }}>
          Marking criteria <span className="faint">· pass = {item.pass_criteria} of {item.criteria?.length}, distinction = all</span>
        </div>
        <ul className="criteria">
          {(met ?? item.criteria?.map((d) => ({ descriptor: d, met: undefined as boolean | undefined, nudge: undefined as string | undefined })) ?? []).map((c, i) => (
            <li key={i} className={c.met === undefined ? '' : c.met ? 'met' : 'unmet'}>
              <span className="mk"><Icon name={c.met === undefined ? 'dot' : c.met ? 'check' : 'minus'} size={16} /></span>
              <span>{c.descriptor}{c.met === false && c.nudge && <span className="nudge"><Icon name="bulb" size={12} /> {c.nudge}</span>}</span>
            </li>
          ))}
        </ul>
      </div>
      {model && (
        <div className="panel" style={{ borderColor: 'color-mix(in srgb, var(--chalk) 40%, transparent)' }}>
          <div className="small" style={{ fontWeight: 700, color: 'var(--chalk)', marginBottom: 4 }}>A model answer</div>
          <div className="small">{model}</div>
        </div>
      )}
    </div>
  )
}
