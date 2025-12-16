# PlayBalance Overhaul Plan

This plan resets the tuning effort by walking through the entire simulation stack — engine loop, configuration, batter and pitcher decision systems — so we can converge on MLB discipline, contact, and run-scoring targets without ad-hoc override swings.

## 0. Current State Recap
- Latest 50-game sim (`results.json`) shows P/PA 7.84, swing% 0.40, O-swing 0.23, called-third share 0.32, BB% 0.16, K% 0.38, and BIP rate 9.7%. All are far outside the MLB targets captured in `docs/sim_tuning_plan.md`.
- Batter logic now has additional two-strike knobs but is still dominated by penalty accumulation (`playbalance/batter_ai.py:650-760`), and overrides alone cannot overcome the structural issues (auto take, logit gates, penalty scaling).
- Pitcher AI still leans heavily on `objective_weights_by_count` defaults (see `playbalance/pitcher_ai.py:30-140`), so chase-heavy objectives persist regardless of base-state or hitter behavior.
- Simulation loop (`playbalance/simulation.py:169+`) still carries legacy elements such as pitch injection and foul/BIP balancing that we have only partially understood.

## 1. Instrument Everything (Phase 1)
**Goal:** capture deterministic diagnostics for every pitch/swing decision so we can replace guesswork with data.
- Extend `GameSimulation` pitch pipeline to log each pitch with outcome (ball/strike/foul/in-play), batter state, pitcher objective, and whether pitch injection fired. Wire this through the existing `PitchSurvivalTracker` / `BatterDecisionTracker` hooks.
- Update `playbalance_simulate.py` to emit a comprehensive `diag.json` schema: pitch counts by classification, swing/take contributions (auto take vs discipline vs random), pitcher objective frequency, foul/BIP transitions.
- Document how to enable/interpret the diagnostics in `docs/instrumentation_plan.md` and augment tests (`tests/test_instrumentation.py`, `tests/test_playbalance_batter_ai.py`) to assert the fields exist.

## 2. Simulation Engine Cleanup (Phase 2)
**Goal:** ensure the core loop produces realistic pitch sequences before AI tuning.
- Remove or rework the pitch injection path around `targetPitchesPerPA` in `playbalance/simulation.py` so each recorded pitch corresponds to an actual swing/take.
- Audit foul and ball-in-play resolution (`GameSimulation._resolve_swing`, `_foul_probability`, BIP injection knobs) so outcomes come directly from miss/contact probabilities rather than overrides; add tests for foul/BIP splits.
- Align plate geometry config (e.g., `sureStrikeDist`, `closeStrikeDist`) with actual pitch distances by collecting histograms from physics outputs.
- After cleanup, record a baseline 50-game sim with instrumentation off to make sure P/PA and pitch mix reflect reality before touching AI.
- **Status:** Phantom pitch injection is gone, foul/BIP resolution now flows directly from swing contact (with regression tests), and the diagnostics export a pitch-distance histogram used to retune `plateWidth`/`plateHeight` plus the `sure/close` strike thresholds (current zone share ≈46%, ball share ≈54%). Phase 2 is now complete.

## 3. Batter Discipline & Swing System Redesign (Phase 3)
**Goal:** rebuild `BatterAI.decide_swing` logic so discipline, count leverage, and two-strike behavior produce MLB swing patterns.
- Reorganize discipline computation (lines `playbalance/batter_ai.py:600-760`) into discrete stages: rating normalization, count/context adjustments, logit conversion, penalty application. Document each stage and expose config keys through `playbalance/playbalance_config.py`.
- Replace the old multiplicative penalty/floor logic with zone vs. chase bias weights and expose them (plus new auto-take probabilities) via config so we can tune called-third vs. chase behaviour independently.
- Replace the monolithic penalty multiplier with separate contributions for (a) called-strike tolerance and (b) chase tolerance, each with their own floors/caps. Introduce per-count multipliers instead of raw floors to reduce override dependence.
- Redesign auto-take logic so the forced-take thresholds are derived from count leverage and hitter aggression rather than static feet measurements.
- Introduce an explicit two-strike resolver: after the main discipline pass, enforce minimum swing chances for sure/close strikes and allow configurable chase aggression scaling; verify via diagnostics that called-third share drops near 0.23 before touching other knobs.
- Expand unit coverage: add tests around the new pipeline (e.g., verifying high-discipline hitters take borderline pitches early in the count but expand with two strikes).

## 4. Pitcher Objective & Attack Logic (Phase 4)
**Goal:** give `PitcherAI` enough situational awareness to stop spamming chase/waste targets.
- Replace the static `objective_weights_by_count` lookups with a generator that considers base-out leverage, batter handedness, recent swing behavior, and pitcher control ratings (e.g., high-control pitchers attack more often until behind in count).
- Track recent hitter aggression within the game (`BatterDecisionTracker`) and feed it back into the pitcher objective selection to keep reseting loops from forming.
- Expose new config tables for leverage bands and ensure defaults sit in `playbalance/playbalance_config.py` instead of scattering overrides.
- Add diagnostics + tests validating that low-leverage base-empty situations yield mostly attack targets while high-leverage spots reintroduce chase/waste per design.

## 5. Config Layering & Auto-Tune (Phase 5)
**Goal:** make configuration predictable and keep overrides minimal.
- Tighten `playbalance/sim_config.py` so simulation defaults clamp into safe ranges and reference the new config keys introduced above. Document the override order (PB.INI → sim_config tuning → `data/playbalance_overrides.json`).
- Rework `scripts/auto_tune_playbalance.py` to adjust only the high-level knobs (global swing scales, pitch-around chances, BIP injection knob once reinstated). Enforce small deltas and provide a dry-run diff to keep tuning auditable.
- Version and document the override set in `docs/sim_tuning_plan.md` so every iteration references a known baseline.

## 6. Validation & Regression Harness (Phase 6)
**Goal:** bake the MLB benchmarks into automated checks.
- Create a deterministic “mini season” harness (e.g., `scripts/check_playbalance_metrics.py --games 50 --seed ...`) that prints key KPIs alongside tolerances; add a test that fails when metrics drift outside bounds.
- Expand targeted pytest modules: keep `tests/test_league_swing_pct.py`, `test_called_third_strike_rate.py`, `test_pitches_per_pa.py`, etc., in sync with the new tolerances and instrumentation outputs.
- Document the full workflow in a new `docs/playbalance_overhaul_plan.md` (this file) plus an update to `docs/sim_tuning_plan.md` summarizing how each phase contributes to the final acceptance criteria.

## Execution Notes
- Treat phases as sequential but overlap instrumentation work with later phases where sensible.
- Every phase produces a short Markdown summary (linked from `docs/sim_tuning_plan.md`) plus diagnostic snapshots (results.json + diag.json) committed for traceability.
- Revisit auto-tuner only after phases 1-4 confirm swing/zone behavior matches MLB tolerances; until then, overrides stay static and changes live in code/config.

## Ratings-Driven Simulation Plan (current focus)

Goal: make every in-game outcome visibly driven by player ratings and keep the season flow intact. Work strictly in order; keep statuses and notes updated as we progress.

- **Task 1: Event/diagnostic scaffolding** — *Status: Completed*  
  Acceptance: (a) Introduce structured events (`PitchEvent`, `SwingDecision`, `ContactEvent`, `BattedBall`, `PlateAppearance`) without changing external APIs; (b) Route the existing `BatterDecisionTracker` / `PitchSurvivalTracker` through the new structures; (c) Flag to emit per-pitch JSON for dev runs; (d) Regression: all current pytest suites pass.
- **Task 2: Pitch resolution extraction** — *Status: Completed*  
  Acceptance: (a) Extract a pitch-resolution helper used by `play_at_bat` that consumes pitcher/batter ratings plus config and returns in-zone/swing/contact/foul/BIP outcomes; (b) No phantom/“simulated” pitch counters remain; `pitches_thrown/balls/strikes` reflect only real pitches; (c) Pitch-count calibration, if enabled, injects only real waste/foul pitches; (d) Zone% histogram export available for tuning plate geometry.
- **Task 3: Batter discipline pipeline** — *Status: In progress*  
  Acceptance: (a) `BatterAI.decide_swing` split into stages: rating normalization, count/leverage adjustments, swing/take logits for zone vs. chase, two-strike resolver, contact-quality calc; (b) Each stage exposes rating-derived terms (`ch`, discipline) in diagnostics; (c) Config clamps exist for floors/caps; (d) Tests proving monotonicity: higher `ch` → lower K% and higher contact quality at fixed pitch mix.
- **Task 4: Pitcher objective upgrade** — *Status: Not started*  
  Acceptance: (a) `PitcherAI` objective selection uses leverage (base/out/score), handedness, recent swing aggression, control/fatigue; (b) Default tables live in `playbalance/playbalance_config.py` with clamps; (c) Diagnostics report objective frequencies vs. counts; (d) Tests showing higher-control pitchers attack more often until behind, and leverage shifts toward chase/waste.
- **Task 5: Baserunning/fielding rating hooks** — *Status: Not started*  
  Acceptance: (a) Steal attempt/success uses runner `sp` vs. catcher/pitcher `arm/fa/hold_runner`, with documented floors/ceilings; (b) DP/force/tag decisions use timing based on fielder range/arm and runner speed; (c) Fielding AI catch/throw/error paths take fielder ratings as inputs; (d) Tests showing faster runners steal/tag more successfully and stronger arms suppress attempts.
- **Task 6: Season integration & KPI harness** — *Status: Not started*  
  Acceptance: (a) `simulate_game` remains the entry point; season stats persistence unchanged; (b) Add a deterministic mini-season harness that outputs KPIs and rating-stratified splits (top vs. bottom decile contact/power/control); (c) Target tolerances defined for P/PA, zone%, Z/O-swing, foul%, BIP%, BB%, K%, HR/FB, BABIP, steals/CS, DP/G; (d) CI/test hook fails when metrics drift beyond tolerances; (e) Doc update describing how to run/interpret the harness.

### Notes
- Keep all rating → mechanic mappings documented in a shared module (`playbalance/ratings_map.py`) as we implement tasks 2–5.
- When toggling diagnostic emission, ensure it does not alter RNG sequences for season sims.
- Unit-test fast paths now gated by `simDeterministicTestMode` so production runs stay rating/physics driven; keep test-only hooks isolated.
- Update status lines above as tasks start/finish and link to snapshots or PRs when available.
