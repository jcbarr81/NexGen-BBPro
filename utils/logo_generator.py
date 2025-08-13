"""Utilities for generating team logos.

Creates simple team logos using the :mod:`images.auto_logo` module. Logos are
written to ``logo/teams`` relative to the repository root and named after the
team's ID (lower‑cased).
"""
from __future__ import annotations

import os
from typing import Callable, List, Optional

from images.auto_logo import TeamSpec, batch_generate, _seed_from_name
from utils.team_loader import load_teams


def generate_team_logos(
    out_dir: str | None = None,
    size: int = 512,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> str:
    """Generate logos for all teams and return the output directory.

    Parameters
    ----------
    out_dir:
        Optional output directory. Defaults to ``logo/teams`` relative to the
        project root.
    size:
        Pixel size for the generated square logos.
    progress_callback:
        Optional callback receiving ``(completed, total)`` after each logo is
        saved.
    """

    teams = load_teams("data/teams.csv")
    specs: List[TeamSpec] = []
    for t in teams:
        specs.append(
            TeamSpec(
                location=t.city,
                mascot=t.name,
                primary=t.primary_color,
                secondary=t.secondary_color,
                abbrev=t.team_id,
                template="auto",
                seed=_seed_from_name(t.name, t.city),
            )
        )

    if out_dir is None:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        out_dir = os.path.join(base_dir, "logo", "teams")
    os.makedirs(out_dir, exist_ok=True)
    total = len(specs)
    completed = 0

    def cb(spec: TeamSpec, path: str) -> None:
        nonlocal completed
        completed += 1
        if progress_callback:
            progress_callback(completed, total)

    batch_generate(specs, out_dir=out_dir, size=size, callback=cb)
    return out_dir
