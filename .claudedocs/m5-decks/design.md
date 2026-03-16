# M5 Decks -- Design

> Technical design for Milestone 5: Decks (Collections Redesign)
> Refer to [architecture.md](../../.claude/architecture.md) for source-of-truth technical stack

---

## 1. Database Schema Changes

### 1.1 New Model: Deck

```python
class Deck(db.Model):
    __tablename__ = 'deck'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    laoshi_message = db.Column(db.String(500), nullable=True)  # AI-generated one-liner
    created_ds = db.Column(db.DateTime, default=datetime.utcnow)
    updated_ds = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', back_populates='decks')
    words = db.relationship('Word', back_populates='deck')
    sessions = db.relationship('UserSession', back_populates='deck')
```

### 1.2 Modified Models

**Word** - Add deck_id FK and SRS fields:
```python
# Deck relationship
deck_id = db.Column(db.Integer, db.ForeignKey("deck.id"), nullable=True)  # Nullable during migration only
deck = db.relationship('Deck', back_populates='words')

# SRS (Spaced Repetition System) fields
repetitions = db.Column(db.Integer, default=0)
interval_days = db.Column(db.Integer, default=1)
ease_factor = db.Column(db.Float, default=2.5)
next_review_date = db.Column(db.Date, nullable=True)  # NULL = new word

# Mastery tracking
last_quality = db.Column(db.Integer, nullable=True)  # 0-5, NULL if never rated
marked_as_known = db.Column(db.Boolean, default=False)
is_mastered = db.Column(db.Boolean, default=False)
```

**Remove:**
```python
confidence_score = db.Column(db.Float, default=0.5)  # REMOVED - replaced by SRS
```

Update `Word.format_data()` to include `deck_id`, SRS fields, and `is_mastered`.

Add method:
```python
def update_mastery_status(self):
    """
    Update is_mastered based on last_quality and marked_as_known (Option B - Lenient).
    
    Logic:
    - Quality 5: Always mark as mastered
    - Quality 4: Preserve existing is_mastered state (don't demote easily)
    - Quality ≤ 3: Remove mastered status
    - marked_as_known: Always mark as mastered (user override)
    """
    if self.marked_as_known or self.last_quality == 5:
        self.is_mastered = True
    elif self.last_quality is not None and self.last_quality <= 3:
        self.is_mastered = False
    # Quality 4: preserve existing is_mastered state (no change)

**UserSession** - Add deck_id FK:
```python
deck_id = db.Column(db.Integer, db.ForeignKey("deck.id"), nullable=True)  # Null for legacy sessions
deck = db.relationship('Deck', back_populates='sessions')
```

Update `UserSession.format_data()` to include `deck_id`.

**UserProfile** - Add streak fields:
```python
current_streak = db.Column(db.Integer, default=0)
last_practice_date = db.Column(db.Date, nullable=True)  # Date only, not datetime
```

### 1.3 Alembic Migration

Single migration file includes:
1. Create `deck` table
2. Add `deck_id` FK to `word` table (nullable)
3. Add `deck_id` FK to `user_session` table (nullable)
4. Add `current_streak`, `last_practice_date` to `user_profile`
5. **Data migration**:
   ```python
   # For each user with words:
   #   - Check if user already has decks (idempotent)
   #   - If not, create "My Words" deck
   #   - Set all their words' deck_id to it
   ```

---

## 2. Backend API Design

### 2.1 API Design Philosophy: Words as Deck Sub-resource

Since each word belongs to exactly one deck (1:many), word creation moves to a deck sub-resource endpoint following the RESTful parent-child pattern (like GitHub's `POST /repos/:owner/:repo/issues`).

**Benefits:**
- Explicit ownership (URL makes it clear words belong to a deck)
- No orphan words
- Scalable (users can add words to a deck at any time)
- Single canonical way to create words

**Trade-off:** `POST /api/words` bulk endpoint is **removed**. All word creation goes through `POST /api/decks/:id/words`.

### 2.2 New Endpoints (`backend/deck_resources.py`)

| Method | Path | Request Body | Response | Notes |
|--------|------|--------------|----------|-------|
| GET | `/api/decks` | - | `{decks: [{id, name, description, word_count, mastered_count, mastery_percentage, last_practiced_at, laoshi_message, created_ds}]}` | Sorted by last_practiced_at ASC (nulls first = least recent on top) |
| POST | `/api/decks` | `{name, description?}` | `{id, name, description, ...}` | Creates empty deck |
| GET | `/api/decks/:id` | - | `{id, name, description, word_count, ...}` | Deck detail + stats |
| PUT | `/api/decks/:id` | `{name?, description?}` | `{id, name, description, ...}` | Update name/description |
| DELETE | `/api/decks/:id` | - | `{}` | Cascade deletes words |
| GET | `/api/decks/:id/words` | Query params: `page`, `per_page`, `search`, `sort_by`, `sort_order` | `{data: [{word, pinyin, meaning, ...}], pagination: {...}}` | Reuse `paginate_query` from utils.py |
| POST | `/api/decks/:id/words` | `{words: [{word, pinyin, meaning, source_name?}, ...]}` | `{created: [{id, word, ...}]}` | Bulk create words in deck |
| POST | `/api/decks/combine` | `{name, description?, source_deck_ids: [int]}` | `{id, name, description, ...}` | Create deck + copy words (SRS state preserved) |

**Stats computation (avoid N+1):**
Use SQLAlchemy `scalar_subquery()` to compute stats in a single query:
- `word_count`: COUNT words WHERE deck_id = deck.id
- `mastered_count`: COUNT words WHERE deck_id = deck.id AND is_mastered = true
- `mastery_percentage`: ROUND((mastered_count / word_count) * 100) (or 0 if word_count = 0)
- `last_practiced_at`: MAX(user_session.session_end_ds) WHERE deck_id = deck.id

### 2.3 Modified/Removed Endpoints

| Endpoint | Change |
|----------|--------|
| `POST /api/words` (bulk create) | **REMOVED** - replaced by `POST /api/decks/:id/words` |
| `DELETE /api/words` (delete all) | **REMOVED** - use `DELETE /api/decks/:id` to delete a deck's words |
| `GET /api/words` | Add optional `deck_id` query param to filter by deck |
| `POST /api/practice/sessions` | Now requires `deck_id` in request body: `{deck_id, words_count?}` |

### 2.4 Streak Endpoint

| Method | Path | Response | Notes |
|--------|------|----------|-------|
| GET | `/api/progress/streak` | `{current_streak, last_practice_date}` | Returns streak data from UserProfile |

### 2.5 Practice Session End Endpoint

| Method | Path | Response | Notes |
|--------|------|----------|-------|
| POST | `/api/practice/sessions/:id/end` | `{laoshi_response, summary, ...}` | Marks remaining SessionWords as skipped, calls `complete_session()` |

---

## 3. Backend Business Logic Changes

### 3.1 Practice Runner Modifications (`practice_runner.py`)

**`initialize_session()` - with SRS word selection:**
```python
def initialize_session(user_id: int, deck_id: int, words_count: int):
    """Start a new practice session using SRS algorithm."""
    from datetime import date
    import random

    user = User.get_by_id(user_id)
    if not user:
        return None, "User not found"

    today = date.today()

    # Calculate target counts (40% new, 60% review)
    target_new = round(words_count * 0.4)
    target_review = words_count - target_new

    # Pool 1: New words (never reviewed)
    new_words = Word.query.filter_by(
        deck_id=deck_id,
        user_id=user_id,
        next_review_date=None
    ).all()

    # Pool 2: Due/overdue review words
    review_words = Word.query.filter(
        Word.deck_id == deck_id,
        Word.user_id == user_id,
        Word.next_review_date <= today
    ).order_by(Word.next_review_date.asc()).all()  # Overdue first

    # Take what's available
    actual_new = min(target_new, len(new_words))
    actual_review = min(target_review, len(review_words))

    # Use buffer pools
    new_shortfall = target_new - actual_new
    review_shortfall = target_review - actual_review

    if new_shortfall > 0:
        actual_review = min(target_review + new_shortfall, len(review_words))
    elif review_shortfall > 0:
        actual_new = min(target_new + review_shortfall, len(new_words))

    # Select words
    selected_new = random.sample(new_words, actual_new) if actual_new > 0 else []
    selected_review = review_words[:actual_review]
    selected_words = selected_new + selected_review

    # Fallback: if both pools insufficient, use future words
    if len(selected_words) < words_count:
        selected_ids = {w.id for w in selected_words}
        future_words = Word.query.filter(
            Word.deck_id == deck_id,
            Word.user_id == user_id,
            Word.next_review_date > today
        ).order_by(Word.next_review_date.asc()).all()

        remaining = [w for w in future_words if w.id not in selected_ids]
        needed = words_count - len(selected_words)
        selected_words.extend(remaining[:needed])

    if not selected_words:
        return None, "No words available for practice in this deck."

    # Create session
    session = UserSession(
        session_start_ds=datetime.utcnow(),
        user_id=user_id,
        deck_id=deck_id,
        words_per_session=len(selected_words),
    )
    session.add()

    # Create SessionWord rows
    for i, word in enumerate(selected_words):
        sw = SessionWord(
            word_id=word.id,
            session_id=session.id,
            session_word_load_ds=datetime.utcnow(),
            word_order=i,
        )
        sw.add()

    # ... rest of logic (mem0 preferences, etc.)
```

**`complete_session()`:**
```python
def complete_session(session_id: int, user_id: int):
    # ... existing summary generation logic

    # Extract deck_oneliner from summary JSON
    summary_data = _parse_json_from_string(summary_text)
    if summary_data and 'deck_oneliner' in summary_data:
        deck_id = session.deck_id
        if deck_id:
            deck = Deck.get_by_id(deck_id)
            if deck:
                deck.laoshi_message = summary_data['deck_oneliner']
                deck.update()
    else:
        # Fallback placeholder if AI doesn't generate one-liner
        deck_id = session.deck_id
        if deck_id:
            deck = Deck.get_by_id(deck_id)
            if deck and (not deck.laoshi_message or deck.laoshi_message == ""):
                deck.laoshi_message = "Laoshi is waiting for your next practice session"
                deck.update()

    # Update streak
    update_streak(user_id)

    # ... rest of logic
```

**New function: `update_streak(user_id)`:**
```python
def update_streak(user_id: int):
    """
    Update user's practice streak with database-level locking to prevent race conditions.
    Uses SELECT FOR UPDATE to ensure atomic streak updates.
    """
    from backend.extensions import db
    
    # Use transaction with row-level locking
    with db.session.begin():
        # Lock the user_profile row for this user
        profile = db.session.query(UserProfile).filter_by(
            user_id=user_id
        ).with_for_update().first()
        
        if not profile:
            return
        
        today = date.today()

        if profile.last_practice_date == today:
            return  # Already practiced today
        elif profile.last_practice_date == today - timedelta(days=1):
            profile.current_streak += 1
        else:
            profile.current_streak = 1

        profile.last_practice_date = today
        # No explicit commit needed - db.session.begin() context manager handles it
```

**New function: `update_srs(word, quality)`:**
```python
def update_srs(word, quality: int):
    """
    Update word SRS state using modified SM-2 algorithm.

    Args:
        word: Word instance
        quality: 0-5 rating from user self-assessment
    """
    from datetime import date, timedelta
    import math

    # Fast-track perfect first attempts
    if word.repetitions == 0 and quality == 5:
        word.interval_days = 14
        word.repetitions = 2
        word.ease_factor = 2.5
    elif quality < 3:
        # Harsh reset on failure (fair since user controls quality)
        word.repetitions = 0
        word.interval_days = 1
    else:
        # Standard SM-2 progression with gentler early intervals
        if word.repetitions == 0:
            word.interval_days = 1
        elif word.repetitions == 1:
            word.interval_days = 3  # Gentler than SM-2 default (6 days)
        elif word.repetitions == 2:
            word.interval_days = 7
        else:
            new_interval = word.interval_days * word.ease_factor
            # Use ceil for intervals < 7 to prevent stuck at 1 day
            if new_interval < 7:
                word.interval_days = math.ceil(new_interval)
            else:
                word.interval_days = round(new_interval)

        word.repetitions += 1

    # Update ease factor (SM-2 formula)
    word.ease_factor += (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    word.ease_factor = max(1.3, word.ease_factor)  # Clamp to minimum 1.3

    # Set next review date
    word.next_review_date = date.today() + timedelta(days=word.interval_days)
```

**New function: `mark_word_as_mastered(word)`:**
```python
def mark_word_as_mastered(word):
    """Fast-track word to mastered state with long interval."""
    from datetime import date, timedelta

    word.marked_as_known = True
    word.last_quality = 5
    word.is_mastered = True

    # SRS fast-track
    word.repetitions = 5
    word.interval_days = 90
    word.ease_factor = 2.5
    word.next_review_date = date.today() + timedelta(days=90)


def unmark_word_as_mastered(word):
    """Remove mastered status and recalculate based on last quality rating."""
    word.marked_as_known = False
    # Recalculate is_mastered based on last_quality
    word.update_mastery_status()
```

**Modified: `advance_word()` - add quality rating and SRS update:**
```python
def advance_word(session_id: int, user_id: int, quality: int):
    """
    Advance to next word - compute averaged scores, update SRS, update mastery.

    Args:
        quality: User's self-rated quality (0-5)
    """
    # ... existing logic to get session, current_sw, attempts ...

    if attempts:
        # Average AI scores
        avg_grammar = sum(a.grammar_score for a in attempts) / len(attempts)
        avg_usage = sum(a.usage_score for a in attempts)  / len(attempts)
        avg_naturalness = sum(a.naturalness_score for a in attempts) / len(attempts)

        # Use isCorrect from last attempt
        last_attempt = attempts[-1]
        is_correct = last_attempt.is_correct

        # Write to SessionWord
        current_sw.avg_grammar_score = avg_grammar
        current_sw.avg_usage_score = avg_usage
        current_sw.avg_naturalness_score = avg_naturalness
        current_sw.is_correct = is_correct
        current_sw.status = 1  # completed
        current_sw.update()

        # Update Word SRS state
        word = Word.get_by_id(current_sw.word_id)
        word.last_quality = quality
        update_srs(word, quality)
        word.update_mastery_status()
        word.update()

    else:
        # Skipped without attempts - defer by 1 day
        current_sw.is_skipped = True
        current_sw.status = 1
        current_sw.update()

        word = Word.get_by_id(current_sw.word_id)
        if word.next_review_date:
            word.next_review_date = word.next_review_date + timedelta(days=1)
        else:
            word.next_review_date = date.today() + timedelta(days=1)
        word.update()

    # ... rest of logic (increment current_word_index, etc.)
```

### 3.2 AI Agent Changes (`chat_agents.py`)

**`build_summary_prompt()`:**
Add to JSON output spec:
```
"deck_oneliner": "A short (max 80 chars) message about this deck's progress and what to focus on next. Examples: 'Your 把 sentences are getting natural! Try 被 constructions next.' or 'Great work on restaurant vocab! Ready for ordering?'"
```

---

## 4. Frontend UX - Library Page

The Library page is the deck management hub where users create, edit, delete, and upload words to decks. It is visually distinct from the Home page (which is motivation-focused with laoshi messages).

### 4.1 Main Library View

**Layout:**
- No top-level summary stats (removed for simplicity)
- Grid of deck cards (3-4 columns on desktop, responsive for tablet/mobile)
- "+ Create New Deck" button (top-right) opens dropdown menu
- Empty state when user has 0 decks

**Deck Card Content:**
```
┌─────────────────────────────────────┐
│ Daily Conversations            ⋮    │  ← Name (bold) + kebab menu (top-right)
│ Everyday phrases and expressions    │  ← Description (muted gray, 1-2 lines, truncated)
│                                     │
│ 234 words  •  🌸 65% mastered      │  ← Total words + growth icon + mastery %
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │  ← Progress bar (recency-colored)
│                                     │
│ 🟢 2h ago                           │  ← Recency badge (bottom-left)
└─────────────────────────────────────┘
```

**Elements:**
- **Deck name**: Bold, 1-2 lines max, truncated with ellipsis
- **Description**: Muted gray, 1-2 lines, truncated
- **Stats row**: `{word_count} words  •  {growth_icon} {mastery_percentage}% mastered`
- **Progress bar**: Full-width at bottom, colored by recency (not mastery)
- **Recency badge**: Bottom-left, small text with color dot (🟢/🟡/🔴/⚫) + time ago
- **Kebab menu (⋮)**: Top-right corner

**Recency Color Logic (Option B - Icon + Bar Together):**

Uses the new theme tokens (sage/amber/coral/neutral). See Section 6.4 for the full `getRecencyStyle()` implementation.

```tsx
const style = getRecencyStyle(deck.last_practiced_at);

// Card left border colored by recency
<div className={`border-l-[3px] ${style.border} ...`}>

// Progress bar (recency-colored fill + tint track)
<div className={`h-1.5 rounded-full ${style.progressTrack}`}>
  <div className={`h-full rounded-full ${style.progressFill}`}
       style={{ width: `${deck.mastery_percentage}%` }} />
</div>

// Recency badge pill
<span className={`text-xs px-2 py-0.5 rounded-full ${style.badgeBg} ${style.badgeText}`}>
  {formatRecency(deck.last_practiced_at)}
</span>
```

**Kebab Menu (⋮) Items:**
- Edit Deck (name, description)
- Delete Deck

**Create New Deck Dropdown:**
```
┌─────────────────────────┐
│ + Manual Creation       │
│ ↑ Upload CSV            │
│ 🔗 Combine Decks        │
│ 👥 Shared Decks         │  ← (Deferred to future milestone)
└─────────────────────────┘
```

**Notes:**
- No descriptions under menu items (e.g., "Add cards one by one" removed)
- "Community Decks" renamed to "Shared Decks"
- Clicking "Manual Creation" opens CreateDeckModal with empty form
- Clicking "Upload CSV" opens CreateDeckModal with CSV upload option
- Clicking "Combine Decks" opens CombineDecksModal

**Click Behavior:**
- Clicking deck card navigates to `/library/deck/:id` (word table view)

### 4.2 Deck Detail View (`/library/deck/:id`)

**Header:**
- "← Back to Library" breadcrumb (top-left)
- Deck name + description (editable via Edit button)

**Stats (Simplified):**
```
┌──────────────────────────────────┐
│        102 / 156 mastered        │  ← Single line, clear ratio
│          (65%)                   │  ← Percentage below
│                                  │
│        🌿 Growing                │  ← Growth icon + stage name
└──────────────────────────────────┘
```

**Growth Stage Names:**
- 🌱 Seedling (0-24% mastered)
- 🌿 Growing (25-74% mastered)  // Note: "Leaves" icon used in code
- 🌸 Blooming (75-100% mastered)

**Actions (Top-right):**
- "+ Add Word" button
- "Export" button

**Content:**
- Search bar (filter words by character, pinyin, or meaning)
- Words table (reuse pattern from current Vocabulary.tsx):
  - Columns: #, 中文, Pinyin, Meaning, Notes, Status, Actions (edit/delete icons)
  - **Status column**: Shows word SRS status as badge
    - "New" (grey) - `next_review_date IS NULL`
    - "In Review" (blue) - `next_review_date IS NOT NULL AND is_mastered = false`
    - "Mastered" (green) - `is_mastered = true`
  - Pagination (10/25/50 per page)
  - Sort by any column

**Info Banner (for combined decks):**
If deck was created via "Combine Decks", show info note:
```
ℹ️ Words in this deck are copies. Changes here won't affect the original decks.
```

### 4.3 Empty State (0 decks)

```
┌────────────────────────────────────────┐
│         📚 No decks yet                │
│                                        │
│   Create your first deck to start      │
│          practicing!                   │
│                                        │
│      [+ Create New Deck]               │
└────────────────────────────────────────┘
```

### 4.4 Home vs Library Comparison

| Element | **Home** (Left Panel) | **Library** (Main View) |
|---------|----------------------|------------------------|
| **Purpose** | Choose what to practice (motivational) | Manage deck content (functional) |
| Growth icon | 🌿 (colored by recency) | 🌿 (colored by recency) |
| Progress bar | Colored by recency | Colored by recency |
| Deck name | ✅ | ✅ |
| Description | ✅ (1 line) | ✅ (1-2 lines) |
| Stats | "102/156 words" | "234 words • 🌸 65% mastered" |
| **Laoshi message** | ✅ **"Your 把 sentences..."** | ❌ **REMOVED** |
| Recency badge | 🟢 2h ago | 🟢 2h ago |
| Actions | None (nav only) | Kebab menu (⋮) |
| Click action | Show deck detail in right panel | Navigate to word table (`/library/deck/:id`) |

**Key Difference:** Home has `laoshi_message` for motivation; Library doesn't (cleaner, management-focused).

### 4.5 New Components

**`pages/Library.tsx`**:
- Replaces `Vocabulary.tsx`
- Grid layout for deck cards
- "+ Create New Deck" dropdown
- Empty state

**`pages/library/CreateDeckModal.tsx`**:
- Form with name (required), description (optional)
- Triggered by dropdown menu items

**`pages/library/CombineDecksModal.tsx`**:
- Multi-select checkbox list of user's decks
- Name + description for new deck
- Info note: "Words will be copied. Changes to the new deck won't affect the originals."

**`pages/library/DeckWordsView.tsx`**:
- Word table for a specific deck
- Reuses table pattern from current `Vocabulary.tsx`
- Search, sort, paginate
- Edit/delete individual words
- "+ Add Word" and "Export" buttons

**`pages/library/UploadModal.tsx`** (moved from `vocabulary/`):
- CSV upload form
- PapaParse for CSV parsing
- Validation
- Accepts `deckId` prop (upload words to specific deck)

**`pages/library/EditWordModal.tsx`** (moved from `vocabulary/`):
- Form to edit word, pinyin, meaning

### 4.6 Deleted Files

- `pages/Vocabulary.tsx` → replaced by `pages/Library.tsx`
- `pages/Practice.tsx` → logic moves to `pages/home/PracticePanel.tsx`
- `pages/vocabulary/UploadModal.tsx` → moved to `pages/library/UploadModal.tsx`
- `pages/vocabulary/EditWordModal.tsx` → moved to `pages/library/EditWordModal.tsx`

---

## 5. Frontend Architecture

### 5.1 Routing Structure (`App.tsx`)

**New nested routing:**
```tsx
<Route path="/home" element={<Home />}>
  <Route index element={<EmptyDeckPlaceholder />} />
  <Route path="deck/:deckId" element={<DeckDetailPanel />} />
  <Route path="deck/:deckId/practice" element={<PracticePanel />} />
</Route>
<Route path="/library" element={<Library />}>
  <Route index element={<DeckList />} />
  <Route path="deck/:deckId" element={<DeckWordsView />} />
</Route>
<Route path="/progress" element={<ReportCard />} />
<Route path="/settings" element={<Settings />} />

{/* REMOVED: */}
{/* <Route path="/practice" element={<Practice />} /> */}
{/* <Route path="/vocabulary" element={<Vocabulary />} /> */}
```

### 5.2 Component Architecture

**Home Page (Split-Panel):**
```
<Home> (pages/Home.tsx)
  <HomeProvider>  (pages/home/HomeContext.tsx)
    <div className="flex">
      <DeckListPanel />  (pages/home/DeckListPanel.tsx)
        - Fetches GET /api/decks
        - Renders DeckListItem for each deck
        - Streak badge at top
        - "+ New Deck" button at bottom

      <Outlet />  (right panel - nested routes)
        - EmptyDeckPlaceholder (pages/home/EmptyDeckPlaceholder.tsx)
        - DeckDetailPanel (pages/home/DeckDetailPanel.tsx)
        - PracticePanel (pages/home/PracticePanel.tsx)
    </div>
  </HomeProvider>
</Home>
```

**HomeContext:**
```tsx
interface HomeContextValue {
  selectedDeckId: number | null
  activePracticeSessionId: number | null
  showEndSessionModal: boolean
  selectDeck: (deckId: number) => void
  startPractice: (deckId: number) => void
  endPractice: () => void
  confirmEndSession: () => void
}
```

**DeckListItem (`pages/home/DeckListPanel.tsx`):**

Chat-app style list item (not card layout). Each deck is a horizontal row with border-b separator.

```
┌──────────────────────────────────────────────────────┐
│ ┌───┐                                                │
│ │ 🌿│  HSK 4 Core              2 hours ago           │  ← Avatar (recency-colored circle + Lucide growth icon)
│ └───┘  Your 把 sentences are getting...              │  ← Laoshi message preview (line-clamp-1)
│         ━━━━━━━━━━━━━━━━━━━━━━━━━  34/120            │  ← Progress bar (indented under avatar) + word count
└──────────────────────────────────────────────────────┘
```

**Layout:**
- `w-full text-left px-5 py-4 border-b border-warm-gray/50`
- No border/rounded card — flat list items

**Avatar (left):**
- `w-11 h-11 rounded-full` with recency-colored background + white Lucide icon
- Growth icons (3 tiers, Lucide components):
  - `<Sprout size={20}>` for <25% mastered
  - `<Leaf size={20}>` for 25-74% mastered
  - `<Flower size={20}>` for 75-100% mastered
- Avatar background color = recency color (sage/amber/coral hex via inline style)

**Content (right of avatar):**
- Row 1: **Deck name** (`font-medium text-warm-black truncate`) + **time ago** (right-aligned, `text-xs text-warm-black/40`)
- Row 2: **Laoshi message preview** (`text-sm text-warm-black/50 line-clamp-1`)

**Progress bar (below content, indented):**
- Indented with `pl-[60px]` to align under content (past avatar)
- `h-1.5 bg-warm-gray/60 rounded-full` track
- Fill color = recency color (via inline `style={{ backgroundColor: recency.bar }}`)
- Word count right of bar: `text-[10px] text-warm-black/35 font-medium tabular-nums` showing `{mastered}/{total}`

**Active state:**
- `bg-sage-tint` background
- Left indicator: `absolute left-0 top-0 bottom-0 w-[3px]` with recency background color

**Recency color function (returns hex values for inline styles):**
```tsx
function getRecencyColor(lastPracticedAt: string | null) {
  if (!lastPracticedAt) return { bg: '#A8A5A0', bar: '#A8A5A0', tint: 'rgba(168,165,160,0.12)' }
  const hours = (Date.now() - new Date(lastPracticedAt).getTime()) / 3_600_000
  if (hours <= 48)  return { bg: '#6B8F71', bar: '#6B8F71', tint: 'rgba(107,143,113,0.12)' }  // sage
  if (hours <= 120) return { bg: '#C4973B', bar: '#C4973B', tint: 'rgba(196,151,59,0.12)' }   // amber
  return { bg: '#D4715E', bar: '#D4715E', tint: 'rgba(212,113,94,0.12)' }                     // coral
}
```

**DeckDetailPanel / DeckLobby (`pages/home/DeckDetailPanel.tsx`):**

Wide horizontal 2-column layout with framer-motion entrance animation.

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│     ┌─────────┐                   ┏━ Last practiced 2h ago ━┓   │
│     │         │                                              │   │
│     │  28%    │      HSK 4 Core          (font-serif 4xl)   │   │
│     │  ring   │                                              │   │
│     │         │     120          58          34              │   │
│     └─────────┘   Total Words  Practiced  Mastered (sage)   │   │
│                                                              │   │
│                   "Your 把 sentences are getting really      │   │
│                    natural! Ready for some 被 constructions?" │   │
│                                                              │   │
│                   [▶ Start Practice]   Manage in Library →   │   │
└──────────────────────────────────────────────────────────────────┘
```

**Layout:**
- `flex-1 h-full flex flex-col items-center justify-center bg-warm-offwhite p-8`
- Inner card: `max-w-3xl w-full bg-white rounded-3xl p-12 border border-warm-gray shadow-sm`
- Decorative: `absolute -top-24 -right-24 w-64 h-64 bg-sage-tint rounded-full opacity-50 blur-3xl` (subtle background orb)
- Flex row: progress ring (left) + content (right), `gap-12`

**Progress ring (left):**
- Reusable `<ProgressRing>` component (SVG circular progress)
- `size={160} strokeWidth={10}`
- Track: `stroke-warm-gray`
- Fill: `stroke-sage`
- Center text: percentage + "mastered"

**Content (right):**
- "Last practiced" pill badge: `px-3 py-1 bg-warm-gray/30 text-warm-black/60 rounded-full text-xs`
- Deck name: `font-serif text-4xl text-warm-black` (uses Lora font)
- Stats: 3-column grid with large numbers (`text-2xl font-medium`), mastered count in `text-sage`
- Laoshi message: quote box with `bg-sage-tint/50 p-5 rounded-2xl border border-warm-gray/50`, italic text
- Buttons row:
  - Start Practice: `bg-sage hover:bg-sage/90 text-white px-8 py-4 rounded-xl text-lg` with PlayIcon
  - Manage in Library: text link `text-warm-black/40 hover:text-warm-black` with ArrowRightIcon + hover translate-x animation

**Animation (framer-motion):**
```tsx
<motion.div
  initial={{ opacity: 0, scale: 0.98 }}
  animate={{ opacity: 1, scale: 1 }}
  exit={{ opacity: 0 }}
  transition={{ duration: 0.2 }}
>
```

**Dependencies:**
- `framer-motion` (added to package.json)
- Lucide icons: `Sprout`, `Leaf`, `Flower2` (3-tier growth), `PlayIcon`, `ArrowRightIcon`

**PracticePanel:**
- Refactored from `Practice.tsx`
- Extract state logic into `usePracticeSession` hook
- Chat area center
- Collapsible word panel right side (only current word)
- Close button top right → `POST /api/practice/sessions/:id/end`
- SessionSummary inline (not full-screen)

**Library Page:**
```
<Library> (pages/Library.tsx)
  <div>Deck card grid</div>
  <CreateDeckModal />
  <Outlet />
    - DeckWordsView (pages/library/DeckWordsView.tsx)
      - Reuses Vocabulary.tsx table pattern
      - Search, sort, paginate
      - Edit/delete words
      - Upload CSV button (adds to this deck)
      - Info banner for combined decks
</Library>
```

### 5.3 TypeScript Types (`types/api.ts`)

```typescript
export interface Deck {
  id: number
  name: string
  description: string | null
  user_id: number
  laoshi_message: string | null
  created_ds: string
  updated_ds: string
}

export interface DeckWithStats extends Deck {
  word_count: number
  mastered_count: number
  mastery_percentage: number
  last_practiced_at: string | null
}

export interface Word {
  id: number
  word: string
  pinyin: string
  meaning: string
  user_id: number
  deck_id: number | null
  source_name: string | null

  // SRS fields
  repetitions: number
  interval_days: number
  ease_factor: number
  next_review_date: string | null

  // Mastery fields
  last_quality: number | null
  marked_as_known: boolean
  is_mastered: boolean

  created_ds: string
  updated_ds: string
}

export interface DeckListItem extends DeckWithStats {}

export interface DeckDetail extends DeckWithStats {}

export interface StreakData {
  current_streak: number
  last_practice_date: string | null
}
```

### 5.4 API Client (`lib/api.ts`)

```typescript
export const deckApi = {
  getDecks: () => api.get<{decks: DeckListItem[]}>('/api/decks'),
  createDeck: (data: {name: string, description?: string}) =>
    api.post<DeckDetail>('/api/decks', data),
  updateDeck: (id: number, data: {name?: string, description?: string}) =>
    api.put<DeckDetail>(`/api/decks/${id}`, data),
  deleteDeck: (id: number) => api.delete(`/api/decks/${id}`),
  getDeckWords: (id: number, params?: PaginationParams) =>
    api.get<PaginatedResponse<Word>>(`/api/decks/${id}/words`, {params}),
  addWordsToDeck: (id: number, words: {word: string, pinyin: string, meaning: string, source_name?: string}[]) =>
    api.post(`/api/decks/${id}/words`, {words}),
  combineDecks: (data: {name: string, description?: string, source_deck_ids: number[]}) =>
    api.post<DeckDetail>('/api/decks/combine', data),
}

export const progressApi = {
  // ... existing methods
  getStreak: () => api.get<StreakData>('/api/progress/streak'),
}

export const practiceApi = {
  startSession: (deckId: number, wordsCount?: number) =>
    api.post<PracticeSessionResponse>('/api/practice/sessions', {deck_id: deckId, words_count: wordsCount}),
  endSession: (sessionId: number) =>
    api.post<PracticeSessionResponse>(`/api/practice/sessions/${sessionId}/end`),
  // ... existing methods
}
```

---

## 6. Color Scheme — "Quiet Study" Theme

Replace the old purple (#9333EA) theme with a warm, muted "Quiet Study" palette. This is a **full replacement** — the old `primary-*` and `stone-*` custom tokens are removed entirely.

### 6.1 Tailwind Config (`tailwind.config.js`)

```javascript
export default {
  content: ['./index.html', './frontend/src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        warm: {
          offwhite: '#FAFAF8',   // page backgrounds
          black: '#2A2A28',      // primary text
          gray: '#E8E5E0',       // borders, dividers
          muted: '#8A8A86',      // secondary text, placeholders
        },
        sage: {
          DEFAULT: '#6B8F71',    // primary action color (buttons, active states, links)
          tint: '#EDF2EE',       // light sage background (hover, active sidebar)
        },
        amber: {
          DEFAULT: '#C4973B',    // warning/medium recency accent
          tint: '#FBF5E8',       // light amber background
        },
        coral: {
          DEFAULT: '#D4715E',    // danger/stale recency accent
          tint: '#FDF0ED',       // light coral background
        },
        neutral: {
          DEFAULT: '#A8A5A0',    // never-practiced, disabled states
          tint: '#F2F1EF',       // light neutral background
        },
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        serif: ['Lora', 'serif'],
      },
    },
  },
  plugins: [],
}
```

**Removed tokens:**
- `primary-*` (DEFAULT, 50-900) — old purple palette
- Custom `stone-*` overrides — use Tailwind's built-in `stone-*` or `warm-*` tokens

### 6.2 Theme Replacement Mapping

All components must replace old color classes with the new theme tokens:

| Old Class | New Class | Usage |
|-----------|-----------|-------|
| `bg-purple-600`, `bg-primary-600` | `bg-sage` | Primary buttons |
| `bg-purple-700`, `bg-primary-700`, `hover:bg-purple-700` | `hover:bg-sage/90` | Button hover (use opacity) |
| `bg-purple-100`, `bg-primary-100`, `bg-primary-50` | `bg-sage-tint` | Active/selected backgrounds |
| `text-purple-600`, `text-primary-600` | `text-sage` | Links, active text, icons |
| `text-purple-700`, `text-primary-700` | `text-sage` | Active text (same token) |
| `border-purple-500`, `border-primary-500` | `border-sage` | Active borders |
| `border-purple-300`, `border-primary-300` | `border-sage/50` | Hover borders |
| `focus:ring-purple-500`, `focus:ring-primary-500` | `focus:ring-sage` | Focus rings on inputs |
| `bg-purple-50`, `hover:bg-purple-50` | `hover:bg-sage-tint` | Hover backgrounds |
| `text-stone-800` | `text-warm-black` | Primary text |
| `text-stone-500`, `text-stone-600` | `text-warm-muted` | Secondary text |
| `border-stone-200`, `border-stone-300` | `border-warm-gray` | Borders |
| `bg-stone-50`, `bg-stone-100` | `bg-warm-offwhite` | Page/section backgrounds |
| `disabled:bg-stone-300` | `disabled:bg-warm-gray` | Disabled buttons |

### 6.3 Files Requiring Theme Replacement

**M5 new components (use `primary-*`):**
1. `pages/library/index.tsx` — buttons, modals, active states, focus rings
2. `pages/home/DeckListPanel.tsx` — active deck highlight, buttons
3. `pages/home/DeckDetailPanel.tsx` — progress ring, buttons
4. `pages/home/PracticePanel.tsx` — chat UI, buttons
5. `pages/home/EmptyDeckPlaceholder.tsx` — text, icons

**Existing components (use `purple-*`):**
6. `components/Sidebar.tsx` — active nav item
7. `pages/Progress.tsx` — charts, stats
8. `components/SessionSummary.tsx` — summary cards
9. `pages/Settings.tsx` — form elements
10. `pages/settings/EditApiKeyModal.tsx` — modal buttons
11. `components/FeedbackCard.tsx` — score highlights
12. `pages/Vocabulary.tsx` — _(being replaced by Library, but exists until deleted)_
13. `pages/vocabulary/EditWordModal.tsx` — _(being moved to library/)_
14. `pages/vocabulary/UploadModal.tsx` — _(being moved to library/)_
15. `components/Pagination.tsx` — active page, buttons
16. `pages/Register.tsx` — form, submit button
17. `components/ProtectedRoute.tsx` — loading spinner
18. `pages/Login.tsx` — form, submit button, links
19. `pages/Welcome.tsx` — CTA buttons, hero section
20. `test/Pagination.test.tsx` — test assertions for CSS classes

### 6.4 Recency Colors (using new theme tokens)

The recency color system uses the new theme tokens instead of Tailwind's built-in green/yellow/red:

```tsx
function getRecencyStyle(lastPracticedAt: string | null) {
  if (!lastPracticedAt) {
    return {
      border: 'border-l-neutral',         // card left border
      badgeBg: 'bg-neutral-tint',          // recency badge background
      badgeText: 'text-neutral',           // recency badge text
      progressFill: 'bg-neutral',          // progress bar fill
      progressTrack: 'bg-neutral-tint',    // progress bar track
    }
  }

  const hours = (Date.now() - new Date(lastPracticedAt).getTime()) / 3_600_000

  if (hours < 48) {
    return {
      border: 'border-l-sage',
      badgeBg: 'bg-sage-tint',
      badgeText: 'text-sage',
      progressFill: 'bg-sage',
      progressTrack: 'bg-sage-tint',
    }
  }
  if (hours < 120) {
    return {
      border: 'border-l-amber',
      badgeBg: 'bg-amber-tint',
      badgeText: 'text-amber',
      progressFill: 'bg-amber',
      progressTrack: 'bg-amber-tint',
    }
  }
  return {
    border: 'border-l-coral',
    badgeBg: 'bg-coral-tint',
    badgeText: 'text-coral',
    progressFill: 'bg-coral',
    progressTrack: 'bg-coral-tint',
  }
}
```

### 6.5 Sidebar Navigation Order

Sidebar items top-to-bottom:
1. Home
2. **Library** _(moved above Report Card — higher usage frequency)_
3. Report Card
4. Settings

Active state: `bg-sage-tint text-sage` (replaces `bg-purple-100 text-purple-600`)

### 6.6 Library Deck Card — Inline Edit & Kebab Menu

**Deck Card Visual Structure:**
```
┌─┬──────────────────────────────────────┐
│▌│ Daily Conversations             ⋮    │  ← border-l-[3px] (recency color)
│▌│                                      │
│▌│ Everyday phrases and expressions     │  ← description (line-clamp-2)
│▌│ for daily life situations            │
│▌│                                      │
│▌│ 234 words  ·  🌸 65% mastered       │  ← stats row
│▌│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │  ← progress bar (recency fill + tint track)
│▌│                                      │
│▌│  2h ago                              │  ← recency badge pill
└─┴──────────────────────────────────────┘
```

**Card dimensions:** `h-[240px]`, white background, rounded-lg, shadow-sm, `border-l-[3px]` with recency color

**Kebab Menu (⋮):**
- Positioned top-right, only visible on card hover
- Dropdown items:
  1. **Edit Deck** (PencilIcon) — enters inline edit mode
  2. **Delete Deck** (Trash2Icon, text-coral) — shows delete confirmation

**Inline Edit Mode:**
When "Edit Deck" is clicked, the card transforms in-place:
```
┌─┬──────────────────────────────────────┐
│▌│ ┌──────────────────────────────────┐ │  ← ring-2 ring-sage on card
│▌│ │ Daily Conversations          ▊  │ │  ← input (auto-focus, select all)
│▌│ └──────────────────────────────────┘ │
│▌│ ┌──────────────────────────────────┐ │
│▌│ │ Everyday phrases and            │ │  ← textarea (2 rows)
│▌│ │ expressions for daily life...   │ │
│▌│ └──────────────────────────────────┘ │
│▌│                                      │
│▌│              [Cancel]  [Save]        │  ← Cancel (text), Save (bg-sage)
└─┴──────────────────────────────────────┘
```

**Inline Edit Behavior:**
- Name becomes `<input>` with auto-focus and select-all
- Description becomes `<textarea>` (2 rows)
- Card gets `ring-2 ring-sage` highlight
- Keyboard shortcuts: **Enter** saves, **Esc** cancels
- Save calls `PUT /api/decks/:id` with `{name, description}`
- Cancel restores original values

**Delete Confirmation:**
When "Delete Deck" is clicked:
```
confirm(`Delete "${deckName}"? This will permanently delete ${wordCount} word${wordCount !== 1 ? 's' : ''}. This cannot be undone.`)
```

---

## 7. Growth Icons & Recency Colors

**Growth Icon Logic (3 stages based on mastery %):**

Two implementations depending on context:

**Emoji version** (Library deck cards, stats text):
```tsx
function getGrowthEmoji(masteryPercentage: number): string {
  if (masteryPercentage < 25) return '🌱'  // Seedling
  if (masteryPercentage < 75) return '🌿'  // Growing
  return '🌸'  // Blooming
}
```

**Lucide icon version** (Home DeckListItem avatar):
```tsx
import { Sprout, Leaf, Flower2 } from 'lucide-react'

function getGrowthIcon(masteryPercentage: number) {
  if (masteryPercentage < 25) return <Sprout size={20} strokeWidth={2} />   // Seedling
  if (masteryPercentage < 75) return <Leaf size={20} strokeWidth={2} />     // Growing
  return <Flower2 size={20} strokeWidth={2} />                              // Blooming
}
```

| Stage | Range | Emoji | Lucide Icon | Label |
|-------|-------|-------|-------------|-------|
| Seedling | 0-24% | 🌱 | `<Sprout>` | Seedling |
| Growing | 25-74% | 🌿 | `<Leaf>` | Growing |
| Blooming | 75-100% | 🌸 | `<Flower2>` | Blooming |

**Recency Color Logic:**

Uses new theme tokens. See Section 6.4 for the full `getRecencyStyle()` implementation returning `{ border, badgeBg, badgeText, progressFill, progressTrack }` using sage/amber/coral/neutral tokens.

| Recency | Thresholds | Theme Token |
|---------|-----------|-------------|
| Fresh | <48h | `sage` / `sage-tint` |
| Stale | 48-120h | `amber` / `amber-tint` |
| Overdue | >120h | `coral` / `coral-tint` |
| Never practiced | null | `neutral` / `neutral-tint` |

---

## 8. Quality Rating UI & "Mark as Known" Button

### 8.1 Quality Rating Menu

After user clicks "Next Word," display a chat-style button menu prompting for quality self-assessment:

**UI Design:**
```tsx
<div className="quality-rating-prompt">
  <p className="text-center text-gray-700 mb-4">
    How well do you understand how to use this word?
  </p>

  <div className="grid grid-cols-1 gap-2">
    <button onClick={() => handleQualitySelect(0)} className="quality-button">
      <span className="emoji">😣</span>
      <span className="label">I don't understand how to use this word</span>
    </button>
    <button onClick={() => handleQualitySelect(1)} className="quality-button">
      <span className="emoji">😕</span>
      <span className="label">Very unclear - I'm mostly guessing</span>
    </button>
    <button onClick={() => handleQualitySelect(2)} className="quality-button">
      <span className="emoji">😐</span>
      <span className="label">Somewhat unclear - I struggle to use this word</span>
    </button>
    <button onClick={() => handleQualitySelect(3)} className="quality-button">
      <span className="emoji">🙂</span>
      <span className="label">Rough understanding - I can use this word but it's awkward</span>
    </button>
    <button onClick={() => handleQualitySelect(4)} className="quality-button">
      <span className="emoji">😊</span>
      <span className="label">Good grasp - it's mostly natural to me</span>
    </button>
    <button onClick={() => handleQualitySelect(5)} className="quality-button">
      <span className="emoji">🤩</span>
      <span className="label">Perfect command - I use this word naturally all the time</span>
    </button>
  </div>
</div>
```

**Behavior:**
- Appears after user clicks "Next Word" (blocks progression)
- Selection triggers `advanceWord(sessionId, quality)` API call
- On success, next word loads
- If last word, proceeds to session summary

**API Integration:**
```typescript
// Update advance_word endpoint signature
POST /api/practice/sessions/:id/next-word
Body: { quality: number }  // 0-5
```

### 8.2 "Mark as Known" Button

**Placement:** Word card (right panel during practice session)

**UI Design:**
```tsx
<div className="word-card">
  <div className="word-display">
    <h2 className="character">{currentWord.word}</h2>
    <p className="pinyin">{currentWord.pinyin}</p>
    <p className="meaning">{currentWord.meaning}</p>
  </div>

  <button
    onClick={handleMarkAsMastered}
    className="mark-as-mastered-button text-sm text-sage hover:text-sage/80"
  >
    {currentWord.marked_as_known ? 'Unmark as Mastered' : '✓ Mark as Mastered'}
  </button>
</div>
```

**Behavior:**
- Always visible during practice sessions
- Button text toggles based on `marked_as_known` status:
  - If `marked_as_known === false`: shows "✓ Mark as Mastered"
  - If `marked_as_known === true`: shows "Unmark as Mastered"
- On click:
  1. Call `POST /api/words/:id/mark-as-mastered`
  2. Remove word from current session
  3. Load next word immediately (no quality rating)
  4. Show toast: "Word marked as mastered" or "Word unmarked as mastered"

**API Endpoint:**
```python
@words_bp.route('/words/<int:word_id>/mark-as-mastered', methods=['POST'])
@login_required
def toggle_mark_as_mastered(word_id):
    word = Word.get_by_id(word_id)
    if not word or word.user_id != current_user.id:
        return jsonify({'error': 'Word not found'}), 404

    if word.marked_as_known:
        unmark_word_as_mastered(word)
    else:
        mark_word_as_mastered(word)
    word.update()

    return jsonify(word.format_data()), 200
```

---

## 9. Data Migration Strategy

**Migration file structure:**
```python
def upgrade():
    # 1. Create deck table
    op.create_table('deck', ...)

    # 2. Add deck_id FK to word and SRS fields
    op.add_column('word', sa.Column('deck_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_word_deck_id', 'word', 'deck', ['deck_id'], ['id'])

    # Add SRS fields
    op.add_column('word', sa.Column('repetitions', sa.Integer(), server_default='0'))
    op.add_column('word', sa.Column('interval_days', sa.Integer(), server_default='1'))
    op.add_column('word', sa.Column('ease_factor', sa.Float(), server_default='2.5'))
    op.add_column('word', sa.Column('next_review_date', sa.Date(), nullable=True))

    # Add mastery fields
    op.add_column('word', sa.Column('last_quality', sa.Integer(), nullable=True))
    op.add_column('word', sa.Column('marked_as_known', sa.Boolean(), server_default='false'))
    op.add_column('word', sa.Column('is_mastered', sa.Boolean(), server_default='false'))

    # Drop old confidence_score field
    op.drop_column('word', 'confidence_score')

    # 3. Add deck_id FK to user_session
    op.add_column('user_session', sa.Column('deck_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_user_session_deck_id', 'user_session', 'deck', ['deck_id'], ['id'])

    # 4. Add streak fields to user_profile
    op.add_column('user_profile', sa.Column('current_streak', sa.Integer(), server_default='0'))
    op.add_column('user_profile', sa.Column('last_practice_date', sa.Date(), nullable=True))

    # 5. Data migration (idempotent)
    connection = op.get_bind()

    # Get all users who have words
    users_with_words = connection.execute(text("""
        SELECT DISTINCT user_id FROM word
    """)).fetchall()

    for (user_id,) in users_with_words:
        # Check if user already has decks (idempotent)
        existing_decks = connection.execute(text("""
            SELECT COUNT(*) FROM deck WHERE user_id = :user_id
        """), {'user_id': user_id}).scalar()

        if existing_decks == 0:
            # Create "My Words" deck
            result = connection.execute(text("""
                INSERT INTO deck (name, description, user_id, created_ds, updated_ds)
                VALUES ('My Words', 'Imported vocabulary', :user_id, NOW(), NOW())
                RETURNING id
            """), {'user_id': user_id})
            deck_id = result.scalar()

            # Assign all user's words to this deck
            connection.execute(text("""
                UPDATE word SET deck_id = :deck_id WHERE user_id = :user_id
            """), {'deck_id': deck_id, 'user_id': user_id})

def downgrade():
    # Remove columns and table in reverse order
    op.drop_column('user_profile', 'last_practice_date')
    op.drop_column('user_profile', 'current_streak')
    op.drop_constraint('fk_user_session_deck_id', 'user_session', type_='foreignkey')
    op.drop_column('user_session', 'deck_id')

    # Re-add confidence_score before dropping SRS fields
    op.add_column('word', sa.Column('confidence_score', sa.Float(), server_default='0.5'))

    # Drop SRS and mastery fields
    op.drop_column('word', 'is_mastered')
    op.drop_column('word', 'marked_as_known')
    op.drop_column('word', 'last_quality')
    op.drop_column('word', 'next_review_date')
    op.drop_column('word', 'ease_factor')
    op.drop_column('word', 'interval_days')
    op.drop_column('word', 'repetitions')

    op.drop_constraint('fk_word_deck_id', 'word', type_='foreignkey')
    op.drop_column('word', 'deck_id')
    op.drop_table('deck')
```

---

## 10. Testing Strategy

### Backend Tests

**Unit tests:**
- `Deck` model CRUD operations
- `update_streak()` logic (today, yesterday, older, null)
- `update_srs()` logic (quality 0-5, interval progression, ease_factor updates)
- `mark_word_as_known()` fast-track logic
- `Word.update_mastery_status()` (quality 5 → mastered, quality ≤3 → not mastered, quality 4 preserves)
- Deck stats computation subqueries (mastered_count, mastery_percentage)
- `POST /api/decks/combine` word copying
- SRS word selection algorithm (40% new, 60% review, buffer pools, fallback to future words)

**Integration tests:**
- `GET /api/decks` (auth, empty state, with data, stats accuracy with is_mastered, sorting)
- `POST /api/decks/:id/words` (create words in deck, SRS fields initialized correctly)
- `POST /api/practice/sessions` (require deck_id, SRS word selection 40/60 ratio)
- `POST /api/practice/sessions/:id/next-word` (accept quality param, update SRS state, update mastery)
- `POST /api/practice/sessions/:id/end` (skip remaining words, generate summary with deck_oneliner)
- `POST /api/words/:id/mark-as-known` (fast-track to 90 days, is_mastered=true)
- `GET /api/progress/streak` (return streak data)

### Frontend Tests

**Component tests:**
- `DeckListPanel` (fetch decks, render items, streak badge)
- `DeckListItem` (growth icon, recency color, progress bar)
- `DeckDetailPanel` (stats display, buttons)
- `PracticePanel` (session flow, close button, inline summary)
- `CreateDeckModal` (form validation, submit)
- `CombineDecksModal` (multi-select, info note)

### E2E Manual Tests

1. Fresh user → create deck via CSV → deck appears (🌱 seedling icon) → practice → quality rating menu appears → rate words → SRS intervals update → session end → streak incremented → laoshi_message updated → mastery % updates → growth icon changes (🌱→🌿)
2. Existing user → words migrated to "My Words" with SRS fields initialized → old sessions visible in Report Card
3. New word → "Mark as Known" button visible → click → word removed from session → next word appears → check word has 90-day interval
4. Practice session → select 40% new, 60% review words → overdue words appear first
5. Rate word quality 5 → is_mastered = true → deck mastery % increases
6. Rate word quality 3 → is_mastered = false → deck mastery % decreases
7. Mid-session close → remaining words skipped → summary shown inline
8. Mid-session deck switch → modal appears → confirm → session ends
9. Combine decks → new deck created → words copied with SRS state preserved → info note shown

---

## 11. Deployment Considerations

**Database migration:**
- Run migration during off-peak hours
- Data migration is idempotent (safe to re-run)
- Estimated time: ~1 second per 1000 users with words

**API breaking changes:**
- `POST /api/words` removed → frontend must be deployed **simultaneously** with backend
- `POST /api/practice/sessions` now requires `deck_id` → breaking change

**Deployment sequence:**
1. Run database migration
2. Deploy backend (removes old endpoints, adds new ones)
3. Deploy frontend (uses new endpoints)

**Rollback plan:**
- Downgrade migration reverts schema changes
- Old frontend will fail without old `POST /api/words` endpoint
- Requires coordinated rollback of both backend and frontend

---

## 12. Performance Considerations

**N+1 Query Prevention:**
- `GET /api/decks` uses `scalar_subquery()` for stats (single query, not N+1)
- Estimated query time: ~50ms for 50 decks with 10,000 words total

**Frontend Rendering:**
- Deck list virtualization if user has 100+ decks (unlikely but possible)
- Deck card lazy loading for growth icons (SVG components)

**Database Indexing:**
- Add index on `word.deck_id` (foreign key auto-indexed in PostgreSQL)
- Add index on `word.next_review_date` (for SRS word selection queries)
- Add index on `user_session.deck_id` (foreign key auto-indexed)

---

## 13. Security Considerations

**Authorization:**
- All deck endpoints verify `user_id` matches current user
- Deck stats computed only for current user's decks
- Cannot access other users' decks

**Input Validation:**
- Deck name: required, max 200 chars
- Deck description: optional, max 500 chars
- Laoshi message: max 500 chars (AI-generated, validated)

**Rate Limiting:**
- Existing rate limits apply (200/min default)
- No special rate limits for deck endpoints

---

This design follows the approved implementation plan and ensures a smooth transition from the old vocabulary-centric UX to the new deck-based chat-app-style interface.
