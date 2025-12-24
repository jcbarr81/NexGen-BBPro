from __future__ import annotations

from typing import Dict, Any

from .engine import GameResult


def _aggregate_pitch_log(
    pitch_log: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, int]], dict[str, dict[str, int]]]:
    batter_stats: dict[str, dict[str, int]] = {}
    pitcher_stats: dict[str, dict[str, int]] = {}

    def batter_entry(player_id: str) -> dict[str, int]:
        return batter_stats.setdefault(
            player_id,
            {
                "pitches": 0,
                "so_looking": 0,
                "so_swinging": 0,
                "gb": 0,
                "ld": 0,
                "fb": 0,
            },
        )

    def pitcher_entry(player_id: str) -> dict[str, int]:
        return pitcher_stats.setdefault(
            player_id,
            {
                "balls": 0,
                "strikes": 0,
                "first_pitch_strikes": 0,
                "zone_pitches": 0,
                "o_zone_pitches": 0,
                "zone_swings": 0,
                "o_zone_swings": 0,
                "zone_contacts": 0,
                "o_zone_contacts": 0,
                "gb": 0,
                "ld": 0,
                "fb": 0,
                "so_looking": 0,
                "so_swinging": 0,
            },
        )

    for entry in pitch_log:
        if entry.get("pitch_type") is None:
            continue
        batter_id = entry.get("batter_id")
        pitcher_id = entry.get("pitcher_id")
        if not batter_id or not pitcher_id:
            continue
        batter = batter_entry(str(batter_id))
        pitcher = pitcher_entry(str(pitcher_id))
        batter["pitches"] += 1

        outcome = entry.get("outcome")
        is_strike = outcome in {
            "strike",
            "swinging_strike",
            "foul",
            "in_play",
            "interference",
        }
        is_ball = outcome in {"ball", "hbp"}
        if is_strike:
            pitcher["strikes"] += 1
        elif is_ball:
            pitcher["balls"] += 1

        if entry.get("count") == "0-0" and is_strike:
            pitcher["first_pitch_strikes"] += 1

        in_zone = entry.get("in_zone")
        if in_zone is not None:
            if in_zone:
                pitcher["zone_pitches"] += 1
            else:
                pitcher["o_zone_pitches"] += 1
            if entry.get("swing"):
                if in_zone:
                    pitcher["zone_swings"] += 1
                else:
                    pitcher["o_zone_swings"] += 1
                if entry.get("contact"):
                    if in_zone:
                        pitcher["zone_contacts"] += 1
                    else:
                        pitcher["o_zone_contacts"] += 1

        if entry.get("strikeout"):
            strike_type = entry.get("strikeout_type")
            if strike_type == "called":
                batter["so_looking"] += 1
                pitcher["so_looking"] += 1
            elif strike_type == "swinging":
                batter["so_swinging"] += 1
                pitcher["so_swinging"] += 1

        if entry.get("outcome") == "in_play":
            ball_type = entry.get("ball_type")
            if ball_type in {"gb", "ld", "fb"}:
                batter[ball_type] += 1
                pitcher[ball_type] += 1

    return batter_stats, pitcher_stats


def _merge_line_stats(
    lines: list[dict[str, Any]],
    extras: dict[str, dict[str, int]],
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for line in lines:
        player_id = line.get("player_id")
        updates = extras.get(str(player_id)) if player_id is not None else None
        if updates:
            for key, value in updates.items():
                line.setdefault(key, value)
        merged.append(line)
    return merged


def _enrich_metadata(result: GameResult) -> dict[str, Any]:
    metadata = dict(result.metadata or {})
    batting_lines = metadata.get("batting_lines", {}) or {}
    pitcher_lines = metadata.get("pitcher_lines", {}) or {}
    fielding_lines = metadata.get("fielding_lines", {}) or {}
    batter_stats, pitcher_stats = _aggregate_pitch_log(result.pitch_log)

    enriched_batting: dict[str, list[dict[str, Any]]] = {}
    for side, lines in batting_lines.items():
        if isinstance(lines, list):
            enriched_batting[side] = _merge_line_stats(lines, batter_stats)
        else:
            enriched_batting[side] = lines
    enriched_pitching: dict[str, list[dict[str, Any]]] = {}
    for side, lines in pitcher_lines.items():
        if isinstance(lines, list):
            enriched_pitching[side] = _merge_line_stats(lines, pitcher_stats)
        else:
            enriched_pitching[side] = lines

    metadata["batting_lines"] = enriched_batting
    metadata["pitcher_lines"] = enriched_pitching
    metadata["fielding_lines"] = fielding_lines
    return metadata


def _error_counts_by_side(
    pitch_log: list[dict[str, Any]],
    pitcher_lines: dict[str, list[dict[str, Any]]],
) -> dict[str, dict[str, int]]:
    pitcher_to_side: dict[str, str] = {}
    for side, lines in pitcher_lines.items():
        for line in lines:
            player_id = line.get("player_id")
            if player_id:
                pitcher_to_side[str(player_id)] = side
    counts = {
        "away": {"errors": 0, "fielding_errors": 0, "throwing_errors": 0},
        "home": {"errors": 0, "fielding_errors": 0, "throwing_errors": 0},
    }
    for entry in pitch_log:
        if not entry.get("reached_on_error"):
            continue
        pitcher_id = entry.get("pitcher_id")
        side = pitcher_to_side.get(str(pitcher_id))
        if side not in counts:
            continue
        counts[side]["errors"] += 1
        err_type = entry.get("error_type")
        if err_type == "throwing":
            counts[side]["throwing_errors"] += 1
        elif err_type == "fielding":
            counts[side]["fielding_errors"] += 1
    return counts


def _build_boxscore(
    *, pitch_log: list[dict[str, Any]], metadata: dict[str, Any]
) -> Dict[str, Any]:
    batting_lines = metadata.get("batting_lines", {}) or {}
    pitcher_lines = metadata.get("pitcher_lines", {}) or {}
    fielding_lines = metadata.get("fielding_lines", {}) or {}
    score = metadata.get("score", {}) or {}
    inning_runs = metadata.get("inning_runs", {}) or {}

    def team_section(side: str) -> Dict[str, Any]:
        batting = []
        for line in batting_lines.get(side, []):
            batting.append(
                {
                    "player_id": line.get("player_id"),
                    "g": line.get("g", 0),
                    "gs": line.get("gs", 0),
                    "pa": line.get("pa", 0),
                    "ab": line.get("ab", 0),
                    "r": line.get("r", 0),
                    "h": line.get("h", 0),
                    "1b": line.get("b1", 0),
                    "2b": line.get("b2", 0),
                    "3b": line.get("b3", 0),
                    "hr": line.get("hr", 0),
                    "rbi": line.get("rbi", 0),
                    "bb": line.get("bb", 0),
                    "ibb": line.get("ibb", 0),
                    "hbp": line.get("hbp", 0),
                    "so": line.get("so", 0),
                    "so_looking": line.get("so_looking", 0),
                    "so_swinging": line.get("so_swinging", 0),
                    "sh": line.get("sh", 0),
                    "sf": line.get("sf", 0),
                    "roe": line.get("roe", 0),
                    "fc": line.get("fc", 0),
                    "ci": line.get("ci", 0),
                    "gidp": line.get("gidp", 0),
                    "sb": line.get("sb", 0),
                    "cs": line.get("cs", 0),
                    "po": line.get("po", 0),
                    "pocs": line.get("pocs", 0),
                    "pitches": line.get("pitches", 0),
                    "lob": line.get("lob", 0),
                    "gb": line.get("gb", 0),
                    "ld": line.get("ld", 0),
                    "fb": line.get("fb", 0),
                }
            )
        pitching = []
        for line in pitcher_lines.get(side, []):
            pitching.append(
                {
                    "player_id": line.get("player_id"),
                    "g": line.get("g", 0),
                    "gs": line.get("gs", 0),
                    "w": line.get("w", 0),
                    "l": line.get("l", 0),
                    "gf": line.get("gf", 0),
                    "sv": line.get("sv", 0),
                    "svo": line.get("svo", 0),
                    "hld": line.get("hld", 0),
                    "bs": line.get("bs", 0),
                    "ir": line.get("ir", 0),
                    "irs": line.get("irs", 0),
                    "bf": line.get("bf", line.get("batters_faced", 0)),
                    "outs": line.get("outs", 0),
                    "r": line.get("runs", 0),
                    "er": line.get("earned_runs", line.get("runs", 0)),
                    "h": line.get("hits", 0),
                    "1b": line.get("b1", 0),
                    "2b": line.get("b2", 0),
                    "3b": line.get("b3", 0),
                    "hr": line.get("home_runs", 0),
                    "bb": line.get("walks", 0),
                    "ibb": line.get("ibb", 0),
                    "so": line.get("strikeouts", 0),
                    "so_looking": line.get("so_looking", 0),
                    "so_swinging": line.get("so_swinging", 0),
                    "hbp": line.get("hbp", 0),
                    "wp": line.get("wp", 0),
                    "bk": line.get("bk", 0),
                    "pk": line.get("pk", 0),
                    "pocs": line.get("pocs", 0),
                    "pitches": line.get("pitches", 0),
                    "balls": line.get("balls", 0),
                    "strikes": line.get("strikes", 0),
                    "first_pitch_strikes": line.get("first_pitch_strikes", 0),
                    "zone_pitches": line.get("zone_pitches", 0),
                    "o_zone_pitches": line.get("o_zone_pitches", 0),
                    "zone_swings": line.get("zone_swings", 0),
                    "o_zone_swings": line.get("o_zone_swings", 0),
                    "zone_contacts": line.get("zone_contacts", 0),
                    "o_zone_contacts": line.get("o_zone_contacts", 0),
                    "gb": line.get("gb", 0),
                    "ld": line.get("ld", 0),
                    "fb": line.get("fb", 0),
                }
            )
        fielding = []
        for line in fielding_lines.get(side, []):
            fielding.append(
                {
                    "player_id": line.get("player_id"),
                    "g": line.get("g", 0),
                    "gs": line.get("gs", 0),
                    "po": line.get("po", 0),
                    "a": line.get("a", 0),
                    "e": line.get("e", 0),
                    "dp": line.get("dp", 0),
                    "tp": line.get("tp", 0),
                    "pk": line.get("pk", 0),
                    "pb": line.get("pb", 0),
                    "ci": line.get("ci", 0),
                    "cs": line.get("cs", 0),
                    "sba": line.get("sba", 0),
                }
            )
        return {
            "score": score.get(side, 0),
            "batting": batting,
            "pitching": pitching,
            "fielding": fielding,
            "inning_runs": inning_runs.get(side, []),
        }

    return {"home": team_section("home"), "away": team_section("away")}


def serialize_game_result(result: GameResult) -> Dict[str, Any]:
    """Return a dict compatible with the existing game stats writer."""

    totals = dict(result.totals)
    errors = {
        "errors": totals.get("e", 0),
        "fielding_errors": totals.get("e_field", 0),
        "throwing_errors": totals.get("e_throw", 0),
        "gidp": totals.get("gidp", 0),
        "fielder_choice": totals.get("fc", 0),
    }
    metadata = _enrich_metadata(result)
    return {
        "totals": totals,
        "errors": errors,
        "pitch_log": result.pitch_log,
        "boxscore": _build_boxscore(pitch_log=result.pitch_log, metadata=metadata),
        "metadata": metadata,
    }
