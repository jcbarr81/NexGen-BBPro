# Simulation & AI

## Task List

- [x] Rebalance strikeout and walk probabilities—review the contact/approach calculations in playbalance/offense.py and the pitcher ability weighting in the AI modules so league BB% and K% land near MLB’s 8%/22%. A small global bump to pitcher whiff ability or a reduction to hitter contact caps can move both hits and strikeouts in the right direction.
- [x] Dial back intentional walks by lowering defManPitchAroundToIBBPct and the related pitch-around baselines in playbalance/PBINI.txt:157 (and corresponding defaults in playbalance/playbalance_config.py). That will free more plate appearances for organic BB and SO outcomes.
- [x] Fix the baserunning economy: raise stealSuccessBasePct, increase stealMinSuccessProb, or raise stealAttemptMinProb (playbalance/playbalance_config.py:226-429), and confirm the gating logic in playbalance/simulation.py:2998-3053 keeps sub-55% chances from being attempted. You may also need to lower offManStealChancePct to keep attempts near MLB’s 0.6 per game.
- [x] Boost power production by slightly increasing exit velocity or HR probability on fly balls in the batted-ball physics (playbalance/physics.py) so HR/FB trends toward 11% without over-inflating total hits.
- [x] Restore HBP presence and trim pitch counts by adding a modest HBP branch in the pitch-resolution logic (see playbalance/simulation.py pitch outcome section) and nudging strike/ball weights toward the MLB 60/40 mix; that should also help normalize pitches per PA.
- [x] Tighten bullpen decision rules in playbalance/bullpen.py and playbalance/defensive_manager.py: enforce dedicated closer/setup slots (e.g., use roster role tags), forbid multi-inning outings for those roles, and respect rest days/pitch counts so a pitcher rarely exceeds ~70 games or 75 IP in relief.
- [x] Cap save opportunities by boosting conversion logic: ensure the current pitcher stays in until the game ends when a save is on the line, and track blown saves explicitly to prevent re-crediting the same opportunity multiple times.
- [x] Separate starter vs. reliever usage via rotation depth checks (e.g., guard clauses in playbalance/bullpen.py before selecting a starter to finish games) and confirm five-man rotations are populated for every club to avoid LOS-style gaps.
