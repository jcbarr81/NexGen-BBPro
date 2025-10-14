import pytest

from utils.lineup_loader import build_default_game_state
from utils.player_loader import load_players_from_csv
from utils.roster_loader import load_roster
from utils.pitcher_role import get_role


def _expected_state(team_id: str):
    players = {p.player_id: p for p in load_players_from_csv("data/players.csv")}
    roster = load_roster(team_id)

    hitters = []
    pitchers = []
    for pid in roster.act:
        player = players.get(pid)
        if not player:
            continue
        role = get_role(player)
        if role in {"SP", "RP"}:
            pitchers.append(player)
        else:
            hitters.append(player)

    hitters.sort(key=lambda p: p.ph, reverse=True)
    lineup = hitters[:9]
    bench = hitters[9:]

    starters = [p for p in pitchers if get_role(p) == "SP"]
    if starters:
        starter = max(starters, key=lambda p: p.endurance)
    else:
        starter = max(pitchers, key=lambda p: p.endurance)
    expected_pitchers = [starter] + [p for p in pitchers if p.player_id != starter.player_id]

    return lineup, bench, expected_pitchers


def test_build_default_game_state_creates_expected_lineup():
    team_id = "ABU"
    state = build_default_game_state(team_id)
    lineup, bench, pitchers = _expected_state(team_id)

    assert [p.player_id for p in state.lineup] == [p.player_id for p in lineup]
    assert [p.player_id for p in state.bench] == [p.player_id for p in bench]
    assert [p.player_id for p in state.pitchers] == [p.player_id for p in pitchers]


def test_build_default_game_state_attaches_team_metadata():
    team_id = "DEN"
    state = build_default_game_state(team_id)
    assert state.team is not None
    assert state.team.team_id == team_id
    original = getattr(state.team, "season_stats", {})
    if original:
        assert state.team_stats == original
