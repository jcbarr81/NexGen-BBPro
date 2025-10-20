from types import SimpleNamespace
import importlib

from tests.qt_stubs import patch_qt

patch_qt()

import ui.team_stats_window as team_stats_window
import ui.league_stats_window as league_stats_window
import ui.league_leaders_window as league_leaders_window
from models.team import Team
from models.roster import Roster

# Reload modules to ensure they pick up the testing stubs
importlib.reload(team_stats_window)
importlib.reload(league_stats_window)
importlib.reload(league_leaders_window)

from ui.team_stats_window import TeamStatsWindow
from ui.league_stats_window import LeagueStatsWindow
from ui.league_leaders_window import LeagueLeadersWindow


def _sample_team() -> Team:
    team = Team(
        team_id="T",
        name="Testers",
        city="Test",
        abbreviation="TST",
        division="D",
        stadium="Stadium",
        primary_color="#000000",
        secondary_color="#ffffff",
        owner_id="OWN",
    )
    team.season_stats = {"w": 1, "l": 0}
    return team


def _sample_players():
    batter = SimpleNamespace(
        first_name="A",
        last_name="B",
        is_pitcher=False,
        season_stats={"g": 1, "ab": 2, "r": 1, "h": 1, "avg": 0.5},
    )
    pitcher = SimpleNamespace(
        first_name="C",
        last_name="D",
        is_pitcher=True,
        season_stats={"w": 1, "era": 3.0, "so": 5},
    )
    return {"b1": batter, "p1": pitcher}


def test_team_stats_window_instantiates():
    team = _sample_team()
    players = _sample_players()
    roster = Roster(team_id="T", act=["b1", "p1"])
    TeamStatsWindow(team, players, roster)


def test_league_stats_window_instantiates():
    team = _sample_team()
    players = _sample_players()
    LeagueStatsWindow([team], players.values())


def test_league_leaders_window_instantiates():
    players = _sample_players()
    LeagueLeadersWindow(players.values())


def test_leader_fallback_includes_relief_pitchers():
    window = LeagueLeadersWindow.__new__(LeagueLeadersWindow)
    qualified = [
        SimpleNamespace(
            player_id="starter",
            first_name="Ace",
            last_name="Starter",
            is_pitcher=True,
            season_stats={"sv": 0},
        )
    ]
    fallback = qualified + [
        SimpleNamespace(
            player_id=f"closer{i}",
            first_name="Closer",
            last_name=str(i),
            is_pitcher=True,
            season_stats={"sv": 10 - i},
        )
        for i in range(5)
    ]

    leaders = window._leaders_for_category(
        qualified,
        fallback,
        "sv",
        pitcher_only=True,
        descending=True,
        limit=5,
    )

    ids = {player.player_id for player, _ in leaders}
    assert ids == {f"closer{i}" for i in range(5)}


def test_leader_fallback_skips_pitchers_without_samples():
    window = LeagueLeadersWindow.__new__(LeagueLeadersWindow)
    qualified = []
    fallback = [
        SimpleNamespace(
            player_id="no_stats",
            first_name="Bullpen",
            last_name="Ghost",
            is_pitcher=True,
            season_stats={"sv": 8},
        ),
        SimpleNamespace(
            player_id="with_stats",
            first_name="Relief",
            last_name="Ace",
            is_pitcher=True,
            season_stats={"sv": 7, "ip": 12.1, "era": 2.5},
        ),
    ]

    leaders = window._leaders_for_category(
        qualified,
        fallback,
        "era",
        pitcher_only=True,
        descending=False,
        limit=5,
    )

    ids = {player.player_id for player, _ in leaders}
    assert ids == {"with_stats"}
