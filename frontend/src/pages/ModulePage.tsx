import { useCallback, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useModule, useModules } from '../api/hooks'
import type { Activity, Reward } from '../api/types'
import { CompareActivity } from '../activities/CompareActivity'
import { DemoActivity } from '../activities/DemoActivity'
import { InspectActivity } from '../activities/InspectActivity'
import { MazeActivity } from '../activities/MazeActivity'
import { QuizActivity } from '../activities/QuizActivity'
import { RepresentActivity } from '../activities/RepresentActivity'
import { TraceActivity } from '../activities/TraceActivity'
import type { ActivityProps, RewardMeta } from '../activities/shared'
import { Icon } from '../components/Icon'
import { RewardModal } from '../components/RewardModal'
import { BLOOM_COLORS, Stars } from '../components/bits'
import { flushQuizDraft } from '../activities/useQuizDraft'

const COMPONENTS: Record<Activity['kind'], (p: ActivityProps) => JSX.Element> = {
  maze: MazeActivity,
  inspect: InspectActivity,
  represent: RepresentActivity,
  demo: DemoActivity,
  trace: TraceActivity,
  compare: CompareActivity,
  quiz: QuizActivity,
}

const KIND_LABEL: Record<Activity['kind'], string> = {
  maze: 'Explore', inspect: 'Explore', represent: 'Explore', demo: 'Watch', trace: 'Practice', compare: 'Watch', quiz: 'Assess',
}

const OBJ = {
  1: { bloom: 'Explain', verb: 'Identify & describe' },
  2: { bloom: 'Explain', verb: 'Translate & illustrate' },
  3: { bloom: 'Apply', verb: 'Trace & execute' },
  4: { bloom: 'Apply / Analyse', verb: 'Track & record' },
  5: { bloom: 'Evaluate', verb: 'Compare & contrast' },
} as Record<number, { bloom: string; verb: string }>

export function ModulePage() {
  const { slug = '', activityId } = useParams()
  const navigate = useNavigate()
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
  const obj = mod.objective ? OBJ[mod.objective] : null

  const goNext = () => {
    const next = reward?.reward.next_activity
    setReward(null)
    if (!next) return navigate('/')
    const nextModule = modules?.find((m) => m.activities.some((a) => a.id === next))
    if (nextModule && nextModule.slug !== mod.slug) navigate(nextModule.unlocked || reward?.reward.completed ? `/learn/${nextModule.slug}` : '/')
    else navigate(`/learn/${mod.slug}/${next}`)
  }

  return (
    <div>
      <div className="row small" style={{ marginBottom: 14 }}>
        <Link to="/" className="btn sm ghost"><Icon name="chevronLeft" size={16} /> Map</Link>
        <span className="faint">Module {mod.order} of 6</span>
      </div>

      <div className="module-hero">
        <div>
          <div className="eyebrow" style={{ color: 'var(--thread)' }}>{mod.tagline}</div>
          <h1 style={{ marginTop: 6 }}>{mod.title}</h1>
          <p className="story">{mod.story}</p>
        </div>
        <div className="objective-card">
          <Icon name="target" size={20} className="ic" />
          <div>
            <div className="row" style={{ gap: 6, marginBottom: 4, flexWrap: 'wrap' }}>
              <span className="eyebrow">{mod.objective ? `Objective ${mod.objective}` : mod.order === 0 ? 'Warm-up' : 'All objectives'}</span>
              {obj && <span className={BLOOM_COLORS[obj.bloom] ?? 'chip'}>{obj.bloom} · {obj.verb}</span>}
            </div>
            <div className="small">{mod.outcome}</div>
          </div>
        </div>
      </div>

      {acts.length > 1 && (
        <nav className="steps" aria-label="Activities in this module">
          {acts.map((a, i) => (
            <button key={a.id} className={`step ${a.id === current.id ? 'active' : ''} ${a.state.completed ? 'done' : ''}`}
              disabled={!a.state.unlocked}
              onClick={() => void flushQuizDraft().then(() => navigate(`/learn/${mod.slug}/${a.id}`)).catch(() => {})}
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
          subtitle={reward.meta.subtitle}
          onRetry={() => { setReward(null); setRunKey((k) => k + 1) }}
          onContinue={goNext}
          continueLabel={reward.reward.completed ? (reward.reward.next_activity ? 'Next' : 'Back to the map') : 'Back to the map'}
        />
      )}
    </div>
  )
}
