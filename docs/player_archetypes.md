# Player Archetype Blueprint

This document defines the target archetypes for hitters and pitchers so we can preserve variety (contact, power, balanced bats; power/finesse/balanced arms) while still meeting league-average benchmarks. Each archetype specifies rating envelopes, target share, and random jitter so individual players remain unique.

## Hitters

The generator uses five hitter templates defined in `playbalance/player_generator.py`.
Weights are the global defaults before position overrides (see
`HITTER_POSITION_TEMPLATE_WEIGHTS` for position-specific mixes).

| Archetype | Default Share | Core Bands (percentile ranges) | Notes |
|-----------|---------------|-------------------------------|-------|
| **Power** | 22% | `PH` 82–98, `CH` 35–65, `SP` 20–60, `EYE` 30–60 | Pull-heavy (`PL` 60–90), lower GB tendency |
| **Average** | 18% | `CH` 40–65, `PH` 40–65, `SP` 35–60, `EYE` 40–65 | Neutral profile with mid GB rates |
| **Spray** | 18% | `CH` 70–95, `PH` 30–60, `SP` 45–80, `EYE` 60–90 | Low pull, higher GB rates |
| **Balanced** | 26% | `CH` 48–78, `PH` 48–78, `SP` 40–70, `EYE` 45–72 | Blended contact/power |
| **Speed** | 16% | `CH` 55–80, `PH` 20–50, `SP` 85–99, `EYE` 55–85 | Top-end speed with low pull |

Randomness: ratings are sampled from the underlying normalized distributions
using the percentile bands above, then small jitter is applied. Constraints
ensure power bats stay power-heavy, spray hitters stay contact-heavy, and
balanced hitters remain close in `CH`/`PH`.

## Pitchers

Pitcher templates are also defined in `playbalance/player_generator.py` and are
split between starters and relievers. The starter/reliever split defaults to
~60/40 when creating random pitchers.

### Starters

| Archetype | Default Share | Core Bands (percentile ranges) | Notes |
|-----------|---------------|-------------------------------|-------|
| **Power SP** | 25% | `ARM` 80–98, `CTRL` 45–70, `MOV` 55–80, `END` 70–92 | Power-heavy pitch mix |
| **Finesse SP** | 20% | `ARM` 45–70, `CTRL` 75–95, `MOV` 70–90, `END` 65–88 | Control/movement first |
| **Groundball SP** | 18% | `ARM` 55–80, `CTRL` 55–78, `MOV` 65–85, `END` 65–88 | High `GF` bias |
| **Balanced SP** | 22% | `ARM` 60–82, `CTRL` 60–80, `MOV` 60–82, `END` 65–88 | Even profile |
| **Workhorse SP** | 15% | `ARM` 55–78, `CTRL` 60–80, `MOV` 60–82, `END` 82–99 | Endurance bump |

### Relievers

| Archetype | Default Share | Core Bands (percentile ranges) | Notes |
|-----------|---------------|-------------------------------|-------|
| **Closer** | 12% | `ARM` 90–99, `CTRL` 55–75, `MOV` 70–92, `END` 20–45 | Closer pitch profile |
| **Power RP** | 22% | `ARM` 78–97, `CTRL` 45–70, `MOV` 55–80, `END` 32–60 | Velocity-first |
| **Finesse RP** | 20% | `ARM` 50–75, `CTRL` 70–92, `MOV` 68–88, `END` 32–60 | Command profile |
| **Groundball RP** | 18% | `ARM` 60–82, `CTRL` 55–78, `MOV` 60–84, `END` 32–60 | High `GF` bias |
| **Long Relief** | 8% | `ARM` 55–78, `CTRL` 60–80, `MOV` 60–82, `END` 60–82 | Lower leverage bulk innings |

Pitch profiles steer the secondary pitch mix (power, finesse, groundball,
balanced, closer). Each pitcher draws 2-5 pitches based on role, with
fastball bands tied to `ARM` and primaries/seconaries sampled from the
profile bands.

## Validation Targets

- Run `docs/tools/player_rating_report.py` after regeneration/loading transforms. Expect:
  - Hitter archetype split roughly matching the default weights (power/average/spray/balanced/speed), allowing for position overrides.
  - Pitching archetype table reflecting the starter/reliever shares above.
  - Mean ratings within ±10% of latest MLB Statcast-derived averages (document to be added in future task).

- Store benchmark histograms (CSV or JSON) next to the report so future runs can diff distributions automatically.
