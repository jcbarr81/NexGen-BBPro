"""Icons8 avatar fetching service."""

from __future__ import annotations

import io
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Tuple

from PIL import Image


def fetch_icons8_avatar(
    name: str,
    ethnicity: str,
    primary_hex: str,
    secondary_hex: str,
    size: int = 512,
) -> Tuple[str, str]:
    """Fetch an avatar image from the Icons8 service.

    Parameters
    ----------
    name:
        Display name for the avatar. Used to build the player identifier and is
        sent to the Icons8 API.
    ethnicity:
        Skin tone keyword as documented by Icons8 (e.g. ``"black"`` or
        ``"asian"``).
    primary_hex:
        Jersey colour in ``"#RRGGBB"`` form.
    secondary_hex:
        Background colour in ``"#RRGGBB"`` form.
    size:
        Requested square image size in pixels. Defaults to ``512``.

    Returns
    -------
    tuple[str, str]
        Paths to the saved avatar and thumbnail images.

    The function caches downloads; if both the main image and the thumbnail
    already exist, no network request is performed.
    """

    player_id = re.sub(r"[^0-9a-zA-Z]+", "_", name).lower()
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    out_dir = os.path.join(base_dir, "images", "avatars")
    os.makedirs(out_dir, exist_ok=True)
    avatar_path = os.path.join(out_dir, f"{player_id}.png")
    thumb_path = os.path.join(out_dir, f"{player_id}_150.png")

    if os.path.exists(avatar_path) and os.path.exists(thumb_path):
        return avatar_path, thumb_path

    params = {
        "name": name,
        "ethnicity": ethnicity,
        "size": str(size),
        "clothesColor": primary_hex.lstrip("#"),
        "background": secondary_hex.lstrip("#"),
    }
    url = "https://avatars.icons8.com/api/iconsets/avatar" + "?" + urllib.parse.urlencode(params)

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            if response.status != 200:
                raise RuntimeError(f"Icons8 API returned status {response.status}")
            data = response.read()
    except urllib.error.URLError as exc:
        raise RuntimeError("Failed to fetch avatar from Icons8") from exc

    img = Image.open(io.BytesIO(data))
    if img.size != (size, size):
        img = img.resize((size, size), resample=Image.LANCZOS)
    img.save(avatar_path)
    thumb = img.resize((150, 150), resample=Image.LANCZOS)
    thumb.save(thumb_path)
    return avatar_path, thumb_path


__all__ = ["fetch_icons8_avatar"]
