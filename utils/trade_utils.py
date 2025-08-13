import csv
from models.trade import Trade

def load_trades(file_path="data/trades_pending.csv"):
    trades = []
    try:
        with open(file_path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                trade = Trade(
                    trade_id=row["trade_id"],
                    from_team=row["from_team"],
                    to_team=row["to_team"],
                    give_player_ids=row["give_player_ids"].split("|"),
                    receive_player_ids=row["receive_player_ids"].split("|"),
                    status=row["status"]
                )
                trades.append(trade)
    except FileNotFoundError:
        pass
    return trades

def save_trade(trade: Trade, file_path="data/trades_pending.csv"):
    existing = load_trades(file_path)
    existing.append(trade)
    with open(file_path, "w", newline="") as f:
        fieldnames = ["trade_id", "from_team", "to_team", "give_player_ids", "receive_player_ids", "status"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for t in existing:
            writer.writerow({
                "trade_id": t.trade_id,
                "from_team": t.from_team,
                "to_team": t.to_team,
                "give_player_ids": "|".join(t.give_player_ids),
                "receive_player_ids": "|".join(t.receive_player_ids),
                "status": t.status
            })
