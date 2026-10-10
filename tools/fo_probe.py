"""
Front-office AI checks: can the user fleece CPU clubs, and do fair deals still go through?

  python tools/fo_probe.py [seed]

For every CPU club it tries:
  * star for depth  - 2-3 of the user's 72-79 OVR non-QBs for the club's most valuable player,
                      if he is a star (84+ OVR)
  * QB for depth    - the same packages for the club's starting QB, if he is 78+ OVR
  * fair swap       - one of the user's players worth ~1.3x (neutral value) a similar-level player of theirs
and prints how many clubs said yes. A smart league should refuse the first two and accept most of the third.

  python tools/fo_probe.py [seed] [--iq 0.5] --season

also plays one season and offseason and reports the CPU front offices' year: trades, young stars
lost in re-signing, early extensions, and payroll as a share of the cap when camp opens.
"""
import os, sys, itertools, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from worldgen import new_league
import trades


def run(seed=7, user="DAL", quiet=False):
    t0 = time.time()
    lg = new_league(user_abbr=user, seed=seed)
    me = lg.teams[user]
    pool = sorted([p for p in me.roster if p.position not in ("QB", "K", "P") and 72 <= p.ovr <= 79],
                  key=lambda p: -trades.trade_value(p, lg, None))[:9]
    combos = [list(c) for k in (2, 3) for c in itertools.combinations(pool, k)]
    star = qb = fair = fair_n = stars = qbs = 0
    for t in lg.teams.values():
        if t.abbr == user:
            continue
        best = max(t.roster, key=lambda p: trades.trade_value(p, lg, None))
        if best.ovr >= 84:
            stars += 1
            if any(trades.evaluate(lg, me, t, c, [best])[0] for c in combos):
                star += 1
        q = t.starters()["QB"][0] if t.starters().get("QB") else None
        if q is not None and q.ovr >= 78:
            qbs += 1
            if any(trades.evaluate(lg, me, t, c, [q])[0] for c in combos):
                qb += 1
        # a fair-ish swap: one of theirs (66-82 OVR, not their QB) for one of ours worth ~1.3x
        theirs = [p for p in t.roster if p.position != "QB" and 66 <= p.ovr <= 82]
        for y in sorted(theirs, key=lambda p: -p.ovr)[:3]:
            vy = trades.trade_value(y, lg, None)
            mine = [x for x in me.roster if x.position == y.position and x.position != "QB"]
            mine = [x for x in mine if 1.2 * vy <= trades.trade_value(x, lg, None) <= 1.6 * vy + 1]
            if not mine:
                continue
            fair_n += 1
            if trades.evaluate(lg, me, t, [mine[0]], [y])[0]:
                fair += 1
            break
    out = {"star_for_depth": star, "stars": stars, "qb_for_depth": qb, "qbs": qbs, "fair_accepted": fair,
           "fair_tried": fair_n, "secs": round(time.time() - t0, 1)}
    if not quiet:
        print(f"seed {seed}: star-for-depth accepted by {star}/{stars} clubs, QB-for-depth {qb}/{qbs}, "
              f"fair swaps {fair}/{fair_n}  ({out['secs']}s)")
    return out


def season(seed=7, user="DAL"):
    from season import advance
    import statistics as st
    t0 = time.time()
    import market
    lg = new_league(user_abbr=user, seed=seed)
    count = {"trades": 0}
    orig = trades.execute

    def counted(*a, **k):
        count["trades"] += 1
        return orig(*a, **k)
    trades.execute = market.execute = counted
    news0 = len(lg.news)
    lost, kept = [], 0
    while True:
        ph = lg.phase
        if ph == "resign":
            exp = {p.id: (t.abbr, p) for t in lg.teams.values() if t.abbr != user
                   for p in t.roster if p.contract and p.contract["years"] <= 0}
        advance(lg)
        if ph == "resign":
            for pid, (ab, p) in exp.items():
                if p.team == ab:
                    kept += 1
                elif p.age <= 27 and p.ovr >= 82:
                    lost.append(f"{ab} {p.position} {p.name} {p.age}y {p.ovr}")
        if lg.phase == "preseason":
            break
    pay = [t.payroll / lg.salary_cap * 100 for t in lg.teams.values() if t.abbr != user]
    trades.execute = market.execute = orig
    ext = len([n for n in lg.news[news0:] if "extension" in str(n).lower()])
    print(f"seed {seed} season: {count['trades']} trades, kept {kept} expiring, young 82+ stars lost {len(lost)}, "
          f"extension news {ext}, CPU payroll {min(pay):.0f}-{max(pay):.0f}% of cap (median {st.median(pay):.0f}%)"
          f"  ({time.time() - t0:.0f}s)")
    for x in lost[:8]:
        print("   lost:", x)
    import front_office as fo
    low = min((t for t in lg.teams.values() if t.abbr != user), key=lambda t: t.payroll)
    print(f"   lowest payroll: {low.abbr} ({fo.plan_of(low)}) {low.payroll / lg.salary_cap * 100:.0f}% "
          f"with {len(low.roster)} players")
    return lg


if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 7
    if "--iq" in sys.argv:                 # --iq 0.5 tries the probe at another difficulty
        from settings import settings
        settings._data["cpu_intelligence"] = float(sys.argv[sys.argv.index("--iq") + 1])
    run(seed)
    if "--season" in sys.argv:
        season(seed)
