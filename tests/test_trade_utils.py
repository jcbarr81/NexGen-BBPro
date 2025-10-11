import tempfile
import random
from datetime import timedelta

import pytest

from models.trade import Trade
from utils.trade_utils import get_pending_trades, load_trades, save_trade
from playbalance.season_manager import TRADE_DEADLINE

# Reseed RNG so earlier tests that modify random state don't influence later ones
random.seed()


def test_save_trade_updates_existing(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "utils.trade_utils._today", lambda: TRADE_DEADLINE - timedelta(days=1)
    )
    path = tmp_path / "trades.csv"
    t = Trade("1", "A", "B", ["p1"], ["p2"])
    save_trade(t, str(path))
    trades = load_trades(str(path))
    assert len(trades) == 1
    assert trades[0].status == "pending"

    t.status = "accepted"
    save_trade(t, str(path))
    trades = load_trades(str(path))
    assert len(trades) == 1
    assert trades[0].status == "accepted"


def test_get_pending_trades(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "utils.trade_utils._today", lambda: TRADE_DEADLINE - timedelta(days=1)
    )
    path = tmp_path / "trades.csv"
    save_trade(Trade("1", "A", "B", ["p1"], ["p2"]), str(path))
    save_trade(Trade("2", "C", "A", ["p3"], ["p4"]), str(path))
    save_trade(Trade("3", "D", "A", ["p5"], ["p6"], status="accepted"), str(path))
    pending = get_pending_trades("A", str(path))
    assert len(pending) == 1
    assert pending[0].trade_id == "2"


def test_trade_blocked_after_deadline(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "utils.trade_utils._today", lambda: TRADE_DEADLINE + timedelta(days=1)
    )
    path = tmp_path / "trades.csv"
    t = Trade("1", "A", "B", ["p1"], ["p2"])
    with pytest.raises(RuntimeError):
        save_trade(t, str(path))
