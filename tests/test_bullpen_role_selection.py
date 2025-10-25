from dataclasses import dataclass

from playbalance.substitution_manager import SubstitutionManager
from playbalance.playbalance_config import PlayBalanceConfig
from playbalance.simulation import TeamState
from models.player import Player
from models.pitcher import Pitcher


def _bp_kwargs(pid: str, pos: str) -> dict:
    return dict(
        player_id=pid,
        first_name="Test",
        last_name=pid,
        birthdate="1990-01-01",
        height=72,
        weight=190,
        bats="R",
        primary_position=pos,
        other_positions=[],
        gf=50,
    )


def _make_lineup(n: int = 9):
    return [Player(**_bp_kwargs(f"L{i}", "CF")) for i in range(n)]


def _make_staff():
    starter = Pitcher(**_bp_kwargs("SP1", "SP"), role="SP", endurance=100)
    lr = Pitcher(**_bp_kwargs("LR1", "RP"), role="RP", endurance=80)
    mr = Pitcher(**_bp_kwargs("MR1", "RP"), role="RP", endurance=60)
    su = Pitcher(**_bp_kwargs("SU1", "RP"), role="RP", endurance=50)
    cl = Pitcher(**_bp_kwargs("CL1", "RP"), role="RP", endurance=45)
    # Assign roles explicitly for selection logic
    setattr(lr, "assigned_pitching_role", "LR")
    setattr(mr, "assigned_pitching_role", "MR")
    setattr(su, "assigned_pitching_role", "SU")
    setattr(cl, "assigned_pitching_role", "CL")
    return [starter, lr, mr, su, cl]


def _team_state_with_usage(usage: dict[str, dict] | None = None) -> TeamState:
    state = TeamState(lineup=_make_lineup(), bench=[], pitchers=_make_staff())
    state.usage_status = usage or {}
    return state


def _cfg() -> PlayBalanceConfig:
    from utils.path_utils import get_base_dir

    return PlayBalanceConfig.from_file(get_base_dir() / "playbalance" / "PBINI.txt")


def test_selects_closer_in_ninth_save_situation():
    cfg = _cfg()
    cfg.enableUsageModelV2 = 1
    sm = SubstitutionManager(cfg)
    # All available
    usage = {
        "LR1": {"available": True},
        "MR1": {"available": True},
        "SU1": {"available": True},
        "CL1": {"available": True},
    }
    team = _team_state_with_usage(usage)
    # Ninth inning, defense leading by 1 → run_diff = offense - defense = -1
    idx, emergency = sm._select_reliever_index(team, inning=9, run_diff=-1, home_team=True)
    assert idx is not None
    chosen = team.pitchers[idx]
    assert getattr(chosen, "assigned_pitching_role", "") == "CL"


def test_selects_setup_in_eighth_tie_and_respects_caps():
    cfg = _cfg()
    cfg.enableUsageModelV2 = 1
    # Tighten caps so CL is blocked by 3-day window
    cfg.maxApps3Day_CL = 0
    sm = SubstitutionManager(cfg)
    usage = {
        "LR1": {"available": True, "apps3": 0, "apps7": 0, "consecutive_days": 0},
        "MR1": {"available": True, "apps3": 0, "apps7": 0, "consecutive_days": 0},
        "SU1": {"available": True, "apps3": 0, "apps7": 0, "consecutive_days": 0},
        # Block the closer by window cap
        "CL1": {"available": True, "apps3": 1, "apps7": 10, "consecutive_days": 0},
    }
    team = _team_state_with_usage(usage)
    # Eighth inning, tie game → prefer SU; CL is capped anyway
    idx, emergency = sm._select_reliever_index(team, inning=8, run_diff=0, home_team=False)
    assert idx is not None
    chosen = team.pitchers[idx]
    assert getattr(chosen, "assigned_pitching_role", "") == "SU"


def test_closer_replaces_setup_for_ninth_inning_save():
    cfg = _cfg()
    cfg.enableUsageModelV2 = 1
    sm = SubstitutionManager(cfg)
    usage = {
        "SU1": {"available": True, "apps3": 0, "apps7": 0, "consecutive_days": 0},
        "CL1": {"available": True, "apps3": 0, "apps7": 0, "consecutive_days": 0},
    }
    team = _team_state_with_usage(usage)
    # Recompose staff so the setup man is currently pitching with the closer ready.
    su = next(p for p in team.pitchers if getattr(p, "assigned_pitching_role", "") == "SU")
    cl = next(p for p in team.pitchers if getattr(p, "assigned_pitching_role", "") == "CL")
    team.pitchers = [su, cl] + [p for p in team.pitchers if p is not su and p is not cl]
    from playbalance.state import PitcherState  # local import to avoid circular import issues

    su_state = PitcherState()
    su_state.player = su
    su_state.appearance_outs = 3  # finished the eighth
    team.pitcher_stats = {su.player_id: su_state}
    team.current_pitcher_state = su_state
    team.bullpen_warmups.clear()

    changed = sm.maybe_replace_pitcher(team, inning=9, run_diff=-1, home_team=True)
    assert changed
    assert team.pitchers[0].player_id == cl.player_id


def test_starter_seventh_warms_setup_when_prob_hits():
    cfg = _cfg()
    cfg.enableUsageModelV2 = 1
    cfg.starterSeventhWarmChance = 100
    cfg.starterEighthWarmChance = 100
    cfg.starterLateWarmLeadMax = 3
    sm = SubstitutionManager(cfg)
    sm.rng.random = lambda: 0.0
    usage = {
        "LR1": {"available": True},
        "MR1": {"available": True},
        "SU1": {"available": True},
        "CL1": {"available": True},
    }
    team = _team_state_with_usage(usage)
    starter = team.pitchers[0]
    starter_state = team.pitcher_stats[starter.player_id]
    starter_state.h = 3
    team.pitcher_stats[starter.player_id] = starter_state
    team.runs = 3  # defense has scored 3, leading 3-2
    sm.maybe_warm_reliever(team, inning=7, run_diff=-1, home_team=True)
    su = next(p for p in team.pitchers if getattr(p, "assigned_pitching_role", "") == "SU")
    assert sm._preferred_warm_pid(team) == su.player_id
    assert su.player_id in team.bullpen_warmups


def test_starter_seventh_skips_when_no_hitter():
    cfg = _cfg()
    cfg.enableUsageModelV2 = 1
    cfg.starterSeventhWarmChance = 100
    cfg.starterLateWarmLeadMax = 3
    sm = SubstitutionManager(cfg)
    sm.rng.random = lambda: 0.0
    usage = {
        "LR1": {"available": True},
        "MR1": {"available": True},
        "SU1": {"available": True},
        "CL1": {"available": True},
    }
    team = _team_state_with_usage(usage)
    starter = team.pitchers[0]
    starter_state = team.pitcher_stats[starter.player_id]
    starter_state.h = 0  # no-hitter in progress
    team.pitcher_stats[starter.player_id] = starter_state
    team.runs = 3
    su = next(p for p in team.pitchers if getattr(p, "assigned_pitching_role", "") == "SU")
    sm.maybe_warm_reliever(team, inning=7, run_diff=-3, home_team=True)
    assert sm._preferred_warm_pid(team) != su.player_id
    assert su.player_id not in team.bullpen_warmups


def test_closer_boost_limits_control():
    cfg = _cfg()
    cfg.closerBoostStuffFloor = 90
    cfg.closerBoostControlFloor = 70
    cfg.closerBoostControlCap = 82
    cfg.closerBoostEnduranceFloor = 50
    sm = SubstitutionManager(cfg)
    pitcher = Pitcher(
        player_id="PCL",
        first_name="Test",
        last_name="Closer",
        birthdate="1995-01-01",
        height=74,
        weight=200,
        bats="R",
        primary_position="P",
        other_positions=[],
        gf=50,
        role="RP",
        endurance=35,
        control=55,
        movement=60,
        hold_runner=40,
        fb=65,
        cu=40,
        cb=45,
        sl=50,
        si=45,
        scb=0,
        kn=0,
        arm=60,
        fa=50,
    )

    sm._apply_closer_boost(pitcher)

    assert pitcher.movement >= cfg.closerBoostStuffFloor
    assert pitcher.fb >= cfg.closerBoostStuffFloor
    assert cfg.closerBoostControlFloor <= pitcher.control <= cfg.closerBoostControlCap
    assert pitcher.endurance >= cfg.closerBoostEnduranceFloor
