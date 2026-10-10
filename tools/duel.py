"""Difficulty check: the same clubs, with one staff sharper than the other.

Each pairing is played twice with the sides' CPU intelligence swapped, so the
rosters, home field and luck even out and only the staffs' decisions differ.

    python tools/duel.py [games] [seed] [high_iq] [low_iq]
"""
import os, sys, random, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from calibrate import make_league
from engine import simulate_game
import gameday


def run(games=300, seed=1, hi=2.0, lo=1.0):
    teams = make_league(seed)
    film = {t.abbr: [] for t in teams}
    wins = ties = 0
    margin = 0.0
    t0 = time.time()
    for i in range(games):
        h, a = random.sample(teams, 2)
        for sharp in (h, a):
            iq = {t.abbr: (hi if t is sharp else lo) for t in (h, a)}
            r = simulate_game(h, a, keep_pbp=False, iq=iq,
                              scouting={h.abbr: film[h.abbr], a.abbr: film[a.abbr]})
            own, other = r.score_of(sharp.abbr), r.score_of((a if sharp is h else h).abbr)
            margin += own - other
            wins += own > other
            ties += own == other
            for t in (h, a):
                for p in t.roster:
                    p.injury = None
        for ab in (h.abbr, a.abbr):
            film[ab] = (film[ab] + [r])[-6:]
    n = 2 * games
    print(f"seed {seed}: {gameday.level_name(hi)} ({hi}) vs {gameday.level_name(lo)} ({lo}), {n} games "
          f"in {time.time() - t0:.0f}s")
    print(f"  sharper staff wins {(wins + ties / 2) / n:.3f}, average margin {margin / n:+.2f} points")
    return (wins + ties / 2) / n, margin / n


if __name__ == "__main__":
    a = sys.argv[1:]
    run(int(a[0]) if a else 300, int(a[1]) if len(a) > 1 else 1,
        float(a[2]) if len(a) > 2 else 2.0, float(a[3]) if len(a) > 3 else 1.0)
