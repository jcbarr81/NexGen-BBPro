from collections import Counter

from scripts.physics_sim_season_kpis import (
    _build_rating_splits,
    _decile_groups,
    evaluate_tolerances,
)


def test_evaluate_tolerances_flags_violation() -> None:
    metrics = {"k_pct": 0.3}
    benchmarks = {"k_pct": 0.2}
    tolerances = {"k_pct": 0.05}
    failures = evaluate_tolerances(
        metrics=metrics,
        benchmarks=benchmarks,
        tolerances=tolerances,
    )
    assert failures
    assert failures[0]["metric"] == "k_pct"


def test_decile_groups_selects_edges() -> None:
    ratings = {f"P{i}": float(i) for i in range(10)}
    bottom, top = _decile_groups(ratings)
    assert bottom == {"P0"}
    assert top == {"P9"}


def test_build_rating_splits_returns_expected_keys() -> None:
    batter_totals = {
        "B1": Counter(pa=10, ab=10, h=4, bb=1, so=2, hr=1),
        "B2": Counter(pa=12, ab=12, h=6, bb=0, so=1, hr=0),
        "B3": Counter(pa=8, ab=8, h=2, bb=0, so=3, hr=0),
        "B4": Counter(pa=9, ab=9, h=3, bb=1, so=2, hr=1),
        "B5": Counter(pa=11, ab=11, h=5, bb=1, so=1, hr=0),
        "B6": Counter(pa=7, ab=7, h=2, bb=0, so=2, hr=0),
        "B7": Counter(pa=10, ab=10, h=4, bb=1, so=2, hr=0),
        "B8": Counter(pa=10, ab=10, h=4, bb=1, so=2, hr=1),
        "B9": Counter(pa=10, ab=10, h=4, bb=1, so=2, hr=0),
        "B10": Counter(pa=10, ab=10, h=4, bb=1, so=2, hr=0),
    }
    pitcher_totals = {
        "P1": Counter(bf=20, outs=15, er=2, h=4, bb=2, so=5, hr=1),
        "P2": Counter(bf=18, outs=12, er=3, h=5, bb=3, so=4, hr=1),
        "P3": Counter(bf=22, outs=18, er=1, h=3, bb=1, so=6, hr=0),
        "P4": Counter(bf=16, outs=12, er=2, h=5, bb=2, so=3, hr=1),
        "P5": Counter(bf=24, outs=18, er=2, h=4, bb=2, so=7, hr=1),
        "P6": Counter(bf=19, outs=15, er=3, h=6, bb=3, so=3, hr=1),
        "P7": Counter(bf=21, outs=18, er=2, h=4, bb=2, so=5, hr=0),
        "P8": Counter(bf=17, outs=12, er=2, h=4, bb=2, so=4, hr=1),
        "P9": Counter(bf=20, outs=15, er=1, h=3, bb=1, so=6, hr=0),
        "P10": Counter(bf=18, outs=12, er=3, h=5, bb=3, so=4, hr=1),
    }
    contact = {player_id: 40.0 + idx for idx, player_id in enumerate(batter_totals)}
    power = {player_id: 60.0 + idx for idx, player_id in enumerate(batter_totals)}
    control = {player_id: 50.0 + idx for idx, player_id in enumerate(pitcher_totals)}
    splits = _build_rating_splits(
        batter_totals=batter_totals,
        pitcher_totals=pitcher_totals,
        contact=contact,
        power=power,
        control=control,
    )
    assert "batters" in splits
    assert "pitchers" in splits
    assert "contact" in splits["batters"]
    assert "power" in splits["batters"]
    assert "control" in splits["pitchers"]
