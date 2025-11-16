import pandas as pd
from pybaseball import cache, statcast

YEAR = 2024
start_date = f"{YEAR}-03-01"
end_date = f"{YEAR}-11-30"
OUTPUT_CSV = f"league_foul_rate_by_count_{YEAR}.csv"

def main():
    cache.enable()
    print(f"Downloading Statcast data for {YEAR}...")
    df = statcast(start_dt=start_date, end_dt=end_date)
    print(f"Loaded {len(df):,} pitches.")
    df["count"] = df["balls"].astype(str) + "-" + df["strikes"].astype(str)
    foul_labels = {"foul", "foul_tip", "foul_bunt"}
    df["is_foul"] = df["description"].isin(foul_labels)
    grouped = df.groupby("count").agg(
        pitches=("pitch_type", "size"),
        fouls=("is_foul", "sum"),
    ).reset_index()
    grouped["foul_pct"] = grouped["fouls"] / grouped["pitches"]
    grouped = grouped.sort_values(
        by=["count"],
        key=lambda s: s.str.extract(r"(\d)-(\d)").astype(int).mul([10, 1]).sum(axis=1),
    )
    grouped.to_csv(OUTPUT_CSV, index=False)
    print(f"\nSaved to: {OUTPUT_CSV}\n")
    print("Foul% by count:")
    print(grouped)

if __name__ == "__main__":
    main()
