# Amateur Draft — Task Tracker

> Source plan: `docs/amateur_draft_plan.md`

Status legend: [ ] pending  [~] in progress  [x] done

## Phase 1 — Event Hook and Pause
- [x] Detect Draft Day (third Tuesday in July) or read explicit date from schedule
- [x] SeasonSimulator: add `draft_date` and `on_draft_day(date_str)` callback
- [x] SeasonProgressWindow: open Draft Console on Draft Day and pause sim until it closes (modal)
- [x] Persist flag in `season_progress.json` to avoid duplicate triggers

## Phase 2 — Draft Pool Generation & Persistence
- [x] `playbalance/draft_pool.py` with `generate_draft_pool` and `load_draft_pool`
- [x] Pool schema and position/age distributions; write `draft_pool_<year>.csv/json`
- [x] Locking for writes (pool + state/results use simple file locks)

## Phase 3 — Draft Order & Scouting
- [x] Compute order from standings as of Draft Day (reverse order, tiebreakers)
- [x] Save `draft_state_<year>.json` (order, round, pick, selected, on_the_clock)
- [x] Team needs heuristic for AI (org depth by position, SP/RP balance)

## Phase 4 — UI: Pool Browser & Draft Console
- [x] De-scoped `ui/draft_pool_window.py` — integrated in Draft Console
- [x] `ui/draft_console.py` (board, on-the-clock, pool table, profile preview)
  - [x] Pool table + search filter
  - [x] On-the-clock banner + status
  - [x] Recent picks board (last 10)
  - [x] Human pick (Make Pick) and AI pick (Auto Pick This Team)
  - [x] Auto-draft remaining (multi-round)
  - [x] Per-pick persistence (state + results)

## Phase 5 — Post-Draft Integration
- [x] Append draftees to `data/players.csv` (services/draft_assignment.commit_draft_results)
- [x] Add draftees to `data/rosters/<TEAM>.csv` at `LOW`
- [x] Write `data/draft_results_<year>.csv` (team, player, round, overall) — serves as draft log
- [x] Mark draft complete (season_progress flag) and resume sim
- [x] Add league news entry and toast after commit

## Phase 6 — Season Flow & Admin UX
- [x] Admin Dashboard: "View Draft Pool" and "Start/Resume Draft" buttons
- [x] SeasonProgressWindow: toast/summary after draft completes

## Phase 7 — Configuration & Tuning
- [x] Draft config (rounds, pool size)
- [x] Random seed persistence for reproducibility

## Phase 8 — Validation
- [x] Headless test to generate pool and auto-draft a round; verify writes
- [x] Resume test from mid-round state
- [x] Sanity checks (position counts, age mix)

---

## Notes / Decisions Log
- 2025-09-28: Fixed Draft Console import issues and encoding; UI elements polished; draft log confirmed as `draft_results_<year>.csv`.
- 2025-09-27: Phase 1 hooks implemented; minimal Draft Console added; basic pool gen saved to data/.
- 2025-07-XX: Plan created and tracker initialized.
