# MLB-Style Series Scheduling Plan

## Objectives
- Restructure the schedule generator to build multi-game series instead of individual games.
- Preserve season length targets (e.g., 162 games, 81 home / 81 away) while introducing realistic travel days and rest patterns.
- Maintain compatibility with existing data structures and downstream consumers.

## Key Enhancements
1. **Series-Centric Model**
   - Introduce a series abstraction that bundles consecutive games against the same opponent and tracks metadata (length, venue, optional travel day).
   - Adapt `generate_mlb_schedule` so it emits series objects internally before expanding them into individual games for persistence.

2. **Series Template Library**
   - Define common series archetypes (two-, three-, and four-game sets) with usage ratios mirroring MLB norms.
   - Capture preferred start weekdays and permissible lengths for special events (opening day, rivalry weeks, etc.).

3. **Calendar Placement Logic**
   - Replace the per-day loop in `playbalance/schedule_generator.py` with a scheduler that advances by series length, then inserts travel/off days when the next series changes venue.
   - Retain the midseason All-Star break while allowing additional template-driven pauses (e.g., Opening Day, end-of-season buffers).

4. **Constraint Management**
   - Prevent back-to-back identical matchups, enforce caps on consecutive road/home series, and translate bye rounds (odd team counts) into rest periods.
   - Track cumulative game counts to ensure each team reaches season targets without violating home/away balance.

5. **Geographic & Travel Considerations**
   - Group road series into regional clusters to minimize long-haul jumps.
   - Flag long-distance transitions so the scheduler can mandate an off day before the next series starts.

6. **Validation & Tooling**
   - Add checks that verify game totals, series length distribution, rest day frequency, and travel constraints.
   - Integrate these checks into automated tests to guard against regressions.

## Implementation Approach
- Start with the series data structures and template catalog so the rest of the pipeline can target a clear interface.
- Build a two-pass scheduler: first assign opponents and series lengths, then lay them onto the calendar with travel-aware heuristics.
- Update persistence and UI layers to handle the new series metadata while ensuring backward compatibility with existing CSV formats.
- Extend unit tests (and add targeted `pytest` coverage) to validate constraint handling, especially travel day insertion and home/away balancing.
