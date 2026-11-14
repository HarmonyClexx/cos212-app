import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { confetti, stopConfetti } from './confetti'

const SOUND_KEY = 'ariadne.feedback-muted'
const CELEBRATION_KEY = 'ariadne.celebrations-disabled'
let muted: boolean | undefined
let celebrationsDisabled: boolean | undefined
const listeners = new Set<() => void>()
let speaking: SpeechSynthesisUtterance | null = null
let speaker: symbol | null = null

function storedMute(): boolean {
  try { return localStorage.getItem(SOUND_KEY) === 'true' } catch { return muted ?? false }
}

function getMuted() {
  return muted ??= storedMute()
}

function storedCelebrations(): boolean {
  try { return localStorage.getItem(CELEBRATION_KEY) === 'true' } catch { return celebrationsDisabled ?? false }
}

function getCelebrationsDisabled() {
  return celebrationsDisabled ??= storedCelebrations()
}

export function speechAvailable() {
  try {
    return typeof window !== 'undefined' && typeof window.SpeechSynthesisUtterance === 'function' &&
      typeof window.speechSynthesis?.speak === 'function' && typeof window.speechSynthesis?.cancel === 'function'
  } catch { return false }
}

function cancelSpeech(owner?: symbol) {
  if (!speaking || (owner !== undefined && speaker !== owner)) return true
  speaking = null
  speaker = null
  try { window.speechSynthesis.cancel(); return true } catch { return false }
}

function storageChanged(e: StorageEvent) {
  if (e.key !== SOUND_KEY && e.key !== CELEBRATION_KEY && e.key !== null) return
  if (e.key === SOUND_KEY || e.key === null) {
    muted = storedMute()
    if (muted) cancelSpeech()
  }
  if (e.key === CELEBRATION_KEY || e.key === null) {
    celebrationsDisabled = storedCelebrations()
    if (celebrationsDisabled) stopConfetti()
  }
  listeners.forEach((listener) => listener())
}

function subscribe(listener: () => void) {
  if (!listeners.size) window.addEventListener('storage', storageChanged)
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
    if (!listeners.size) window.removeEventListener('storage', storageChanged)
  }
}

export function useFeedbackMuted(): [boolean, () => void] {
  const value = useSyncExternalStore(subscribe, getMuted, () => false)
  const toggle = () => {
    muted = !getMuted()
    try { localStorage.setItem(SOUND_KEY, String(muted)) } catch { /* Keep the preference in memory. */ }
    if (muted) cancelSpeech()
    listeners.forEach((listener) => listener())
  }
  return [value, toggle]
}

export function useCelebrationsDisabled(): [boolean, () => void] {
  const value = useSyncExternalStore(subscribe, getCelebrationsDisabled, () => false)
  const toggle = () => {
    celebrationsDisabled = !getCelebrationsDisabled()
    try { localStorage.setItem(CELEBRATION_KEY, String(celebrationsDisabled)) } catch { /* Keep the preference in memory. */ }
    if (celebrationsDisabled) stopConfetti()
    listeners.forEach((listener) => listener())
  }
  return [value, toggle]
}

export function useAnswerFeedback(scope: string) {
  const owner = useRef(Symbol('answer-feedback'))
  const active = useRef(false)
  const currentScope = useRef(scope)
  currentScope.current = scope
  const seen = useRef(new Set<string>())
  const burst = useRef<(() => void) | undefined>()
  const [praisedScope, setPraisedScope] = useState<string | null>(null)

  useEffect(() => {
    active.current = true
    setPraisedScope(null)
    const onHidden = () => {
      if (document.hidden) { cancelSpeech(owner.current); burst.current?.() }
    }
    document.addEventListener('visibilitychange', onHidden)
    return () => {
      active.current = false
      cancelSpeech(owner.current)
      burst.current?.()
      document.removeEventListener('visibilitychange', onHidden)
    }
  }, [scope])

  const announce = useCallback((id: string, correct: boolean) => {
    if (!active.current || currentScope.current !== scope || seen.current.has(id)) return
    seen.current.add(id)
    if (document.hidden ||
      (navigator.userActivation && !navigator.userActivation.hasBeenActive)) return
    setPraisedScope(correct ? scope : null)
    burst.current?.()
    if (correct && !getCelebrationsDisabled()) {
      try { burst.current = confetti(0.35, document.body, 1000) } catch { /* Keep the visible praise without animation. */ }
    }
    if (getMuted() || !speechAvailable()) return
    try {
      if (!cancelSpeech()) return
      const utterance = new SpeechSynthesisUtterance(correct ? 'Well done!' : "Oops, let's try again!")
      utterance.lang = 'en'
      utterance.onend = utterance.onerror = () => {
        if (speaking === utterance) { speaking = null; speaker = null }
      }
      speaking = utterance
      speaker = owner.current
      window.speechSynthesis.speak(utterance)
    } catch { cancelSpeech(owner.current) }
  }, [scope])
  return { announce, praised: praisedScope === scope }
}
