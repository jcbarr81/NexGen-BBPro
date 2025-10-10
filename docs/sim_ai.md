# Simulation & AI

## Task List

- [ ] Introduce pitch and plate-appearance event callbacks on `GameSimulation` so every swing, substitution, and physics result can feed live visualizations or machine-learning analyzers (`playbalance/simulation.py:151`).
- [ ] Replace the placeholder training camp that only toggles `player.ready` with an attribute progression model driven by historical benchmarks and XP budgets (`playbalance/training_camp.py:1`); tie the outcomes into player potentials before Opening Day.
- [ ] Add a schedule sandbox that lets admins branch, edit, and replay parts of the calendar using `SeasonSimulator`'s hooks for draft day and `after_game` callbacks (`playbalance/season_simulator.py:17`) to test weather postponements or alternate playoff formats.
- [ ] Enrich the pitcher/batter AI to learn during games: persist pitch selection tendencies and batter hot zones between at-bats instead of recalculating from static ratings (`playbalance/pitcher_ai.py:102`), laying groundwork for adaptive difficulty.
