"""Utilities for generating team logos.

Logos are created using OpenAI's image generation API and written to
``logo/teams`` relative to the project root. Each logo is named after the
team's ID (lower-cased). Existing logos in the output directory are removed
before new ones are generated. If the OpenAI client is unavailable a fallback
to the legacy :mod:`images.auto_logo` generator can be enabled.
"""

from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path
from typing import Callable, List, Optional

from PIL import Image

from utils.openai_client import client
from utils.team_loader import load_teams
from utils.path_utils import get_base_dir


def _auto_logo_fallback(
    teams: List[object],
    out_dir: str,
    size: int,
    progress_callback: Optional[Callable[[int, int], None]],
) -> None:
    """Generate logos using the legacy ``images.auto_logo`` module."""

    from images.auto_logo import (
        TeamSpec,
        generate_logo,
        save_logo,
        _seed_from_name,
    )  # pragma: no cover

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

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for spec in specs:
        img = generate_logo(spec, size=1024)
        if size != 1024:
            img = img.resize((size, size), Image.LANCZOS)
        filename = f"{(spec.abbrev or (spec.location + ' ' + spec.mascot)).replace(' ', '_').lower()}.png"
        path = out_dir / filename
        save_logo(img, str(path))
        completed += 1
        if progress_callback:
            progress_callback(completed, total)


def generate_team_logos(
    out_dir: str | None = None,
    size: int = 512,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    allow_auto_logo: bool = True,
) -> str:
    """Generate logos for all teams and return the output directory.

    Parameters
    ----------
    out_dir:
        Optional output directory. Defaults to ``logo/teams`` relative to the
        project root.
    size:
        Pixel size for the square logos. Images are always generated at
        ``1024x1024`` and then resized to this value when saved.
    progress_callback:
        Optional callback receiving ``(completed, total)`` after each logo is
        saved.
    allow_auto_logo:
        When ``True`` (the default) and the OpenAI client is not configured,
        fall back to the older :mod:`images.auto_logo` generator. Set to
        ``False`` to raise a ``RuntimeError`` instead.
    """

    teams = load_teams("data/teams.csv")

    if out_dir is None:
        out_dir = get_base_dir() / "logo" / "teams"
    else:
        out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    # Remove any existing logos so stale files do not persist
    for existing in out_dir.glob("*.png"):
        existing.unlink(missing_ok=True)

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
            size="1024x1024",
        )
        b64 = result.data[0].b64_json
        image_bytes = base64.b64decode(b64)
        path = out_dir / f"{t.team_id.lower()}.png"
        with Image.open(BytesIO(image_bytes)) as img:
            if size != 1024:
                img = img.resize((size, size), Image.LANCZOS)
            img.save(path, format="PNG")
        if progress_callback:
            progress_callback(idx, total)

    return str(out_dir)


__all__ = ["generate_team_logos"]

