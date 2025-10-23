# Pitcher Usage, Fatigue, and Rest Model (MLB‑Anchored)

This document specifies an ordered implementation plan to overhaul pitcher usage and fatigue/rest so simulated usage patterns mirror modern MLB. It includes goals, data baselines, APIs, and file‑by‑file tasks with acceptance criteria.

The plan keeps changes minimal and surgical, building on existing components:
- Season/day availability: `utils/pitcher_recovery.py`
- Pre‑game ordering: `playbalance/game_runner.py`
- In‑game bullpen AI: `playbalance/substitution_manager.py`
- Warmup tracking: `playbalance/bullpen.py` + `TeamState.bullpen_warmups`


## Goals
- Prevent relievers from appearing in far too many games.
- Model closer/setup usage primarily in late/high‑leverage innings.
- Enforce rest patterns (no 3rd straight day; 7‑day caps) and pitch‑count‑based recovery.
- Track “warmed but unused” bullpen cost to deter churn.
- Preserve 5‑man rotations and proper starter rest.


## MLB Baseline (from 2020–2024 dataset)
Source: `data/MLB_avg/role_averages_mlbstats_2020_2024.csv`.

Representative per‑pitcher seasonal workloads (approximate):
- 2021 closers: 1606.7 IP across 25 closers → ~64.3 IP per closer.
- 2021 setup: 2615.7 IP across 43 setup → ~60.8 IP per setup.
- 2021 middle: 17875.3 IP across 688 relievers → ~26.0 IP per RP (large group with variable roles).
- 2021 starters: 20517.3 IP across 152 SP → ~135 IP per starter (simulation targets should be calibrated via GS/IP distribution, not just this mean).

Operational targets to emulate:
- Starters: ~32 GS, ~5.5–6.0 IP/GS, 4 days rest baseline.
- Closers: ~60–70 G, ~60–70 IP, mostly 9th, single inning; back‑to‑back (B2B) occasionally, 3rd day rare/never.
- Setup: ~65–70 G, ~60–70 IP, mostly 7th–8th; single inning typical.
- Middle: ~50–65 G, ~45–60 IP; 1–2 innings typical.
- Long: ~35–50 G, ~60–80 IP; multi‑inning/emergency.


## High‑Level Design
- Availability = intersection of:
  - Pitch‑count recovery days after appearances (steeper for 30–50+ pitches).
  - B2B rule: forbid 3rd straight day; permit 2nd day only if yesterday’s pitches are small (e.g., ≤ 20).
  - Rolling window caps per role (3‑day and 7‑day limits).
  - Warmup tax: warming but not entering consumes ~8–12 “virtual pitches”.
- Role‑aware bullpen AI:
  - Inning/score matrix selects a role bucket: LR/MR for early, SU in 8th/leverage, CL in 9th+/save/tie.
  - Multi‑inning caps: CL/SU 3–4 outs; MR up to 6; LR up to 9.
- Pre‑game bullpen ordering prioritizes rested arms and sinks resting ones; early de‑prioritizes CL/SU.


## Configuration (new keys, with example defaults)
Add to `playbalance/playbalance_config.py` and expose via PB config.

- Rest curve
  - `restDaysPitchesLvl0` = 10 (≤10 pitches → 0 days)
  - `restDaysPitchesLvl1` = 20 (≤20 → 1 day)
  - `restDaysPitchesLvl2` = 35 (≤35 → 2 days)
  - `restDaysPitchesLvl3` = 50 (≤50 → 3 days)
  - `restDaysPitchesLvl4` = 70 (≤70 → 4 days)
  - `restDaysPitchesLvl5` = 95 (≤95 → 5 days)
  - above → 6 days
- Back‑to‑back & consecutive days
  - `b2bMaxPriorPitches` = 20 (allow B2B only if last game ≤ 20 pitches)
  - `forbidThirdConsecutiveDay` = 1 (boolean)
- Rolling caps by role (appearances)
  - `maxApps3Day_CL` = 2; `maxApps3Day_SU` = 2; `maxApps3Day_MR` = 3; `maxApps3Day_LR` = 2
  - `maxApps7Day_CL` = 4; `maxApps7Day_SU` = 4; `maxApps7Day_MR` = 5; `maxApps7Day_LR` = 4
- Warmup tax
  - `warmupTaxPitches` = 10 (credited as “virtual pitches” when warmed but unused)
- Role outing caps (outs per appearance)
  - `maxOuts_CL` = 3–4; `maxOuts_SU` = 3–4; `maxOuts_MR` = 6; `maxOuts_LR` = 9
- Feature toggle
  - `enableUsageModelV2` = 1 (allows quick disable if issues found)


## Data Extensions
Augment recovery persistence to support rolling windows and warmups.

- `_PitcherStatus` (JSON)
  - existing: `available_on`, `last_used`, `last_pitches`
  - add: `recent` = list of entries `{date, pitches, appeared, warmed_only}` (keep last ~14 days)
  - optional: `last_role` (e.g., `CL`, `SU`, `MR`, `LR`, `SP`)

- Derived fields (computed, not persisted):
  - `consecutive_days`
  - `apps_in_3_days`, `apps_in_7_days`


## APIs (utils/pitcher_recovery.py)
- `start_day(date_str: str) -> None` (exists)
- `ensure_team(team_id, players_file, roster_dir) -> None` (exists)
- `assign_starter(team_id, date_str, players_file, roster_dir) -> str | None` (exists)
- `bullpen_game_status(team_id, date_str, players_file, roster_dir) -> Dict[str, Dict]` (extend):
  - add computed: `consecutive_days`, `apps3`, `apps7`
- `record_game(team_id, date_str, pitcher_stats, players_file, roster_dir) -> None` (extend):
  - push into `recent` with `appeared=True`, `warmed_only=False`, `pitches`
  - set `last_role` when available (from player role/assignment)
- New: `record_warmups(team_id, date_str, bullpen_warmups: Dict[str, WarmupTracker]) -> None`
  - For any warmed pitcher without an appearance: push `recent` entry with `appeared=False`, `warmed_only=True`, `pitches=warmupTaxPitches`
- New: `is_available(team_id, pid, role, date_str) -> tuple[bool, str]`
  - Enforce: available_on; forbid 3rd consecutive day; B2B rule; 3‑day/7‑day role caps
  - Return reason for UI/debugging


## TeamState Extension
Add a lightweight, precomputed availability map used in‑game.
- `TeamState.usage_status: Dict[str, Dict[str, object]]` (pid → status dict from `bullpen_game_status` enriched with `is_available` result)


## In‑Game Role Selection
- Role targets by context (inning, leverage):
  - 1–5: prefer `LR/MR`; avoid `SU/CL` unless emergency
  - 6–7: `MR` primacy; `SU` in leverage
  - 8: `SU` in leverage; otherwise `MR`
  - 9+: `CL` for save/tie; `SU` if CL unavailable; extras allow rare 4‑out saves
- Enforce outing caps via `_max_reliever_outs` (already present) and toast flags.


## Ordered Tasks

1) Add configuration keys — Status: DONE
- File: `playbalance/playbalance_config.py`
- Add keys listed in Configuration; set sensible defaults. Guard usage behind `enableUsageModelV2`.
- Acceptance: importing config exposes keys with defaults; sim loads without errors.

2) Extend recovery data model and helpers — Status: DONE
- File: `utils/pitcher_recovery.py`
- Augment `_PitcherStatus` with `recent` list and optional `last_role`.
- Add ring buffer behavior (trim to last 14 entries).
- Extend `record_game()` to append to `recent` and compute `available_on` via new rest curve.
- Add `record_warmups()` to record warmed‑only entries (using `warmupTaxPitches`).
- Extend `bullpen_game_status()` to include `consecutive_days`, `apps3`, `apps7`.
- Implement `is_available()` applying: rest gates, B2B prior pitch threshold, 3rd‑day ban, 3‑day and 7‑day caps by role.
- Acceptance: unit tests can simulate back‑to‑back and third‑day cases and see availability toggle.

3) Update rest curve — Status: DONE
- File: `utils/pitcher_recovery.py`
- Replace `_rest_days()` step function with thresholds driven by config keys (see Rest curve).
- Distinguish starter‑level rest implicitly by pitch count (≥70 treated as start‑level).
- Acceptance: ≤10 pitches can be 0 rest; 30–50 implies 2–3 days; ≥70 implies 4–5 days.

4) Precompute bullpen availability and attach to TeamState — Status: DONE
- File: `playbalance/game_runner.py`
- After building `TeamState`, compute `status_map = tracker.bullpen_game_status(...)` and `TeamState.usage_status`.
- Modify `_apply_bullpen_usage_order()`:
  - Partition bullpen into available vs resting using `status_map` and sink resting.
  - Within available, sort by `days_since_use` desc, then `last_pitches` asc; keep role ordering (LR/MR preferred over SU/CL pre‑game).
- Acceptance: pitchers with `available=False` sort to end; rested arms prioritized.

5) Wire warmup tax after each game — Status: DONE
- File: `playbalance/game_runner.py`
- After both `record_game` calls, compute warmed but unused pitchers from `TeamState.bullpen_warmups`; call `tracker.record_warmups(team_id, date_token, state.bullpen_warmups)`.
- Acceptance: next day’s availability reflects warmups (virtual pitches applied).

6) Make role‑aware reliever selection — Status: DONE
- File: `playbalance/substitution_manager.py`
- Introduce `target_role(inning, run_diff, home_team) -> set[str]` role bucket.
- Update `_select_reliever_index()`:
  - Skip starters; prefer candidates whose `assigned_pitching_role` is in the target set.
  - Filter using `defense.usage_status[pid]['available']` if present.
  - Fall back to any available bullpen arm if none match.
- Update `maybe_warm_reliever()` and `maybe_replace_pitcher()`:
  - Use `_select_reliever_index()` result instead of always using `pitchers[1]`.
  - Warm and swap specifically to the selected index; enforce `_max_reliever_outs()` for CL/SU by setting `state.is_toast` as currently done.
- Acceptance: CL appears primarily in 9th+ save/tie; SU in 8th/leverage; MR/LR earlier.

7) Enforce B2B/3rd day and window caps in‑game decisions — Status: DONE
- File: `playbalance/substitution_manager.py`
- If `TeamState.usage_status` indicates unavailable (reasoned by tracker), do not warm/select that pitcher unless emergency (e.g., position player pitching threshold already exists).
- Acceptance: same reliever does not appear 3 consecutive days; 7‑day caps hold.

8) Tests: availability rules — Status: DONE
- Files: `tests/test_pitcher_usage_windows.py`, `tests/test_bullpen_role_selection.py`
- Add targeted tests:
  - Warmup tax increases next‑day rest appropriately.
  - B2B allowed only if prior pitches ≤ threshold; 3rd day never.
  - Weekly caps by role enforced.
  - CL/SU inning usage respects role matrix.
- Run via `pytest -k pitcher_usage`.

9) Season calibration script — Status: DONE
- File: `scripts/usage_calibration.py`
- Simulate a full season schedule; aggregate G/IP per role and compute B2B/3‑in‑4/7‑day rates.
- Print comparisons against target bands derived from the CSV.
- Provide CLI args to tweak key thresholds; exit with summary table.

10) Tune defaults to hit target bands — Status: PENDING
- Iterate: adjust `b2bMaxPriorPitches`, 7‑day caps, and rest thresholds to land CL/SU usage near ~60–70 G/60–70 IP and MR/LR bands.
- Re‑run calibration; track variance.

11) Optional: UI/analytics improvements (phase 2)
- Display bullpen “ready today” counts using `usage_status` (owner dashboards already surface a similar metric; ensure fields align).


## Acceptance Criteria (end‑to‑end)
- No reliever logs 3 consecutive game days under normal conditions.
- Closer usage concentrates in 9th+/save/tie; setup in 7th–8th; minimal early‑inning CL/SU.
- Typical season: 
  - CL/SU ~60–70 G, ~60–70 IP.
  - MR ~50–65 G.
  - LR ~35–50 G, with multi‑inning stints.
- Starters receive ≥4 days rest; rotation remains five pitchers.
- Warmed‑but‑unused relievers incur a rest impact.


## Compatibility & Rollout
- Gated by `enableUsageModelV2`. Keep old behavior by setting to `0`.
- Persistence additions are backward compatible: new JSON keys are optional, default to safe values.
- Failure modes (no available reliever) already have fallbacks (position player pitching) and should remain extremely rare with these caps.


## Risks & Mitigations
- Over‑tight caps causing bullpen exhaustion: provide emergency bypass if no arm is available; ensure LR role remains flexible.
- Teams with shallow bullpens: dynamic rotation promotion (already present) and MR preference in early innings reduce stress on CL/SU.
- Performance: availability checks are O(bullpen) per decision with small windows; caching `TeamState.usage_status` keeps in‑game costs minimal.


## Developer Notes
- Use `rg` for repository searches.
- Follow PEP8 for any new Python code.
- Before committing significant changes, run targeted tests with `pytest` in the `.venv` interpreter (e.g., `source .venv/bin/activate && pytest -k pitcher_usage`).
