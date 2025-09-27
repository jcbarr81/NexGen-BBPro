# Amateur Draft — Task Tracker

> Source plan: `docs/amateur_draft_plan.md`

Status legend: [ ] pending · [~] in progress · [x] done

## Phase 1 — Event Hook and Pause
- [ ] Detect Draft Day (third Tuesday in July) or read explicit date from schedule
- [ ] SeasonSimulator: add `draft_date` and `on_draft_day(date_str)` callback
- [ ] SeasonProgressWindow: open Draft Console on Draft Day and pause sim until it closes
- [ ] Persist flag in `season_progress.json` to avoid duplicate triggers

## Phase 2 — Draft Pool Generation & Persistence
- [ ] `playbalance/draft_pool.py` with `generate_draft_pool` and `load_draft_pool`
- [ ] Pool schema and position/age distributions; write `draft_pool_<year>.csv/json`
- [ ] Locking for writes (reuse pattern from `utils.stats_persistence`)

## Phase 3 — Draft Order & Scouting
- [ ] Compute order from standings as of Draft Day (reverse order, tiebreakers)
- [ ] Save `draft_state_<year>.json` (order, round, pick, selected, on_the_clock)
- [ ] Team‑needs heuristic for AI (org depth by position, SP/RP balance)

## Phase 4 — UI: Pool Browser & Draft Console
- [ ] `ui/draft_pool_window.py` (filter/sort, open profile)
- [ ] `ui/draft_console.py` (board, on‑clock, pool table, profile preview)
- [ ] Human pick + AI pick; Auto‑draft remaining
- [ ] Persist after each pick to `draft_state_<year>.json` and append to `draft_results_<year>.csv`

## Phase 5 — Post‑Draft Integration
- [ ] Append draftees to `data/players.csv`
- [ ] Add draftees to `data/rosters/<TEAM>.csv` at `LOW`
- [ ] Write `data/draft_log_<year>.csv` (team, player, round, overall)
- [ ] Mark draft complete; resume sim

## Phase 6 — Season Flow & Admin UX
- [ ] Admin Dashboard: “View Draft Pool” and “Start/Resume Draft” buttons
- [ ] SeasonProgressWindow: toast/summary after draft completes

## Phase 7 — Configuration & Tuning
- [ ] Draft config (rounds, pool size, distributions, AI weights)
- [ ] Random seed persistence for reproducibility

## Phase 8 — Validation
- [ ] Headless test to generate pool and auto‑draft a round; verify writes
- [ ] Resume test from mid‑round state
- [ ] Sanity checks (position counts, age mix)

---

## Notes / Decisions Log
- 2025‑07‑XX: Plan created and tracker initialized.

