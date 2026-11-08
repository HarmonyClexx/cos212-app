import { useLeaderboard } from '../api/hooks'
import { Icon } from '../components/Icon'
import { avatarColor } from '../components/bits'

export function LeaderboardPage() {
  const { data, isLoading } = useLeaderboard()
  return (
    <div className="stack-v" style={{ gap: 20 }}>
      <div>
        <div className="eyebrow">Hall of explorers</div>
        <h1 style={{ marginTop: 6 }}>Leaderboard</h1>
        <p className="muted" style={{ marginTop: 8, maxWidth: 620 }}>
          XP is only earned for <em>improvement</em> — replaying an activity you've already aced earns nothing, so this board
          rewards learning, not grinding.
        </p>
      </div>
      {data && (
        <div className="tiles">
          <div className="tile"><div className="label">Your rank</div><div className="value">#{data.me.rank}</div><div className="sub">of everyone in the course</div></div>
          <div className="tile"><div className="label">Your XP</div><div className="value">{data.me.xp.toLocaleString()}</div><div className="sub">Level {data.me.level} · {data.me.title}</div></div>
          <div className="tile"><div className="label">Badges</div><div className="value">{data.me.badges}</div><div className="sub">of 10</div></div>
        </div>
      )}
      <div className="card" style={{ padding: 0, overflowX: 'auto' }}>
        {isLoading && <div className="skeleton" style={{ height: 300, margin: 20 }} />}
        {data && (
          <table className="table">
            <thead>
              <tr><th style={{ width: 70 }}>Rank</th><th>Explorer</th><th>Title</th><th className="num">Badges</th><th className="num">Streak</th><th className="num">XP</th></tr>
            </thead>
            <tbody>
              {data.top.map((r) => (
                <tr key={r.username} className={r.is_me ? 'me' : ''}>
                  <td><span className={`rank ${r.rank <= 3 ? `r${r.rank}` : ''}`}>{r.rank}</span></td>
                  <td>
                    <div className="row">
                      <span className="avatar" style={{ background: avatarColor(r.username) }}>{r.display_name.slice(0, 1).toUpperCase()}</span>
                      <span><b>{r.display_name}</b>{r.is_me && <span className="chip brand" style={{ marginLeft: 8 }}>you</span>}<br /><span className="faint small">@{r.username}</span></span>
                    </div>
                  </td>
                  <td className="muted">Lv {r.level} · {r.title}</td>
                  <td className="num">{r.badges}</td>
                  <td className="num">{r.streak_days > 0 ? <span className="row" style={{ justifyContent: 'flex-end', gap: 4 }}><Icon name="flame" size={14} style={{ color: 'var(--danger)' }} />{r.streak_days}</span> : '—'}</td>
                  <td className="num">{r.xp.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
