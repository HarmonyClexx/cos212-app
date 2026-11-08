// Formative quizzes: per-item "Check" with progressive scaffolding (Design 2.6). Help comes
// from asking (Hint) or from a wrong try, whichever is first: level 1 is a nudge, level 2 the
// idea in full with the relevant vertices ringed; the worked answer needs three tries. Summative ("Face the Minotaur"): no feedback until the
// end, then a criterion-referenced report per objective with revision recommendations.

import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useCheckItem, useFinishAttempt, useHint, useStartAttempt } from '../api/hooks'
import type { Answer, AttemptStart, CheckResult, FinishResult, HintResult, MasteryRow, QuizItem } from '../api/types'
import { Icon } from '../components/Icon'
import { FeedbackBox, HintButton, Meter, masteryStatus } from '../components/bits'
import type { Feedback } from '../engine/tracer'
import { useIdle } from '../lib/useIdle'
import { ItemView, emptyAnswer, isAnswered } from './items/QuizItems'
import type { ActivityProps } from './shared'

const OBJ_NAMES: Record<number, string> = {
  1: 'Graph concepts', 2: 'Representation', 3: 'DFS traversal', 4: 'State & backtracking', 5: 'DFS vs BFS',
}

export function QuizActivity({ activity, onReward }: ActivityProps) {
  const start = useStartAttempt(activity.id)
  const [attempt, setAttempt] = useState<AttemptStart | null>(null)
  const started = useRef(false)

  useEffect(() => {
    if (started.current) return
    started.current = true
    start.mutate(undefined, { onSuccess: setAttempt })
  }, [start])

  if (start.isError) return <div className="card empty-state">Couldn't start the quiz: {(start.error as Error).message}</div>
  if (!attempt) return <div className="skeleton" style={{ height: 420 }} />
  return attempt.mode === 'formative'
    ? <Formative attempt={attempt} onReward={onReward} />
    : <Summative attempt={attempt} onReward={onReward} activityTitle={activity.title} />
}

function Formative({ attempt, onReward }: { attempt: AttemptStart; onReward: ActivityProps['onReward'] }) {
  const items = attempt.items
  const [idx, setIdx] = useState(0)
  const [answers, setAnswers] = useState<Record<string, Answer>>(() => Object.fromEntries(items.map((i) => [i.id, emptyAnswer(i)])))
  const [results, setResults] = useState<Record<string, CheckResult>>({})
  const [revealed, setRevealed] = useState<Record<string, boolean>>({})
  const [hints, setHints] = useState<Record<string, HintResult>>({})
  const [last, setLast] = useState<Record<string, 'hint' | 'check'>>({})
  const check = useCheckItem(attempt.attempt_id)
  const hint = useHint(attempt.attempt_id)
  const finish = useFinishAttempt(attempt.attempt_id)

  const item = items[idx]
  const res = results[item.id]
  const resolved = (i: QuizItem) => results[i.id]?.correct || revealed[i.id]
  const isResolved = resolved(item)
  const allResolved = items.every(resolved)

  const doCheck = (reveal = false) =>
    check.mutate({ item_id: item.id, answer: reveal ? undefined : answers[item.id], reveal }, {
      onSuccess: (r) => {
        setResults((m) => ({ ...m, [item.id]: { ...r, tries: reveal ? (m[item.id]?.tries ?? r.tries) : r.tries } }))
        setLast((m) => ({ ...m, [item.id]: 'check' }))
        if (reveal) setRevealed((m) => ({ ...m, [item.id]: true }))
      },
    })

  const askHint = () =>
    hint.mutate({ item_id: item.id }, {
      onSuccess: (h) => {
        setHints((m) => ({ ...m, [item.id]: h }))
        setLast((m) => ({ ...m, [item.id]: 'hint' }))
      },
    })

  const h = hints[item.id]
  const showingHint = last[item.id] === 'hint' && h && !isResolved
  // Help already seen on this item, from hints or wrong tries (capped at the 2 hint levels).
  const level = Math.max(h?.level ?? 0, Math.min(2, res && !res.correct ? res.tier : 0))
  const worth = (showingHint ? h.worth : res?.worth) ?? 1
  const focus = isResolved ? undefined : showingHint ? h.focus : res?.focus
  const idle = useIdle(25000, `${item.id}|${JSON.stringify(answers[item.id])}|${res?.tries ?? 0}|${level}`, !isResolved)

  const fb: Feedback | null = showingHint
    ? { tone: 'hint', tier: h.level, title: h.level === 1 ? 'Hint' : 'A bigger hint', body: h.hint }
    : res
      ? {
          tone: res.correct ? 'good' : revealed[item.id] ? 'info' : 'warn',
          tier: res.correct ? 0 : revealed[item.id] ? 3 : res.tier,
          title: res.correct ? (res.tries === 1 ? 'Correct — first try!' : `Correct after ${res.tries} tries.`) : revealed[item.id] ? 'Here is the worked answer' : res.feedback,
          body: res.correct || revealed[item.id] ? res.explanation : res.hint,
        }
      : idle
        ? { tone: 'hint', tier: 0, title: 'Take your time', body: 'If you’re not sure where to start, press Hint. It costs much less than a wrong guess.' }
        : null

  return (
    <div className="card">
      <div className="quiz-top">
        <span className="chip brand">Formative · retries allowed</span>
        <div className="pips" aria-label="Questions">
          {items.map((it, i) => (
            <button key={it.id} className={`pip ${i === idx ? 'current' : results[it.id]?.correct ? 'done' : revealed[it.id] ? 'revealed' : ''}`}
              onClick={() => setIdx(i)} aria-label={`Question ${i + 1}`} />
          ))}
        </div>
        <span className="spacer" />
        <span className="faint small">Question {idx + 1} of {items.length}</span>
      </div>

      <ItemView key={item.id} item={item} value={answers[item.id]} locked={!!isResolved}
        onChange={(v) => setAnswers((a) => ({ ...a, [item.id]: v }))}
        answer={isResolved ? res?.answer : undefined} detail={res && !res.correct ? res.detail : undefined} focus={focus} />

      <div style={{ marginTop: 16 }}>
        {fb && (
          <FeedbackBox fb={fb}>
            {!showingHint && res && !res.correct && !revealed[item.id] && res.can_reveal && (
              <button className="btn sm hint" style={{ marginTop: 10 }} onClick={() => doCheck(true)} disabled={check.isPending}>
                <Icon name="eye" size={16} /> Show me the answer
              </button>
            )}
          </FeedbackBox>
        )}
      </div>

      <div className="controls" style={{ marginTop: 16 }}>
        <button className="btn ghost" onClick={() => setIdx((i) => Math.max(0, i - 1))} disabled={idx === 0}><Icon name="chevronLeft" /> Back</button>
        <span className="spacer" />
        {(check.isError || hint.isError) && <span className="error-text">{((check.error ?? hint.error) as Error).message}</span>}
        {!isResolved && worth < 1 && (
          <span className="hint-note" title="Credit if your next answer is right. Getting there yourself is always worth at least 20%.">
            <Icon name="target" size={14} /> Now worth <b>{Math.round(worth * 100)}%</b>
          </span>
        )}
        {!isResolved && (
          <HintButton level={level} max={2} onClick={askHint} disabled={hint.isPending}
            nudge={idle || (!!res && !res.correct && level < 2)}
            cost="A hint costs 15% of this question — half the price of a wrong guess." />
        )}
        {!isResolved && (
          <button className="btn primary" onClick={() => doCheck()} disabled={check.isPending || !isAnswered(item, answers[item.id])}>
            <Icon name="check" /> Check
          </button>
        )}
        {isResolved && idx < items.length - 1 && (
          <button className="btn primary" onClick={() => setIdx(items.findIndex((it, i) => i > idx && !resolved(it)) === -1 ? idx + 1 : items.findIndex((it, i) => i > idx && !resolved(it)))}>
            Next <Icon name="arrowRight" />
          </button>
        )}
        {allResolved && (
          <button className="btn gold" disabled={finish.isPending} onClick={() => finish.mutate(undefined, {
            onSuccess: (r) => onReward(r.reward, { graded: true, subtitle: `Score ${Math.round(r.result.score * 100)}% — first-try answers count most.` }),
          })}>
            <Icon name="trophy" /> Finish quiz
          </button>
        )}
      </div>
    </div>
  )
}

function Summative({ attempt, onReward, activityTitle }: { attempt: AttemptStart; onReward: ActivityProps['onReward']; activityTitle: string }) {
  const items = attempt.items
  const [idx, setIdx] = useState(0)
  const [answers, setAnswers] = useState<Record<string, Answer>>(() => Object.fromEntries(items.map((i) => [i.id, emptyAnswer(i)])))
  const [report, setReport] = useState<FinishResult | null>(null)
  const [confirm, setConfirm] = useState(false)
  const finish = useFinishAttempt(attempt.attempt_id)
  const item = items[idx]
  const answered = items.filter((i) => isAnswered(i, answers[i.id])).length

  const submit = () => finish.mutate(answers, {
    onSuccess: (r) => {
      setReport(r)
      onReward(r.reward, {
        graded: true,
        subtitle: r.result.passed ? `You scored ${Math.round(r.result.score * 100)}%. The Minotaur is defeated!` : `You scored ${Math.round(r.result.score * 100)}% — ${Math.round(attempt.pass_mark * 100)}% needed. Check your report and revise.`,
      })
    },
  })

  if (report) return <SummativeReport items={items} answers={answers} report={report} title={activityTitle} />

  return (
    <div className="card">
      <div className="quiz-top">
        <span className="chip danger"><Icon name="sword" size={14} /> Summative · no hints</span>
        <div className="pips">
          {items.map((it, i) => (
            <button key={it.id} className={`pip ${i === idx ? 'current' : isAnswered(it, answers[it.id]) ? 'answered' : ''}`} onClick={() => setIdx(i)} aria-label={`Question ${i + 1}`} />
          ))}
        </div>
        <span className="spacer" />
        <span className="chip">{OBJ_NAMES[item.objective]}</span>
        <span className="faint small">{idx + 1} / {items.length}</span>
      </div>

      <ItemView key={item.id} item={item} value={answers[item.id]} locked={false} onChange={(v) => setAnswers((a) => ({ ...a, [item.id]: v }))} />

      <div className="controls" style={{ marginTop: 18 }}>
        <button className="btn ghost" onClick={() => setIdx((i) => Math.max(0, i - 1))} disabled={idx === 0}><Icon name="chevronLeft" /> Back</button>
        <span className="spacer" />
        <span className="faint small">{answered}/{items.length} answered</span>
        {idx < items.length - 1
          ? <button className="btn primary" onClick={() => setIdx(idx + 1)}>Next <Icon name="arrowRight" /></button>
          : <button className="btn gold" onClick={() => (answered < items.length ? setConfirm(true) : submit())} disabled={finish.isPending}><Icon name="sword" /> Submit trial</button>}
      </div>
      {confirm && (
        <FeedbackBox fb={{ tone: 'warn', tier: 0, title: `${items.length - answered} question(s) unanswered`, body: 'Unanswered questions score zero. Submit anyway?' }}>
          <div className="row" style={{ marginTop: 10 }}>
            <button className="btn sm gold" onClick={() => { setConfirm(false); submit() }}>Submit anyway</button>
            <button className="btn sm ghost" onClick={() => setConfirm(false)}>Keep working</button>
          </div>
        </FeedbackBox>
      )}
      {finish.isError && <p className="error-text">{(finish.error as Error).message}</p>}
    </div>
  )
}

function SummativeReport({ items, answers, report, title }: { items: QuizItem[]; answers: Record<string, Answer>; report: FinishResult; title: string }) {
  const navigate = useNavigate()
  const { result, recommendations, mastery } = report
  const masteryBy = Object.fromEntries(mastery.map((m) => [m.objective, m])) as Record<number, MasteryRow>
  return (
    <div className="stack-v" style={{ gap: 16 }}>
      <div className="card">
        <div className="row wrap" style={{ gap: 16 }}>
          <div>
            <div className="eyebrow">{title} · report</div>
            <h2 style={{ marginTop: 4 }}>{result.passed ? 'Passed' : 'Not yet passed'} · {Math.round(result.score * 100)}%</h2>
          </div>
          <span className="spacer" />
          <span className={`chip ${result.passed ? 'chalk' : 'danger'}`}><Icon name={result.passed ? 'check' : 'x'} size={14} /> {result.passed ? 'Criterion met' : 'Criterion not met'}</span>
        </div>
        <div style={{ marginTop: 16 }}>
          {Object.entries(result.objectives).map(([o, s]) => {
            const m = masteryBy[Number(o)]
            const st = masteryStatus(s, 1)
            return (
              <div className="mastery-row" key={o}>
                <span className="name">Objective {o} · {OBJ_NAMES[Number(o)]}</span>
                <span className="val">{Math.round(s * 100)}%</span>
                <Meter value={s} color={st.color} target={0.7} label={`Objective ${o} score`} />
                <span className="meta"><span className="status"><Icon name={st.icon} size={14} style={{ color: st.color }} /> {st.label}</span>
                  {m && <span>· running mastery {Math.round(m.value * 100)}%</span>}</span>
              </div>
            )
          })}
        </div>
      </div>

      {recommendations.filter((r) => r.type === 'revise').length > 0 && (
        <div className="card">
          <div className="card-title"><Icon name="target" size={18} /> Recommended revision</div>
          <div className="stack-v">
            {recommendations.filter((r) => r.type === 'revise').map((r) => (
              <button key={r.activity_id} className="rec revise" onClick={() => navigate(`/learn/${r.module}/${r.activity_id}`)}>
                <span className="ic"><Icon name="undo" /></span>
                <span style={{ flex: 1 }}><b>{r.title}</b><br /><span className="small muted">{r.reason}</span></span>
                <Icon name="chevronRight" />
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-title"><Icon name="eye" size={18} /> Question review</div>
        <div className="stack-v">
          {result.review.map((r, i) => {
            const it = items.find((x) => x.id === r.item_id)!
            return (
              <details key={r.item_id} className="review-item">
                <summary className="row" style={{ cursor: 'pointer' }}>
                  <Icon name={r.correct ? 'check' : 'x'} style={{ color: r.correct ? 'var(--chalk)' : 'var(--danger)' }} />
                  <b>Q{i + 1}</b><span className="muted small">{OBJ_NAMES[r.objective]}</span>
                  <span className="spacer" /><span className="small">{Math.round(r.score * 100)}%</span>
                </summary>
                <div style={{ marginTop: 12 }}>
                  {/* Lists and orders show the learner's own attempt with wrong rows/positions marked;
                      the explanation below spells out the correct one. */}
                  <ItemView item={it} value={answers[it.id]} locked onChange={() => {}} detail={r.detail}
                    answer={['mcq', 'graph_select', 'short_answer'].includes(it.type) ? r.answer : undefined} />
                  {r.feedback && <p className="small" style={{ marginTop: 10 }}><b>{r.feedback}</b></p>}
                  {r.explanation && <p className="small muted" style={{ marginTop: 4 }}>{r.explanation}</p>}
                </div>
              </details>
            )
          })}
        </div>
      </div>
    </div>
  )
}
