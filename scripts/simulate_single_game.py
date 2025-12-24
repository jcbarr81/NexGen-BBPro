"""Simulate a single game between two teams and render an ESPN-style box score."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Iterable, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from playbalance.game_runner import (
    LineupEntry,
    read_lineup_file,
    run_single_game,
)
from playbalance.simulation import save_boxscore_html


def _maybe_read_lineup(path: Path | None) -> Sequence[LineupEntry] | None:
    """Return lineup entries from ``path`` if provided."""

    if path is None:
        return None
    return read_lineup_file(path)


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simulate a single game with the play-balance engine")
    parser.add_argument("home", help="Home team ID (matches roster and lineup files)")
    parser.add_argument("away", help="Away team ID")
    parser.add_argument(
        "--home-lineup",
        type=Path,
        help="CSV file defining the nine-man batting order for the home team",
    )
    parser.add_argument(
        "--away-lineup",
        type=Path,
        help="CSV file defining the nine-man batting order for the away team",
    )
    parser.add_argument(
        "--home-starter",
        help="Player ID of the starting pitcher for the home team",
    )
    parser.add_argument(
        "--away-starter",
        help="Player ID of the starting pitcher for the away team",
    )
    parser.add_argument(
        "--players-file",
        default="data/players.csv",
        help="CSV containing player definitions (default: data/players.csv)",
    )
    parser.add_argument(
        "--roster-dir",
        default="data/rosters",
        help="Directory containing team roster CSV files (default: data/rosters)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Optional random seed for reproducible simulations",
    )
    parser.add_argument(
        "--engine",
        choices=["legacy", "physics"],
        help="Simulation engine override (default: PB_GAME_ENGINE or legacy)",
    )
    parser.add_argument(
        "--html-output",
        type=Path,
        help="Optional path to save the rendered ESPN-style box score HTML",
    )
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)

    home_lineup = _maybe_read_lineup(args.home_lineup)
    away_lineup = _maybe_read_lineup(args.away_lineup)

    home_state, away_state, box, html, _ = run_single_game(
        args.home,
        args.away,
        home_lineup=home_lineup,
        away_lineup=away_lineup,
        home_starter=args.home_starter,
        away_starter=args.away_starter,
        players_file=args.players_file,
        roster_dir=args.roster_dir,
        seed=args.seed,
        engine=args.engine,
    )

    if args.html_output:
        args.html_output.parent.mkdir(parents=True, exist_ok=True)
        args.html_output.write_text(html, encoding="utf-8")
        html_path = str(args.html_output)
    else:
        html_path = save_boxscore_html("exhibition", html)

    home_team_name = home_state.team.name if home_state.team else args.home
    away_team_name = away_state.team.name if away_state.team else args.away
    home_score = box["home"]["score"]
    away_score = box["away"]["score"]

    print(f"Final: {away_team_name} {away_score}, {home_team_name} {home_score}")
    print(f"Box score saved to: {html_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
