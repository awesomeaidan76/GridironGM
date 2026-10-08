"""
Usage & distribution report: who gets the ball, and do individual stat lines
look like the NFL? Simulates full regular seasons and compares against
real-world ranges.

    python tools/usage.py [seasons] [era-prefix]
"""
import os
import random
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from season import advance  # noqa: E402
from worldgen import new_league  # noqa: E402

# Typical NFL ranges, roughly 2000-2024 (per 17-game-equivalent season, 32 teams)
TARGETS = {
    "RB1 share of team rushes": (0.46, 0.58),
    "RB2 share of team rushes": (0.15, 0.25),
    "QB share of team rushes": (0.10, 0.17),
    "Median RB1 carries": (205, 260),
    "Max carries": (310, 390),
    "1000-yd rushers": (9, 18),
    "Rush yds leader": (1450, 2000),
    "WR1 target share": (0.21, 0.27),
    "TE1 target share": (0.13, 0.19),
    "RB target share": (0.14, 0.21),
    "1000-yd receivers": (14, 26),
    "Rec leader receptions": (115, 150),
    "Rec yds leader": (1500, 1850),
    "4000-yd passers": (3, 10),
    "Pass yds leader": (4500, 5300),
    "Pass TD leader": (33, 45),
    "Sack leader": (14, 20),
    "INT leader": (6, 10),
}


def season_report(lg):
    teams = list(lg.teams.values())
    ps = [p for t in teams for p in t.roster] + list(lg.free_agents)
    ps = [p for p in ps if p.season_stats.get("gp")]
    out = {}
    rb1s, rb2s, qbs, wr1, te1, rbt, rb1_att = [], [], [], [], [], [], []
    for t in teams:
        mine = [p for p in ps if p.team == t.abbr]
        tot_r = sum(p.season_stats["rush_att"] for p in mine) or 1
        tot_t = sum(p.season_stats["targets"] for p in mine) or 1
        rbs = sorted([p for p in mine if p.position == "RB"], key=lambda p: -p.season_stats["rush_att"])
        rb1s.append(rbs[0].season_stats["rush_att"] / tot_r if rbs else 0)
        rb2s.append(rbs[1].season_stats["rush_att"] / tot_r if len(rbs) > 1 else 0)
        rb1_att.append(rbs[0].season_stats["rush_att"] if rbs else 0)
        qbs.append(sum(p.season_stats["rush_att"] for p in mine if p.position == "QB") / tot_r)
        wrs = sorted([p for p in mine if p.position == "WR"], key=lambda p: -p.season_stats["targets"])
        tes = sorted([p for p in mine if p.position == "TE"], key=lambda p: -p.season_stats["targets"])
        wr1.append(wrs[0].season_stats["targets"] / tot_t if wrs else 0)
        te1.append(tes[0].season_stats["targets"] / tot_t if tes else 0)
        rbt.append(sum(p.season_stats["targets"] for p in mine if p.position in ("RB", "FB")) / tot_t)

    def mx(k):
        return max(p.season_stats[k] for p in ps)
    out["RB1 share of team rushes"] = st.mean(rb1s)
    out["RB2 share of team rushes"] = st.mean(rb2s)
    out["QB share of team rushes"] = st.mean(qbs)
    out["Median RB1 carries"] = st.median(rb1_att)
    out["Max carries"] = mx("rush_att")
    out["1000-yd rushers"] = sum(p.season_stats["rush_yds"] >= 1000 for p in ps)
    out["Rush yds leader"] = mx("rush_yds")
    out["WR1 target share"] = st.mean(wr1)
    out["TE1 target share"] = st.mean(te1)
    out["RB target share"] = st.mean(rbt)
    out["1000-yd receivers"] = sum(p.season_stats["rec_yds"] >= 1000 for p in ps)
    out["Rec leader receptions"] = mx("rec")
    out["Rec yds leader"] = mx("rec_yds")
    out["4000-yd passers"] = sum(p.season_stats["pass_yds"] >= 4000 for p in ps)
    out["Pass yds leader"] = mx("pass_yds")
    out["Pass TD leader"] = mx("pass_td")
    out["Sack leader"] = mx("sacks")
    out["INT leader"] = mx("def_int")
    return out


def team_spread(lg):
    """Points-per-game spread between teams and blowout / close-game rates."""
    games = [g for g in lg.all_results() if not g.playoff]
    margins = [abs(g.home_score - g.away_score) for g in games]
    ppg = {}
    for g in games:
        for ab in (g.home, g.away):
            ppg.setdefault(ab, []).append(g.score_of(ab))
    team_ppg = [st.mean(v) for v in ppg.values()]
    scores = [s for v in ppg.values() for s in v]
    wins = sorted((r.w for r in lg.standings.values()), reverse=True)
    return {
        "team ppg range": f"{min(team_ppg):.1f}-{max(team_ppg):.1f}",
        "score sd": f"{st.pstdev(scores):.1f}",
        "one-score games": f"{sum(m <= 8 for m in margins) / len(margins):.0%}",
        "blowouts 21+": f"{sum(m >= 21 for m in margins) / len(margins):.0%}",
        "40+ point games": f"{sum(s >= 40 for s in scores) / len(scores):.1%}",
        "held to <=10": f"{sum(s <= 10 for s in scores) / len(scores):.1%}",
        "best/worst record": f"{wins[0]}/{wins[-1]} wins",
        "home win %": f"{sum(g.home_score > g.away_score for g in games) / len(games):.3f}",
        "margin per pt of edge": _slope(games),
        "favourite wins": _fav(games, 0.0),
        "7+ pt favourite wins": _fav(games, 7.0),
    }


def _slope(games):
    xs = [getattr(g, "pre_edge", 0.0) for g in games]
    ys = [g.home_score - g.away_score for g in games]
    mx, my = st.mean(xs), st.mean(ys)
    vx = sum((x - mx) ** 2 for x in xs) or 1.0
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / vx
    resid = st.pstdev([y - (my + b * (x - mx)) for x, y in zip(xs, ys)])
    return f"{b:.2f} (resid sd {resid:.1f})"


def _fav(games, edge):
    gs = [g for g in games if abs(getattr(g, "pre_edge", 0.0)) >= max(0.5, edge) and g.winner]
    if not gs:
        return "-"
    won = sum(1 for g in gs if (g.pre_edge > 0) == (g.winner == g.home))
    return f"{won / len(gs):.0%} of {len(gs)}"


def run(seasons=2, seed=5):
    random.seed(seed)
    lg = new_league(user_abbr="DAL", seed=seed)
    reports, spreads = [], []
    for _ in range(seasons):
        while lg.phase in ("preseason",):
            advance(lg)
        while lg.phase == "regular":
            advance(lg)
        reports.append(season_report(lg))
        spreads.append(team_spread(lg))
        if _ < seasons - 1:
            while not (lg.phase == "regular" and lg.week == 0):
                advance(lg)
    print(f"seed {seed} — {seasons} season(s)")
    for k, (lo, hi) in TARGETS.items():
        vals = [r[k] for r in reports]
        v = st.mean(vals)
        ok = "OK " if lo <= v <= hi else "<--"
        fmt = (lambda x: f"{x:.3f}") if isinstance(lo, float) else (lambda x: f"{x:.0f}")
        print(f"  {ok} {k:26s} {fmt(v):>7s}   target {fmt(lo)}-{fmt(hi)}   "
              f"[{', '.join(fmt(x) for x in vals)}]")
    for k in spreads[0]:
        print(f"      {k:26s} {' | '.join(s[k] for s in spreads)}")
    return lg


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    run(n, seed)
