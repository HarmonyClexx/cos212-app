import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { GraphCanvas } from '../components/GraphCanvas'
import { Icon, Logo } from '../components/Icon'
import { dfsTrace, type GraphSpec } from '../engine/graph'
import { traceVisuals } from '../activities/shared'
import { useAuth } from '../lib/auth'
import { useTheme } from '../lib/theme'

const HERO: GraphSpec = {
  id: 'hero', directed: false,
  nodes: [
    { id: 'A', x: 6, y: 36 }, { id: 'B', x: 26, y: 12 }, { id: 'C', x: 26, y: 60 }, { id: 'D', x: 50, y: 6 },
    { id: 'E', x: 50, y: 36 }, { id: 'F', x: 50, y: 66 }, { id: 'G', x: 74, y: 20 }, { id: 'H', x: 96, y: 44 },
  ],
  edges: [['A', 'B'], ['A', 'C'], ['B', 'D'], ['B', 'E'], ['C', 'F'], ['D', 'G'], ['E', 'F'], ['E', 'G'], ['G', 'H'], ['F', 'H']],
}

function HeroGraph() {
  const events = useMemo(() => dfsTrace(HERO, 'A'), [])
  const [i, setI] = useState(0)
  useEffect(() => {
    const t = setTimeout(() => setI((x) => (x + 1) % (events.length + 3)), i >= events.length - 1 ? 1600 : 750)
    return () => clearTimeout(t)
  }, [i, events.length])
  const shown = Math.min(i, events.length - 1)
  const v = traceVisuals(HERO, events, shown, 'A')
  const marks = { ...v.nodeMarks }
  if (events[shown].kind === 'backtrack') marks[events[shown].node] = [...(marks[events[shown].node] ?? []), 'deadend']
  return (
    <div className="hero-graph" aria-hidden="true">
      <GraphCanvas graph={HERO} nodeMarks={marks} edgeMarks={v.edgeMarks} thread={v.thread} badges={v.badges} maxHeight={320} />
      <div className="row" style={{ gap: 8, marginTop: 8, flexWrap: 'wrap' }}>
        <span className="faint small">stack</span>
        {v.ev.stack.map((n, k) => <span key={`${k}${n}`} className={`frame ${k === v.ev.stack.length - 1 ? 'top' : ''}`} style={{ padding: '3px 9px' }}>{n}</span>)}
        {v.ev.stack.length === 0 && <span className="faint small">empty — done!</span>}
      </div>
    </div>
  )
}

export function Landing() {
  useTheme()
  const { login, register } = useAuth()
  const [mode, setMode] = useState<'register' | 'login'>('register')
  const [username, setUsername] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      if (mode === 'login') await login(username, password)
      else await register(username, displayName || username, password)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="container">
      <div className="row" style={{ height: 70 }}>
        <div className="logo"><Logo /><span>Ariadne</span></div>
        <span className="spacer" />
        <span className="chip">COS750 · Graphs &amp; DFS</span>
      </div>
      <div className="landing">
        <div>
          <div className="eyebrow" style={{ color: 'var(--thread)' }}>Learn depth-first search by playing it</div>
          <h1 style={{ marginTop: 12 }}>Follow the <span className="gold">thread</span>.<br />Escape the labyrinth.</h1>
          <p className="lede">
            Theseus survived the Labyrinth with a ball of thread and a stick of chalk. That's depth-first search.
            Explore, trace, backtrack and level up — no prior data-structures knowledge needed.
          </p>
          <HeroGraph />
          <div className="feature-row">
            <span className="chip gold"><Icon name="spool" size={14} /> Thread = stack</span>
            <span className="chip chalk"><Icon name="check" size={14} /> Chalk = visited</span>
            <span className="chip brand"><Icon name="bulb" size={14} /> Hints that adapt</span>
            <span className="chip"><Icon name="trophy" size={14} /> XP, badges &amp; leaderboard</span>
          </div>
        </div>

        <div className="card auth-card">
          <h2>{mode === 'register' ? 'Begin the descent' : 'Welcome back'}</h2>
          <p className="muted small" style={{ marginBottom: 18 }}>
            {mode === 'register' ? 'Create an explorer profile to save your progress.' : 'Sign in to pick up your thread.'}
          </p>
          <div className="tabs" style={{ marginBottom: 18 }}>
            <button className={mode === 'register' ? 'active' : ''} onClick={() => setMode('register')} type="button">Sign up</button>
            <button className={mode === 'login' ? 'active' : ''} onClick={() => setMode('login')} type="button">Sign in</button>
          </div>
          <form className="stack-v" onSubmit={submit}>
            <div className="field">
              <label htmlFor="u">Username</label>
              <input id="u" className="input" autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)}
                required minLength={3} maxLength={32} pattern="[A-Za-z0-9_.\-]+" placeholder="e.g. theseus" />
            </div>
            {mode === 'register' && (
              <div className="field">
                <label htmlFor="d">Display name <span className="faint">(shown on the leaderboard)</span></label>
                <input id="d" className="input" value={displayName} onChange={(e) => setDisplayName(e.target.value)} maxLength={48} placeholder="Theseus of Athens" />
              </div>
            )}
            <div className="field">
              <label htmlFor="p">Password</label>
              <input id="p" className="input" type="password" autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                value={password} onChange={(e) => setPassword(e.target.value)} required minLength={6} />
            </div>
            {error && <div className="error-text" role="alert">{error}</div>}
            <button className="btn primary lg block" disabled={busy} type="submit">
              {busy ? 'One moment…' : mode === 'register' ? 'Enter the Labyrinth' : 'Sign in'} <Icon name="arrowRight" />
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
