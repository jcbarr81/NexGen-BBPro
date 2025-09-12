"""Compatibility layer exposing simulation primitives for the play-balance engine.

This module provides a thin wrapper around the full-featured simulation
implementation in :mod:`logic.simulation`.  Importing through this module
allows the rest of the ``playbalance`` package to depend solely on the
``playbalance`` namespace while a dedicated simulation engine is developed.
"""
from __future__ import annotations

from logic.simulation import (
    FieldingState as _FieldingState,
    GameSimulation as _GameSimulation,
    PitcherState as _PitcherState,
    TeamState as _TeamState,
    generate_boxscore as _generate_boxscore,
)

# Re-export the simulation classes so callers can import them from
# ``playbalance.simulation`` without touching the legacy ``logic`` package.
FieldingState = _FieldingState
PitcherState = _PitcherState
TeamState = _TeamState
GameSimulation = _GameSimulation

generate_boxscore = _generate_boxscore

__all__ = [
    "FieldingState",
    "PitcherState",
    "TeamState",
    "GameSimulation",
    "generate_boxscore",
]
