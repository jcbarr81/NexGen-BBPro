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

__all__ = ["generate_schedule", "save_schedule"]


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
