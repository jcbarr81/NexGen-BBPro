"""Utility helpers for computing combined player ratings.

These functions are intentionally light-weight; they provide reasonably
documented behaviour without yet replicating all of the formulas contained in
``PBINI.txt``.  The helpers will be expanded as later modules require more
fidelity.
"""
from __future__ import annotations

from typing import Any


def clamp_rating(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    """Clamp ``value`` between ``minimum`` and ``maximum``."""

    return max(minimum, min(maximum, value))


def _weights(cfg: Any | None, defaults: tuple[float, ...], names: tuple[str, ...]) -> tuple[float, ...]:
    """Return tuple of weights pulling values from ``cfg`` when available."""

    if not cfg:
        return defaults
    return tuple(getattr(cfg, name, default) for name, default in zip(names, defaults))


def combine_offense(
    contact: float,
    power: float,
    discipline: float = 50.0,
    cfg: Any | None = None,
) -> float:
    """Return a blended offensive rating on a ``0``-``100`` scale.

    Weighting factors may be supplied in ``cfg`` using the attribute names
    ``offenseContactWt``, ``offensePowerWt`` and ``offenseDisciplineWt``.
    """

    w_contact, w_power, w_disc = _weights(
        cfg,
        (0.5, 0.4, 0.1),
        ("offenseContactWt", "offensePowerWt", "offenseDisciplineWt"),
    )
    rating = (contact * w_contact) + (power * w_power) + (discipline * w_disc)
    return clamp_rating(rating)


def combine_slugging(power: float, discipline: float, cfg: Any | None = None) -> float:
    """Return a blended slugging rating on a ``0``-``100`` scale.

    Weighting attributes ``slugPowerWt`` and ``slugDisciplineWt`` may be present
    on ``cfg`` to tweak the combination.
    """

    w_power, w_disc = _weights(
        cfg,
        (0.8, 0.2),
        ("slugPowerWt", "slugDisciplineWt"),
    )
    rating = (power * w_power) + (discipline * w_disc)
    return clamp_rating(rating)


def combine_defense(
    fielding: float,
    arm: float,
    range_: float = 50.0,
    cfg: Any | None = None,
) -> float:
    """Return a blended defensive rating on a ``0``-``100`` scale.

    The configuration may provide weighting attributes ``defenseFieldingWt``,
    ``defenseArmWt`` and ``defenseRangeWt``.
    """

    w_field, w_arm, w_range = _weights(
        cfg,
        (0.6, 0.3, 0.1),
        ("defenseFieldingWt", "defenseArmWt", "defenseRangeWt"),
    )
    rating = (fielding * w_field) + (arm * w_arm) + (range_ * w_range)
    return clamp_rating(rating)


__all__ = [
    "clamp_rating",
    "combine_offense",
    "combine_slugging",
    "combine_defense",
]
