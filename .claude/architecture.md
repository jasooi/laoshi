# architecture.md

## Frontend Stack
- React 18 + TypeScript + Vite
- Tailwind CSS (purple color scheme, primary: #9333EA)
- React Router DOM for navigation
- Axios for HTTP requests

## Backend Stack
- Flask + Flask-RESTful
- SQLAlchemy ORM with PostgreSQL
- Flask-JWT-Extended for authentication
- Flask-Migrate (Alembic) for migrations

## AI Layer Stack
- OpenAI Agents SDK (`openai-agents`) - multi-agent orchestration
- DeepSeek API (via OpenAI-compatible client) - feedback agent (sentence evaluation)
- Gemini Flash API (via OpenAI-compatible client) - orchestrator + summary agents
- mem0 (`mem0ai`) - cross-session persistent user memory
- Redis - session-scoped conversation history (via SDK's `RedisSession`)

## API Proxy
Vite proxies `/api/*` requests to `http://localhost:5000` during development.

## Repository Structure
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
├── extensions.py       # Flask extensions (db, jwt)
├── config.py           # Configuration from .env
├── utils.py            # Helpers (password hashing, pagination, filters)
└── ai_layer/
    ├── context.py          # UserSessionContext and WordContext dataclasses
    ├── chat_agents.py      # Agent definitions (orchestrator, feedback, summary)
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
- **Word**: Vocabulary items with `confidence_score` (0-1) and computed `status` property (Mastered >0.9, Reviewing >0.7, Learning >0.3, Needs Revision <=0.3)
- **User**: Accounts with username, email, password (hashed)
- **UserProfile**: 1:1 with User. Stores `preferred_name`, `words_per_session`, encrypted API keys (`encrypted_deepseek_api_key`, `encrypted_gemini_api_key`), and key versions (`deepseek_key_version`, `gemini_key_version`) for session invalidation on key changes.
- **UserSession**: Practice sessions with start/end timestamps, `summary_text`, `words_per_session`
- **SessionWord**: Links words to sessions with `word_order`, averaged scores (`grammar_score`, `usage_score`, `naturalness_score`), `is_correct`, `is_skipped`. Scores are computed as averages across all attempts when the user clicks "Next Word".
- **SessionWordAttempt**: Individual sentence attempts per word per session. Stores per-attempt scores from the feedback agent (grammar_score, usage_score, naturalness_score, is_correct, feedback text). Multiple rows per word per session.
- **TokenBlocklist**: Revoked JWT refresh tokens

## AI Agent Architecture
Three agents orchestrated via the OpenAI Agents SDK:

| Agent | Model | Role | Communication |
|---|---|---|---|
| Orchestrator | Gemini Flash | Primary agent. Sassy teacher persona. Intent classification (sentence vs chat). | Calls Feedback Agent as tool; hands off to Summary Agent at session end |
| Feedback Agent | DeepSeek | Evaluates sentences. Returns structured JSON scores. Stateless. | Agent-as-tool (called by Orchestrator) |
| Summary Agent | Gemini Flash | Produces end-of-session summary and mem0 update recommendations. | Handoff from Orchestrator when session complete |

**Data flow:** App code hydrates read-only `UserSessionContext` before each `Runner.run()` call. Agents never access DB or mem0 directly. All writes happen in app code after agent output is returned.

**Conversation history:** Stored in Redis via the SDK's `RedisSession`, keyed by session ID. Cleared at session end.

**Persistent memory:** mem0 stores cross-session user preferences and learning patterns. Read at session start, written at session end based on Summary Agent recommendations.

## API Endpoints

### Vocabulary
- `GET /api/words` - List user's words (paginated, searchable, sortable)
- `POST /api/words` - Bulk create words (JSON array)
- `GET /api/words/<id>` - Get single word
- `PUT /api/words/<id>` - Update word fields
- `DELETE /api/words/<id>` - Delete single word
- `DELETE /api/words` - Delete all user's words

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

### Sessions (admin/raw access)
- `GET /api/sessions` - List all sessions (admin only)
- `POST /api/sessions` - Create session
- `GET /api/sessions/<id>` - Get session details
- `PUT /api/sessions/<id>` - Update session

### Practice (AI-powered session flow)
- `POST /api/practice/sessions` - Start a new practice session (body: `{words_count?}`)
- `POST /api/practice/sessions/<id>/messages` - Send message during practice (body: `{message}`)
- `POST /api/practice/sessions/<id>/next-word` - Advance to next word (computes averaged scores, updates confidence)
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
