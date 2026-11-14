import { useCallback, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useModule, useModules } from '../api/hooks'
import type { Activity, Reward } from '../api/types'
import { CompareActivity } from '../activities/CompareActivity'
import { DemoActivity } from '../activities/DemoActivity'
import { InspectActivity } from '../activities/InspectActivity'
import { LessonActivity } from '../activities/LessonActivity'
import { MazeActivity } from '../activities/MazeActivity'
import { QuizActivity } from '../activities/QuizActivity'
import { RepresentActivity } from '../activities/RepresentActivity'
import { TraceActivity } from '../activities/TraceActivity'
import type { ActivityProps, RewardMeta } from '../activities/shared'
import { Icon } from '../components/Icon'
import { RewardModal } from '../components/RewardModal'
import { BLOOM_COLORS, Stars } from '../components/bits'
import { flushQuizDraft, followQuizStudy } from '../activities/useQuizDraft'

const COMPONENTS: Record<Activity['kind'], (p: ActivityProps) => JSX.Element> = {
  lesson: LessonActivity,
  maze: MazeActivity,
  inspect: InspectActivity,
  represent: RepresentActivity,
  demo: DemoActivity,
  trace: TraceActivity,
  compare: CompareActivity,
  quiz: QuizActivity,
}

const KIND_LABEL: Record<Activity['kind'], string> = {
  lesson: 'Learn', maze: 'Explore', inspect: 'Explore', represent: 'Explore', demo: 'Watch', trace: 'Practice', compare: 'Watch', quiz: 'Assess',
}

const OBJ = {
  1: { bloom: 'Explain', verb: 'Identify & describe',
    statement: "Identify vertices and edges, tell one-way from two-way connections, and find a vertex's degree." },
  2: { bloom: 'Explain', verb: 'Translate & illustrate',
    statement: 'Write a graph as an adjacency list or matrix, and read its connections back from either representation.' },
  3: { bloom: 'Apply', verb: 'Trace & execute',
    statement: "Trace DFS from the stated start and neighbour order, recording each vertex's first visit." },
  4: { bloom: 'Apply / Analyse', verb: 'Track & record',
    statement: 'Track visited vertices and the current-path stack, and decide when DFS should backtrack.' },
  5: { bloom: 'Evaluate', verb: 'Compare & contrast',
    statement: 'Compare DFS and BFS visit orders, and explain the role of a stack versus a queue.' },
} as Record<number, { bloom: string; verb: string; statement: string }>

export function ModulePage() {
  const { slug = '', activityId } = useParams()
  const navigate = useNavigate()
  const [query] = useSearchParams()
  const { data: mod, error, isLoading } = useModule(slug)
  const { data: modules } = useModules()
  const [reward, setReward] = useState<{ reward: Reward; meta: RewardMeta } | null>(null)
  const [runKey, setRunKey] = useState(0)

  const onReward = useCallback((r: Reward, meta: RewardMeta) => setReward({ reward: r, meta }), [])

  if (isLoading) return <div className="skeleton" style={{ height: 520 }} />
  if (error || !mod) {
    return (
      <div className="card empty-state">
        <Icon name="lock" size={36} />
        <h2 style={{ margin: '12px 0 6px' }}>This room is still locked</h2>
        <p>Finish the earlier modules to open it.</p>
        <Link to="/" className="btn primary" style={{ marginTop: 16 }}><Icon name="map" /> Back to the map</Link>
      </div>
    )
  }

  const acts = mod.activities
  const current = acts.find((a) => a.id === activityId && a.state.unlocked)
    ?? acts.find((a) => a.state.unlocked && !a.state.completed)
    ?? acts[0]
  const Component = COMPONENTS[current.kind]
  const course = mod.track === 'course'
  const objective = current.objective ?? mod.objective
  const objectiveIds = (current.config.mode === 'summative'
    ? Object.keys(OBJ).map(Number) : objective ? [objective] : []).filter((id) => OBJ[id])
  const gameCount = modules ? modules.filter((m) => m.track === 'game').length - 1 : 6
  // The intro-course lesson that teaches this module, if the learner can open it.
  const lesson = mod.lesson ? modules?.flatMap((m) => m.activities.map((a) => ({ m, a }))).find((x) => x.a.id === mod.lesson) : undefined
  const returnQuiz = modules?.flatMap((m) => m.activities.map((a) => ({ m, a })))
    .find((x) => x.a.id === query.get('returnQuiz') && x.a.kind === 'quiz' && x.a.unlocked && x.m.unlocked)

  const goNext = () => {
    const next = reward?.reward.next_activity
    setReward(null)
    if (!next) return navigate('/')
    const nextModule = modules?.find((m) => m.activities.some((a) => a.id === next))
    if (nextModule && nextModule.slug !== mod.slug) navigate(nextModule.unlocked || reward?.reward.completed ? `/learn/${nextModule.slug}` : '/')
    else navigate(`/learn/${mod.slug}/${next}`)
  }

  const goActivity = async (a: Activity) => {
    const href = `/learn/${mod.slug}/${a.id}`
    if (a.kind !== 'quiz' && await followQuizStudy(href, a.id)) return
    await flushQuizDraft()
    navigate(href)
  }

  return (
    <div>
      <div className="row wrap small" style={{ marginBottom: 14 }}>
        <Link to="/" className="btn sm ghost"><Icon name="chevronLeft" size={16} /> Map</Link>
        {returnQuiz && <Link to={`/learn/${returnQuiz.m.slug}/${returnQuiz.a.id}`} className="btn sm ghost">
          <Icon name="chevronLeft" size={16} /> Return to quiz
        </Link>}
        <span className="faint">{course ? `Intro course · ${acts.length} short lessons` : `Module ${mod.order} of ${gameCount}`}</span>
      </div>

      <div className="module-hero">
        <div className="eyebrow" style={{ color: 'var(--thread)' }}>{mod.tagline}</div>
        <h1 style={{ marginTop: 6 }}>{mod.title}</h1>
        <section className="objective-card" aria-labelledby="learning-goals-title">
          <Icon name="target" size={20} className="ic" />
          <div className="objective-content">
            <h2 id="learning-goals-title">Learning goals</h2>
            {objectiveIds.length > 0 ? (
              <ul className="objective-list">
                {objectiveIds.map((id) => {
                  const obj = OBJ[id]
                  return (
                    <li key={id}>
                      <div className="row" style={{ gap: 6, flexWrap: 'wrap' }}>
                        <span className="eyebrow">Objective {id}</span>
                        {objectiveIds.length === 1 && <span className={BLOOM_COLORS[obj.bloom] ?? 'chip'}>{obj.bloom} · {obj.verb}</span>}
                      </div>
                      <p className="objective-outcome">{obj.statement}</p>
                    </li>
                  )
                })}
              </ul>
            ) : (
              <>
                <span className="eyebrow">{mod.order === 0 ? 'Warm-up' : 'Module focus'}</span>
                <p className="objective-outcome">{mod.outcome}</p>
              </>
            )}
            {lesson?.a.unlocked && (
              <Link to={`/learn/${lesson.m.slug}/${lesson.a.id}`} className="revisit small">
                <Icon name="book" size={14} /> Need a refresher? Revisit the lesson <b>{lesson.a.title}</b>
              </Link>
            )}
          </div>
        </section>
        <p className="story">{mod.story}</p>
      </div>

      {acts.length > 1 && (
        <nav className="steps" aria-label="Activities in this module">
          {acts.map((a, i) => (
            <button key={a.id} className={`step ${a.id === current.id ? 'active' : ''} ${a.state.completed ? 'done' : ''}`}
              disabled={!a.state.unlocked}
              onClick={() => void goActivity(a).catch(() => {})}
              aria-current={a.id === current.id ? 'step' : undefined}>
              <span className="num">{a.state.completed ? <Icon name="check" size={16} /> : !a.state.unlocked ? <Icon name="lock" size={14} /> : i + 1}</span>
              <span>
                <span className="s-title">{a.title}</span>
                <span className="s-meta">{KIND_LABEL[a.kind]} · {a.xp} XP {['trace', 'quiz'].includes(a.kind) && a.state.attempts > 0 && <Stars count={a.state.best_stars} size={11} />}</span>
              </span>
            </button>
          ))}
        </nav>
      )}

      <div className="activity-intro">
        <h2>{current.title}</h2>
        <span className="chip">{KIND_LABEL[current.kind]}</span>
        {current.state.completed && <span className="chip chalk"><Icon name="check" size={12} /> Completed{['trace', 'quiz'].includes(current.kind) ? ' · replay to improve' : ''}</span>}
        <p className="muted" style={{ flexBasis: '100%' }}>{current.summary}</p>
      </div>

      <Component key={`${current.id}-${runKey}`} activity={current} onReward={onReward} />

      {reward && (
        <RewardModal
          reward={reward.reward}
          graded={reward.meta.graded}
          title={reward.meta.title}
          subtitle={reward.meta.subtitle}
          onRetry={() => { setReward(null); setRunKey((k) => k + 1) }}
          onContinue={goNext}
          continueLabel={reward.reward.completed ? (reward.reward.next_activity ? 'Next' : 'Back to the map') : 'Back to the map'}
        />
      )}
    </div>
  )
}
