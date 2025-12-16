# Player Input Normalization Plan

Task 1 requires a concrete strategy for moving from today's flat rating distributions to the archetype blueprint defined in `docs/player_archetypes.md`, and ensuring both the static CSV data and the runtime generator stay in sync. This document describes the approach, randomness rules, and regression checks.

## Overview

1. **Static roster normalization** – apply deterministic transforms to `data/players.csv` so existing league files match the archetype distribution.
2. **Runtime generator integration** – update `playbalance.player_generator.generate_player` to sample from the same archetype envelopes whenever new players are created (drafts, league expansion, admin tools).
3. **Regression harness** – use `docs/tools/player_rating_report.py` to verify archetype shares and mean ratings before/after changes.

## Step 1: CSV normalization

- Implement a one-off script (`scripts/normalize_players.py`) that:
  - Reads `data/players.csv`.
  - Assigns each player an archetype based on current ratings (or re-samples if the archetype is missing).
  - Re-samples ratings using the rules in `docs/player_archetypes.md` and writes a new CSV (keeping IDs/names intact).
- Keep the original file under version control; commit the updated CSV once the report confirms the desired distributions.
- Document the script usage in `docs/player_archetypes.md` so future seasons can regenerate the pool.

## Step 2: Generator integration

- Refactor `playbalance.player_generator.generate_player`:
  - Add an `ArchetypeConfig` module that holds the same target ranges/jitter logic used for the CSV normalization.
  - Extend the generator API with optional `hitter_archetype` / `pitcher_archetype` parameters; when not provided, sample according to the target share.
  - Ensure roles are respected (e.g., if `pitcher_archetype="closer"`, force closer ranges regardless of random selection).
  - Cover the new code with tests in `tests/test_player_generator.py` verifying that generated players land inside the specified ranges and that randomness still produces diversity (use statistical assertions with tolerances).
- Update any admin/CLI entry points that create players (e.g., `playbalance/league_creator.py`, UI admin actions) to pass through archetype hints when appropriate.

## Step 3: Regression / acceptance checks

- After running the normalization script and updating the generator, execute:

  ```
  python docs/tools/player_rating_report.py --players data/players.csv --output docs/player_rating_report.md
  ```

  Ensure the archetype counts match target shares within ±3 percentage points and mean ratings stay within ±10% of MLB benchmarks.

- Add a CI step (or document a manual check) that runs the report plus a smoke test generating 500 hitters and 300 pitchers via `generate_player`. Compare the generated-player report against the CSV to ensure both paths align.

- Acceptance criteria recap (from `docs/sim_tuning_plan.md` Task 1):
  - Report + archetype doc checked in (done).
  - Normalization strategy documented (this file).
  - `build_default_game_state` uses normalized data (covered once CSV is rewritten).
  - Player generator uses the same archetype logic so new players continue to match the tuning.
