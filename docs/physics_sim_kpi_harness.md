# Physics Sim KPI Harness

This harness runs a deterministic physics-sim mini season and reports KPIs
alongside MLB benchmark deltas and tolerance checks.

## Run

```bash
./.venv/bin/python scripts/physics_sim_season_kpis.py \
  --games 50 \
  --seed 1 \
  --players data/players_normalized.csv \
  --ensure-lineups \
  --output tmp/physics_kpis.json \
  --strict
```

- `--strict` exits non-zero if any KPI drifts outside the configured tolerance.
- `--tolerances path/to/tolerances.json` overrides defaults (keys must match KPI names).

## Output

The JSON payload includes:

- `metrics`: computed KPIs (P/PA, zone/swing/contact rates, K%, BB%, HR/FB, BABIP,
  steals/attempts, BIP double-play rate, runs/hits/HR per team game).
- `deltas`: KPI minus MLB benchmark (where available).
- `tolerance_ok` and `tolerance_failures`: pass/fail summary vs tolerances.
- `rating_splits`: top/bottom decile summaries for batter contact/power and pitcher control.

## Notes

- The DP check uses `bip_double_play_pct` (GIDP per ball in play) because the MLB
  benchmark file does not include a direct DP-per-game target.
- The harness defaults to `data/players_normalized.csv` when present.
