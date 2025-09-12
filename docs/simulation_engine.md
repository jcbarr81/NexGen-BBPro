# Simulation Engine Overview

This document describes how NexGen BBPro simulates a baseball game and the key
modules involved in decision making and physics.

## Player State Data Structures

Several dataclasses track in-game state and statistics:

- **`BatterState`** and **`FieldingState`** capture performance for individual
  players during the game【F:playbalance/simulation.py†L33-L118】, while **`PitcherState`**
  records pitch-level totals in the play-balance engine【F:playbalance/state.py†L20-L27】
- **`TeamState`** maintains the current lineup, bench, pitchers, base runners and
  cumulative team stats for each side【F:playbalance/simulation.py†L121-L178】

These structures are created before the game starts and are updated throughout
play as events occur.

## GameSimulation

The `GameSimulation` class orchestrates the game loop.  It owns references to
state for both teams and composes the managers and AI helpers that drive
strategy and outcomes【F:playbalance/simulation.py†L193-L200】【F:playbalance/simulation.py†L10-L18】.
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
  tracks which pitches have been established【F:playbalance/pitcher_ai.py†L1-L33】【F:playbalance/pitcher_ai.py†L48-L60】.
- `BatterAI` applies count-based adjustments to swing decisions and computes the
  contact quality of a swing【F:playbalance/batter_ai.py†L1-L39】【F:playbalance/batter_ai.py†L58-L70】.
- `SubstitutionManager` evaluates pinch hitting, defensive replacements and
  bullpen usage using ratings derived from player attributes and configuration
  chances【F:playbalance/substitution_manager.py†L1-L108】.
- Offensive and defensive strategy is delegated to `OffensiveManager` and
  `DefensiveManager` (not shown here), while `FieldingAI` positions fielders
  according to batter tendencies.

## Physics Helpers

The `Physics` class provides deterministic calculations for movement speed,
reaction delays, throwing mechanics and pitch characteristics.  All formulas are
parameterised by the `PlayBalanceConfig` so tests can verify configuration
impact【F:playbalance/physics.py†L8-L75】【F:playbalance/physics.py†L92-L130】.

## Foul Balls

MLB pitch tracking shows roughly **18%** of all pitches are fouled off and a
similar **18%** are put into play. When batters put the ball in play, about
**42.3%** become grounders and roughly
**30–35%** are fly balls, with the remainder line drives or bunts. These averages
seed the simulation's batted-ball model. `PlayBalanceConfig` exposes knobs to
tune them: `foulPitchBasePct` sets the foul-per-pitch rate and
`ballInPlayPitchPct` the share of pitches turned into balls in play
【F:playbalance/playbalance_config.py†L142-L148】【F:playbalance/playbalance_config.py†L154】,
while `groundBallBaseRate` and `flyBallBaseRate` establish grounder and fly-ball
shares that influence vertical launch angles【F:playbalance/playbalance_config.py†L134-L135】.
A slight negative `vertAngleGFPct` flattens trajectories, nudging extreme
ground- or fly-ball hitters toward the middle. The defaults now bias outcomes
toward an even **50/50** split rather than the previous MLB-average of roughly
45% grounders and 55% flies.

## Statistics

At the end of each play, raw totals are converted into derived and rate stats
using helpers in `playbalance.stats`.  For example, batting rates include batting
average, on-base percentage and slugging percentage computed from counting
stats【F:playbalance/stats.py†L9-L60】.

## Configuration

`PlayBalanceConfig` exposes the many tunable values that influence all of the
above modules.  By adjusting this configuration, tests and future gameplay modes
can explore different balancing options for the simulation engine.

Key entries now available include:

- **`exitVeloBase`** – baseline exit velocity applied to all batted balls.
- **`exitVeloPHPct`** – percentage boost to exit velocity for pinch hitters.
- **`hit1BProb`**, **`hit2BProb`**, **`hit3BProb`**, **`hitHRProb`** – distribution of hit outcomes
  tuned to MLB rates (63% singles, 21% doubles, 2% triples, 14% homers)【F:playbalance/playbalance_config.py†L144-L147】.
- **`groundBallBaseRate`** – baseline percentage of balls in play that become grounders【F:playbalance/playbalance_config.py†L140】.
- **`flyBallBaseRate`** – baseline percentage of balls in play that become fly balls【F:playbalance/playbalance_config.py†L141】.
- **`vertAngleGFPct`** – percentage adjustment to vertical launch angle based on a
  batter's ground/fly rating; the default ``-5`` gently flattens launch angles
  toward an even ground/fly distribution.
- **`sprayAnglePLPct`** – pull/line tendency applied to spray angle calculations.
- **`minMisreadContact`** – minimum contact quality applied when a batter
  completely misidentifies a pitch.  The value acts as a floor scaled by the
  batter's contact rating so weak hitters still produce occasional foul tips
  without generating excessive hits.
- **`contactQualityScale`** – multiplier applied to raw contact quality. Values
  above ``1.0`` generate more fouls and balls in play while lower values
  increase whiffs.
- **`contactAbilityScale`** – scales contact quality based on a batter's
  contact rating, letting elite hitters put more balls in play.
- **`contactDisciplineScale`** – scales contact quality using the plate
  discipline calculation so patient hitters make more quality contact.
- **`fielderReactionScale`** – boosts the probability that a fielder reacts to
  and catches a ball in play.
- **`throwSuccessScale`** – adjusts the chance of completing an accurate throw,
  improving double plays and other outs.

