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
- Flask-JWT-Extended for authentication
- Flask-CORS for cross-origin support

## Project Structure

```
laoshi/
├── backend/
│   ├── app.py              # Flask app factory & route registration
│   ├── models.py           # SQLAlchemy models
│   ├── resources.py        # REST API endpoints
│   ├── extensions.py       # Flask extensions (db, jwt)
│   ├── config.py           # Configuration from .env
│   ├── utils.py            # Helper functions
│   ├── requirements.txt    # Python dependencies
│   └── migrations/         # Alembic database migrations
├── frontend/
│   └── src/
│       ├── App.tsx         # React Router configuration
│       ├── main.tsx        # Entry point
│       ├── index.css       # Global styles (Tailwind)
│       ├── components/     # Layout, Sidebar, Header
│       └── pages/          # Welcome, Home, Practice, Vocabulary, Progress, Settings
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

# Create a .env file in the project root with:
#   SQLALCHEMY_DATABASE_URI=postgresql://user:password@localhost/laoshi_db
#   JWT_SECRET_KEY=your-secret-key

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

## API Overview

All endpoints are served from the Flask backend on port 5000. Most require JWT authentication.

| Area | Endpoints |
|------|-----------|
| Auth | `POST /token`, `GET /me` |
| Users | `POST /users`, `GET /users`, `GET/PUT /users/<id>` |
| Words | `GET/POST/DELETE /words`, `GET/PUT/DELETE /words/<id>` |
| Sessions | `GET/POST /sessions`, `GET/PUT /sessions/<id>` |
| Session Words | `GET/POST /sessions/<id>/words`, `GET/PUT /sessions/<id>/words/<word_id>` |

## Data Models

- **User** - account with username, email, hashed password, preferred name
- **Word** - vocabulary entry with Chinese characters, pinyin, meaning, and a confidence score (0-1) that determines status (Needs Revision / Learning / Reviewing / Mastered)
- **UserSession** - a practice session with start/end timestamps
- **SessionWord** - junction table linking words to sessions, with skip/notes tracking
