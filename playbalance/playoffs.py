from __future__ import annotations

"""Postseason data structures, persistence, and (later) simulation.

This module provides the bracket model and load/save helpers. Seeding and
simulation are implemented in subsequent tickets; here we define the
data-shapes and stable JSON schema to support resume and UI rendering.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import json

from utils.path_utils import get_base_dir
import hashlib
from datetime import date as _date


SCHEMA_VERSION = 1

_DEFAULT_SERIES_LENGTHS = {"wildcard": 3, "ds": 5, "cs": 7, "ws": 7}


def _extract_series_settings(cfg_like: Any) -> Tuple[Dict[str, Any], Dict[int, List[int]]]:
    if isinstance(cfg_like, dict):
        lengths = dict((cfg_like.get("series_lengths") or {}))
        patterns_raw = cfg_like.get("home_away_patterns") or {}
    else:
        lengths = dict(getattr(cfg_like, "series_lengths", {}) or {})
        patterns_raw = getattr(cfg_like, "home_away_patterns", {}) or {}

    patterns: Dict[int, List[int]] = {}
    for key, value in patterns_raw.items():
        try:
            patterns[int(key)] = [int(x) for x in (value or [])]
        except Exception:
            continue
    return lengths, patterns


def _series_config_from_settings(cfg_like: Any, key: str) -> SeriesConfig:
    lengths, patterns = _extract_series_settings(cfg_like)
    length = int(lengths.get(key, _DEFAULT_SERIES_LENGTHS.get(key, 7)))
    pattern = list(patterns.get(length, []))
    return SeriesConfig(length=length, pattern=pattern)


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
class ParticipantRef:
    """Reference to a future matchup participant."""

    kind: str  # 'seed' or 'winner'
    league: Optional[str] = None
    seed: Optional[int] = None
    source_round: Optional[str] = None
    slot: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "league": self.league,
            "seed": self.seed,
            "source_round": self.source_round,
            "slot": self.slot,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ParticipantRef":
        return ParticipantRef(
            kind=str(data.get("kind", "seed")),
            league=data.get("league"),
            seed=data.get("seed"),
            source_round=data.get("source_round"),
            slot=int(data.get("slot", 0)),
        )


@dataclass
class RoundPlanEntry:
    """Plan for creating a matchup once prerequisite winners are known."""

    series_key: str
    sources: List[ParticipantRef] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "series_key": self.series_key,
            "sources": [ref.to_dict() for ref in self.sources],
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "RoundPlanEntry":
        return RoundPlanEntry(
            series_key=str(data.get("series_key", "cs")),
            sources=[ParticipantRef.from_dict(ref) for ref in (data.get("sources") or [])],
        )


@dataclass
class Round:
    name: str  # e.g. "WC", "DS", "CS", "WS"
    matchups: List[Matchup] = field(default_factory=list)
    plan: List[RoundPlanEntry] = field(default_factory=list)


@dataclass
class PlayoffBracket:
    year: int
    rounds: List[Round] = field(default_factory=list)
    champion: Optional[str] = None
    runner_up: Optional[str] = None
    schema_version: int = SCHEMA_VERSION
    seeds_by_league: Dict[str, List[PlayoffTeam]] = field(default_factory=dict)

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
            "seeds": {lg: [team_to_dict(t) for t in (teams or [])] for lg, teams in (self.seeds_by_league or {}).items()},
            "rounds": [
                {
                    "name": r.name,
                    "matchups": [matchup_to_dict(m) for m in r.matchups],
                    "plan": [entry.to_dict() for entry in getattr(r, "plan", [])],
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
            Round(
                name=str(r.get("name", "")),
                matchups=[matchup_from_dict(m) for m in (r.get("matchups") or [])],
                plan=[RoundPlanEntry.from_dict(p) for p in (r.get("plan") or [])],
            )
            for r in (data.get("rounds") or [])
        ]
        seeds_raw = data.get("seeds") or {}
        seeds_by_league: Dict[str, List[PlayoffTeam]] = {}
        for lg, teams in seeds_raw.items():
            if isinstance(teams, list):
                seeds_by_league[str(lg)] = [team_from_dict(t) for t in teams]

        br = PlayoffBracket(
            year=int(data.get("year", 0)),
            rounds=rounds,
            champion=data.get("champion"),
            runner_up=data.get("runner_up"),
            schema_version=int(data.get("schema_version", SCHEMA_VERSION)),
            seeds_by_league=seeds_by_league,
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
    """Load the most relevant bracket if present, otherwise return ``None``."""

    candidates: List[Path] = []
    if path is not None:
        candidates.append(Path(path))
    else:
        matches: List[Path] = []
        if year is not None:
            candidates.append(_bracket_path(year))
            candidates.append(_bracket_path())
        else:
            candidates.append(_bracket_path())
            try:
                inferred_year = _get_year_from_schedule()
            except Exception:
                inferred_year = None
            if inferred_year:
                candidates.append(_bracket_path(inferred_year))
        base = get_base_dir() / "data"
        try:
            matches = list(base.glob("playoffs_*.json"))
        except Exception:
            matches = []
        if year is None and matches:
            def _year_key(p: Path) -> int:
                stem = p.stem
                try:
                    return int(stem.split("_", 1)[1])
                except Exception:
                    return 0
            matches = sorted(matches, key=_year_key, reverse=True)
        else:
            matches = sorted(matches, reverse=True)
        candidates.extend(matches)
    seen: set[Path] = set()
    for candidate in candidates:
        p = Path(candidate)
        if p in seen:
            continue
        seen.add(p)
        try:
            if not p.exists():
                continue
            data = json.loads(p.read_text(encoding="utf-8"))
            if int(data.get("schema_version", SCHEMA_VERSION)) != SCHEMA_VERSION:
                continue
            return PlayoffBracket.from_dict(data)
        except Exception:
            continue
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


def _build_league_rounds(league: str, seeds: List[PlayoffTeam], cfg: Any) -> Tuple[List[Round], Optional[str]]:
    rounds: List[Round] = []
    final_round_name: Optional[str] = None

    if len(seeds) < 2:
        return rounds, final_round_name

    seed_lookup = {team.seed: team for team in seeds}

    def team_for(seed_number: int) -> Optional[PlayoffTeam]:
        return seed_lookup.get(seed_number)

    def add_match(round_obj: Round, high_seed: int, low_seed: int, series_key: str) -> None:
        high = team_for(high_seed)
        low = team_for(low_seed)
        if high is None or low is None:
            return
        round_obj.matchups.append(
            Matchup(high=high, low=low, config=_series_config_from_settings(cfg, series_key))
        )

    n = len(seeds)

    if n == 2:
        cs = Round(name=f"{league} CS")
        add_match(cs, 1, 2, "cs")
        rounds.append(cs)
        final_round_name = cs.name
        return rounds, final_round_name

    if n == 3:
        wc = Round(name=f"{league} WC")
        add_match(wc, 2, 3, "wildcard")
        rounds.append(wc)

        cs = Round(name=f"{league} CS")
        cs.plan.append(
            RoundPlanEntry(
                series_key="cs",
                sources=[
                    ParticipantRef(kind="seed", league=league, seed=1),
                    ParticipantRef(kind="winner", source_round=wc.name, slot=0),
                ],
            )
        )
        rounds.append(cs)
        final_round_name = cs.name
        return rounds, final_round_name

    if n == 4:
        ds = Round(name=f"{league} DS")
        add_match(ds, 1, 4, "ds")
        add_match(ds, 2, 3, "ds")
        rounds.append(ds)

        cs = Round(name=f"{league} CS")
        cs.plan.append(
            RoundPlanEntry(
                series_key="cs",
                sources=[
                    ParticipantRef(kind="winner", source_round=ds.name, slot=0),
                    ParticipantRef(kind="winner", source_round=ds.name, slot=1),
                ],
            )
        )
        rounds.append(cs)
        final_round_name = cs.name
        return rounds, final_round_name

    if n == 5:
        wc = Round(name=f"{league} WC")
        add_match(wc, 4, 5, "wildcard")
        rounds.append(wc)

        ds = Round(name=f"{league} DS")
        add_match(ds, 2, 3, "ds")
        ds.plan.append(
            RoundPlanEntry(
                series_key="ds",
                sources=[
                    ParticipantRef(kind="seed", league=league, seed=1),
                    ParticipantRef(kind="winner", source_round=wc.name, slot=0),
                ],
            )
        )
        rounds.append(ds)

        cs = Round(name=f"{league} CS")
        cs.plan.append(
            RoundPlanEntry(
                series_key="cs",
                sources=[
                    ParticipantRef(kind="winner", source_round=ds.name, slot=0),
                    ParticipantRef(kind="winner", source_round=ds.name, slot=1),
                ],
            )
        )
        rounds.append(cs)
        final_round_name = cs.name
        return rounds, final_round_name

    # n >= 6 -> treat as 6 with wildcards
    wc = Round(name=f"{league} WC")
    add_match(wc, 3, 6, "wildcard")
    add_match(wc, 4, 5, "wildcard")
    rounds.append(wc)

    ds = Round(name=f"{league} DS")
    ds.plan.append(
        RoundPlanEntry(
            series_key="ds",
            sources=[
                ParticipantRef(kind="seed", league=league, seed=1),
                ParticipantRef(kind="winner", source_round=wc.name, slot=0),
            ],
        )
    )
    ds.plan.append(
        RoundPlanEntry(
            series_key="ds",
            sources=[
                ParticipantRef(kind="seed", league=league, seed=2),
                ParticipantRef(kind="winner", source_round=wc.name, slot=1),
            ],
        )
    )
    rounds.append(ds)

    cs = Round(name=f"{league} CS")
    cs.plan.append(
        RoundPlanEntry(
            series_key="cs",
            sources=[
                ParticipantRef(kind="winner", source_round=ds.name, slot=0),
                ParticipantRef(kind="winner", source_round=ds.name, slot=1),
            ],
        )
    )
    rounds.append(cs)
    final_round_name = cs.name
    return rounds, final_round_name




def generate_bracket(standings: Dict[str, Dict[str, Any]], teams: List[Any], cfg: Any) -> PlayoffBracket:
    """Generate an initial bracket based on final standings and configuration."""

    div_map: Dict[str, str] = dict(getattr(cfg, "division_to_league", {}) or {})
    by_league: Dict[str, List[Any]] = {}
    for team in teams:
        league = _infer_league(getattr(team, "division", ""), div_map) or ""
        by_league.setdefault(league or "LEAGUE", []).append(team)

    leagues = sorted(by_league.keys())
    seeds_by_league: Dict[str, List[PlayoffTeam]] = {}
    rounds: List[Round] = []
    league_finals: Dict[str, str] = {}

    for league in leagues:
        seeded = _seed_league(league, by_league[league], standings, cfg)
        default_slots = int(getattr(cfg, "num_playoff_teams_per_league", 6) or 6)
        slot_fn = getattr(cfg, "slots_for_league", None)
        if callable(slot_fn):
            try:
                slots = int(slot_fn(len(by_league[league])))
            except Exception:
                slots = default_slots
        else:
            slots = default_slots

        slots = min(slots, len(seeded))
        if slots < 2:
            continue

        seeds = seeded[:slots]
        seeds_by_league[league] = seeds

        league_rounds, final_round_name = _build_league_rounds(league, seeds, cfg)
        rounds.extend(league_rounds)
        if final_round_name:
            league_finals[league] = final_round_name

    if len(league_finals) >= 2:
        contenders = sorted(league_finals.keys())[:2]
        ws = Round(name="WS")
        ws.plan.append(
            RoundPlanEntry(
                series_key="ws",
                sources=[
                    ParticipantRef(kind="winner", source_round=league_finals[contenders[0]], slot=0),
                    ParticipantRef(kind="winner", source_round=league_finals[contenders[1]], slot=0),
                ],
            )
        )
        rounds.append(ws)
    elif len(league_finals) == 1:
        # Single-league setup: rename the league final so champion resolution works.
        (_, final_name), = league_finals.items()
        for rnd in rounds:
            if rnd.name == final_name:
                rnd.name = "Final"
                break

    year = _get_year_from_schedule()
    return PlayoffBracket(year=year, rounds=rounds, seeds_by_league=seeds_by_league)



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
    """Populate planned matchups when prerequisites are met."""

    if not bracket.rounds:
        return

    by_name: Dict[str, Round] = {r.name: r for r in bracket.rounds}
    lengths, patterns = _extract_series_settings(cfg)
    seeds_map = getattr(bracket, "seeds_by_league", {}) or {}

    def make_cfg(key: str) -> SeriesConfig:
        length = int(lengths.get(key, _DEFAULT_SERIES_LENGTHS.get(key, 7)))
        pattern = list(patterns.get(length, []))
        return SeriesConfig(length=length, pattern=pattern)

    def seed_team(ref: ParticipantRef) -> Optional[PlayoffTeam]:
        league = ref.league or ""
        seed_no = ref.seed
        if seed_no is None:
            return None
        for team in seeds_map.get(league, []):
            if team.seed == seed_no:
                return team
        return None

    def round_winner(ref: ParticipantRef) -> Optional[PlayoffTeam]:
        source_round = by_name.get(ref.source_round or "")
        if not source_round or ref.slot >= len(source_round.matchups):
            return None
        matchup = source_round.matchups[ref.slot]
        win_id = matchup.winner
        if not win_id:
            return None
        if matchup.high.team_id == win_id:
            return matchup.high
        if matchup.low.team_id == win_id:
            return matchup.low
        return None

    for rnd in bracket.rounds:
        if not rnd.plan:
            continue
        existing_pairs = {tuple(sorted((m.high.team_id, m.low.team_id))) for m in rnd.matchups}
        for entry in rnd.plan:
            participants: List[PlayoffTeam] = []
            for ref in entry.sources:
                team: Optional[PlayoffTeam] = None
                if ref.kind == "seed":
                    team = seed_team(ref)
                elif ref.kind == "winner":
                    team = round_winner(ref)
                if team is None:
                    participants = []
                    break
                participants.append(team)

            if len(participants) != 2:
                continue

            pair_key = tuple(sorted((participants[0].team_id, participants[1].team_id)))
            if pair_key in existing_pairs:
                continue

            participants.sort(key=lambda t: (t.seed, -t.wins, -t.run_diff, t.team_id))
            high, low = participants[0], participants[1]
            rnd.matchups.append(Matchup(high=high, low=low, config=make_cfg(entry.series_key)))
            existing_pairs.add(pair_key)



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
    "ParticipantRef",
    "RoundPlanEntry",
    "Round",
    "PlayoffBracket",
    "save_bracket",
    "load_bracket",
    "generate_bracket",
    "simulate_series",
    "simulate_playoffs",
    "simulate_next_round",
]
