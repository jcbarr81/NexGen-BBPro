from scripts.auto_tune_playbalance import apply_tuning_rules, TUNING_RULES


def test_apply_tuning_rules_generates_adjustments():
    metrics = {
        "swing_pct": 0.55,
        "z_swing_pct": 0.70,
        "o_swing_pct": 0.40,
        "pitches_put_in_play_pct": 0.15,
        "bb_pct": 0.05,
    }
    benchmarks = {
        "swing_pct": 0.47,
        "z_swing_pct": 0.65,
        "o_swing_pct": 0.32,
        "pitches_put_in_play_pct": 0.175,
        "bb_pct": 0.08,
    }
    values = {
        "swingProbScale": 1.0,
        "zSwingProbScale": 1.0,
        "oSwingProbScale": 1.0,
        "ballInPlayPitchPct": 9,
        "pitchAroundChanceBase": 10,
        "pitchAroundChanceOn23": 5,
    }

    updates = apply_tuning_rules(metrics, benchmarks, values, TUNING_RULES)

    assert updates["swingProbScale"] < values["swingProbScale"]
    assert updates["zSwingProbScale"] < values["zSwingProbScale"]
    assert updates["ballInPlayPitchPct"] > values["ballInPlayPitchPct"]
    assert updates["pitchAroundChanceBase"] > values["pitchAroundChanceBase"]


def test_apply_tuning_rules_ignores_missing_values():
    metrics = {"swing_pct": 0.45}
    benchmarks = {"swing_pct": 0.47}
    updates = apply_tuning_rules(metrics, benchmarks, {"swingProbScale": None}, TUNING_RULES)
    assert updates == {}
