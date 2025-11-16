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


def test_autofill_falls_back_to_starters_for_bullpen_roles():
    # Only starters provided; bullpen slots should still be filled without duplicates.
    players = [
        (f"sp{i}", {"role": "SP", "endurance": 90 - i * 5})
        for i in range(10)
    ]

    assignments = autofill_pitching_staff(players)

    # Rotation should still consume five distinct starters.
    assert len({assignments.get(f"SP{i}") for i in range(1, 6)}) == len(
        [assignments.get(f"SP{i}") for i in range(1, 6) if assignments.get(f"SP{i}")]
    )

    # Bullpen roles should all be present and unique.
    for role in ("LR", "MR", "SU", "CL"):
        assert role in assignments and assignments[role]

    values = list(assignments.values())
    assert len(values) == len(set(values))


def test_autofill_assigns_closer_when_relivers_insufficient():
    players = [
        ("sp1", {"role": "SP", "endurance": 85}),
        ("sp2", {"role": "SP", "endurance": 80}),
        ("sp3", {"role": "SP", "endurance": 75}),
        ("sp4", {"role": "SP", "endurance": 70}),
        ("sp5", {"role": "SP", "endurance": 65}),
        ("sp6", {"role": "SP", "endurance": 60}),
        ("rp1", {"role": "RP", "endurance": 55}),
        ("rp2", {"role": "RP", "endurance": 50}),
        ("rp3", {"role": "RP", "endurance": 45}),
    ]

    assignments = autofill_pitching_staff(players)

    assert assignments["LR"] == "rp1"
    assert assignments["MR"] == "rp2"
    # Only one RP left, so SU should use rp3 and CL should fall back to a starter.
    assert assignments["SU"] == "rp3"
    assert assignments["CL"].startswith("sp")
    assert len(set(assignments.values())) == len(assignments)


def test_autofill_prefers_designated_closer():
    players = [
        ("sp1", {"role": "SP", "endurance": 90}),
        ("sp2", {"role": "SP", "endurance": 85}),
        ("sp3", {"role": "SP", "endurance": 80}),
        ("sp4", {"role": "SP", "endurance": 78}),
        ("sp5", {"role": "SP", "endurance": 76}),
        ("rp1", {"role": "RP", "endurance": 70}),
        ("rp2", {"role": "RP", "endurance": 65}),
        (
            "cl1",
            {"role": "RP", "endurance": 45, "preferred_pitching_role": "CL"},
        ),
        (
            "cl2",
            {"role": "RP", "endurance": 42, "preferred_pitching_role": "CL"},
        ),
    ]

    assignments = autofill_pitching_staff(players)

    assert assignments["CL"] == "cl2"  # lower-endurance closer should finish games
    assert assignments["CL"] not in {assignments["LR"], assignments["MR"], assignments["SU"]}


def test_autofill_elevates_preferred_starter_relief():
    players = [
        ("rp_sp", {"role": "RP", "endurance": 68, "preferred_pitching_role": "SP"}),
        ("rp_lr", {"role": "RP", "endurance": 62}),
        ("rp_mid", {"role": "RP", "endurance": 58}),
        ("rp_su", {"role": "RP", "endurance": 55}),
        ("rp_cl", {"role": "RP", "endurance": 40, "preferred_pitching_role": "CL"}),
    ]

    assignments = autofill_pitching_staff(players)

    # Reliever who prefers starting should anchor SP1 despite RP designation.
    assert assignments["SP1"] == "rp_sp"
    # Remaining relievers should backfill the rotation before bullpen roles.
    assert assignments["SP2"] == "rp_lr"
    assert assignments["SP3"] == "rp_mid"
    assert assignments["SP4"] == "rp_su"
    assert assignments["SP5"] == "rp_cl"


def test_autofill_handles_all_relief_staff():
    players = [
        (f"rp{i}", {"role": "RP", "endurance": 70 - i * 3})
        for i in range(9)
    ]

    assignments = autofill_pitching_staff(players)

    for slot in ("SP1", "SP2", "SP3", "SP4", "SP5"):
        assert assignments.get(slot) is not None
    assert len(set(assignments.values())) == len(assignments)
