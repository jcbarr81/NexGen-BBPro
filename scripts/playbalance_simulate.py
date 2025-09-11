"""Simulate a season schedule using the play-balance engine.

This script loads real rosters and plays out an entire schedule generated for
the configured teams.  Box score totals are aggregated across the league and
compared to MLB benchmarks.

Usage examples::

    python scripts/playbalance_simulate.py --seed 1
    python scripts/playbalance_simulate.py --games 20 --output results.json

"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from copy import deepcopy
from datetime import date
from pathlib import Path
import random
import sys

from tqdm import tqdm

# Allow running the script without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from playbalance.benchmarks import load_benchmarks, league_average
from logic.schedule_generator import generate_mlb_schedule
from logic.sim_config import load_tuned_playbalance_config
from logic.simulation import (
    FieldingState,
    GameSimulation,
    PitcherState,
    TeamState,
    generate_boxscore,
)
from utils.lineup_loader import build_default_game_state
from utils.team_loader import load_teams


def clone_team_state(base: TeamState) -> TeamState:
    """Return a deep-copied ``TeamState`` with per-game fields reset."""

    team = deepcopy(base)
    team.lineup_stats = {}
    team.pitcher_stats = {}
    team.fielding_stats = {}
    team.batting_index = 0
    team.bases = [None, None, None]
    team.base_pitchers = [None, None, None]
    team.runs = 0
    team.inning_runs = []
    team.lob = 0
    team.inning_lob = []
    team.inning_events = []
    team.team_stats = {}
    team.warming_reliever = False
    team.bullpen_warmups = {}
    if team.pitchers:
        starter = team.pitchers[0]
        ps = PitcherState(starter)
        team.pitcher_stats[starter.player_id] = ps
        team.current_pitcher_state = ps
        ps.g += 1
        ps.gs += 1
        fs = team.fielding_stats.setdefault(
            starter.player_id, FieldingState(starter)
        )
        fs.g += 1
        fs.gs += 1
    else:
        team.current_pitcher_state = None
    for p in team.lineup:
        fs = team.fielding_stats.setdefault(
            p.player_id, FieldingState(p)
        )
        fs.g += 1
        fs.gs += 1
    return team


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Simulate games using the play-balance engine"
    )
    parser.add_argument(
        "--games",
        type=int,
        default=162,
        help="number of games each team plays",
    )
    parser.add_argument(
        "--start-date",
        type=lambda s: date.fromisoformat(s),
        default=date(2025, 4, 1),
        help="start date for the generated schedule (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="random seed for reproducibility",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="optional file to write JSON aggregated results to",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="disable progress bar",
    )
    args = parser.parse_args(argv)

    benchmarks = load_benchmarks()
    cfg, _ = load_tuned_playbalance_config()

    team_ids = [t.team_id for t in load_teams("data/teams.csv")]
    base_states = {tid: build_default_game_state(tid) for tid in team_ids}
    schedule = generate_mlb_schedule(team_ids, args.start_date, args.games)

    rng = random.Random(args.seed)
    totals: Counter[str] = Counter()

    def simulate_game(home_id: str, away_id: str) -> None:
        home = clone_team_state(base_states[home_id])
        away = clone_team_state(base_states[away_id])
        sim = GameSimulation(home, away, cfg, rng)
        sim.simulate_game()
        box = generate_boxscore(home, away)
        for side in ("home", "away"):
            batting = box[side]["batting"]
            totals["pa"] += sum(p["pa"] for p in batting)
            totals["bb"] += sum(p["bb"] for p in batting)
            totals["k"] += sum(p["so"] for p in batting)
            totals["h"] += sum(p["h"] for p in batting)
            totals["hr"] += sum(p["hr"] for p in batting)
            totals["ab"] += sum(p["ab"] for p in batting)
            totals["sf"] += sum(p.get("sf", 0) for p in batting)
            totals["sb"] += sum(p["sb"] for p in batting)
            totals["cs"] += sum(p["cs"] for p in batting)

        for team in (home, away):
            for bs in team.lineup_stats.values():
                totals["hbp"] += bs.hbp
                totals["b1"] += bs.b1
                totals["b2"] += bs.b2
                totals["b3"] += bs.b3
                totals["gb"] += bs.gb
                totals["ld"] += bs.ld
                totals["fb"] += bs.fb
                totals["gidp"] += bs.gidp
            for ps in team.pitcher_stats.values():
                totals["pitches_thrown"] += ps.pitches_thrown
                totals["zone_pitches"] += ps.zone_pitches
                totals["zone_swings"] += ps.zone_swings
                totals["zone_contacts"] += ps.zone_contacts
                totals["o_zone_swings"] += ps.o_zone_swings
                totals["o_zone_contacts"] += ps.o_zone_contacts
                totals["so_looking"] += ps.so_looking

    for game in tqdm(
        schedule, desc="Simulating games", disable=args.no_progress
    ):
        simulate_game(game["home"], game["away"])

    pa = totals["pa"] or 1
    pitches = totals["pitches_thrown"] or 1
    bip = totals["gb"] + totals["ld"] + totals["fb"]

    k_pct = totals["k"] / pa
    bb_pct = totals["bb"] / pa
    pitches_per_pa = pitches / pa
    pitches_put_in_play_pct = bip / pitches if pitches else 0.0
    bip_gb_pct = totals["gb"] / bip if bip else 0.0
    bip_fb_pct = totals["fb"] / bip if bip else 0.0
    bip_ld_pct = totals["ld"] / bip if bip else 0.0
    bip_double_play_pct = totals["gidp"] / bip if bip else 0.0
    hits_on_bip = totals["h"] - totals["hr"]
    babip = hits_on_bip / bip if bip else 0.0
    tb = (
        totals["b1"] + 2 * totals["b2"] + 3 * totals["b3"] + 4 * totals["hr"]
    )
    avg = totals["h"] / totals["ab"] if totals["ab"] else 0.0
    obp_den = totals["ab"] + totals["bb"] + totals["hbp"] + totals["sf"]
    obp = (
        (totals["h"] + totals["bb"] + totals["hbp"])
        / obp_den
        if obp_den
        else 0.0
    )
    slg = tb / totals["ab"] if totals["ab"] else 0.0
    swings = totals["zone_swings"] + totals["o_zone_swings"]
    contacts = totals["zone_contacts"] + totals["o_zone_contacts"]
    swstr_pct = (swings - contacts) / pitches if pitches else 0.0
    called_third_strike_share_of_so = (
        totals["so_looking"] / totals["k"] if totals["k"] else 0.0
    )
    o_zone_pitches = pitches - totals["zone_pitches"]
    o_swing_pct = (
        totals["o_zone_swings"] / o_zone_pitches if o_zone_pitches else 0.0
    )
    z_swing_pct = (
        totals["zone_swings"] / totals["zone_pitches"]
        if totals["zone_pitches"]
        else 0.0
    )
    swing_pct = swings / pitches if pitches else 0.0
    z_contact_pct = (
        totals["zone_contacts"] / totals["zone_swings"]
        if totals["zone_swings"]
        else 0.0
    )
    o_contact_pct = (
        totals["o_zone_contacts"] / totals["o_zone_swings"]
        if totals["o_zone_swings"]
        else 0.0
    )
    contact_pct = contacts / swings if swings else 0.0
    sb_attempts = totals["sb"] + totals["cs"]
    sba_rate = sb_attempts / pa
    sb_pct = totals["sb"] / sb_attempts if sb_attempts else 0.0

    results = {
        "pa": totals["pa"],
        "k": totals["k"],
        "bb": totals["bb"],
        "hits": totals["h"],
        "home_runs": totals["hr"],
        "sb_success": totals["sb"],
        "sb_caught": totals["cs"],
    }

    if args.output is not None:
        args.output.write_text(json.dumps(results, indent=2))
        print(f"Saved results to {args.output}")

    print(
        f"Pitches/PA: {pitches_per_pa:.2f} "
        f"(MLB {league_average(benchmarks, 'pitches_per_pa'):.2f})"
    )
    print(
        "Pitches Put In Play%: "
        f"{pitches_put_in_play_pct:.3f} "
        f"(MLB {league_average(benchmarks, 'pitches_put_in_play_pct'):.3f})"
    )
    print(
        f"BIP GB%: {bip_gb_pct:.3f} "
        f"(MLB {league_average(benchmarks, 'bip_gb_pct'):.3f})"
    )
    print(
        f"BIP FB%: {bip_fb_pct:.3f} "
        f"(MLB {league_average(benchmarks, 'bip_fb_pct'):.3f})"
    )
    print(
        f"BIP LD%: {bip_ld_pct:.3f} "
        f"(MLB {league_average(benchmarks, 'bip_ld_pct'):.3f})"
    )
    print(
        f"Double Play%: {bip_double_play_pct:.3f} "
        f"(MLB {league_average(benchmarks, 'bip_double_play_pct'):.3f})"
    )
    print(f"AVG:  {avg:.3f} (MLB {league_average(benchmarks, 'avg'):.3f})")
    print(f"OBP:  {obp:.3f} (MLB {league_average(benchmarks, 'obp'):.3f})")
    print(f"SLG:  {slg:.3f} (MLB {league_average(benchmarks, 'slg'):.3f})")
    print(
        f"SwStr%: {swstr_pct:.3f} "
        f"(MLB {league_average(benchmarks, 'swstr_pct'):.3f})"
    )
    called_share_avg = league_average(
        benchmarks, "called_third_strike_share_of_so"
    )
    print(
        "Called Strike 3 Share: "
        f"{called_third_strike_share_of_so:.3f} (MLB {called_share_avg:.3f})"
    )
    print(
        f"O-Swing%: {o_swing_pct:.3f} "
        f"(MLB {league_average(benchmarks, 'o_swing_pct'):.3f})"
    )
    print(
        f"Z-Swing%: {z_swing_pct:.3f} "
        f"(MLB {league_average(benchmarks, 'z_swing_pct'):.3f})"
    )
    print(
        f"Swing%: {swing_pct:.3f} "
        f"(MLB {league_average(benchmarks, 'swing_pct'):.3f})"
    )
    print(
        f"Z-Contact%: {z_contact_pct:.3f} "
        f"(MLB {league_average(benchmarks, 'z_contact_pct'):.3f})"
    )
    print(
        f"O-Contact%: {o_contact_pct:.3f} "
        f"(MLB {league_average(benchmarks, 'o_contact_pct'):.3f})"
    )
    print(
        f"Contact%: {contact_pct:.3f} "
        f"(MLB {league_average(benchmarks, 'contact_pct'):.3f})"
    )
    print(
        f"K%:  {k_pct:.3f} (MLB {league_average(benchmarks, 'k_pct'):.3f})"
    )
    print(
        f"BB%: {bb_pct:.3f} (MLB {league_average(benchmarks, 'bb_pct'):.3f})"
    )
    print(
        f"BABIP: {babip:.3f} (MLB {league_average(benchmarks, 'babip'):.3f})"
    )
    print(
        f"SB Attempt/PA: {sba_rate:.3f} "
        f"(MLB {league_average(benchmarks, 'sba_per_pa'):.3f})"
    )
    print(
        f"SB%: {sb_pct:.3f} (MLB {league_average(benchmarks, 'sb_pct'):.3f})"
    )

    return 0


if __name__ == "__main__":  # pragma: no cover - script entry point
    raise SystemExit(main())

