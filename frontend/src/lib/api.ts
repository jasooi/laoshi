import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'
import type {
  PracticeSessionResponse,
  PracticeMessageResponse,
  PracticeSummaryResponse,
  PracticeSession,
  PracticeResponse,
  ProgressStats,
  ReportCardData,
  UserSettings,
  DeckWithStats,
  Word,
  PaginatedResponse,
  StreakData,
} from '../types/api'

const api = axios.create({
  headers: {
    'Content-Type': 'application/json',
  },
})

// --- Access token management (in-memory) ---

let accessToken: string | null = null

export function setAccessToken(token: string | null) {
  accessToken = token
}

export function getAccessToken(): string | null {
  return accessToken
}

// Request interceptor: attach in-memory access token
api.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }
  return config
})

// --- 401 Response interceptor: automatic token refresh ---

let isRefreshing = false
let failedQueue: Array<{
  resolve: (value: unknown) => void
  reject: (reason?: unknown) => void
  config: InternalAxiosRequestConfig
}> = []

const processQueue = (error: AxiosError | null, token: string | null) => {
  failedQueue.forEach(({ resolve, reject, config }) => {
    if (error) {
      reject(error)
    } else {
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
      resolve(api(config))
    }
  })
  failedQueue = []
}

// Callback for when refresh fails (set by AuthContext)
let onRefreshFailure: (() => void) | null = null

export function setOnRefreshFailure(callback: () => void) {
  onRefreshFailure = callback
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

    // Only attempt refresh on 401, and not on token endpoints themselves
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url?.includes('/api/token')
    ) {
      if (isRefreshing) {
        // Queue this request until the refresh completes
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject, config: originalRequest })
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        const refreshResponse = await axios.post(
          '/api/token/refresh',
          {},
          { withCredentials: true }
        )
        const newToken = refreshResponse.data.access_token
        setAccessToken(newToken)
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        processQueue(null, newToken)
        return api(originalRequest)
      } catch (refreshError) {
        processQueue(refreshError as AxiosError, null)
        setAccessToken(null)
        if (onRefreshFailure) {
          onRefreshFailure()
        }
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  }
)

// Practice session API helpers
export const practiceApi = {
  startSession: (deckId: number, wordsCount?: number) =>
    api.post<PracticeSessionResponse>(
      '/api/practice/sessions',
      { deck_id: deckId, ...(wordsCount ? { words_count: wordsCount } : {}) }
    ),

  getSession: (sessionId: number) =>
    api.get<{ session: PracticeSession }>(`/api/practice/sessions/${sessionId}`),

  sendMessage: (sessionId: number, message: string) =>
    api.post<PracticeMessageResponse>(
      `/api/practice/sessions/${sessionId}/messages`,
      { message }
    ),

  submitSentence: (sessionId: number, sentence: string) =>
    api.post<PracticeResponse>(
      `/api/practice/sessions/${sessionId}/messages`,
      { message: sentence }
    ),

  nextWord: (sessionId: number, quality?: number) =>
    api.post<PracticeResponse>(
      `/api/practice/sessions/${sessionId}/next-word`,
      quality !== undefined ? { quality } : {}
    ),

  endSession: (sessionId: number) =>
    api.post<PracticeMessageResponse>(
      `/api/practice/sessions/${sessionId}/end`
    ),

  getSummary: (sessionId: number) =>
    api.get<PracticeSummaryResponse>(
      `/api/practice/sessions/${sessionId}/summary`
    ),
}

// Progress stats API helpers
export const progressApi = {
  getStats: () => api.get<ProgressStats>('/api/progress/stats'),
  getReportCard: () => api.get<ReportCardData>('/api/progress/report-card'),
  generateFeedback: () => api.post('/api/progress/generate-feedback'),
  getStreak: () => api.get<StreakData>('/api/progress/streak'),
}

// Deck API helpers
export const deckApi = {
  getDecks: () => api.get<{ decks: DeckWithStats[] }>('/api/decks'),
  createDeck: (data: { name: string; description?: string }) =>
    api.post<DeckWithStats>('/api/decks', data),
  getDeck: (id: number) => api.get<DeckWithStats>(`/api/decks/${id}`),
  updateDeck: (id: number, data: { name?: string; description?: string }) =>
    api.put<DeckWithStats>(`/api/decks/${id}`, data),
  deleteDeck: (id: number) => api.delete(`/api/decks/${id}`),
  getDeckWords: (id: number, params?: { page?: number; per_page?: number; search?: string; sort_by?: string; sort_order?: string }) =>
    api.get<PaginatedResponse<Word>>(`/api/decks/${id}/words`, { params }),
  addWordsToDeck: (id: number, words: { word: string; pinyin: string; meaning: string; source_name?: string }[]) =>
    api.post<{ created: Word[] }>(`/api/decks/${id}/words`, { words }),
  combineDecks: (data: { name: string; description?: string; source_deck_ids: number[] }) =>
    api.post<DeckWithStats & { words_copied: number }>('/api/decks/combine', data),
}

// Word API helpers
export const wordsApi = {
  getWords: (deckId: number, page?: number, perPage?: number) =>
    api.get<PaginatedResponse<Word>>(`/api/decks/${deckId}/words`, {
      params: { page, per_page: perPage },
    }),
  uploadWords: (deckId: number, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post<{ created: Word[] }>(`/api/decks/${deckId}/words/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  },
  markAsMastered: (wordId: number, marked?: boolean) =>
    api.post<Word & { message: string }>(`/api/words/${wordId}/mark-as-mastered`, { marked }),
}

// Settings API helpers
export const settingsApi = {
  getSettings: () => api.get<UserSettings>('/api/settings'),
  updateSettings: (settings: Partial<UserSettings>) =>
    api.put<UserSettings>('/api/settings', settings),
  validateKey: (provider: 'deepseek' | 'gemini', apiKey: string) =>
    api.post<{ valid: boolean; error?: string }>(
      `/api/settings/keys/${provider}/validate`,
      { api_key: apiKey }
    ),
}

export default api
