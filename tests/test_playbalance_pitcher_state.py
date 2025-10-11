from playbalance.state import PitcherState


def test_pitcher_state_records_zone_and_contact():
    ps = PitcherState()
    ps.record_pitch(in_zone=True, swung=True, contact=True)
    ps.record_pitch(in_zone=False, swung=True, contact=False)
    assert ps.zone_pitches == 1
    assert ps.zone_swings == 1
    assert ps.zone_contacts == 1
    assert ps.o_zone_swings == 1
    assert ps.o_zone_contacts == 0


def test_pitcher_state_defaults():
    ps = PitcherState()
    assert ps.ir == 0
    assert ps.irs == 0
    assert ps.svo == 0
    assert ps.sv == 0
    assert ps.hld == 0
    assert ps.bs == 0
    assert not ps.in_save_situation
