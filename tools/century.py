"""
The 100-season test: simulate a league for a century, headless, and record how
it evolves - scoring and style, talent levels, schemes, coaching trends, rule
changes, parity and dynasties, the salary cap, rosters, the record book, and
how long each season takes to simulate.

    python tools/century.py [seasons] [seed] [out.jsonl]

One JSON line per season goes to the output file (default
century_<seed>.jsonl); a summary is printed at the end. Run
`python tools/century.py --report file.jsonl` to summarise an existing run.
"""
import json
import os
import pickle
import random
import statistics as st
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from season import advance  # noqa: E402
from worldgen import new_league  # noqa: E402
import records  # noqa: E402

AVG_KEYS = ("ppg", "pass_rate", "pass_att", "comp_pct", "ypa", "ypc", "int_rate", "sack_rate", "fg_pct",
            "plays", "third_pct", "fourth_att", "fourth_conv", "two_att", "turnovers")
RECORD_KEYS = ("pass_yds", "pass_td", "rush_yds", "rec_yds", "rec", "sacks", "def_int")


def snapshot(lg, secs, prev_records):
    h = lg.history[-1]
    a = h.get("averages") or {}
    players = [p for t in lg.teams.values() for p in t.roster]
    ovrs = [p.ovr for p in players]
    elite = Counter(p.position for p in players if p.ovr >= 90)
    team_ovr = [t.overall for t in lg.teams.values()]
    cap = lg.salary_cap
    over_cap = sum(1 for t in lg.teams.values() if t.payroll > cap)
    space = [t.cap_space(cap) / cap for t in lg.teams.values()]
    off_s = Counter(t.coach.off_scheme for t in lg.teams.values())
    def_s = Counter(t.coach.def_scheme for t in lg.teams.values())
    aggr = [t.coach.tendencies.get("aggression", 0.45) for t in lg.teams.values()]
    lean = [t.coach.tendencies.get("pass_lean", 0.0) for t in lg.teams.values()]
    tops = records.season_records(lg, 1, include_current=False)
    broken = [k for k in RECORD_KEYS
              if tops.get(k) and prev_records.get(k) and tops[k][0][0] > prev_records[k]]
    for k in RECORD_KEYS:
        if tops.get(k):
            prev_records[k] = tops[k][0][0]
    trades = sum(1 for y, _w, txt in lg.transactions if y == h["year"] and "trade" in txt.lower())
    mvp = (h.get("awards") or {}).get("MVP") or {}
    return {
        "year": h["year"], "secs": round(secs, 1), "era": h.get("era", ""),
        "avg": {k: round(a.get(k, 0.0), 3) for k in AVG_KEYS},
        "champion": h.get("champion"), "best": (h.get("best_record") or ("", ""))[0],
        "mvp_pos": mvp.get("pos"),
        "n90": sum(o >= 90 for o in ovrs), "n85": sum(o >= 85 for o in ovrs),
        "ovr_mean": round(st.mean(ovrs), 2), "elite_pos": dict(elite),
        "team_ovr_sd": round(st.pstdev(team_ovr), 2), "team_ovr_range": round(max(team_ovr) - min(team_ovr), 1),
        "over_cap": over_cap, "cap_space_mean": round(st.mean(space), 3),
        "dead_cap_mean": round(st.mean(t.dead_cap for t in lg.teams.values()) / cap, 4),
        "roster_mean": round(st.mean(len(t.roster) for t in lg.teams.values()), 1),
        "age_mean": round(st.mean(p.age for p in players), 2),
        "fa_pool": len(lg.free_agents), "retired": len(lg.retired), "hof": len(lg.hall_of_fame),
        "off_schemes": dict(off_s), "def_schemes": dict(def_s),
        "aggr_mean": round(st.mean(aggr), 3), "pass_lean_mean": round(st.mean(lean), 3),
        "pipeline": {k: round(v, 2) for k, v in lg.pipeline.items()},
        "rules": dict(getattr(lg, "rules", {}) or {}),
        "records_broken": broken, "trades": trades,
        "holdouts": sum(1 for p in players if getattr(p, "holdout", False)),
    }


def run(seasons=100, seed=11, out=None):
    random.seed(seed)
    out = out or f"century_{seed}.jsonl"
    lg = new_league(seed=seed)
    prev = {}
    with open(out, "w", encoding="utf-8") as f:
        for s in range(seasons):
            t0 = time.time()
            start = lg.year
            guard = 0
            while True:
                advance(lg)
                guard += 1
                if (lg.phase == "regular" and lg.week == 0 and lg.year > start) or guard > 400:
                    break
            row = snapshot(lg, time.time() - t0, prev)
            if (s + 1) % 10 == 0:
                row["save_kb"] = len(pickle.dumps(lg, protocol=pickle.HIGHEST_PROTOCOL)) // 1024
            f.write(json.dumps(row) + "\n")
            f.flush()
            print(f"{row['year']} {row['secs']:5.1f}s ppg {row['avg']['ppg']:.1f} pass {row['avg']['pass_rate']:.1f}% "
                  f"ypc {row['avg']['ypc']:.2f} 90+ {row['n90']} champ {row['champion']} {row['era']}",
                  flush=True)
    report(out)
    return lg


def report(path):
    rows = [json.loads(line) for line in open(path, encoding="utf-8")]
    n = len(rows)
    print(f"\n=== {path}: {n} seasons ({rows[0]['year']}-{rows[-1]['year']}) ===")

    def series(fn):
        return [fn(r) for r in rows]

    def band(name, vals, fmt="{:.1f}"):
        dec = [st.mean(vals[i:i + 10]) for i in range(0, len(vals), 10)]
        print(f"{name:22s} min {fmt.format(min(vals))} max {fmt.format(max(vals))} mean {fmt.format(st.mean(vals))}"
              f" | by decade: " + " ".join(fmt.format(d) for d in dec))
    for k in ("ppg", "pass_rate", "ypa", "ypc", "comp_pct", "int_rate", "sack_rate", "fg_pct", "plays",
              "fourth_att", "two_att"):
        band(k, series(lambda r, k=k: r["avg"][k]), "{:.2f}" if k in ("ypa", "ypc", "fourth_att", "two_att") else "{:.1f}")
    band("90+ players", series(lambda r: r["n90"]), "{:.0f}")
    band("85+ players", series(lambda r: r["n85"]), "{:.0f}")
    band("mean OVR", series(lambda r: r["ovr_mean"]))
    band("team OVR spread (sd)", series(lambda r: r["team_ovr_sd"]))
    band("teams over cap", series(lambda r: r["over_cap"]), "{:.0f}")
    band("mean age", series(lambda r: r["age_mean"]))
    band("coach aggression", series(lambda r: r["aggr_mean"]), "{:.2f}")
    band("coach pass lean", series(lambda r: r["pass_lean_mean"]), "{:.2f}")
    band("trades / season", series(lambda r: r["trades"]), "{:.0f}")
    band("holdouts", series(lambda r: r["holdouts"]), "{:.0f}")
    band("secs / season", series(lambda r: r["secs"]))
    champs = Counter(r["champion"] for r in rows)
    print(f"champions: {len(champs)} different teams; most titles {champs.most_common(5)}")
    # dynasties: titles in any 10-season window
    best_window = max((Counter(r["champion"] for r in rows[i:i + 10]).most_common(1)[0]
                       for i in range(0, max(1, n - 9))), key=lambda c: c[1])
    print(f"biggest dynasty: {best_window[0]} with {best_window[1]} titles in 10 seasons")
    repeat = sum(1 for a, b in zip(rows, rows[1:]) if a["champion"] == b["champion"])
    print(f"back-to-back titles: {repeat}")
    eras = Counter(r["era"] for r in rows)
    print(f"eras: {dict(eras)}")
    changes = sum(1 for a, b in zip(rows, rows[1:]) if a["era"] != b["era"])
    print(f"era changes: {changes}")
    mvp = Counter(r["mvp_pos"] for r in rows)
    print(f"MVP by position: {dict(mvp)}")
    rb = Counter(k for r in rows for k in r["records_broken"])
    print(f"single-season records broken: {dict(rb)} (total {sum(rb.values())})")
    first, last = rows[0], rows[-1]
    print(f"offensive systems: start {first['off_schemes']}")
    print(f"                   end   {last['off_schemes']}")
    print(f"defensive systems: start {first['def_schemes']}")
    print(f"                   end   {last['def_schemes']}")
    print(f"rules at end: {last['rules']}")
    print(f"pipeline at end: {last['pipeline']}")
    sizes = [(r["year"], r["save_kb"]) for r in rows if "save_kb" in r]
    print(f"save size (KB): {sizes}")


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--report":
        report(sys.argv[2])
    else:
        run(int(sys.argv[1]) if len(sys.argv) > 1 else 100, int(sys.argv[2]) if len(sys.argv) > 2 else 11,
            sys.argv[3] if len(sys.argv) > 3 else None)
