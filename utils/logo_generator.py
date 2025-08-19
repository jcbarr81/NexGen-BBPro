"""Utilities for generating team logos.

Logos are created using OpenAI's image generation API and written to
``logo/teams`` relative to the project root. Each logo is named after the
team's ID (lower-cased). If the OpenAI client is unavailable a fallback to the
legacy :mod:`images.auto_logo` generator can be enabled.
"""

from __future__ import annotations

import base64
import os
from typing import Callable, List, Optional

from utils.openai_client import client
from utils.team_loader import load_teams


def _auto_logo_fallback(
    teams: List[object],
    out_dir: str,
    size: int,
    progress_callback: Optional[Callable[[int, int], None]],
) -> None:
    """Generate logos using the legacy ``images.auto_logo`` module."""

    from images.auto_logo import TeamSpec, batch_generate, _seed_from_name  # pragma: no cover

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

    total = len(specs)
    completed = 0

    def cb(spec: TeamSpec, path: str) -> None:
        nonlocal completed
        completed += 1
        if progress_callback:
            progress_callback(completed, total)

    batch_generate(specs, out_dir=out_dir, size=size, callback=cb)


def generate_team_logos(
    out_dir: str | None = None,
    size: int = 512,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    allow_auto_logo: bool = False,
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
    allow_auto_logo:
        When ``True`` and the OpenAI client is not configured, fall back to the
        older :mod:`images.auto_logo` generator.
    """

    teams = load_teams("data/teams.csv")

    if out_dir is None:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        out_dir = os.path.join(base_dir, "logo", "teams")
    os.makedirs(out_dir, exist_ok=True)

    if client is None:
        if allow_auto_logo:
            _auto_logo_fallback(teams, out_dir, size, progress_callback)
            return out_dir
        raise RuntimeError("OpenAI client is not configured")

    total = len(teams)
    for idx, t in enumerate(teams, start=1):
        prompt = (
            f"Professional baseball logo for the {t.city} {t.name}. "
            f"Use primary color {t.primary_color} and secondary color {t.secondary_color}."
        )
        result = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size=f"{size}x{size}",
        )
        b64 = result.data[0].b64_json
        image_bytes = base64.b64decode(b64)
        path = os.path.join(out_dir, f"{t.team_id.lower()}.png")
        with open(path, "wb") as f:
            f.write(image_bytes)
        if progress_callback:
            progress_callback(idx, total)

    return out_dir


__all__ = ["generate_team_logos"]

