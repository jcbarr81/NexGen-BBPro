# Phantom Pitch Baseline Snapshot - 2025-10-30

## 50-Game Simulation Summary
- Command: inline script executed via `.venv/bin/python - <<'PY' ... | tee docs/notes/50_game_baseline.txt`
- Config: `load_tuned_playbalance_config()` with default `ABU` vs `BCH` rosters and seeds `2025 + game_index`
- Raw output: `docs/notes/50_game_baseline.txt`
- Totals: `pitches_thrown=25467`, `plate_appearances=4891`, `pitches_per_PA=5.207`
- Starter fatigue: pitch count avg `51.3` (min `4`, max `176`), average outs `6.1` (max `25`), toast avg `6.23` (max `37.00`), `is_toast` triggered `0` times
- Debug sample: first 20 log entries from game 1 included in `docs/notes/50_game_baseline.txt`

## Targeted Pytest Checks
- Command: `.venv/bin/pytest tests/test_simulation.py::test_pinch_hitter_used tests/test_simulation.py::test_walk_records_stats tests/test_simulation.py::test_steal_attempt_success`
- Output: `docs/notes/pytest_phantom_baseline.log`
- Results: `test_pinch_hitter_used` PASS, `test_steal_attempt_success` PASS, `test_walk_records_stats` FAIL (`outs` returned `1` instead of expected `0`; batter walk not recorded)

## Notes
- The failing walk test documents current behaviour and will need to be revisited when implementing calibration fixes.
- Baseline files in `docs/notes/` serve as the source of truth for Phase 1 Task 1.1 until superseded.
