# Milestone 6: Report Card Dashboard -- Handover Document

> This document summarises the agreed plan for the Report Card feature so that another developer can pick up the work. For full details, refer to the companion documents in this folder.

---

## What We're Building

Replace the placeholder Progress page (`/progress`) with a **Report Card** dashboard. The page shows:

1. **Topline metrics** -- Time Practiced (hours), Sessions Completed, Words Practiced (distinct)
2. **Daily sentences chart** -- Recharts stacked bar chart (green = correct, red = incorrect) for the last 7 days
3. **Teacher Feedback tab** -- AI-generated holistic feedback from Laoshi, shown with avatar + italicised quote
4. **Score Breakdown tab** -- Rolling average Grammar/Usage/Naturalness scores (out of 10) with icons, template descriptions, and (i) info tooltips

---

## Key Design Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Score aggregation period | Rolling window -- last 5 completed sessions | Reflects current ability, doesn't punish early mistakes |
| Words Practiced | COUNT DISTINCT word_id (status=1) | Shows vocabulary breadth, not raw attempt count |
| Score descriptions | Static template lookup (score range → text) | Instant, zero cost, zero latency |
| Teacher feedback | New AI agent (Gemini) + mem0 + recent session summaries | Holistic, cross-session feedback in Laoshi's voice |
| Feedback trigger | Fire-and-forget POST when user clicks "Back to Home" from session summary | Doesn't block the user; feedback is ready by next Report Card visit |
| Feedback storage | `UserProfile.report_card_feedback` (Text, nullable) | Single latest assessment, overwritten each time |
| Chart library | Recharts | Most popular React charting lib, TypeScript-typed, stacked bar support |
| Chart range | Last 7 days | Digestible, matches mockup |

---

## What Already Exists (No Changes Needed)

All raw data for the Report Card is already in the database:

- **`SessionWordAttempt`** -- per-attempt `is_correct` + `created_ds` → daily chart
- **`SessionWord`** -- averaged `grammar_score`, `usage_score`, `naturalness_score`, `status` → rolling scores + words practiced
- **`UserSession`** -- `session_start_ds`, `session_end_ds`, `summary_text` → time practiced, sessions completed, recent summaries for AI agent
- **`UserProfile`** -- already has encrypted API key columns for BYOK support
- **mem0** -- already stores cross-session user preferences

---

## What Needs to Be Built

### Backend

1. **Schema**: Add `report_card_feedback` (Text, nullable) column to `UserProfile` + Alembic migration.

2. **AI Agent** (`ai_layer/`):
   - `ReportCardContext` dataclass in `context.py` (user_id, preferred_name, mem0_preferences, recent_summaries, avg scores)
   - `build_report_card_prompt()` in `chat_agents.py` -- teacher persona, JSON output `{"feedback": string}`
   - `report_card_agent` (Gemini) + `build_report_card_agent(gemini_api_key=None)` for BYOK

3. **Business logic** (`report_card_service.py` -- new file):
   - `get_topline_metrics(user_id)` → `{time_practiced_hours, sessions_completed, words_practiced}`
   - `get_daily_chart_data(user_id)` → 7 entries of `{date, correct, incorrect}`
   - `get_rolling_scores(user_id)` → `{grammar, usage, naturalness}` averages from last 5 sessions
   - `get_score_description(score_type, score)` → template text lookup
   - `generate_report_card_feedback(user_id)` → run AI agent, store result

4. **Endpoints** (`report_card_resources.py` -- new file):
   - `GET /api/progress/report-card` → returns all report card data in one response
   - `POST /api/progress/generate-feedback` → triggers AI feedback generation
   - Register both in `app.py`

### Frontend

5. **Install**: `npm install recharts`

6. **Types** (`types/api.ts`): Add `ReportCardData`, `ReportCardTopline`, `DailyChartData`, `ScoreDetail`, `ScoreBreakdown`

7. **API helpers** (`lib/api.ts`): Add `progressApi.getReportCard()` and `progressApi.generateFeedback()`

8. **Page rewrite** (`Progress.tsx`):
   - Header: bar chart icon + "Report Card"
   - Topline metrics: 3 cards in a row
   - Recharts stacked bar chart (green/red, DD/MM dates, 7 days)
   - Tabs: Teacher Feedback (avatar + quote) and Score Breakdown (3 cards with purple icons, scores, descriptions, info tooltips)
   - Empty states for new users

9. **Integration**:
   - `SessionSummary.tsx`: fire-and-forget `progressApi.generateFeedback()` on "Back to Home" click
   - `Sidebar.tsx`: rename "Progress" → "Report Card" (keep `/progress` route)

### Testing

10. **Unit tests** (`test_report_card_service.py`): topline, chart, rolling scores, descriptions
11. **Integration tests** (`test_report_card.py`): auth, empty state, populated state, rolling window, chart shape
12. **E2E manual test**: complete session → exit → check Report Card

---

## Score Breakdown Visual Spec

Each of the 3 score cards has:
- **Purple icon**: Grammar = document/notepad, Usage = speech bubble, Naturalness = smiley face
- **Large score**: `X.X/10` (or `--/10` if null)
- **Label**: "Grammar", "Usage", "Naturalness"
- **(i) button**: toggles tooltip explaining what the score measures
- **Description**: template text based on score range

Score description ranges:
| Range | Grammar | Usage | Naturalness |
|-------|---------|-------|-------------|
| 1-3 | Needs significant work on structure... | Needs significant work on meaning... | Sentences sound translated... |
| 4-5 | Developing grammar skills... | Developing word usage... | Developing naturalness... |
| 6-7 | Solid grammar... | Good word usage... | Reasonably natural... |
| 8-9 | Strong grammar... | Strong word usage... | Strong natural expression... |
| 10 | Excellent grammar... | Excellent word usage... | Excellent naturalness... |

Info tooltip content:
- **Grammar**: word order, particles, verb aspect, measure words
- **Usage**: correct meaning, context, collocations
- **Naturalness**: native-like expression, idiomatic usage

---

## API Response Shape

```json
GET /api/progress/report-card
{
  "topline": {
    "time_practiced_hours": 12.5,
    "sessions_completed": 24,
    "words_practiced": 892
  },
  "chart_data": [
    {"date": "2026-02-27", "correct": 5, "incorrect": 3},
    ...7 entries total
  ],
  "score_breakdown": {
    "grammar": {"score": 6.0, "description": "Solid grammar..."},
    "usage": {"score": 8.0, "description": "Strong word usage..."},
    "naturalness": {"score": 7.0, "description": "Reasonably natural..."}
  },
  "teacher_feedback": "Your grammar is getting tighter every session..."
}
```

Empty state: zeros for topline, 7 zero entries for chart, null scores/descriptions, null feedback.

---

## Implementation Order

```
Phase 1: Schema (T-6.1, T-6.2)
Phase 2: AI Agent (T-6.3 → T-6.4 → T-6.5)     ← can parallel with Phase 1
Phase 3: Business Logic (T-6.6-T-6.10)           ← after Phase 1+2
Phase 4: Endpoints (T-6.11 → T-6.12 → T-6.13)   ← after Phase 3
Phase 5: Frontend (T-6.14-T-6.25)                ← after Phase 4 (install/types can start earlier)
Phase 6: Testing (T-6.26-T-6.28)                 ← after all above
```

Backend and frontend install/types can be parallelised. See `tasks.md` for full dependency graph.

---

## Files Changed / Created

| File | Action |
|------|--------|
| `backend/models.py` | Add column to UserProfile |
| `backend/migrations/versions/` | New migration |
| `backend/ai_layer/context.py` | Add ReportCardContext |
| `backend/ai_layer/chat_agents.py` | Add prompt builder, agent, BYOK builder |
| `backend/report_card_service.py` | **New file** -- all business logic |
| `backend/report_card_resources.py` | **New file** -- API endpoints |
| `backend/app.py` | Register new routes |
| `frontend/package.json` | Add recharts dependency |
| `frontend/src/types/api.ts` | Add 5 interfaces |
| `frontend/src/lib/api.ts` | Add 2 methods to progressApi |
| `frontend/src/pages/Progress.tsx` | Full rewrite |
| `frontend/src/components/SessionSummary.tsx` | Add onClick handler |
| `frontend/src/components/Sidebar.tsx` | Rename label |
| `backend/tests/test_report_card_service.py` | **New file** -- unit tests |
| `backend/tests/test_report_card.py` | **New file** -- integration tests |

---

## Reference Documents

| Document | Purpose |
|----------|---------|
| `.claudedocs/m6-report-card/requirements.md` | User stories, functional requirements, acceptance criteria, API specs |
| `.claudedocs/m6-report-card/design.md` | Technical architecture, data model, queries, data flow diagrams, frontend layout |
| `.claudedocs/m6-report-card/tasks.md` | Granular task breakdown with dependencies and execution order |
| `.claude/PROJECT_PLAN.md` | Milestone 6 task checklist (high-level) |
| `.claude/PRD.md` | Product requirements (section 4.3, user story #16, AI strategy 6.1) |
| `.claude/plans/wiggly-gliding-cerf.md` | Original plan file from planning session |
