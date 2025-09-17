from __future__ import annotations

import csv
import random
from functools import lru_cache
from pathlib import Path
from typing import Iterable, List, Mapping, Sequence, Tuple

from models.team import Team
from playbalance.sim_config import load_tuned_playbalance_config
from playbalance.simulation import (
    GameSimulation,
    TeamState,
    generate_boxscore,
    render_boxscore_html,
)
from utils.lineup_loader import build_default_game_state
from utils.team_loader import load_teams

LineupEntry = Tuple[str, str]


@lru_cache(maxsize=1)
def _teams_by_id() -> Mapping[str, Team]:
    """Return a cached mapping of team IDs to :class:`Team` objects."""

    return {team.team_id: team for team in load_teams()}


def _starter_hand(state: TeamState) -> str:
    """Return the throwing hand of the team's starting pitcher."""

    if not state.pitchers:
        return ""
    starter = state.pitchers[0]
    hand = getattr(starter, "throws", "") or getattr(starter, "bats", "")
    return str(hand or "").upper()[:1]


def read_lineup_file(path: Path) -> List[LineupEntry]:
    """Return ``(player_id, position)`` tuples parsed from ``path``."""

    entries: List[LineupEntry] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            player_id = (row.get("player_id") or "").strip()
            position = (row.get("position") or "").strip()
            if not player_id:
                raise ValueError(f"Missing player_id in lineup file {path}")
            if not position:
                raise ValueError(
                    f"Missing position for {player_id} in lineup file {path}"
                )
            entries.append((player_id, position))
    if len(entries) != 9:
        raise ValueError(
            f"Lineup file {path} must contain exactly nine players; "
            f"found {len(entries)}"
        )
    return entries


def apply_lineup(state: TeamState, lineup: Sequence[LineupEntry]) -> None:
    """Reorder ``state.lineup`` using ``lineup`` and assign positions."""

    hitters = list(state.lineup) + list(state.bench)
    id_to_player = {p.player_id: p for p in hitters}
    new_lineup = []
    seen: set[str] = set()
    for player_id, position in lineup:
        player = id_to_player.get(player_id)
        if player is None:
            raise ValueError(
                f"Player {player_id} is not on the active roster"
            )
        if player_id in seen:
            raise ValueError(
                f"Player {player_id} appears multiple times in the lineup"
            )
        setattr(player, "position", position)
        new_lineup.append(player)
        seen.add(player_id)
    state.lineup = new_lineup
    state.bench = [p for p in hitters if p.player_id not in seen]


def reorder_pitchers(state: TeamState, starter_id: str | None) -> None:
    """Move ``starter_id`` to the front of ``state.pitchers`` if provided."""

    if not starter_id:
        return
    for idx, pitcher in enumerate(state.pitchers):
        if pitcher.player_id == starter_id:
            state.pitchers.insert(0, state.pitchers.pop(idx))
            return
    raise ValueError(f"Pitcher {starter_id} not found on pitching staff")


def prepare_team_state(
    team_id: str,
    *,
    lineup: Sequence[LineupEntry] | None = None,
    starter_id: str | None = None,
    players_file: str = "data/players.csv",
    roster_dir: str = "data/rosters",
) -> TeamState:
    """Return a :class:`TeamState` populated for ``team_id``.

    Lineups or starting pitchers supplied via ``lineup`` or ``starter_id``
    override the defaults derived from roster data.  The returned state stores
    a reference to the :class:`Team` object so season statistics can be
    persisted after the game completes.
    """

    state = build_default_game_state(
        team_id, players_file=players_file, roster_dir=roster_dir
    )
    state.team = _teams_by_id().get(team_id)
    if lineup:
        apply_lineup(state, lineup)
    reorder_pitchers(state, starter_id)
    return state


def run_single_game(
    home_id: str,
    away_id: str,
    *,
    home_lineup: Sequence[LineupEntry] | None = None,
    away_lineup: Sequence[LineupEntry] | None = None,
    home_starter: str | None = None,
    away_starter: str | None = None,
    players_file: str = "data/players.csv",
    roster_dir: str = "data/rosters",
    seed: int | None = None,
) -> tuple[TeamState, TeamState, dict[str, object], str, dict[str, object]]:
    """Simulate a single game and return team states, box score, HTML and metadata."""

    rng = random.Random(seed)
    home_state = prepare_team_state(
        home_id,
        lineup=home_lineup,
        starter_id=home_starter,
        players_file=players_file,
        roster_dir=roster_dir,
    )
    away_state = prepare_team_state(
        away_id,
        lineup=away_lineup,
        starter_id=away_starter,
        players_file=players_file,
        roster_dir=roster_dir,
    )

    cfg, _ = load_tuned_playbalance_config()
    sim = GameSimulation(home_state, away_state, cfg, rng)
    sim.simulate_game()

    box = generate_boxscore(home_state, away_state)
    home_name = home_state.team.name if home_state.team else home_id
    away_name = away_state.team.name if away_state.team else away_id
    html = render_boxscore_html(
        box,
        home_name=home_name,
        away_name=away_name,
    )
    meta = {
        "home_innings": len(home_state.inning_runs),
        "away_innings": len(away_state.inning_runs),
        "extra_innings": max(len(home_state.inning_runs), len(away_state.inning_runs)) > 9,
        "home_starter_hand": _starter_hand(home_state),
        "away_starter_hand": _starter_hand(away_state),
    }
    return home_state, away_state, box, html, meta


def simulate_game_scores(
    home_id: str,
    away_id: str,
    *,
    seed: int | None = None,
    players_file: str = "data/players.csv",
    roster_dir: str = "data/rosters",
) -> tuple[int, int, str, dict[str, object]]:
    """Return the final score, rendered HTML and metadata for a matchup."""

    home_state, away_state, _, html, meta = run_single_game(
        home_id,
        away_id,
        seed=seed,
        players_file=players_file,
        roster_dir=roster_dir,
    )
    return home_state.runs, away_state.runs, html, meta


__all__ = [
    "LineupEntry",
    "apply_lineup",
    "prepare_team_state",
    "read_lineup_file",
    "reorder_pitchers",
    "run_single_game",
    "simulate_game_scores",
]
