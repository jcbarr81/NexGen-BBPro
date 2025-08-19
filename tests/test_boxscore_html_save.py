import shutil
from pathlib import Path

from tests.test_simulation import make_player, make_pitcher, MockRandom
from logic.simulation import BatterState
from tests.util.pbini_factory import load_config

from logic.simulation import (
    GameSimulation,
    TeamState,
    generate_boxscore,
    render_boxscore_html,
    save_boxscore_html,
)


def _simulate_simple_game():
    cfg = load_config()
    home = TeamState(lineup=[make_player("h1")], bench=[], pitchers=[make_pitcher("hp")])
    away = TeamState(lineup=[make_player("a1")], bench=[], pitchers=[make_pitcher("ap")])
    sim = GameSimulation(home, away, cfg, MockRandom([]))

    def fake_play_half(self, offense, defense):
        runs = 1 if offense is self.away and len(offense.inning_runs) == 0 else 0
        batter = offense.lineup[0]
        bs = offense.lineup_stats.setdefault(batter.player_id, BatterState(batter))
        bs.pa += 1
        bs.ab += 1
        if runs:
            bs.h += 1
            bs.b1 += 1
            bs.r += 1
            bs.rbi += 1
        offense.runs += runs
        offense.inning_runs.append(runs)

    sim._play_half = fake_play_half.__get__(sim, GameSimulation)
    sim.simulate_game(innings=1)
    return home, away


def test_boxscore_html_written():
    # Ensure a clean output directory
    shutil.rmtree(Path("data/boxscores"), ignore_errors=True)

    home, away = _simulate_simple_game()
    box = generate_boxscore(home, away)
    html = render_boxscore_html(box, home_name="Home", away_name="Away")

    path_ex = save_boxscore_html("exhibition", html, "game_ex")
    path_se = save_boxscore_html("season", html, "game_se")

    assert Path(path_ex).is_file()
    assert Path(path_se).is_file()

    text = Path(path_ex).read_text(encoding="utf-8")
    assert "1  2  3" in text  # score header
    assert "Fa1 La1" in text  # away player
    assert "Fh1 Lh1" in text  # home player

    # Clean up generated files to keep repository tidy
    shutil.rmtree(Path("data/boxscores"))

