"""Generate player avatars using OpenAI's image model."""
from __future__ import annotations

import base64
import os
from io import BytesIO
from typing import Dict

from PIL import Image

from utils.openai_client import client
from utils.team_loader import load_teams


# Preload team colors once to avoid repeated file reads.
# Mapping: team_id -> {"primary": color, "secondary": color}
_TEAM_COLOR_MAP: Dict[str, Dict[str, str]] = {
    t.team_id: {
        "primary": t.primary_color,
        "secondary": t.secondary_color,
    }
    for t in load_teams("data/teams.csv")
}


def _infer_ethnicity(name: str) -> str:
    """Very naive placeholder for ethnicity inference."""
    return "unspecified"


def _team_colors(team_id: str) -> Dict[str, str]:
    return _TEAM_COLOR_MAP.get(
        team_id, {"primary": "#000000", "secondary": "#ffffff"}
    )


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
    result = client.images.generate(model="gpt-image-1", prompt=prompt, size="1024x1024")
    b64 = result.data[0].b64_json
    image_bytes = base64.b64decode(b64)
    with Image.open(BytesIO(image_bytes)) as img:
        img = img.resize((512, 512), Image.LANCZOS)
        os.makedirs(os.path.dirname(out_file), exist_ok=True)
        img.save(out_file, format="PNG")
    return out_file

__all__ = ["generate_avatar"]
