from __future__ import annotations

import csv
import os
import random
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Iterable, List, Mapping, Sequence, Tuple

from models.pitcher import Pitcher
from models.team import Team
from playbalance.sim_config import load_tuned_playbalance_config
from playbalance.simulation import (
    GameSimulation,
    TeamState,
    generate_boxscore,
    render_boxscore_html,
)
from utils.lineup_loader import build_default_game_state, load_lineup
from utils.lineup_autofill import auto_fill_lineup_for_team
from utils.roster_loader import load_roster
from utils.pitcher_recovery import PitcherRecoveryTracker
from utils.player_loader import load_players_from_csv
from utils.team_loader import load_teams

LineupEntry = Tuple[str, str]



@lru_cache(maxsize=1)
def _teams_by_id() -> Mapping[str, Team]:
    """Return a cached mapping of team IDs to :class:`Team` objects."""

    return {team.team_id: team for team in load_teams()}


def _normalize_game_date(value: str | date | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _starter_hand(state: TeamState) -> str:
    """Return the throwing hand of the team's starting pitcher."""

    if not state.pitchers:
        return ""
    starter = state.pitchers[0]
    hand = getattr(starter, "throws", "") or getattr(starter, "bats", "")
    return str(hand or "").upper()[:1]


def _load_saved_lineup(
    team_id: str,
    vs: str,
    *,
    lineup_dir: str | Path,
) -> Sequence[LineupEntry] | None:
    try:
        return load_lineup(team_id, vs=vs, lineup_dir=lineup_dir)
    except FileNotFoundError:
        return None
    except ValueError:
        return None


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
    # Defensive programming: ensure we always field a complete batting order.
    # If a saved lineup is incomplete or malformed (e.g., fewer than nine
    # entries), fall back to the default lineup by signaling an error to the
    # caller. This prevents simulations from running with 1–2 hitters and
    # producing distorted stats.
    if len(new_lineup) != 9:
        raise ValueError(
            f"Lineup must list 9 unique players; found {len(new_lineup)}"
        )
    state.lineup = new_lineup
    state.bench = [p for p in hitters if p.player_id not in seen]


def _apply_bullpen_usage_order(
    state: TeamState,
    team_id: str,
    tracker: PitcherRecoveryTracker | None,
    date_token: str | None,
    seed: int | None,
    *,
    players_file: str,
    roster_dir: str,
) -> None:
    """Reorder bullpen arms so rested pitchers are prioritised and tired arms sink."""

    if tracker is None or not date_token or not state.pitchers or len(state.pitchers) <= 1:
        return
    status_map = tracker.bullpen_game_status(team_id, date_token, players_file, roster_dir)
    if not status_map:
        return

    starter = state.pitchers[0]
    bullpen = list(state.pitchers[1:])
    if not bullpen:
        return

    rng_seed = hash((team_id, date_token, seed or 0))
    ordering_rng = random.Random(rng_seed)
    tie_breakers = {p.player_id: ordering_rng.random() for p in bullpen}

    available: list[tuple[dict[str, object], Pitcher]] = []
    resting: list[tuple[dict[str, object], Pitcher]] = []
    for pitcher in bullpen:
        info = dict(status_map.get(pitcher.player_id, {}))
        if info.get("available", True):
            available.append((info, pitcher))
        else:
            resting.append((info, pitcher))

    def _available_key(item: tuple[dict[str, object], Pitcher]) -> tuple[float, float, float, float]:
        info, pitcher = item
        days_since = float(info.get("days_since_use", 9999))
        last_pitches = float(info.get("last_pitches", 0))
        return (
            1.0,
            days_since,
            -last_pitches,
            tie_breakers.get(pitcher.player_id, 0.0),
        )

    def _resting_key(item: tuple[dict[str, object], Pitcher]) -> tuple[float, float]:
        info, pitcher = item
        available_on = info.get("available_on")
        ordinal = available_on.toordinal() if hasattr(available_on, "toordinal") else float("inf")
        return (
            ordinal,
            tie_breakers.get(pitcher.player_id, 0.0),
        )

    available.sort(key=_available_key, reverse=True)
    resting.sort(key=_resting_key)

    state.pitchers = [starter] + [p for _, p in available] + [p for _, p in resting]


def reorder_pitchers(state: TeamState, starter_id: str | None) -> None:
    """Move ``starter_id`` to the front and set as current starter.

    TeamState initializes the current pitcher (and credits G/GS) in
    ``__post_init__`` using the first entry in ``state.pitchers``. When a
    starter is supplied later (e.g., by the recovery tracker), simply
    reordering the list is not sufficient — the already-created
    ``current_pitcher_state`` would still point at the previous first pitcher
    who already received a G/GS credit. This helper reorders the list and also
    transfers the game/GS credit and ``current_pitcher_state`` to the desired
    starter so starts are attributed correctly.
    """

    def _prioritize_bullpen() -> None:
        if len(state.pitchers) <= 1:
            return
        starter = state.pitchers[0]
        bullpen: list = []
        rotation_rest: list = []
        for pitcher in state.pitchers[1:]:
            role = str(getattr(pitcher, "assigned_pitching_role", "") or "")
            if role.upper().startswith("SP"):
                rotation_rest.append(pitcher)
            else:
                bullpen.append(pitcher)
        state.pitchers[:] = [starter] + bullpen + rotation_rest

    if not starter_id:
        _prioritize_bullpen()
        return
    # Find desired starter
    target_index = None
    for idx, p in enumerate(state.pitchers):
        if p.player_id == starter_id:
            target_index = idx
            break
    if target_index is None:
        raise ValueError(f"Pitcher {starter_id} not found on pitching staff")

    # If already first, ensure current_pitcher_state exists and points to him
    if target_index == 0:
        if state.current_pitcher_state is None or (
            state.current_pitcher_state.player.player_id != starter_id
        ):
            from playbalance.state import PitcherState  # local import to avoid cycle

            new_ps = state.pitcher_stats.get(starter_id)
            if new_ps is None:
                new_ps = PitcherState(state.pitchers[0])
                new_ps.g += 1
                new_ps.gs += 1
                state.pitcher_stats[starter_id] = new_ps
            state.current_pitcher_state = new_ps
        _prioritize_bullpen()
        return

    # Move target pitcher to front
    starter = state.pitchers.pop(target_index)
    state.pitchers.insert(0, starter)

    from playbalance.state import PitcherState  # local import to avoid cycle
    # Remove the credit from the prior assumed starter
    prev_ps = state.current_pitcher_state
    if prev_ps is not None:
        if getattr(prev_ps, "g", 0) > 0:
            prev_ps.g -= 1
        if getattr(prev_ps, "gs", 0) > 0:
            prev_ps.gs -= 1
    # Credit the selected starter and set current state
    ps = state.pitcher_stats.get(starter.player_id)
    if ps is None:
        ps = PitcherState(starter)
        state.pitcher_stats[starter.player_id] = ps
    ps.g += 1
    ps.gs += 1
    state.current_pitcher_state = ps
    _prioritize_bullpen()


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
    team_obj = _teams_by_id().get(team_id)
    state.team = team_obj
    if team_obj is not None and getattr(team_obj, "season_stats", None):
        state.team_stats = dict(team_obj.season_stats)
    if lineup:
        apply_lineup(state, lineup)
    reorder_pitchers(state, starter_id)
    return state


def _sanitize_lineup(
    team_id: str,
    desired: Sequence[LineupEntry],
    *,
    players_file: str = "data/players.csv",
    roster_dir: str = "data/rosters",
    lineup_dir: str | Path = "data/lineups",
) -> Sequence[LineupEntry]:
    """Return a valid 9-player lineup and persist it to disk.

    Ignores ``desired`` when regenerating to ensure the final lineup reflects
    the current active roster.
    """
    try:
        load_roster.cache_clear()
    except Exception:
        pass
    lineup = auto_fill_lineup_for_team(
        team_id,
        players_file=players_file,
        roster_dir=roster_dir,
        lineup_dir=lineup_dir,
    )
    # Provide as sequence of (pid, position)
    return list(lineup)


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
    lineup_dir: str | Path = "data/lineups",
    game_date: str | date | None = None,
    seed: int | None = None,
) -> tuple[TeamState, TeamState, dict[str, object], str, dict[str, object]]:
    """Simulate a single game and return team states, box score, HTML and metadata."""

    date_token = _normalize_game_date(game_date)
    tracker = PitcherRecoveryTracker.instance() if date_token else None
    if tracker and date_token:
        if home_starter is None:
            assigned = tracker.assign_starter(
                home_id, date_token, players_file, roster_dir
            )
            if assigned:
                home_starter = assigned
        else:
            tracker.ensure_team(home_id, players_file, roster_dir)
        if away_starter is None:
            assigned = tracker.assign_starter(
                away_id, date_token, players_file, roster_dir
            )
            if assigned:
                away_starter = assigned
        else:
            tracker.ensure_team(away_id, players_file, roster_dir)

    player_source = str(players_file)
    players_lookup = {
        player.player_id: player
        for player in load_players_from_csv(player_source)
    }

    def _pitcher_matchup(starter_id: str | None) -> str:
        if not starter_id:
            return "rhp"
        pitcher = players_lookup.get(starter_id)
        hand = str(getattr(pitcher, "throws", "") or getattr(pitcher, "bats", "") or "").upper()
        return "lhp" if hand.startswith("L") else "rhp"

    def _select_saved_lineup(team_id: str, opponent_starter: str | None) -> Sequence[LineupEntry] | None:
        desired: list[str] = []
        primary = _pitcher_matchup(opponent_starter)
        desired.append(primary)
        for fallback in ("rhp", "lhp"):
            if fallback not in desired:
                desired.append(fallback)
        for variant in desired:
            lineup = _load_saved_lineup(team_id, vs=variant, lineup_dir=lineup_dir)
            if lineup and len(lineup) == 9:
                return lineup
        return None

    if home_lineup is None:
        home_lineup = _select_saved_lineup(home_id, away_starter)
    if away_lineup is None:
        away_lineup = _select_saved_lineup(away_id, home_starter)

    def _build_state(team_id: str, lineup: Sequence[LineupEntry] | None, starter_id: str | None) -> TeamState:
        try:
            return prepare_team_state(
                team_id,
                lineup=lineup,
                starter_id=starter_id,
                players_file=players_file,
                roster_dir=roster_dir,
            )
        except ValueError:
            if lineup:
                # Salvage by sanitizing against ACT and persist the fix so
                # subsequent games use the corrected lineup.
                safe = _sanitize_lineup(
                    team_id,
                    lineup,
                    players_file=players_file,
                    roster_dir=roster_dir,
                    lineup_dir=lineup_dir,
                )
                return prepare_team_state(
                    team_id,
                    lineup=safe,
                    starter_id=starter_id,
                    players_file=players_file,
                    roster_dir=roster_dir,
                )
            raise

    rng = random.Random(seed)
    home_state = _build_state(home_id, home_lineup, home_starter)
    away_state = _build_state(away_id, away_lineup, away_starter)
    _apply_bullpen_usage_order(
        home_state,
        home_id,
        tracker,
        date_token,
        seed,
        players_file=players_file,
        roster_dir=roster_dir,
    )
    _apply_bullpen_usage_order(
        away_state,
        away_id,
        tracker,
        date_token,
        seed,
        players_file=players_file,
        roster_dir=roster_dir,
    )

    cfg, _ = load_tuned_playbalance_config()
    sim = GameSimulation(home_state, away_state, cfg, rng)

    # Allow heavy simulation runs to disable per-game persistence via env var.
    # PB_PERSIST_STATS: "1"/"true"/"yes" to persist; "0"/"false"/"no" to skip.
    def _env_flag(name: str, default: bool) -> bool:
        val = os.getenv(name)
        if val is None:
            return default
        return str(val).strip().lower() in {"1", "true", "yes", "on"}

    persist_stats = _env_flag("PB_PERSIST_STATS", True)
    sim.simulate_game(persist_stats=persist_stats)

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
    if tracker and date_token:
        tracker.record_game(
            home_id,
            date_token,
            home_state.pitcher_stats.values(),
            players_file,
            roster_dir,
        )
        tracker.record_game(
            away_id,
            date_token,
            away_state.pitcher_stats.values(),
            players_file,
            roster_dir,
        )
    return home_state, away_state, box, html, meta


def simulate_game_scores(
    home_id: str,
    away_id: str,
    *,
    seed: int | None = None,
    players_file: str = "data/players.csv",
    roster_dir: str = "data/rosters",
    lineup_dir: str | Path = "data/lineups",
    game_date: str | date | None = None,
) -> tuple[int, int, str, dict[str, object]]:
    """Return the final score, rendered HTML and metadata for a matchup."""

    home_state, away_state, _, html, meta = run_single_game(
        home_id,
        away_id,
        seed=seed,
        players_file=players_file,
        roster_dir=roster_dir,
        lineup_dir=lineup_dir,
        game_date=game_date,
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



