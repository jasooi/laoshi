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

## API Proxy
Vite proxies `/api/*` requests to `http://localhost:5000` during development.

## Repository Structure
### Frontend
```
frontend/src/
├── App.tsx           # Router configuration
├── main.tsx          # Entry point
├── components/       # Reusable components (Layout, Sidebar, Header)
└── pages/            # Page components
```

### Backend
```
backend/
├── app.py            # Flask app factory, route registration
├── models.py         # SQLAlchemy models (Word, User, UserSession, SessionWord)
├── resources.py      # Flask-RESTful endpoints
├── extensions.py     # Flask extensions (db, jwt)
├── config.py         # Configuration from .env
└── utils.py          # Helpers (password hashing, filters)
```

## Environment Variables
Backend requires `.env` file with:
- `DATABASE_URI` - PostgreSQL connection string
- `JWT_SECRET_KEY` - Secret for JWT tokens
- `DEEPSEEK_API_KEY` - API key for DeepSeek model (primary)
- `GEMINI_API_KEY` - API key for Gemini 2.5 Flash model (backup)

## Database Models
- **Word**: Vocabulary items with confidence_score (0-1) and computed `status` property
- **User**: Accounts with username, email, password (hashed)
- **UserSession**: Practice sessions with start/end timestamps
- **SessionWord**: Junction table linking words to sessions

## API Endpoints
- `/words` - Vocabulary CRUD (list, create bulk, delete all)
- `/words/<id>` - Single word operations
- `/users`, `/users/<id>` - User management
- `/sessions`, `/sessions/<id>` - Practice session management
- `/sessions/<id>/words` - Words within a session
- `/token` - Login (returns JWT)
- `/me` - Current user info

## Performance Optimization
- **Frontend**:
  - Code splitting
  - Lazy loading of components
  - Virtual scrolling for long word lists
- **Backend**:
  - Database indexing
  - Query optimization
  - Response caching
  - Connection pooling






