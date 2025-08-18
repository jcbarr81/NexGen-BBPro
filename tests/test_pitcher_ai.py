import random

from logic.pitcher_ai import PitcherAI
from models.player import Player
from models.pitcher import Pitcher
from tests.util.pbini_factory import make_cfg


class SeqRandom(random.Random):
    """Random generator that returns predefined integers."""

    def __init__(self, ints: list[int], floats: list[float] | None = None):
        super().__init__()
        self.ints = list(ints)
        self.floats = list(floats or [])

    def randint(self, a, b):  # type: ignore[override]
        return self.ints.pop(0)

    def random(self):  # type: ignore[override]
        if self.floats:
            return self.floats.pop(0)
        return 0.5


def make_player(pid: str) -> Player:
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
        ch=50,
        ph=50,
        sp=50,
        pl=0,
        vl=0,
        sc=0,
        fa=0,
        arm=0,
    )


def make_pitcher(pid: str, fb: int = 50, sl: int = 49) -> Pitcher:
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
        fb=fb,
        sl=sl,
        cu=0,
        cb=0,
        si=0,
        scb=0,
        kn=0,
        arm=50,
        fa=50,
        role="SP",
    )


def test_primary_pitch_adjust_affects_selection():
    pitcher = make_pitcher("p1")
    cfg_base = dict(
        pitchRatVariationCount=1,
        pitchRatVariationFaces=6,
        pitchRatVariationBase=0,
        nonEstablishedPitchTypeAdjust=0,
    )

    cfg1 = make_cfg(**cfg_base, primaryPitchTypeAdjust=0)
    ai1 = PitcherAI(cfg1, SeqRandom([1, 6]))  # fb -> 1, sl -> 6
    ai1.new_game()
    pitch1, _ = ai1.select_pitch(pitcher)
    assert pitch1 == "sl"

    cfg2 = make_cfg(**cfg_base, primaryPitchTypeAdjust=10)
    ai2 = PitcherAI(cfg2, SeqRandom([1, 6]))
    ai2.new_game()
    pitch2, _ = ai2.select_pitch(pitcher)
    assert pitch2 == "fb"


def test_pitch_objective_weights():
    pitcher = make_pitcher("p2", sl=0)
    cfg = make_cfg(
        pitchRatVariationCount=1,
        pitchRatVariationFaces=6,
        pitchRatVariationBase=0,
        pitchObj00CountEstablishWeight=1,
        pitchObj00CountOutsideWeight=2,
        pitchObj00CountBestWeight=3,
    )
    # Three calls using deterministic floats to select each objective based on
    # their relative weight: 1/6 establish, 2/6 outside, 3/6 best.
    ai = PitcherAI(cfg, SeqRandom([1], floats=[0.0, 0.4, 0.9]))
    ai.new_game()
    _, obj1 = ai.select_pitch(pitcher)
    _, obj2 = ai.select_pitch(pitcher)
    _, obj3 = ai.select_pitch(pitcher)

    assert obj1 == "establish"
    assert obj2 == "outside"
    assert obj3 == "best"


def test_pitch_variation_cached_per_game():
    pitcher = make_pitcher("p3")
    cfg = make_cfg(
        pitchRatVariationCount=1,
        pitchRatVariationFaces=6,
        pitchRatVariationBase=0,
        nonEstablishedPitchTypeAdjust=0,
    )
    # Provide enough integers for two games. If variation was re-rolled every
    # pitch the RNG would be exhausted before the second game begins.
    rng = SeqRandom([1, 6, 5, 2])
    ai = PitcherAI(cfg, rng)

    ai.new_game()
    pitch1, _ = ai.select_pitch(pitcher)
    pitch2, _ = ai.select_pitch(pitcher)
    assert pitch1 == pitch2 == "sl"

    ai.new_game()
    pitch3, _ = ai.select_pitch(pitcher)
    pitch4, _ = ai.select_pitch(pitcher)
    assert pitch3 == pitch4 == "fb"

