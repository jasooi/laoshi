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
