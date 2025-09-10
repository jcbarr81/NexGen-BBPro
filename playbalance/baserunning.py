"""Baserunning helpers for the play-balance engine."""
from __future__ import annotations

from random import Random

from .config import PlayBalanceConfig


def lead_level(cfg: PlayBalanceConfig, runner_sp: float) -> int:
    """Return lead level (0 or 2) based on runner speed.

    Runners take a long lead only when their speed rating meets or exceeds
    ``cfg.longLeadSpeed``.
    """

    # Only particularly fast runners take an aggressive lead which is modelled
    # as ``2``. Everyone else stays with the conservative ``0`` lead.
    return 2 if runner_sp >= getattr(cfg, "longLeadSpeed", 0) else 0


def pickoff_scare(
    cfg: PlayBalanceConfig,
    runner_sp: float,
    lead: int,
    rng: Random | None = None,
) -> int:
    """Return adjusted lead after a pickoff attempt.

    When a pickoff throw nearly succeeds and the runner's speed is at or
    below ``cfg.pickoffScareSpeed`` there is a 10% chance the runner retreats
    to a short lead.
    """

    if rng is None:
        rng = Random()
    if lead > 0 and runner_sp <= getattr(cfg, "pickoffScareSpeed", 0):
        # A near-miss pickoff may scare slower runners back to a short lead.
        if rng.random() < 0.1:
            return 0
    return lead


__all__ = ["lead_level", "pickoff_scare"]
