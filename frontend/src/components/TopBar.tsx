import { NavLink } from 'react-router-dom'
import { useMe } from '../api/hooks'
import { useAuth } from '../lib/auth'
import { useTheme } from '../lib/theme'
import { Icon, Logo } from './Icon'
import { Meter } from './bits'

export function TopBar() {
  const { logout } = useAuth()
  const { data: me } = useMe()
  const [theme, toggleTheme] = useTheme()
  const lv = me?.level

  return (
    <header className="topbar">
      <div className="container topbar-inner">
        <NavLink to="/" className="logo" aria-label="Ariadne home"><Logo /><span>Ariadne</span></NavLink>
        <nav className="nav" aria-label="Main">
          <NavLink to="/" end><Icon name="map" /><span>Map</span></NavLink>
          <NavLink to="/leaderboard"><Icon name="trophy" /><span>Leaderboard</span></NavLink>
          <NavLink to="/profile"><Icon name="user" /><span>Profile</span></NavLink>
        </nav>
        <div className="hud">
          {me && (
            <>
              <span className="hud-pill" title="Daily learning streak">
                <Icon name="flame" size={16} className="flame" /> {me.streak_days}
              </span>
              <span className="hud-pill xp" title="Total XP"><Icon name="bolt" size={16} className="bolt" /> {lv!.xp}</span>
              <div className="hud-level" title={`${lv!.title} — ${lv!.next ? `${lv!.next - lv!.xp} XP to level ${lv!.level + 1}` : 'max level'}`}>
                <div className="lvl">{lv!.level}</div>
                <div className="meta">
                  <span style={{ fontWeight: 600 }}>{lv!.title}</span>
                  <Meter value={lv!.progress} color="var(--thread)" size="thin" label="Progress to next level" />
                </div>
              </div>
            </>
          )}
          <button className="icon-btn" onClick={toggleTheme} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}>
            <Icon name={theme === 'dark' ? 'sun' : 'moon'} />
          </button>
          <button className="icon-btn" onClick={logout} aria-label="Sign out" title="Sign out"><Icon name="logout" /></button>
        </div>
      </div>
    </header>
  )
}
