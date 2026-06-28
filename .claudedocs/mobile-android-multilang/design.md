# Mobile Android + Multi-Language Support -- Design Document

> **Source of truth for architecture**: `.claude/architecture.md`
> **Plan file**: `C:\Users\Jasmine\.claude\plans\lazy-purring-sparrow.md`
> This document describes technical design decisions, component architecture, and data flow for the multi-language backend and Android mobile app.

---

## 1. Architecture Overview

### 1.1 Phase 1: Multi-Language Backend

**Core changes:**
- `Deck` model gains a `language` column (`String(2)`, NOT NULL, default `'ZH'`).
- `Word.pinyin` column renamed to `Word.reading` for language generality.
- AI prompts become dynamic via a `LANGUAGE_CONFIG` dictionary keyed by language code.
- Model routing: feedback agent uses DeepSeek for ZH, Claude 3.5 Sonnet (via LiteLLM) for JP.
- Sample deck service refactored to support per-language CSV files via env vars.

**No new tables.** Only column additions/renames on existing tables.

### 1.2 Phase 2: Android Mobile App

**Core addition:**
- Native Android app at `mobile_android/` (peer to `frontend/` and `backend/`).
- Kotlin + Jetpack Compose, Material 3, sharing the same backend API.
- Mobile auth flow with JWT tokens in JSON body (not cookies).
- All screens mirror web functionality with mobile-native UX patterns.

```
Architecture (post-milestone):

  [React Web Frontend]  ----\
                              \     [Nginx Gateway]     [Flask Backend]     [PostgreSQL]
  [Android Mobile App]  ------/---->  /api/*  -------->  REST API  -------->  DB
                                                            |
                                                     [AI Layer]
                                                     /    |    \
                                              DeepSeek  Gemini  Claude
                                              (ZH FB)  (Orch)  (JP FB)
```

---

## 2. Database Schema Changes

### 2.1 Migration: Add `language` to `deck`, rename `pinyin` to `reading` on `word`

**Alembic migration operations:**

```python
# 1. Add language column to deck table
op.add_column('deck', sa.Column('language', sa.String(2), nullable=False, server_default='ZH'))

# 2. Rename word.pinyin to word.reading
op.alter_column('word', 'pinyin', new_column_name='reading')
```

**Rollback:**
```python
op.alter_column('word', 'reading', new_column_name='pinyin')
op.drop_column('deck', 'language')
```

### 2.2 Model Changes

**`backend/models.py` -- Deck:**
```python
class Deck(db.Model):
    # ... existing fields ...
    language = db.Column(db.String(2), nullable=False, default='ZH', server_default='ZH')

    SUPPORTED_LANGUAGES = ('ZH', 'JP')

    def format_data(self, viewer=None):
        # ... existing logic ...
        return {
            # ... existing fields ...
            'language': self.language,
        }
```

**`backend/models.py` -- Word:**
```python
class Word(db.Model):
    # ... existing fields ...
    reading = db.Column(db.String(150), nullable=False)  # Was: pinyin

    def __repr__(self):
        return f"{self.id} - {self.word} - {self.reading} - {self.meaning}"

    def format_data(self, viewer=None):
        # ... existing logic ...
        return {
            # ... existing fields ...
            'reading': self.reading,  # Was: 'pinyin': self.pinyin
        }
```

---

## 3. AI Layer Architecture

### 3.1 Language Configuration Dictionary

**`backend/ai_layer/chat_agents.py`:**

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

### 3.2 Context Dataclass Updates

**`backend/ai_layer/context.py`:**

```python
@dataclass
class WordContext:
    word_id: int
    word: str
    reading: str      # Was: pinyin
    meaning: str
    language: str     # New: 'ZH' or 'JP'

@dataclass
class UserSessionContext:
    # ... existing fields ...
    language: str     # New: 'ZH' or 'JP'

@dataclass
class ReportCardContext:
    # ... existing fields ...
    language: str     # New: 'ZH' or 'JP'
```

### 3.3 Dynamic Prompt Updates

All four prompt builders use `ctx.language` to look up `LANGUAGE_CONFIG`:

- **`build_feedback_prompt`**: Replaces hardcoded "Mandarin Chinese" with `lang['name']`, `word.pinyin` with `word.reading`, grammar criteria with `lang['feedback_focus']`, feedback language with `lang['feedback_language']`.
- **`build_orchestrator_prompt`**: Replaces "Mandarin Chinese teacher" with `lang['name']` teacher. Keeps "Laoshi" persona. Uses `word.reading`.
- **`build_summary_prompt`**: Replaces "Mandarin practice session" and `wc.pinyin` with `wc.reading`.
- **`build_report_card_prompt`**: Replaces "Mandarin Chinese teacher" with language-aware version.

### 3.4 Model Routing

**`build_agents()` updated to accept `language` parameter:**

```python
# New env vars
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL_NAME = os.getenv("ANTHROPIC_MODEL_NAME", "claude-3-5-sonnet-20241022")

# Claude client via direct LiteLLM (no proxy -- litellm already a dependency via mem0)
claude_model = None
if ANTHROPIC_API_KEY:
    try:
        import litellm
        # Use litellm's OpenAI-compatible wrapper for Anthropic models
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
        logger.warning(f"Failed to initialize Claude model: {e}")
else:
    logger.warning("ANTHROPIC_API_KEY not set. JP feedback unavailable.")

# Module-level cached JP agents (parallel to ZH singletons)
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

def build_agents(deepseek_api_key=None, gemini_api_key=None, language='ZH'):
    """Build agents with language-specific model routing."""
    # Return cached singletons when no custom keys
    if not deepseek_api_key and not gemini_api_key:
        if language == 'JP' and jp_laoshi_agent:
            return jp_laoshi_agent, jp_summary_agent  # Cached JP agents
        return laoshi_agent, summary_agent             # Cached ZH agents

    # Build custom agents only when BYOK keys provided
    # ... (same logic as before, but picks feedback model by language) ...
```

**Routing table:**

| Agent | ZH Model | JP Model |
|-------|----------|----------|
| Feedback | DeepSeek | Claude 3.5 Sonnet (via LiteLLM) |
| Orchestrator | Gemini Flash | Gemini Flash |
| Summary | Gemini Flash | Gemini Flash |
| Report Card | Gemini Flash | Gemini Flash |

### 3.5 Practice Runner Threading

**`backend/ai_layer/practice_runner.py`** -- all functions receive `language` from `session.deck.language`:

- `hydrate_context()`: Uses `word.reading` instead of `word.pinyin`. Looks up `session.deck.language` and passes to `UserSessionContext`.
- `get_user_agent()`: Accepts `language` param, passes to `build_agents()`.
- `initialize_session()`: Threads `language` through context and agent construction.
- `handle_message()`: Passes deck language to `get_user_agent()`.
- `advance_word()`: Uses `reading` in next-word introduction and API response.
- `complete_session()`: Passes `language` to `get_user_agent()`.

---

## 4. API Endpoint Changes

### 4.1 Deck Endpoints

**`POST /api/decks`** -- accepts optional `language` field:
```json
{ "name": "JLPT N5 Vocab", "description": "...", "language": "JP" }
```
- Default: `'ZH'`
- Validated against `Deck.SUPPORTED_LANGUAGES`

**`POST /api/decks/combine`** -- validates all source decks share the same language:
```json
{ "name": "Combined", "source_deck_ids": [1, 2, 3] }
```
- Returns 400 if source decks have different languages.
- New deck inherits language from source decks.

**`GET /api/decks`** -- response now includes `language` on each deck. Accepts optional `?language=JP` query parameter to filter by language.

### 4.2 Word Endpoints

All word endpoints use `reading` instead of `pinyin`:

**`POST /api/decks/<id>/words`** -- accepts `reading` field (falls back to `pinyin` for backward compat):
```json
{ "words": [{ "word": "...", "reading": "...", "meaning": "..." }] }
```

**`GET /api/decks/<id>/words`** -- sorts/searches on `Word.reading`.

**`PUT /api/words/<id>`** -- accepts `reading` field (falls back to `pinyin`).

### 4.3 Practice Endpoints

**`POST /api/practice/sessions`** -- unchanged request format, but response uses `reading`:
```json
{
  "current_word": {
    "word_id": 1,
    "word": "...",
    "reading": "...",
    "meaning": "..."
  }
}
```

### 4.4 Auth Endpoints (OAuth2 Client Credentials)

Both web and mobile clients identify themselves via `client_id` in the login request. Mobile clients also send `client_secret` (confidential client). This replaces the previously planned `X-Client-Type` header approach.

**`POST /api/token`** -- client-aware login:
- Request body includes `client_id` (required) and `client_secret` (required for mobile).
- Backend validates client credentials against `OAUTH_CLIENTS` config.
- Response varies by client type:
  - **Web** (`laoshi-web`, public client): `access_token` in body, `refresh_token` in HttpOnly cookie only.
  - **Mobile** (`laoshi-android`, confidential client): both `access_token` and `refresh_token` in response body.

**`POST /api/token/refresh`** -- dual-path refresh:
- **Web path**: Flask-JWT-Extended handles cookie-based refresh automatically (no change).
- **Mobile path**: Accepts `{"refresh_token": "..."}` in request body. The endpoint manually decodes and verifies the refresh token using `flask_jwt_extended.decode_token()` -- this avoids adding `'json'` to `JWT_TOKEN_LOCATION` globally.
- `JWT_TOKEN_LOCATION` remains `['headers', 'cookies']` (unchanged).

**Rate limiting** (Flask-Limiter):
- `POST /api/token`: 10/minute per IP.
- `POST /api/token/refresh`: 30/minute per IP.
- `POST /api/users`: 5/minute per IP.

---

## 5. Sample Deck Service Refactor

**`backend/sample_deck_service.py`:**

```python
# Per-language configuration
SAMPLE_DECK_CONFIG = {
    'ZH': {
        'env_var': 'ZH_SAMPLE_DECK_FILE',
        'default_file': 'swe_vocab_list.csv',
        'name': 'Software Engineering Vocabulary',
        'description': 'Common Mandarin vocabulary used in software engineering contexts.',
        'laoshi_message': 'This is a sample deck to help you get started with Laoshi!',
    },
    'JP': {
        'env_var': 'JP_SAMPLE_DECK_FILE',
        'default_file': 'jp_sample_vocab_list.csv',
        'name': 'Japanese Starter Vocabulary',
        'description': 'Common Japanese vocabulary to get you started.',
        'laoshi_message': 'This is a sample Japanese deck. Practice forming sentences!',
    },
}

def seed_sample_deck_for_user(user_id, language='ZH'):
    """Seed a sample deck for the given language. Gracefully skips if CSV missing."""
    config = SAMPLE_DECK_CONFIG[language]
    csv_filename = os.getenv(config['env_var'], config['default_file'])
    # ... load CSV, create deck with language=language, use 'reading' column ...
```

CSV parsing accepts both `Pinyin` and `Reading` headers:
```python
reading = row.get('Reading', '') or row.get('Pinyin', '')
```

On registration: seed both ZH and JP (skip JP if file missing).

---

## 6. Web Frontend Changes

### 6.1 Type Updates

**`frontend/src/types/api.ts`:**
```typescript
export interface Word {
  // ... existing fields ...
  reading: string     // Was: pinyin
}

export interface WordContext {
  word_id: number
  word: string
  reading: string    // Was: pinyin
  meaning: string
}

export interface Deck {
  // ... existing fields ...
  language: 'ZH' | 'JP'
}
```

### 6.2 API Client Updates

**`frontend/src/lib/api.ts`:**
```typescript
export const deckApi = {
  createDeck: (data: { name: string; description?: string; language?: 'ZH' | 'JP' }) =>
    api.post<DeckWithStats>('/api/decks', data),

  addWordsToDeck: (id: number, words: { word: string; reading: string; meaning: string; notes?: string }[]) =>
    api.post<{ created: Word[] }>(`/api/decks/${id}/words`, { words }),
  // ...
}
```

### 6.3 Component Updates

**Library -- `CreateDeckModal`**: Add ZH/JP language selector (radio buttons, default ZH).

**Library -- `DeckWordsView.tsx`**: Dynamic table header based on `deck.language`:
```tsx
const readingLabel = deck.language === 'JP' ? 'Furigana' : 'Pinyin'
```

**Home -- `FloatingWordPill.tsx`**: `word.pinyin` -> `word.reading`.

**Home -- `PracticePanel.tsx`**: All `pinyin` references -> `reading`.

---

## 7. Android App Architecture

### 7.1 Project Structure

```
mobile_android/
  app/
    build.gradle.kts
    src/main/
      AndroidManifest.xml
      java/com/laoshicoach/app/
        LaoshiApp.kt                    # @HiltAndroidApp Application class
        MainActivity.kt                 # @AndroidEntryPoint Single Activity host
        navigation/
          NavGraph.kt                   # Navigation graph definition
        di/
          NetworkModule.kt             # @Module: OkHttp, Retrofit, ApiService
          RepositoryModule.kt          # @Module: Repository bindings
          StorageModule.kt             # @Module: TokenManager, DataStore
        data/
          api/
            ApiService.kt              # Retrofit interface
            AuthInterceptor.kt         # JWT token interceptor
            TokenRefreshAuthenticator.kt # 401 refresh handler (Mutex-based)
          model/
            Deck.kt, Word.kt, etc.     # Kotlin DTOs
          repository/
            AuthRepository.kt
            DeckRepository.kt
            PracticeRepository.kt
            ProgressRepository.kt
            SettingsRepository.kt
          local/
            TokenManager.kt            # EncryptedSharedPreferences
            PreferencesManager.kt       # DataStore preferences
        ui/
          theme/
            Color.kt                   # Material 3 color scheme
            Type.kt                    # Typography definitions
            Theme.kt                   # LaoshiTheme composable
          components/                   # Shared composables
            LaoshiCard.kt
            ScoreBadge.kt
            ProgressRing.kt
            WordPill.kt
            FeedbackCard.kt
            ConfidenceRating.kt
            SkeletonLoading.kt
          auth/
            LoginScreen.kt
            RegisterScreen.kt
            AuthViewModel.kt
          onboarding/
            OnboardingScreen.kt
            OnboardingViewModel.kt
          home/
            HomeScreen.kt
            DeckListView.kt
            DeckDetailView.kt
            PracticeScreen.kt
            HomeViewModel.kt
            PracticeViewModel.kt
          library/
            LibraryScreen.kt
            DeckWordsScreen.kt
            CreateDeckDialog.kt
            LibraryViewModel.kt
          progress/
            ProgressScreen.kt
            ProgressViewModel.kt
          settings/
            SettingsScreen.kt
            SettingsViewModel.kt
        util/
          DateFormatter.kt
          Extensions.kt
      res/
        values/strings.xml
        values/themes.xml
  build.gradle.kts (project-level)
  settings.gradle.kts
  gradle.properties
```

### 7.2 Key Dependencies

```kotlin
// build.gradle.kts (app)
dependencies {
    // Compose
    implementation(platform("androidx.compose:compose-bom:2024.10.00"))
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.activity:activity-compose:1.9.0")

    // Navigation
    implementation("androidx.navigation:navigation-compose:2.7.7")

    // Networking
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-gson:2.11.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")

    // Hilt (DI)
    implementation("com.google.dagger:hilt-android:2.51.1")
    kapt("com.google.dagger:hilt-android-compiler:2.51.1")
    implementation("androidx.hilt:hilt-navigation-compose:1.2.0")

    // Security
    implementation("androidx.security:security-crypto:1.1.0-alpha06")

    // Charts
    implementation("com.patrykandpatrick.vico:compose-m3:1.13.1")

    // CSV parsing
    implementation("org.apache.commons:commons-csv:1.11.0")

    // DataStore
    implementation("androidx.datastore:datastore-preferences:1.1.1")

    // Lifecycle
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.0")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.0")
}
```

---

## 8. Android Design System

The mobile app mirrors the web app's visual identity exactly. All values are extracted from `tailwind.config.js`, `index.css`, and component source files.

### 8.1 Color Palette

**`ui/theme/Color.kt`:**

```kotlin
// Semantic colors (from tailwind.config.js)
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

**Material 3 color scheme mapping:**

| Semantic Name | Hex | Material 3 Role | Usage |
|---------------|-----|-----------------|-------|
| Sage | `#6B8F71` | Primary | Primary buttons, active states, mastered count, progress ring fill, links |
| Sage Tint | `#EDF2EE` | PrimaryContainer | Active sidebar bg, example sentences bg, selected deck bg |
| Coral | `#D4715E` | Error | Error states, "needs improvement", overdue decks (>5 days), ratings 0-2 |
| Coral Tint | `#FDF0ED` | ErrorContainer | Coral tinted backgrounds |
| Amber | `#C4973B` | Tertiary | Warning states, mid-recency (2-5 days), rating 3 |
| Amber Tint | `#FBF5E8` | TertiaryContainer | Amber tinted backgrounds |
| Neutral | `#A8A5A0` | Outline/Disabled | Never-practiced decks, inactive icons |
| Neutral Tint | `#F2F1EF` | OutlineVariant | Neutral tinted backgrounds |
| Warm Offwhite | `#FAFAF8` | Surface/Background | App background, note cards bg |
| Warm Black | `#2A2A28` | OnSurface | Primary text, headings |
| Warm Gray | `#E8E5E0` | SurfaceVariant/Outline | Borders, dividers, skeleton loading, progress track |
| Warm Muted | `#8A8A86` | OnSurfaceVariant | Secondary text, timestamps, labels, "Never practiced" |
| Chat BG | `#F5F3EE` | SurfaceContainerLow | Practice chat panel background |
| White | `#FFFFFF` | SurfaceContainerHighest | Cards, message bubbles, feedback cards |

### 8.2 Typography

**`ui/theme/Type.kt`:**

| Role | Font Family | Android Font | Usage |
|------|-------------|-------------|-------|
| Sans-serif (UI) | Inter | Google Sans or Inter (Google Fonts) | All UI text, labels, buttons, body text |
| Serif (CJK) | Lora | Noto Serif or Lora (with CJK glyph support) | Chinese/Japanese characters in word display, word pill |

```kotlin
val LaoshiTypography = Typography(
    displayLarge = TextStyle(fontFamily = InterFontFamily, fontWeight = FontWeight.Bold, fontSize = 30.sp),
    headlineMedium = TextStyle(fontFamily = InterFontFamily, fontWeight = FontWeight.Medium, fontSize = 24.sp),
    titleLarge = TextStyle(fontFamily = InterFontFamily, fontWeight = FontWeight.Medium, fontSize = 20.sp),
    bodyLarge = TextStyle(fontFamily = InterFontFamily, fontSize = 16.sp),
    bodyMedium = TextStyle(fontFamily = InterFontFamily, fontSize = 15.sp),
    bodySmall = TextStyle(fontFamily = InterFontFamily, fontSize = 14.sp),
    labelLarge = TextStyle(fontFamily = InterFontFamily, fontWeight = FontWeight.Medium, fontSize = 14.sp),
    labelSmall = TextStyle(fontFamily = InterFontFamily, fontSize = 11.sp),
)

// CJK word display
val CjkWordStyle = TextStyle(fontFamily = SerifFontFamily, fontWeight = FontWeight.Medium)
```

### 8.3 Component Patterns

**Cards:**
- Background: White (`#FFFFFF`)
- Border: `1px solid warm-gray/60` (subtle, ~60% opacity of `#E8E5E0`)
- Border radius: `12.dp` for large cards (rounded-xl), `16.dp` for hero cards (rounded-2xl), `24.dp` for deck detail card (rounded-3xl)
- Shadow: `sm` (minimal, soft) -- `elevation = 1.dp`
- Padding: `16.dp` standard, `24.dp` for detail panels, `48.dp` for hero panels

**Buttons:**
- Primary: sage bg, white text, hover: sage/90, border radius `12.dp` (rounded-xl)
- Disabled: warm-gray bg, cursor-not-allowed
- Text/Link: sage text, hover: sage/80
- Padding: `px=32.dp, py=16.dp` (large), `px=16.dp, py=8.dp` (standard)

**Score Badges (FeedbackCard):**
- High (8-10): `bg-green-100 text-green-800 border-green-200`
- Medium (5-7): `bg-yellow-100 text-yellow-800 border-yellow-200`
- Low (1-4): `bg-red-100 text-red-800 border-red-200`
- Border radius: `8.dp` (rounded-lg)

```kotlin
@Composable
fun ScoreBadge(score: Int) {
    val (bgColor, textColor, borderColor) = when {
        score >= 8 -> Triple(Color(0xFFDCFCE7), Color(0xFF166534), Color(0xFFBBF7D0))
        score >= 5 -> Triple(Color(0xFFFEF9C3), Color(0xFF854D0E), Color(0xFFFDE68A))
        else -> Triple(Color(0xFFFEE2E2), Color(0xFF991B1B), Color(0xFFFECACA))
    }
    // ...
}
```

**Confidence Rating Colors:**
- 0-2 (Blackout/Very Hard/Hard): `bg-coral/15 text-coral` -> `Coral.copy(alpha = 0.15f)`, text `Coral`
- 3 (OK): `bg-amber/15 text-amber` -> `Amber.copy(alpha = 0.15f)`, text `Amber`
- 4-5 (Good/Mastered): `bg-sage/15 text-sage` -> `Sage.copy(alpha = 0.15f)`, text `Sage`

**Deck Recency Colors (circle avatars):**
- Practiced <48h ago: Sage (`#6B8F71`)
- Practiced 48-120h ago: Amber (`#C4973B`)
- Practiced >120h ago: Coral (`#D4715E`)
- Never practiced: Neutral (`#A8A5A0`)

```kotlin
fun deckRecencyColor(lastPracticedAt: Instant?): Color {
    if (lastPracticedAt == null) return Neutral
    val hoursAgo = Duration.between(lastPracticedAt, Instant.now()).toHours()
    return when {
        hoursAgo < 48 -> Sage
        hoursAgo < 120 -> Amber
        else -> Coral
    }
}
```

**Growth Icons (Lucide equivalents for Android):**
- <25% mastery: Sprout icon (Material: `Spa` or custom drawable)
- 25-74% mastery: Leaf icon (Material: `Eco` or `Park`)
- 75%+ mastery: Flower icon (Material: `LocalFlorist` or `FilterVintage`)

**Progress Ring:**
- Track color: warm-gray (`#E8E5E0`)
- Fill color: sage (`#6B8F71`)
- Stroke width: `10.dp` on `160.dp` diameter
- Center text: percentage in bold + "mastered" label

```kotlin
@Composable
fun ProgressRing(masteryPercentage: Float) {
    val sweepAngle = 360f * masteryPercentage / 100f
    Box(modifier = Modifier.size(160.dp)) {
        Canvas(modifier = Modifier.fillMaxSize()) {
            // Track
            drawArc(color = WarmGray, startAngle = -90f, sweepAngle = 360f,
                    useCenter = false, style = Stroke(width = 10.dp.toPx(), cap = StrokeCap.Round))
            // Fill
            drawArc(color = Sage, startAngle = -90f, sweepAngle = sweepAngle,
                    useCenter = false, style = Stroke(width = 10.dp.toPx(), cap = StrokeCap.Round))
        }
        Column(modifier = Modifier.align(Alignment.Center), horizontalAlignment = Alignment.CenterHorizontally) {
            Text("${masteryPercentage.toInt()}%", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
            Text("mastered", style = MaterialTheme.typography.labelSmall, color = WarmMuted)
        }
    }
}
```

**Word Pill (FloatingWordPill):**
- Collapsed: `rounded-full`, white bg, `border-warm-gray/60`, `px=20.dp, py=8.dp`
  - Word in serif font, `text-xl font-medium text-warm-black` -> `fontSize = 20.sp, fontFamily = SerifFontFamily`
  - Reading in `text-sm text-warm-black/40` -> `fontSize = 14.sp, color = WarmBlack.copy(alpha = 0.4f)`
  - Meaning in `text-sm text-warm-black/50 truncate` -> `fontSize = 14.sp, color = WarmBlack.copy(alpha = 0.5f), maxLines = 1, overflow = TextOverflow.Ellipsis`
- Expanded: `rounded-2xl`, white bg, `p=24.dp`
  - Word in `text-5xl font-serif text-warm-black` -> `fontSize = 48.sp, fontFamily = SerifFontFamily`
  - Reading in `text-sm font-medium text-sage` -> `fontSize = 14.sp, fontWeight = FontWeight.Medium, color = Sage`
  - Meaning in `text-base text-warm-black/80` -> `fontSize = 16.sp, color = WarmBlack.copy(alpha = 0.8f)`
  - Notes in `bg-warm-offwhite rounded-lg p=12.dp`

**Message Bubbles:**
- AI messages: white bg, `border-warm-gray/40`, `shadow-sm`, `rounded-2xl` with `rounded-tl-sm` (4.dp top-left)
- User messages: sage bg, white text, `rounded-2xl` with `rounded-tr-sm` (4.dp top-right)
- Text: `fontSize = 15.sp, color = WarmBlack, lineHeight = 22.sp`
- Timestamps: `fontSize = 10.sp, color = WarmBlack.copy(alpha = 0.3f)`

### 8.4 Spacing Scale

`4.dp, 8.dp, 12.dp, 16.dp, 24.dp, 32.dp, 48.dp`

### 8.5 Animations

Compose equivalents for Framer Motion on web:
- `AnimatedVisibility` for enter/exit transitions
- `animateContentSize()` for expanding/collapsing elements
- Slide transitions: `250ms` ease-out (word pill slide), `280ms` custom bezier for layout
- Fade-in-up: `300ms` ease-out (general content appearance)
- Scale pulse: `2s` ease-in-out infinite (loading ritual)

### 8.6 Loading States

- Skeleton: `WarmGray` rounded blocks with `shimmer` modifier
- Spinner: White `CircularProgressIndicator` on sage button background

### 8.7 Empty States

- Centered text in `WarmMuted` color
- Action link in `Sage` color, `fontWeight = FontWeight.Medium`

---

## 9. Android Networking Layer

### 9.1 Retrofit API Service

**`data/api/ApiService.kt`:**

```kotlin
interface ApiService {
    // Auth
    @POST("/api/v1/token")
    suspend fun login(@Body credentials: LoginRequest): Response<LoginResponse>

    @POST("/api/v1/token/refresh")
    suspend fun refreshToken(@Body body: RefreshTokenRequest): Response<TokenResponse>

    @POST("/api/v1/token/revoke")
    suspend fun logout(): Response<Unit>

    @POST("/api/v1/users")
    suspend fun register(@Body data: RegisterRequest): Response<UserResponse>

    @GET("/api/v1/me")
    suspend fun getCurrentUser(): Response<UserResponse>

    // Decks
    @GET("/api/v1/decks")
    suspend fun getDecks(@Query("language") language: String? = null): Response<DecksResponse>

    @POST("/api/v1/decks")
    suspend fun createDeck(@Body data: CreateDeckRequest): Response<DeckWithStats>

    @GET("/api/v1/decks/{id}")
    suspend fun getDeck(@Path("id") id: Int): Response<DeckWithStats>

    @DELETE("/api/v1/decks/{id}")
    suspend fun deleteDeck(@Path("id") id: Int): Response<Unit>

    @GET("/api/v1/decks/{id}/words")
    suspend fun getDeckWords(@Path("id") id: Int, @QueryMap params: Map<String, String>): Response<PaginatedResponse<Word>>

    @POST("/api/v1/decks/{id}/words")
    suspend fun addWordsToDeck(@Path("id") id: Int, @Body data: AddWordsRequest): Response<CreatedWordsResponse>

    // Words
    @PUT("/api/v1/words/{id}")
    suspend fun updateWord(@Path("id") id: Int, @Body data: UpdateWordRequest): Response<Word>

    @DELETE("/api/v1/words/{id}")
    suspend fun deleteWord(@Path("id") id: Int): Response<Unit>

    // Practice
    @POST("/api/v1/practice/sessions")
    suspend fun startPracticeSession(@Body data: StartSessionRequest): Response<PracticeSessionResponse>

    @POST("/api/v1/practice/sessions/{id}/messages")
    suspend fun sendMessage(@Path("id") id: Int, @Body data: SendMessageRequest): Response<PracticeMessageResponse>

    @POST("/api/v1/practice/sessions/{id}/next-word")
    suspend fun nextWord(@Path("id") id: Int, @Body data: NextWordRequest): Response<PracticeMessageResponse>

    @POST("/api/v1/practice/sessions/{id}/end")
    suspend fun endSession(@Path("id") id: Int): Response<PracticeMessageResponse>

    @GET("/api/v1/practice/sessions/{id}/summary")
    suspend fun getSessionSummary(@Path("id") id: Int): Response<PracticeSummaryResponse>

    // Progress
    @GET("/api/v1/progress/stats")
    suspend fun getProgressStats(): Response<ProgressStats>

    @GET("/api/v1/progress/streak")
    suspend fun getStreak(): Response<StreakData>

    @GET("/api/v1/progress/report-card")
    suspend fun getReportCard(): Response<ReportCardData>

    @POST("/api/v1/progress/generate-feedback")
    suspend fun generateFeedback(): Response<Unit>

    // Settings
    @GET("/api/v1/settings")
    suspend fun getSettings(): Response<SettingsResponse>

    @PUT("/api/v1/settings")
    suspend fun updateSettings(@Body data: UpdateSettingsRequest): Response<SettingsResponse>

    // Account
    @HTTP(method = "DELETE", path = "/api/v1/account", hasBody = true)
    suspend fun deleteAccount(@Body data: DeleteAccountRequest): Response<Unit>
}
```

### 9.2 Auth Interceptor

```kotlin
class AuthInterceptor(private val tokenManager: TokenManager) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()
        val accessToken = tokenManager.getAccessToken()
        return if (accessToken != null) {
            val newRequest = request.newBuilder()
                .header("Authorization", "Bearer $accessToken")
                .build()
            chain.proceed(newRequest)
        } else {
            chain.proceed(request)
        }
    }
}
```

### 9.3 Token Refresh Authenticator (Coroutine-Safe)

Uses `Mutex` instead of `runBlocking` to avoid blocking the OkHttp thread (which can cause ANR):

```kotlin
class TokenRefreshAuthenticator(
    private val tokenManager: TokenManager,
    private val refreshApi: Lazy<ApiService>,
) : Authenticator {
    private val mutex = Mutex()

    override fun authenticate(route: Route?, response: Response): Request? {
        if (response.code != 401) return null
        val refreshToken = tokenManager.getRefreshToken() ?: return null

        // Use a CountDownLatch to bridge sync OkHttp callback to async refresh
        val latch = CountDownLatch(1)
        var newAccessToken: String? = null

        // Double-check: another thread may have refreshed already
        val currentToken = tokenManager.getAccessToken()
        val requestToken = response.request.header("Authorization")?.removePrefix("Bearer ")
        if (currentToken != null && currentToken != requestToken) {
            return response.request.newBuilder()
                .header("Authorization", "Bearer $currentToken")
                .build()
        }

        // Launch coroutine on IO dispatcher to avoid blocking main thread
        CoroutineScope(Dispatchers.IO).launch {
            mutex.withLock {
                // Re-check after acquiring lock
                val tokenAfterLock = tokenManager.getAccessToken()
                if (tokenAfterLock != null && tokenAfterLock != requestToken) {
                    newAccessToken = tokenAfterLock
                    latch.countDown()
                    return@launch
                }

                try {
                    val refreshResponse = refreshApi.value.refreshToken(
                        RefreshTokenRequest(refreshToken)
                    )
                    if (refreshResponse.isSuccessful) {
                        newAccessToken = refreshResponse.body()?.access_token
                        newAccessToken?.let { tokenManager.saveAccessToken(it) }
                    } else {
                        tokenManager.clearTokens()
                    }
                } catch (e: Exception) {
                    tokenManager.clearTokens()
                }
                latch.countDown()
            }
        }

        latch.await(30, TimeUnit.SECONDS)

        return newAccessToken?.let { token ->
            response.request.newBuilder()
                .header("Authorization", "Bearer $token")
                .build()
        }
    }
}
```

### 9.4 Token Manager

```kotlin
class TokenManager(context: Context) {
    private val prefs = EncryptedSharedPreferences.create(
        "laoshi_auth",
        MasterKey.Builder(context).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build(),
        context,
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
    )

    fun saveAccessToken(token: String) = prefs.edit().putString("access_token", token).apply()
    fun getAccessToken(): String? = prefs.getString("access_token", null)
    fun saveRefreshToken(token: String) = prefs.edit().putString("refresh_token", token).apply()
    fun getRefreshToken(): String? = prefs.getString("refresh_token", null)
    fun clearTokens() = prefs.edit().clear().apply()
}
```

---

## 10. Android Navigation

### 10.1 Navigation Graph

```kotlin
sealed class Screen(val route: String) {
    object Login : Screen("login")
    object Register : Screen("register")
    object Onboarding : Screen("onboarding")
    object Home : Screen("home")
    object DeckDetail : Screen("home/deck/{deckId}") {
        fun createRoute(deckId: Int) = "home/deck/$deckId"
    }
    object Practice : Screen("practice/{sessionId}/{deckId}") {
        fun createRoute(sessionId: Int, deckId: Int) = "practice/$sessionId/$deckId"
    }
    object Library : Screen("library")
    object DeckWords : Screen("library/deck/{deckId}") {
        fun createRoute(deckId: Int) = "library/deck/$deckId"
    }
    object Progress : Screen("progress")
    object Settings : Screen("settings")
}
```

### 10.2 Bottom Navigation

Tabs: Home, Library, Progress, Settings.

### 10.3 Auth Flow

```
Login -> (if !onboarding_complete -> Onboarding) -> Home
```

### 10.4 Practice Flow

```
Home -> tap deck -> DeckDetail -> "Start Practice" -> PracticeScreen (full-screen, no bottom nav)
```

---

## 11. Android State Management

### 11.1 Practice Screen State Machine

```kotlin
enum class PracticeStatus {
    AI_TYPING,          // Laoshi generating response
    WAITING_FOR_USER,   // User can type
    FEEDBACK_GIVEN,     // "Next Word" enabled
    RATING_TYPING,      // Typing indicator before rating prompt
    AWAITING_RATING,    // Rating buttons visible
    RATING_SELECTED,    // User selected, advancing
    TRANSITIONING,      // Word divider, loading next
    SESSION_COMPLETE,   // "View Summary" shown
}
```

### 11.2 Session Persistence

Session state saved via `SavedStateHandle` (survives process death) + DataStore:
```kotlin
// In PracticeViewModel
val sessionId: Int = savedStateHandle["sessionId"] ?: 0
val deckId: Int = savedStateHandle["deckId"] ?: 0
```

### 11.3 Client-Side Repository Caching

Repositories implement in-memory caching with TTL to avoid redundant API calls on every screen navigation:

```kotlin
class CachedValue<T>(private val ttlMs: Long = 30_000L) {
    private var value: T? = null
    private var timestamp: Long = 0L

    fun get(): T? {
        if (System.currentTimeMillis() - timestamp > ttlMs) return null
        return value
    }

    fun set(newValue: T) {
        value = newValue
        timestamp = System.currentTimeMillis()
    }

    fun invalidate() { value = null; timestamp = 0L }
}

// Usage in DeckRepository
@Singleton
class DeckRepository @Inject constructor(private val api: ApiService) {
    private val decksCache = CachedValue<List<DeckWithStats>>(ttlMs = 30_000L)  // 30s TTL

    suspend fun getDecks(forceRefresh: Boolean = false): Result<List<DeckWithStats>> {
        if (!forceRefresh) {
            decksCache.get()?.let { return Result.success(it) }
        }
        return runCatching {
            val response = api.getDecks()
            if (response.isSuccessful) {
                val decks = response.body()!!.decks
                decksCache.set(decks)
                decks
            } else throw ApiException(response.code(), response.errorBody()?.string())
        }
    }

    fun invalidateCache() = decksCache.invalidate()
}
```

**Cache TTLs:**
- Deck list: 30 seconds
- Report card: 60 seconds
- Settings: 60 seconds

**Cache invalidation triggers:**
- Pull-to-refresh (`forceRefresh = true`)
- User-initiated mutations (deck create/delete, practice completion, settings update)

---

## 12. Backend Auth Modifications (OAuth2 Client Credentials)

### 12.1 Client Configuration

**`backend/config.py`:**
```python
# OAuth2 client registry
OAUTH_CLIENTS = {
    'laoshi-web': {
        'type': 'web',
        'secret_required': False,   # Public client (SPA -- secret can't be hidden in browser)
    },
    'laoshi-android': {
        'type': 'mobile',
        'secret_required': True,    # Confidential client (secret baked into APK)
        'secret': os.getenv('ANDROID_CLIENT_SECRET'),
    },
}

# JWT_TOKEN_LOCATION stays unchanged -- do NOT add 'json'
JWT_TOKEN_LOCATION = ['headers', 'cookies']
```

**New env vars**: `ANDROID_CLIENT_SECRET` (generated secret for mobile app).

### 12.2 Token Endpoint Changes

**`backend/resources.py` -- `TokenResource.post`:**
```python
from config import OAUTH_CLIENTS

# Validate client credentials
client_id = data.get('client_id')
client_secret = data.get('client_secret')

if not client_id or client_id not in OAUTH_CLIENTS:
    return {'error': 'Invalid client_id'}, 400

client = OAUTH_CLIENTS[client_id]
if client['secret_required']:
    if not client_secret or client_secret != client['secret']:
        return {'error': 'Invalid client credentials'}, 401

# ... existing user authentication logic ...

# Build response based on client type
response_data = {'access_token': access_token}
if client['type'] == 'mobile':
    response_data['refresh_token'] = refresh_token

resp = make_response(jsonify(response_data))
# Always set cookie (harmless for mobile, needed for web)
set_refresh_cookies(resp, refresh_token)
return resp
```

### 12.3 Token Refresh Changes

**`backend/resources.py` -- `TokenRefreshResource.post`:**
```python
from flask_jwt_extended import decode_token

def post(self):
    # Try mobile path first: refresh token in JSON body
    data = request.get_json(silent=True) or {}
    body_refresh_token = data.get('refresh_token')

    if body_refresh_token:
        # Mobile path: manually decode and verify
        try:
            decoded = decode_token(body_refresh_token)
            user_id = decoded['sub']
            # Verify it's a refresh token
            if decoded.get('type') != 'refresh':
                return {'error': 'Invalid token type'}, 401
        except Exception:
            return {'error': 'Invalid or expired refresh token'}, 401

        # Issue new access token
        new_access_token = create_access_token(identity=user_id)
        return {'access_token': new_access_token}, 200
    else:
        # Web path: Flask-JWT-Extended handles cookie-based refresh
        # (existing @jwt_required(refresh=True) logic)
        ...
```

### 12.4 Web Frontend Changes

**`frontend/src/lib/api.ts`:**
```typescript
// Add client_id to login request
const WEB_CLIENT_ID = 'laoshi-web'

export const authApi = {
  login: (username: string, password: string) =>
    api.post('/api/token', { username, password, client_id: WEB_CLIENT_ID }),
  // ...
}
```

### 12.5 Rate Limiting

**`backend/resources.py`:**
```python
from flask_limiter import Limiter

# On TokenResource
@limiter.limit("10/minute")
def post(self):
    ...

# On TokenRefreshResource
@limiter.limit("30/minute")
def post(self):
    ...

# On UserResource (register)
@limiter.limit("5/minute")
def post(self):
    ...
```

---

## 12.6 API Versioning

All existing `/api/*` routes are aliased under `/api/v1/*` via Nginx rewrite:

```nginx
# nginx.conf
location /api/v1/ {
    rewrite ^/api/v1/(.*)$ /api/$1 break;
    proxy_pass http://backend;
}
```

- **Mobile app** uses `/api/v1/` paths exclusively (hardcoded in `BuildConfig.BASE_URL`).
- **Web frontend** continues using `/api/` (both work identically via Nginx rewrite).
- When breaking changes are needed in the future, `/api/v2/` routes can be implemented in the backend while `/api/v1/` continues to work for older mobile clients.
- For local development without Nginx, add a simple Flask `before_request` handler:

```python
@app.before_request
def rewrite_v1():
    if request.path.startswith('/api/v1/'):
        request.environ['PATH_INFO'] = request.path.replace('/api/v1/', '/api/', 1)
```

---

## 13. Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Mobile framework | Kotlin + Jetpack Compose | Native Android performance, Material 3 support, modern declarative UI |
| Language scope | Per-deck tag (`ZH`/`JP`) | Most flexible -- users can have mixed-language decks, language is a deck property |
| DB column rename | `Word.pinyin` -> `Word.reading` | Language-generic: pinyin (ZH) and furigana (JP) are both "readings" |
| JP feedback model | Claude 3.5 Sonnet via LiteLLM | Strong Japanese language understanding; LiteLLM already a dependency (via mem0) |
| ZH feedback model | DeepSeek (unchanged) | Proven Mandarin evaluation capabilities, no reason to change |
| Orchestrator model | Gemini Flash for both | Fast, cost-effective, language-agnostic orchestration |
| BYOK on mobile | Removed | Simplifies mobile UX; BYOK stays on web |
| Backend | Shared between web and mobile | Single API, no duplication |
| Teacher persona | "Laoshi" for all languages | Consistent brand identity |
| Language selection | Per-deck, not onboarding | Users may study multiple languages; per-deck is more flexible |
| Android project path | `mobile_android/` at repo root | Peer to `frontend/` and `backend/`, clean monorepo structure |
| Sample deck env vars | `ZH_SAMPLE_DECK_FILE`, `JP_SAMPLE_DECK_FILE` | Configurable per deployment, graceful skip if missing |
| Mobile auth | OAuth2 client credentials (`client_id` + `client_secret`) | Prevents spoofing via header; mobile is confidential client, web is public client |
| JWT_TOKEN_LOCATION | `['headers', 'cookies']` only (no `'json'`) | Avoids broadening attack surface; mobile refresh token extracted manually in endpoint |
| API versioning | `/api/v1/` alias for mobile | Mobile app uses versioned paths; web continues on `/api/`; enables future `/api/v2/` divergence |
| DI framework (Android) | Hilt | Standard Android DI; enables testable ViewModels and proper dependency scoping |
| LiteLLM integration | Direct `litellm.acompletion()` (no proxy) | Avoids extra network hop; LiteLLM already a dependency via mem0 |
| Chart library (Android) | Vico | Material 3 native, Compose-first, good stacked bar support |

---

## 14. Error Handling

### Backend
- Missing or invalid `client_id`: Return 400 with `{'error': 'Invalid client_id'}`.
- Invalid `client_secret` for confidential client: Return 401 with `{'error': 'Invalid client credentials'}`.
- Rate limit exceeded on auth endpoints: Return 429 with `{'error': 'Too many requests'}`.
- Missing `ANTHROPIC_API_KEY`: Log warning at startup, JP practice returns `{'error': 'Japanese feedback model not configured'}`, 503.
- Invalid `language` on deck creation: Return 400 with `{'error': 'Unsupported language. Must be one of: ZH, JP'}`.
- Combining decks with mixed languages: Return 400 with `{'error': 'Cannot combine decks with different languages'}`.
- Missing JP sample CSV: Log info, skip JP seeding silently, continue registration.

### Android
- Network errors: Show Snackbar with retry option.
- Auth failures (401 after refresh fails): Navigate to login screen.
- Practice session errors: Show error dialog, allow retry.
- Empty states: Show centered message with optional action button.

---

## 15. Testing Strategy

### Backend Tests
- Unit tests for `LANGUAGE_CONFIG` prompt generation with ZH and JP.
- Unit tests for model routing in `build_agents()`.
- Integration tests for deck creation with language field.
- Integration tests for word CRUD with `reading` field.
- Integration tests for backward compat (API accepts `pinyin`, maps to `reading`).
- Integration tests for OAuth2 client credentials flow (web + mobile).
- Integration tests for mobile refresh token via JSON body.
- Integration tests for rate limiting on auth endpoints.
- Migration test: verify existing data unaffected.

### Web Frontend Tests
- Update all tests referencing `pinyin` to use `reading`.
- Component tests for language selector in `CreateDeckModal`.
- Component tests for dynamic column headers in `DeckWordsView`.

### Android Tests
- Unit tests for ViewModels (mock repository).
- Unit tests for TokenManager.
- Integration tests for Retrofit API calls (MockWebServer).
- UI tests for critical flows (Compose testing).
