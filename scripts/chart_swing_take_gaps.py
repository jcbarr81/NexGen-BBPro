#!/usr/bin/env python3

"""Compare Statcast and sim swing/take rates by count and chart gaps."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

SIM_PATH = Path("docs/notes/batter_decisions/batter_decisions_stochastic.csv")
MLB_PATH = Path("data/MLB_avg/statcast_counts_2023.csv")
OUTPUT_DIR = Path("docs/notes/batter_decisions")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

sim_df = pd.read_csv(SIM_PATH)
mlb_df = pd.read_csv(MLB_PATH)
merged = (
    sim_df.merge(mlb_df, on=["balls", "strikes"], suffixes=("_sim", "_mlb"))
    .sort_values(["balls", "strikes"])
)

for metric in ["take_rate", "swing_rate", "ball_rate", "called_strike_rate"]:
    merged[f"{metric}_diff"] = merged[f"{metric}_sim"] - merged[f"{metric}_mlb"]

merged.to_csv(OUTPUT_DIR / "batter_decision_gap_analysis.csv", index=False)

counts = merged[["balls", "strikes"]].apply(lambda row: f"{int(row.balls)}-{int(row.strikes)}", axis=1)
x = range(len(counts))

plt.style.use("seaborn-v0_8")
fig, axes = plt.subplots(2, 2, figsize=(14, 10), sharex=True)
metric_titles = [
    ("take_rate", "Take Rate"),
    ("swing_rate", "Swing Rate"),
    ("ball_rate", "Ball Call Rate"),
    ("called_strike_rate", "Called Strike Rate"),
]

for ax, (metric, title) in zip(axes.flatten(), metric_titles):
    ax.plot(x, merged[f"{metric}_mlb"], marker="o", label="MLB (Statcast)")
    ax.plot(x, merged[f"{metric}_sim"], marker="o", label="Sim")
    ax.set_title(title)
    ax.set_ylabel("Rate")
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.set_xticks(x)
    ax.set_xticklabels(counts, rotation=45)

axes[0, 0].legend(loc="best")
fig.tight_layout()
fig.suptitle(
    "MLB vs Sim Swing/Take Rates by Count (2023 Statcast vs Baseline Sim)",
    fontsize=16,
    y=1.02,
)
fig.savefig(OUTPUT_DIR / "batter_decision_rate_comparison.png", dpi=300, bbox_inches="tight")
plt.close(fig)

fig, ax = plt.subplots(figsize=(14, 4))
ax.bar(x, merged["take_rate_diff"], color="tab:orange")
ax.axhline(0.0, color="black", linewidth=1)
ax.set_xticks(x)
ax.set_xticklabels(counts, rotation=45)
ax.set_ylabel("Sim - MLB")
ax.set_title("Take Rate Gap (Sim minus MLB)")
ax.grid(True, axis="y", linestyle="--", alpha=0.4)
fig.savefig(OUTPUT_DIR / "batter_decision_take_gap.png", dpi=300, bbox_inches="tight")
plt.close(fig)

print("Wrote gap analysis to", OUTPUT_DIR)
