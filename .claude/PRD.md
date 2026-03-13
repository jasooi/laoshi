# Laoshi - Product Requirements Document

## 1. Product Overview

Laoshi is a free, community-driven Mandarin learning web app that helps intermediate learners develop a natural command of the language through AI-coached sentence formation practice. Unlike flashcard apps that encourage rote memorisation, Laoshi focuses on active usage — learners build sentences with vocabulary words and receive real-time feedback on naturalness, correctness, and word choice from an AI coach powered by Chinese-native language models.

## 2. Problem Statement

Existing language learning tools leave intermediate Mandarin learners underserved in three key ways:

### Gap 1: Rote memorisation does not build fluency
Flashcard-based apps show a word's definition and ask learners to memorise it. Words are learnt in isolation, never actively used in context. This makes it easy to score on exams but impairs real-world fluency — learners recognise words but struggle to produce natural sentences with them.

### Gap 2: English-Chinese semantic mismatch
English words tend to have broad definitions, while Mandarin words are more specific. A single English word (e.g. "open") may map to several Chinese translations (打开, 开放, 展开, 开设), each correct only in certain contexts. When learners look up a word in the dictionary, they are confronted with multiple options that have similar English glosses. Without guidance, they frequently pick a word that seems right based on the English definition but sounds clearly wrong to a native speaker.

### Gap 3: No tools for intermediate learners
Most language learning apps target complete beginners with basic grammar drills and vocabulary. Intermediate learners — those who already grasp grammar rules and have a sizeable vocabulary but cannot yet speak their thoughts fluently and naturally — need more challenging exercises that go beyond fundamentals.

## 3. Target Audience

- **English-speaking adults** learning Mandarin as a second language
- **Professionals and expats** who need Mandarin for work or daily life in Chinese-speaking environments
- **Intermediate-level learners** who understand grammar and have foundational vocabulary, but want to improve naturalness and fluency
- **Self-directed learners** who want structured practice outside of a classroom setting

## 4. Core Features

### 4.1 Vocabulary Management & Decks
Vocabulary is organised into **decks** — themed collections of words that learners practice together. Each word belongs to exactly one deck.

- **Deck Creation**: Learners create decks with a name and description, then populate them via CSV import, manual word addition, or by combining words from existing decks (words are copied, not linked)
- **CSV Import**: Upload vocabulary from CSV files directly into a deck (2-step: create deck, then upload words)
- **Pre-defined Library** *(deferred to future milestone)*: Import curated vocabulary sets from the Laoshi database
- **Deck Combining**: Select words from one or more existing decks to create a new deck. An info note informs users that copied words are independent of the originals.
- **Word Details**: Each word entry includes Chinese characters, pinyin, and English definition
- **CRUD Operations**: Add, edit, and delete individual words within a deck. Deleting a deck cascade-deletes its words.
- **Library Page**: A dedicated page (replacing the previous Vocabulary page) for browsing, creating, and managing decks and their words

### 4.2 Home Screen & Deck-Based Navigation
The home screen uses a **chat-app-style split-panel layout** (inspired by WhatsApp/Telegram web) to create a friendly, inviting interface where studying feels like chatting with a friend.

- **Left Panel — Deck List**: All of the learner's decks, sorted by reverse recency (least recently practiced first, to create urgency). Each deck shows:
  - **Growth Icon**: 🌱 Seedling (0–24% mastered), 🌿 Leaves (25–74% mastered), or 🌸 Flower (75–100% mastered), representing vocabulary mastery growth
  - **Recency Colour**: Green (practiced <48h ago), yellow (48–120h), red (>120h), muted grey (never practiced) — applied to both the icon and progress bar
  - **Progress Bar**: Visual mastery progress (mastered words / total words)
  - **Word Count**: e.g. "34/120"
  - **Laoshi Message Preview**: AI-generated one-liner about the deck's progress (truncated)
  - **"+ New Deck"** button at bottom → navigates to the Library page
- **Right Panel — Deck Detail**: When a deck is selected, shows:
  - Circular progress ring, deck name, total/mastered word counts
  - Full Laoshi message in a quote box
  - "Start Practice" and "Manage in Library →" action buttons
- **Right Panel — Empty State**: When no deck is selected, shows the Laoshi avatar, "Select a deck to begin", and the day streak counter
- **Day Streak**: Tracks consecutive days with at least one completed practice session. Displayed as a badge on the home screen.

### 4.3 AI-Coached Practice Sessions (Inline)
The centrepiece of Laoshi. Practice sessions appear **inline in the home screen's right panel** (like opening a chat in WhatsApp web), reinforcing the conversational feel. The AI coach ("Laoshi") has a consistent sassy-but-encouraging teacher persona and guides the learner through practice sessions using a multi-agent architecture.

**Starting a session:** The learner selects a deck from the left panel, then clicks "Start Practice" on the deck detail view. Words are selected using a **Spaced Repetition System (SRS)** — 40% new words (never reviewed) and 60% words due for review (based on learning intervals), with the most overdue words prioritized first.

**During a session**, the system presents vocabulary words one at a time. For each word, the learner can:
- Submit one or more practice sentences for evaluation (multiple attempts allowed)
- Chat freely with Laoshi (ask questions, discuss goals, ask about the word or prior feedback)
- Click "Mark as Known" to fast-track words they already know (removes from session, schedules for 90-day review)
- Click "Next Word" to advance to the next word

The coach evaluates each submitted sentence for:
- Grammatical correctness (1-10)
- Word usage accuracy (1-10)
- Naturalness (1-10) -- does it sound like something a native speaker would say?
- The coach provides persona-toned feedback, corrections, explanations, and example sentences.

**Current word display:** A collapsible panel on the right side of the chat shows only the current word (character, pinyin, meaning). Practiced and skipped word lists are no longer displayed during the session.

**Multi-attempt scoring:** When the learner clicks "Next Word", the system averages all attempt scores for that word. A word is considered correctly practiced when the averaged grammar score is 10 and averaged usage score is >= 8. If the word was never attempted (no sentences submitted), clicking "Next Word" counts it as skipped.

**Quality self-rating:** After clicking "Next Word", the learner rates their understanding of the word (0-5 scale from "I don't understand" to "Perfect command"). This rating updates the word's review schedule using the SM-2 spaced repetition algorithm — words rated highly appear less frequently, while words rated poorly appear sooner for reinforcement.

**Early exit:** A close button (top right) ends the session immediately -- remaining unpracticed words are marked as skipped and the session summary is shown. If the learner clicks a different deck while a session is active, a confirmation modal asks whether to end the current session.

**Session end:** The session ends when all words have been either attempted or skipped, or when the learner closes the session early. At session end, the coach produces:
1. A summary with 2 specific positives and 1 area for improvement, drawn from actual session content
2. A **deck one-liner** -- a short AI-generated message about the deck's progress and what to focus on next (displayed on the deck's card in the left panel)

The system also updates persistent user memory (mem0) with learning patterns observed during the session, and updates the learner's day streak.

**Persistent memory:** Laoshi remembers user preferences, learning patterns, and study style across sessions via mem0 (cross-session memory). This enables personalised coaching that adapts over time.

The number of words per session is configurable (default 10, user-settable via Settings).

### 4.4 Progress Tracking
- **Home Page Stats**: At-a-glance summary including words practiced today, mastery level percentage, and words ready for review
- **Report Card**: A detailed dashboard showing the learner's overall progress and performance:
  - **Topline Metrics**: Time practiced (hours), sessions completed, and distinct words practiced
  - **Daily Sentence Chart**: Stacked bar chart showing correct vs incorrect sentences formed per day over the last 7 days
  - **Teacher Feedback**: AI-generated report card feedback quip from the Laoshi persona, based on mem0 memories and recent session performance. Generated when the learner exits a completed session and displayed alongside the teacher's avatar.
  - **Score Breakdown**: Rolling average scores (last 5 sessions) for Grammar, Usage, and Naturalness (each out of 10), with info buttons explaining what each score measures and template-based descriptions of the learner's current level
- **Spaced Repetition & Mastery**: Words are scheduled for review using the SM-2 spaced repetition algorithm. Each word has a dynamic **mastery status** based on the learner's quality self-ratings:
  - A word becomes "mastered" when rated quality 5 (perfect command)
  - Mastery is removed if rated quality 3 or below (struggling)
  - Quality 4 (good grasp) preserves existing mastery state
  - Words marked as "already known" via the "Mark as Known" button are immediately mastered and scheduled for long-interval review (90 days)
  - The deck's growth icon (🌱🌿🌸) reflects the percentage of mastered words, providing visual motivation as learners progress

### 4.5 BYOK (Bring Your Own API Key)
Laoshi provides free-tier API keys by default for the AI coach. Users can input their own API key in Settings so that the app continues to work if the default keys reach their usage limits.

### 4.6 Saved Sentences
Learners can save correct sentences they have constructed during practice to a word, creating a personal reference library of natural Mandarin sentences they have produced.

### 4.7 Contextual Hints (Future Phase)
Attach images and personal notes to words as memory aids that trigger recall through association rather than explicit definition. For example:
- A photo of a billboard with 销售 that the learner sees on their commute
- A note like "Tom's favourite vegetable" attached to 芥兰

## 5. User Stories

### Onboarding & Account
1. As a new user, I want to register an account and log in so that my vocabulary and progress are saved.
2. As a new user, I want a guided onboarding experience that helps me upload my first vocabulary set and start practicing quickly.

### Vocabulary Management
3. As a learner, I want to upload a CSV file of vocabulary so that I can practice with words I am currently studying.
4. As a learner, I want to browse and import pre-defined vocabulary sets from the Laoshi library so that I can start practicing without preparing my own word lists.
5. As a learner, I want to create custom collections (e.g. "Business Mandarin") and organise my words into them so that I can practice contextually related vocabulary together.
6. As a learner, I want to search, filter, and sort my vocabulary list so that I can quickly find specific words.
7. As a learner, I want to edit or delete words from my vocabulary so that I can keep my word lists accurate and relevant.

### Practice Sessions
8. As a learner, I want to select a collection and start a practice session so that I can practice words in a specific context.
9. As a learner, I want the AI coach to show me a word on a flashcard and prompt me to form a sentence using it, so that I actively practice producing natural Mandarin.
10. As a learner, I want the AI coach to evaluate my sentence and tell me whether it sounds natural to a native speaker, so that I learn correct usage rather than just correct grammar.
11. As a learner, I want to receive detailed feedback including corrections, explanations, and example sentences so that I understand my mistakes and learn the right way to express my thoughts.
12. As a learner, I want to skip a word during a session if I am not ready to practice it yet, so that I can focus on words I feel more prepared for.
13. As a learner, I want to toggle pinyin and English definitions on the flashcard so that I can challenge myself at different difficulty levels.
14. As a learner, I want to save sentences I constructed correctly to the word, so that I can refer to them as examples in the future.

### Progress & Motivation
15. As a learner, I want to see my learning statistics on the home page (words practiced today, mastery percentage, words ready for review) so that I stay motivated.
16. As a learner, I want a Report Card page showing topline practice metrics, a daily sentence chart (correct vs incorrect), AI-generated teacher feedback, and a score breakdown (grammar, usage, naturalness) so that I can track improvement and identify weak areas.
17. As a learner, I want to rate how well I understand each word after practicing it (quality 0-5 self-rating), so that the system can schedule reviews at optimal intervals using spaced repetition and I can focus on words that need reinforcement.

### Settings
18. As a learner, I want to configure how many words are practiced per session so that I can adjust sessions to my available time and energy.
19. As a learner, I want to input my own API key for the AI coach so that I can continue practicing if the default free-tier keys are exhausted.

### Future Phase Stories
20. As a learner, I want to attach photos and personal notes to words as memory hints so that I can build stronger mental associations and recall words more easily.

## 6. AI Strategy

### 6.1 Multi-Agent Architecture
Laoshi uses a multi-agent system built on the OpenAI Agents SDK:

- **Orchestrator Agent** (Gemini Flash): Primary agent with sassy teacher persona. Classifies user intent (sentence attempt vs chat/question), responds to chat directly, calls the Feedback Agent as a tool for sentence evaluation, and hands off to the Summary Agent at session end.
- **Feedback Agent** (DeepSeek): Agent-as-tool. Evaluates sentences for grammar, usage, and naturalness. Returns structured JSON scores. Stateless -- receives only the current sentence and target word. DeepSeek is used for its strong Mandarin evaluation capabilities.
- **Summary Agent** (Gemini Flash): Handoff agent activated at session end. Reads the full conversation history and produces a session summary with mem0 update recommendations.
- **Report Card Agent** (Gemini Flash): Standalone agent triggered when the learner exits a completed session. Reads mem0 memories and recent session data to produce a short (2-3 sentence) report card feedback quip in Laoshi's voice. Stored on UserProfile for display on the Report Card page.

### 6.2 Design Principles
- Agents reason; app code manages all data. No agent has direct database or memory-store tools.
- Session state (word counter, completion) is tracked deterministically in app code, never by the LLM.
- All writes to PostgreSQL and mem0 happen in app code after agent output is returned.
- Persona tone is baked into agent system prompts, not applied by a separate tone agent.
- Defensive score extraction: app code takes scores from the feedback agent's raw tool output, not from the orchestrator's text response.

### 6.3 Persistent Memory (mem0)
Cross-session memory stores user preferences, learning patterns, and study style observations. Memory is read at session start (injected into agent context) and written at session end (based on Summary Agent recommendations). Per-turn updates are avoided to prevent noisy, low-signal entries.

### 6.4 Model Selection
- **DeepSeek** (`deepseek-chat`): Used for the Feedback Agent -- chosen for its strong understanding of Mandarin nuance, natural phrasing, and cultural context
- **Gemini Flash** (`gemini-2.5-flash`): Used for the Orchestrator and Summary agents -- chosen for speed in conversational responses
- **Default Access**: Free-tier API keys provided by the app for both models
- **BYOK Fallback**: Users can supply their own API key in Settings when default keys reach usage limits (future milestone)
- **Evaluation Criteria**: The AI coach assesses sentences on grammar (1-10), word usage accuracy (1-10), and naturalness (1-10) -- it does not merely check for correctness but evaluates whether the sentence sounds like something a native speaker would actually say

## 7. MVP Scope (Phase 1)

The minimum viable product includes:

| Feature | Description |
|---|---|
| Registration & Login | User account creation and JWT-based authentication |
| CSV Vocabulary Import | Upload vocabulary from a CSV file |
| Vocabulary List View | Browse, search, sort, edit, and delete words |
| Practice Sessions | AI-coached chat sessions with flashcard-based word prompts |
| Configurable Session Length | Setting to control how many words per session |
| Home Page Statistics | Today's progress, mastery level, words ready for review |
| BYOK API Key | Setting to input a personal API key |

## 8. Future Roadmap

| Phase | Features |
|---|---|
| Phase 2 | Report Card dashboard, custom collections, pre-defined vocabulary sets from Laoshi library |
| Phase 3 | Saved sentences, advanced SRS features (leeches detection, custom ease factors), community-contributed vocabulary sets |
| Phase 4 | Contextual hints (images and notes on words), voice chat for spoken sentence practice |

## 9. Success Metrics

Since Laoshi is a free community tool, success is measured by engagement, retention, and learning outcomes rather than revenue.

| Metric | Description |
|---|---|
| Weekly Active Users | Number of users who complete at least one practice session per week |
| Session Completion Rate | % of started practice sessions that are completed (not abandoned) |
| Words Mastered | Average number of words achieving mastered status (quality 5 rating) per user |
| Return Rate | % of users who return for a second session within 7 days of their first |
| Vocabulary Growth | Average number of words added per user over time |
| Mastery Progression | Average time (in days) and number of practice repetitions for a word to achieve mastered status |
| User Satisfaction | Qualitative feedback from the community on naturalness of AI feedback |
