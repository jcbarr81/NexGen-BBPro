"""Play-balance simulation package.

This package hosts the next generation simulation engine derived from
PBINI.txt configuration and MLB league benchmarks. The modules are
organized for clarity and unit-testability.

This is an early scaffolding of the full engine.
"""

from .config import PlayBalanceConfig, load_config  # noqa: F401
from .benchmarks import (  # noqa: F401
    load_benchmarks,
    park_factors,
    weather_profile,
    league_averages,
    get_park_factor,
    league_average,
)
from .ratings import (  # noqa: F401
    clamp_rating,
    combine_offense,
    combine_slugging,
    combine_defense,
    rating_to_pct,
    pct_to_rating,
)
from .probability import (  # noqa: F401
    clamp01,
    roll,
    weighted_choice,
    prob_or,
    prob_and,
    pct_modifier,
    adjustment,
    dice_roll,
    final_chance,
)
from .state import PlayerState, BaseState, GameState  # noqa: F401
from .defense import (  # noqa: F401
    bunt_charge_chance,
    hold_runner_chance,
    pickoff_chance,
    pitch_out_chance,
    pitch_around_chance,
    outfielder_position,
    fielder_template,
)
from .offense import (  # noqa: F401
    steal_chance,
    maybe_attempt_steal,
    hit_and_run_chance,
    maybe_hit_and_run,
    sacrifice_bunt_chance,
    maybe_sacrifice_bunt,
    squeeze_chance,
    maybe_squeeze,
)

__all__ = [
    "PlayBalanceConfig",
    "load_config",
    "load_benchmarks",
    "park_factors",
    "weather_profile",
    "league_averages",
    "get_park_factor",
    "league_average",
    "clamp_rating",
    "combine_offense",
    "combine_slugging",
    "combine_defense",
    "rating_to_pct",
    "pct_to_rating",
    "clamp01",
    "roll",
    "weighted_choice",
    "prob_or",
    "prob_and",
    "pct_modifier",
    "adjustment",
    "dice_roll",
    "final_chance",
    "bunt_charge_chance",
    "hold_runner_chance",
    "pickoff_chance",
    "pitch_out_chance",
    "pitch_around_chance",
    "outfielder_position",
    "fielder_template",
    "steal_chance",
    "maybe_attempt_steal",
    "hit_and_run_chance",
    "maybe_hit_and_run",
    "sacrifice_bunt_chance",
    "maybe_sacrifice_bunt",
    "squeeze_chance",
    "maybe_squeeze",
    "PlayerState",
    "BaseState",
    "GameState",
]
