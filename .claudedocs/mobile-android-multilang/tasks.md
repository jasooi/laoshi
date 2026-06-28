# Mobile Android + Multi-Language Support -- Task Breakdown

## Task Overview

**Total tasks**: 56 tasks across 9 phases (Phase 1A-1E for backend/web, Phase 2A-2D for Android)
**Phase 1** (backend multi-language + web frontend): 31 tasks (includes T-020b, T-025b)
**Phase 2** (Android mobile app): 25 tasks (includes T-031b, Hilt DI changes)
**Phases are sequential within each group.** Phase 2 can begin after Phase 1C (API endpoints stable).

---

## Prerequisites

Before starting any tasks:

1. Ensure Milestones 7, 8, and 9 are complete (or at least M9 onboarding is stable).
2. Ensure `flask db upgrade` runs without errors.
3. Ensure `npm run build` succeeds in `frontend/`.
4. Read the design document: `.claudedocs/mobile-android-multilang/design.md`.
5. Read the plan file: `C:\Users\Jasmine\.claude\plans\lazy-purring-sparrow.md`.

---

## Phase 1A: Database + Models

Schema changes and model updates. Must be done first.

---

### T-001: Create Alembic migration for Deck.language and Word.pinyin -> reading rename

**Description**: Create a single migration that adds the `language` column to the `deck` table and renames `word.pinyin` to `word.reading`.

**Files affected**:
- New migration file in `backend/migrations/versions/`

**Changes**:
```python
def upgrade():
    # Add language column to deck table
    op.add_column('deck', sa.Column('language', sa.String(2), nullable=False, server_default='ZH'))

    # Rename word.pinyin to word.reading
    op.alter_column('word', 'pinyin', new_column_name='reading')

def downgrade():
    op.alter_column('word', 'reading', new_column_name='pinyin')
    op.drop_column('deck', 'language')
```

**Acceptance criteria**:
- `flask db migrate` generates the migration.
- `flask db upgrade` runs without errors.
- All existing decks have `language='ZH'`.
- All existing words have their pinyin data preserved in the renamed `reading` column.
- `flask db downgrade` reverses the changes cleanly.

**Dependencies**: None.

---

### T-002: Update Deck model with language field

**Description**: Add the `language` column and `SUPPORTED_LANGUAGES` constant to the `Deck` model. Update `format_data()`.

**Files affected**:
- `backend/models.py` -- `Deck` class

**Changes**:
1. Add to `Deck` class:
```python
language = db.Column(db.String(2), nullable=False, default='ZH', server_default='ZH')

SUPPORTED_LANGUAGES = ('ZH', 'JP')
```

2. Update `format_data()` to include `'language': self.language`.

**Acceptance criteria**:
- `Deck` model has `language` field with default `'ZH'`.
- `SUPPORTED_LANGUAGES` constant is accessible as `Deck.SUPPORTED_LANGUAGES`.
- `format_data()` includes `language` in output.
- Existing tests pass (default `'ZH'` applied).

**Dependencies**: T-001.

---

### T-003: Rename Word.pinyin to Word.reading in model

**Description**: Rename the `pinyin` column to `reading` in the `Word` model. Update `__repr__` and `format_data()`.

**Files affected**:
- `backend/models.py` -- `Word` class

**Changes**:
1. Rename column declaration:
```python
reading = db.Column(db.String(150), nullable=False)  # Was: pinyin
```

2. Update `__repr__`:
```python
def __repr__(self):
    return f"{self.id} - {self.word} - {self.reading} - {self.meaning}"
```

3. Update `format_data()`:
```python
'reading': self.reading,  # Was: 'pinyin': self.pinyin
```

**Acceptance criteria**:
- `Word` model uses `reading` attribute instead of `pinyin`.
- `format_data()` returns `reading` key instead of `pinyin`.
- `__repr__` uses `self.reading`.

**Dependencies**: T-001.

---

## Phase 1B: AI Layer

Context dataclasses, prompts, model routing, and LiteLLM integration.

---

### T-004: Update AI context dataclasses with language and reading

**Description**: Rename `pinyin` to `reading` in `WordContext`. Add `language` field to `WordContext`, `UserSessionContext`, and `ReportCardContext`.

**Files affected**:
- `backend/ai_layer/context.py`

**Changes**:
```python
@dataclass
class WordContext:
    word_id: int
    word: str
    reading: str       # Was: pinyin
    meaning: str
    language: str      # New: 'ZH' or 'JP'

@dataclass
class UserSessionContext:
    user_id: int
    session_id: int
    preferred_name: str
    current_word: WordContext | None
    session_word_dict: dict
    words_practiced: int
    words_skipped: int
    words_total: int
    session_complete: bool
    mem0_preferences: str | None
    word_roster: list[WordContext]
    language: str      # New: 'ZH' or 'JP'

@dataclass
class ReportCardContext:
    user_id: int
    preferred_name: str
    mem0_preferences: str | None
    recent_summaries: str | None
    avg_grammar: float
    avg_usage: float
    avg_naturalness: float
    language: str      # New: 'ZH' or 'JP'
```

**Acceptance criteria**:
- All three dataclasses have the new `language` field.
- `WordContext` uses `reading` instead of `pinyin`.
- No import errors.

**Dependencies**: None (can start in parallel with T-001).

---

### T-005: Add LANGUAGE_CONFIG dict and update prompt builders

**Description**: Create the `LANGUAGE_CONFIG` dictionary and update all four prompt builders to use language-aware templates.

**Files affected**:
- `backend/ai_layer/chat_agents.py`

**Changes**:

1. Add `LANGUAGE_CONFIG` at module level:
```python
LANGUAGE_CONFIG = {
    'ZH': {
        'name': 'Mandarin Chinese',
        'reading_label': 'pinyin',
        'feedback_focus': 'word order, particles, verb aspect, measure words',
        'feedback_language': 'simple Chinese',
        'example_type': 'Mandarin Chinese',
    },
    'JP': {
        'name': 'Japanese',
        'reading_label': 'furigana',
        'feedback_focus': 'particle usage (wa/ga/wo/ni), verb conjugation, keigo levels, word order (SOV)',
        'feedback_language': 'simple Japanese',
        'example_type': 'Japanese',
    },
}
```

2. Update `build_feedback_prompt`:
- Get `lang = LANGUAGE_CONFIG.get(ctx.language, LANGUAGE_CONFIG['ZH'])`
- Replace `"Mandarin Chinese"` with `lang['name']`
- Replace `word.pinyin` with `word.reading`
- Replace hardcoded grammar criteria with `lang['feedback_focus']`
- Replace `"simple Chinese"` with `lang['feedback_language']`

3. Update `build_orchestrator_prompt`:
- Replace `"Mandarin Chinese teacher"` with `f"{lang['name']} teacher"`
- Keep `"Laoshi"` persona name
- Replace `word.pinyin` with `word.reading`

4. Update `build_summary_prompt`:
- Replace `"Mandarin practice session"` with language-aware text
- Replace `wc.pinyin` with `wc.reading`

5. Update `build_report_card_prompt`:
- Replace `"Mandarin Chinese teacher"` with language-aware version

**Acceptance criteria**:
- All prompt builders use `ctx.language` to select from `LANGUAGE_CONFIG`.
- All `pinyin` references replaced with `reading`.
- ZH prompts produce identical output to current (backward compat).
- JP prompts produce Japanese-specific feedback criteria and language.
- Default fallback to ZH config if language not in dict.

**Dependencies**: T-004.

---

### T-006: Add Anthropic/Claude via LiteLLM client

**Description**: Add Claude model client initialization using direct LiteLLM (no proxy). Make it optional (graceful skip if `ANTHROPIC_API_KEY` not set).

**Files affected**:
- `backend/ai_layer/chat_agents.py`

**Changes**:

1. Add env vars:
```python
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL_NAME = os.getenv("ANTHROPIC_MODEL_NAME", "claude-3-5-sonnet-20241022")
```

2. Create Claude client using direct LiteLLM (no proxy -- litellm already a dependency via mem0):
```python
claude_model = None
if ANTHROPIC_API_KEY:
    try:
        claude_client = AsyncOpenAI(
            base_url="https://api.anthropic.com/v1",
            api_key=ANTHROPIC_API_KEY,
        )
        claude_model = OpenAIChatCompletionsModel(
            model=ANTHROPIC_MODEL_NAME,
            openai_client=claude_client,
        )
        logger.info("Claude model initialized for JP feedback")
    except Exception as e:
        logger.warning(f"Failed to initialize Claude model: {e}. JP feedback will be unavailable.")
else:
    logger.warning("ANTHROPIC_API_KEY not set. Japanese feedback will use DeepSeek fallback.")
```

3. Do NOT add `ANTHROPIC_API_KEY` to the `env_list` validation check (it's optional).
4. Do NOT use a LiteLLM proxy URL -- use direct `litellm.acompletion()` via the OpenAI-compatible wrapper.

**Acceptance criteria**:
- If `ANTHROPIC_API_KEY` is set, `claude_model` is initialized via direct LiteLLM.
- If `ANTHROPIC_API_KEY` is not set, `claude_model` is `None` and a warning is logged.
- Backend starts successfully with or without the key.
- No crash if Claude client initialization fails.
- No LiteLLM proxy service needed.

**Dependencies**: None.

---

### T-007: Implement language-based model routing in build_agents

**Description**: Update `build_agents()` to accept a `language` parameter and route the feedback agent to the appropriate model.

**Files affected**:
- `backend/ai_layer/chat_agents.py`

**Changes**:

1. Update `build_agents()` signature:
```python
def build_agents(deepseek_api_key=None, gemini_api_key=None, language='ZH'):
```

2. Create module-level cached JP agents (parallel to ZH singletons):
```python
# Module-level JP agent singletons (created at import time if claude_model available)
jp_feedback_agent = None
jp_laoshi_agent = None
jp_summary_agent = None
if claude_model:
    jp_feedback_agent = Agent[UserSessionContext](
        name="feedback_agent", instructions=build_feedback_prompt, model=claude_model
    )
    jp_summary_agent = Agent[UserSessionContext](
        name="summary_agent", instructions=build_summary_prompt, model=gemini_model
    )
    jp_laoshi_agent = Agent[UserSessionContext](
        name="laoshi_orchestrator", instructions=build_orchestrator_prompt, model=gemini_model,
        tools=[jp_feedback_agent.as_tool(
            tool_name="evaluate_sentence",
            tool_description="Evaluate student's Japanese sentence and give feedback..."
        )],
    )
```

3. Update `build_agents()` to return cached agents for both languages:
```python
def build_agents(deepseek_api_key=None, gemini_api_key=None, language='ZH'):
    # Return cached singletons when no custom keys
    if not deepseek_api_key and not gemini_api_key:
        if language == 'JP' and jp_laoshi_agent:
            return jp_laoshi_agent, jp_summary_agent
        return laoshi_agent, summary_agent

    # Build custom agents only when BYOK keys provided
    # ... (same logic, but picks feedback model by language) ...
```

4. Update `build_report_card_agent()` to accept `language` for prompt context:
```python
def build_report_card_agent(gemini_api_key=None, language='ZH'):
    # Language is handled in the prompt builder via context, not model selection
    # Report card always uses Gemini
    ...
```

5. Update the `evaluate_sentence` tool description to be language-aware.

**Acceptance criteria**:
- `build_agents(language='ZH')` returns cached ZH agents (existing behavior).
- `build_agents(language='JP')` returns cached JP agents (no object creation per request).
- `build_agents(language='JP')` falls back to ZH agents if `claude_model` is None.
- BYOK keys bypass cache and create fresh agents.
- Tool description adapts to language.

**Dependencies**: T-005, T-006.

---

### T-008: Thread language through practice_runner.py

**Description**: Update all functions in `practice_runner.py` to use `language` from `session.deck.language` and `reading` instead of `pinyin`.

**Files affected**:
- `backend/ai_layer/practice_runner.py`

**Changes**:

1. Update `hydrate_context()`:
- Use `word.reading` instead of `word.pinyin`
- Look up `session.deck.language` and pass to `UserSessionContext`
- Create `WordContext` with `reading=word.reading, language=deck_language`

2. Update `get_user_agent()` (or wherever agents are obtained):
- Accept `language` param, pass to `build_agents(language=language)`

3. Update `initialize_session()`:
- Get `deck_language = deck.language`
- Thread `language` through context creation and agent construction
- Use `reading` in word info strings

4. Update `handle_message()`:
- Pass `session.deck.language` to agent construction

5. Update `advance_word()`:
- Use `word.reading` in next-word introduction message
- Use `reading` in API response data

6. Update `complete_session()`:
- Pass `language` to agent construction

**Acceptance criteria**:
- All practice runner functions use `reading` instead of `pinyin`.
- `UserSessionContext` always has `language` set from `session.deck.language`.
- `WordContext` instances use `reading` and include `language`.
- ZH sessions work identically to before.
- JP sessions use Claude feedback model (if configured).

**Dependencies**: T-003, T-004, T-007.

---

## Phase 1C: API Endpoints

Update all API endpoints for reading field and language support.

---

### T-009: Update deck_resources.py for language support

**Description**: Accept `language` parameter on deck creation, validate against `SUPPORTED_LANGUAGES`, and handle combine validation.

**Files affected**:
- `backend/deck_resources.py`

**Changes**:

1. `create_deck` endpoint -- accept `language`:
```python
language = data.get('language', 'ZH')
if language not in Deck.SUPPORTED_LANGUAGES:
    return {'error': f'Unsupported language. Must be one of: {", ".join(Deck.SUPPORTED_LANGUAGES)}'}, 400
deck = Deck(name=name, description=description, user_id=user_id, language=language)
```

2. `add_words_to_deck` -- accept `reading` (backward compat with `pinyin`):
```python
reading = word_data.get('reading') or word_data.get('pinyin', '')
```

3. `get_decks` -- accept optional `?language=` query parameter to filter decks by language.

4. `get_deck_words` -- search/sort on `Word.reading` instead of `Word.pinyin`.

5. `combine_decks` -- validate source decks share same language:
```python
languages = set(d.language for d in source_decks)
if len(languages) > 1:
    return {'error': 'Cannot combine decks with different languages'}, 400
new_deck.language = languages.pop()
```

**Acceptance criteria**:
- `POST /api/decks` with `{"name": "Test", "language": "JP"}` creates a JP deck.
- `POST /api/decks` without `language` defaults to ZH.
- Invalid language returns 400.
- `POST /api/decks/<id>/words` accepts both `reading` and `pinyin` fields.
- `POST /api/decks/combine` rejects mixed-language source decks.
- `GET /api/decks/<id>/words` sorts by `Word.reading`.

**Dependencies**: T-002, T-003.

---

### T-010: Update resources.py for reading field and OAuth2 client credentials

**Description**: Update word CRUD endpoints to use `reading` instead of `pinyin`. Implement OAuth2 client credentials auth.

**Files affected**:
- `backend/resources.py`

**Changes**:

1. Word CRUD endpoints -- use `reading`:
```python
# Accept both 'reading' and 'pinyin' for backward compat
reading = data.get('reading') or data.get('pinyin')
```

2. `WORD_FIELD_LIMITS` -- rename `pinyin` to `reading`:
```python
WORD_FIELD_LIMITS = {
    'word': 200,
    'reading': 200,  # Was: 'pinyin': 200
    'meaning': 300,
    'notes': 200,
}
```

3. `TokenResource.post` -- OAuth2 client credentials:
```python
from config import OAUTH_CLIENTS

# Validate client credentials
client_id = data.get('client_id')
client_secret = data.get('client_secret')
if not client_id or client_id not in OAUTH_CLIENTS:
    return {'error': 'Invalid client_id'}, 400
client = OAUTH_CLIENTS[client_id]
if client['secret_required'] and client_secret != client['secret']:
    return {'error': 'Invalid client credentials'}, 401

# ... existing user auth logic ...

# Response based on client type
response_data = {'access_token': access_token}
if client['type'] == 'mobile':
    response_data['refresh_token'] = refresh_token
resp = make_response(jsonify(response_data))
set_refresh_cookies(resp, refresh_token)  # Always set cookie (harmless for mobile)
return resp
```

4. `TokenRefreshResource.post` -- manual refresh token extraction for mobile:
```python
from flask_jwt_extended import decode_token

data = request.get_json(silent=True) or {}
body_refresh_token = data.get('refresh_token')
if body_refresh_token:
    # Mobile path: manually decode and verify
    decoded = decode_token(body_refresh_token)
    user_id = decoded['sub']
    if decoded.get('type') != 'refresh':
        return {'error': 'Invalid token type'}, 401
    new_access_token = create_access_token(identity=user_id)
    return {'access_token': new_access_token}, 200
else:
    # Web path: Flask-JWT-Extended handles cookie-based token
    ...
```

5. Add rate limiting decorators:
```python
@limiter.limit("10/minute")  # on TokenResource.post
@limiter.limit("30/minute")  # on TokenRefreshResource.post
@limiter.limit("5/minute")   # on UserResource.post (register)
```

**Acceptance criteria**:
- `PUT /api/words/<id>` accepts `reading` field.
- `PUT /api/words/<id>` still accepts `pinyin` (mapped to `reading`).
- `POST /api/token` with `client_id=laoshi-android` + `client_secret` returns `refresh_token` in body.
- `POST /api/token` with `client_id=laoshi-web` (no secret) returns `access_token` only in body, refresh in cookie.
- `POST /api/token` without `client_id` returns 400.
- `POST /api/token/refresh` accepts `{"refresh_token": "..."}` from mobile (manual decode).
- Web cookie-based refresh flow unchanged.
- Rate limits enforced on auth endpoints.

**Dependencies**: T-003.

---

### T-011: Update practice_resources.py for reading field

**Description**: Update practice session endpoints to return `reading` instead of `pinyin` in word context.

**Files affected**:
- `backend/practice_resources.py`

**Changes**:

Session detail and message responses use `reading`:
```python
'current_word': {
    'word_id': word.id,
    'word': word.word,
    'reading': word.reading,  # Was: 'pinyin': word.pinyin
    'meaning': word.meaning,
}
```

**Acceptance criteria**:
- `POST /api/practice/sessions` response uses `reading` field.
- `POST /api/practice/sessions/<id>/messages` response uses `reading`.
- `GET /api/practice/sessions/<id>` response uses `reading`.

**Dependencies**: T-003, T-008.

---

### T-012: Update report_card_service.py for language awareness

**Description**: Make report card score descriptions language-parameterized and pass language to report card context.

**Files affected**:
- `backend/report_card_service.py`

**Changes**:

1. `SCORE_DESCRIPTIONS` -- make language-aware (different example text for ZH vs JP):
```python
SCORE_DESCRIPTIONS = {
    'ZH': {
        'grammar': { ... },  # Existing ZH descriptions
        'usage': { ... },
        'naturalness': { ... },
    },
    'JP': {
        'grammar': { ... },  # JP-specific descriptions
        'usage': { ... },
        'naturalness': { ... },
    },
}
```

2. `generate_report_card_feedback()` -- determine language from recent sessions:
```python
# Get most recent session's deck language
recent_session = UserSession.query.filter_by(user_id=user_id).order_by(UserSession.id.desc()).first()
language = recent_session.deck.language if recent_session and recent_session.deck else 'ZH'
```

3. Pass `language` to `ReportCardContext` and `build_report_card_agent()`.

**Acceptance criteria**:
- Report card score descriptions adapt to primary practice language.
- `ReportCardContext` includes `language` field.
- Defaults to ZH if no sessions or no deck.

**Dependencies**: T-004, T-005.

---

### T-013: Refactor sample_deck_service.py for multi-language seeding

**Description**: Refactor sample deck service to support per-language CSV files via env vars.

**Files affected**:
- `backend/sample_deck_service.py`

**Changes**:

1. Replace constants with per-language config:
```python
SAMPLE_DECK_CONFIG = {
    'ZH': {
        'env_var': 'ZH_SAMPLE_DECK_FILE',
        'default_file': 'swe_vocab_list.csv',
        'name': 'Software Engineering Vocabulary',
        'description': 'Common Mandarin vocabulary used in software engineering contexts.',
        'laoshi_message': 'This is a sample deck to help you get started with Laoshi! You can delete or modify this deck as you please.',
    },
    'JP': {
        'env_var': 'JP_SAMPLE_DECK_FILE',
        'default_file': 'jp_sample_vocab_list.csv',
        'name': 'Japanese Starter Vocabulary',
        'description': 'Common Japanese vocabulary to get you started with Laoshi.',
        'laoshi_message': 'This is a sample Japanese deck. Practice forming sentences!',
    },
}
```

2. Update `get_sample_csv_path()` to accept language:
```python
def get_sample_csv_path(language='ZH'):
    config = SAMPLE_DECK_CONFIG[language]
    csv_filename = os.getenv(config['env_var'], config['default_file'])
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(backend_dir, 'sample_decks', csv_filename))
```

3. Update `load_sample_words_from_csv()` to accept language and use `Reading`/`Pinyin` header:
```python
def load_sample_words_from_csv(language='ZH'):
    csv_path = get_sample_csv_path(language)
    if not os.path.exists(csv_path):
        logger.info(f"Sample CSV for {language} not found at {csv_path} - skipping.")
        return []
    # ...
    reading = row.get('Reading', '') or row.get('Pinyin', '')
    # ...
```

4. Update `seed_sample_deck_for_user()` to accept language:
```python
def seed_sample_deck_for_user(user_id, language='ZH'):
    config = SAMPLE_DECK_CONFIG[language]
    # Check if user already has this specific sample deck
    if Deck.query.filter_by(user_id=user_id, name=config['name']).first():
        return None
    # Create deck with language=language
    deck = Deck(name=config['name'], ..., language=language)
    # Use 'reading' for Word creation
    Word(word=wd['word'], reading=wd['reading'], meaning=wd['meaning'], ...)
```

5. Update registration to seed both:
```python
# In user registration handler
seed_sample_deck_for_user(user_id, language='ZH')
seed_sample_deck_for_user(user_id, language='JP')  # Skips if CSV missing
```

**Acceptance criteria**:
- ZH sample deck seeds as before (using `swe_vocab_list.csv`).
- JP sample deck seeds if `jp_sample_vocab_list.csv` exists.
- JP seeding is silently skipped if the CSV is missing.
- CSV parser accepts both `Reading` and `Pinyin` headers.
- Each sample deck has the correct `language` field set.
- Env vars `ZH_SAMPLE_DECK_FILE` and `JP_SAMPLE_DECK_FILE` override defaults.

**Dependencies**: T-002, T-003.

---

### T-014: Update config.py for OAuth2 client config and new env vars

**Description**: Add `OAUTH_CLIENTS` config for client credentials auth. Do NOT modify `JWT_TOKEN_LOCATION`. Add new env vars.

**Files affected**:
- `backend/config.py`

**Changes**:
```python
# JWT_TOKEN_LOCATION stays unchanged
JWT_TOKEN_LOCATION = ['headers', 'cookies']

# OAuth2 client registry
OAUTH_CLIENTS = {
    'laoshi-web': {
        'type': 'web',
        'secret_required': False,   # Public client (SPA)
    },
    'laoshi-android': {
        'type': 'mobile',
        'secret_required': True,    # Confidential client
        'secret': os.getenv('ANDROID_CLIENT_SECRET'),
    },
}
```

New env var: `ANDROID_CLIENT_SECRET`

**Acceptance criteria**:
- `OAUTH_CLIENTS` config accessible from resources.py.
- `JWT_TOKEN_LOCATION` remains `['headers', 'cookies']` (no `'json'`).
- `ANDROID_CLIENT_SECRET` env var documented and used.
- Backend starts successfully with or without `ANDROID_CLIENT_SECRET` (mobile auth simply fails if missing).

**Dependencies**: None.

---

## Phase 1D: Web Frontend

Update TypeScript types, API client, and UI components for reading/language.

---

### T-015: Update frontend TypeScript types

**Description**: Rename `pinyin` to `reading` in all type interfaces. Add `language` to `Deck`.

**Files affected**:
- `frontend/src/types/api.ts`

**Changes**:
```typescript
export interface Word {
  // ...
  reading: string        // Was: pinyin
}

export interface WordContext {
  word_id: number
  word: string
  reading: string       // Was: pinyin
  meaning: string
}

export interface Deck {
  // ...
  language: 'ZH' | 'JP'
}

export interface DeckWithStats extends Deck {
  // ... inherits language
}
```

**Acceptance criteria**:
- `Word` interface uses `reading` instead of `pinyin`.
- `WordContext` interface uses `reading` instead of `pinyin`.
- `Deck` interface includes `language: 'ZH' | 'JP'`.
- `npm run build` type-checks pass (after updating components).

**Dependencies**: None (can start in parallel with backend).

---

### T-016: Update frontend API client

**Description**: Update `lib/api.ts` to use `reading` field and accept `language` on deck creation.

**Files affected**:
- `frontend/src/lib/api.ts`

**Changes**:

1. `deckApi.createDeck` -- accept `language`:
```typescript
createDeck: (data: { name: string; description?: string; language?: 'ZH' | 'JP' }) =>
  api.post<DeckWithStats>('/api/decks', data),
```

2. `deckApi.addWordsToDeck` -- use `reading`:
```typescript
addWordsToDeck: (id: number, words: { word: string; reading: string; meaning: string; notes?: string }[]) =>
  api.post<{ created: Word[] }>(`/api/decks/${id}/words`, { words }),
```

3. `wordsApi.updateWord` -- use `reading`:
```typescript
updateWord: (wordId: number, data: { word?: string; reading?: string; meaning?: string; notes?: string }) =>
  api.put<Word>(`/api/words/${wordId}`, data),
```

**Acceptance criteria**:
- `deckApi.createDeck` sends `language` parameter.
- `deckApi.addWordsToDeck` sends `reading` field.
- `wordsApi.updateWord` sends `reading` field.

**Dependencies**: T-015.

---

### T-017: Add language selector to CreateDeckModal

**Description**: Add ZH/JP radio buttons to the create deck modal in the Library page.

**Files affected**:
- `frontend/src/pages/library/index.tsx` (or `CreateDeckModal.tsx` if separate)

**Changes**:

1. Add language state:
```typescript
const [language, setLanguage] = useState<'ZH' | 'JP'>('ZH')
```

2. Add radio buttons to modal:
```tsx
<div className="flex gap-4">
  <label className="flex items-center gap-2 cursor-pointer">
    <input type="radio" name="language" value="ZH"
           checked={language === 'ZH'} onChange={() => setLanguage('ZH')}
           className="accent-sage" />
    <span className="text-sm">Chinese (ZH)</span>
  </label>
  <label className="flex items-center gap-2 cursor-pointer">
    <input type="radio" name="language" value="JP"
           checked={language === 'JP'} onChange={() => setLanguage('JP')}
           className="accent-sage" />
    <span className="text-sm">Japanese (JP)</span>
  </label>
</div>
```

3. Pass `language` to `deckApi.createDeck()`.

4. Show language badge on deck cards:
```tsx
<span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-warm-gray/30 text-warm-black/50">
  {deck.language}
</span>
```

**Acceptance criteria**:
- Create deck modal has ZH/JP selector, defaulting to ZH.
- Selected language is sent to API.
- Deck cards show a small language badge.

**Dependencies**: T-016.

---

### T-018: Update DeckWordsView for dynamic column headers

**Description**: Change table header from hardcoded "Pinyin" to language-aware label.

**Files affected**:
- `frontend/src/pages/library/DeckWordsView.tsx`

**Changes**:

1. Determine label from deck language:
```typescript
const readingLabel = deck.language === 'JP' ? 'Furigana' : 'Pinyin'
```

2. Use `readingLabel` in table header, sort labels, and edit modal.

3. Update all `word.pinyin` references to `word.reading`.

4. Update `EditWordModal` to use dynamic label for reading field.

5. CSV upload: accept both `Pinyin` and `Reading` column headers:
```typescript
const reading = row['Reading'] || row['Pinyin'] || ''
```

**Acceptance criteria**:
- ZH deck shows "Pinyin" column header.
- JP deck shows "Furigana" column header.
- Sort dropdown labels adapt to language.
- Edit modal labels adapt.
- CSV upload accepts both header names.

**Dependencies**: T-015, T-016.

---

### T-019: Update FloatingWordPill for reading field

**Description**: Replace `word.pinyin` with `word.reading` in the floating word pill component.

**Files affected**:
- `frontend/src/pages/home/FloatingWordPill.tsx`

**Changes**:

Replace all instances of `word.pinyin` with `word.reading`:
```tsx
// Collapsed state
<span className="text-sm text-warm-black/40">{word.reading}</span>

// Expanded state
<span className="text-sm font-medium text-sage">{word.reading}</span>
```

**Acceptance criteria**:
- Word pill displays `reading` field from word context.
- No TypeScript errors.

**Dependencies**: T-015.

---

### T-020: Update PracticePanel for reading field

**Description**: Replace all `pinyin` references with `reading` in the practice chat panel.

**Files affected**:
- `frontend/src/pages/home/PracticePanel.tsx`

**Changes**:
- Replace `word.pinyin` with `word.reading` everywhere.
- Replace `pinyin` in any variable names or comments.

**Acceptance criteria**:
- All practice panel code uses `reading` instead of `pinyin`.
- No TypeScript errors.
- Practice flow works as before.

**Dependencies**: T-015.

---

### T-020b: Update web frontend login for client credentials

**Description**: Add `client_id` to the web frontend login request.

**Files affected**:
- `frontend/src/lib/api.ts`

**Changes**:

```typescript
const WEB_CLIENT_ID = 'laoshi-web'

// In login function, add client_id to request body
export const authApi = {
  login: (username: string, password: string) =>
    api.post('/api/token', { username, password, client_id: WEB_CLIENT_ID }),
}
```

**Acceptance criteria**:
- Web login sends `client_id: 'laoshi-web'` in request body.
- No `client_secret` sent (public client).
- Login flow works as before.

**Dependencies**: T-010 (backend client credentials).

---

### T-021: Update FeedbackCard for reading field

**Description**: Replace any `pinyin` references in the FeedbackCard component.

**Files affected**:
- `frontend/src/components/FeedbackCard.tsx`

**Changes**:
- Check for and replace any `pinyin` references with `reading`.
- If no `pinyin` references exist (FeedbackCard uses score data, not word data), mark as no-op.

**Acceptance criteria**:
- No `pinyin` references in FeedbackCard.
- Component renders correctly.

**Dependencies**: T-015.

---

## Phase 1E: Tests + Docs

Backend and frontend test updates, environment docs.

---

### T-022: Update all backend test fixtures for reading and language

**Description**: Rename `pinyin=` to `reading=` in all Word constructors across test files. Add `language='ZH'` to Deck constructors.

**Files affected**:
- All test files in `backend/tests/`

**Changes**:
- Search and replace `pinyin=` with `reading=` in Word constructors.
- Search and replace `['pinyin']` with `['reading']` in response assertions.
- Add `language='ZH'` to Deck constructors in fixtures where needed.
- Update any test that asserts on `pinyin` key in API responses.

**Acceptance criteria**:
- All existing backend tests pass with the renamed field.
- No references to `pinyin` in test Word constructors.

**Dependencies**: T-002, T-003.

---

### T-023: Create test_multilanguage.py backend tests

**Description**: New test file covering JP deck creation, model routing, backward compat, and language validation.

**Files affected**:
- New: `backend/tests/test_multilanguage.py`

**Changes**:

Test cases:
1. Create a JP deck via `POST /api/decks` with `language='JP'`.
2. Create a ZH deck (default language).
3. Reject invalid language (`POST /api/decks` with `language='KR'`).
4. Add words to JP deck with `reading` field.
5. Add words with `pinyin` field (backward compat -- mapped to `reading`).
6. Verify `GET /api/decks` returns `language` field.
7. Combine decks -- reject mixed languages.
8. Combine decks -- accept same language.
9. Verify `build_agents(language='JP')` returns different feedback model (mock test).
10. Verify `build_agents(language='ZH')` returns default agents.

**Acceptance criteria**:
- All 10+ tests pass.
- JP deck creation works end-to-end.
- Backward compat for `pinyin` field verified.
- Mixed-language combine rejected.

**Dependencies**: T-009, T-010.

---

### T-024: Update frontend tests for reading field

**Description**: Update all frontend test files referencing `pinyin` to use `reading`.

**Files affected**:
- All test files in `frontend/src/` referencing `pinyin`

**Changes**:
- Search and replace `pinyin` with `reading` in mock data and assertions.
- Update any component test that renders pinyin text.

**Acceptance criteria**:
- `npx vitest --run` passes with no failures.
- No `pinyin` references in test mock data.

**Dependencies**: T-015, T-019, T-020.

---

### T-025: Update environment docs and architecture.md

**Description**: Add new env vars to `.env` template and update architecture documentation.

**Files affected**:
- `.claude/architecture.md`
- `backend/CLAUDE.md` (if needed)

**Changes**:

1. Add to architecture.md Environment Variables section:
```
- `ANTHROPIC_API_KEY` - API key for Anthropic Claude (optional, for JP feedback)
- `ANTHROPIC_MODEL_NAME` - Claude model identifier (default: claude-3-5-sonnet-20241022)
- `ZH_SAMPLE_DECK_FILE` - Filename for ZH sample deck CSV (default: swe_vocab_list.csv)
- `JP_SAMPLE_DECK_FILE` - Filename for JP sample deck CSV (default: jp_sample_vocab_list.csv)
- `ANDROID_CLIENT_SECRET` - OAuth2 client secret for mobile app
```

2. Update Database Models section:
- `Deck`: Add `language` field description.
- `Word`: Rename `pinyin` to `reading`.

3. Update AI Agent Architecture table:
- Add Claude row for JP feedback.

4. Update API Endpoints section:
- `POST /api/decks` accepts `language`.
- Word endpoints use `reading`.

**Acceptance criteria**:
- Architecture doc reflects all schema and API changes.
- New env vars documented.

**Dependencies**: All Phase 1 tasks.

---

### T-025b: Set up API versioning (Nginx + Flask dev fallback)

**Description**: Add `/api/v1/` prefix aliasing so mobile app can use versioned paths while web continues on `/api/`.

**Files affected**:
- Nginx config (production)
- `backend/app.py` (development fallback)

**Changes**:

1. Nginx rewrite rule (production):
```nginx
location /api/v1/ {
    rewrite ^/api/v1/(.*)$ /api/$1 break;
    proxy_pass http://backend;
}
```

2. Flask development fallback:
```python
# backend/app.py
@app.before_request
def rewrite_v1():
    if request.path.startswith('/api/v1/'):
        request.environ['PATH_INFO'] = request.path.replace('/api/v1/', '/api/', 1)
```

**Acceptance criteria**:
- `GET /api/v1/decks` returns same response as `GET /api/decks`.
- All `/api/v1/*` paths route to corresponding `/api/*` handlers.
- Existing `/api/*` paths continue working (web frontend unchanged).
- Works in both development (Flask fallback) and production (Nginx).

**Dependencies**: None (can be done early).

---

### T-026: Build verification (Phase 1)

**Description**: Verify the full backend and frontend build after all Phase 1 changes.

**Steps**:
1. `flask db upgrade` -- migration succeeds.
2. Run all backend tests -- all pass.
3. `npm run build` in `frontend/` -- no TypeScript errors.
4. `npx vitest --run` -- all frontend tests pass.
5. Manual: Create ZH deck, run practice -- unchanged behavior.
6. Manual: Create JP deck, add words -- verify language badge, "Furigana" header.
7. Manual: Upload CSV with `Reading` header -- works.
8. Manual: Upload CSV with `Pinyin` header -- backward compat works.

**Acceptance criteria**:
- Zero errors in build and test runs.
- ZH practice session works identically to before.
- JP deck creation and word management works.

**Dependencies**: All Phase 1 tasks.

---

## Phase 2A: Android Project Setup

Gradle project, theme, networking, DTOs, repositories.

---

### T-027: Create Android project structure

**Description**: Initialize the Android project at `mobile_android/` with Gradle build files, manifest, and package structure.

**Files affected**:
- New: `mobile_android/` directory tree (see design doc section 7.1)
- New: `mobile_android/build.gradle.kts` (project-level)
- New: `mobile_android/settings.gradle.kts`
- New: `mobile_android/gradle.properties`
- New: `mobile_android/app/build.gradle.kts`
- New: `mobile_android/app/src/main/AndroidManifest.xml`

**Changes**:

1. Create project-level Gradle files with Compose BOM, Kotlin, AGP, and Hilt plugins.
2. Create app-level `build.gradle.kts` with all dependencies including Hilt (see design doc section 7.2).
3. Create `AndroidManifest.xml` with internet permission and single-activity setup.
4. Set `minSdk = 26`, `targetSdk = 34`, `compileSdk = 34`.
5. Set application ID: `com.laoshicoach.app`.
6. Add `BuildConfig` fields: `BASE_URL`, `CLIENT_ID`, `CLIENT_SECRET`.

**Acceptance criteria**:
- `./gradlew assembleDebug` succeeds from `mobile_android/`.
- Empty app launches on emulator.
- All dependencies resolve.

**Dependencies**: None (can start in parallel with Phase 1).

---

### T-028: Implement Material 3 theme

**Description**: Create the Laoshi theme with exact color palette, typography, and component patterns.

**Files affected**:
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/ui/theme/Color.kt`
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/ui/theme/Type.kt`
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/ui/theme/Theme.kt`

**Changes**:

1. `Color.kt` -- define all semantic colors:
```kotlin
val Sage = Color(0xFF6B8F71)
val SageTint = Color(0xFFEDF2EE)
val Coral = Color(0xFFD4715E)
val CoralTint = Color(0xFFFDF0ED)
val Amber = Color(0xFFC4973B)
val AmberTint = Color(0xFFFBF5E8)
val Neutral = Color(0xFFA8A5A0)
val NeutralTint = Color(0xFFF2F1EF)
val WarmOffwhite = Color(0xFFFAFAF8)
val WarmBlack = Color(0xFF2A2A28)
val WarmGray = Color(0xFFE8E5E0)
val WarmMuted = Color(0xFF8A8A86)
val ChatBg = Color(0xFFF5F3EE)
```

2. `Type.kt` -- define typography with Inter and serif CJK fonts.

3. `Theme.kt` -- `LaoshiTheme` composable wrapping `MaterialTheme` with custom `lightColorScheme()` mapping.

**Acceptance criteria**:
- `LaoshiTheme` applies correct colors and typography.
- Preview renders show correct visual appearance.

**Dependencies**: T-027.

---

### T-029: Implement networking layer (Retrofit, OkHttp, auth)

**Description**: Set up Retrofit API service, auth interceptor, token refresh authenticator, and token manager. All endpoints use `/api/v1/` prefix. Login includes `client_id` + `client_secret` from `BuildConfig`.

**Files affected**:
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/data/api/ApiService.kt`
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/data/api/AuthInterceptor.kt`
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/data/api/TokenRefreshAuthenticator.kt`
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/data/local/TokenManager.kt`

**Changes**: Implement as specified in design doc sections 9.1-9.4.

Key differences from basic implementation:
1. All `ApiService` endpoints use `/api/v1/` prefix.
2. `LoginRequest` includes `client_id` and `client_secret` from `BuildConfig`.
3. `TokenRefreshAuthenticator` uses `Mutex` + `CountDownLatch` pattern (no `runBlocking`) to avoid ANR.
4. `TokenManager` uses EncryptedSharedPreferences (stores both access and refresh tokens).

**Acceptance criteria**:
- `ApiService` interface has all endpoint methods with `/api/v1/` prefix.
- `AuthInterceptor` attaches JWT to requests.
- `TokenRefreshAuthenticator` refreshes on 401 using coroutine-safe Mutex pattern.
- `TokenManager` stores tokens in EncryptedSharedPreferences.
- Backend URL configurable via `BuildConfig.BASE_URL`.
- `BuildConfig.CLIENT_ID` and `BuildConfig.CLIENT_SECRET` used for auth.
- No `runBlocking` calls in OkHttp interceptors/authenticators.

**Dependencies**: T-027, T-010 (mobile auth backend changes).

---

### T-030: Create Kotlin DTOs

**Description**: Translate all TypeScript interfaces from `frontend/src/types/api.ts` to Kotlin data classes.

**Files affected**:
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/data/model/` -- multiple files

**Changes**:

Create data classes for:
- `Deck`, `DeckWithStats`, `Word`, `WordContext`
- `PracticeSessionResponse`, `PracticeMessageResponse`, `PracticeSummaryResponse`, `WordResult`
- `FeedbackData`, `ProgressStats`, `StreakData`
- `ReportCardData`, `ReportCardTopline`, `DailyChartData`, `ScoreDetail`, `ScoreBreakdown`
- `SettingsResponse`, `UserResponse`
- Request classes: `LoginRequest`, `RegisterRequest`, `CreateDeckRequest`, `AddWordsRequest`, etc.

All use `@SerializedName` for snake_case mapping where needed.

```kotlin
data class DeckWithStats(
    val id: Int,
    val name: String,
    val description: String?,
    @SerializedName("user_id") val userId: Int,
    @SerializedName("laoshi_message") val laoshiMessage: String?,
    val language: String,
    @SerializedName("word_count") val wordCount: Int,
    @SerializedName("mastered_count") val masteredCount: Int,
    @SerializedName("mastery_percentage") val masteryPercentage: Float,
    @SerializedName("last_practiced_at") val lastPracticedAt: String?,
)
```

**Acceptance criteria**:
- All API response shapes have corresponding Kotlin data classes.
- All request shapes have corresponding Kotlin data classes.
- `@SerializedName` annotations handle snake_case/camelCase mapping.
- All DTOs use `reading` field (not `pinyin`).

**Dependencies**: T-027, T-015 (need updated TypeScript types as reference).

---

### T-031: Create repository layer

**Description**: Create repository classes wrapping `ApiService` with `Result<T>` error handling.

**Files affected**:
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/data/repository/AuthRepository.kt`
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/data/repository/DeckRepository.kt`
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/data/repository/PracticeRepository.kt`
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/data/repository/ProgressRepository.kt`
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/data/repository/SettingsRepository.kt`

**Changes**:

Each repository wraps API calls with error handling:
```kotlin
class DeckRepository(private val api: ApiService) {
    suspend fun getDecks(): Result<List<DeckWithStats>> = runCatching {
        val response = api.getDecks()
        if (response.isSuccessful) response.body()!!.decks
        else throw ApiException(response.code(), response.errorBody()?.string())
    }
    // ...
}
```

**Acceptance criteria**:
- One repository per domain.
- All API calls wrapped in `Result<T>`.
- Error handling produces meaningful messages.

**Dependencies**: T-029, T-030.

---

### T-031b: Implement client-side repository caching

**Description**: Add `CachedValue<T>` utility and integrate in-memory caching with TTL into repositories for read-heavy endpoints.

**Files affected**:
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/data/repository/CachedValue.kt`
- Modified: `DeckRepository.kt`, `ProgressRepository.kt`, `SettingsRepository.kt`

**Changes**:

1. Create `CachedValue<T>`:
```kotlin
class CachedValue<T>(private val ttlMs: Long = 30_000L) {
    private var value: T? = null
    private var timestamp: Long = 0L
    fun get(): T? = if (System.currentTimeMillis() - timestamp > ttlMs) null else value
    fun set(newValue: T) { value = newValue; timestamp = System.currentTimeMillis() }
    fun invalidate() { value = null; timestamp = 0L }
}
```

2. Use in repositories:
- `DeckRepository`: 30s cache for `getDecks()`, invalidated on deck create/delete
- `ProgressRepository`: 60s cache for `getReportCard()`, invalidated on pull-to-refresh
- `SettingsRepository`: 60s cache for `getSettings()`, invalidated on settings update

3. All `get*()` methods accept `forceRefresh: Boolean = false` parameter.

**Acceptance criteria**:
- Repeated navigation to home screen doesn't re-fetch deck list within 30s.
- Pull-to-refresh bypasses cache.
- User-initiated mutations (create deck, complete practice) invalidate relevant caches.
- Cache is in-memory only (no persistence needed).

**Dependencies**: T-031.

---

## Phase 2B: Android Auth + Navigation

---

### T-032: Create LaoshiApp application class and Hilt DI setup

**Description**: Create the Application class with Hilt dependency injection. Create DI modules for networking, repositories, and storage.

**Files affected**:
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/LaoshiApp.kt`
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/di/NetworkModule.kt`
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/di/RepositoryModule.kt`
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/di/StorageModule.kt`

**Changes**:

```kotlin
@HiltAndroidApp
class LaoshiApp : Application()
```

```kotlin
// di/NetworkModule.kt
@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {
    @Provides @Singleton
    fun provideTokenManager(@ApplicationContext context: Context) = TokenManager(context)

    @Provides @Singleton
    fun provideOkHttpClient(tokenManager: TokenManager, authenticator: TokenRefreshAuthenticator) =
        OkHttpClient.Builder()
            .addInterceptor(AuthInterceptor(tokenManager))
            .authenticator(authenticator)
            .build()

    @Provides @Singleton
    fun provideRetrofit(client: OkHttpClient) =
        Retrofit.Builder()
            .baseUrl(BuildConfig.BASE_URL)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()

    @Provides @Singleton
    fun provideApiService(retrofit: Retrofit) = retrofit.create(ApiService::class.java)
}

// di/RepositoryModule.kt
@Module
@InstallIn(SingletonComponent::class)
object RepositoryModule {
    @Provides @Singleton
    fun provideAuthRepository(api: ApiService, tokenManager: TokenManager) = AuthRepository(api, tokenManager)

    @Provides @Singleton
    fun provideDeckRepository(api: ApiService) = DeckRepository(api)

    // ... other repositories
}
```

```kotlin
// MainActivity.kt
@AndroidEntryPoint
class MainActivity : ComponentActivity() { ... }
```

ViewModels use `@HiltViewModel` + `@Inject constructor`:
```kotlin
@HiltViewModel
class HomeViewModel @Inject constructor(
    private val deckRepository: DeckRepository,
) : ViewModel() { ... }
```

**Acceptance criteria**:
- `LaoshiApp` annotated with `@HiltAndroidApp`.
- `MainActivity` annotated with `@AndroidEntryPoint`.
- All ViewModels use `@HiltViewModel` with `@Inject constructor`.
- `NetworkModule` provides `TokenManager`, `OkHttpClient`, `Retrofit`, `ApiService` as singletons.
- `RepositoryModule` provides all repositories as singletons.
- Dependencies are properly scoped (no leaks).
- All existing unit tests still pass with Hilt test rules.

**Dependencies**: T-029, T-031.

---

### T-033: Create auth screens (Login + Register)

**Description**: Build login and register screens matching web validation rules.

**Files affected**:
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/ui/auth/LoginScreen.kt`
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/ui/auth/RegisterScreen.kt`
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/ui/auth/AuthViewModel.kt`

**Changes**:

Material 3 text fields with validation:
- Username: 3-80 chars
- Password: 8+ chars with uppercase, lowercase, digit
- Email: basic format validation

Login calls `POST /api/v1/token` with `client_id` + `client_secret` from `BuildConfig`.
Register calls `POST /api/v1/users` then auto-login with client credentials.

**Acceptance criteria**:
- Login screen with username/password fields, validation errors, loading state.
- Register screen with username/email/password fields, validation.
- Successful login stores tokens and navigates to home (or onboarding).
- Error states shown for invalid credentials.

**Dependencies**: T-032.

---

### T-034: Create navigation graph with bottom navigation

**Description**: Set up the navigation graph with auth flow, bottom navigation, and screen routing.

**Files affected**:
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/navigation/NavGraph.kt`
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/MainActivity.kt`

**Changes**:

Bottom nav tabs: Home, Library, Progress, Settings.
Auth flow: check token on launch -> Login or Home.
Onboarding check: if `!onboarding_complete` -> Onboarding -> Home.
Practice: full-screen (no bottom nav).

```kotlin
@Composable
fun NavGraph(navController: NavHostController, startDestination: String) {
    NavHost(navController, startDestination) {
        composable(Screen.Login.route) { LoginScreen(...) }
        composable(Screen.Register.route) { RegisterScreen(...) }
        composable(Screen.Onboarding.route) { OnboardingScreen(...) }
        composable(Screen.Home.route) { HomeScreen(...) }
        composable(Screen.DeckDetail.route) { DeckDetailScreen(...) }
        composable(Screen.Practice.route) { PracticeScreen(...) }
        composable(Screen.Library.route) { LibraryScreen(...) }
        composable(Screen.DeckWords.route) { DeckWordsScreen(...) }
        composable(Screen.Progress.route) { ProgressScreen(...) }
        composable(Screen.Settings.route) { SettingsScreen(...) }
    }
}
```

**Acceptance criteria**:
- Bottom navigation with 4 tabs.
- Auth flow routes correctly.
- Practice screen is full-screen (bottom nav hidden).
- Deep links work for deck detail.

**Dependencies**: T-033.

---

## Phase 2C: Android Screens

All main app screens.

---

### T-035: Create Home screen with deck list

**Description**: Deck list with growth icons, recency colors, progress bars, Laoshi message preview.

**Files affected**:
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/ui/home/HomeScreen.kt`
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/ui/home/DeckListView.kt`
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/ui/home/HomeViewModel.kt`

**Changes**:

Phone: single-pane deck list. Tap deck -> navigate to deck detail.
Tablet: two-pane master-detail (optional, stretch goal).

Each deck card shows:
- Growth icon (sprout/leaf/flower based on mastery %)
- Recency color (sage/amber/coral/neutral)
- Progress bar
- Word count (mastered/total)
- Laoshi message preview (truncated)
- Language badge

**Acceptance criteria**:
- Deck list loads from API.
- Growth icons and recency colors match web.
- Loading skeleton shown while fetching.
- Empty state shown when no decks.
- Pull-to-refresh supported.

**Dependencies**: T-031, T-034.

---

### T-036: Create Deck Detail screen

**Description**: Deck detail with progress ring, stats, Laoshi message, and "Start Practice" button.

**Files affected**:
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/ui/home/DeckDetailView.kt`
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/ui/components/ProgressRing.kt`

**Changes**:

Custom `ProgressRing` composable (see design doc section 8.3).
Stats row: total words, mastered count, mastery percentage.
Laoshi message in quote box.
"Start Practice" button -> starts session -> navigates to PracticeScreen.
"Manage in Library" link -> navigates to Library.

**Acceptance criteria**:
- Progress ring renders with correct fill percentage.
- Stats match API data.
- "Start Practice" calls `POST /api/practice/sessions` and navigates.
- Loading state during session creation.

**Dependencies**: T-035.

---

### T-037: Create Practice screen (most complex)

**Description**: Full chat interface with word pill, messages, feedback cards, confidence rating, and session management.

**Files affected**:
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/ui/home/PracticeScreen.kt`
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/ui/home/PracticeViewModel.kt`
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/ui/components/WordPill.kt`
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/ui/components/FeedbackCard.kt`
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/ui/components/ConfidenceRating.kt`

**Changes**:

1. `PracticeViewModel` with state machine (`PracticeStatus` enum).
2. `WordPill` -- collapsed/expanded, tappable, matches web FloatingWordPill.
3. Message list (`LazyColumn`) with user/AI bubbles.
4. `FeedbackCard` -- score badges with color coding.
5. `ConfidenceRating` -- 0-5 rating buttons, 3-tier color coding.
6. Text input with send button.
7. Session summary screen after completion.
8. End session dialog (back press).
9. State persistence via `SavedStateHandle`.

**Acceptance criteria**:
- Full practice flow works: start -> send message -> receive feedback -> rate -> next word -> complete.
- Word pill shows current word, tappable to expand.
- Feedback card scores match web styling (green/yellow/red).
- Confidence rating colors: 0-2 coral, 3 amber, 4-5 sage.
- Session survives process death via SavedStateHandle.
- Both ZH and JP sessions work.

**Dependencies**: T-031, T-034, T-036.

---

### T-038: Create Library screen

**Description**: Deck management with create, CSV import, and word CRUD.

**Files affected**:
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/ui/library/LibraryScreen.kt`
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/ui/library/DeckWordsScreen.kt`
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/ui/library/CreateDeckDialog.kt`
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/ui/library/LibraryViewModel.kt`

**Changes**:

1. Deck list with cards showing language badge, word count, mastery %.
2. Create deck dialog with name, description, language selector (ZH/JP).
3. CSV import via `ActivityResultContracts.GetContent` (MIME type `text/*`).
4. Deck words screen: paginated `LazyColumn` with search, sort options.
5. Edit/delete word via bottom sheet or dialog.
6. Column headers adapt to language.

**Acceptance criteria**:
- Create deck with language selection works.
- CSV import parses file and adds words.
- Word list paginated with search and sort.
- Edit/delete word works.
- "Furigana" header for JP decks, "Pinyin" for ZH.

**Dependencies**: T-031, T-034.

---

### T-039: Create Progress screen (Report Card)

**Description**: Report card with topline metrics, chart, scores, and teacher feedback.

**Files affected**:
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/ui/progress/ProgressScreen.kt`
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/ui/progress/ProgressViewModel.kt`

**Changes**:

1. Topline metrics row: time practiced, sessions, words.
2. 7-day stacked bar chart using Vico library (correct=green, incorrect=red).
3. Score breakdown cards: grammar, usage, naturalness (out of 10).
4. Teacher feedback section with Laoshi avatar and italic text.
5. Pull-to-refresh triggers `POST /api/progress/generate-feedback`.

**Acceptance criteria**:
- All report card data loads correctly.
- Chart renders 7 days of data.
- Score cards show descriptions.
- Teacher feedback displays.
- Pull-to-refresh works.
- Empty states handled.

**Dependencies**: T-031, T-034.

---

### T-040: Create Settings screen

**Description**: User settings with name, words per session, logout, and delete account.

**Files affected**:
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/ui/settings/SettingsScreen.kt`
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/ui/settings/SettingsViewModel.kt`

**Changes**:

1. Preferred name text field.
2. Words per session slider or stepper (5-50 range).
3. Save button.
4. Logout button -> clears tokens, navigates to login.
5. Delete account button -> confirmation dialog -> calls `DELETE /api/account`.
6. No BYOK (API key management intentionally omitted).

**Acceptance criteria**:
- Settings load from API on screen open.
- Name and words per session update via `PUT /api/settings`.
- Logout clears tokens and returns to login.
- Delete account works with confirmation.
- No API key fields visible.

**Dependencies**: T-031, T-034.

---

### T-041: Create Onboarding wizard

**Description**: 5-step onboarding wizard for first-time mobile users.

**Files affected**:
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/ui/onboarding/OnboardingScreen.kt`
- New: `mobile_android/app/src/main/java/com/laoshicoach/app/ui/onboarding/OnboardingViewModel.kt`

**Changes**:

HorizontalPager with 5 cards:
1. NameCard: "What should Laoshi call you?" with text input.
2. MeetLaoshiCard: Laoshi persona introduction.
3. DecksCard: Deck concept explanation.
4. PracticeCard: Practice flow explanation.
5. ReadyCard: "Get Started" button.

On completion: `PUT /api/settings` with `onboarding_complete=true`, navigate to home.

**Acceptance criteria**:
- 5-step wizard with swipe navigation.
- Step indicator dots.
- Name saved to settings on card 1 progression.
- "Get Started" sets `onboarding_complete=true`.
- After completion, navigates to home screen.
- Wizard only shows if `onboarding_complete` is false.

**Dependencies**: T-031, T-034.

---

## Phase 2D: Backend Mobile Auth Modifications

Backend changes needed for mobile auth. Can be done in parallel with Phase 2A.

---

### T-042: Implement OAuth2 client credentials in TokenResource

**Description**: Validate `client_id` (and `client_secret` for confidential clients) in the login endpoint. Return `refresh_token` in response body only for mobile clients.

**Files affected**:
- `backend/resources.py` -- `TokenResource.post`

**Changes**:

```python
from config import OAUTH_CLIENTS

# Validate client credentials
client_id = data.get('client_id')
client_secret = data.get('client_secret')
if not client_id or client_id not in OAUTH_CLIENTS:
    return {'error': 'Invalid client_id'}, 400
client = OAUTH_CLIENTS[client_id]
if client['secret_required'] and client_secret != client['secret']:
    return {'error': 'Invalid client credentials'}, 401

# ... existing user auth logic ...

response_data = {'access_token': access_token}
if client['type'] == 'mobile':
    response_data['refresh_token'] = refresh_token

resp = make_response(jsonify(response_data))
set_refresh_cookies(resp, refresh_token)
return resp
```

**Acceptance criteria**:
- Web login (`client_id=laoshi-web`, no secret): `access_token` in body, refresh in cookie only.
- Mobile login (`client_id=laoshi-android` + valid `client_secret`): both tokens in body.
- Missing `client_id`: returns 400.
- Invalid `client_secret` for mobile: returns 401.
- Web auth flow unchanged (cookie-based refresh continues working).

**Dependencies**: None.

---

### T-043: Implement manual refresh token extraction for mobile

**Description**: Allow `TokenRefreshResource` to accept refresh token from JSON body (for mobile clients) via manual `decode_token()`. Do NOT add `'json'` to `JWT_TOKEN_LOCATION`.

**Files affected**:
- `backend/resources.py` -- `TokenRefreshResource.post`

**Changes**:

```python
from flask_jwt_extended import decode_token, create_access_token

def post(self):
    # Try mobile path: refresh token in JSON body
    data = request.get_json(silent=True) or {}
    body_refresh_token = data.get('refresh_token')

    if body_refresh_token:
        try:
            decoded = decode_token(body_refresh_token)
            user_id = decoded['sub']
            if decoded.get('type') != 'refresh':
                return {'error': 'Invalid token type'}, 401
        except Exception:
            return {'error': 'Invalid or expired refresh token'}, 401

        new_access_token = create_access_token(identity=user_id)
        return {'access_token': new_access_token}, 200
    else:
        # Web path: existing @jwt_required(refresh=True) logic
        ...
```

**Important**: `JWT_TOKEN_LOCATION` remains `['headers', 'cookies']`. The refresh token is manually extracted and verified using `decode_token()` -- this avoids broadening the global token search to JSON bodies on all endpoints.

**Acceptance criteria**:
- `POST /api/token/refresh` with `{"refresh_token": "..."}` in body returns new access token.
- `POST /api/token/refresh` with cookie-based token still works (web).
- `JWT_TOKEN_LOCATION` is NOT modified (still `['headers', 'cookies']`).
- Invalid/expired refresh tokens return 401.
- Both flows tested.

**Dependencies**: T-014.

---

### T-044: Test mobile auth flow end-to-end

**Description**: Integration test for the full OAuth2 client credentials auth lifecycle.

**Files affected**:
- New or updated: `backend/tests/test_mobile_auth.py`

**Changes**:

Test cases:
1. Login with `client_id=laoshi-android` + valid `client_secret` -> response includes `refresh_token` in body.
2. Login with `client_id=laoshi-web` (no secret) -> response does NOT include `refresh_token` in body.
3. Login without `client_id` -> returns 400.
4. Login with `client_id=laoshi-android` + wrong `client_secret` -> returns 401.
5. Login with invalid `client_id` -> returns 400.
6. Refresh with JSON body `{"refresh_token": "..."}` -> returns new access token.
7. Refresh with cookie (web flow) -> still works.
8. Refresh with expired token -> returns 401.
9. Access protected endpoint with header-based token -> works.
10. Rate limiting: 11th login attempt in 1 minute -> returns 429.

**Acceptance criteria**:
- All 10 test cases pass.
- Web auth flow unaffected.
- Rate limiting enforced.

**Dependencies**: T-042, T-043.

---

## Integration + Verification

---

### T-045: Android build verification

**Description**: Ensure the Android project builds and runs on emulator.

**Steps**:
1. `./gradlew assembleDebug` from `mobile_android/`.
2. Install on emulator (API 26+).
3. Verify app launches, shows login screen.

**Acceptance criteria**:
- Debug APK builds successfully.
- App installs and launches on emulator.
- No crash on startup.

**Dependencies**: All Phase 2 tasks.

---

### T-046: Android E2E test -- registration and onboarding

**Description**: Manual end-to-end test of mobile registration and onboarding.

**Test plan**:
1. Launch app -> login screen shown.
2. Tap "Register" -> register screen shown.
3. Enter valid credentials -> account created, auto-login.
4. Onboarding wizard appears (5 steps).
5. Complete onboarding -> home screen shown.
6. Sample decks visible (at least ZH).

**Dependencies**: T-045.

---

### T-047: Android E2E test -- practice session

**Description**: Manual end-to-end test of mobile practice flow.

**Test plan**:
1. Select a deck -> deck detail shown.
2. Tap "Start Practice" -> practice screen opens.
3. Type sentence, submit -> AI response + feedback card.
4. Tap "Next Word" -> confidence rating appears.
5. Select rating -> next word loads.
6. Complete all words -> session summary shown.
7. Tap "Back to Home" -> returns to home.

**Dependencies**: T-045.

---

### T-048: Android E2E test -- JP deck practice

**Description**: Manual end-to-end test of Japanese deck creation and practice on mobile.

**Test plan**:
1. Go to Library -> create new deck with language "JP".
2. Add words with furigana readings.
3. Return to Home -> tap JP deck -> start practice.
4. Verify AI feedback uses Japanese context.
5. Complete session -> verify summary.

**Dependencies**: T-045, T-026 (Phase 1 complete).

---

## Dependency Graph

```
Phase 1A (Database + Models):
  T-001 (migration)
    -> T-002 (Deck.language)     ──┐
    -> T-003 (Word.reading)      ──┤
                                   │
Phase 1B (AI Layer):               │
  T-004 (context dataclasses)    ──┤── no DB dep (parallel with T-001)
    -> T-005 (LANGUAGE_CONFIG)   ──┤── depends on T-004
  T-006 (Claude/LiteLLM)        ──┤── no dep (parallel)
    -> T-007 (model routing)     ──┤── depends on T-005, T-006
      -> T-008 (practice runner) ──┤── depends on T-003, T-004, T-007
                                   │
Phase 1C (API Endpoints):          │
  T-009 (deck_resources)         ──┤── depends on T-002, T-003
  T-010 (resources)              ──┤── depends on T-003
  T-011 (practice_resources)     ──┤── depends on T-003, T-008
  T-012 (report_card_service)    ──┤── depends on T-004, T-005
  T-013 (sample_deck_service)    ──┤── depends on T-002, T-003
  T-014 (config.py)              ──┤── no dep (parallel)
                                   │
Phase 1D (Web Frontend):          │
  T-015 (types)                  ──┤── no dep (parallel)
  T-016 (api client)             ──┤── depends on T-015
  T-017 (CreateDeckModal)        ──┤── depends on T-016
  T-018 (DeckWordsView)          ──┤── depends on T-015, T-016
  T-019 (FloatingWordPill)       ──┤── depends on T-015
  T-020 (PracticePanel)          ──┤── depends on T-015
  T-020b (web login client_id)   ──┤── depends on T-010
  T-021 (FeedbackCard)           ──┤── depends on T-015
                                   │
Phase 1E (Tests + Docs):          │
  T-022 (backend test fixtures)  ──┤── depends on T-002, T-003
  T-023 (test_multilanguage)     ──┤── depends on T-009, T-010
  T-024 (frontend tests)         ──┤── depends on T-015-T-020
  T-025 (docs)                   ──┤── depends on all Phase 1
  T-025b (API versioning)        ──┤── no dep (parallel, early)
  T-026 (build verification)     ──┘── depends on all Phase 1

Phase 2A (Android Setup, can start after Phase 1C):
  T-027 (project structure+Hilt) ──┐
    -> T-028 (theme)             ──┤
    -> T-029 (networking+creds)  ──┤── depends on T-010 (OAuth2 client creds)
    -> T-030 (DTOs)              ──┤── depends on T-015 (type reference)
      -> T-031 (repositories)    ──┤── depends on T-029, T-030
        -> T-031b (repo caching) ──┤── depends on T-031
                                   │
Phase 2B (Auth + Navigation):     │
  T-032 (LaoshiApp Hilt DI)     ──┤── depends on T-029, T-031
    -> T-033 (auth screens)      ──┤── depends on T-032
      -> T-034 (navigation)      ──┤── depends on T-033
                                   │
Phase 2C (Screens):                │
  T-035 (home screen)            ──┤── depends on T-031, T-034
  T-036 (deck detail)            ──┤── depends on T-035
  T-037 (practice screen)        ──┤── depends on T-031, T-034, T-036
  T-038 (library screen)         ──┤── depends on T-031, T-034
  T-039 (progress screen)        ──┤── depends on T-031, T-034
  T-040 (settings screen)        ──┤── depends on T-031, T-034
  T-041 (onboarding wizard)      ──┤── depends on T-031, T-034
                                   │
Phase 2D (Backend OAuth2 Client Credentials, parallel with 2A):
  T-042 (OAuth2 client creds)    ──┤── depends on T-014
  T-043 (manual refresh extract) ──┤── depends on T-014
  T-044 (mobile auth tests)      ──┤── depends on T-042, T-043
                                   │
Integration:                       │
  T-045 (Android build)           ──┤── depends on all Phase 2
  T-046 (E2E registration)        ──┤── depends on T-045
  T-047 (E2E practice)            ──┤── depends on T-045
  T-048 (E2E JP deck)             ──┘── depends on T-045, T-026
```

---

## Definition of Done

The milestone is complete when:

1. **Backend**: All existing tests pass with `reading` rename and `language` field.
2. **Backend**: New `test_multilanguage.py` and `test_mobile_auth.py` tests pass (including OAuth2 client credentials, rate limiting).
3. **Backend**: `flask db upgrade` succeeds without errors.
4. **Backend**: `/api/v1/` aliasing works (Nginx rewrite + Flask dev fallback).
5. **Backend**: OAuth2 client credentials flow works for both web (`laoshi-web`) and mobile (`laoshi-android`).
6. **Web Frontend**: `npm run build` succeeds with zero TypeScript errors.
7. **Web Frontend**: All existing frontend tests pass with updated field names.
8. **Web Frontend**: Login includes `client_id: 'laoshi-web'` in request body.
9. **Web Frontend**: ZH deck creation and practice works identically to before (regression check).
10. **Web Frontend**: JP deck creation shows "Furigana" column header and language badge.
11. **Android**: Debug APK builds and installs on API 26+ emulator.
12. **Android**: Hilt DI properly wired (all ViewModels use `@HiltViewModel`).
13. **Android**: Full registration -> onboarding -> practice flow works with client credentials.
14. **Android**: ZH and JP deck creation and practice works.
15. **Android**: Report card displays correctly.
16. **Android**: Settings (name, words per session, logout, delete account) work.
17. **Android**: Repository caching reduces redundant API calls (verified via network logging).
18. **Architecture docs**: Updated with new env vars, schema changes, agent routing, and OAuth2 client config.
