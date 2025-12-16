# Instrumentation Plan (Task 2)

Goal: capture fine-grained swing/pitch decision data so we can understand plate-discipline deltas and debugs during sim runs. This document expands on the subtasks listed in `docs/sim_tuning_plan.md`.

## Scope

1. **Batter diagnostics**
   - Extend `playbalance/batter_ai.py` so every call to `decide_swing` records a structured event (count, pitch class, distance, archetype, base swing probability, penalties, auto-take reasons).
   - Gate logging behind a config flag (`collectSwingDiagnostics`) and expose snapshots via `playbalance_simulate.py --diag-output`.
   - Roll up diagnostics by count/pitch-type/archetype so we can compare MLB benchmarks quickly.

2. **Pitcher/pitch pipeline instrumentation**
   - In `playbalance/pitcher_ai.py` and `playbalance/simulation.py`, track:
     - Objective weights chosen per count.
     - Actual pitch locations (distance buckets) vs intended objectives.
     - Raw pitch/strike/ball totals so we can validate that every recorded pitch is live (phantom injection is now removed).
   - Provide aggregated counts (zone%, o-zone%, attack/chase/waste shares) in the sim output JSON.

3. **Reporting + documentation**
   - Update `scripts/playbalance_simulate.py` to include the new metrics in both stdout summaries and `--output` JSON.
   - Produce a `docs/instrumentation_usage.md` guide showing how to run the diagnostics and interpret the output.
   - Add a smoke test (`tests/test_instrumentation.py`) ensuring the logging machinery produces expected keys/structures when sims run with diagnostics enabled.

## Current Instrumentation Surface

- Running `scripts/playbalance_simulate.py --diag-output tmp/diag.json --games 50 --seed 2026 --no-progress` now forces a sequential run that attaches the batter decision tracker, pitch intent tracker, and pitch survival tracker directly to the orchestrator. The emitted JSON contains:
  - `swing_pitch`, `swing_count`, and `auto_take` sections from `batter_ai`'s inline diagnostics.
  - `batter_decisions.counts/breakdown/objectives/target_offsets` summarising the GameSimulation tracker, reflecting only live pitches now that phantom injection is gone.
  - `batter_decisions.distance_histogram` plus `avg_pitch_distance` per count so we can derive plate geometry thresholds without rerunning the sim.
  - Per-pitch `auto_take_prob`/`auto_take_roll` fields (when enabled) so we can trace the new probabilistic take model and verify forced takes by count.
  - `pitch_intent` bucket/objective counts plus per-pitch breakdowns from `PitcherAI`.
  - `pitch_survival` distributions and survival curves to visualize pitch-count decay across live plate appearances.
- `results.json` now exposes a `pitch_counts` block (`pitches_thrown`, `strikes_thrown`, `balls_thrown`, `zone_pitches`, `first_pitch_strikes`) for every run. When diagnostics are enabled, the file also includes `pitch_objectives` totals (attack/chase/waste counts with the logged pitch total) so CLI consumers can diff the intent mix alongside league KPIs.

## Deliverables & Acceptance

- CLI flag(s) to enable diagnostics, writing JSON under a user-specified path.
- Results JSON includes raw counters (balls_thrown, strikes_thrown, fouls, zone counts) plus the derived metrics currently printed to stdout.
- Documentation describing how to gather/interpret data, and tests asserting instrumentation hooks don’t regress.
