# Play-Balance Simulation Engine Tasks

This document tracks outstanding work required to build a new simulation engine
that mirrors all formulas and decisions in `playbalance/PBINI.txt` and validates
outputs against `data/MLB_avg/mlb_league_benchmarks_2025_filled.csv`.

## 1. Foundation & Utilities
### PlayBalanceConfig
- Map every entry in `playbalance/PBINI.txt` to structured configuration fields.
- Allow loading user JSON and merge overrides atop PBINI defaults.
- Validate that all PBINI keys are represented and raise on unknown keys.
- Tests verifying override precedence and full coverage of PBINI entries.

### Benchmark Loader
- Load league benchmark CSVs and expose park and weather factor helpers.
- Provide utilities returning league-average rates for common stats.
- Ensure helpers gracefully handle missing data or unknown parks.
- Tests confirming helpers return expected values for sample inputs.

### Utility Expansion
- Extend `ratings` module with conversions needed by later managers.
- Add core probability calculations for reuse across modules.
- Introduce a `state` container tracking inning, outs, runners, and score.
- Tests demonstrating utilities work together to update and query state.

## 2. Defensive Manager
- Port bunt charging, runner holding, pickoff, pitch-out, pitch-around/IBB,
  outfielder positioning, and fielder templates using PBINI formulas.
- Expose APIs that return probabilities or fielding coordinates.
- Unit tests verifying each calculation falls within expected ranges.

## 3. Offensive Manager
- Implement steal, hit-and-run, sacrifice bunt, and squeeze chance calculations
  with situational and rating modifiers from PBINI.
- Add decision utilities that determine whether tactics are attempted.
- Unit tests ensuring probabilities react correctly to input variables.

## 4. Substitutions
- Add combined rating helpers (offense, slugging, defense) and percentage modifiers.
- Implement pinch-hitting, pinch-running, defensive substitutions, double switches,
  pitcher replacement, and warm-up/cool-down management with toast tracking.
- Unit tests validating substitution decisions and pitcher fatigue handling.

## 5. Physics
- Translate environmental and player interaction formulas: friction, air resistance,
  swing angle, bat speed, power zones, hit angle distributions, pitch fatigue,
  warm-up, speed ranges, control-miss effects, and AI timing constants.
- Unit tests for representative calculations (exit velocity, pitch movement, fatigue).

## 6. Pitcher AI
- Implement pitch rating variation, selection adjustments, objective weight tables
  by count, and decision flow returning pitch type and location.
- Unit tests verifying correct objective weighting and selection behaviour.

## 7. Batter AI
- Build strike-zone grid classes, look-for logic, pitch identification formula,
  swing timing curves, swing adjustments, discipline and check-swing mechanics,
  foul-ball and HBP avoidance per PBINI settings.
- Unit tests ensuring discipline and identification outputs vary with ratings and count.

## 8. Fielder Abilities
- Implement reaction delay, catch chance, throw distance/speed/accuracy, wild pitch
  catching, and chase distance calculations.
- Unit tests validating catch/throw probabilities and distances against PBINI ranges.

## 9. Baserunners
- Implement long lead logic and pickoff scare reactions.
- Unit tests verifying speed thresholds and behaviour around pickoffs.

## 10. Engine Orchestrator
- Compose modules into a pitch-by-pitch loop updating player and team state.
- Provide `simulate_day`, `simulate_week`, `simulate_month`, and `simulate_season`
  helpers with state persistence.
- Integration tests simulating short seasons to validate stat accumulation.

## 11. Benchmark-Based Integration Tests
- Run simulated game batches and compare aggregated stats (K%, BB%, BABIP, SB rates,
  etc.) to benchmark targets within tolerances.

## 12. Documentation & Examples
- Add module docstrings summarising formulas and config references.
- Create README outlining how to run simulations and tests plus example scripts.
- Document meanings of MLB benchmark metrics for contributor reference.

