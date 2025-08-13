"""SDXL-based player avatar generation utilities.

This module provides a :func:`generate_player_avatars_sdxl` function which
leverages the Stable Diffusion XL pipeline to create more realistic player
avatars.  Heavy ML dependencies are imported lazily so that the rest of the
application can be used without them installed.
"""
from __future__ import annotations

import os
from typing import Callable, Dict, Optional

from utils.player_loader import load_players_from_csv
from utils.team_loader import load_teams
from utils.roster_loader import load_roster


def generate_player_avatars_sdxl(
    out_dir: str | None = None,
    size: int = 512,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    players: Dict[str, object] | None = None,
    teams: list | None = None,
    controlnet_path: str | None = None,
    ip_adapter_path: str | None = None,
) -> str:
    """Generate player avatars using Stable Diffusion XL and return the output directory.

    Parameters
    ----------
    out_dir:
        Optional output directory. Defaults to ``images/avatars`` relative to the
        project root.
    size:
        Pixel size for the generated square avatars.
    progress_callback:
        Optional callback receiving ``(completed, total)`` after each avatar is
        saved. Useful for updating progress displays.
    players, teams:
        Optional pre-loaded player dictionary and team list. If omitted they are
        loaded from disk internally.
    controlnet_path, ip_adapter_path:
        Optional paths to ControlNet and IP-Adapter models to further customise
        generation.
    """

    # Heavy imports are delayed to keep normal operation lightweight
    try:
        from PIL import Image
        from diskcache import Cache
        import torch
        from diffusers import StableDiffusionXLPipeline
    except Exception as exc:  # pragma: no cover - Only executed when deps missing
        raise RuntimeError(
            "SDXL avatar generation requires diffusers, transformers, torch, "
            "Pillow and diskcache to be installed"
        ) from exc

    if players is None:
        players = {p.player_id: p for p in load_players_from_csv("data/players.csv")}
    if teams is None:
        teams = load_teams("data/teams.csv")

    # Map each player ID to their team ID via roster files
    player_team: Dict[str, str] = {}
    for t in teams:
        try:
            roster = load_roster(t.team_id)
        except FileNotFoundError:
            continue
        for pid in roster.act + roster.aaa + roster.low:
            player_team[pid] = t.team_id

    total = sum(1 for pid in players if pid in player_team)
    completed = 0

    if out_dir is None:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        out_dir = os.path.join(base_dir, "images", "avatars")
    os.makedirs(out_dir, exist_ok=True)

    cache = Cache(os.path.join(out_dir, ".cache"))

    # Initialise the SDXL pipeline
    model_id = "stabilityai/stable-diffusion-xl-base-1.0"
    pipe = StableDiffusionXLPipeline.from_pretrained(
        model_id, torch_dtype=torch.float16
    )
    device = "cuda" if torch.cuda.is_available() else "cpu"
    pipe.to(device)

    if controlnet_path:
        try:
            from diffusers import ControlNetModel

            controlnet = ControlNetModel.from_pretrained(
                controlnet_path, torch_dtype=torch.float16
            )
            pipe.controlnet = controlnet
        except Exception:
            pass  # Best-effort loading only

    if ip_adapter_path:
        try:  # diffusers provides a helper for IP-Adapter models
            pipe.load_ip_adapter(ip_adapter_path)  # type: ignore[attr-defined]
        except Exception:
            pass

    team_map = {t.team_id: t for t in teams}

    for pid, player in players.items():
        team_id = player_team.get(pid)
        if not team_id:
            continue
        team = team_map.get(team_id)
        if not team:
            continue

        cache_key = f"{pid}-{team.primary_color}-{team.secondary_color}"
        out_path = os.path.join(out_dir, f"{pid}.png")
        thumb_path = os.path.join(out_dir, f"{pid}_150.png")

        # Skip generation if we already have an image for this player
        cached_file = cache.get(cache_key)
        if cached_file and os.path.exists(cached_file):
            if not os.path.exists(out_path):
                Image.open(cached_file).save(out_path)
            if not os.path.exists(thumb_path):
                img = Image.open(cached_file).resize((150, 150), resample=Image.LANCZOS)
                img.save(thumb_path)
            completed += 1
            if progress_callback:
                progress_callback(completed, total)
            continue

        prompt = (
            f"portrait photo of {player.first_name} {player.last_name} as a baseball "
            f"player, {team.name} colours"
        )
        image = pipe(prompt).images[0]
        image = image.resize((size, size))
        image.save(out_path)
        thumb = image.resize((150, 150), resample=Image.LANCZOS)
        thumb.save(thumb_path)

        cache.set(cache_key, out_path)

        completed += 1
        if progress_callback:
            progress_callback(completed, total)

    cache.close()
    return out_dir
