import { Link } from 'react-router-dom'
import { useMe } from '../api/hooks'
import { Icon } from '../components/Icon'
import { BLOOM_COLORS, Meter, avatarColor, masteryStatus } from '../components/bits'

export function ProfilePage() {
  const { data: me } = useMe()
  if (!me) return <div className="skeleton" style={{ height: 500 }} />
  const earned = me.badges.filter((b) => b.earned_at).length
  return (
    <div className="stack-v" style={{ gap: 20 }}>
      <div className="row" style={{ gap: 16 }}>
        <span className="avatar" style={{ width: 64, height: 64, fontSize: 28, borderRadius: 20, background: avatarColor(me.username) }}>
          {me.display_name.slice(0, 1).toUpperCase()}
        </span>
        <div>
          <h1>{me.display_name}</h1>
          <div className="muted">@{me.username} · Level {me.level.level} {me.level.title}</div>
        </div>
      </div>

      <div className="tiles">
        <div className="tile"><div className="label">Total XP</div><div className="value">{me.level.xp.toLocaleString()}</div>
          <div className="sub">{me.level.next ? `${me.level.next - me.level.xp} to level ${me.level.level + 1}` : 'Max level'}</div></div>
        <div className="tile"><div className="label">Activities completed</div><div className="value">{me.stats.completed}<span className="faint" style={{ fontSize: 18 }}>/{me.stats.total}</span></div></div>
        <div className="tile"><div className="label">Stars</div><div className="value">{me.stats.stars}<span className="faint" style={{ fontSize: 18 }}>/{me.stats.max_stars}</span></div><div className="sub">on challenges and quizzes</div></div>
        <div className="tile"><div className="label">Streak</div><div className="value">{me.streak_days}</div><div className="sub">day{me.streak_days === 1 ? '' : 's'} in a row</div></div>
        <div className="tile"><div className="label">Attempts</div><div className="value">{me.stats.attempts}</div><div className="sub">practice makes permanent</div></div>
      </div>

      <div className="card">
        <div className="card-title"><Icon name="layers" size={18} /> Mastery report <span className="faint small">running estimate per instructional objective · target 70%</span></div>
        <div style={{ overflowX: 'auto' }}>
          <table className="table">
            <thead><tr><th>Objective</th><th>Skill level</th><th style={{ minWidth: 180 }}>Mastery</th><th>Status</th><th className="num">Evidence</th><th /></tr></thead>
            <tbody>
              {me.mastery.map((m) => {
                const st = masteryStatus(m.value, m.evidence)
                return (
                  <tr key={m.objective}>
                    <td><b>{m.objective}. {m.title}</b><br /><span className="small faint">{m.statement}</span></td>
                    <td><span className={BLOOM_COLORS[m.bloom] ?? 'chip'}>{m.bloom}</span></td>
                    <td>
                      <div className="row"><div style={{ flex: 1 }}><Meter value={m.value} color={st.color} target={0.7} label={`${m.title} mastery`} /></div>
                        <b style={{ width: 44, textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>{m.evidence ? `${Math.round(m.value * 100)}%` : '—'}</b></div>
                    </td>
                    <td><span className="status"><Icon name={st.icon} size={14} style={{ color: st.color }} /> {st.label}</span></td>
                    <td className="num">{m.evidence}</td>
                    <td><Link to={`/learn/${m.module}`} className="btn sm ghost">Practise <Icon name="chevronRight" size={14} /></Link></td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <div className="card-title"><Icon name="trophy" size={18} /> Badges <span className="faint small">{earned}/{me.badges.length}</span></div>
        <div className="badge-big">
          {me.badges.map((b) => (
            <div key={b.id} className={`badge-card ${b.earned_at ? 'earned' : ''}`}>
              <div className="medal"><Icon name={b.earned_at ? b.icon : 'lock'} size={24} /></div>
              <div>
                <div style={{ fontWeight: 700 }}>{b.name}</div>
                <div className="small muted">{b.description}</div>
                {b.earned_at && <div className="tiny faint">Earned {new Date(b.earned_at).toLocaleDateString()}</div>}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
