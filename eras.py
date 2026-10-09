"""
eras.py — how the league's style of play evolves on its own.

Nothing here forces an era. Instead the league has *talent pipelines*: how
strong the incoming pool of players is at each position group. Pipelines
drift slowly, and they respond to what the league rewards — if quarterbacks
dominate the awards, the headlines and the money, more young athletes chase
the position and, a few years later, quarterback classes get deeper. Add
coaching trees (winning schemes get copied) and roster-driven play calling,
and eras emerge: a run of great running back classes produces a run-heavy
league, a cluster of elite passers pulls everyone toward the air.

A new league starts from random, era-neutral conditions; real rule changes
come from the competition committee (committee.py), which reacts to the
league the same way the real one does.
"""
import math
import random


GROUPS = {
    "QB": ["QB"], "RB": ["RB", "FB"], "WR": ["WR"], "TE": ["TE"],
    "OL": ["OT", "IOL"], "DL": ["DT", "EDGE"], "LB": ["LB"],
    "DB": ["CB", "S"], "K": ["K", "P"],
}
POS_GROUP = {pos: g for g, ps in GROUPS.items() for pos in ps}

# Expected share of league prestige per group (roughly its share of
# starters, weighted by importance) — used to measure over/under rewarding
BASELINE_PRESTIGE = {
    "QB": 0.17, "RB": 0.08, "WR": 0.15, "TE": 0.06, "OL": 0.12,
    "DL": 0.16, "LB": 0.09, "DB": 0.15, "K": 0.02,
}

# A brand-new league starts from a neutral landscape with random wrinkles —
# a few position groups a little deeper or thinner than usual, some styles of
# player a little more common, a slightly different mix of schemes. Nothing
# about it is tied to a year or a real-life era; what follows grows out of it.
BASE_SCHEMES = {"West Coast": 15, "Pro Style": 15, "Zone Run": 14, "Air Coryell": 12,
                "Spread Option": 10, "Power Run": 12, "Air Raid": 10, "Run and Shoot": 8,
                "Pistol": 6, "Wing-T": 1.5, "Flexbone": 1.0}
BASE_DEFENSES = {"4-3 Over": 15, "3-4 Two Gap": 14, "Cover 3": 15, "Two-High Match": 13,
                 "Press Man": 12, "Zone Blitz": 12, "Tampa 2": 11, "46 Blitz": 6}
BASE_AGGRESSION = 0.50

FOUNDING_LABEL = "Founding season"


def random_landscape(rng=random):
    """Initial conditions for a new league: neutral on average, never identical."""
    from player import ARCHETYPES
    pipeline = {g: round(rng.gauss(0.0, 2.2), 2) for g in GROUPS}
    archetypes = {}
    for pos, table in ARCHETYPES.items():
        archetypes[pos] = {name: round(math.exp(rng.gauss(0.0, 0.22)), 3) for name in table}
    schemes = {k: v * math.exp(rng.gauss(0.0, 0.30)) for k, v in BASE_SCHEMES.items()}
    defenses = {k: v * math.exp(rng.gauss(0.0, 0.30)) for k, v in BASE_DEFENSES.items()}
    return {"pipeline": pipeline, "archetypes": archetypes, "schemes": schemes,
            "defenses": defenses,
            "aggression": max(0.30, min(0.70, rng.gauss(BASE_AGGRESSION, 0.06)))}


def archetype_weights_for(landscape):
    """Full archetype weight table (base frequency x landscape multiplier)."""
    from player import ARCHETYPES
    mult = landscape["archetypes"]
    out = {}
    for pos, table in ARCHETYPES.items():
        out[pos] = {name: table[name][0] * mult.get(pos, {}).get(name, 1.0)
                    for name in table}
    return out


def adapt_coaching(league):
    """
    Coaches league-wide react to what worked last season. If passing has been
    much more efficient than running, everyone leans a little more toward the
    pass; defenses respond to a pass-happy league by playing more two-high
    zone, which in turn makes the run game efficient again. The lags in this
    loop are what make eras rise and fall.
    """
    if not league.history:
        return
    avgs = league.history[-1].get("averages") or {}
    if not avgs:
        return
    vol = 1.0
    ratio = avgs.get("ny_a", 6.0) / max(2.5, avgs.get("ypc", 4.2))
    ema = getattr(league, "ratio_ema", None) or ratio
    off_push = max(-0.09, min(0.09, (ratio - ema) * 1.1)) * vol
    league.ratio_ema = ema * 0.85 + ratio * 0.15
    pass_rate = avgs.get("pass_rate", 57.0)
    def_push = max(-0.08, min(0.08, (pass_rate - 57.5) / 100.0 * 2.0)) * vol
    conv = avgs.get("fourth_conv")
    aggr_push = 0.0
    if conv is not None and avgs.get("fourth_att", 0) > 0.2:
        aggr_push = max(-0.03, min(0.03, (conv - 50.0) / 100.0 * 0.25 + random.gauss(0, 0.006)))
    from coach import OFFENSIVE_SCHEMES, DEFENSIVE_SCHEMES
    for team in league.teams.values():
        c = team.coach
        t = c.tendencies
        learn = 0.4 + c.r("adaptability") / 20.0 * 0.6
        base_off = OFFENSIVE_SCHEMES[c.off_scheme]["pass_lean"]
        t["pass_lean"] = max(-1.0, min(1.0, t["pass_lean"] + off_push * learn))
        t["pass_lean"] = t["pass_lean"] * 0.93 + base_off * 0.07
        # 4th-down boldness follows results: if going for it keeps working around the
        # league, coaches get bolder; if it keeps failing, they go back to kicking
        t["aggression"] = max(0.0, min(1.0, t.get("aggression", 0.45) + aggr_push * learn))
        base_def = DEFENSIVE_SCHEMES[c.def_scheme]
        for key, mult in (("two_high", 1.0), ("zone", 0.6)):
            v = t.get(key, base_def[key]) + def_push * mult * learn
            t[key] = max(0.0, min(1.0, v * 0.93 + base_def[key] * 0.07))
    league.meta = {"off_push": off_push, "def_push": def_push, "ratio": ratio, "aggr_push": aggr_push}


def pipeline_shift(league, position):
    """CA shift applied to new prospects at this position."""
    return league.pipeline.get(POS_GROUP[position], 0.0)


# ── Yearly evolution ──────────────────────────────────────────────────────────

def measure_prestige(league):
    """How much of the league's fame and money each group holds right now."""
    totals = {g: 0.0 for g in GROUPS}
    players = [p for t in league.teams.values() for p in t.roster]
    players.sort(key=lambda p: -(p.reputation * 2 + p.ca))
    for p in players[:160]:
        totals[POS_GROUP[p.position]] += p.reputation + p.salary / 1_000_000.0
    tot = sum(totals.values()) or 1.0
    return {g: v / tot for g, v in totals.items()}


def _scarcity(league):
    """+ when a group's starters are well below the long-run norm, - when far above."""
    from ratings import OVR_ANCHORS
    out = {}
    for g, poss in GROUPS.items():
        diffs = []
        for t in league.teams.values():
            for pos in poss:
                mu = OVR_ANCHORS[pos][0]
                n = {"WR": 3, "OT": 2, "IOL": 3, "DT": 2, "EDGE": 2, "LB": 2, "CB": 3, "S": 2}.get(pos, 1)
                for p in t.lineup(pos, n):
                    diffs.append(mu - p.ca)
        if diffs:
            out[g] = max(-7.0, min(7.0, sum(diffs) / len(diffs) / 1.8))
    return out


def evolve(league):
    """Run once per offseason before the draft class is generated."""
    vol = 1.0
    adapt_coaching(league)
    prestige = measure_prestige(league)
    league.prestige_history.append(prestige)
    if len(league.prestige_history) > 60:
        league.prestige_history = league.prestige_history[-60:]
    base = getattr(league, "prestige_baseline", None) or dict(prestige)
    lagged = league.prestige_history[-5:-1] or league.prestige_history[-1:]
    scarcity = _scarcity(league)
    for g in GROUPS:
        share = sum(h[g] for h in lagged) / len(lagged)
        # Kids chase what is *newly* glamorous relative to the long-run norm,
        # and a scarce position means opportunity: demand rises when the
        # group's talent has fallen well below normal.
        demand = (share / max(0.005, base[g]) - 1.0) * 6.0
        demand -= league.pipeline.get(g, 0.0) * 0.35
        # When a position's talent has thinned out, starting jobs open up and
        # young athletes (and college coaches) notice
        demand += scarcity.get(g, 0.0)
        demand = max(-8.0, min(8.0, demand))
        drift = league.pipeline_drift.get(g, 0.0)
        drift = drift * 0.94 + random.gauss(0, 1.1 * vol)
        league.pipeline_drift[g] = max(-10.0, min(10.0, drift))
        target = demand * 0.6 + drift
        cur = league.pipeline.get(g, 0.0)
        new = cur * 0.82 + target * 0.18 + random.gauss(0, 1.6 * vol)
        league.pipeline[g] = max(-16.0, min(16.0, new))
    for g in GROUPS:
        base[g] = base[g] * 0.92 + prestige[g] * 0.08
    league.prestige_baseline = base

    # Archetype popularity: styles that are winning get copied by young players
    from player import ARCHETYPES
    for pos, table in ARCHETYPES.items():
        weights = league.archetype_weights.setdefault(
            pos, {n: table[n][0] for n in table})
        players = [p for t in league.teams.values() for p in t.roster
                   if p.position == pos]
        if not players:
            continue
        avg = sum(p.ca for p in players) / len(players)
        for name in table:
            members = [p for p in players if p.archetype == name]
            if members:
                top = sorted(members, key=lambda p: -p.ca)[:6]
                succ = (sum(p.ca for p in top) / len(top) - avg) / 40.0
            else:
                succ = -0.1
            base = table[name][0]
            cur = weights.get(name, base) / base
            new = cur * 0.88 + (1.0 + succ) * 0.12 + random.gauss(0, 0.05 * vol)
            weights[name] = base * max(0.3, min(3.0, new))


# ── League-wide trend measurement ─────────────────────────────────────────────

TREND_KEYS = [
    ("ppg", "Points / team game"),
    ("pass_att", "Pass attempts"),
    ("comp_pct", "Completion %"),
    ("pass_yds", "Pass yards"),
    ("ypa", "Yards / attempt"),
    ("pass_td", "Pass TD"),
    ("int_rate", "INT %"),
    ("sack_rate", "Sack %"),
    ("rush_att", "Rush attempts"),
    ("rush_yds", "Rush yards"),
    ("ypc", "Yards / carry"),
    ("rush_td", "Rush TD"),
    ("pass_rate", "Pass play %"),
    ("fg_pct", "FG %"),
    ("punt_avg", "Punt average"),
    ("plays", "Plays / team game"),
    ("third_pct", "3rd down %"),
    ("turnovers", "Turnovers"),
]


def season_averages(results):
    """Per-team-game league averages from a list of GameResults."""
    from collections import Counter
    tot = Counter()
    games = 0
    for g in results:
        for abbr in (g.home, g.away):
            ts = g.team_stats[abbr]
            tot.update(ts)
            games += 1
        for pid, line in g.player_stats.items():
            tot["_pass_td"] += line["pass_td"]
            tot["_pass_int"] += line["pass_int"]
            tot["_rush_td"] += line["rush_td"]
            tot["_fgm"] += line["fgm"]
            tot["_fga"] += line["fga"]
            tot["_punts"] += line["punts"]
            tot["_punt_yds"] += line["punt_yds"]
    if games == 0:
        return {}
    dropbacks = tot["pass_att"] + tot["sacked"]
    plays = dropbacks + tot["rush_att"]
    out = {
        "ppg": tot["points"] / games,
        "pass_att": tot["pass_att"] / games,
        "comp_pct": 100.0 * tot["pass_cmp"] / max(1, tot["pass_att"]),
        "pass_yds": tot["pass_yds"] / games,
        "ypa": tot["pass_yds"] / max(1, tot["pass_att"]),
        "pass_td": tot["_pass_td"] / games,
        "int_rate": 100.0 * tot["_pass_int"] / max(1, tot["pass_att"]),
        "sack_rate": 100.0 * tot["sacked"] / max(1, dropbacks),
        "rush_att": tot["rush_att"] / games,
        "rush_yds": tot["rush_yds"] / games,
        "ypc": tot["rush_yds"] / max(1, tot["rush_att"]),
        "rush_td": tot["_rush_td"] / games,
        "pass_rate": 100.0 * dropbacks / max(1, plays),
        "ny_a": (tot["pass_yds"] - tot["sack_yds"]) / max(1, dropbacks),
        "fg_pct": 100.0 * tot["_fgm"] / max(1, tot["_fga"]),
        "punt_avg": tot["_punt_yds"] / max(1, tot["_punts"]),
        "plays": plays / games,
        "third_pct": 100.0 * tot["third_conv"] / max(1, tot["third_att"]),
        "turnovers": tot["turnovers"] / games,
        "penalties": tot["penalties"] / games,
        "pen_yds": tot["pen_yds"] / games,
        "sacks": tot["sacked"] / games,
        "first_downs": tot["first_downs"] / games,
        "drives": tot["drives"] / games,
        "fourth_att": tot["fourth_att"] / games,
        "fourth_conv": 100.0 * tot["fourth_conv"] / max(1, tot["fourth_att"]),
        "two_att": tot["two_att"] / games,
        "two_conv": 100.0 * tot["two_conv"] / max(1, tot["two_att"]),
        "games": games // 2,
    }
    return out


def era_label(avgs):
    """A name for the style of play, judged by what actually happened."""
    if not avgs:
        return "—"
    pr = avgs["pass_rate"]
    ypc = avgs["ypc"]
    ppg = avgs["ppg"]
    comp = avgs["comp_pct"]
    if pr >= 63 and ppg >= 24:
        return "Air Raid Era"
    if pr >= 61:
        return "Passing Era"
    if pr <= 52 and ypc >= 4.3:
        return "Ground Game Era"
    if pr <= 54:
        return "Smash-Mouth Era"
    if ppg <= 20 or comp <= 57:
        return "Defensive Era"
    if ppg >= 25.5:
        return "Shootout Era"
    return "Balanced Era"
