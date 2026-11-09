import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, ApiError, tokenStore } from '../api/client'
import type { Answer, AttemptStart } from '../api/types'
import { emptyAnswer } from './items/QuizItems'

interface Draft {
  answers: Record<string, Answer>
  reflections: Record<string, string>
  current_item: string
}
interface SaveRequest extends Draft {
  revision: number
  request_id: string
}
interface Backup extends Draft {
  revision: number
  pending: SaveRequest | null
}

let activeSave: (() => Promise<void>) | null = null
export async function flushQuizDraft() {
  await activeSave?.()
}

export function useQuizDraft(attempt: AttemptStart) {
  const navigate = useNavigate()
  const key = `ariadne.quiz-draft:${attempt.user_id}:${attempt.attempt_id}`
  const [initial] = useState(() => {
    const saved: Draft = {
      answers: { ...Object.fromEntries(attempt.items.map((i) => [i.id, emptyAnswer(i)])), ...attempt.answers },
      reflections: attempt.reflections,
      current_item: attempt.current_item,
    }
    try {
      const backup: Backup | null = JSON.parse(localStorage.getItem(key) ?? 'null')
      if (backup && (backup.revision === attempt.revision ||
        (backup.pending?.request_id === attempt.last_draft_request && backup.revision + 1 === attempt.revision))) {
        return {
          draft: { answers: backup.answers, reflections: backup.reflections, current_item: backup.current_item },
          pending: backup.revision === attempt.revision ? backup.pending : null,
          dirty: true,
        }
      }
    } catch { /* The server copy remains usable if local storage is unavailable. */ }
    return { draft: saved, pending: null, dirty: false }
  })
  const [draft, setDraft] = useState<Draft>(initial.draft)
  const current = useRef(draft)
  const revision = useRef(attempt.revision)
  const pending = useRef<SaveRequest | null>(initial.pending)
  const dirty = useRef(initial.dirty)
  const generation = useRef(0)
  const saving = useRef<Promise<void> | null>(null)
  const failedAction = useRef<{ path: string; body: Record<string, unknown> } | null>(null)
  const blocked = useRef(false)
  const [status, setStatus] = useState<'saved' | 'saving' | 'error'>(initial.dirty ? 'saving' : 'saved')
  const [error, setError] = useState('')
  const [conflict, setConflict] = useState(false)
  const [busy, setBusy] = useState(false)
  const [uncertain, setUncertain] = useState(false)

  const backup = useCallback(() => {
    try {
      if (!dirty.current && !pending.current) localStorage.removeItem(key)
      else localStorage.setItem(key, JSON.stringify({
        ...current.current, revision: revision.current, pending: pending.current,
      }))
    } catch { /* Saving to the account still works without a local fallback. */ }
  }, [key])

  const fail = useCallback((e: unknown) => {
    setError(e instanceof Error ? e.message : 'Could not save your quiz.')
    setStatus('error')
    if (e instanceof ApiError && e.status === 409) {
      blocked.current = true
      setConflict(true)
    }
  }, [])

  const flush = useCallback((): Promise<void> => {
    if (blocked.current || failedAction.current) return Promise.reject(new Error('Resolve the pending quiz action first.'))
    if (saving.current) return saving.current
    const work = async () => {
      while (dirty.current || pending.current) {
        setStatus('saving')
        const sentGeneration = generation.current
        pending.current ??= { ...current.current, revision: revision.current, request_id: crypto.randomUUID() }
        backup()
        const sent = pending.current
        const response = await api<{ revision: number }>(`/attempts/${attempt.attempt_id}/draft`, {
          method: 'PUT', body: sent,
        })
        revision.current = response.revision
        pending.current = null
        dirty.current = sentGeneration !== generation.current ||
          JSON.stringify(current.current) !== JSON.stringify({
            answers: sent.answers, reflections: sent.reflections, current_item: sent.current_item,
          })
        backup()
      }
      setStatus('saved')
      setError('')
    }
    saving.current = work().catch((e) => { fail(e); throw e }).finally(() => { saving.current = null })
    return saving.current
  }, [attempt.attempt_id, backup, fail])

  const update = (patch: Partial<Draft>) => {
    current.current = { ...current.current, ...patch }
    generation.current += 1
    dirty.current = true
    setDraft(current.current)
    setStatus('saving')
    backup()
  }

  useEffect(() => {
    const timer = window.setTimeout(() => { if (!blocked.current) void flush().catch(() => {}) }, 300)
    return () => clearTimeout(timer)
  }, [draft, flush])

  useEffect(() => {
    activeSave = flush
    const beforeUnload = (e: BeforeUnloadEvent) => {
      if (dirty.current || pending.current || failedAction.current) e.preventDefault()
    }
    const followLink = (e: MouseEvent) => {
      const link = (e.target as Element).closest?.('a')
      if (!link || link.target || link.origin !== location.origin ||
        e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return
      if (!dirty.current && !pending.current && !failedAction.current && !blocked.current) return
      e.preventDefault()
      e.stopPropagation()
      void flush().then(() => navigate(link.pathname + link.search + link.hash)).catch(() => {})
    }
    window.addEventListener('beforeunload', beforeUnload)
    document.addEventListener('click', followLink, true)
    return () => {
      window.removeEventListener('beforeunload', beforeUnload)
      document.removeEventListener('click', followLink, true)
      if (activeSave === flush) activeSave = null
      if (tokenStore.get()) void flush().catch(() => {})
    }
  }, [flush, navigate])

  const perform = async <T extends { revision: number }>(path: string, body: Record<string, unknown>): Promise<T> => {
    setBusy(true)
    try {
      if (!failedAction.current) {
        await flush()
        failedAction.current = { path, body: { ...body, revision: revision.current, request_id: crypto.randomUUID() } }
      }
      if (failedAction.current.path !== path) throw new Error('Retry the pending action first.')
      const response = await api<T>(`/attempts/${attempt.attempt_id}/${path}`, { body: failedAction.current.body })
      revision.current = response.revision
      failedAction.current = null
      setUncertain(false)
      setError('')
      setStatus('saved')
      return response
    } catch (e) {
      if (e instanceof ApiError && e.status < 500) failedAction.current = null
      setUncertain(!!failedAction.current)
      fail(e)
      throw e
    } finally { setBusy(false) }
  }

  return {
    ...draft, idx: Math.max(0, attempt.items.findIndex((i) => i.id === draft.current_item)),
    setIdx: (i: number) => update({ current_item: attempt.items[i].id }),
    setAnswer: (id: string, value: Answer) => update({ answers: { ...current.current.answers, [id]: value } }),
    setReflection: (id: string, text: string) => update({ reflections: { ...current.current.reflections, [id]: text } }),
    status, error, conflict, busy, uncertain, flush, perform,
  }
}

export type QuizDraft = ReturnType<typeof useQuizDraft>
