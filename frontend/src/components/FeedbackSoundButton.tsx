import { speechAvailable, useCelebrationsDisabled, useFeedbackMuted } from '../lib/answerFeedback'
import { Icon } from './Icon'

export function FeedbackSoundButton() {
  const [muted, toggle] = useFeedbackMuted()
  const available = speechAvailable()
  const label = available ? muted ? 'Unmute spoken feedback' : 'Mute spoken feedback' : 'Spoken feedback unavailable'
  return (
    <button className="icon-btn" onClick={toggle} disabled={!available} aria-label={label}
      aria-pressed={muted} title={available
        ? `Spoken feedback ${muted ? 'muted' : 'on'}. Written feedback stays visible.`
        : 'Spoken feedback is unavailable in this browser. Written feedback stays visible.'}>
      <Icon name={muted || !available ? 'soundOff' : 'soundOn'} />
    </button>
  )
}

export function CelebrationButton() {
  const [disabled, toggle] = useCelebrationsDisabled()
  return (
    <button className="icon-btn" onClick={toggle} aria-pressed={disabled}
      aria-label={disabled ? 'Enable celebrations' : 'Disable celebrations'}
      title={`Confetti ${disabled ? 'off' : 'on'}. Written feedback stays visible; reduced motion is always respected.`}>
      <Icon name={disabled ? 'sparklesOff' : 'sparkles'} />
    </button>
  )
}
