"""Generate player avatars using OpenAI's image model."""
from __future__ import annotations

import base64
import os
from typing import Dict

from utils.openai_client import client
from utils.team_loader import load_teams


def _infer_ethnicity(name: str) -> str:
    """Very naive placeholder for ethnicity inference."""
    return "unspecified"


def _team_colors(team_id: str) -> Dict[str, str]:
    teams = {t.team_id: t for t in load_teams("data/teams.csv")}
    team = teams.get(team_id)
    if team:
        return {"primary": team.primary_color, "secondary": team.secondary_color}
    return {"primary": "#000000", "secondary": "#ffffff"}


def generate_avatar(name: str, team_id: str, out_file: str) -> str:
    """Generate an avatar for ``name`` and save it to ``out_file``.

    Parameters
    ----------
    name:
        Player's full name.
    team_id:
        Identifier of the player's team to derive colors.
    out_file:
        Path where the resulting PNG should be written.
    """
    if client is None:  # pragma: no cover - depends on external package
        raise RuntimeError("OpenAI client is not configured")

    colors = _team_colors(team_id)
    ethnicity = _infer_ethnicity(name)
    prompt = (
        f"Portrait of {name}, a {ethnicity} baseball player, wearing team colors "
        f"{colors['primary']} and {colors['secondary']}."
    )
    result = client.images.generate(model="gpt-image-1", prompt=prompt, size="512x512")
    b64 = result.data[0].b64_json
    image_bytes = base64.b64decode(b64)
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "wb") as f:
        f.write(image_bytes)
    return out_file

__all__ = ["generate_avatar"]
