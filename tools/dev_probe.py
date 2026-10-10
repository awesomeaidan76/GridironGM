"""
Development and potential over a few real seasons.

    python tools/dev_probe.py [seasons] [seed]

Prints, for a new league advanced season by season: league talent (players 90+, 82+, 74+ and the
mean OVR of 26-30 year olds), POT minus OVR by age for non-quarterbacks, the yearly OVR change by
age, and how often young players reach their ceiling (the hidden potential POT shows): Football GM
treats potential as the 75th percentile of a player's peak, so about a quarter to a third should.
"""
import math
import os
import random
import sys
import time
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from worldgen import new_league
from season import advance


def snapshot(lg):
    """{id: (age, position, ca, pa, years to peak, ovr, pot, rostered)} for rostered players and free agents."""
    d = {}
    for t in lg.teams.values():
        for p in t.roster:
            d[p.id] = (p.age, p.position, p.ca, p.pa, p.years_to_peak(), p.ovr, p.pot, True)
    for p in lg.free_agents:
        d[p.id] = (p.age, p.position, p.ca, p.pa, p.years_to_peak(), p.ovr, p.pot, False)
    return d


def report(snaps):
    print("season  90+  82+  74+  OVR 26-30 | non-QB POT-OVR at 21 22 23 24 25 26")
    for i, s in enumerate(snaps):
        v = [x for x in s.values() if x[7] and x[1] not in ("K", "P")]
        prime = [x[5] for x in v if 26 <= x[0] <= 30]
        gaps = []
        for age in range(21, 27):
            g = [x[6] - x[5] for x in v if x[0] == age and x[1] != "QB"]
            gaps.append(sum(g) / len(g) if g else 0.0)
        print(f"  {i:4d} {sum(1 for x in v if x[5] >= 90):4d} {sum(1 for x in v if x[5] >= 82):4d} "
              f"{sum(1 for x in v if x[5] >= 74):4d}   {sum(prime) / max(1, len(prime)):5.1f}   |"
              + "".join(f" {g:5.1f}" for g in gaps))
    ch = defaultdict(list)
    for a, b in zip(snaps[1:], snaps[2:]):
        for pid, x in a.items():
            y = b.get(pid)
            if x[7] and y and y[1] == x[1] and x[1] not in ("K", "P"):
                ch[("QB" if x[1] == "QB" else "other", min(x[0], 33))].append(y[5] - x[5])
    print("Yearly OVR change by age (mean):")
    for g in ("other", "QB"):
        print(f"  {g:5s}" + "".join(f" {a}:{sum(v) / len(v):+.1f}" for a in range(21, 34)
                                    for v in [ch.get((g, a), [])] if len(v) >= 5))
    # ceiling vs the peak actually reached, for young players with enough seasons left to see it
    rows = defaultdict(list)
    last = len(snaps) - 1
    for i, s in enumerate(snaps[:-1]):
        for pid, x in s.items():
            if x[1] in ("K", "P") or x[4] <= 0.5 or last - i < math.ceil(x[4]) + 1:
                continue
            later = [snaps[j][pid] for j in range(i + 1, last + 1) if pid in snaps[j]]
            if any(y[1] != x[1] for y in later):
                continue
            peak = max([x[2]] + [y[2] for y in later])
            rows[min(5, int(round(x[4])))].append(peak >= x[3])
    print("Share of young players who reach their ceiling, by years left before the peak:")
    print("  " + "  ".join(f"{k}y {sum(v) / len(v):.0%} (n {len(v)})" for k, v in sorted(rows.items())))


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    random.seed(seed)
    lg = new_league(user_abbr="DAL", seed=seed)
    snaps = [snapshot(lg)]
    for s in range(n):
        t0 = time.time()
        while True:
            advance(lg)
            if lg.phase == "regular" and lg.week == 0:
                break
        snaps.append(snapshot(lg))
        print(f"season {s + 1}/{n} in {time.time() - t0:.0f}s", flush=True)
    report(snaps)
