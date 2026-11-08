import { useEffect, useRef, useState } from 'react'
import type { Reward } from '../api/types'
import { confetti } from '../lib/confetti'
import { Icon } from './Icon'
import { Meter, Stars } from './bits'

function useCountUp(target: number, ms = 900) {
  const [v, setV] = useState(0)
  useEffect(() => {
    let raf = 0
    const t0 = performance.now()
    const tick = (t: number) => {
      const p = Math.min(1, (t - t0) / ms)
      setV(Math.round(target * (1 - Math.pow(1 - p, 3))))
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [target, ms])
  return v
}

export function RewardModal({ reward, title, subtitle, graded, onContinue, onRetry, continueLabel = 'Continue' }: {
  reward: Reward
  title?: string
  subtitle?: string
  graded: boolean
  onContinue: () => void
  onRetry?: () => void
  continueLabel?: string
}) {
  const xp = useCountUp(reward.xp_gained)
  const btn = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    btn.current?.focus()
    if (reward.completed) confetti(reward.level_up || reward.new_badges.length ? 1.4 : reward.stars === 3 ? 1 : 0.6)
  }, [reward])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onContinue()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onContinue])

  const heading = title ?? (!reward.completed ? 'Not quite yet' : reward.stars === 3 ? 'Flawless!' : reward.stars === 2 ? 'Great work!' : 'Completed!')
  const lv = reward.level

  return (
    <div className="overlay" role="dialog" aria-modal="true" aria-labelledby="reward-title">
      <div className="modal">
        {graded && (
          <div className="big-stars"><Stars count={reward.stars} size={44} pop /></div>
        )}
        {!graded && reward.completed && <div style={{ color: 'var(--chalk)', marginBottom: 6 }}><Icon name="check" size={44} /></div>}
        <h2 id="reward-title" style={{ marginTop: 6 }}>{heading}</h2>
        {subtitle && <p className="muted" style={{ marginTop: 6 }}>{subtitle}</p>}

        <div style={{ margin: '18px 0 6px' }}>
          <div className="xp-burst">+{xp} XP</div>
          <div className="small muted">
            {reward.xp_gained > 0
              ? reward.improved && !reward.first_completion ? 'Improvement bonus — you beat your best!' : `Earned ${reward.xp_gained} of ${reward.xp_possible} XP for this activity`
              : reward.completed ? 'You already banked this XP. Beat your best stars to earn more.' : 'Pass to earn XP.'}
          </div>
        </div>

        <div className="panel" style={{ textAlign: 'left', marginTop: 14 }}>
          <div className="row small" style={{ justifyContent: 'space-between', marginBottom: 8 }}>
            <strong>Level {lv.level} · {lv.title}</strong>
            <span className="faint">{lv.next ? `${lv.xp} / ${lv.next} XP` : `${lv.xp} XP · max level`}</span>
          </div>
          <Meter value={lv.progress} color="var(--thread)" label={`Level progress ${Math.round(lv.progress * 100)}%`} />
          <div className="row small" style={{ marginTop: 10, color: 'var(--ink-2)' }}>
            <Icon name="flame" size={16} style={{ color: 'var(--danger)' }} /> {reward.streak_days}-day streak
          </div>
        </div>

        {reward.level_up && (
          <div className="levelup"><Icon name="sparkles" /> Level up! You are now a <span style={{ color: 'var(--thread)' }}>{lv.title}</span>.</div>
        )}

        {reward.new_badges.length > 0 && (
          <div className="stack-v" style={{ marginTop: 14 }}>
            {reward.new_badges.map((b, i) => (
              <div key={b.id} className="new-badge" style={{ animationDelay: `${0.3 + i * 0.15}s` }}>
                <div className="medal"><Icon name={b.icon} size={24} /></div>
                <div>
                  <div className="eyebrow" style={{ color: 'var(--thread)' }}>New badge</div>
                  <div style={{ fontWeight: 700 }}>{b.name}</div>
                  <div className="small muted">{b.description}</div>
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="row" style={{ marginTop: 22, justifyContent: 'center' }}>
          {onRetry && graded && reward.stars < 3 && (
            <button className="btn" onClick={onRetry}><Icon name="restart" /> Try for {reward.stars < 2 ? 'more stars' : '3 stars'}</button>
          )}
          <button ref={btn} className="btn primary" onClick={onContinue}>{continueLabel} <Icon name="arrowRight" /></button>
        </div>
      </div>
    </div>
  )
}
