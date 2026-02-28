// Backend response shapes -- must match the format_data() output of each model.

export interface Word {
  id: number
  word: string
  pinyin: string
  meaning: string
  confidence_score: number
  status: string
  source_name: string | null
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

// Settings types
export interface UserSettings {
  preferred_name: string | null
  words_per_session: number | null
  deepseek_api_key: string | null
  gemini_api_key: string | null
}
