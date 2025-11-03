#!/usr/bin/env python3
"""Download MLB Statcast pitch-level data and aggregate swing/take rates by count."""

from __future__ import annotations

import argparse
import calendar
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from pybaseball import statcast


# Description buckets adopted from Savant glossary.
SWING_EVENTS = {
    "swinging_strike",
    "swinging_strike_blocked",
    "foul",
    "foul_tip",
    "foul_bunt",
    "missed_bunt",
    "hit_into_play",
    "hit_into_play_no_out",
    "hit_into_play_score",
    "hit_into_play_no_out_r",
    "hit_into_play_score_run",
    "hit_into_play_score_out",
}

TAKE_EVENTS = {
    "ball",
    "blocked_ball",
    "called_strike",
    "hit_by_pitch",
}

FOUL_EVENTS = {
    "foul",
    "foul_tip",
    "foul_bunt",
    "foul_pitchout",
    "foul_blocked",
}

BALL_IN_PLAY_EVENTS = {
    "hit_into_play",
    "hit_into_play_score",
    "hit_into_play_no_out",
    "hit_into_play_score_run",
    "hit_into_play_no_out_r",
    "hit_into_play_score_out",
}

HIT_EVENTS = {"single", "double", "triple", "home_run"}
WALK_EVENTS = {"walk", "intent_walk"}
STRIKEOUT_EVENTS = {"strikeout", "strikeout_double_play"}


def month_date_range(year: int, month: int) -> tuple[date, date]:
    """Return first and last date for a given month."""

    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def fetch_statcast_range(start: date, end: date) -> pd.DataFrame:
    """Fetch statcast data for the inclusive date range."""

    return statcast(
        start_dt=start.isoformat(),
        end_dt=end.isoformat(),
    )


def collect_season(year: int) -> pd.DataFrame:
    """Collect regular-season statcast data for a given year month by month."""

    frames: list[pd.DataFrame] = []
    for month in range(3, 11):  # MLB regular season (Mar/Apr through Sep/Oct)
        start, end = month_date_range(year, month)
        print(f"Fetching {start} -> {end}")
        df = fetch_statcast_range(start, end)
        if not df.empty:
            frames.append(df)
    if not frames:
        raise RuntimeError(f"No data retrieved for season {year}")
    all_df = pd.concat(frames, ignore_index=True)
    # Keep only regular-season pitches
    regular = all_df[all_df["game_type"] == "R"].copy()
    if regular.empty:
        raise RuntimeError(f"No regular-season data found for season {year}")
    return regular


def enrich_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Add swing/take and zone flags needed for aggregation."""

    # Ensure we only consider actual pitches
    df = df[df["pitch_type"].notna()].copy()

    desc = df["description"].fillna("")
    events = df["events"].fillna("")

    df["is_swing"] = desc.isin(SWING_EVENTS)
    df["is_take"] = desc.isin(TAKE_EVENTS)
    df["is_foul"] = desc.isin(FOUL_EVENTS)
    df["is_ball_in_play"] = desc.isin(BALL_IN_PLAY_EVENTS)
    df["is_hit"] = events.isin(HIT_EVENTS)
    df["is_walk"] = events.isin(WALK_EVENTS)
    df["is_strikeout_event"] = events.isin(STRIKEOUT_EVENTS)
    df["is_ball_call"] = desc.isin({"ball", "blocked_ball"})
    df["is_called_strike"] = desc.eq("called_strike")
    df["is_hbp"] = desc.eq("hit_by_pitch")

    # Zone classification: Statcast zone 1-9 is in-zone; 11-14 triangles; others out.
    df["is_zone_pitch"] = df["zone"].between(1, 9)
    df["is_outside_pitch"] = ~df["is_zone_pitch"]

    df["is_zone_swing"] = df["is_swing"] & df["is_zone_pitch"]
    df["is_chase_swing"] = df["is_swing"] & df["is_outside_pitch"]

    return df


def aggregate_by_count(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate metrics by balls/strikes count."""

    grouped = (
        df.groupby(["balls", "strikes"], dropna=False)
        .agg(
            pitches=("pitch_type", "size"),
            swings=("is_swing", "sum"),
            takes=("is_take", "sum"),
            zone_pitches=("is_zone_pitch", "sum"),
            outside_pitches=("is_outside_pitch", "sum"),
            zone_swings=("is_zone_swing", "sum"),
            chase_swings=("is_chase_swing", "sum"),
            ball_calls=("is_ball_call", "sum"),
            called_strike_calls=("is_called_strike", "sum"),
            fouls=("is_foul", "sum"),
            ball_in_play=("is_ball_in_play", "sum"),
            hits=("is_hit", "sum"),
            walks=("is_walk", "sum"),
            strikeouts=("is_strikeout_event", "sum"),
            hbp=("is_hbp", "sum"),
        )
        .reset_index()
    )

    grouped["take_rate"] = grouped["takes"] / grouped["pitches"]
    grouped["swing_rate"] = grouped["swings"] / grouped["pitches"]
    grouped["foul_rate"] = grouped["fouls"] / grouped["pitches"]
    grouped["ball_rate"] = grouped["ball_calls"] / grouped["pitches"]
    grouped["called_strike_rate"] = grouped["called_strike_calls"] / grouped["pitches"]
    grouped["zone_rate"] = grouped["zone_pitches"] / grouped["pitches"]
    grouped["chase_rate"] = grouped["chase_swings"] / grouped["outside_pitches"].clip(lower=1)
    grouped["zone_swing_rate"] = grouped["zone_swings"] / grouped["zone_pitches"].clip(lower=1)

    grouped.sort_values(["balls", "strikes"], inplace=True)
    return grouped


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download MLB Statcast and aggregate swing/take metrics by count."
    )
    parser.add_argument("--season", type=int, default=2023, help="Season year (e.g., 2023)")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/MLB_avg"),
        help="Directory to store the aggregated CSV",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir: Path = args.output
    output_dir.mkdir(parents=True, exist_ok=True)
    season = args.season

    df = collect_season(season)
    df = enrich_flags(df)
    grouped = aggregate_by_count(df)

    output_path = output_dir / f"statcast_counts_{season}.csv"
    grouped.to_csv(output_path, index=False)
    print(f"Wrote aggregated data to {output_path}")


if __name__ == "__main__":
    main()
