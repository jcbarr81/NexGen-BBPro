# Endurance-Driven Pitch Budget Model

This document describes the blueprint for introducing an endurance-based pitch budget that dictates reliever availability, warmup requirements, and fatigue penalties. It complements the existing rest-day and appearance-cap heuristics to produce MLB-like usage patterns.

## Overview

Every pitcher maintains a recoverable `available_pitches` pool derived from endurance. Game usage, warmups and emergency appearances deduct from the pool; daily recovery restores it. Availability, warmup requirements, and ratings penalties when pushing beyond the pool all hinge on this budget.

### Key Concepts

1. **Pitch Budget**
   - `max_pitches = endurance * role_multiplier[role]`
     - Example multipliers: SP=3.0, LR=2.0, MR=1.8, SU=1.6, CL=1.5 (configurable).
   - `available_pitches` starts at `max_pitches` and never exceeds it.

2. **Daily Recovery**
   - Each calendar day restores `daily_recovery = max_pitches * recovery_pct[role]`.
   - Recovery percentage tuned per role (e.g. relievers ~40%, starters ~25%).

3. **Workload Deduction**
   - Game appearances subtract actual pitches thrown plus simulated/virtual pitches (warmups, emergency penalties).
   - Warmups subtract a role-scaled cost (see “Warmup Requirement”).
   - Emergency fallback adds extra penalties (rest lockout handled by the budget).

4. **Availability Gate**
   - Pitcher is “available” only if `available_pitches / max_pitches >= availability_threshold[role]`.
   - Example thresholds: SP=0.85, LR=0.65, MR=0.60, SU=0.55, CL=0.55.
   - Combined with existing rest-day and B2B caps; whichever fails first blocks availability.

5. **Warmup Requirement**
   - Required warmup pitches scale with remaining budget.
     - Suggest formula: `required = base_warmup[role] * (available_pct) ^ exponent` where `available_pct = available_pitches / max_pitches`.
     - Low-endurance arms (smaller max_pitches) naturally need fewer pitches to get hot.

6. **Exhaustion Penalty**
   - When pitching with `available_pct <= 0` (i.e. exhausted), apply rating decreases driven by deficit magnitude. Example approach:
     - Reduce velocity and control proportionally to deficit (e.g. -10% at deficit of 10 pitches, -20% at 20, capped at a floor).
     - Increase fatigue state (`toast`/`is_toast`) aggressively for the AI to swap them out.
     - Record deficit-driven penalty so the budget has to climb above a higher threshold before they perform normally again.

7. **Emergency Usage**
   - Emergency fallback selects the least-taxed arm, applies extra deductions (already implemented), and optionally triggers a “lockout” that requires the budget to climb above `availability_threshold + lockout_delta` before they are considered again.

## Implementation Plan

1. **Configuration Keys** (playbalance/playbalance_config.py)
   - `pitchBudgetMultiplier_{CL,SU,MR,LR,SP}`
   - `pitchBudgetRecoveryPct_{role}`
   - `pitchBudgetAvailThresh_{role}`
   - `warmupPitchBase_{role}`, `warmupAvailabilityExponent`
   - `pitchBudgetExhaustionPenaltyScale` (ratings decay per deficit unit)
   - Optional: `pitchBudgetEmergencyLockoutDelta`

2. **Tracker Extensions** (utils/pitcher_recovery.py)
   - `_PitcherStatus` gains `max_pitches`, `available_pitches`.
   - On team load (`_ensure_team`), compute `max_pitches` using endurance + role.
   - New helper `_apply_daily_recovery(status, role)` invoked in `start_day()` and before status queries.
   - All workload writers (`record_game`, `record_warmups`, `apply_penalties`) subtract from `available_pitches` and clamp ≥0.
   - `apply_penalties` updated to record virtual usage entries and maintain budget integrity.

3. **Availability Logic**
   - `bullpen_game_status` includes `available_pct` for UI and selection.
   - `is_available()` checks budget threshold first, returning `(False, "budget")` when under.
   - Existing B2B and cap rules run only if budget is sufficient.
   - Emergency fallback already calls `apply_penalties`; it naturally keeps the pitcher below threshold for longer.

4. **Warmup Behavior**
   - `SubstitutionManager.maybe_warm_reliever` calculates required warmup dynamically (per role and availability).
   - `WarmupTracker` can optionally store the target and report readiness based on the dynamic count instead of a fixed config value.

5. **Exhaustion Effects**
   - When `available_pitches <= 0`:
     - Record deficit in `PitcherState` or attach to `Pitcher` as `budget_deficit`.
     - In `GameSimulation._update_fatigue` or `_fatigued_pitcher`, subtract ratings proportional to `budget_deficit * penalty_scale`.
     - Increase `state.toast` and mark `state.is_toast` to encourage removal.

6. **UI Updates**
   - Bullpen readiness displays `available_pct` and communicates rest days implied by recovery.
   - Optionally add tooltip “Available (65%) – ready in 2 days for full workload.”

7. **Testing & Calibration**
   - Unit tests verifying:
     - Budget decreases with appearances/warmups/penalties.
     - Daily recovery and availability threshold behavior.
     - Exhaustion penalty reduces ratings appropriately.
   - Re-run full-season simulation and adjust multipliers until closers/log relievers align with MLB usage (60–70 G, ~60–70 IP for CL/SU; ~50–65 G for MR; ~35–50 G for LR).
   - Monitor cadence metrics; adjust thresholds/recovery until avg max apps ~4–5/7 days for leverage arms and B2B rates below ~20%.

## Migration Notes

- Persisted data remains backward-compatible: new keys default to legacy numbers; legacy flow uses rest-day heuristics when `enableUsageModelV2` is off.
- Warmup logic must gracefully handle budget when pitchers are brand-new (e.g. not yet seen this season); default `available_pitches = max_pitches` ensures readiness.
- Ratings penalty ensures the AI firmly avoids exhausted arms even if emergency fallback is triggered.

