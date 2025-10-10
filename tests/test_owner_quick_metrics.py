from __future__ import annotations

import json
from types import SimpleNamespace

from ui.analytics.quick_metrics import gather_owner_quick_metrics


def test_gather_owner_quick_metrics_handles_missing(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "standings.json").write_text(json.dumps({}), encoding="utf-8")
    (data_dir / "schedule.csv").write_text(
        "date,home,away,result,played\n", encoding="utf-8"
    )

    roster = SimpleNamespace(dl=[], ir=[], act=[])
    players: dict[str, object] = {}

    metrics = gather_owner_quick_metrics(
        "TST", base_path=tmp_path, roster=roster, players=players
    )

    assert metrics["record"] == "--"
    assert metrics["bullpen"]["total"] == 0
    assert metrics["matchup"]["opponent"] == "--"
