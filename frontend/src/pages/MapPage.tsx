// The course map is itself a path through a labyrinth: modules are rooms, the golden thread
// runs through every module you've completed, and the next room pulses.

import { useNavigate } from 'react-router-dom'
import { useMe, useModules } from '../api/hooks'
import type { Me, ModuleSummary } from '../api/types'
import { Icon } from '../components/Icon'
import { Meter, Stars, masteryStatus } from '../components/bits'

const POS = [
  { x: 90, y: 100 }, { x: 290, y: 60 }, { x: 540, y: 110 }, { x: 380, y: 280 },
  { x: 130, y: 330 }, { x: 330, y: 470 }, { x: 560, y: 430 },
]

function QuestMap({ modules }: { modules: ModuleSummary[] }) {
  const navigate = useNavigate()
  const current = modules.find((m) => m.unlocked && !m.completed)
  const lastDone = modules.reduce((acc, m, i) => (m.completed ? i : acc), -1)
  const pathD = (pts: { x: number; y: number }[]) =>
    pts.map((p, i) => {
      if (i === 0) return `M ${p.x} ${p.y}`
      const prev = pts[i - 1]
      const mx = (prev.x + p.x) / 2
      return `C ${mx} ${prev.y}, ${mx} ${p.y}, ${p.x} ${p.y}`
    }).join(' ')
  const donePts = POS.slice(0, Math.min(modules.length, lastDone + 2 > 0 && current ? lastDone + 2 : lastDone + 1))

  return (
    <div className="card quest-map">
      <svg className="quest-svg" viewBox="0 0 660 560" role="list" aria-label="Course map">
        <path className="qpath" d={pathD(POS.slice(0, modules.length))} />
        {donePts.length > 1 && <path className="qpath-done" d={pathD(donePts)} />}
        {modules.map((m, i) => {
          const p = POS[i]
          const isCurrent = current?.slug === m.slug
          const boss = m.slug === 'minotaur'
          const r = boss ? 44 : 38
          const cls = ['qnode', !m.unlocked && 'locked', m.completed && 'done', isCurrent && 'current', boss && 'boss'].filter(Boolean).join(' ')
          const go = () => m.unlocked && navigate(`/learn/${m.slug}`)
          return (
            <g key={m.slug} className={cls} role="listitem" tabIndex={m.unlocked ? 0 : -1}
              aria-label={`${m.title}${m.completed ? ', completed' : !m.unlocked ? ', locked' : ''}`}
              onClick={go} onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && go()}>
              {isCurrent && <circle className="pulse" cx={p.x} cy={p.y} r={r} />}
              <circle className="disc" cx={p.x} cy={p.y} r={r} />
              <foreignObject x={p.x - 14} y={p.y - 14} width={28} height={28} style={{ pointerEvents: 'none' }}>
                <div className="qicon" style={{ display: 'grid', placeItems: 'center', width: 28, height: 28 }}>
                  <Icon name={!m.unlocked ? 'lock' : m.icon} size={boss ? 28 : 24} />
                </div>
              </foreignObject>
              <text className="qtitle" x={p.x} y={p.y + r + 22}>{m.title}</text>
              <text className="qsub" x={p.x} y={p.y + r + 40}>
                {m.order === 0 ? 'Prologue' : m.slug === 'minotaur' ? 'Final trial' : `Objective ${m.objective}`}
                {m.max_stars > 0 ? ` · ★ ${m.stars}/${m.max_stars}` : m.completed ? ' · ✓' : ''}
              </text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}

function Sidebar({ me, modules }: { me: Me; modules: ModuleSummary[] }) {
  const navigate = useNavigate()
  const lv = me.level
  const earned = me.badges.filter((b) => b.earned_at)
  return (
    <div className="side-stack">
      <div className="card">
        <div className="row">
          <div className="hud-level" style={{ minWidth: 0, flex: 1 }}>
            <div className="lvl" style={{ width: 44, height: 44, fontSize: 18, borderRadius: 13 }}>{lv.level}</div>
            <div className="meta" style={{ fontSize: 13 }}>
              <span className="eyebrow">Level {lv.level}</span>
              <span style={{ fontWeight: 700, fontSize: 16 }}>{lv.title}</span>
            </div>
          </div>
          <span className="hud-pill"><Icon name="flame" size={16} className="flame" /> {me.streak_days} day{me.streak_days === 1 ? '' : 's'}</span>
        </div>
        <div style={{ marginTop: 14 }}>
          <Meter value={lv.progress} color="var(--thread)" size="thick" label="Progress to next level" />
          <div className="row small muted" style={{ marginTop: 6, justifyContent: 'space-between' }}>
            <span>{lv.xp} XP</span><span>{lv.next ? `${lv.next - lv.xp} XP to level ${lv.level + 1}` : 'Max level'}</span>
          </div>
        </div>
        <div className="row small muted" style={{ marginTop: 10, gap: 16 }}>
          <span><b style={{ color: 'var(--ink)' }}>{me.stats.completed}</b>/{me.stats.total} activities</span>
          <span><Stars count={1} max={1} size={13} /> <b style={{ color: 'var(--ink)' }}>{me.stats.stars}</b>/{me.stats.max_stars}</span>
        </div>
      </div>

      {me.recommendations.length > 0 && (
        <div className="card">
          <div className="card-title"><Icon name="target" size={18} /> Up next for you</div>
          <div className="stack-v">
            {me.recommendations.map((r) => (
              <button key={`${r.type}${r.activity_id}`} className={`rec ${r.type}`} onClick={() => navigate(`/learn/${r.module}/${r.activity_id}`)}>
                <span className="ic"><Icon name={r.type === 'continue' ? 'play' : 'undo'} /></span>
                <span style={{ flex: 1 }}>
                  <b>{r.type === 'continue' ? r.title : `Revise: ${r.title}`}</b><br />
                  <span className="small muted">{r.reason}</span>
                </span>
                <Icon name="chevronRight" />
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-title"><Icon name="layers" size={18} /> Mastery by objective <span className="faint small">target 70%</span></div>
        {me.mastery.map((m) => {
          const st = masteryStatus(m.value, m.evidence)
          const mod = modules.find((x) => x.slug === m.module)
          return (
            <div className="mastery-row" key={m.objective} title={`${m.statement} (${m.evidence} assessment${m.evidence === 1 ? '' : 's'})`}>
              <span className="name">{m.objective}. {m.title}</span>
              <span className="val">{m.evidence ? `${Math.round(m.value * 100)}%` : '—'}</span>
              <Meter value={m.value} color={st.color} target={0.7} size="thin" label={`${m.title} mastery`} />
              <span className="meta">
                <span className="status"><Icon name={st.icon} size={13} style={{ color: st.color }} /> {st.label}</span>
                <span>· {m.bloom}</span>
                {mod && !mod.unlocked && <span>· locked</span>}
              </span>
            </div>
          )
        })}
      </div>

      <div className="card">
        <div className="card-title"><Icon name="trophy" size={18} /> Badges <span className="faint small">{earned.length}/{me.badges.length}</span></div>
        <div className="badge-grid">
          {me.badges.slice(0, 10).map((b) => (
            <div key={b.id} className={`badge-tile ${b.earned_at ? 'earned' : ''}`} title={`${b.name}: ${b.description}`}>
              <div className="medal"><Icon name={b.earned_at ? b.icon : 'lock'} size={22} /></div>
              <span>{b.name}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export function MapPage() {
  const { data: me } = useMe()
  const { data: modules, isLoading } = useModules()
  if (isLoading || !modules || !me) return <div className="map-layout"><div className="skeleton" style={{ height: 560 }} /><div className="skeleton" style={{ height: 560 }} /></div>
  const firstTime = me.stats.completed === 0
  return (
    <>
      <div style={{ marginBottom: 20 }}>
        <div className="eyebrow">{firstTime ? 'Welcome, explorer' : `Welcome back, ${me.display_name}`}</div>
        <h1 style={{ marginTop: 6 }}>{firstTime ? 'Your thread starts here.' : 'The Labyrinth awaits.'}</h1>
        <p className="muted" style={{ marginTop: 8, maxWidth: 640 }}>
          Seven rooms stand between you and mastery of depth-first search. Each one unlocks the next — and the golden thread
          marks the way you have come.
        </p>
      </div>
      <div className="map-layout">
        <QuestMap modules={modules} />
        <Sidebar me={me} modules={modules} />
      </div>
    </>
  )
}
