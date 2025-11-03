# Batter Decision Diagnostics — 2025-10-30

Instrumentation: `BatterDecisionTracker` (wired via `GameSimulation.set_batter_decision_tracker`) with collection script `scripts/collect_batter_decisions.py`. Runs captured with calibration/phantom padding disabled (`pitchCalibrationEnabled=0`, `targetPitchesPerPA=0`).

Artifacts:

- `docs/notes/batter_decisions/batter_decisions_stochastic.csv`
- `docs/notes/batter_decisions/batter_decisions_deterministic.csv`
- `docs/notes/batter_decisions/batter_decisions_summary.json`

## Key Findings (200-Game Sample)

- **Overall take rate:** `30.6%` (MLB reference ~`47%`). Hitters still offer at ~70% of pitches.
- **Count breakdown:** 1-0 take `29.6%`, 2-0 take `45.6%`, 2-1 take `48.6%`, 3-1 take `80.3%`, 3-2 take `76.2%`. They remain hyper-aggressive early but become overly passive once three balls accrue.
- **Two-strike approach:** 0-2 take `22.0%` (reasonable), but the full-count passivity yields a `3.7%` called-strike rate and heavy walk/strikeout polarity.
- **Zone vs chase:** Overall ball rate `25.2%` despite the pitcher waste calibration (Task 6.2), signalling hitters continue expanding the zone with fewer than three balls while over-adjusting later.

| Count | Take % | MLB Target (approx) | Notes |
| --- | --- | --- | --- |
| 0-0 | 28.6% | ~47% | Need broader auto-take buffer to tame first-pitch swings. |
| 1-0 | 29.6% | ~64% | Green-light behaviour still dominant. |
| 2-0 | 45.6% | ~71% | Hitters rarely accept the count despite advantage. |
| 2-1 | 48.6% | ~60% | Slight improvement needed; still aggressive. |
| 3-1 | 80.3% | ~72% | Now overly passive—huge ball rate inflates walks/called Ks. |
| 3-2 | 76.2% | ~46% | Severe overcorrection; called strikeouts surge. |

## Config Experiment (2025-10-30)

Tried nudging the count swing adjustments (`swingProb10/20/21/31/32CountAdjust`), the auto-take window, and `swingProbCloseBall`. After rerunning the diagnostics there was **no material improvement**—early-count takes stayed flat and the 3-1/3-2 passivity remained extreme. Restored the original PBINI/override values. Next step is to trace `load_tuned_playbalance_config` (which clamps discipline/auto-take settings) and evaluate whether BatterAI’s discipline logic is overpowering these knobs.

## Iteration — discipline logistic + tuned count clamps (2025-11-02)

- Added swing-chance breakdown logging (`playbalance/batter_ai.py`) and taught the diagnostics tracker to persist per-count component averages so we can attribute swings vs takes directly from `batter_decision_breakdown_*.csv`.
- Relaxed the PBINI discipline clamps inside `load_tuned_playbalance_config` and introduced a logistic discipline mapping with count-aware penalty floors, configurable close-strike mixing, and optional auto-take overrides.
- Tuned early-count `swingProb` adjustments and per-count discipline scaling to pull first-pitch and 1-0 swings toward Statcast. Latest 200-game sample take rates: 0-0 `63.1%`, 1-0 `48.8%`, 2-0 `47.1%` (vs MLB `68.9%`, `57.3%`, `57.3%`).
- Three-ball behaviour now blends count-specific penalty floors with chase allowances. Take rates sit at 3-1 `51.0%` (MLB `46.4%`) and 3-2 `35.7%` (MLB `29.9%`), shrinking the earlier 30–40 pt gap to roughly +4–6 pts.
- Re-ran `scripts/chart_swing_take_gaps.py`; refreshed artifacts live in `docs/notes/batter_decisions/`. Remaining discrepancies are concentrated in (a) early-count aggression (0-0 `-21 pts`, 1-0 `-14 pts`, 2-0 `-15 pts`) and (b) late-count caution (3-1 `+7 pts`, 3-2 `+8 pts`), so the next iteration should target leverage-aware scaling rather than broader baselines.

## Next Steps

- Nudge the 0-0/1-0/2-0 tuning (count adjusts, raw scales, logit centers) to erase the remaining `≈9–15` pt take deficits while reining in the +3–5 pt ball-rate bump.
- Continue refining 3-1 / 3-2 chase behaviour with Statcast pitch-location/chase splits; residual take gaps of `+4–6` pts and ball-rate deltas of `+14` pts suggest the new chase odds still need work.
- Validate the revised config over a season sim to ensure P/PA, BB%, K%, and run environment remain within tolerated ranges before moving on to roster AI adjustments.
- _2025-10-30:_ Downloaded Statcast 2023 count-level swing/take data via `scripts/download_statcast_counts.py` → `data/MLB_avg/statcast_counts_2023.csv`. Generated comparison artifacts in `docs/notes/batter_decisions/` (`batter_decision_gap_analysis.csv`, `batter_decision_rate_comparison.png`, `batter_decision_take_gap.png`). Post-adjustment diagnostics show remaining take gaps of roughly `-21/-14/-15` pts on 0-0/1-0/2-0 and `+7/+8` pts on 3-1/3-2, guiding the next tuning targets above.

## Iteration — auto-take window expansion (2025-11-05)

- Relaxed three-ball penalty floors (`disciplinePenaltyFloorThreeBall` ≥`0.18`) and boosted per-count auto-take distances to curb forced takes once hitters showed intent to swing.
- Current 200-game deltas (Sim − MLB): 0-0 take `-10.1` pts / ball `+5.5` pts; 1-0 take `-8.5` pts / ball `+3.7` pts; 2-0 take `-5.1` pts / ball `+9.0` pts; 3-1 take `-3.7` pts / ball `+6.4` pts; 3-2 take `+0.8` pts / ball `+2.8` pts.
- 3-1/3-2 chase deficits from earlier iterations are resolved without reintroducing the extreme passivity—swing rates sit at `59.8%` (3-1) and `69.7%` (3-2) with ball-call gaps trimmed by ~4–5 pts.
- Remaining imbalance is dominated by pitcher zone rate (≈28% vs Statcast ≈57% on leverage counts), keeping early-count ball deltas stubbornly high; a follow-up pass on pitcher calibration or auto-take chase odds may be required if we want ball gaps below ~5 pts without reopening aggression.

## Iteration — pitcher zone calibration (2025-11-05)

- Expanded `plateWidth/Height` to `2.0` and introduced configurable miss scaling (`pitchMissScale=64`, `controlMissBaseExpansion=1.1`, `controlMissPenaltyDist=2.1`) so strike probability responds to control while keeping foul/ball distributions stable.
- Hooked `PitcherAI` objectives into the simulation loop and added per-count `pitchObjective{Zone,Center,Waste}Bias*` overrides. Updated weights removed waste directives from 2-0 and trimmed 3-1 outside intent to 10%.
- Latest 200-game deltas (Sim − MLB): 0-0 take `-4.9` pts / ball `-1.1` pts; 1-0 take `-4.6` pts / ball `-7.7` pts; 2-0 take `-2.1` pts / ball `-2.6` pts; 3-1 take `-5.7` pts / ball `+0.4` pts; 3-2 take `+0.6` pts / ball `-2.4` pts.
- Mid-count splits still show excess strikes when pitchers are ahead (0-1/0-2 ball gaps `-12` to `-24` pts) and lingering chase inflation on 2-1/2-2 (`+13`/`+9` pts). Next pass should balance `pitchObjective*Bias` across those counts before moving to season-scale regression.
- Follow-up tuning pushed count-specific objective biases and two-strike aggressiveness to bring ball deltas within ±0.05 on `0-1`, `1-0`, `2-0`, and `2-1`. Current sims (200-game stochastic) show: `0-1` ball `-0.04`, `1-0` ball `-0.04`, `2-0` ball `-0.02`, `2-1` ball `+0.03`, while `2-2` remains elevated at `+0.09` despite softened discipline floors and heightened swing incentives.
