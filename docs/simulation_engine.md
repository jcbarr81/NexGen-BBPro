# Simulation Engine Overview

This document describes how NexGen BBPro simulates a baseball game and the key
modules involved in decision making and physics.

## Player State Data Structures

Several dataclasses track in-game state and statistics:

- **`BatterState`**, **`PitcherState`**, and **`FieldingState`** capture
  performance for individual players during the game【F:logic/simulation.py†L33-L146】
- **`TeamState`** maintains the current lineup, bench, pitchers, base runners and
  cumulative team stats for each side【F:logic/simulation.py†L149-L192】

These structures are created before the game starts and are updated throughout
play as events occur.

## GameSimulation

The `GameSimulation` class orchestrates the game loop.  It owns references to
state for both teams and composes the managers and AI helpers that drive
strategy and outcomes【F:logic/simulation.py†L193-L200】【F:logic/simulation.py†L10-L18】.
It also tracks situational details such as defensive alignment, pitcher fatigue
and environmental conditions.

During play the simulation:

1. Sets the defensive alignment before each plate appearance.
2. Uses `PitcherAI` to choose pitch type and `BatterAI` to decide whether to
   swing.
3. Delegates physical calculations—like pitch speed or batted ball flight—to the
   `Physics` helper.
4. Updates statistics in the player and team state objects.
5. Consults the `SubstitutionManager` for pinch hitters, pitching changes and
   other personnel moves.

## AI and Managers

A collection of focused modules encapsulate specific decision making:

- `PitcherAI` selects pitches and objectives using configurable weights and
  tracks which pitches have been established【F:logic/pitcher_ai.py†L1-L33】【F:logic/pitcher_ai.py†L48-L60】.
- `BatterAI` applies count-based adjustments to swing decisions and computes the
  contact quality of a swing【F:logic/batter_ai.py†L1-L39】【F:logic/batter_ai.py†L58-L70】.
- `SubstitutionManager` evaluates pinch hitting, defensive replacements and
  bullpen usage using ratings derived from player attributes and configuration
  chances【F:logic/substitution_manager.py†L1-L108】.
- Offensive and defensive strategy is delegated to `OffensiveManager` and
  `DefensiveManager` (not shown here), while `FieldingAI` positions fielders
  according to batter tendencies.

## Physics Helpers

The `Physics` class provides deterministic calculations for movement speed,
reaction delays, throwing mechanics and pitch characteristics.  All formulas are
parameterised by the `PlayBalanceConfig` so tests can verify configuration
impact【F:logic/physics.py†L8-L75】【F:logic/physics.py†L92-L130】.

## Foul Balls

Foul tips are modeled through `_foul_probability`, which derives the chance of a
foul ball from player ratings, pitch location and configuration. The formula
starts with `foulStrikeBasePct`—the share of strikes that are fouls in MLB. It is
derived from an `18.3%` foul-per-pitch rate and a `65.9%` strike rate, yielding a
baseline `27.8%` of strikes that become fouls—and adjusts it by
`foulContactTrendPct` (default 1.5 percentage points) for every 20 point contact
edge the batter holds over the pitcher. The resulting percentage is converted to
a foul-to-balls-in-play ratio and then scaled so that an average matchup yields a
1:1 split between foul balls and contacted pitches put in play.
Out-of-zone distance reduces the probability while a complete pitch misread
boosts it, nudging such swings toward foul tips instead of whiffs. The final
probability is clamped between 0 and 0.5 to avoid unrealistic extremes【F:logic/simulation.py†L1339-L1369】.

Historical foul-strike rates have changed gradually over time:

| Season | Foul/Strike % |
|-------:|--------------:|
| 1988   | 23.0% |
| 1998   | 25.1% |
| 2008   | 26.4% |
| 2018   | 27.3% |
| 2023   | 27.8% |

To explore these eras, tweak the `PlayBalanceConfig` values. Setting
`foulStrikeBasePct` to one of the percentages above shifts the league-wide foul
rate, while `foulContactTrendPct` controls how strongly batter contact versus
pitcher movement affects foul frequency【F:logic/playbalance_config.py†L136-L138】.

## Statistics

At the end of each play, raw totals are converted into derived and rate stats
using helpers in `logic.stats`.  For example, batting rates include batting
average, on-base percentage and slugging percentage computed from counting
stats【F:logic/stats.py†L9-L60】.

## Configuration

`PlayBalanceConfig` exposes the many tunable values that influence all of the
above modules.  By adjusting this configuration, tests and future gameplay modes
can explore different balancing options for the simulation engine.

Key entries now available include:

- **`exitVeloBase`** – baseline exit velocity applied to all batted balls.
- **`exitVeloPHPct`** – percentage boost to exit velocity for pinch hitters.
- **`vertAngleGFPct`** – ground/fly ratio adjustment for vertical launch angles.
- **`sprayAnglePLPct`** – pull/line tendency applied to spray angle calculations.
- **`minMisreadContact`** – minimum contact quality applied when a batter
  completely misidentifies a pitch.

