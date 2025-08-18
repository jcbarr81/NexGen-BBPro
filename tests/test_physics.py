import random

import pytest

from logic.batter_ai import BatterAI
from logic.simulation import GameSimulation, TeamState, BatterState
from logic.physics import Physics
from models.player import Player
from models.pitcher import Pitcher
from tests.util.pbini_factory import make_cfg


class MockRandom(random.Random):
    """Deterministic random generator using a predefined sequence."""

    def __init__(self, values):
        super().__init__()
        self.values = list(values)

    def random(self):  # type: ignore[override]
        return self.values.pop(0)

    def randint(self, a, b):  # type: ignore[override]
        # ``PitcherAI`` uses ``randint`` for pitch variation.  Returning the
        # lower bound keeps the predefined sequence for ``random`` intact.
        return a


def make_player(pid: str, ph: int = 50, sp: int = 50, ch: int = 50) -> Player:
    return Player(
        player_id=pid,
        first_name="F" + pid,
        last_name="L" + pid,
        birthdate="2000-01-01",
        height=72,
        weight=180,
        bats="R",
        primary_position="1B",
        other_positions=[],
        gf=50,
        ch=ch,
        ph=ph,
        sp=sp,
        pl=0,
        vl=0,
        sc=0,
        fa=0,
        arm=0,
    )


def make_pitcher(pid: str) -> Pitcher:
    return Pitcher(
        player_id=pid,
        first_name="PF" + pid,
        last_name="PL" + pid,
        birthdate="2000-01-01",
        height=72,
        weight=180,
        bats="R",
        primary_position="P",
        other_positions=[],
        gf=50,
        endurance=100,
        control=50,
        movement=50,
        hold_runner=50,
        fb=50,
        cu=0,
        cb=0,
        sl=0,
        si=0,
        scb=0,
        kn=0,
        arm=50,
        fa=50,
        role="SP",
    )


def test_swing_angle_varies_with_range():
    cfg = make_cfg(
        swingAngleTenthDegreesBase=100,
        swingAngleTenthDegreesRange=20,
    )
    rng = MockRandom([0.0, 0.9])
    physics = Physics(cfg, rng)
    angle1 = physics.swing_angle(50)
    angle2 = physics.swing_angle(50)
    assert angle1 == pytest.approx(10.0)
    assert angle2 == pytest.approx(11.8)
    assert angle1 != angle2


def test_vertical_hit_angle_power_vs_contact():
    cfg = make_cfg(
        hitAngleCountPower=1,
        hitAngleFacesPower=59,
        hitAngleBasePower=0,
        hitAngleCountContact=1,
        hitAngleFacesContact=39,
        hitAngleBaseContact=0,
    )
    power_phys = Physics(cfg, random.Random(0))
    contact_phys = Physics(cfg, random.Random(0))
    power_angles = [power_phys.vertical_hit_angle("power") for _ in range(1000)]
    contact_angles = [contact_phys.vertical_hit_angle("contact") for _ in range(1000)]
    assert sum(power_angles) / len(power_angles) > sum(contact_angles) / len(contact_angles)


def test_swing_result_respects_bat_speed():
    # Low bat speed -> out
    cfg_slow = make_cfg(swingSpeedBase=10, averagePitchSpeed=50)
    batter1 = make_player("b1")
    home1 = TeamState(lineup=[make_player("h1")], bench=[], pitchers=[make_pitcher("hp1")])
    away1 = TeamState(lineup=[batter1], bench=[], pitchers=[make_pitcher("ap1")])
    rng1 = MockRandom([0.0, 0.4, 0.0, 0.4, 0.0, 0.4])
    sim1 = GameSimulation(home1, away1, cfg_slow, rng1)
    outs1 = sim1.play_at_bat(away1, home1)
    assert outs1 == 1
    assert away1.lineup_stats["b1"].h == 0

    # High bat speed -> hit
    cfg_fast = make_cfg(swingSpeedBase=80, averagePitchSpeed=50)
    batter2 = make_player("b2")
    home2 = TeamState(lineup=[make_player("h2")], bench=[], pitchers=[make_pitcher("hp2")])
    away2 = TeamState(lineup=[batter2], bench=[], pitchers=[make_pitcher("ap2")])
    rng2 = MockRandom([0.0, 0.0, 0.9])
    sim2 = GameSimulation(home2, away2, cfg_fast, rng2)
    outs2 = sim2.play_at_bat(away2, home2)
    assert outs2 == 0
    assert away2.lineup_stats["b2"].h == 1


def test_runner_advancement_respects_speed():
    batter1 = make_player("bat1", ph=80)
    runner1 = make_player("run1", sp=50)
    runner_state1 = BatterState(runner1)
    home1 = TeamState(lineup=[make_player("h1")], bench=[], pitchers=[make_pitcher("hp1")])
    away1 = TeamState(lineup=[batter1], bench=[], pitchers=[make_pitcher("ap1")])
    away1.lineup_stats[runner1.player_id] = runner_state1
    away1.bases[0] = runner_state1

    cfg_slow = make_cfg(speedBase=10, averagePitchSpeed=50)
    rng1 = MockRandom([0.0, 0.0, 0.9, 0.9])
    sim1 = GameSimulation(home1, away1, cfg_slow, rng1)
    outs1 = sim1.play_at_bat(away1, home1)
    assert outs1 == 0
    assert away1.bases[1] is runner_state1
    assert away1.bases[2] is None

    batter2 = make_player("bat2", ph=80)
    runner2 = make_player("run2", sp=50)
    runner_state2 = BatterState(runner2)
    home2 = TeamState(lineup=[make_player("h2")], bench=[], pitchers=[make_pitcher("hp2")])
    away2 = TeamState(lineup=[batter2], bench=[], pitchers=[make_pitcher("ap2")])
    away2.lineup_stats[runner2.player_id] = runner_state2
    away2.bases[0] = runner_state2

    cfg_fast = make_cfg(speedBase=30, averagePitchSpeed=50)
    rng2 = MockRandom([0.0, 0.0, 0.9, 0.9])
    sim2 = GameSimulation(home2, away2, cfg_fast, rng2)
    outs2 = sim2.play_at_bat(away2, home2)
    assert outs2 == 0
    assert away2.bases[2] is runner_state2


def test_roll_distance_respects_surface_friction():
    cfg = make_cfg(
        rollFrictionGrass=12,
        rollFrictionTurf=6,
        ballAirResistancePct=100,
    )
    physics = Physics(cfg)
    grass = physics.ball_roll_distance(100, surface="grass")
    turf = physics.ball_roll_distance(100, surface="turf")
    assert grass < turf


def test_bounce_wet_vs_dry():
    cfg = make_cfg(
        bounceVertGrassPct=50,
        bounceHorizGrassPct=50,
        bounceWetAdjust=-10,
    )
    physics = Physics(cfg)
    dry_vert, dry_horiz = physics.ball_bounce(100, 100, surface="grass", wet=False)
    wet_vert, wet_horiz = physics.ball_bounce(100, 100, surface="grass", wet=True)
    assert wet_vert < dry_vert
    assert wet_horiz < dry_horiz


def test_roll_distance_altitude_and_wind():
    cfg = make_cfg(
        rollFrictionGrass=10,
        ballAirResistancePct=100,
        ballAltitudePct=10,
        ballWindSpeedPct=10,
    )
    physics = Physics(cfg)
    base = physics.ball_roll_distance(100, surface="grass", altitude=0, wind_speed=0)
    altwind = physics.ball_roll_distance(
        100, surface="grass", altitude=1000, wind_speed=10
    )
    assert altwind > base


def test_bat_speed_adjusts_for_pitch_speed():
    cfg = make_cfg(
        averagePitchSpeed=90,
        fastPitchBatSlowdownPct=50,
        slowPitchBatSpeedupPct=50,
    )
    physics = Physics(cfg)
    ph = 50
    base = physics.bat_speed(ph, pitch_speed=90)
    fast = physics.bat_speed(ph, pitch_speed=100)
    slow = physics.bat_speed(ph, pitch_speed=80)
    assert fast == pytest.approx(base - 5)
    assert slow == pytest.approx(base + 5)


def test_bat_impact_sweet_spot_more_power():
    cfg = make_cfg()
    physics = Physics(cfg)
    bat_speed = 100.0
    sweet, _ = physics.bat_impact(bat_speed, part="sweet", rand=0.5)
    handle, _ = physics.bat_impact(bat_speed, part="handle", rand=0.5)
    end, _ = physics.bat_impact(bat_speed, part="end", rand=0.5)
    assert sweet > handle
    assert sweet > end


@pytest.mark.parametrize(
    "ptype, cfg_key",
    [
        ("fb", "fb"),
        ("cb", "cb"),
        ("cu", "cu"),
        ("sl", "sl"),
        ("si", "si"),
        ("scb", "sb"),
        ("kn", "kb"),
    ],
)
def test_pitch_velocity_by_type(ptype, cfg_key):
    cfg = make_cfg(
        **{
            f"{cfg_key}SpeedBase": 60,
            f"{cfg_key}SpeedRange": 10,
            f"{cfg_key}SpeedASPct": 20,
        }
    )
    physics = Physics(cfg, MockRandom([0.5]))
    speed = physics.pitch_velocity(ptype, as_rating=50)
    assert speed == pytest.approx(60 + 5 + 10)


class CaptureDist(Exception):
    """Internal exception used to abort after a single pitch."""


class TrackingBatterAI(BatterAI):
    """Batter AI that records the last distance value passed in."""

    last_dist: int | None = None

    def decide_swing(
        self,
        batter,
        pitcher,
        *,
        pitch_type: str,
        balls: int = 0,
        strikes: int = 0,
        dist: int = 0,
        random_value: float = 0.0,
    ):
        self.last_dist = dist
        raise CaptureDist


def make_pitcher_for_type(pid: str, pitch_type: str) -> Pitcher:
    ratings = {p: 0 for p in ["fb", "sl", "cu", "cb", "si", "scb", "kn"]}
    ratings[pitch_type] = 50
    return Pitcher(
        player_id=pid,
        first_name="PF" + pid,
        last_name="PL" + pid,
        birthdate="2000-01-01",
        height=72,
        weight=180,
        bats="R",
        primary_position="P",
        other_positions=[],
        gf=50,
        endurance=100,
        control=100,
        movement=50,
        hold_runner=50,
        fb=ratings["fb"],
        cu=ratings["cu"],
        cb=ratings["cb"],
        sl=ratings["sl"],
        si=ratings["si"],
        scb=ratings["scb"],
        kn=ratings["kn"],
        arm=50,
        fa=50,
        role="SP",
    )


@pytest.mark.parametrize(
    "ptype,cfg_key,width,height",
    [
        ("fb", "fb", 5, 1),
        ("cb", "cb", 1, 6),
        ("cu", "cu", 7, 3),
        ("sl", "sl", 2, 8),
        ("scb", "sb", 9, 4),
        ("kn", "kb", 3, 10),
        ("si", "si", 11, 5),
    ],
)
def test_pitch_aim_uses_control_box_dimensions(ptype, cfg_key, width, height):
    cfg = make_cfg(
        **{
            f"{cfg_key}ControlBoxWidth": width,
            f"{cfg_key}ControlBoxHeight": height,
        }
    )
    pitcher = make_pitcher_for_type("hp", ptype)
    batter = make_player("b")
    away = TeamState(lineup=[batter], bench=[], pitchers=[make_pitcher("ap")])
    home = TeamState(lineup=[make_player("h1")], bench=[], pitchers=[pitcher])
    rng = MockRandom([0.9, 0.0])
    sim = GameSimulation(home, away, cfg, rng)
    tracker = TrackingBatterAI(cfg)
    sim.batter_ai = tracker
    with pytest.raises(CaptureDist):
        sim.play_at_bat(away, home)
    expected = int(round(0.8 * max(width, height)))
    assert tracker.last_dist == expected


@pytest.mark.parametrize(
    "ptype,cfg_key",
    [
        ("fb", "fb"),
        ("cb", "cb"),
        ("cu", "cu"),
        ("sl", "sl"),
        ("scb", "sb"),
        ("kn", "kb"),
        ("si", "si"),
    ],
)
def test_control_box_lookup(ptype, cfg_key):
    cfg = make_cfg(
        **{f"{cfg_key}ControlBoxWidth": 3, f"{cfg_key}ControlBoxHeight": 4}
    )
    physics = Physics(cfg)
    assert physics.control_box(ptype) == (3, 4)


@pytest.mark.parametrize(
    "ptype,cfg_key",
    [
        ("fb", "fb"),
        ("cb", "cb"),
        ("cu", "cu"),
        ("sl", "sl"),
        ("scb", "sb"),
        ("kn", "kb"),
        ("si", "si"),
    ],
)
def test_pitch_break_lookup(ptype, cfg_key):
    cfg = make_cfg(
        **{
            f"{cfg_key}BreakBaseWidth": 1,
            f"{cfg_key}BreakBaseHeight": 2,
            f"{cfg_key}BreakRangeWidth": 3,
            f"{cfg_key}BreakRangeHeight": 4,
        }
    )
    physics = Physics(cfg)
    dx, dy = physics.pitch_break(ptype, rand=0.5)
    assert dx == pytest.approx(1 + 1.5)
    assert dy == pytest.approx(2 + 2)


def _throw_for_dist(ptype: str, cfg, rng_vals=None) -> int:
    """Helper to throw a single pitch and capture ``dist``."""

    rng_vals = rng_vals or [0.0, 0.0]
    pitcher = make_pitcher_for_type("hp", ptype)
    batter = make_player("b")
    away = TeamState(lineup=[batter], bench=[], pitchers=[make_pitcher("ap")])
    home = TeamState(lineup=[make_player("h1")], bench=[], pitchers=[pitcher])
    sim = GameSimulation(home, away, cfg, MockRandom(rng_vals))
    tracker = TrackingBatterAI(cfg)
    sim.batter_ai = tracker
    with pytest.raises(CaptureDist):
        sim.play_at_bat(away, home)
    return tracker.last_dist  # type: ignore[return-value]


@pytest.mark.parametrize(
    "ptype,cfg_key,dx,dy",
    [
        ("cb", "cb", 2, -5),
        ("scb", "sb", -2, -4),
    ],
)
def test_pitch_break_affects_location(ptype, cfg_key, dx, dy):
    cfg = make_cfg(
        fbControlBoxWidth=0,
        fbControlBoxHeight=0,
        fbBreakBaseWidth=0,
        fbBreakBaseHeight=0,
        fbBreakRangeWidth=0,
        fbBreakRangeHeight=0,
        **{
            f"{cfg_key}ControlBoxWidth": 0,
            f"{cfg_key}ControlBoxHeight": 0,
            f"{cfg_key}BreakBaseWidth": dx,
            f"{cfg_key}BreakBaseHeight": dy,
            f"{cfg_key}BreakRangeWidth": 0,
            f"{cfg_key}BreakRangeHeight": 0,
        },
    )
    dist_fast = _throw_for_dist("fb", cfg)
    dist_non = _throw_for_dist(ptype, cfg)
    assert dist_fast == 0
    expected = int(round(max(abs(dx), abs(dy))))
    assert dist_non == expected
    assert dist_non != dist_fast


def test_missed_control_expands_box_and_reduces_velocity():
    cfg = make_cfg(
        fbControlBoxWidth=2,
        fbControlBoxHeight=3,
        fbSpeedBase=10,
        fbSpeedRange=0,
        fbSpeedASPct=0,
        controlBoxIncreaseEffCOPct=25,
        speedReductionBase=3,
        speedReductionRange=0,
        speedReductionEffMOPct=5,
    )
    pitcher = make_pitcher_for_type("hp", "fb")
    pitcher.control = 50
    batter = make_player("b")
    away = TeamState(lineup=[batter], bench=[], pitchers=[make_pitcher("ap")])
    home = TeamState(lineup=[make_player("h1")], bench=[], pitchers=[pitcher])
    sim = GameSimulation(home, away, cfg, MockRandom([0.9, 0.0]))
    tracker = TrackingBatterAI(cfg)
    sim.batter_ai = tracker
    with pytest.raises(CaptureDist):
        sim.play_at_bat(away, home)
    miss_amt = (0.9 - 0.5) * 100
    inc = miss_amt * cfg.controlBoxIncreaseEffCOPct / 100
    expected_dist = int(round((max(2, 3) + inc) * 0.8))
    assert tracker.last_dist == expected_dist
    reduction = (
        cfg.speedReductionBase
        + miss_amt * cfg.speedReductionEffMOPct / 100
    )
    assert sim.last_pitch_speed == pytest.approx(10 - reduction)
