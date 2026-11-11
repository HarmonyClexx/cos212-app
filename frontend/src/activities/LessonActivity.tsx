// Intro course: the *explanation* step that comes before the game's demonstration, practice
// and assessment (design doc 2.2; Gagné event 4 "present the content").
//
// A lesson is a few short pages, each a bit of reading beside a figure to try, usually ending in
// a quick check (retrieval practice). A wrong pick is answered with why it's wrong, and the learner
// tries again; the next page opens once the check is right. A recap closes the lesson.

import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMe, useModules, useSubmitActivity } from '../api/hooks'
import type { LessonCheck } from '../api/types'
import { Icon } from '../components/Icon'
import { Inline, Prose } from '../components/Prose'
import { FeedbackBox } from '../components/bits'
import { LessonFigureView } from './lesson/LessonFigures'
import type { ActivityProps } from './shared'

interface Saved {
  page: number
  picked: Record<string, number>
  tries: Record<string, number>
}

// Per-tab convenience only: losing it just means starting the lesson from page 1 again.
const storeKey = (userId: number, id: string) => `ariadne:lesson:${userId}:${id}`
function load(userId: number, id: string): Saved | null {
  try {
    // Older drafts have no owner and cannot safely be assigned to this account.
    sessionStorage.removeItem(`ariadne:lesson:${id}`)
    const raw = sessionStorage.getItem(storeKey(userId, id))
    return raw ? (JSON.parse(raw) as Saved) : null
  } catch {
    return null
  }
}
function save(userId: number, id: string, s: Saved | null) {
  try {
    if (s) sessionStorage.setItem(storeKey(userId, id), JSON.stringify(s))
    else sessionStorage.removeItem(storeKey(userId, id))
  } catch { /* storage unavailable: fine */ }
}

function Check({ check, picked, tries, onPick }: {
  check: LessonCheck
  picked: number | undefined
  tries: number
  onPick: (i: number) => void
}) {
  const solved = picked === check.answer
  return (
    <div className="card lesson-check">
      <div className="eyebrow" style={{ color: 'var(--brand)' }}><Icon name="target" size={14} /> Quick check</div>
      <div className="item-prompt"><Inline text={check.prompt} /></div>
      <div className="options" role="group" aria-label="Answer options">
        {check.options.map((o, i) => {
          const state = picked === i ? (i === check.answer ? 'correct' : 'wrong') : ''
          return (
            <button key={i} className={`option ${state}`} disabled={solved} onClick={() => onPick(i)}
              aria-pressed={picked === i}>
              <span className="key">{String.fromCharCode(65 + i)}</span><span><Inline text={o} /></span>
            </button>
          )
        })}
      </div>
      {picked !== undefined && (
        <FeedbackBox fb={solved
          ? { tone: 'good', tier: 0, title: tries === 1 ? 'Spot on.' : 'That’s it.' }
          : { tone: 'warn', tier: 0, title: 'Not quite. Try another answer.' }}>
          <div className="b"><Inline text={check.why[picked]} /></div>
        </FeedbackBox>
      )}
    </div>
  )
}

export function LessonActivity(props: ActivityProps) {
  const { data: me, error, refetch, isFetching } = useMe()
  if (!me) {
    return error ? (
      <div className="card">
        <p className="error-text" role="alert">Couldn’t load your account to open the lesson.</p>
        <button className="btn" disabled={isFetching} onClick={() => void refetch()}>Retry</button>
      </div>
    ) : <div className="skeleton" style={{ height: 320 }} aria-label="Loading lesson" />
  }
  return <LearnerLesson key={`${me.id}:${props.activity.id}`} {...props} userId={me.id} />
}

function LearnerLesson({ activity, onReward, userId }: ActivityProps & { userId: number }) {
  const lesson = activity.config.lesson!
  const done = activity.state.completed
  const { data: modules } = useModules()
  const navigate = useNavigate()
  const submit = useSubmitActivity(activity.id)
  const top = useRef<HTMLDivElement>(null)
  const first = useRef(true)

  const [saved] = useState(() => load(userId, activity.id))
  const [page, setPage] = useState(() => Math.min(saved?.page ?? 0, lesson.pages.length))
  const [picked, setPicked] = useState<Record<string, number>>(saved?.picked ?? {})
  const [tries, setTries] = useState<Record<string, number>>(saved?.tries ?? {})

  useEffect(() => save(userId, activity.id, { page, picked, tries }), [userId, activity.id, page, picked, tries])
  useEffect(() => {
    if (first.current) { first.current = false; return }
    top.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [page])

  const solved = (c: LessonCheck | null) => !c || picked[c.id] === c.answer
  // How far the learner may go: up to and including the first page with an unanswered check.
  const firstOpen = lesson.pages.findIndex((p) => !solved(p.check))
  const reachable = done || firstOpen === -1 ? lesson.pages.length : firstOpen
  const onSummary = page === lesson.pages.length
  const p = lesson.pages[page]

  const intro = modules?.find((m) => m.track === 'course')
  const index = intro?.activities.findIndex((a) => a.id === activity.id) ?? -1
  const nextLesson = index >= 0 ? intro?.activities[index + 1] : undefined
  const practice = modules?.find((m) => m.slug === lesson.practice)

  const pick = (c: LessonCheck, i: number) => {
    if (picked[c.id] === c.answer) return
    setPicked((x) => ({ ...x, [c.id]: i }))
    setTries((x) => ({ ...x, [c.id]: (x[c.id] ?? 0) + 1 }))
  }

  const finish = () => submit.mutate(
    { data: { answers: picked, tries } },
    {
      onSuccess: ({ reward }) => {
        save(userId, activity.id, null)
        onReward(reward, {
          graded: false,
          title: nextLesson ? 'Lesson complete' : 'Intro course complete!',
          subtitle: nextLesson ? `Next lesson: ${nextLesson.title}.` : 'The Labyrinth is open. Time to put it all to work.',
        })
      },
    },
  )

  const pageLabel = (i: number) => (i === lesson.pages.length ? 'Summary' : lesson.pages[i].title)

  return (
    <div className="lesson" ref={top}>
      <div className="lesson-top">
        <span className="chip brand"><Icon name="book" size={13} /> Lesson {index + 1} of {intro?.activities.length ?? 5}</span>
        <span className="faint small">about {lesson.minutes} min</span>
        <nav className="lesson-dots" aria-label="Lesson pages">
          {[...lesson.pages.map((_, i) => i), lesson.pages.length].map((i) => (
            <button key={i} className={`ldot ${i === page ? 'current' : ''} ${i < page || (done && i !== page) ? 'seen' : ''}`}
              disabled={i > reachable} onClick={() => setPage(i)}
              aria-label={`Page ${i + 1}: ${pageLabel(i)}`} aria-current={i === page ? 'step' : undefined} title={pageLabel(i)} />
          ))}
        </nav>
      </div>

      {!onSummary && p && (
        <>
          <div className={`lesson-grid ${p.figure ? '' : 'solo'}`}>
            <article className="card lesson-text">
              <div className="eyebrow">Page {page + 1} of {lesson.pages.length}</div>
              <h2>{p.title}</h2>
              <Prose text={p.body} />
              {p.code && <pre className="lesson-code" aria-label="Pseudocode"><code>{p.code}</code></pre>}
            </article>
            {p.figure && <div className="card flat lesson-figure"><LessonFigureView fig={p.figure} /></div>}
          </div>
          {p.check && (
            <Check key={p.check.id} check={p.check} picked={picked[p.check.id]} tries={tries[p.check.id] ?? 0}
              onPick={(i) => pick(p.check!, i)} />
          )}
        </>
      )}

      {onSummary && (
        <div className="card lesson-summary">
          <div className="eyebrow">Summary</div>
          <h2>In a nutshell</h2>
          <ul className="recap">
            {lesson.recap.map((r, i) => <li key={i}><Icon name="check" size={16} /><span><Inline text={r} /></span></li>)}
          </ul>
          {practice && (
            <p className="muted small" style={{ marginTop: 14 }}>
              <Icon name="map" size={14} /> In the game, <b>{practice.title}</b> (Module {practice.order}) puts this lesson to work.
            </p>
          )}
        </div>
      )}

      <div className="lesson-nav">
        <button className="btn" onClick={() => setPage((x) => Math.max(0, x - 1))} disabled={page === 0}>
          <Icon name="chevronLeft" /> Back
        </button>
        <span className="spacer" />
        {!onSummary && (
          <button className={`btn ${solved(p?.check ?? null) ? 'primary' : ''}`} onClick={() => setPage((x) => x + 1)}
            disabled={page >= reachable} title={page >= reachable ? 'Answer the quick check first' : undefined}>
            {page === lesson.pages.length - 1 ? 'Summary' : 'Next'} <Icon name="chevronRight" />
          </button>
        )}
        {onSummary && !done && (
          <button className="btn gold" onClick={finish} disabled={submit.isPending}>
            <Icon name="check" /> Finish lesson · +{activity.xp} XP
          </button>
        )}
        {onSummary && done && (
          <button className="btn primary" onClick={() => navigate(nextLesson ? `/learn/${intro!.slug}/${nextLesson.id}` : '/')}>
            {nextLesson ? <>Next lesson <Icon name="chevronRight" /></> : <><Icon name="map" /> Back to the map</>}
          </button>
        )}
      </div>
      {submit.isError && <p className="error-text" role="alert">Couldn’t save that. Check your connection and try again.</p>}
    </div>
  )
}
