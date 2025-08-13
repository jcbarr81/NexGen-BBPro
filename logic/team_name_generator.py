"""Utilities for generating random baseball team names.

This module exposes lists of plausible cities and mascots along with a
helper :func:`random_team` which returns a randomly selected
``(city, mascot)`` pair. The lists are intentionally short but can be
extended as needed and are primarily meant for demo data and quick UI
entry.
"""

import random
from typing import List, Set, Tuple

# Lists of sample cities and mascots.
CITIES: List[str] = [
    "New York",
    "Los Angeles",
    "Chicago",
    "Houston",
    "Phoenix",
    "Philadelphia",
    "San Antonio",
    "San Diego",
    "Dallas",
    "San Jose",
    "Austin",
    "Jacksonville",
    "Fort Worth",
    "Columbus",
    "Charlotte",
    "San Francisco",
    "Indianapolis",
    "Seattle",
    "Denver",
    "Washington",
    "Boston",
    "El Paso",
    "Nashville",
    "Detroit",
    "Oklahoma City",
    "Portland",
    "Las Vegas",
    "Memphis",
    "Louisville",
    "Baltimore",
    "Milwaukee",
    "Albuquerque",
]

MASCOTS: List[str] = [
    "Bears",
    "Tigers",
    "Eagles",
    "Sharks",
    "Dragons",
    "Wolves",
    "Lions",
    "Hawks",
    "Rockets",
    "Pirates",
    "Knights",
    "Warriors",
    "Panthers",
    "Bulls",
    "Kings",
    "Giants",
    "Falcons",
    "Rangers",
    "Thunder",
    "Saints",
    "Wildcats",
    "Spartans",
    "Hornets",
    "Raiders",
    "Royals",
    "Dolphins",
    "Chargers",
    "Coyotes",
    "Jets",
    "Mariners",
    "Chiefs",
    "Cardinals",
]

# Track used names to ensure uniqueness during generation.
_used_cities: Set[str] = set()
_used_mascots: Set[str] = set()


def random_team() -> Tuple[str, str]:
    """Return a random `(city, mascot)` pair without repeats.

    Cities and mascots are removed from the available pool after use. A
    :class:`RuntimeError` is raised if no unused names remain.
    """

    available_cities = [c for c in CITIES if c not in _used_cities]
    if not available_cities:
        raise RuntimeError("No unused city names remain.")

    available_mascots = [m for m in MASCOTS if m not in _used_mascots]
    if not available_mascots:
        raise RuntimeError("No unused mascot names remain.")

    city = random.choice(available_cities)
    mascot = random.choice(available_mascots)

    _used_cities.add(city)
    _used_mascots.add(mascot)

    return city, mascot


def reset_name_pool() -> None:
    """Clear tracking of used cities and mascots."""

    _used_cities.clear()
    _used_mascots.clear()
