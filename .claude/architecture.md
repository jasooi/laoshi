# architecture.md

## Frontend Stack
- React 18 + TypeScript + Vite
- Tailwind CSS (purple color scheme, primary: #9333EA)
- React Router DOM for navigation
- Axios for HTTP requests
- Recharts for data visualization (stacked bar charts for Report Card)

## Backend Stack
- Flask + Flask-RESTful
- SQLAlchemy ORM with PostgreSQL
- Flask-JWT-Extended for authentication
- Flask-Migrate (Alembic) for migrations

## AI Layer Stack
- OpenAI Agents SDK (`openai-agents`) - multi-agent orchestration
- DeepSeek API (via OpenAI-compatible client) - feedback agent (sentence evaluation)
- Gemini Flash API (via OpenAI-compatible client) - orchestrator + summary + report card agents
- mem0 (`mem0ai`) - cross-session persistent user memory
- Redis - session-scoped conversation history (via SDK's `RedisSession`)

## Networking

### Local Development
Vite dev server proxies `/api/*` requests to `http://localhost:5000` (configured in `vite.config.ts`).

### Production
Nginx reverse proxy (`laoshi-gateway`) acts as the single public entry point, routing `/api/*` to the backend service and `/*` to the frontend service.

```
gateway/
├── nginx.conf    # Routes /api/* → backend, /* → frontend
└── Dockerfile    # nginx:alpine with custom config
```

## Repository Structure
### Gateway
```
gateway/
├── nginx.conf      # Reverse proxy routing rules
└── Dockerfile      # nginx:alpine container
```

### Frontend
```
frontend/src/
├── App.tsx           # Router configuration
├── main.tsx          # Entry point
├── components/       # Reusable components (Layout, Sidebar, Header, FeedbackCard, SessionSummary)
├── lib/              # API client (api.ts with practiceApi helpers)
├── types/            # TypeScript interfaces (api.ts)
└── pages/            # Page components (Practice.tsx is full-screen, others use Layout)
```

### Backend
```
backend/
├── app.py              # Flask app factory, route registration
├── models.py           # SQLAlchemy models (Word, User, UserSession, SessionWord, SessionWordAttempt)
├── resources.py        # Flask-RESTful endpoints (words, users, sessions, auth)
├── practice_resources.py # Flask-RESTful endpoints for practice session flow
├── report_card_resources.py # Flask-RESTful endpoints for report card (GET report-card, POST generate-feedback)
├── report_card_service.py  # Business logic for report card metrics, chart data, scores, AI feedback
├── extensions.py       # Flask extensions (db, jwt)
├── config.py           # Configuration from .env
├── utils.py            # Helpers (password hashing, pagination, filters)
└── ai_layer/
    ├── context.py          # UserSessionContext, WordContext, and ReportCardContext dataclasses
    ├── chat_agents.py      # Agent definitions (orchestrator, feedback, summary, report card)
    ├── practice_runner.py  # Core app code: session init, per-turn handling, score computation
    ├── mem0_setup.py       # mem0 MemoryClient initialization and custom categories
    ├── chat_service.py     # Redis session setup
    ├── function_tools.py   # ARCHIVED - not in use
    └── learning_file.py    # ARCHIVED - not in use
```

## Environment Variables
Backend requires `.env` file with:
- `DATABASE_URI` - PostgreSQL connection string
- `JWT_SECRET_KEY` - Secret for JWT tokens
- `DEEPSEEK_API_KEY` - API key for DeepSeek model
- `DEEPSEEK_BASE_URL` - DeepSeek API base URL
- `DEEPSEEK_MODEL_NAME` - DeepSeek model identifier
- `GEMINI_API_KEY` - API key for Gemini Flash model
- `GEMINI_BASE_URL` - Gemini API base URL
- `GEMINI_MODEL_NAME` - Gemini model identifier
- `MEM0_API_KEY` - API key for mem0 persistent memory
- `REDIS_URI` - Redis connection string (includes credentials)

## Database Models
- **Deck**: Vocabulary collections. Stores `name`, `description`, `user_id` FK, `laoshi_message` (AI-generated one-liner), `created_ds`, `updated_ds`. **1:many relationship with Word** (each word belongs to exactly one deck).
- **Word**: Vocabulary items with **SRS (Spaced Repetition) fields**: `repetitions` (int), `interval_days` (int), `ease_factor` (float), `next_review_date` (Date, NULL=new word). **Mastery fields**: `last_quality` (0-5, user self-rating), `marked_as_known` (bool), `is_mastered` (bool, dynamic: quality 5 → true, quality ≤3 → false, quality 4 preserves). `deck_id` FK (nullable during migration). Each word belongs to exactly one deck. **Removed**: `confidence_score` (replaced by SRS).
- **User**: Accounts with username, email, password (hashed)
- **UserProfile**: 1:1 with User. Stores `preferred_name`, `words_per_session`, encrypted API keys (`encrypted_deepseek_api_key`, `encrypted_gemini_api_key`), key versions (`deepseek_key_version`, `gemini_key_version`) for session invalidation on key changes, `report_card_feedback` (Text) for the latest AI-generated report card feedback, `current_streak` (Integer, consecutive days with practice), and `last_practice_date` (Date, for streak tracking).
- **UserSession**: Practice sessions with start/end timestamps, `summary_text`, `words_per_session`, `deck_id` FK (nullable for legacy sessions). Linked to a specific deck.
- **SessionWord**: Links words to sessions with `word_order`, averaged scores (`grammar_score`, `usage_score`, `naturalness_score`), `is_correct`, `is_skipped`. Scores are computed as averages across all attempts when the user clicks "Next Word".
- **SessionWordAttempt**: Individual sentence attempts per word per session. Stores per-attempt scores from the feedback agent (grammar_score, usage_score, naturalness_score, is_correct, feedback text). Multiple rows per word per session.
- **TokenBlocklist**: Revoked JWT refresh tokens

## AI Agent Architecture
Four agents orchestrated via the OpenAI Agents SDK:

| Agent | Model | Role | Communication |
|---|---|---|---|
| Orchestrator | Gemini Flash | Primary agent. Sassy teacher persona. Intent classification (sentence vs chat). | Calls Feedback Agent as tool; hands off to Summary Agent at session end |
| Feedback Agent | DeepSeek | Evaluates sentences. Returns structured JSON scores. Stateless. | Agent-as-tool (called by Orchestrator) |
| Summary Agent | Gemini Flash | Produces end-of-session summary, mem0 update recommendations, and deck one-liner (80-char progress message). | Handoff from Orchestrator when session complete |
| Report Card Agent | Gemini Flash | Generates holistic teacher feedback for the Report Card page using mem0 + recent summaries + rolling scores. | Called independently by report_card_service.py (fire-and-forget from session exit) |

**Data flow:** App code hydrates read-only `UserSessionContext` before each `Runner.run()` call. Agents never access DB or mem0 directly. All writes happen in app code after agent output is returned.

**Conversation history:** Stored in Redis via the SDK's `RedisSession`, keyed by session ID. Cleared at session end.

**Persistent memory:** mem0 stores cross-session user preferences and learning patterns. Read at session start, written at session end based on Summary Agent recommendations.

## API Endpoints

### Decks
- `GET /api/decks` - List user's decks with computed stats (word_count, mastered_count where is_mastered=true, mastery_percentage, last_practiced_at), sorted by reverse recency (least recently practiced first)
- `POST /api/decks` - Create empty deck (body: `{name, description?}`)
- `GET /api/decks/<id>` - Get deck detail + stats
- `PUT /api/decks/<id>` - Update deck name/description
- `DELETE /api/decks/<id>` - Delete deck AND cascade delete its words
- `GET /api/decks/<id>/words` - Paginated word list for a deck
- `POST /api/decks/<id>/words` - Create words inside this deck (body: `{words: [{word, pinyin, meaning, source_name?}]}`) - used for CSV import and manual add
- `POST /api/decks/combine` - Create new deck + copy words from source decks (body: `{name, description?, source_deck_ids: [int]}`)

### Words (Individual Operations)
- `GET /api/words` - List user's words (paginated, searchable, sortable). Optional `deck_id` query param to filter by deck.
- `GET /api/words/<id>` - Get single word
- `PUT /api/words/<id>` - Update word fields
- `DELETE /api/words/<id>` - Delete single word
- `POST /api/words/<id>/mark-as-known` - Mark word as already known (fast-tracks to 90-day interval, sets is_mastered=true, last_quality=5, repetitions=5)
- **REMOVED**: `POST /api/words` (bulk create) - replaced by `POST /api/decks/<id>/words`
- **REMOVED**: `DELETE /api/words` (delete all) - use `DELETE /api/decks/<id>` instead

### Authentication
- `POST /api/token` - Login (returns access_token, sets refresh cookie)
- `POST /api/token/refresh` - Refresh access token
- `POST /api/token/revoke` - Logout (revokes refresh token)
- `GET /api/me` - Current user info

### Users
- `POST /api/users` - Register new user
- `GET /api/users` - List all users (admin only)
- `GET /api/users/<id>` - Get user info
- `PUT /api/users/<id>` - Update user

### Settings & Progress
- `GET /api/settings` - Get user settings (preferred_name, words_per_session, has_deepseek_key, has_gemini_key)
- `PUT /api/settings` - Update settings (preferred_name, words_per_session)
- `POST /api/settings/keys/<provider>/validate` - Validate and save API key (provider: deepseek|gemini)
- `DELETE /api/settings/keys/<provider>` - Clear API key and increment version
- `GET /api/progress/stats` - Get home page stats (words_practiced_today, mastery_percentage, words_ready_for_review, total_words)
- `GET /api/progress/streak` - Get day streak (current_streak, last_practice_date)
- `GET /api/progress/report-card` - Get report card data (topline metrics, daily chart, score breakdown, teacher feedback)
- `POST /api/progress/generate-feedback` - Trigger AI report card feedback generation (fire-and-forget from frontend)

### Sessions (admin/raw access)
- `GET /api/sessions` - List all sessions (admin only)
- `POST /api/sessions` - Create session
- `GET /api/sessions/<id>` - Get session details
- `PUT /api/sessions/<id>` - Update session

### Practice (AI-powered session flow)
- `POST /api/practice/sessions` - Start a new practice session (body: `{deck_id, words_count?}`) - deck_id is **required** in M5
- `POST /api/practice/sessions/<id>/messages` - Send message during practice (body: `{message}`)
- `POST /api/practice/sessions/<id>/next-word` - Advance to next word (body: `{quality: int}`, computes averaged scores, updates SRS state and mastery via user's quality rating 0-5)
- `POST /api/practice/sessions/<id>/end` - End session early (marks remaining words as skipped, generates summary)
- `GET /api/practice/sessions/<id>/summary` - Get session summary

### Utility
- `GET /api/` - Health check

## Confidence Score Formula
```
correctnessFactor = 1.0 if isCorrect else -0.5
qualityMultiplier = (0.4 * avgGrammarScore + 0.4 * avgUsageScore + 0.2 * avgNaturalnessScore) / 10.0
learningRate = 0.1
newScore = clamp(currentScore + correctnessFactor * qualityMultiplier * learningRate, 0.0, 1.0)
```
- `isCorrect = avgGrammarScore == 10 AND avgUsageScore >= 8`
- Scores are averages across all attempts for the word in the session
- Applied once per word when the user clicks "Next Word"
