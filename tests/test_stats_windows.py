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
