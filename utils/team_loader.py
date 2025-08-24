import csv
import os
import re
from pathlib import Path
from models.team import Team
from utils.path_utils import get_base_dir
from utils.stats_persistence import load_stats


def _resolve_path(file_path: str | Path) -> Path:
    """Return an absolute :class:`Path` for ``file_path`` relative to the project root."""

    path = Path(file_path)
    if path.is_absolute():
        return path
    return get_base_dir() / path


def load_teams(file_path: str | Path = "data/teams.csv"):
    file_path = _resolve_path(file_path)
    teams = []
    with file_path.open(mode="r", newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            team = Team(
                team_id=row["team_id"],
                name=row["name"],
                city=row["city"],
                abbreviation=row["abbreviation"],
                division=row["division"],
                stadium=row["stadium"],
                primary_color=row["primary_color"],
                secondary_color=row["secondary_color"],
                owner_id=row["owner_id"],
            )
            teams.append(team)
    stats = load_stats()
    for team in teams:
        season = stats["teams"].get(team.team_id)
        if season:
            team.season_stats = season
    return teams


def save_team_settings(team: Team, file_path: str | Path = "data/teams.csv") -> None:
    """Persist updates to a single team's stadium or colors.

    Reads the entire teams file, updates the matching team's fields and
    overwrites the CSV. Only the ``stadium`` and color fields are modified so
    other information remains unchanged.
    """

    def _sanitize_color(value: str, field: str) -> str:
        """Return a normalized hex color or raise ``ValueError``.

        The function ensures the color string begins with ``#`` and matches the
        ``#RRGGBB`` or ``#RGB`` formats. If the value cannot be normalized into a
        valid hex color a descriptive ``ValueError`` is raised.
        """

        value = value.strip()
        if not value.startswith("#"):
            value = f"#{value}"
        if re.fullmatch(r"#(?:[0-9a-fA-F]{3}){1,2}$", value):
            return value.upper()
        raise ValueError(f"Invalid hex color for {field}: {value}")

    file_path = _resolve_path(file_path)
    teams = []
    with file_path.open(mode="r", newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row["team_id"] == team.team_id:
                row["stadium"] = team.stadium
                row["primary_color"] = _sanitize_color(team.primary_color, "primary_color")
                row["secondary_color"] = _sanitize_color(team.secondary_color, "secondary_color")
            teams.append(row)

    fieldnames = [
        "team_id",
        "name",
        "city",
        "abbreviation",
        "division",
        "stadium",
        "primary_color",
        "secondary_color",
        "owner_id",
    ]
    with file_path.open(mode="w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(teams)

