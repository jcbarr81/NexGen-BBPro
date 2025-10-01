from __future__ import annotations

"""Postseason data structures, persistence, and (later) simulation.

This module provides the bracket model and load/save helpers. Seeding and
simulation are implemented in subsequent tickets; here we define the
data-shapes and stable JSON schema to support resume and UI rendering.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from pathlib import Path
import json

from utils.path_utils import get_base_dir
import hashlib
from datetime import date as _date


SCHEMA_VERSION = 1


@dataclass
class PlayoffTeam:
    team_id: str
    seed: int
    league: str
    wins: int
    run_diff: int = 0


@dataclass
class GameResult:
    home: str
    away: str
    date: Optional[str] = None
    result: Optional[str] = None  # e.g. "4-2"
    boxscore: Optional[str] = None  # relative path to HTML
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SeriesConfig:
    length: int
    # Pattern of home stretches for higher seed. For BO7 2-3-2 -> [2,3,2].
    pattern: List[int]


@dataclass
class Matchup:
    high: PlayoffTeam  # higher seed (home field advantage)
    low: PlayoffTeam
    config: SeriesConfig
    games: List[GameResult] = field(default_factory=list)
    winner: Optional[str] = None  # team_id


@dataclass
class Round:
    name: str  # e.g. "WC", "DS", "CS", "WS"
    matchups: List[Matchup] = field(default_factory=list)


@dataclass
class PlayoffBracket:
    year: int
    rounds: List[Round] = field(default_factory=list)
    champion: Optional[str] = None
    runner_up: Optional[str] = None
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        def team_to_dict(t: PlayoffTeam) -> Dict[str, Any]:
            return {
                "team_id": t.team_id,
                "seed": t.seed,
                "league": t.league,
                "wins": t.wins,
                "run_diff": t.run_diff,
            }

        def game_to_dict(g: GameResult) -> Dict[str, Any]:
            return {
                "home": g.home,
                "away": g.away,
                "date": g.date,
                "result": g.result,
                "boxscore": g.boxscore,
                "meta": dict(g.meta or {}),
            }

        def matchup_to_dict(m: Matchup) -> Dict[str, Any]:
            return {
                "high": team_to_dict(m.high),
                "low": team_to_dict(m.low),
                "config": {
                    "length": m.config.length,
                    "pattern": list(m.config.pattern),
                },
                "games": [game_to_dict(g) for g in m.games],
                "winner": m.winner,
            }

        return {
            "schema_version": self.schema_version,
            "year": self.year,
            "champion": self.champion,
            "runner_up": self.runner_up,
            "rounds": [
                {
                    "name": r.name,
                    "matchups": [matchup_to_dict(m) for m in r.matchups],
                }
                for r in self.rounds
            ],
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "PlayoffBracket":
        def team_from_dict(d: Dict[str, Any]) -> PlayoffTeam:
            return PlayoffTeam(
                team_id=str(d.get("team_id", "")),
                seed=int(d.get("seed", 0)),
                league=str(d.get("league", "")),
                wins=int(d.get("wins", 0)),
                run_diff=int(d.get("run_diff", 0)),
            )

        def game_from_dict(d: Dict[str, Any]) -> GameResult:
            return GameResult(
                home=str(d.get("home", "")),
                away=str(d.get("away", "")),
                date=d.get("date"),
                result=d.get("result"),
                boxscore=d.get("boxscore"),
                meta=dict(d.get("meta", {}) or {}),
            )

        def matchup_from_dict(d: Dict[str, Any]) -> Matchup:
            cfg = d.get("config", {}) or {}
            return Matchup(
                high=team_from_dict(d.get("high", {})),
                low=team_from_dict(d.get("low", {})),
                config=SeriesConfig(
                    length=int(cfg.get("length", 7)),
                    pattern=[int(x) for x in (cfg.get("pattern") or [])],
                ),
                games=[game_from_dict(x) for x in (d.get("games") or [])],
                winner=d.get("winner"),
            )

        rounds = [
            Round(name=str(r.get("name", "")), matchups=[matchup_from_dict(m) for m in (r.get("matchups") or [])])
            for r in (data.get("rounds") or [])
        ]
        br = PlayoffBracket(
            year=int(data.get("year", 0)),
            rounds=rounds,
            champion=data.get("champion"),
            runner_up=data.get("runner_up"),
            schema_version=int(data.get("schema_version", SCHEMA_VERSION)),
        )
        return br


def _bracket_path(year: int | None = None) -> Path:
    base = get_base_dir() / "data"
    if year:
        return base / f"playoffs_{year}.json"
    return base / "playoffs.json"


def save_bracket(bracket: PlayoffBracket, path: Optional[Path] = None) -> Path:
    """Atomically persist a bracket JSON file and return the path."""

    p = path or _bracket_path(bracket.year)
    p.parent.mkdir(parents=True, exist_ok=True)
    # Roll a simple .bak before replacing if a file exists
    try:
        if p.exists():
            bak = p.with_suffix(p.suffix + ".bak")
            try:
                # Best-effort copy
                bak.write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
            except Exception:
                pass
    except Exception:
        pass
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(bracket.to_dict(), indent=2), encoding="utf-8")
    tmp.replace(p)
    return p


def load_bracket(path: Optional[Path] = None, *, year: Optional[int] = None) -> Optional[PlayoffBracket]:
    """Load a bracket if present, else return ``None``."""

    p = path or _bracket_path(year)
    try:
        if not p.exists():
            return None
        data = json.loads(p.read_text(encoding="utf-8"))
        # Schema/version guard
        if int(data.get("schema_version", SCHEMA_VERSION)) != SCHEMA_VERSION:
            return None
        return PlayoffBracket.from_dict(data)
    except Exception:
        return None


# --- Seeding engine (Ticket 2) ---------------------------------------------------------

def _infer_league(division: str, mapping: Dict[str, str]) -> str:
    if division in mapping:
        return mapping[division]
    # Best-effort inference: league is first token before space (e.g., "AL East")
    div = str(division).strip()
    return div.split(" ")[0] if div else ""


def _get_year_from_schedule() -> int:
    """Infer season year from the last schedule date if available."""

    from datetime import date
    import csv

    sched = get_base_dir() / "data" / "schedule.csv"
    try:
        if sched.exists():
            with sched.open(newline="", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            dates = [str(r.get("date") or "") for r in rows if r.get("date")]
            dates.sort()
            if dates:
                return int(dates[-1].split("-")[0])
    except Exception:
        pass
    return date.today().year


def _wins_and_diff(stand: Dict[str, Any]) -> tuple[int, int]:
    try:
        wins = int(stand.get("wins", 0))
        rf = int(stand.get("runs_for", 0))
        ra = int(stand.get("runs_against", 0))
        return wins, (rf - ra)
    except Exception:
        return 0, 0


def _rank_division_winners(teams_in_div: List[Any], standings: Dict[str, Dict[str, Any]]) -> Optional[Any]:
    if not teams_in_div:
        return None
    best = None
    best_key = (-1, -1)
    for t in teams_in_div:
        st = standings.get(getattr(t, "team_id", ""), {}) or {}
        wins, diff = _wins_and_diff(st)
        key = (wins, diff)
        if key > best_key:
            best_key = key
            best = t
    return best


def _seed_league(league_name: str, league_teams: List[Any], standings: Dict[str, Dict[str, Any]], cfg: Any) -> List[PlayoffTeam]:
    # Group by division name (full string)
    by_div: Dict[str, List[Any]] = {}
    for t in league_teams:
        div = getattr(t, "division", "")
        by_div.setdefault(div, []).append(t)

    # Pick division winners
    winners: List[Any] = []
    for div, members in by_div.items():
        w = _rank_division_winners(members, standings)
        if w is not None:
            winners.append(w)

    # Remaining teams are wildcard candidates
    winner_ids = {getattr(t, "team_id", "") for t in winners}
    wildcards = [t for t in league_teams if getattr(t, "team_id", "") not in winner_ids]

    # Rank all by wins -> run diff
    def rank_key(t: Any):
        st = standings.get(getattr(t, "team_id", ""), {}) or {}
        wins, diff = _wins_and_diff(st)
        return (wins, diff)

    winners.sort(key=rank_key, reverse=True)
    wildcards.sort(key=rank_key, reverse=True)

    slots = int(getattr(cfg, "num_playoff_teams_per_league", 6) or 6)
    if getattr(cfg, "division_winners_priority", True):
        pool = winners + wildcards
    else:
        pool = (league_teams or [])
        pool.sort(key=rank_key, reverse=True)

    seeded: List[PlayoffTeam] = []
    for idx, t in enumerate(pool[:slots], start=1):
        st = standings.get(getattr(t, "team_id", ""), {}) or {}
        wins, diff = _wins_and_diff(st)
        seeded.append(
            PlayoffTeam(
                team_id=getattr(t, "team_id", ""),
                seed=idx,
                league=league_name,
                wins=wins,
                run_diff=diff,
            )
        )
    return seeded


def generate_bracket(standings: Dict[str, Dict[str, Any]], teams: List[Any], cfg: Any) -> PlayoffBracket:
    """Generate an initial bracket based on final standings and config.

    The bracket includes explicit first-round pairings per league (WC or DS
    depending on size). Later rounds are created with empty matchups and will
    be populated after previous rounds complete.
    """

    # Infer leagues from team divisions (or config override)
    div_map: Dict[str, str] = dict(getattr(cfg, "division_to_league", {}) or {})
    by_league: Dict[str, List[Any]] = {}
    for t in teams:
        league = _infer_league(getattr(t, "division", ""), div_map) or ""
        by_league.setdefault(league or "LEAGUE", []).append(t)

    # Produce seeds per league
    leagues = sorted(by_league.keys())
    seeds_by_league: Dict[str, List[PlayoffTeam]] = {}
    for lg in leagues:
        seeds_by_league[lg] = _seed_league(lg, by_league[lg], standings, cfg)

    # Build rounds per league
    rounds: List[Round] = []
    num = int(getattr(cfg, "num_playoff_teams_per_league", 6) or 6)

    def cfg_for(length: int) -> SeriesConfig:
        pats = dict(getattr(cfg, "home_away_patterns", {}) or {3: [1, 1, 1], 5: [2, 2, 1], 7: [2, 3, 2]})
        return SeriesConfig(length=length, pattern=list(pats.get(length, [])))

    for lg in leagues:
        seeds = seeds_by_league.get(lg, [])
        if num == 4:
            # Division Series (2 matchups)
            r_ds = Round(name=f"{lg} DS")
            if len(seeds) >= 4:
                r_ds.matchups.append(Matchup(high=seeds[0], low=seeds[3], config=cfg_for(int(getattr(cfg, "series_lengths", {}).get("ds", 5)))))
                r_ds.matchups.append(Matchup(high=seeds[1], low=seeds[2], config=cfg_for(int(getattr(cfg, "series_lengths", {}).get("ds", 5)))))
            rounds.append(r_ds)
            rounds.append(Round(name=f"{lg} CS"))
        elif num == 6:
            # Wildcard (2 matchups), byes for seeds 1 and 2
            r_wc = Round(name=f"{lg} WC")
            if len(seeds) >= 6:
                r_wc.matchups.append(Matchup(high=seeds[2], low=seeds[5], config=cfg_for(int(getattr(cfg, "series_lengths", {}).get("wildcard", 3)))))
                r_wc.matchups.append(Matchup(high=seeds[3], low=seeds[4], config=cfg_for(int(getattr(cfg, "series_lengths", {}).get("wildcard", 3)))))
            rounds.append(r_wc)
            rounds.append(Round(name=f"{lg} DS"))
            rounds.append(Round(name=f"{lg} CS"))
        else:
            # 8 teams -> Division Series (4 matchups)
            r_ds = Round(name=f"{lg} DS")
            if len(seeds) >= 8:
                r_ds.matchups.append(Matchup(high=seeds[0], low=seeds[7], config=cfg_for(int(getattr(cfg, "series_lengths", {}).get("ds", 5)))))
                r_ds.matchups.append(Matchup(high=seeds[1], low=seeds[6], config=cfg_for(int(getattr(cfg, "series_lengths", {}).get("ds", 5)))))
                r_ds.matchups.append(Matchup(high=seeds[2], low=seeds[5], config=cfg_for(int(getattr(cfg, "series_lengths", {}).get("ds", 5)))))
                r_ds.matchups.append(Matchup(high=seeds[3], low=seeds[4], config=cfg_for(int(getattr(cfg, "series_lengths", {}).get("ds", 5)))))
            rounds.append(r_ds)
            rounds.append(Round(name=f"{lg} CS"))

    # Final
    if len(leagues) >= 2:
        rounds.append(Round(name="WS"))
    else:
        rounds.append(Round(name="Final"))

    year = _get_year_from_schedule()
    return PlayoffBracket(year=year, rounds=rounds)


# --- Series simulation (Ticket 3) ------------------------------------------------------

def _deterministic_seed(*parts: str) -> int:
    h = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    # Use 30 bits for compatibility with random.randrange ranges used elsewhere
    return int(h[:8], 16) & ((1 << 30) - 1)


def _wins_needed(length: int) -> int:
    return (int(length) // 2) + 1


def simulate_series(matchup: Matchup, *, year: int, round_name: str, series_index: int, simulate_game=None) -> Matchup:
    """Simulate a single series to completion and return the updated matchup."""

    if matchup.winner:
        return matchup
    wins_needed = _wins_needed(matchup.config.length)
    high_id = matchup.high.team_id
    low_id = matchup.low.team_id

    # Build home/away order for games according to pattern
    homes: List[str] = []
    flip = False
    for block in matchup.config.pattern:
        homes.extend([high_id if not flip else low_id] * block)
        flip = not flip

    # Lazy default simulate function
    if simulate_game is None:
        from playbalance.game_runner import simulate_game_scores as _sim
        simulate_game = _sim

    high_wins = 0
    low_wins = 0
    game_no = 0
    for home in homes:
        if high_wins >= wins_needed or low_wins >= wins_needed:
            break
        away = low_id if home == high_id else high_id
        seed = _deterministic_seed(str(year), round_name, str(series_index), str(game_no), home, away)
        # Call simulate_game with keyword seed if accepted; otherwise rely on RNG state
        try:
            result = simulate_game(home, away, seed=seed)
        except TypeError:
            result = simulate_game(home, away)

        # Parse result tuple
        home_runs = away_runs = None
        html = None
        extra = {}
        if isinstance(result, tuple):
            if len(result) >= 2:
                home_runs, away_runs = result[0], result[1]
            if len(result) >= 3:
                html = result[2] if isinstance(result[2], str) else None
            if len(result) >= 4 and isinstance(result[3], dict):
                extra = result[3]
        # Winning side
        if isinstance(home_runs, int) and isinstance(away_runs, int):
            if home_runs > away_runs:
                if home == high_id:
                    high_wins += 1
                else:
                    low_wins += 1
        # Save boxscore html if provided
        box_path = None
        if html:
            try:
                from playbalance.simulation import save_boxscore_html as _save_html
                game_id = f"{year}_{round_name}_S{series_index}_G{game_no}_{away}_at_{home}"
                box_path = _save_html("playoffs", html, game_id)
            except Exception:
                box_path = None

        matchup.games.append(
            GameResult(home=home, away=away, date=None, result=(f"{home_runs}-{away_runs}" if home_runs is not None else None), boxscore=box_path, meta=extra)
        )
        game_no += 1

    matchup.winner = high_id if high_wins > low_wins else low_id
    return matchup


def _league_from_round_name(name: str) -> Optional[str]:
    # e.g., "AL DS" -> "AL"
    parts = str(name).split()
    return parts[0] if parts and parts[0] not in {"WC", "DS", "CS", "WS", "Final"} else (parts[0] if len(parts) > 1 else None)


def _populate_next_round(bracket: PlayoffBracket, cfg: Any) -> None:
    """Populate the next round's matchups if the previous round has winners."""

    # Handle per-league transitions WC->DS and DS->CS
    by_name: Dict[str, Round] = {r.name: r for r in bracket.rounds}
    # For each league we find rounds
    leagues = set()
    for r in bracket.rounds:
        lg = _league_from_round_name(r.name)
        if lg:
            leagues.add(lg)

    def make_cfg(key: str) -> SeriesConfig:
        length = int(getattr(cfg, "series_lengths", {}).get(key, 7))
        pats = dict(getattr(cfg, "home_away_patterns", {}) or {3: [1, 1, 1], 5: [2, 2, 1], 7: [2, 3, 2]})
        return SeriesConfig(length=length, pattern=list(pats.get(length, [])))

    for lg in leagues:
        r_wc = by_name.get(f"{lg} WC")
        r_ds = by_name.get(f"{lg} DS")
        r_cs = by_name.get(f"{lg} CS")
        # WC complete -> create DS matchups: #1 vs lower winner, #2 vs other
        if r_wc and r_ds and not r_ds.matchups:
            winners = [m.winner for m in r_wc.matchups if m.winner]
            if len(winners) == len(r_wc.matchups) and len(r_wc.matchups) > 0:
                # Determine seeds for winners
                def seed_of(team_id: str) -> int:
                    # Look in a WC matchup participant
                    for m in r_wc.matchups:
                        if m.high.team_id == team_id:
                            return m.high.seed
                        if m.low.team_id == team_id:
                            return m.low.seed
                    return 99

                winners_sorted = sorted(winners, key=seed_of)
                # Find top seeds (1 and 2) from any prior seeding (from WC matchups' opponents)
                top1 = None
                top2 = None
                # Scan all teams seen in WC to get league seeds 1 and 2 via minimal seed numbers
                seen = []
                for m in r_wc.matchups:
                    seen.extend([m.high, m.low])
                if seen:
                    seen_sorted = sorted(seen, key=lambda t: t.seed)
                    # Note: 1 and 2 might not be in WC if they had byes; create phantom entries
                    # We synthesize placeholders for seeds 1 and 2 using league name
                    seeds_present = {t.seed for t in seen_sorted}
                    # Default placeholders
                    top1 = next((t for t in seen_sorted if t.seed == 1), None) or PlayoffTeam(team_id=f"{lg}#1", seed=1, league=lg, wins=0)
                    top2 = next((t for t in seen_sorted if t.seed == 2), None) or PlayoffTeam(team_id=f"{lg}#2", seed=2, league=lg, wins=0)
                if winners_sorted:
                    # Lowest seed winner faces #1
                    low_w = winners_sorted[0]
                    hi_w = winners_sorted[1] if len(winners_sorted) > 1 else winners_sorted[0]
                    r_ds.matchups.append(Matchup(high=top1, low=next((t for t in seen if t.team_id == low_w), PlayoffTeam(team_id=low_w, seed=99, league=lg, wins=0)), config=make_cfg("ds")))
                    r_ds.matchups.append(Matchup(high=top2, low=next((t for t in seen if t.team_id == hi_w), PlayoffTeam(team_id=hi_w, seed=99, league=lg, wins=0)), config=make_cfg("ds")))

        # DS complete -> create CS matchup
        if r_ds and r_cs and not r_cs.matchups:
            winners = [m.winner for m in r_ds.matchups if m.winner]
            if len(winners) == len(r_ds.matchups) and len(winners) >= 2:
                # Home field to lower numerical seed if we carried them through
                participants: List[PlayoffTeam] = []
                for team_id in winners[:2]:
                    # Find seed from DS matchups
                    for m in r_ds.matchups:
                        if m.high.team_id == team_id:
                            participants.append(m.high)
                            break
                        if m.low.team_id == team_id:
                            participants.append(m.low)
                            break
                if len(participants) == 2:
                    participants.sort(key=lambda t: t.seed)
                    r_cs.matchups.append(Matchup(high=participants[0], low=participants[1], config=make_cfg("cs")))

    # CS complete in two leagues -> WS matchup
    r_ws = by_name.get("WS") or by_name.get("Final")
    if r_ws and not r_ws.matchups:
        # Collect league CS winners by league key
        winners_by_lg: Dict[str, PlayoffTeam] = {}
        for r in bracket.rounds:
            if r.name.endswith(" CS") and r.matchups and all(m.winner for m in r.matchups):
                lg = r.name.split()[0]
                # Winner is team_id; locate its seeded object from the CS matchup
                win_id = r.matchups[0].winner
                for side in (r.matchups[0].high, r.matchups[0].low):
                    if side.team_id == win_id:
                        winners_by_lg[lg] = side
                        break
        if len(winners_by_lg) >= 2:
            lgs = sorted(winners_by_lg.keys())
            a, b = winners_by_lg[lgs[0]], winners_by_lg[lgs[1]]
            home, away = (a, b) if a.seed < b.seed else (b, a)
            r_ws.matchups.append(Matchup(high=home, low=away, config=make_cfg("ws")))


def simulate_playoffs(bracket: PlayoffBracket, *, simulate_game=None, persist_cb=None) -> PlayoffBracket:
    """Simulate playoffs from current state to the end.

    - Simulates outstanding matchups in the first non-empty round(s)
    - After each round, populates the next round's matchups
    - Calls ``persist_cb(bracket)`` after each game if provided
    """

    year = bracket.year or _get_year_from_schedule()

    def persist():
        try:
            if persist_cb:
                persist_cb(bracket)
            else:
                save_bracket(bracket)
        except Exception:
            pass

    # Iterate until no progress can be made
    made_progress = True
    while made_progress:
        made_progress = False
        # Simulate the first round that has pending matchups
        for r_index, rnd in enumerate(bracket.rounds):
            pendings = [i for i, m in enumerate(rnd.matchups) if not m.winner and m.high and m.low and m.high.team_id and m.low.team_id]
            if not pendings:
                continue
            for i in pendings:
                simulate_series(rnd.matchups[i], year=year, round_name=rnd.name, series_index=i, simulate_game=simulate_game)
                made_progress = True
                persist()
            # After completing this round (all winners set), populate next stage
            if all(m.winner for m in rnd.matchups):
                # Champion resolution if WS/Final
                if rnd.name in {"WS", "Final"} and rnd.matchups:
                    champ_id = rnd.matchups[0].winner
                    if champ_id:
                        bracket.champion = champ_id
                        # Runner-up is the other participant
                        m = rnd.matchups[0]
                        bracket.runner_up = m.low.team_id if champ_id == m.high.team_id else m.high.team_id
                        # Nothing else to populate; playoffs complete
                        persist()
                        return bracket
                _populate_next_round(bracket, cfg={
                    "series_lengths": getattr(bracket, "series_lengths", {"ds": 5, "cs": 7, "ws": 7, "wildcard": 3}),
                    "home_away_patterns": {3: [1, 1, 1], 5: [2, 2, 1], 7: [2, 3, 2]},
                })
            break  # simulate one round at a time
    return bracket


def simulate_next_round(bracket: PlayoffBracket, *, simulate_game=None, persist_cb=None) -> PlayoffBracket:
    """Simulate only the next round that has any pending matchups."""

    year = bracket.year or _get_year_from_schedule()

    def persist():
        try:
            if persist_cb:
                persist_cb(bracket)
            else:
                save_bracket(bracket)
        except Exception:
            pass

    # Find the next round with pending matchups
    for r_index, rnd in enumerate(bracket.rounds):
        pendings = [i for i, m in enumerate(rnd.matchups) if not m.winner and m.high and m.low and m.high.team_id and m.low.team_id]
        if not pendings:
            continue
        for i in pendings:
            simulate_series(rnd.matchups[i], year=year, round_name=rnd.name, series_index=i, simulate_game=simulate_game)
            persist()
        # After finishing this round, populate next round matchups
        if all(m.winner for m in rnd.matchups):
            if rnd.name in {"WS", "Final"} and rnd.matchups:
                # Champion resolved
                champ_id = rnd.matchups[0].winner
                if champ_id:
                    bracket.champion = champ_id
                    m = rnd.matchups[0]
                    bracket.runner_up = m.low.team_id if champ_id == m.high.team_id else m.high.team_id
            else:
                _populate_next_round(bracket, cfg={
                    "series_lengths": getattr(bracket, "series_lengths", {"ds": 5, "cs": 7, "ws": 7, "wildcard": 3}),
                    "home_away_patterns": {3: [1, 1, 1], 5: [2, 2, 1], 7: [2, 3, 2]},
                })
            persist()
        break
    return bracket
 


__all__ = [
    "PlayoffTeam",
    "GameResult",
    "SeriesConfig",
    "Matchup",
    "Round",
    "PlayoffBracket",
    "save_bracket",
    "load_bracket",
    "generate_bracket",
    "simulate_series",
    "simulate_playoffs",
    "simulate_next_round",
]
