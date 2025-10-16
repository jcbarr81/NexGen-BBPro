import csv
from functools import lru_cache
from pathlib import Path
from typing import Iterable, List, Tuple

from playbalance.simulation import TeamState
from models.player import Player
from models.pitcher import Pitcher
from utils.path_utils import get_base_dir
from .player_loader import load_players_from_csv
from .roster_loader import load_roster
from .pitcher_role import get_role
from utils.team_loader import load_teams


def load_lineup(team_id: str, vs: str = "lhp", lineup_dir: str | Path = "data/lineups") -> List[Tuple[str, str]]:
    """Load a lineup from ``lineup_dir`` for the given team.

    Files are expected to follow the naming pattern
    ``{team_id}_vs_{vs}.csv`` and contain columns
    ``order,player_id,position`` where ``player_id`` uses IDs like
    ``P1000``.
    """
    suffix = f"vs_{vs.lower()}"
    lineup_dir = Path(lineup_dir)
    if not lineup_dir.is_absolute():
        lineup_dir = get_base_dir() / lineup_dir
    file_path = lineup_dir / f"{team_id}_{suffix}.csv"
    if not file_path.exists():
        raise FileNotFoundError(f"Lineup file not found: {file_path}")

    lineup: List[Tuple[str, str]] = []
    with file_path.open(newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            player_id = row.get("player_id", "").strip()
            position = row.get("position", "").strip()
            lineup.append((player_id, position))
    return lineup


def _separate_players(players: Iterable[Player]) -> Tuple[List[Player], List[Pitcher]]:
    """Return hitters and pitchers from ``players``.

    Pitchers are identified using :func:`utils.pitcher_role.get_role`.  Players
    for which ``get_role`` returns ``"SP"`` or ``"RP"`` are treated as
    pitchers, everything else is considered a position player.
    """

    hitters: List[Player] = []
    pitchers: List[Pitcher] = []
    for p in players:
        role = get_role(p)
        if role in {"SP", "RP"}:
            pitchers.append(p)  # type: ignore[arg-type]
        else:
            hitters.append(p)
    return hitters, pitchers


def _load_pitching_staff(
    team_id: str,
    roster_dir: str,
    valid_pitchers: set[str],
) -> List[tuple[str, str]]:
    """Return ordered pitching staff entries from ``*_pitching.csv``."""

    roster_path = Path(roster_dir)
    if not roster_path.is_absolute():
        roster_path = get_base_dir() / roster_path
    file_path = roster_path / f"{team_id}_pitching.csv"
    entries: List[tuple[str, str]] = []
    if not file_path.exists():
        return entries
    seen: set[str] = set()
    try:
        with file_path.open("r", newline="", encoding="utf-8") as fh:
            reader = csv.reader(fh)
            for row in reader:
                if len(row) < 2:
                    continue
                pid = row[0].strip()
                role = row[1].strip()
                if not pid or pid in seen or pid not in valid_pitchers:
                    continue
                entries.append((pid, role))
                seen.add(pid)
    except OSError:
        return []
    return entries


def _build_default_lists(team_id: str, players_file: str, roster_dir: str) -> Tuple[List[Player], List[Player], List[Pitcher]]:
    """Return ``(lineup, bench, pitchers)`` for ``team_id``.

    The active roster is loaded from ``roster_dir`` and players are resolved via
    ``players_file``.  Nine position players are selected for the lineup based
    on descending ``ph`` (power hitting) rating.  Pitchers are ordered with a
    single starter first followed by the remaining bullpen arms.
    """

    all_players = {
        p.player_id: p for p in load_players_from_csv(players_file)
    }
    roster = load_roster(team_id, roster_dir)

    active = [all_players.get(pid) for pid in roster.act]
    active = [p for p in active if p is not None]

    hitters, pitchers = _separate_players(active)

    hitters.sort(key=lambda p: getattr(p, "ph", 0), reverse=True)
    lineup = hitters[:9]
    bench = hitters[9:]

    pitcher_lookup = {p.player_id: p for p in pitchers}
    staff_entries = _load_pitching_staff(team_id, roster_dir, set(pitcher_lookup))
    ordered_pitchers: List[Pitcher] = []

    for pid, role in staff_entries:
        pitcher = pitcher_lookup.pop(pid, None)
        if pitcher is None:
            continue
        setattr(pitcher, "assigned_pitching_role", role)
        ordered_pitchers.append(pitcher)

    remaining = list(pitcher_lookup.values())
    for pitcher in remaining:
        assigned = getattr(pitcher, "assigned_pitching_role", None)
        if not assigned:
            derived = get_role(pitcher)
            setattr(pitcher, "assigned_pitching_role", derived or "")
    remaining.sort(key=lambda p: getattr(p, "endurance", 0), reverse=True)
    ordered_pitchers.extend(remaining)

    if not ordered_pitchers:
        pitchers.sort(key=lambda p: getattr(p, "endurance", 0), reverse=True)
        ordered_pitchers = pitchers
        for pitcher in ordered_pitchers:
            assigned = getattr(pitcher, "assigned_pitching_role", None)
            if not assigned:
                derived = get_role(pitcher)
                setattr(pitcher, "assigned_pitching_role", derived or "")

    return lineup, bench, ordered_pitchers


@lru_cache(maxsize=None)
def _teams_lookup(path: str) -> dict[str, object]:
    try:
        teams = load_teams(path)
    except Exception:
        return {}
    return {t.team_id: t for t in teams}


def build_default_game_state(
    team_id: str,
    players_file: str = "data/players.csv",
    roster_dir: str = "data/rosters",
    teams_file: str | Path = "data/teams.csv",
) -> TeamState:
    """Return a :class:`~playbalance.simulation.TeamState` for ``team_id``.

    The state uses nine best hitters for the lineup, remaining hitters as the
    bench and pitchers ordered with a starter first followed by the bullpen.
    """

    lineup, bench, pitchers = _build_default_lists(team_id, players_file, roster_dir)

    if len(lineup) < 9:
        raise ValueError(f"Team {team_id} does not have enough position players")
    if not pitchers:
        raise ValueError(f"Team {team_id} does not have any pitchers")

    team_obj = None
    if teams_file:
        lookup_path = Path(teams_file)
        if not lookup_path.is_absolute():
            lookup_path = get_base_dir() / lookup_path
        team_obj = _teams_lookup(str(lookup_path)).get(team_id)

    state = TeamState(lineup=lineup, bench=bench, pitchers=pitchers, team=team_obj)
    if team_obj is not None:
        season = getattr(team_obj, "season_stats", None)
        if season:
            state.team_stats = dict(season)
    return state
