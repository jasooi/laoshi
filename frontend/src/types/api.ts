// Backend response shapes -- must match the format_data() output of each model.

export interface Word {
  id: number
  word: string
  pinyin: string
  meaning: string
  notes: string | null
  deck_id: number | null
  // SRS fields
  repetitions: number
  interval_days: number
  ease_factor: number
  next_review_date: string | null
  // Mastery fields
  last_quality: number | null
  marked_as_known: boolean
  is_mastered: boolean
  srs_status: string
}

export interface User {
  id: number
  username?: string
  preferred_name?: string | null
}

export interface UserSession {
  id: number
  session_start_ds: string
  session_end_ds: string | null
  user_id: number
  deck_id: number | null
}

export interface SessionWord {
  id: string
  is_skipped: boolean
  session_notes: string | null
}

export interface PaginationMeta {
  page: number
  per_page: number
  total: number
  total_pages: number
  has_next: boolean
  has_prev: boolean
  next_page: number | null
  prev_page: number | null
}

export interface PaginatedResponse<T> {
  data: T[]
  pagination: PaginationMeta
}

// Practice session types
export interface WordContext {
  word_id: number
  word: string
  pinyin: string
  meaning: string
}

export interface FeedbackData {
  grammarScore: number
  usageScore: number
  naturalnessScore: number
  isCorrect: boolean
  feedback: string
  corrections: string[]
  explanations: string[]
  exampleSentences: string[]
}

export interface PracticeSessionResponse {
  session: { id: number; session_start_ds: string; words_per_session: number }
  current_word: WordContext
  greeting_message: string
  words_practiced: number
  words_skipped: number
  words_total: number
  session_complete: boolean
}

export interface PracticeSession {
  id: number
  session_start_ds: string
  deck_id: number | null
  words_per_session: number
  words_practiced: number
  words_total: number
}

export interface PracticeResponse {
  word_id: number
  target_word: string
  target_pinyin: string
  target_english: string
  user_sentence: string
  is_correct: boolean
  corrected_sentence: string | null
  explanation: string
  words_practiced: number
  words_total: number
  is_session_complete: boolean
  is_mastered: boolean
  marked_as_known: boolean
}

export interface PracticeMessageResponse {
  laoshi_response: string
  feedback: FeedbackData | null
  current_word: WordContext | null
  words_practiced: number
  words_skipped: number
  words_total: number
  session_complete: boolean
  summary?: PracticeSummaryResponse
}

export interface WordResult {
  word: string
  grammar_score: number | null
  usage_score: number | null
  naturalness_score: number | null
  is_correct: boolean | null
  is_skipped: boolean
}

export interface PracticeSummaryResponse {
  session_id: number
  summary_text: string
  words_practiced: number
  words_skipped: number
  word_results: WordResult[]
}

// Progress stats types
export interface ProgressStats {
  total_words: number
  words_practiced_today: number
  mastery_percentage: number
  words_ready_for_review: number
}

// Report Card types
export interface ReportCardTopline {
  time_practiced_hours: number
  sessions_completed: number
  words_practiced: number
}

export interface DailyChartData {
  date: string
  correct: number
  incorrect: number
}

export interface ScoreDetail {
  score: number | null
  description: string | null
}

export interface ScoreBreakdown {
  grammar: ScoreDetail
  usage: ScoreDetail
  naturalness: ScoreDetail
}

export interface ReportCardData {
  topline: ReportCardTopline
  chart_data: DailyChartData[]
  score_breakdown: ScoreBreakdown
  teacher_feedback: string | null
}

// Settings types
export interface UserSettings {
  preferred_name: string | null
  words_per_session: number | null
  deepseek_api_key: string | null
  gemini_api_key: string | null
}

// Deck types
export interface Deck {
  id: number
  name: string
  description: string | null
  user_id: number
  laoshi_message: string | null
  created_ds: string
  updated_ds: string
}

export interface DeckWithStats extends Deck {
  word_count: number
  mastered_count: number
  mastery_percentage: number
  last_practiced_at: string | null
}

export interface StreakData {
  current_streak: number
  last_practice_date: string | null
}
