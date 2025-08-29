"""Generate player avatars using OpenAI's image model."""
from __future__ import annotations

import base64
import csv
from collections import Counter, defaultdict
from io import BytesIO
from pathlib import Path
from typing import Dict, Tuple

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


# Preload ethnicity data from names.csv for quick lookups.
# Mapping: (first_name, last_name) -> Counter of ethnicities
_NAME_ETHNICITY_FULL: Dict[Tuple[str, str], Counter[str]] = defaultdict(Counter)
# Mapping: individual name -> Counter of ethnicities
_NAME_ETHNICITY_SINGLE: Dict[str, Counter[str]] = defaultdict(Counter)

with Path("data/names.csv").open(newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        ethnicity = row["ethnicity"]
        first = row["first_name"].strip().lower()
        last = row["last_name"].strip().lower()
        _NAME_ETHNICITY_FULL[(first, last)][ethnicity] += 1
        _NAME_ETHNICITY_SINGLE[first][ethnicity] += 1
        _NAME_ETHNICITY_SINGLE[last][ethnicity] += 1


def _infer_ethnicity(name: str) -> str:
    """Return the most probable ethnicity for ``name``.

    The lookup prioritizes an exact match of both first and last name and then
    falls back to individual name statistics. "unspecified" is returned when no
    data exists for the provided name.
    """

    parts = [p.strip().lower() for p in name.split() if p.strip()]
    if not parts:
        return "unspecified"

    first, last = parts[0], parts[-1]

    scores: Counter[str] = Counter()
    scores.update(_NAME_ETHNICITY_FULL.get((first, last), {}))
    scores.update(_NAME_ETHNICITY_SINGLE.get(first, {}))
    scores.update(_NAME_ETHNICITY_SINGLE.get(last, {}))

    if not scores:
        return "unspecified"

    return scores.most_common(1)[0][0]


def _team_colors(team_id: str) -> Dict[str, str]:
    return _TEAM_COLOR_MAP.get(
        team_id, {"primary": "#000000", "secondary": "#ffffff"}
    )


def generate_avatar(
    name: str,
    team_id: str,
    out_file: str,
    size: int = 512,
    style: str = "illustrated",
    skin_tone: str | None = None,
    hair_color: str | None = None,
    facial_hair: str | None = None,
) -> str:
    """Generate an avatar for ``name`` and save it to ``out_file``.

    The avatar uses an off-white background and depicts a player in a plain cap
    and jersey in team colors without any logos, images, letters, names, or
    numbers. The image must contain no text overlays.

    Parameters
    ----------
    name:
        Player's full name.
    team_id:
        Identifier of the player's team to derive colors.
    out_file:
        Path where the resulting PNG should be written.
    size:
        Pixel size for the square avatar. This value is passed directly to the
        OpenAI image API.
    style:
        Art style for the portrait (e.g., ``"illustrated"``). The prompt always
        requests a cartoon style.
    skin_tone:
        Optional descriptor for the player's complexion (e.g., ``"light"``).
    hair_color:
        Optional hair color descriptor.
    facial_hair:
        Optional facial hair style (e.g., ``"goatee"``).
    """
    if client is None:  # pragma: no cover - depends on external package
        raise RuntimeError("OpenAI client is not configured")

    colors = _team_colors(team_id)
    ethnicity = _infer_ethnicity(name)

    tone_part = f"{skin_tone}-skinned " if skin_tone else ""
    trait_bits = []
    if hair_color:
        trait_bits.append(f"{hair_color} hair")
    if facial_hair:
        trait_bits.append(f"a {facial_hair}")
    traits = ""
    if trait_bits:
        traits = " with " + " and ".join(trait_bits)

    descriptor = f"{tone_part}{ethnicity} baseball player"
    prompt = (
        f"{style.capitalize()} portrait of {name}, a {descriptor}{traits}, "
        "wearing a plain ball cap and jersey in team colors "
        f"{colors['primary']} and {colors['secondary']}. The cap has no logo, "
        "image, or letters and the jersey has no names, letters, or numbers. "
        "The image contains no text overlays or names on an off-white background "
        "in a cartoon style."
    )
    api_size = 1024 if size == 512 else size
    result = client.images.generate(
        model="gpt-image-1", prompt=prompt, size=f"{api_size}x{api_size}"
    )
    b64 = result.data[0].b64_json
    image_bytes = base64.b64decode(b64)
    with Image.open(BytesIO(image_bytes)) as img:
        if img.size != (size, size):
            img = img.resize((size, size))
        Path(out_file).parent.mkdir(parents=True, exist_ok=True)
        img.save(out_file, format="PNG")
    return out_file

__all__ = ["generate_avatar"]
