from types import SimpleNamespace

from playbalance.awards_manager import AwardsManager


def test_awards_manager_respects_qualification_thresholds():
    players = {
        "BAT_SMALL": SimpleNamespace(player_id="BAT_SMALL", first_name="Tiny", last_name="Sample"),
        "BAT_QUAL": SimpleNamespace(player_id="BAT_QUAL", first_name="Full", last_name="Season"),
        "PIT_SMALL": SimpleNamespace(player_id="PIT_SMALL", first_name="Short", last_name="Stint"),
        "PIT_QUAL": SimpleNamespace(player_id="PIT_QUAL", first_name="Work", last_name="Horse"),
    }
    batting = {
        "BAT_SMALL": {"ops": 1.200, "pa": 30},
        "BAT_QUAL": {"ops": 0.900, "pa": 140},
    }
    pitching = {
        "PIT_SMALL": {"era": 1.50, "ip": 12.0},
        "PIT_QUAL": {"era": 3.20, "ip": 95.0},
    }

    manager = AwardsManager(
        players,
        batting,
        pitching,
        min_pa=100,
        min_ip=60.0,
    )
    winners = manager.select_award_winners()

    assert winners["MVP"].player.player_id == "BAT_QUAL"
    assert winners["CY_YOUNG"].player.player_id == "PIT_QUAL"
