import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'
import type {
  Answer, AttemptStart, CheckResult, FinalAvailability, FinishResult, HintResult, LeaderRow, Me, ModuleDetail, ModuleSummary, SubmitResult,
} from './types'
import type { TraceAction } from '../engine/tracer'

export const useMe = (enabled = true) => useQuery({ queryKey: ['me'], queryFn: () => api<Me>('/me'), enabled })

export const useModules = () => useQuery({ queryKey: ['modules'], queryFn: () => api<ModuleSummary[]>('/modules') })

export const useModule = (slug: string) =>
  useQuery({ queryKey: ['module', slug], queryFn: () => api<ModuleDetail>(`/modules/${slug}`), retry: false })

export const useLeaderboard = () =>
  useQuery({ queryKey: ['leaderboard'], queryFn: () => api<{ top: LeaderRow[]; me: LeaderRow; badge_total: number }>('/leaderboard') })

/** Anything that changes progress invalidates the learner-facing caches. */
export function useProgressInvalidation() {
  const qc = useQueryClient()
  return () => {
    qc.invalidateQueries({ queryKey: ['me'] })
    qc.invalidateQueries({ queryKey: ['modules'] })
    qc.invalidateQueries({ queryKey: ['module'] })
    qc.invalidateQueries({ queryKey: ['leaderboard'] })
  }
}

export function useSubmitActivity(activityId: string) {
  const invalidate = useProgressInvalidation()
  return useMutation({
    mutationFn: (body: { actions?: TraceAction[]; data?: Record<string, unknown> }) =>
      api<SubmitResult>(`/activities/${activityId}/submit`, { body }),
    onSuccess: invalidate,
  })
}

export function useStartAttempt(activityId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { new_attempt?: boolean; repeat_practice?: boolean; request_id?: string } = {}) =>
      api<AttemptStart>(`/activities/${activityId}/attempts`, { body }),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ['final-availability', activityId] }) },
  })
}

export const useFinalAvailability = (activityId: string, enabled: boolean) =>
  useQuery({ queryKey: ['final-availability', activityId],
    queryFn: () => api<FinalAvailability>(`/activities/${activityId}/final-availability`), enabled, retry: false })

export function useCheckItem(attemptId: number | undefined) {
  return useMutation({
    mutationFn: (body: { item_id: string; answer?: Answer; reveal?: boolean }) =>
      api<CheckResult>(`/attempts/${attemptId}/check`, { body }),
  })
}

export function useHint(attemptId: number | undefined) {
  return useMutation({
    mutationFn: (body: { item_id: string }) => api<HintResult>(`/attempts/${attemptId}/hint`, { body }),
  })
}

export function useFinishAttempt(attemptId: number | undefined) {
  const invalidate = useProgressInvalidation()
  return useMutation({
    mutationFn: (answers?: Record<string, Answer>) => api<FinishResult>(`/attempts/${attemptId}/finish`, { body: { answers } }),
    onSuccess: invalidate,
  })
}
