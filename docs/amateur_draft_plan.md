# NexGen BBPro Amateur Draft — Project Plan

This plan introduces a mid-July amateur draft into the league progression. It extends the simulation to pause on Draft Day, generates a draft pool, conducts the draft in a dedicated console, assigns drafted players to organizations, and then resumes the season.

---

## Goals
- Add a Draft Day event (mid-July) that pauses the Season Simulator.
- Generate a realistic draft pool (HS/college mix, position balance, potentials).
- Provide a Draft Console to conduct the draft (human + AI), resumable at any pick.
- Persist results and assign players to team rosters.
- Resume the season seamlessly.

## Key Decisions
- Draft date: Third Tuesday of July (configurable; or read from schedule).
- Persistence: CSV + JSON under `data/` with file locks (same approach as season stats).
- Resumability: `data/draft_state_<year>.json` stores order, current pick, selected IDs.
- Order: Reverse standings at Draft Day (worst→best), tiebreakers by run differential then coin toss.
- Assignment: Draftees appended to `data/players.csv`; placed on `LOW` rosters.

## Architecture
- SeasonSimulator
  - Add `draft_date` and `on_draft_day(date_str)` callback.
  - On the draft date, call the callback and pause day advancement until it returns.
- Draft Pool (`playbalance/draft_pool.py`)
  - `generate_draft_pool(year, teams, size)` and `load_draft_pool(year)`.
  - Uses existing `player_generator` with tuned distributions.
- Draft Console (`ui/draft_console.py`)
  - Displays pool, order, recent picks; supports human picks; AI for others.
  - Writes `data/draft_results_<year>.csv` and updates `draft_state_<year>.json` after each pick.
- UI Integration
  - `SeasonProgressWindow` opens the Draft Console on Draft Day.
  - Admin Dashboard adds "View Draft Pool" and "Start/Resume Draft".

## File Layout
- `data/draft_pool_<year>.csv`  (canonical pool)
- `data/draft_pool_<year>.json` (scouting/metadata)
- `data/draft_state_<year>.json` (in-progress/resume)
- `data/draft_results_<year>.csv` (round, overall, team_id, player_id)

## Milestones
1) Hook + pause; pool generation; simple auto-draft — prove pause/resume.
2) Full multi-round draft; human picks; persistent results.
3) Admin integration; roster assignment; logs.
4) AI tuning (team needs, scarcity, age); UX polish (filters, queue, watchlist).
5) Docs and troubleshooting.

---

## Risks & Mitigations
- Data races while saving state — use file locks (same as `utils.stats_persistence`).
- Long drafts — provide Auto-Draft and Pause/Resume, persist after every pick.
- Shallow org depth — pool generator ensures scarce positions (C/SS/CF) and ~5 SP each.

## Acceptance
- On Draft Day the simulator pauses and the Draft Console opens.
- A complete draft (AI only) writes pool, state, and results; season resumes with draftees on rosters.
- Human-controlled teams can make picks; resuming mid-draft is supported.

