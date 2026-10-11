"""
Substitutions over one regular season.

    python tools/subs_probe.py [seed]

Prints snap shares by depth-chart place (league-wide and by head-coach rotation style),
backup quarterback snaps (blowouts), injuries and knocks per game, how many questionable
players played, and how many players finished the season with a heavy workload.
"""
import os
import random
import sys
import time
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from worldgen import new_league
from season import advance
import front_office as fo

try:
    import substitutions as sub
except ImportError:          # an older build, for before/after comparisons
    sub = None

PLACES = (("DT", 0), ("DT", 1), ("DT", 2), ("EDGE", 0), ("EDGE", 2), ("LB", 0), ("LB", 2), ("CB", 0),
          ("CB", 3), ("S", 0), ("S", 2), ("WR", 0), ("WR", 2), ("WR", 3), ("TE", 0), ("TE", 1),
          ("RB", 0), ("RB", 1))
DEF = ("DT", "EDGE", "LB", "CB", "S")


def main(seed):
    random.seed(seed)
    lg = new_league(user_abbr=None, seed=seed)
    played_hurt = Counter()
    prep = getattr(fo, "game_week_prep", None)
    if prep is not None:
        def counted(lg_, playing, playoff=False):
            prep(lg_, playing, playoff)
            for a in playing:
                played_hurt["flagged"] += sum(1 for p in lg_.teams[a].roster
                                              if p.injury and p.injury.get("play"))
        fo.game_week_prep = counted
    # depth places at kickoff of each game: take them from the week before
    shares = defaultdict(list)
    by_style = defaultdict(list)
    t0 = time.time()
    while lg.phase != "regular":
        advance(lg)
    weeks = len(lg.schedule)
    while lg.phase == "regular":
        places = {}
        for t in lg.teams.values():
            for pos, i in PLACES:
                d = t.depth(pos)
                if len(d) > i:
                    places[(t.abbr, pos, i)] = d[i].id
        week = lg.week
        advance(lg)
        for res in lg.results.get(week, []):
            for abbr in (res.home, res.away):
                ts = res.team_stats[abbr]
                plays = {"off": 0, "def": 0}
                for pid, line in res.player_stats.items():
                    if res.player_meta[pid][2] == abbr:
                        plays["off"] = max(plays["off"], line["off_snaps"])
                        plays["def"] = max(plays["def"], line["def_snaps"])
                style = sub.coach_rotation(lg.teams[abbr].coach) if sub else "-"
                for pos, i in PLACES:
                    pid = places.get((abbr, pos, i))
                    if pid is None:
                        continue
                    line = res.player_stats.get(pid)
                    unit = "def" if pos in DEF else "off"
                    if not plays[unit]:
                        continue
                    sh = (line[unit + "_snaps"] if line else 0) / plays[unit]
                    shares[(pos, i)].append(sh)
                    by_style[(style, pos, i)].append(sh)
    games = [r for w in range(weeks) for r in lg.results.get(w, [])]
    print(f"{len(games)} games in {time.time() - t0:.0f}s")
    print("Snap share by depth place (share of the unit's snaps, mean over games):")
    print("  " + "  ".join(f"{pos}{i + 1} {sum(v) / len(v):.0%}" for (pos, i), v in shares.items()))
    if sub:
        print("By the head coach's rotation style:")
        for style in sub.ROTATION_STYLES:
            cells = []
            for pos, i in PLACES:
                v = by_style.get((style, pos, i))
                if v:
                    cells.append(f"{pos}{i + 1} {sum(v) / len(v):.0%}")
            n = sum(1 for t in lg.teams.values() if sub.coach_rotation(t.coach) == style)
            print(f"  {style} ({n} clubs): " + "  ".join(cells))
    qb2 = 0
    for r in games:
        for pid, line in r.player_stats.items():
            if r.player_meta[pid][1] == "QB" and pid not in r.starters and line["pass_att"]:
                qb2 += line["pass_att"]
    inj = sum(len(r.injuries) for r in games)
    knocks = sum(1 for r in games for i in r.injuries if i[4] <= 0)
    back = sum(len(getattr(r, "returned", ())) for r in games)
    print(f"Backup QB passes per game: {qb2 / len(games):.2f}")
    print(f"Injuries per team-game {inj / (2 * len(games)):.2f}; knocks {knocks} ({back} went back in)")
    if prep is not None:
        print(f"Questionable starters who played: {played_hurt['flagged']}")
    loads = Counter()
    for t in lg.teams.values():
        for p in t.roster:
            ld = getattr(p, "load", 0.0)
            if ld >= 10:
                loads[(p.position, "worn" if ld >= 22 else "heavy")] += 1
    if loads:
        print("Heavy workload at the end of the regular season: "
              + ", ".join(f"{pos} {kind} {n}" for (pos, kind), n in sorted(loads.items())))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 7)
