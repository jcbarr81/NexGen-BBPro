from playbalance.state import PitcherState


def test_pitch_zone_counter_sequence():
    ps = PitcherState()
    ps.record_pitch(in_zone=True, swung=False, contact=False)
    ps.record_pitch(in_zone=True, swung=True, contact=True)
    ps.record_pitch(in_zone=False, swung=True, contact=False)
    ps.record_pitch(in_zone=False, swung=True, contact=True)
    ps.record_pitch(in_zone=False, swung=False, contact=False)

    assert ps.zone_pitches == 2
    assert ps.o_zone_pitches == 3
    assert ps.zone_swings == 1
    assert ps.zone_contacts == 1
    assert ps.o_zone_swings == 2
    assert ps.o_zone_contacts == 1
