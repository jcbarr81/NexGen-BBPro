# Playbalance Tuning Tasks — 2025-10-31

Tracked priorities coming out of the latest full-season sim and batter diagnostics.

- **Priority 1 – Restore contact throughput**  
  Adjust the contact limiter stack so league K% and pitches/PA move back toward MLB ranges. Raise `contactFactorBase`, pull `contactFactorDiv` down, and cut `missChanceScale`/lift `contactOutcomeScale` in `playbalance/sim_config.py:446` and `:462`, then confirm the resulting swing-contact math in `playbalance/batter_ai.py:603`.

- **Priority 2 – Ease 2-1/2-2 discipline penalties**  
  Reduce the extra take bias on leverage counts by loosening the overrides in `playbalance/sim_config.py:278`–`:318` (raw scales, rating offsets, penalty multipliers, chase chance) so called-strike gaps shrink and strikeouts normalize.

- **Priority 3 – Rebalance pitcher objectives on hitter counts**  
  Make pitcher intent less zone-heavy when behind by softening the negative zone biases and nudging waste bias up in `playbalance/sim_config.py:428`–`:435`, targeting MLB-level ball rates without reopening early-count aggression.

- **Priority 4 – Rein in steal spam**  
  Tone down baserunning aggression and restore realistic speed adjustments around `playbalance/sim_config.py:164` so steal attempts fall and success percentage climbs toward ~75%.

- **Priority 5 – Reset diagnostics after each pass**  
  After any tuning update, rerun `scripts/collect_batter_decisions.py` and a full-season sim to verify P/PA, BB%, K%, HR/PA, SB%, and starter workloads are converging before moving on.

