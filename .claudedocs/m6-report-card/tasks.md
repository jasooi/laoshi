# Milestone 6: Report Card Dashboard -- Task Breakdown

## Task Overview

**Total tasks**: 28 tasks (6.1-6.28) across 6 phases
**Phases are sequential**: each phase depends on the previous one. Within a phase, tasks can be parallelised where noted.

---

## Prerequisites

Before starting any tasks:

1. Ensure Milestone 4 is complete and all M4 tests pass.
2. Ensure the backend virtual environment is active and `backend/requirements.txt` dependencies are installed.
3. Ensure `npm install` has been run in `frontend/`.
4. Ensure PostgreSQL is running and `DATABASE_URI` in `.env` is valid.
5. Ensure Redis is running and `REDIS_URI` is set in `.env`.
6. Ensure existing tests pass: `cd backend && python -m pytest tests/ -v` and `cd frontend && npm test -- --run`.

---

## Phase 1: Backend Schema

One new column on an existing model. No endpoint or frontend changes.

---

### T-6.1: Add report_card_feedback column to UserProfile

**Description**: Add a nullable Text column to `UserProfile` for storing the latest AI-generated report card feedback.

**Files affected**:
- `backend/models.py` -- add column to `UserProfile` class

**Changes**:

Add to `UserProfile` class (after existing columns):
```python
report_card_feedback = db.Column(db.Text, nullable=True)
```

**Acceptance criteria**:
- `UserProfile` model has `report_card_feedback` column.
- Column is nullable (no default value needed).
- Existing tests pass (column is optional, no impact on existing code).

**Dependencies**: None.

---

### T-6.2: Run Alembic migration

**Description**: Generate and run migration for the new column.

**Steps**:
1. `flask db migrate -m "add_report_card_feedback_to_user_profile"`
2. Review generated migration file.
3. `flask db upgrade`

**Acceptance criteria**:
- Migration runs without errors.
- `user_profile` table has `report_card_feedback` column.
- Existing data is unaffected.

**Dependencies**: T-6.1.

---

## Phase 2: AI Agent

New context dataclass and agent definition. Can be done in parallel with Phase 1.

---

### T-6.3: Add ReportCardContext dataclass

**Description**: Create a new context dataclass for the report card agent, separate from `UserSessionContext`.

**Files affected**:
- `backend/ai_layer/context.py` -- add new dataclass

**Changes**:

Add after existing dataclasses:
```python
@dataclass
class ReportCardContext:
    user_id: int
    preferred_name: str
    mem0_preferences: str | None
    recent_summaries: str | None
    avg_grammar: float
    avg_usage: float
    avg_naturalness: float
```

**Acceptance criteria**:
- `ReportCardContext` importable from `ai_layer.context`.
- Has all 7 fields with correct types.
- Does NOT inherit from or modify `UserSessionContext`.

**Dependencies**: None (independent).

---

### T-6.4: Add report card prompt builder

**Description**: Add `build_report_card_prompt()` to `chat_agents.py`. The prompt instructs the agent to write a 2-3 sentence feedback quip in Laoshi's voice.

**Files affected**:
- `backend/ai_layer/chat_agents.py` -- add function

**Changes**:

Add prompt builder function (see design.md section 2.2 for full implementation). Key points:
- Teacher persona (sassy, encouraging, specific).
- Inputs: mem0 memories wrapped in `[DATA]` tags, recent session summaries wrapped in `[DATA]` tags, rolling average scores.
- Output: JSON `{"feedback": string}`.
- Security rules: data tags treated as data only.

**Acceptance criteria**:
- Function signature: `build_report_card_prompt(ctx_wrapper, agent) -> str`.
- Prompt includes mem0 section (conditional), summaries section (conditional), scores.
- User-supplied data wrapped in `[DATA]...[/DATA]` tags.
- Returns valid prompt string.

**Dependencies**: T-6.3 (uses ReportCardContext fields).

---

### T-6.5: Add report_card_agent and BYOK builder

**Description**: Define the module-level `report_card_agent` and a `build_report_card_agent()` factory for BYOK.

**Files affected**:
- `backend/ai_layer/chat_agents.py` -- add agent + function

**Changes**:

Add after existing agent definitions:
```python
from ai_layer.context import ReportCardContext

report_card_agent = Agent[ReportCardContext](
    name="report_card_agent",
    instructions=build_report_card_prompt,
    model=gemini_model
)

def build_report_card_agent(gemini_api_key=None):
    if not gemini_api_key:
        return report_card_agent
    custom_client = AsyncOpenAI(base_url=GEMINI_BASE_URL, api_key=gemini_api_key)
    custom_model = OpenAIChatCompletionsModel(model=GEMINI_MODEL_NAME, openai_client=custom_client)
    return Agent[ReportCardContext](
        name="report_card_agent",
        instructions=build_report_card_prompt,
        model=custom_model
    )
```

**Acceptance criteria**:
- `report_card_agent` exists at module level using Gemini model.
- `build_report_card_agent()` with no args returns default agent.
- `build_report_card_agent(gemini_api_key="...")` returns a custom agent.
- Agent uses `ReportCardContext` type parameter.

**Dependencies**: T-6.4 (prompt builder).

---

## Phase 3: Backend Business Logic

New service file with all business logic functions. Depends on Phase 1 (schema) and Phase 2 (agent).

---

### T-6.6: Create report_card_service.py with topline metrics

**Description**: Create the new service file and implement `get_topline_metrics(user_id)`.

**Files affected**:
- `backend/report_card_service.py` -- new file

**Changes**:

Implement `get_topline_metrics()` (see design.md section 3.1):
- `time_practiced_hours`: SUM of session durations, converted to hours, rounded to 1 decimal.
- `sessions_completed`: COUNT of completed sessions.
- `words_practiced`: COUNT DISTINCT word_id from completed SessionWords.
- Returns dict with all three metrics (zeros if no data).

**Acceptance criteria**:
- Returns `{time_practiced_hours: 0, sessions_completed: 0, words_practiced: 0}` for new users.
- Correctly sums session durations for time metric.
- Only counts completed sessions (session_end_ds IS NOT NULL).
- Only counts distinct word_ids with status=1 for words metric.

**Dependencies**: T-6.1 (schema, but only for import consistency -- function doesn't use new column).

---

### T-6.7: Add daily chart data function

**Description**: Implement `get_daily_chart_data(user_id)` in the service file.

**Files affected**:
- `backend/report_card_service.py` -- add function

**Changes**:

Implement `get_daily_chart_data()` (see design.md section 3.2):
- Query SessionWordAttempt grouped by DATE(created_ds).
- Filter by user via UserSession join.
- Filter to last 7 days.
- Fill missing days with zeros.
- Always return exactly 7 entries in chronological order.

**Acceptance criteria**:
- Always returns exactly 7 dict entries.
- Each entry has `{date, correct, incorrect}`.
- Dates are in ISO format (YYYY-MM-DD).
- Days with no attempts have `correct: 0, incorrect: 0`.
- Only includes user's own data (filtered by user_id via session join).

**Dependencies**: T-6.6 (same file, shared imports).

---

### T-6.8: Add rolling scores function

**Description**: Implement `get_rolling_scores(user_id)` in the service file.

**Files affected**:
- `backend/report_card_service.py` -- add function

**Changes**:

Implement `get_rolling_scores()` (see design.md section 3.3):
- Get last 5 completed session IDs.
- AVG grammar/usage/naturalness from SessionWord where status=1 in those sessions.
- Falls back to all completed sessions if fewer than 5.
- Returns None values if no data at all.
- Round averages to 1 decimal.

**Acceptance criteria**:
- Returns `{grammar: None, usage: None, naturalness: None}` for new users.
- With < 5 sessions, averages across all available sessions.
- With 5+ sessions, only uses last 5 (by session_end_ds DESC).
- Excludes skipped words (status != 1) and words with NULL scores.
- Scores rounded to 1 decimal place.

**Dependencies**: T-6.6 (same file).

---

### T-6.9: Add score description templates

**Description**: Implement `get_score_description(score_type, score)` with template mappings.

**Files affected**:
- `backend/report_card_service.py` -- add dict + function

**Changes**:

Add `SCORE_DESCRIPTIONS` dictionary and `get_score_description()` function (see design.md section 3.4):
- Three score types: grammar, usage, naturalness.
- Five ranges per type: 1-3, 4-5, 6-7, 8-9, 10.
- Returns None if score is None.

**Acceptance criteria**:
- All 15 descriptions (5 ranges x 3 types) are defined.
- `get_score_description('grammar', 7.2)` returns the 6-7 range grammar description.
- `get_score_description('usage', None)` returns None.
- Scores are rounded before range lookup.

**Dependencies**: None (independent utility, can run in parallel with T-6.6-T-6.8).

---

### T-6.10: Add feedback generation function

**Description**: Implement `generate_report_card_feedback(user_id)` that runs the AI agent and stores the result.

**Files affected**:
- `backend/report_card_service.py` -- add async function

**Changes**:

Implement `generate_report_card_feedback()` (see design.md section 3.5):
1. Load user + profile.
2. Fetch mem0 memories.
3. Fetch last 3 session summaries.
4. Get rolling scores.
5. Check for BYOK Gemini key → `build_report_card_agent()`.
6. Build `ReportCardContext`, run agent.
7. Parse JSON output, store in `profile.report_card_feedback`.
8. On failure: store static fallback message, log error.

**Acceptance criteria**:
- Successfully generates and stores feedback when agent succeeds.
- Falls back to static message when agent fails.
- Uses custom Gemini key if available (BYOK).
- Fetches mem0 memories and recent summaries.
- Stores result in UserProfile.report_card_feedback column.
- Never raises uncaught exceptions.

**Dependencies**: T-6.1 (report_card_feedback column), T-6.5 (report_card_agent), T-6.8 (rolling scores).

---

## Phase 4: Backend Endpoints

New API resources. Depends on Phase 3 (business logic).

---

### T-6.11: Create GET /api/progress/report-card endpoint

**Description**: Create `report_card_resources.py` with the main report card endpoint.

**Files affected**:
- `backend/report_card_resources.py` -- new file

**Changes**:

Create `ReportCardResource` class:
- `@jwt_required()` on GET.
- Calls `get_topline_metrics()`, `get_daily_chart_data()`, `get_rolling_scores()`, `get_score_description()`.
- Reads `report_card_feedback` from UserProfile.
- Returns combined JSON response (see design.md section 4.1).

**Acceptance criteria**:
- JWT-protected (401 without token).
- Returns correct JSON shape with all sections.
- Empty state returns zeros/nulls (not errors).
- Score descriptions are populated when scores exist.
- Teacher feedback is null when no feedback stored.

**Dependencies**: T-6.6 through T-6.9 (all service functions).

---

### T-6.12: Create POST /api/progress/generate-feedback endpoint

**Description**: Add the feedback generation trigger endpoint.

**Files affected**:
- `backend/report_card_resources.py` -- add resource class

**Changes**:

Create `GenerateFeedbackResource` class:
- `@jwt_required()` on POST.
- Calls `generate_report_card_feedback(user_id)`.
- Returns `{"feedback": "..."}`.

Note: This is an async endpoint (calls async agent). Use `run_async()` pattern from existing practice resources if needed, or `asyncio.run()`.

**Acceptance criteria**:
- JWT-protected (401 without token).
- Returns generated feedback text.
- Handles agent failures gracefully (returns fallback).

**Dependencies**: T-6.10 (feedback generation function).

---

### T-6.13: Register routes in app.py

**Description**: Import and register both new resources.

**Files affected**:
- `backend/app.py` -- add imports and routes

**Changes**:

```python
from report_card_resources import ReportCardResource, GenerateFeedbackResource

# In register_resources():
api.add_resource(ReportCardResource, '/progress/report-card')
api.add_resource(GenerateFeedbackResource, '/progress/generate-feedback')
```

**Acceptance criteria**:
- Both routes registered.
- App starts without import errors.
- `flask routes` shows both new endpoints.

**Dependencies**: T-6.11, T-6.12.

---

## Phase 5: Frontend

Complete page rewrite + integration. Depends on Phase 4 (working endpoints).

---

### T-6.14: Install Recharts

**Description**: Install the Recharts charting library as a frontend dependency.

**Commands**:
```bash
cd frontend && npm install recharts
```

**Acceptance criteria**:
- `recharts` appears in `package.json` dependencies.
- `npm run build` succeeds.

**Dependencies**: None (can run anytime).

---

### T-6.15: Add TypeScript interfaces

**Description**: Add Report Card type interfaces to the frontend type definitions.

**Files affected**:
- `frontend/src/types/api.ts` -- add interfaces

**Changes**:

Add interfaces (see design.md section 5.2):
- `ReportCardTopline`
- `DailyChartData`
- `ScoreDetail`
- `ScoreBreakdown`
- `ReportCardData`

**Acceptance criteria**:
- All 5 interfaces exported.
- TypeScript compiles without errors.
- Types match the API response shape from design.md.

**Dependencies**: None (can run anytime).

---

### T-6.16: Add API helpers

**Description**: Add `getReportCard()` and `generateFeedback()` to the `progressApi` object.

**Files affected**:
- `frontend/src/lib/api.ts` -- add methods to progressApi

**Changes**:

Extend `progressApi`:
```typescript
export const progressApi = {
  getStats: () => api.get<ProgressStats>('/api/progress/stats'),
  getReportCard: () => api.get<ReportCardData>('/api/progress/report-card'),
  generateFeedback: () => api.post('/api/progress/generate-feedback'),
}
```

Import `ReportCardData` from types.

**Acceptance criteria**:
- Both new methods exist on `progressApi`.
- TypeScript compiles without errors.

**Dependencies**: T-6.15 (types).

---

### T-6.17: Rewrite Progress.tsx -- header and data fetching

**Description**: Replace the placeholder Progress page with the Report Card header and data fetching logic.

**Files affected**:
- `frontend/src/pages/Progress.tsx` -- rewrite

**Changes**:

- Replace placeholder with Report Card header (bar chart icon + "Report Card" title).
- Add state: `reportCard`, `loading`, `activeTab`.
- Add `useEffect` that calls `progressApi.getReportCard()` on mount.
- Add loading spinner while data loads.
- Add full-page empty state if no sessions exist (sessions_completed === 0 and no chart data).

**Acceptance criteria**:
- Header shows bar chart icon and "Report Card" title.
- Data fetches on mount and populates state.
- Loading state shown during fetch.
- Empty state shown for new users.
- No traces of old placeholder remain.

**Dependencies**: T-6.16 (API helpers).

---

### T-6.18: Add topline metrics row

**Description**: Render the three topline metric cards.

**Files affected**:
- `frontend/src/pages/Progress.tsx` -- add section

**Changes**:

Add a 3-column grid row with cards for:
1. **Time Practiced**: clock icon, hours value, "hours" label.
2. **Sessions Completed**: checkmark icon, count value, "sessions" label.
3. **Words Practiced**: book icon, count value, "words" label.

Follow existing card styling from Home.tsx (bg-white, rounded-2xl, shadow-sm, border).

**Acceptance criteria**:
- Three cards render in a row.
- Each shows correct value from `reportCard.topline`.
- Follows existing Tailwind design system.
- Shows 0 values gracefully for new users.

**Dependencies**: T-6.17 (page structure + data).

---

### T-6.19: Add stacked bar chart

**Description**: Render the Recharts stacked bar chart for daily sentence data.

**Files affected**:
- `frontend/src/pages/Progress.tsx` -- add chart section

**Changes**:

Add Recharts BarChart (see design.md section 5.5):
- Green bars for correct, red bars for incorrect, stacked.
- X-axis: date in DD/MM format.
- Y-axis: integer sentence count.
- Wrapped in ResponsiveContainer.
- Chart title: "Daily Sentences" or similar.

**Acceptance criteria**:
- Chart renders with correct/incorrect stacked bars.
- X-axis shows DD/MM date labels for 7 days.
- Y-axis shows integer counts.
- Colors: green (#22c55e) for correct, red (#ef4444) for incorrect.
- Chart renders gracefully with all-zero data.

**Dependencies**: T-6.14 (Recharts installed), T-6.17 (data available).

---

### T-6.20: Add tab section

**Description**: Add the tabbed section with Teacher Feedback and Score Breakdown tabs.

**Files affected**:
- `frontend/src/pages/Progress.tsx` -- add tab section

**Changes**:

Add tab UI:
- Two tab buttons: "Teacher Feedback" and "Score Breakdown".
- `activeTab` state controls which content is visible.
- Tab styling: active tab has purple bottom border and bold text.
- Tab content area below with conditional rendering.

**Acceptance criteria**:
- Two tabs render correctly.
- Clicking a tab switches content.
- Active tab has visual indicator (border, bold text).
- Matches existing design system styling.

**Dependencies**: T-6.17 (page structure).

---

### T-6.21: Add Teacher Feedback tab content

**Description**: Render the teacher feedback content with Laoshi avatar and feedback text.

**Files affected**:
- `frontend/src/pages/Progress.tsx` -- add tab content

**Changes**:

Teacher Feedback tab layout:
- Left: `laoshi-logo.png` in a circular container.
- Right: feedback text in italicised quotes.
- Empty state: "Complete a session to get Laoshi's feedback!" when `teacher_feedback` is null.

**Acceptance criteria**:
- Avatar displays correctly from `/laoshi-logo.png`.
- Feedback text is italicised and in quotes.
- Empty state shows when no feedback exists.
- Layout is responsive.

**Dependencies**: T-6.20 (tab structure).

---

### T-6.22: Add Score Breakdown tab content

**Description**: Render the three score cards with icons, scores, descriptions, and info tooltips.

**Files affected**:
- `frontend/src/pages/Progress.tsx` -- add tab content

**Changes**:

Score Breakdown tab layout:
- 3 score cards in a row: Grammar, Usage, Naturalness.
- Each card:
  - Purple icon (Grammar: document/notepad SVG, Usage: speech bubble SVG, Naturalness: smiley face SVG).
  - Large score display: `X.X/10` (or `--/10` if null).
  - Score name label.
  - (i) info button that toggles a tooltip.
  - Description text below.
- Info tooltips explain what each score measures (see design.md section 5.6).
- Empty state: "Complete a practice session to see your scores." when all scores are null.

**Acceptance criteria**:
- Three score cards render with correct icons, scores, and descriptions.
- Icons are purple SVGs matching the mockup.
- Info buttons toggle tooltips on click.
- Tooltips show relevant explanation text.
- Empty state shown when no scores exist.
- Handles null scores gracefully (show `--/10`).

**Dependencies**: T-6.20 (tab structure).

---

### T-6.23: Handle empty states

**Description**: Ensure all empty states render correctly throughout the page.

**Files affected**:
- `frontend/src/pages/Progress.tsx` -- review and add empty states

**Changes**:

Review and implement all empty states (see design.md section 5.7):
1. No completed sessions: full-page empty state with icon and link to practice.
2. Chart with all zeros: renders normally (zero-height bars).
3. No teacher feedback: show message in feedback tab.
4. No scores: show message in scores tab.

**Acceptance criteria**:
- New user (no sessions) sees full-page empty state.
- User with sessions but no recent data sees appropriate per-section empty states.
- No crashes or undefined errors for any null/zero data combination.

**Dependencies**: T-6.17 through T-6.22 (all page sections exist).

---

## Phase 5b: Frontend Integration

These tasks wire the Report Card into the broader app. Can run in parallel with page tasks.

---

### T-6.24: Add feedback generation trigger to SessionSummary

**Description**: When the user clicks "Back to Home" in the session summary, fire off a background request to generate report card feedback.

**Files affected**:
- `frontend/src/components/SessionSummary.tsx` -- add onClick handler

**Changes**:

Add `onClick` handler to "Back to Home" link:
```tsx
onClick={() => {
  progressApi.generateFeedback().catch(() => {})
}}
```

Import `progressApi` from `../lib/api`.

**Acceptance criteria**:
- Clicking "Back to Home" triggers the POST request.
- Navigation is NOT blocked by the request.
- Errors are silently caught (fire-and-forget).
- Existing navigation behavior is preserved.

**Dependencies**: T-6.16 (API helper).

---

### T-6.25: Rename sidebar label

**Description**: Change the sidebar "Progress" label to "Report Card".

**Files affected**:
- `frontend/src/components/Sidebar.tsx` -- change label text

**Changes**:

Find the "Progress" sidebar item and change label to "Report Card". Keep same:
- Route: `/progress`
- Icon: bar chart icon

**Acceptance criteria**:
- Sidebar shows "Report Card" instead of "Progress".
- Link still navigates to `/progress`.
- Icon unchanged.

**Dependencies**: None (independent).

---

## Phase 6: Testing

These tasks write tests and verify the full flow. Depends on all previous phases.

---

### T-6.26: Backend unit tests for report_card_service.py

**Description**: Write unit tests for all business logic functions.

**Files affected**:
- `backend/tests/test_report_card_service.py` -- new file

**Test cases**:

**Topline metrics:**
1. No sessions: returns all zeros.
2. With completed sessions: correct time, count, distinct words.
3. Incomplete sessions (no session_end_ds) are excluded from time and count.
4. Skipped words (status != 1) excluded from words_practiced.

**Daily chart data:**
5. No attempts: 7 entries with all zeros.
6. With attempts: correct/incorrect counts per day.
7. Missing days filled with zeros.
8. Always exactly 7 entries returned.
9. Only includes user's own data.

**Rolling scores:**
10. No sessions: returns all None.
11. Fewer than 5 sessions: uses all available.
12. Exactly 5 sessions: uses all 5.
13. More than 5 sessions: only uses last 5.
14. Excludes skipped words and words with NULL scores.

**Score descriptions:**
15. Each score type at each range boundary (1, 3, 4, 5, 6, 7, 8, 9, 10).
16. None score returns None description.
17. Fractional scores (e.g., 6.7) round correctly.

**Dependencies**: T-6.6 through T-6.9.

---

### T-6.27: Backend integration tests for report card endpoints

**Description**: Write integration tests for both report card API endpoints.

**Files affected**:
- `backend/tests/test_report_card.py` -- new file

**Test cases**:

**GET /api/progress/report-card:**
1. Unauthenticated: 401.
2. Empty user: correct empty state response shape.
3. With session data: correct topline, chart, scores, feedback.
4. Rolling window: only uses last 5 sessions for scores.
5. Chart data: 7 entries, correct dates, missing days filled.
6. Score descriptions populated when scores exist.
7. Teacher feedback from UserProfile.report_card_feedback.

**POST /api/progress/generate-feedback:**
8. Unauthenticated: 401.
9. Success: feedback generated and stored (mock AI agent).
10. Agent failure: fallback message returned and stored.

**Dependencies**: T-6.11, T-6.12, T-6.13.

---

### T-6.28: End-to-end manual test

**Description**: Run a full manual test of the report card feature.

**Test sequence**:
1. Start with a fresh user or clear feedback.
2. Complete a practice session (several words with mix of correct/incorrect).
3. On session summary, click "Back to Home".
4. Navigate to Report Card page (`/progress`).
5. Verify topline metrics (time, sessions, words) are correct.
6. Verify stacked bar chart shows today's correct/incorrect data.
7. Verify "Teacher Feedback" tab shows Laoshi's feedback (may need to refresh if generation is still in progress).
8. Verify "Score Breakdown" tab shows grammar/usage/naturalness with scores and descriptions.
9. Click (i) info buttons and verify tooltips appear.
10. Switch between tabs and verify content changes.
11. Test with BYOK Gemini key: complete session, verify feedback generates with custom key.
12. Run `cd backend && python -m pytest tests/ -v` -- all pass.
13. Run `cd frontend && npm test -- --run` -- all pass.

**Acceptance criteria**:
- All visual elements match the mockup.
- Data is accurate and reflects actual practice data.
- Empty states render correctly for sections without data.
- No console errors in browser.
- No unhandled exceptions in Flask logs.
- All automated tests pass.

**Dependencies**: All previous tasks.

---

## Execution Order Summary

```
Phase 1 (Schema):
  T-6.1   Add report_card_feedback column         (independent)
  T-6.2   Run Alembic migration                   (depends on T-6.1)

Phase 2 (AI Agent -- can parallel with Phase 1):
  T-6.3   ReportCardContext dataclass              (independent)
  T-6.4   Report card prompt builder               (depends on T-6.3)
  T-6.5   report_card_agent + BYOK builder         (depends on T-6.4)

Phase 3 (Business Logic -- after Phase 1 + 2):
  T-6.6   Topline metrics function                 (after T-6.1)
  T-6.7   Daily chart data function                (parallel with T-6.6)
  T-6.8   Rolling scores function                  (parallel with T-6.6)
  T-6.9   Score description templates              (independent, parallel)
  T-6.10  Feedback generation function             (after T-6.1, T-6.5, T-6.8)

Phase 4 (Endpoints -- after Phase 3):
  T-6.11  GET /api/progress/report-card            (after T-6.6-T-6.9)
  T-6.12  POST /api/progress/generate-feedback     (after T-6.10)
  T-6.13  Register routes in app.py                (after T-6.11, T-6.12)

Phase 5 (Frontend -- after Phase 4 for data, but install/types can start earlier):
  T-6.14  Install Recharts                         (independent, anytime)
  T-6.15  TypeScript interfaces                    (independent, anytime)
  T-6.16  API helpers                              (after T-6.15)
  T-6.17  Progress.tsx header + data fetching      (after T-6.16)
  T-6.18  Topline metrics row                      (after T-6.17)
  T-6.19  Stacked bar chart                        (after T-6.14, T-6.17)
  T-6.20  Tab section                              (after T-6.17)
  T-6.21  Teacher Feedback tab                     (after T-6.20)
  T-6.22  Score Breakdown tab                      (after T-6.20)
  T-6.23  Empty states                             (after T-6.17-T-6.22)
  T-6.24  SessionSummary trigger                   (after T-6.16)
  T-6.25  Sidebar label rename                     (independent, anytime)

Phase 6 (Testing -- after all above):
  T-6.26  Unit tests for report_card_service       (parallel with T-6.27)
  T-6.27  Integration tests for endpoints          (parallel with T-6.26)
  T-6.28  End-to-end manual test                   (after T-6.26, T-6.27)
```
