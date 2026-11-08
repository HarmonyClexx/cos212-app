import type { GraphSpec } from '../engine/graph'

export interface LevelInfo {
  level: number
  title: string
  xp: number
  floor: number
  next: number | null
  progress: number
}

export interface Badge {
  id: string
  name: string
  description: string
  icon: string
  earned_at?: string | null
}

export interface MasteryRow {
  objective: number
  title: string
  bloom: string
  verb: string
  statement: string
  module: string
  value: number
  evidence: number
}

export interface Recommendation {
  type: 'continue' | 'revise'
  module: string
  activity_id: string
  title: string
  reason: string
  objective?: number
}

export interface Me {
  id: number
  username: string
  display_name: string
  level: LevelInfo
  streak_days: number
  badges: Badge[]
  mastery: MasteryRow[]
  recommendations: Recommendation[]
  stats: { completed: number; total: number; stars: number; max_stars: number; attempts: number }
}

export type ActivityKind = 'maze' | 'inspect' | 'represent' | 'demo' | 'trace' | 'compare' | 'quiz'

export interface ActivityState {
  id: string
  kind: ActivityKind
  title: string
  summary: string
  xp: number
  objective: number | null
  completed: boolean
  best_stars: number
  xp_earned: number
  attempts: number
  unlocked: boolean
}

export interface ModuleSummary {
  slug: string
  order: number
  title: string
  tagline: string
  icon: string
  objective: number | null
  unlocked: boolean
  completed: boolean
  stars: number
  max_stars: number
  activities: ActivityState[]
}

export interface ActivityConfig {
  graph?: GraphSpec
  directed_graph?: GraphSpec
  start?: string
  goal?: string
  auto_backtrack?: boolean
  difficulty?: number
  focus?: 'traversal' | 'backtracking'
  assessment?: string
  mode?: 'formative' | 'summative'
  item_count?: number
  pass_mark?: number
}

export interface Activity {
  id: string
  kind: ActivityKind
  title: string
  summary: string
  objective: number | null
  xp: number
  config: ActivityConfig
  state: ActivityState
}

export interface ModuleDetail {
  slug: string
  order: number
  title: string
  tagline: string
  story: string
  objective: number | null
  outcome: string
  icon: string
  activities: Activity[]
}

export interface Objective {
  id: number
  title: string
  bloom: string
  verb: string
  statement: string
  module: string
}

export interface Reward {
  completed: boolean
  first_completion: boolean
  stars: number
  best_stars: number
  improved: boolean
  score: number
  xp_gained: number
  xp_possible: number
  level: LevelInfo
  level_up: boolean
  streak_days: number
  new_badges: Badge[]
  next_activity: string | null
}

export type ItemType = 'mcq' | 'graph_select' | 'adjacency' | 'order' | 'short_answer'

export interface QuizItem {
  id: string
  type: ItemType
  objective: number
  prompt: string
  graph: GraphSpec | null
  options: string[] | null
  multi: boolean
  select: 'nodes' | 'edges' | null
  algorithm: 'dfs' | 'bfs' | null
  start: string | null
  pass_criteria: number
  criteria?: string[]
}

export type Answer = number[] | string[] | Record<string, string[]> | string

export interface AttemptStart {
  attempt_id: number
  mode: 'formative' | 'summative'
  pass_mark: number
  items: QuizItem[]
}

export interface GradeDetail {
  extra?: string[]
  missing_count?: number
  wrong_rows?: string[]
  correct_prefix?: number
  looks_like?: string
  criteria?: { id: string; descriptor: string; met: boolean; nudge?: string }[]
}

export interface CheckResult {
  item_id: string
  tries: number
  hints: number
  correct: boolean
  score: number
  feedback: string
  detail: GradeDetail
  tier: number
  can_reveal: boolean
  /** Credit this question earns (if correct) or would earn on the next correct try. */
  worth: number
  hint?: string
  /** Level-2 visual cue: vertices to ring on the graph. */
  focus?: string[]
  explanation?: string
  answer?: unknown
}

export interface HintResult {
  item_id: string
  level: number
  max_level: number
  /** False when this level was already shown (asking again is free). */
  charged: boolean
  hints: number
  worth: number
  hint: string
  focus: string[]
}

export interface ReviewRow {
  item_id: string
  objective: number
  score: number
  correct: boolean
  feedback?: string
  detail?: GradeDetail
  explanation?: string
  answer?: unknown
  your_answer?: unknown
  tries?: number
  revealed?: boolean
}

export interface FinishResult {
  result: { score: number; passed?: boolean; review: ReviewRow[]; objectives: Record<string, number> }
  reward: Reward
  mastery: MasteryRow[]
  recommendations: Recommendation[]
}

export interface SubmitResult {
  result: Record<string, unknown>
  reward: Reward
}

export interface LeaderRow {
  rank: number
  display_name: string
  username: string
  xp: number
  level: number
  title: string
  badges: number
  streak_days: number
  is_me: boolean
}
