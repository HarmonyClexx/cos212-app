import { useEffect, useState } from 'react'

/**
 * True once `ms` pass without `key` changing, while `active`.
 *
 * Learners who are stuck often don't ask for help (help avoidance), so activities use this to
 * *offer* a hint after a quiet spell instead of waiting to be asked.
 */
export function useIdle(ms: number, key: unknown, active = true): boolean {
  const [idle, setIdle] = useState(false)
  useEffect(() => {
    setIdle(false)
    if (!active) return
    const t = setTimeout(() => setIdle(true), ms)
    return () => clearTimeout(t)
  }, [ms, key, active])
  return idle && active
}
