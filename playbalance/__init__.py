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
)
from .ratings import (  # noqa: F401
    clamp_rating,
    combine_offense,
    combine_slugging,
    combine_defense,
)
from .probability import (  # noqa: F401
    clamp01,
    roll,
    weighted_choice,
    prob_or,
    prob_and,
)
from .state import PlayerState, BaseState, GameState  # noqa: F401

__all__ = [
    "PlayBalanceConfig",
    "load_config",
    "load_benchmarks",
    "park_factors",
    "weather_profile",
    "league_averages",
    "clamp_rating",
    "combine_offense",
    "combine_slugging",
    "combine_defense",
    "clamp01",
    "roll",
    "weighted_choice",
    "prob_or",
    "prob_and",
    "PlayerState",
    "BaseState",
    "GameState",
]
