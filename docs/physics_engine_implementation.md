# Physics Engine Implementation Plan

This plan tracks the physics simulation engine rollout, the remaining gaps,
and the acceptance criteria for each milestone. It replaces the old
playbalance-focused plan for ongoing work.

## Current State (2025-12-31)
- HR tuning locked (hr_scale=0.965) with non-HR XBH lift retained.
- 5-season validation confirms HR leader band 43-59 with no anomaly flags.
- In-game simulation now uses the physics engine by default; legacy toggle removed.
- Park factors are currently disabled (park config retained for later).

Latest artifacts:
- Locked config snapshot: `tmp/config_backups/physics_sim_config_locked_20251231_030700.py`
- 5-season validation run: `tmp/long_term_runs/hr_tune_pass_20251230_215043`
- Season summaries: `tmp/long_term_runs/hr_tune_pass_20251230_215043/analysis/season_summaries.jsonl`

## Milestones

### 1) Core Engine & Stat Parity
Status: Completed
- Pitch-by-pitch physics sim producing complete boxscore + metadata.
- Ratings-driven outcomes (batting, pitching, baserunning, fielding).
- Season integration via `simulate_game` with consistent stat persistence.

Acceptance:
- Game-level stats align with MLB benchmarks within tolerances in the KPI harness.
- Boxscore/metadata fields are complete for UI display.

### 2) KPI Harness + Tuning Lock
Status: Completed
- Deterministic KPI harness in `scripts/physics_sim_season_kpis.py`.
- Multi-season validation using `scripts/run_long_term_physics_sim.py`.
- Tuned values locked into `physics_sim/config.py`.

Acceptance:
- 5-season validation shows stable ranges with no metric drift.

### 3) UI Integration & A/B Toggle
Status: Completed
- In-game toggle allows switching between legacy and physics sim.
- Season progress UI supports the new engine path.

Acceptance:
- Full-season sim completes from the UI with physics engine enabled.

### 4) Hardening & Regression Gating
Status: Completed
- Physics-sim tests now run against the physics KPI harness where needed.
- Targeted pytest coverage passes without loosening tolerances.

Acceptance:
- Targeted pytest suite passes in `.venv` without loosening tolerances.
- KPI harness can be run in strict mode as a regression check.

### 5) Long-Term League Stability
Status: Completed
- Ensure multi-decade runs do not fail due to roster/lineup depletion.
- Verify auto-assign and roster backfill logic after draft/aging.
- Auto-fill lineups and fallback pitchers when rosters are thin.

Acceptance:
- 50+ consecutive seasons run without roster-related failures.

Latest run:
- 50-season stability pass: `tmp/long_term_runs/stability_pass_20251229_024500`

### 6) Park Factors & Stadium Effects
Status: Deferred
- Re-enable park factors and validate their impact on HR/2B/3B.

Acceptance:
- Park-adjusted metrics remain within MLB tolerances after re-enable.

### 7) Legacy Swap
Status: Completed
- Physics engine is now the default path and the legacy toggle is removed from UI.

Acceptance:
- Full-season UI flows and tests pass using physics engine only.

## Runbook (quick commands)

KPI harness:
```bash
./.venv/bin/python scripts/physics_sim_season_kpis.py \
  --games 50 --seed 1 --players data/players_normalized.csv \
  --ensure-lineups --output tmp/physics_kpis.json --strict
```

Multi-season validation:
```bash
./.venv/bin/python scripts/run_long_term_physics_sim.py \
  --seasons 5 --teams 14 --games 162 --seed 1 \
  --output-dir tmp/long_term_runs/validation_pass_YYYYMMDD_HHMMSS --force
```

## Notes
- Keep park factors disabled until post-validation to avoid skewing HR rates.
- Any tuning changes should be snapshot in `tmp/config_backups/` before running
  multi-season validation.
