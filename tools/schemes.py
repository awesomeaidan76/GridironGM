"""
Offensive scheme identity check: does every system play the way it should?

Puts each offensive system on a league-average team in turn and plays it
against random opponents, then prints a stat profile per system: pass rate,
depth of target, screens, play-action, RPO, shotgun, personnel, QB runs,
explosive plays, EPA per play and points.

    python tools/schemes.py [games_per_scheme] [seed]
"""
import os
import random
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import coach  # noqa: E402
from calibrate import make_league  # noqa: E402
from engine import simulate_game  # noqa: E402


def profile(games=120, seed=1):
    teams = make_league(seed)
    # the team closest to league-average strength plays every system
    avg = sum(t.overall for t in teams) / len(teams)
    me = min(teams, key=lambda t: abs(t.overall - avg))
    others = [t for t in teams if t is not me]
    keep = (me.coach.off_scheme, dict(me.coach.tendencies))
    rows = []
    for sch in coach.OFFENSIVE_SCHEMES:
        me.coach.off_scheme = sch
        me.coach.set_tendencies(noise=0.0)
        T = Counter()
        P = Counter()
        pts = 0
        for _ in range(games):
            opp = random.choice(others)
            home = random.random() < 0.5
            r = simulate_game(me, opp) if home else simulate_game(opp, me)
            T.update(r.team_stats[me.abbr])
            pts += r.score_of(me.abbr)
            for pid, line in r.player_stats.items():
                if r.player_meta[pid][2] == me.abbr:
                    P[r.player_meta[pid][1] + "_rush"] += line["rush_att"]
            for t in (me, opp):
                for p in t.roster:
                    p.injury = None
        drop = T["pass_att"] + T["sacked"]
        plays = drop + T["rush_att"]
        pers = {k.split("|")[1]: v for k, v in T.items() if isinstance(k, str) and k.startswith("pers|")}
        ptot = max(1, sum(pers.values()))
        rows.append((sch, {
            "pass%": 100 * drop / max(1, plays),
            "aDOT": T["iay"] / max(1, T["pass_att"]),
            "scr%": 100 * T["screen_att"] / max(1, T["pass_att"]),
            "PA%": 100 * T["pa_att"] / max(1, T["pass_att"]),
            "RPO/g": T["rpo_pass"] / games,
            "gun%": 100 * T["gun_snaps"] / max(1, ptot),
            "11%": 100 * pers.get("11", 0) / ptot,
            "12+%": 100 * sum(v for k, v in pers.items() if 5 - int(k[0]) - int(k[1]) <= 2) / ptot,
            "10%": 100 * pers.get("10", 0) / ptot,
            "QBrush%": 100 * P["QB_rush"] / max(1, T["rush_att"]),
            "EPA/pl": T["epa"] / max(1, T["epa_plays"]),
            "ppg": pts / games,
            "plays": plays / games,
        }))
    me.coach.off_scheme, me.coach.tendencies = keep
    cols = list(rows[0][1])
    print(f"{'system':14s}" + "".join(f"{c:>8s}" for c in cols))
    for sch, d in rows:
        print(f"{sch:14s}" + "".join(f"{d[c]:8.2f}" if c == "EPA/pl" else f"{d[c]:8.1f}" for c in cols))
    return rows


if __name__ == "__main__":
    random.seed(int(sys.argv[2]) if len(sys.argv) > 2 else 1)
    profile(int(sys.argv[1]) if len(sys.argv) > 1 else 120, int(sys.argv[2]) if len(sys.argv) > 2 else 1)
