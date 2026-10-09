"""
capplan.py — the multi-year cap planner: committed money by season, dead money,
expiring players and "what if I extend him?". No UI code.

Contract years count the seasons still to be paid, starting with the current
season during the regular season and playoffs, and with next season once the
season has ended (contracts tick down at season end). Either way a player is
paid in planner column k while contract["years"] > k, so column 0 is the cap
year being managed now.
"""
from contracts import min_salary
import negotiation as nego
from settings import settings

IN_SEASON = ("regular", "playoffs")


def first_season(lg):
    """The season shown in column 0."""
    return lg.year if lg.phase in IN_SEASON else lg.year + 1


def projected_caps(lg, n):
    g = settings["cap_growth"]
    lead = 0 if lg.phase in IN_SEASON else 1      # the cap grows when the new season starts
    return [int(lg.salary_cap * (1.0 + g) ** (k + lead)) for k in range(n)]


def player_hits(p, n, what_if=None):
    """Cap hit for each of the next n seasons (0 once the deal has run out)."""
    if what_if and p.id in what_if:
        apy, years = what_if[p.id]
        return [apy if k < years else 0 for k in range(n)]
    c = p.contract
    if not c:
        return [0] * n
    return [c["salary"] if c["years"] > k else 0 for k in range(n)]


def extension_estimate(lg, team, p):
    """What his agent would ask for an extension now: (apy, years)."""
    dem = nego.demands(lg, team, p, resign=True)
    return max(min_salary(lg.salary_cap), dem["apy"]), max(1, min(5, dem["years"]))


def extension_dead_money(p):
    """Unamortised bonus from the old deal that an extension leaves on this year's books."""
    c = p.contract
    if not c or c.get("years", 0) <= 0 or "length" not in c:
        return 0
    return int(c.get("bonus", 0) / max(1, c["length"]) * max(0, c["years"] - 1))


def plan(lg, team, n=5, what_if=None):
    """
    The cap picture for the next n seasons.
    what_if: {pid: (apy, years)} extensions to preview in place of the current deals.
    Returns a dict with 'seasons', 'caps', 'committed', 'dead', 'space', 'counts',
    'expiring' (names whose deals end after each season) and 'players' (rows).
    """
    what_if = what_if or {}
    in_season = lg.phase in IN_SEASON
    seasons = [first_season(lg) + k for k in range(n)]
    caps = projected_caps(lg, n)
    committed = [0] * n
    counts = [0] * n
    expiring = [[] for _ in range(n)]
    dead = [0] * n
    dead[0] = team.dead_cap + sum(extension_dead_money(p) for p in team.roster if p.id in what_if)
    rows = []
    for p in team.roster:
        hits = player_hits(p, n, what_if)
        if not any(hits):
            continue
        for k, h in enumerate(hits):
            if h:
                committed[k] += h
                counts[k] += 1
        last = max(k for k, h in enumerate(hits) if h)
        total = what_if[p.id][1] if p.id in what_if else p.contract["years"]
        if total - 1 < n:
            expiring[total - 1].append(p)
        cut_dead = nego.dead_money(p.contract, in_season) if p.contract else 0
        rows.append({"player": p, "hits": hits, "last": last, "preview": p.id in what_if,
                     "cut_dead": cut_dead, "cut_saves": hits[0] - cut_dead})
    rows.sort(key=lambda r: -sum(r["hits"]))
    space = [caps[k] - committed[k] - dead[k] for k in range(n)]
    return {"seasons": seasons, "caps": caps, "committed": committed, "dead": dead, "space": space,
            "counts": counts, "expiring": expiring, "players": rows}
