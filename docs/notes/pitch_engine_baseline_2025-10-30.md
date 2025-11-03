# Pitch Engine Baseline — 2025-10-30

This note records the raw (uncalibrated) pitch/plate-appearance behaviour with the legacy phantom-padding disabled (`pitchCalibrationEnabled=0`, `targetPitchesPerPA=0`). Two samples were captured:

- **200-game stochastic set** using varied RNG seeds to approximate league-wide behaviour.
- **10-game deterministic harness** seeded for reproducibility when debugging plate appearance flow.

Detailed aggregates and raw counters are stored alongside this note:

- `docs/notes/pitch_engine_baseline_2025-10-30.csv`
- `docs/notes/pitch_engine_baseline_2025-10-30.json`

## Key Metrics (200-game sample)

- **Pitches per PA:** `2.48` (target ≈ `3.8`) — plate appearances are resolving almost a full pitch too early.
- **Take rate:** `29.9%` vs. MLB ~`47–48%`; hitters offer at ~70% of pitches, driving quick resolutions.
- **Walk rate:** `2.1%` (MLB baseline ~`8.5%`), confirming the aggressive approach leaves little room for ball-four scenarios.
- **Ball-in-play share:** `71.5%` of plate appearances end in fair contact; MLB trends hover near the mid-50s, so outs/hits are occurring far too quickly.
- **First-pitch strike rate:** `45.9%`, implying pitchers are missing the zone but still escaping because batters chase; PitcherAI waste/edge logic needs review.
- **Estimated foul share:** `16.6%` of pitches, producing only ~`0.41` fouls per PA — even with a generous estimate, the game lacks spoil pitches deep in counts.

## Deterministic 10-game Harness

The deterministic slice mirrors the broader trends (`P/PA≈2.50`, `take_rate≈29.9%`, `walk_pct≈2.2%`), making it a reliable reproduction scenario for targeted tuning and regression tests.

## Leverage Points

1. **Retune batter decision models** to raise called takes—especially early-count takes—so walks can re-emerge and plate appearances stretch toward 3.8 pitches. Plate-discipline, chase, and situational logic need to be tightened.
2. **Rebalance PitcherAI command/waste mix** so pitchers throw more intentional balls and borderline strikes. With first-pitch strikes below 46% yet hitters still swinging, the engine is depending on batter aggression rather than organic pitch quality to extend counts.

Follow-up work should iterate on these fronts and re-run both samples to confirm that the raw simulation sits near MLB-style distributions before re-enabling the calibrator as a light correction.
