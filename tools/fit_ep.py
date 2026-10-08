"""
Fit the expected-points model in advanced.py to the match engine itself.

For every scrimmage snap it records down, distance and field position, then
looks ahead to the next score in the same half ("next score" expected
points). A least-squares fit of
    EP = f(yard line) + down_adj[down] + togo_coef[down] * (togo - 10)
with f piecewise-linear on the knots in advanced._EP_POINTS gives the
constants to paste into advanced.py. Re-run after big engine changes.

    python tools/fit_ep.py [games]
"""
import os
import random
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import advanced  # noqa: E402
import engine  # noqa: E402
from calibrate import make_league  # noqa: E402

KNOTS = [x for x, _ in advanced._EP_POINTS]


def collect(games):
    rows = []
    cur = []
    orig = engine.GameSim._ep_pre

    def rec(self):
        side = self.poss
        half = 1 if self.quarter <= 2 else 2 if self.quarter <= 4 else 3
        cur.append((half, side is self.home, self.down, self.togo, self.yl,
                    self.home.score, self.away.score))
        return orig(self)

    engine.GameSim._ep_pre = rec
    teams = make_league(7)
    for _ in range(games):
        cur.clear()
        h, a = random.sample(teams, 2)
        r = engine.simulate_game(h, a, keep_pbp=False)
        for t in (h, a):
            for p in t.roster:
                p.injury = None
        final = (9, None, 0, 0, 0, r.home_score, r.away_score)    # end-of-game sentinel
        seq = cur + [final]
        for i, (half, home_ball, down, togo, yl, hs, as_) in enumerate(seq[:-1]):
            val = 0.0
            for nh, _, _, _, _, hs2, as2 in seq[i + 1:]:
                if (hs2, as2) != (hs, as_):
                    # the score changed after this snap (a change first seen in the
                    # next half came from the last play of this one)
                    dh, da = hs2 - hs, as2 - as_
                    val = (dh - da) if home_ball else (da - dh)
                    break
                if nh != half:
                    break
            rows.append((down, min(togo, 25), yl, val))
    engine.GameSim._ep_pre = orig
    return rows


def design(down, togo, yl):
    x = np.zeros(len(KNOTS) + 3 + 4)
    # piecewise-linear basis (hat functions)
    for k in range(len(KNOTS)):
        x0 = KNOTS[k - 1] if k > 0 else None
        x1 = KNOTS[k]
        x2 = KNOTS[k + 1] if k + 1 < len(KNOTS) else None
        if x0 is not None and x0 <= yl <= x1:
            x[k] = (yl - x0) / (x1 - x0)
        elif x2 is not None and x1 <= yl <= x2:
            x[k] = (x2 - yl) / (x2 - x1)
        elif yl == x1:
            x[k] = 1.0
    n = len(KNOTS)
    if down >= 2:
        x[n + down - 2] = 1.0
    x[n + 3 + down - 1] = togo - 10
    return x


def main():
    games = int(sys.argv[1]) if len(sys.argv) > 1 else 2500
    rows = collect(games)
    X = np.array([design(d, t, y) for d, t, y, _ in rows])
    yv = np.array([v for *_, v in rows])
    coef, *_ = np.linalg.lstsq(X, yv, rcond=None)
    n = len(KNOTS)
    print(f"{len(rows)} snaps from {games} games")
    print("_EP_POINTS = [" + ", ".join(f"({k}, {coef[i]:.2f})" for i, k in enumerate(KNOTS)) + "]")
    print("DOWN_ADJ = {1: 0.0, " + ", ".join(f"{d}: {coef[n + d - 2]:.2f}" for d in (2, 3, 4)) + "}")
    print("TOGO_COEF = {" + ", ".join(f"{d}: {coef[n + 3 + d - 1]:.3f}" for d in (1, 2, 3, 4)) + "}")


if __name__ == "__main__":
    main()
