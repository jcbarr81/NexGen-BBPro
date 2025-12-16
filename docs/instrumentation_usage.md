# Instrumentation Quickstart

NexGen BBPro now emits detailed swing and pitch diagnostics so tuning runs can be analyzed without diving into the debugger. Follow these steps to collect and interpret the data.

## Enable Diagnostics

1. Set the `ARBITRARY` flag to gate logging:
   - Export `SWING_DIAGNOSTICS=1` in your shell **or** override `collectSwingDiagnostics=1` in `playbalance_overrides.json`.
2. Run `scripts/playbalance_simulate.py` with `--diag-output path/to/diag.json`. When diagnostics are enabled the script automatically runs sequentially so per-pitch logging remains ordered.

Example:

```bash
SWING_DIAGNOSTICS=1 .venv/bin/python scripts/playbalance_simulate.py \
  --games 20 --seed 42 --diag-output tmp/diag.json --output tmp/results.json
```

## Files Produced

* `diag.json` – high-volume logs
  * `swing_pitch`: aggregates by pitch class and count (n, swing%, aggression, zone/chase adjustments). Includes an `archetype_counts` map showing how often each hitter archetype saw that combination.
  * `swing_count`: aggregates by count only (swing% etc., independent of pitch class).
  * `auto_take`: forced-take counters (distance, three-ball, full counts).
  * `pitch_distance_histogram`: histogram of pitch distances (rounded to nearest foot) for plate geometry tuning.
  * `events`: per-pitch events. Each entry contains:
    - `count`, `pitch_kind`, `pitch_type`, `objective`
    - Batter/pitcher archetype IDs
    - Flags for `swing`, `contact`, result-specific fields (`ball`, `called_strike`, `foul`, etc.)
    - Probabilities (base/final swing chance, discipline adjustments, ID probability)
* `results.json` – same aggregate totals printed to stdout plus:
  * `pitch_counts`: real vs. simulated pitches, ball/strike breakdown, zone counts.
  * `pitch_objectives`: total attack/chase/waste selections logged across the run.

## Interpreting The Metrics

- `results.json["pitch_counts"]["real_pitches"]` – live pitches only (excludes calibration padding). Use this to compute P/PA and zone%.
- `pitch_objectives.* / total_logged` – objective mix (should trend toward desired attack vs. chase rates once tuning is complete).
- `diag.json["events"]` – import into pandas or a notebook to slice by count, archetype, or pitch type. Each event records whether the pitch was simulated (`simulated`: true) so you can filter them out.

## Tips

- Keep `--diag-output` runs small (e.g., 10–20 games) unless you plan to stream the output somewhere else; full seasons generate millions of event entries.
- When troubleshooting a specific issue (e.g., low O-Swing), start by comparing `swing_pitch` entries vs. MLB targets, then dive into `events` for the count/pitch class in question.

## Deterministic Test Mode

- The test harness sets `simDeterministicTestMode=1` (see `tests/util/pbini_factory.py`) to force repeatable outcomes: a one-pitch RBI single with R3 only, and three-pitch strikeouts with empty bases. This keeps unit tests stable.
- Leave this flag at `0` for any production or tuning runs; it is purely a test aid and bypasses normal rating/physics logic.
