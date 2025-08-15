"""Icons8 avatar fetching service."""

from __future__ import annotations

import configparser
import io
import logging
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import ssl
from typing import Tuple

from PIL import Image

log = logging.getLogger(__name__)


def _get_api_key() -> str | None:
    """Return the Icons8 API key from environment or config file if present."""

    key = os.getenv("ICONS8_API_KEY")
    if key:
        key = key.strip()
        if key:
            return key

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    cfg_path = os.path.join(base_dir, "config.ini")
    if os.path.exists(cfg_path):
        parser = configparser.ConfigParser()
        parser.read(cfg_path)
        key = parser.get("icons8", "api_key", fallback=None)
        if key:
            key = key.strip()
            if key:
                return key

    log.warning(
        "Icons8 API key not found; requests will fail with HTTP 403"
    )
    return None


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

    api_key = _get_api_key()
    if not api_key:
        raise RuntimeError(
            "Icons8 API key is missing. Set the ICONS8_API_KEY environment "
            "variable or add an [icons8] section with api_key to config.ini."
        )

    params = {
        "name": name,
        "ethnicity": ethnicity,
        "size": str(size),
        "clothesColor": primary_hex.lstrip("#"),
        "background": secondary_hex.lstrip("#"),
        "token": api_key,
    }
    url = (
        "https://avatars.icons8.com/api/iconsets/avatar?"
        + urllib.parse.urlencode(params)
    )

    # WARNING: This disables certificate checks and must not be enabled in production.
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    headers = {"User-Agent": "Mozilla/5.0"}
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=10, context=ssl_context) as response:
            if response.status != 200:
                raise RuntimeError(
                    f"Icons8 API returned status {response.status}"
                )
            data = response.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        snippet = body[:200]
        raise RuntimeError(
            f"Icons8 API HTTP {exc.code}: {exc.reason}. "
            f"Response: {snippet}"
        ) from exc
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, ssl.SSLCertVerificationError):
            hint = (
                "certificate verify failed. Update your OS certificate store "
                "(e.g. sudo update-ca-certificates)"
            )
            raise RuntimeError(
                f"Failed to fetch avatar from Icons8: {hint}"
            ) from exc
        raise RuntimeError(
            f"Failed to fetch avatar from Icons8: {exc.reason}"
        ) from exc

    img = Image.open(io.BytesIO(data))
    if img.size != (size, size):
        img = img.resize((size, size), resample=Image.LANCZOS)
    img.save(avatar_path)
    thumb = img.resize((150, 150), resample=Image.LANCZOS)
    thumb.save(thumb_path)
    return avatar_path, thumb_path


__all__ = ["fetch_icons8_avatar"]
