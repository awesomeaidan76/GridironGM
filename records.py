"""
records.py — the league record book (single-season and career).
"""
from collections import Counter

from stats import total_tackles

CATEGORIES = [
    ("pass_yds", "Passing Yards"), ("pass_td", "Passing TD"), ("pass_cmp", "Completions"),
    ("rush_yds", "Rushing Yards"), ("rush_td", "Rushing TD"),
    ("rec", "Receptions"), ("rec_yds", "Receiving Yards"), ("rec_td", "Receiving TD"),
    ("scrim", "Scrimmage Yards"), ("total_td", "Total TD"),
    ("sacks", "Sacks"), ("def_int", "Interceptions"), ("tackles", "Tackles"),
    ("ff", "Forced Fumbles"), ("fgm", "Field Goals Made"),
    ("pressures", "Pressures"), ("pd", "Passes Defended"), ("ret_td", "Return TD"),
    ("pass_epa", "Passing EPA"), ("rush_epa", "Rushing EPA"), ("rec_epa", "Receiving EPA"),
]

# Single-game records (player stat lines, plus two team categories)
GAME_CATEGORIES = [
    ("pass_yds", "Passing Yards"), ("pass_td", "Passing TD"), ("rush_yds", "Rushing Yards"),
    ("rush_td", "Rushing TD"), ("rec", "Receptions"), ("rec_yds", "Receiving Yards"),
    ("rec_td", "Receiving TD"), ("sacks", "Sacks"), ("def_int", "Interceptions"),
    ("tackles", "Tackles"), ("pressures", "Pressures"), ("fgm", "Field Goals Made"),
    ("scrim", "Scrimmage Yards"), ("pass_long", "Longest Pass"), ("rush_long", "Longest Run"),
    ("fg_long", "Longest Field Goal"),
]
TEAM_GAME_CATEGORIES = [("team_points", "Points in a Game"), ("margin", "Margin of Victory"),
                        ("team_yds", "Total Yards in a Game")]


def _value(stats, key):
    if key == "tackles":
        return total_tackles(stats)
    if key == "scrim":
        return stats["rush_yds"] + stats["rec_yds"]
    if key == "total_td":
        return stats["rush_td"] + stats["rec_td"] + stats["def_td"] + stats["kr_td"] + stats["pr_td"]
    if key == "ret_td":
        return stats["kr_td"] + stats["pr_td"]
    return stats[key]


def _push(table, key, row, n=10):
    rows = table.setdefault(key, [])
    if len(rows) >= n and row[0] <= rows[-1][0]:
        return False
    rows.append(row)
    rows.sort(key=lambda r: -r[0])
    del rows[n:]
    return rows[0] is row


def update_game_records(lg, res):
    """Called after every game. Returns news strings for new league records."""
    if not hasattr(lg, "game_records") or lg.game_records is None:
        lg.game_records = {}
    news = []
    wk = res.playoff or f"Wk {res.week}"
    for pid, line in res.player_stats.items():
        name, pos, abbr, _ = res.player_meta[pid]
        opp = res.opponent(abbr) if abbr in (res.home, res.away) else ""
        for k, label in GAME_CATEGORIES:
            v = _value(line, k)
            if v <= 0:
                continue
            row = (v, name, pos, abbr, opp, lg.year, wk, pid)
            if _push(lg.game_records, k, row) and lg.year > getattr(lg, "founded", lg.year):
                news.append(f"{name} ({abbr}) set a league single-game record: {v:g} {label.lower()}")
    for abbr in (res.home, res.away):
        opp = res.opponent(abbr)
        pts, opp_pts = res.score_of(abbr), res.score_of(opp)
        ts = res.team_stats[abbr]
        for k, v in (("team_points", pts), ("margin", pts - opp_pts), ("team_yds", ts["total_yds"])):
            if v > 0:
                _push(lg.game_records, k, (v, f"{pts}-{opp_pts} vs {opp}", "", abbr, opp, lg.year, wk, None))
    return news


def _people(lg):
    seen = set()
    out = []
    for p in lg.all_players(include_fa=True) + lg.retired:
        if p.id not in seen:
            seen.add(p.id)
            out.append(p)
    return out


def season_records(lg, n=10, include_current=True):
    """{key: [(value, name, pos, team, year, pid), ...]}"""
    rows = {k: [] for k, _ in CATEGORIES}
    for p in _people(lg):
        seasons = [(yr, s["team"], s["stats"]) for yr, s in p.career.items()]
        if include_current and lg.phase in ("regular", "playoffs") and p.season_stats["gp"]:
            seasons.append((lg.year, p.team or "FA", p.season_stats))
        for yr, team, st in seasons:
            for k, _ in CATEGORIES:
                v = _value(st, k)
                if v > 0:
                    rows[k].append((v, p.name, p.position, team, yr, p.id))
    return {k: sorted(v, key=lambda r: -r[0])[:n] for k, v in rows.items()}


def career_totals(p, include_current=True, lg=None):
    tot = Counter()
    for s in p.career.values():
        tot.update(s["stats"])
    if include_current and lg is not None and lg.phase in ("regular", "playoffs"):
        tot.update(p.season_stats)
    return tot


def career_leaders(lg, n=25):
    rows = {k: [] for k, _ in CATEGORIES}
    for p in _people(lg):
        tot = career_totals(p, True, lg)
        if not tot["gp"]:
            continue
        status = "HOF" if p.hall_of_fame else ("Retired" if p.retired else (p.team or "FA"))
        for k, _ in CATEGORIES:
            v = _value(tot, k)
            if v > 0:
                rows[k].append((v, p.name, p.position, status, len(p.career), p.id))
    return {k: sorted(v, key=lambda r: -r[0])[:n] for k, v in rows.items()}


def team_records(lg):
    best = []
    for t in lg.teams.values():
        for h in t.history:
            best.append((h["w"], h["pf"], t.abbr, h["year"], f"{h['w']}-{h['l']}" +
                         (f"-{h['t']}" if h['t'] else ""), h["result"]))
    most_wins = sorted(best, key=lambda r: (-r[0], -r[1]))[:10]
    most_points = sorted(best, key=lambda r: -r[1])[:10]
    titles = sorted(((t.titles, t.conf_titles, t.abbr) for t in lg.teams.values()),
                    reverse=True)
    return {"wins": most_wins, "points": most_points, "titles": titles}
