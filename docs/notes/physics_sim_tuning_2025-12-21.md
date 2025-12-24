# Physics Sim Tuning Summary (2025-12-21)

## Scope
- Run: `./.venv/bin/python tmp/physics_sim_league_run.py --games 60 --seed 1`
- Teams: 12 (360 total games)
- Benchmarks: `data/MLB_avg/mlb_league_benchmarks_2025_filled.csv`

## Key Metrics (Sim vs MLB, delta)
- P/PA: `3.8458` (‑0.0142)
- K%: `0.2308` (+0.0108)
- BB%: `0.0849` (+0.0049)
- O‑Swing%: `0.3266` (+0.0066)
- Z‑Swing%: `0.6736` (+0.0236)
- Swing%: `0.5058` (+0.0358)
- Contact%: `0.8026` (+0.0426)
- SwStr%: `0.0999` (‑0.0101)
- Called‑3rd share of SO: `0.2216` (‑0.0084)
- AVG / OBP / SLG: `0.2419` / `0.3151` / `0.3725`
- BABIP: `0.2879` (‑0.0031)
- HR/FB: `0.1037` (‑0.0063)
- Zone%: `0.5165` (+0.0265)
- Pitches put in play: `0.1728` (‑0.0022)

## Final Tuning Knobs
These are the major adjustments locked into `physics_sim/config.py` at this point:
- Swing/chase: `zone_swing_scale=0.88`, `chase_scale=0.72`
- Two‑strike: `two_strike_aggression_scale=1.1`, `two_strike_zone_protect=0.6`, `two_strike_chase_protect=0.18`
- 3‑ball takes: `take_on_3_0_scale=0.5`, `take_on_3_1_scale=0.8`, `walk_scale=0.7`
- Whiff model: `whiff_base=0.013`, `whiff_quality_scale=0.095`, `whiff_velocity_scale=0.075`, `whiff_break_scale=0.085`, `whiff_location_scale=0.05`, `whiff_chase_scale=1.12`
- Contact/fouls: `contact_prob_scale=1.05`, `chase_contact_scale=0.75`, `foul_rate=0.36`, `two_strike_foul_scale=1.2`
- Pitching zone: `zone_target_base=0.38`, `called_zone_shrink_ft=0.025`
- Batted‑ball environment: `bat_speed_base=65.0`, `hr_scale=0.94`, `babip_scale=1.07`

## Notes
- P/PA is aligned with MLB target and stable.
- Discipline rates are in an acceptable band; residual deltas are small and do not destabilize run environment.
- Z‑Swing/Contact remain slightly elevated; adjust only if higher swing aggression becomes an issue in downstream game integration.
