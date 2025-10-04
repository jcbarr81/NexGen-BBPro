from __future__ import annotations

import argparse
from typing import Iterable

from services.transaction_log import load_transactions


def _parse_actions(value: str | None) -> set[str] | None:
    if not value:
        return None
    parts = [p.strip().lower() for p in value.split(",") if p.strip()]
    return set(parts) or None


def list_transactions(team: str | None, actions: Iterable[str] | None, limit: int | None) -> int:
    rows = load_transactions(team_id=team, actions=actions, limit=limit)
    if not rows:
        print("No transactions found.")
        return 0

    # Column headers consistent with UI order
    headers = [
        "Timestamp",
        "Season",
        "Team",
        "Player",
        "Action",
        "Movement",
        "Counterparty",
        "Details",
    ]

    def row_to_values(row: dict[str, str]) -> list[str]:
        movement = ""
        if row.get("from_level") or row.get("to_level"):
            movement = f"{row.get('from_level', '')} -> {row.get('to_level', '')}"
        return [
            row.get("timestamp", ""),
            row.get("season_date", ""),
            row.get("team_id", ""),
            row.get("player_name", row.get("player_id", "")),
            (row.get("action", "") or "").replace("_", " ").title(),
            movement,
            row.get("counterparty", ""),
            row.get("details", ""),
        ]

    values = [row_to_values(r) for r in rows]
    # Compute simple column widths, capped for Details to avoid very wide output
    widths = [len(h) for h in headers]
    for v in values:
        for i, cell in enumerate(v):
            cell_len = len(str(cell))
            if i == 7:  # Details
                cell_len = min(cell_len, 80)
            widths[i] = max(widths[i], cell_len)

    def fmt_row(cols: list[str]) -> str:
        parts: list[str] = []
        for i, c in enumerate(cols):
            text = str(c)
            if i == 7 and len(text) > 80:
                text = text[:77] + "..."
            parts.append(text.ljust(widths[i]))
        return "  ".join(parts)

    print(fmt_row(headers))
    print("  ".join("-" * w for w in widths))
    for v in values:
        print(fmt_row(v))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="List NexGen-BBPro transactions.")
    parser.add_argument("--team", help="Filter by team ID (e.g., WAS)")
    parser.add_argument(
        "--actions",
        help="Comma-separated list of actions (e.g., draft,cut,trade_in)",
    )
    parser.add_argument("--limit", type=int, help="Max number of rows to show")
    args = parser.parse_args()

    return list_transactions(args.team, _parse_actions(args.actions), args.limit)


if __name__ == "__main__":
    raise SystemExit(main())

