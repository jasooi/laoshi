# Laoshi Coach

A Mandarin Chinese language learning app that helps users practice sentence formation with AI-powered coaching. Users import vocabulary, practice creating sentences with target words, and receive evaluation and feedback with confidence score tracking.

## Tech Stack

**Frontend**
- React 18 with TypeScript
- Vite for build tooling
- Tailwind CSS for styling
- React Router for navigation
- Axios for HTTP requests

**Backend**
- Python Flask with Flask-RESTful
- SQLAlchemy ORM with PostgreSQL
- Flask-Migrate (Alembic) for database migrations
- Flask-JWT-Extended for authentication (access tokens + refresh cookies)
- Flask-Limiter for rate limiting
- Fernet symmetric encryption for BYOK API key storage

**AI Layer**
- OpenAI Agents SDK for multi-agent orchestration
- DeepSeek API for sentence evaluation (Feedback Agent)
- Gemini Flash API for orchestration and summaries (Orchestrator + Summary Agents)
- mem0 for cross-session persistent user memory
- Redis for session-scoped conversation history

**Gateway**
- Nginx reverse proxy for production routing

## Project Structure

```
laoshi/
├── gateway/
│   ├── nginx.conf          # Reverse proxy: /api/* → backend, /* → frontend
│   └── Dockerfile          # nginx:alpine container
├── backend/
│   ├── app.py              # Flask app factory & route registration
│   ├── models.py           # SQLAlchemy models
│   ├── resources.py        # REST API endpoints (words, users, auth)
│   ├── practice_resources.py   # AI practice session endpoints
│   ├── settings_resources.py   # User settings & BYOK key endpoints
│   ├── progress_resources.py   # Progress stats endpoint
│   ├── extensions.py       # Flask extensions (db, jwt, limiter)
│   ├── config.py           # Configuration from .env
│   ├── crypto_utils.py     # Fernet encryption for API keys
│   ├── utils.py            # Helper functions (pagination, password hashing)
│   ├── ai_layer/
│   │   ├── chat_agents.py      # Agent definitions & build_agents() factory
│   │   ├── practice_runner.py  # Session flow: init, message handling, scoring
│   │   ├── context.py          # UserSessionContext and WordContext dataclasses
│   │   ├── mem0_setup.py       # mem0 client initialization
│   │   └── chat_service.py     # Redis session setup
│   ├── requirements.txt    # Python dependencies
│   └── migrations/         # Alembic database migrations
├── frontend/
│   └── src/
│       ├── App.tsx         # React Router configuration
│       ├── main.tsx        # Entry point
│       ├── index.css       # Global styles (Tailwind)
│       ├── components/     # Layout, Sidebar, Header, FeedbackCard, SessionSummary
│       ├── contexts/       # AuthContext (JWT token management)
│       ├── lib/            # API client (Axios instance, practiceApi, settingsApi, progressApi)
│       ├── types/          # TypeScript interfaces
│       └── pages/          # Welcome, Home, Practice, Vocabulary, Settings
├── vite.config.ts          # Vite config (dev server + API proxy)
├── tailwind.config.js      # Tailwind theme config
├── package.json            # Frontend dependencies
└── .env                    # Environment variables (not committed)
```

## Getting Started

### Prerequisites

- Node.js
- Python 3
- PostgreSQL
- Redis

### Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv ../laoshivenv
# Windows:
..\laoshivenv\Scripts\activate
# Mac/Linux:
source ../laoshivenv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create a .env file in the project root (see Environment Variables below)

# Run database migrations
flask db upgrade

# Start the server (port 5000)
python app.py
```

### Frontend Setup

```bash
# From the project root
npm install
npm run dev
```

The frontend runs at `http://localhost:5173` and proxies API requests to the backend at `http://localhost:5000`.

### Production Deployment

In production, the Nginx gateway (`gateway/`) serves as the single public entry point:
- `/api/*` requests are routed to the backend service
- All other requests are routed to the frontend service

Deploy the gateway as a separate service alongside the frontend and backend. Bind your public domain to the gateway only.

## Environment Variables

Backend requires a `.env` file with:

| Variable | Description |
|---|---|
| `SQLALCHEMY_DATABASE_URI` | PostgreSQL connection string |
| `JWT_SECRET_KEY` | Secret for JWT token signing |
| `ENCRYPTION_KEY` | Fernet key for encrypting BYOK API keys |
| `DEEPSEEK_API_KEY` | API key for DeepSeek model |
| `DEEPSEEK_BASE_URL` | DeepSeek API base URL |
| `DEEPSEEK_MODEL_NAME` | DeepSeek model identifier |
| `GEMINI_API_KEY` | API key for Gemini Flash model |
| `GEMINI_BASE_URL` | Gemini API base URL |
| `GEMINI_MODEL_NAME` | Gemini model identifier |
| `MEM0_API_KEY` | API key for mem0 persistent memory |
| `REDIS_URI` | Redis connection string |

## API Overview

All endpoints are prefixed with `/api`. Most require JWT authentication.

| Area | Endpoints |
|---|---|
| Auth | `POST /api/token`, `POST /api/token/refresh`, `POST /api/token/revoke`, `GET /api/me` |
| Users | `POST /api/users`, `GET /api/users/<id>`, `PUT /api/users/<id>` |
| Words | `GET/POST/DELETE /api/words`, `GET/PUT/DELETE /api/words/<id>` |
| Practice | `POST /api/practice/sessions`, `POST .../messages`, `POST .../next-word`, `GET .../summary` |
| Settings | `GET/PUT /api/settings`, `DELETE /api/settings/keys/<provider>`, `POST .../validate` |
| Progress | `GET /api/progress/stats` |

## Data Models

- **User** - Account with username, email, hashed password
- **UserProfile** - 1:1 with User. Stores preferred name, words per session, encrypted BYOK API keys
- **Word** - Vocabulary entry with Chinese characters, pinyin, meaning, and confidence score (0-1) determining status (Needs Revision / Learning / Reviewing / Mastered)
- **UserSession** - Practice session with timestamps, summary text, words per session count
- **SessionWord** - Links words to sessions with averaged scores and correctness tracking
- **SessionWordAttempt** - Individual sentence attempts with per-attempt feedback scores
- **TokenBlocklist** - Revoked JWT refresh tokens
