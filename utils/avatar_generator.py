"""Utilities for generating player avatar images.

Creates simple illustrated headshots for each player using the
:mod:`images.avatars` module. Avatars are written to ``images/avatars``
relative to the repository root and named after the player's ID.
"""
from __future__ import annotations

import os
from typing import Callable, Dict, Optional

from PIL import Image

from images.avatars import generate_player_headshot
from utils.player_loader import load_players_from_csv
from utils.team_loader import load_teams
from utils.roster_loader import load_roster


def generate_player_avatars(
    out_dir: str | None = None,
    size: int = 512,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    *,
    use_sdxl: bool = False,
    players: Dict[str, object] | None = None,
    teams: list | None = None,
    controlnet_path: str | None = None,
    ip_adapter_path: str | None = None,
) -> str:
    """Generate avatar images for all players and return the output directory.

    Parameters
    ----------
    out_dir:
        Optional output directory. Defaults to ``images/avatars`` relative to
        the project root.
    size:
        Pixel size for the generated square avatars.
    progress_callback:
        Optional callback receiving ``(completed, total)`` after each avatar is
        saved. Useful for updating progress displays.
    """

    if use_sdxl:
        from utils.ubl_avatar_generator import generate_player_avatars_sdxl

        return generate_player_avatars_sdxl(
            out_dir=out_dir,
            size=size,
            progress_callback=progress_callback,
            players=players,
            teams=teams,
            controlnet_path=controlnet_path,
            ip_adapter_path=ip_adapter_path,
        )

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

    # Determine total number of players that will have avatars generated
    total = sum(1 for pid in players if pid in player_team)
    completed = 0

    if out_dir is None:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        out_dir = os.path.join(base_dir, "images", "avatars")
    os.makedirs(out_dir, exist_ok=True)

    team_map = {t.team_id: t for t in teams}
    for pid, player in players.items():
        team_id = player_team.get(pid)
        if not team_id:
            continue
        team = team_map.get(team_id)
        if not team:
            continue
        name = f"{player.first_name} {player.last_name}"
        img = generate_player_headshot(
            player_name=name,
            team_primary_hex=team.primary_color,
            team_secondary_hex=team.secondary_color,
            size=size,
        )
        img.save(os.path.join(out_dir, f"{pid}.png"))
        # Smaller version for UI thumbnails
        thumb = img.resize((150, 150), resample=Image.LANCZOS)
        thumb.save(os.path.join(out_dir, f"{pid}_150.png"))

        completed += 1
        if progress_callback:
            progress_callback(completed, total)

    return out_dir


if __name__ == "__main__":  # pragma: no cover - CLI helper
    def _print_progress(completed: int, total: int) -> None:
        """Print simple progress information to the console."""
        print(f"Generated {completed}/{total} avatars", end="\r", flush=True)

    generate_player_avatars(
        use_sdxl=True,
        controlnet_path=None,
        ip_adapter_path=None,
        progress_callback=_print_progress,
    )
    print()  # Newline after progress output
