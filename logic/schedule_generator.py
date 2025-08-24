from __future__ import annotations

"""Utilities for generating season schedules.

This module produces a basic full-season schedule for a league.  The
current implementation generates a double round-robin schedule where each
team plays every other team twice: once at home and once away.  Games are
scheduled on consecutive days starting from a provided start date.

The function returns a list of dictionaries with ``date`` (ISO formatted
string), ``home`` team and ``away`` team keys.  The simple data structure
is easy for callers or tests to consume and can be written to disk using
:func:`save_schedule` if desired.

The algorithm supports both even and odd numbers of teams.  For an odd
number of teams a bye is automatically inserted each round and games
involving the bye are skipped.
"""

from datetime import date, timedelta
from pathlib import Path
from typing import Iterable, List, Dict
import csv

__all__ = ["generate_schedule", "generate_mlb_schedule", "save_schedule"]


def _round_robin_pairs(teams: List[str]) -> List[List[tuple[str, str]]]:
    """Return pairings for a single round-robin tournament.

    The returned value is a list of rounds, each round being a list of
    ``(home, away)`` tuples.  Home teams alternate in a simple pattern to
    avoid the same team always being home or away.  If the number of teams
    is odd, a ``None`` placeholder is added internally and any games
    involving ``None`` are skipped by callers.
    """

    teams = list(teams)
    if not teams:
        return []

    # For odd counts insert a bye placeholder.
    bye = None
    if len(teams) % 2 == 1:
        teams.append(bye)
    n = len(teams)
    rounds: List[List[tuple[str, str]]] = []

    for i in range(n - 1):
        round_games: List[tuple[str, str]] = []
        for j in range(n // 2):
            t1 = teams[j]
            t2 = teams[n - 1 - j]
            if t1 is bye or t2 is bye:
                continue
            # Alternate home/away to spread home games.
            if j % 2 == i % 2:
                round_games.append((t1, t2))
            else:
                round_games.append((t2, t1))
        rounds.append(round_games)
        # Rotate teams (fixed first team).
        teams = [teams[0]] + teams[-1:] + teams[1:-1]
    return rounds


def generate_schedule(teams: Iterable[str], start_date: date) -> List[Dict[str, str]]:
    """Generate a double round-robin schedule.

    Parameters
    ----------
    teams:
        Iterable of team identifiers/names.
    start_date:
        Date of the first day of the schedule.

    Returns
    -------
    list of dict
        Each dictionary contains ``date`` (ISO formatted string), ``home``
        team and ``away`` team keys.
    """

    teams_list = list(teams)
    rounds = _round_robin_pairs(teams_list)
    schedule: List[Dict[str, str]] = []
    current = start_date

    # First half of the season
    for round_games in rounds:
        for home, away in round_games:
            schedule.append({
                "date": current.isoformat(),
                "home": home,
                "away": away,
            })
        current += timedelta(days=1)

    # Mid-season break for the All-Star exhibition
    # ``current`` has already been advanced by one day after the last round
    # above so we add six additional days to produce roughly a one week pause
    # in the schedule.
    current += timedelta(days=6)

    # Second half with reversed home/away
    for round_games in rounds:
        for home, away in round_games:
            schedule.append({
                "date": current.isoformat(),
                "home": away,
                "away": home,
            })
        current += timedelta(days=1)

    return schedule


def generate_mlb_schedule(
    teams: Iterable[str], start_date: date, games_per_team: int = 162
) -> List[Dict[str, str]]:
    """Generate a full 162-game schedule for each team.

    The algorithm builds upon :func:`generate_schedule` which creates a single
    double round-robin cycle with an All-Star break.  That base cycle is
    repeated as many times as necessary and truncated so that every club plays
    exactly *games_per_team* contests (81 home and 81 away when using the
    default).

    Parameters
    ----------
    teams:
        Iterable of team identifiers/names.
    start_date:
        Date of the first day of the schedule.
    games_per_team:
        Total number of games each team should play.  Defaults to ``162`` to
        mirror the length of a Major League Baseball season.

    Returns
    -------
    list of dict
        Each dictionary contains ``date`` (ISO formatted string), ``home`` team
        and ``away`` team keys representing a single game.
    """

    teams_list = list(teams)
    if not teams_list:
        return []

    base_cycle = generate_schedule(teams_list, start_date)
    first = date.fromisoformat(base_cycle[0]["date"])
    last = date.fromisoformat(base_cycle[-1]["date"])
    cycle_span = (last - first).days + 1
    games_per_cycle_per_team = 2 * (len(teams_list) - 1)

    full_cycles, remainder = divmod(games_per_team, games_per_cycle_per_team)

    schedule: List[Dict[str, str]] = []
    offset = 0

    # Add complete cycles
    for _ in range(full_cycles):
        for game in base_cycle:
            adjusted_date = (
                date.fromisoformat(game["date"]) + timedelta(days=offset)
            ).isoformat()
            schedule.append(
                {"date": adjusted_date, "home": game["home"], "away": game["away"]}
            )
        offset += cycle_span

    if remainder:
        extra_counts = {t: 0 for t in teams_list}
        for game in base_cycle:
            home = game["home"]
            away = game["away"]
            if extra_counts[home] >= remainder or extra_counts[away] >= remainder:
                continue
            adjusted_date = (
                date.fromisoformat(game["date"]) + timedelta(days=offset)
            ).isoformat()
            schedule.append({"date": adjusted_date, "home": home, "away": away})
            extra_counts[home] += 1
            extra_counts[away] += 1
            if all(c >= remainder for c in extra_counts.values()):
                break

    return schedule


def save_schedule(schedule: Iterable[Dict[str, str]], path: str | Path) -> None:
    """Save a generated schedule to a CSV file.

    Parameters
    ----------
    schedule:
        Iterable of dictionaries as produced by :func:`generate_schedule`.
    path:
        Destination path for the CSV file.  Parent directories are created
        automatically.
    """

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "home", "away"])
        for game in schedule:
            writer.writerow([game["date"], game["home"], game["away"]])
