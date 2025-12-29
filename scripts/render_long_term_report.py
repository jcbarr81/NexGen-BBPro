#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PERCENT_KEYS = {
    "k_pct",
    "bb_pct",
    "k_minus_bb_pct",
    "swing_pct",
    "z_swing_pct",
    "o_swing_pct",
    "contact_pct",
    "z_contact_pct",
    "o_contact_pct",
    "first_pitch_strike_pct",
    "zone_pct",
    "pitches_put_in_play_pct",
    "bip_gb_pct",
    "bip_ld_pct",
    "bip_fb_pct",
    "hr_per_fb_pct",
    "sb_pct",
    "bip_double_play_pct",
    "called_third_strike_share_of_so",
}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    seasons: list[dict[str, Any]] = []
    if not path.exists():
        return seasons
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            seasons.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    seasons.sort(key=lambda s: s.get("year", 0))
    return seasons


def _fmt_value(key: str, value: Any, *, percent: bool = False) -> str:
    if value is None:
        return "n/a"
    try:
        val = float(value)
    except (TypeError, ValueError):
        return html.escape(str(value))
    if percent:
        return f"{val * 100:.1f}%"
    if key in {"avg", "obp", "slg", "ops", "iso", "babip"}:
        return f"{val:.3f}"
    if abs(val) >= 100:
        return f"{val:.0f}"
    if abs(val) >= 10:
        return f"{val:.2f}"
    return f"{val:.3f}"


def _fmt_delta(key: str, value: Any, *, percent: bool = False) -> str:
    if value is None:
        return "n/a"
    try:
        val = float(value)
    except (TypeError, ValueError):
        return html.escape(str(value))
    if percent:
        return f"{val * 100:+.1f}%"
    if key in {"avg", "obp", "slg", "ops", "iso", "babip"}:
        return f"{val:+.3f}"
    if abs(val) >= 10:
        return f"{val:+.2f}"
    return f"{val:+.3f}"


def _escape(text: Any) -> str:
    return html.escape("" if text is None else str(text))


def _render_report(seasons: list[dict[str, Any]], output_dir: Path) -> Path:
    metrics_keys = sorted(
        {k for season in seasons for k in (season.get("metrics") or {}).keys()}
    )
    flag_counts = Counter()
    for season in seasons:
        for flag in season.get("flags", []) or []:
            metric = flag.get("metric")
            if metric:
                flag_counts[metric] += 1

    def top_flags(limit: int = 6) -> list[tuple[str, int]]:
        return flag_counts.most_common(limit)

    years = [s.get("year") for s in seasons if s.get("year") is not None]
    year_min = min(years) if years else "n/a"
    year_max = max(years) if years else "n/a"
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")

    flag_list = "".join(
        f"<li><span class=\"badge\">{_escape(k)}</span> {v} seasons</li>"
        for k, v in top_flags()
    ) or "<li>n/a</li>"

    nav_years = "".join(
        f"<a class=\"chip\" href=\"#y{year}\">{year}</a>" for year in years
    )

    season_blocks = []
    for season in seasons:
        year = season.get("year")
        year_id = f"y{year}"
        metrics = season.get("metrics") or {}
        deltas = season.get("mlb_deltas") or {}
        flags = {f.get("metric") for f in season.get("flags", []) or []}
        leaders = season.get("leaders") or {}

        def build_metric_rows(source: dict[str, Any], is_delta: bool) -> str:
            rows = []
            for key in metrics_keys:
                if key not in source:
                    continue
                percent = key in PERCENT_KEYS or key.endswith("_pct")
                value = (
                    _fmt_delta(key, source.get(key), percent=percent)
                    if is_delta
                    else _fmt_value(key, source.get(key), percent=percent)
                )
                classes = "flag" if key in flags else ""
                rows.append(
                    f"<tr class=\"{classes}\"><td>{_escape(key)}</td><td>{value}</td></tr>"
                )
            return "".join(rows)

        def leader_rows(side: str) -> str:
            rows = []
            side_data = leaders.get(side, {}) if isinstance(leaders, dict) else {}
            for stat, entries in (side_data or {}).items():
                vals = []
                for entry in entries:
                    name = _escape(entry.get("name"))
                    team_id = _escape(entry.get("team_id"))
                    value = _fmt_value(stat, entry.get("value"))
                    vals.append(f"{name} ({team_id}) - {value}")
                rows.append(
                    f"<tr><td>{_escape(stat)}</td><td>{'<br>'.join(vals) if vals else 'n/a'}</td></tr>"
                )
            return "".join(rows)

        flagged_text = ", ".join(sorted(flags)) if flags else "none"
        champion = _escape(season.get("champion", "n/a"))
        runner_up = _escape(season.get("runner_up", "n/a"))

        season_blocks.append(
            f"""
<details class="season" id="{year_id}">
  <summary>
    <span class="year">{year}</span>
    <span class="meta">Champion: {champion}</span>
    <span class="meta">Runner-up: {runner_up}</span>
    <span class="meta">Flags: {len(flags)}</span>
  </summary>
  <div class="grid">
    <div class="panel">
      <h3>KPIs</h3>
      <table>
        <thead><tr><th>Metric</th><th>Value</th></tr></thead>
        <tbody>
          {build_metric_rows(metrics, False)}
        </tbody>
      </table>
    </div>
    <div class="panel">
      <h3>MLB Deltas</h3>
      <table>
        <thead><tr><th>Metric</th><th>Delta</th></tr></thead>
        <tbody>
          {build_metric_rows(deltas, True)}
        </tbody>
      </table>
    </div>
  </div>
  <div class="grid">
    <div class="panel">
      <h3>Batting Leaders (Top 3)</h3>
      <table>
        <thead><tr><th>Stat</th><th>Leaders</th></tr></thead>
        <tbody>
          {leader_rows("batting")}
        </tbody>
      </table>
    </div>
    <div class="panel">
      <h3>Pitching Leaders (Top 3)</h3>
      <table>
        <thead><tr><th>Stat</th><th>Leaders</th></tr></thead>
        <tbody>
          {leader_rows("pitching")}
        </tbody>
      </table>
    </div>
  </div>
  <p class="flagline"><strong>Flagged:</strong> {_escape(flagged_text)}</p>
</details>
"""
        )

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Long-Term Sim Report</title>
<style>
:root {{
  --ink: #0b1220;
  --paper: #f7f2e7;
  --accent: #2d5bff;
  --accent-2: #f08b32;
  --muted: #6f7683;
  --card: #fffaf0;
  --border: #e3ddcf;
  --flag: #ffe4cc;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  background: radial-gradient(circle at top, #fff7ea 0%, #f0e8d8 45%, #efe6d5 100%);
  color: var(--ink);
  font-family: "Avenir Next", "Gill Sans", "Trebuchet MS", sans-serif;
}}
header {{
  padding: 32px 28px 16px;
  border-bottom: 1px solid var(--border);
  background: linear-gradient(120deg, #fff3dd 0%, #f7f2e7 60%, #f3efe4 100%);
}}
header h1 {{
  font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", Palatino, serif;
  margin: 0 0 6px;
  font-size: 28px;
  letter-spacing: 0.5px;
}}
header p {{ margin: 4px 0; color: var(--muted); }}
.summary {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
  padding: 16px 28px;
}}
.card {{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 14px 16px;
  box-shadow: 0 10px 30px rgba(20, 20, 20, 0.06);
}}
.card h2 {{
  margin: 0 0 6px;
  font-size: 16px;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: var(--muted);
}}
.card p {{ margin: 0; font-size: 18px; }}
.card ul {{ margin: 6px 0 0 18px; padding: 0; }}
.badge {{
  display: inline-block;
  background: var(--accent);
  color: white;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 12px;
  margin-right: 6px;
}}
.nav {{
  padding: 0 28px 18px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}}
.chip {{
  padding: 6px 12px;
  border-radius: 999px;
  background: #ffffff;
  border: 1px solid var(--border);
  text-decoration: none;
  color: var(--ink);
  font-size: 13px;
}}
main {{ padding: 0 28px 40px; }}
.season {{
  margin: 14px 0;
  border-radius: 14px;
  border: 1px solid var(--border);
  background: #fff;
  box-shadow: 0 10px 25px rgba(10, 10, 10, 0.06);
}}
.season summary {{
  cursor: pointer;
  padding: 12px 16px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  font-weight: 600;
}}
.season .year {{
  font-size: 18px;
  padding: 4px 10px;
  background: var(--accent-2);
  color: #fff;
  border-radius: 10px;
}}
.season .meta {{ color: var(--muted); font-weight: 500; }}
.grid {{
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  padding: 0 16px 16px;
}}
.panel {{
  background: #fffdf8;
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 12px;
}}
.panel h3 {{ margin: 0 0 8px; font-size: 16px; }}
.flagline {{ padding: 0 16px 16px; color: var(--muted); }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th, td {{ padding: 6px 8px; text-align: left; border-bottom: 1px solid var(--border); }}
tr.flag td {{ background: var(--flag); }}
@media (max-width: 720px) {{
  header {{ padding: 24px 18px 10px; }}
  .summary, .nav, main {{ padding-left: 18px; padding-right: 18px; }}
}}
</style>
</head>
<body>
<header>
  <h1>Long-Term Physics Sim Report</h1>
  <p>Seasons {year_min} to {year_max} | Generated {stamp}</p>
</header>
<section class="summary">
  <div class="card">
    <h2>Seasons</h2>
    <p>{len(seasons)} completed</p>
  </div>
  <div class="card">
    <h2>Years</h2>
    <p>{year_min} to {year_max}</p>
  </div>
  <div class="card">
    <h2>Most Flagged</h2>
    <ul>{flag_list}</ul>
  </div>
</section>
<nav class="nav">{nav_years}</nav>
<main>
  {''.join(season_blocks)}
</main>
</body>
</html>
"""

    output_path = output_dir / "season_report.html"
    output_path.write_text(html_doc, encoding="utf-8")
    return output_path


def _render_leaders(seasons: list[dict[str, Any]], output_dir: Path) -> Path:
    rows = []
    for season in seasons:
        year = season.get("year")
        leaders = season.get("leaders") or {}
        for side, side_data in leaders.items():
            for stat, entries in (side_data or {}).items():
                for idx, entry in enumerate(entries, start=1):
                    rows.append(
                        {
                            "year": year,
                            "side": side,
                            "stat": stat,
                            "rank": idx,
                            "player_id": entry.get("player_id"),
                            "name": entry.get("name"),
                            "team_id": entry.get("team_id"),
                            "value": entry.get("value"),
                        }
                    )

    years = sorted({r["year"] for r in rows if r.get("year") is not None})
    stats = sorted({r["stat"] for r in rows if r.get("stat")})

    options_year = "".join(f"<option value=\"{y}\">{y}</option>" for y in years)
    options_stat = "".join(
        f"<option value=\"{_escape(s)}\">{_escape(s)}</option>" for s in stats
    )

    data_json = json.dumps(rows)

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Season Leaders</title>
<style>
:root {{
  --ink: #0b1220;
  --paper: #f7f2e7;
  --accent: #2d5bff;
  --muted: #6f7683;
  --border: #e3ddcf;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  background: linear-gradient(120deg, #f7f2e7 0%, #f1eadc 100%);
  color: var(--ink);
  font-family: "Avenir Next", "Gill Sans", "Trebuchet MS", sans-serif;
}}
header {{
  padding: 28px 24px 12px;
  border-bottom: 1px solid var(--border);
}}
header h1 {{
  font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", Palatino, serif;
  margin: 0;
}}
.controls {{
  padding: 12px 24px;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}}
select, input {{
  padding: 6px 10px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: #fff;
}}
main {{ padding: 0 24px 24px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
th, td {{ padding: 8px 10px; text-align: left; border-bottom: 1px solid var(--border); }}
.tag {{
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--accent);
  color: white;
  font-size: 12px;
}}
</style>
</head>
<body>
<header>
  <h1>Season Leaders</h1>
</header>
<div class="controls">
  <label>Year
    <select id="year">
      <option value="">All</option>
      {options_year}
    </select>
  </label>
  <label>Stat
    <select id="stat">
      <option value="">All</option>
      {options_stat}
    </select>
  </label>
  <label>Search
    <input id="search" type="text" placeholder="player or team" />
  </label>
</div>
<main>
  <table>
    <thead>
      <tr>
        <th>Year</th>
        <th>Side</th>
        <th>Stat</th>
        <th>Rank</th>
        <th>Player</th>
        <th>Team</th>
        <th>Value</th>
      </tr>
    </thead>
    <tbody id="rows"></tbody>
  </table>
</main>
<script>
const data = {data_json};
const rows = document.getElementById('rows');
const yearSel = document.getElementById('year');
const statSel = document.getElementById('stat');
const search = document.getElementById('search');

function render() {{
  const y = yearSel.value;
  const s = statSel.value;
  const q = search.value.toLowerCase();
  const filtered = data.filter(r => {{
    if (y && String(r.year) !== y) return false;
    if (s && String(r.stat) !== s) return false;
    const hay = `${{r.name || ''}} ${{r.team_id || ''}} ${{r.player_id || ''}}`.toLowerCase();
    if (q && !hay.includes(q)) return false;
    return true;
  }});
  rows.innerHTML = filtered.map(r => `
    <tr>
      <td>${{r.year}}</td>
      <td><span class="tag">${{r.side}}</span></td>
      <td>${{r.stat}}</td>
      <td>${{r.rank}}</td>
      <td>${{r.name || ''}}</td>
      <td>${{r.team_id || ''}}</td>
      <td>${{r.value}}</td>
    </tr>
  `).join('');
}}

[yearSel, statSel, search].forEach(el => el.addEventListener('input', render));
render();
</script>
</body>
</html>
"""

    output_path = output_dir / "season_leaders.html"
    output_path.write_text(html_doc, encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Render long-term sim HTML reports.")
    parser.add_argument(
        "--analysis-dir",
        type=str,
        default=None,
        help="Path to the analysis folder containing season_summaries.jsonl",
    )
    args = parser.parse_args()

    analysis_dir = Path(args.analysis_dir) if args.analysis_dir else Path.cwd()
    summaries_path = analysis_dir / "season_summaries.jsonl"
    seasons = _read_jsonl(summaries_path)
    if not seasons:
        raise SystemExit(f"No seasons found at {summaries_path}")

    report_path = _render_report(seasons, analysis_dir)
    leaders_path = _render_leaders(seasons, analysis_dir)
    print(f"Wrote {report_path}")
    print(f"Wrote {leaders_path}")


if __name__ == "__main__":
    main()
