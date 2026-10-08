import os, sys, time, random, statistics as st
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from worldgen import new_league
from season import advance
from collections import Counter

def snapshot(lg):
    starters = {"QB":[], "RB":[], "WR":[], "OL":[], "DL":[], "LB":[], "DB":[], "K":[]}
    allp = [p for t in lg.teams.values() for p in t.roster]
    for t in lg.teams.values():
        s = t.starters()
        starters["QB"] += [p.ca for p in s["QB"]]
        starters["RB"] += [p.ca for p in s["RB"]]
        starters["WR"] += [p.ca for p in s["WR"]]
        starters["OL"] += [p.ca for p in s["OT"] + s["IOL"]]
        starters["DL"] += [p.ca for p in s["DT"] + s["EDGE"]]
        starters["LB"] += [p.ca for p in s["LB"]]
        starters["DB"] += [p.ca for p in s["CB"] + s["S"]]
        starters["K"] += [p.ca for p in s["K"]]
    wc = sum(1 for p in allp if p.ca >= 180)
    q = sum(1 for p in allp if 140 <= p.ca < 180)
    age = st.mean(p.age for p in allp)
    ovr = [t.overall for t in lg.teams.values()]
    return {k: round(st.mean(v)) for k, v in starters.items()}, wc, q, round(age,1), (min(ovr), max(ovr))

def run(n=20, era=None, seed=11):
    kw = {"user_abbr": "DAL", "seed": seed}
    lg = new_league(**kw)
    s, wc, q, age, rng = snapshot(lg)
    print(f"start {lg.year}: starters {s} WC {wc} Q {q} age {age} team ovr {rng}")
    t0 = time.time()
    for i in range(n):
        while True:
            ph = lg.phase
            advance(lg)
            if ph == "season_end":
                pass
            if lg.phase == "regular" and lg.week == 0:
                break
        h = lg.history[-1]; a = h["averages"]
        s, wc, q, age, rng = snapshot(lg)
        sch = h["schemes"].most_common(2)
        print(f"{h['year']} ppg {a['ppg']:.1f} pass% {a['pass_rate']:.0f} cmp {a['comp_pct']:.1f} ypa {a['ypa']:.2f} ypc {a['ypc']:.2f} "
              f"int {a['int_rate']:.1f} fg {a['fg_pct']:.0f} {h['era'][:12]:12s}| {s} WC {wc} Q {q} age {age} ovr {rng} "
              f"| QB {lg.pipeline['QB']:+.0f} RB {lg.pipeline['RB']:+.0f} WR {lg.pipeline['WR']:+.0f} DB {lg.pipeline['DB']:+.0f} | {sch}")
    print(f"total {time.time()-t0:.0f}s")
    return lg

if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 20, sys.argv[2] if len(sys.argv) > 2 else None)
