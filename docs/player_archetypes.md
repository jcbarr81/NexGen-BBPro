# Player Archetype Blueprint

This document defines the target archetypes for hitters and pitchers so we can preserve variety (contact, power, balanced bats; power/finesse/balanced arms) while still meeting league-average benchmarks. Each archetype specifies rating envelopes, target share, and random jitter so individual players remain unique.

## Hitters

| Archetype | Target Share | Core Ratings | Secondary Characteristics |
|-----------|--------------|--------------|---------------------------|
| **Contact Specialist** | 35% | `CH` ≥ `PH` + 8, `CH` 65–90, `PH` capped at 65 | `SP` 55–80, `VL` 60–85 to reflect discipline; random ±5 jitter per attribute |
| **Power Bat** | 20% | `PH` ≥ `CH` + 8, `PH` 70–95, `CH` capped at 65 | `SP` 40–70, `VL` 45–65; add a 10% chance for low-speed sluggers vs rare power/speed combos |
| **Balanced** | 35% | `CH` and `PH` both 55–80 with |`CH`−`PH`| < 8 | `SP` 50–75, `VL` 50–70; use Gaussian noise (σ≈5) so some lean slightly toward contact or power |
| **Speed/Discipline Wildcard** | 10% | Starts from Balanced but forces `SP` ≥ 75 and `VL` ≥ 70 | Assign randomly across contact/power emphasis to create leadoff-style players |

Randomness: after assigning an archetype, sample each rating from the defined range using a truncated normal (μ at midpoint, σ=5) then add ±3 uniform jitter. Clamp to 30–99 to avoid extremes.

## Pitchers

### Starters

| Archetype | Target Share | Core Ratings | Notes |
|-----------|--------------|--------------|-------|
| **Power Starter** | 30% of starters | `FB` ≥ 72, `FB` ≥ `control` + 8, `movement` 60–80 | Endurance 70–90, Control 55–70; sprinkle in two plus secondary pitches (random 70–85) |
| **Finesse Starter** | 25% | `control` ≥ 70, `control` ≥ `FB` + 8 | Velocity 58–72, Movement 70–88, Endurance 65–85. Increase `hold_runner` 60–80 to reflect situational control |
| **Balanced Starter** | 35% | `FB` 65–78, `control` 60–75, |`FB`−`control`| < 8 | Movement 65–80, Endurance 65–85. Randomly boost one breaking ball to create pitch-to-contact vs swing-and-miss flavors |
| **Knuckle/Curve Specialist** | 10% | One secondary pitch 80–95 (e.g., knuckle, curve) | FB 55–70, Control 60–75, Movement 75–90. Used to add unique gameplay moments |

### Relievers

Split bullpen into:

- **Closers (10%)**: Velocity 80–99, Control 60–75, Movement 65–85, Endurance 30–45. At least one secondary pitch ≥80.
- **Setup (15%)**: Velocity 75–95, Control 60–78, Movement 60–80. Endurance 40–55.
- **Middle Relief (50%)**: Mixed archetypes; velocity 65–85, Control 55–72, Movement 55–75, Endurance 45–65.
- **Long Relief (25%)**: Essentially balanced starters with reduced endurance (55–70) and velocity (62–78).

Archetype assignment leverages `preferred_pitching_role`:

1. Tag each pitcher as starter/bullpen based on roster CSV or ratings (endurance ≥ 70 → starter).
2. Within each bucket, sample archetypes according to the shares above.
3. For pitchers with explicit role tags (closer, setup, etc.), lock them into the matching archetype and only randomize ratings within the specified ranges.

Randomness strategy mirrors hitters: sample from truncated normals per rating and add ±3 uniform jitter so no two pitchers share identical stat lines. Secondary pitches: randomly choose 2–3 pitch types per pitcher, then seed ratings according to archetype (e.g., power starters get slider 70–85, changeup 55–75).

## Validation Targets

- Run `docs/tools/player_rating_report.py` after regeneration/loading transforms. Expect:
  - Contact vs power vs balanced hitters within ±3 percentage points of the 35/20/35 split (speed/disc wildcard will appear within the balanced bucket but documented separately).
  - Pitching archetype table reflecting the starter/reliever shares above.
  - Mean ratings within ±10% of latest MLB Statcast-derived averages (document to be added in future task).

- Store benchmark histograms (CSV or JSON) next to the report so future runs can diff distributions automatically.
