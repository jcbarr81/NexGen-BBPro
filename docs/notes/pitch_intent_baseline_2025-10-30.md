# Pitch Intent Diagnostics — 2025-10-30

Instrumentation: `PitchIntentTracker` wired into `PitcherAI` (Task 6.2). Calibration and phantom padding disabled (`pitchCalibrationEnabled=0`, `targetPitchesPerPA=0`). Samples generated via `scripts/collect_pitch_intent.py`.

Artifacts:

- `docs/notes/pitch_intent/pitch_intent_buckets_stochastic.csv`
- `docs/notes/pitch_intent/pitch_intent_buckets_deterministic.csv`
- `docs/notes/pitch_intent/pitch_intent_objectives_*.csv`
- `docs/notes/pitch_intent/pitch_intent_summary.json`

## 200-Game Stochastic Sample

- **Waste vs zone mix:** overall waste directives account for `44.3%` of selections; zone/attack holds `55.7%`.
- **Early-count nibbling:** 0-0 waste is `40%`, but 0-2 rises to `69%`, showing heavy chase attempts once ahead.
- **Hitter's counts thin on waste:** waste drops below `20%` by 2-1 and `16%` by 3-2, confirming pitchers challenge too often when behind (matches low walk rate).
- **Per-count totals (waste / zone / total):**
  - 0-0: `40%` / `60%` (`19,244` selections)
  - 0-1: `62%` / `38%` (`8,900`)
  - 0-2: `69%` / `31%` (`4,196`)
  - 1-0: `25%` / `75%` (`4,384`)
  - 1-1: `41%` / `59%` (`3,976`)
  - 1-2: `55%` / `45%` (`2,545`)
  - 2-0: `25%` / `75%` (`1,054`)
  - 2-1: `19%` / `81%` (`1,443`)
  - 2-2: `25%` / `75%` (`1,278`)
  - 3-0: `31%` / `69%` (`249`)
  - 3-1: `28%` / `72%` (`517`)
  - 3-2: `16%` / `84%` (`632`)
- Deterministic harness mirrors these ratios (see CSV).

## Post-Adjustment Verification (PBINI tuned)

Applied the recommended weight changes directly in `playbalance/PBINI.txt` (OutsideWeight increases paired with Plus/Best trims). Re-ran `scripts/collect_pitch_intent.py` and observed:

- **Overall waste share:** `46.7%` (up from `44.3%`).
- **Per-count waste ratios (stochastic sample):**
  - 1-0: `40.2%` waste (`+15 pts` vs. baseline)
  - 2-0: `39.6%` waste (`+14 pts`)
  - 2-1: `34.6%` waste (`+15 pts`)
  - 3-1: `37.7%` waste (`+9 pts`)
  - 3-2: `28.8%` waste (`+12 pts`)
- Early-count behaviour (0-0, 0-1, 0-2) unchanged, preserving the aggressive chase profile when ahead.

The deterministic harness mirrors the same directional changes (see updated CSVs). Plate-appearance outcome metrics (P/PA, walk%, strikeout%) remain identical because batter tuning is still pending; future retunes should revalidate intent share targets concurrently.

## Next Steps

- Extend the diagnostics to capture location buckets (inner/outer thirds) if we need finer granularity after the initial waste/zone tuning.

## Iteration — objective bias hook (2025-11-05)

- Wired `PitcherAI` objectives into the legacy sim loop by introducing `pitchObjective{Zone,Center,Waste}Bias*` overrides. Zone-directed calls now subtract distance from the control box while waste objectives add a configurable offset.
- Re-tuned hitter-count overrides to favour the zone on 1-0/2-0/3-1 counts (e.g., outside weight suppressed to ≤10% on 2-0). Latest 200-game intent sample: 0-0 waste `29.8%`, 1-0 waste `17.8%`, 2-0 waste `17.5%`, 3-1 waste `20.0%`, 3-2 waste `20.1%`.
- Diagnostics confirm overall waste share trimmed to `36%` while three-ball counts still carry ~20% chase directives, giving BatterAI room to distinguish leveraged balls without overwhelming the zone mix.
