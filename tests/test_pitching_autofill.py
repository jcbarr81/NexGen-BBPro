from utils.pitching_autofill import autofill_pitching_staff


def test_autofill_prefers_sp_and_low_endurance_closer():
    players = [
        ("sp1", {"role": "SP", "endurance": 80}),
        ("sp2", {"role": "SP", "endurance": 70}),
        ("sp3", {"role": "SP", "endurance": 60}),
        ("rp1", {"role": "RP", "endurance": 55}),
        ("rp2", {"role": "RP", "endurance": 45}),
        ("rp3", {"role": "RP", "endurance": 35}),
        ("rp4", {"role": "RP", "endurance": 25}),
        ("rp5", {"role": "RP", "endurance": 15}),
        ("rp6", {"role": "RP", "endurance": 5}),
    ]

    assignments = autofill_pitching_staff(players)

    # Starters should be filled with SPs when available
    assert assignments["SP1"] == "sp1"
    assert assignments["SP2"] == "sp2"
    assert assignments["SP3"] == "sp3"
    # Not enough SPs for SP4/SP5; highest-endurance RPs fill in
    assert assignments["SP4"] == "rp1"
    assert assignments["SP5"] == "rp2"

    # Bullpen: long/middle/setup use remaining highest-endurance RPs
    assert assignments["LR"] == "rp3"
    assert assignments["MR"] == "rp4"
    assert assignments["SU"] == "rp5"

    # Closer should get the lowest-endurance RP
    assert assignments["CL"] == "rp6"

    # Ensure each pitcher is used only once
    assert len(set(assignments.values())) == len(assignments)
