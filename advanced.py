"""
advanced.py — expected points, EPA and other advanced-stat formulas.

No UI code. The expected-points table is a smooth model of the points the
team with the ball can expect to score next from a given down, distance and
field position (NFL-like values). EPA for a play is the change in expected
points it caused; a play is a "success" when its EPA is positive.
"""

# 1st-and-10 expected points by yards from the offense's own goal line.
# Fitted to the match engine with tools/fit_ep.py ("next score" method), then
# lightly smoothed near the goal lines where samples are thin.
_EP_POINTS = [(1, -0.75), (5, -0.35), (10, 0.0), (20, 0.55), (25, 0.78), (30, 1.15), (40, 1.78),
              (50, 2.35), (60, 2.98), (70, 3.68), (80, 4.45), (85, 4.78), (90, 5.05), (95, 5.5),
              (99, 6.0)]
DOWN_ADJ = {1: 0.0, 2: -0.57, 3: -1.36, 4: -2.32}
TOGO_COEF = {1: -0.056, 2: -0.089, 3: -0.095, 4: -0.095}
KICKOFF_EP = 0.65            # what the receiving team expects after a kickoff


def _interp(yl):
    yl = max(1.0, min(99.0, float(yl)))
    for (x0, y0), (x1, y1) in zip(_EP_POINTS, _EP_POINTS[1:]):
        if yl <= x1:
            return y0 + (y1 - y0) * (yl - x0) / (x1 - x0)
    return _EP_POINTS[-1][1]


def expected_points(down, togo, yl):
    """Expected points for the offense. yl = yards from its own goal line."""
    ep = _interp(yl)
    down = max(1, min(4, int(down)))
    ep += DOWN_ADJ[down]
    # distance: every yard to go beyond 10 costs a little, short yardage helps
    ep += TOGO_COEF[down] * (min(togo, 25) - 10)
    return max(-3.0, min(6.6, ep))


def epa(pre, post):
    return post - pre


# ── Derived metrics for stat lines (collections.Counter) ──────────────────────

def _div(a, b):
    return a / b if b else 0.0


def adot(s):
    """Average depth of target for a passer."""
    return _div(s["iay"], s["pass_att"])


def rec_adot(s):
    return _div(s["rec_air"], s["targets"])


def epa_per_dropback(s):
    return _div(s["pass_epa"], s["dropbacks"])


def epa_per_rush(s):
    return _div(s["rush_epa"], s["rush_att"])


def epa_per_target(s):
    return _div(s["rec_epa"], s["targets"])


def pass_success(s):
    return 100.0 * _div(s["pass_succ"], s["dropbacks"])


def rush_success(s):
    return 100.0 * _div(s["rush_succ"], s["rush_att"])


def pressure_rate(s):
    return 100.0 * _div(s["pressured"], s["dropbacks"])


def catch_rate(s):
    return 100.0 * _div(s["rec"], s["targets"])


def yac_per_rec(s):
    return _div(s["yac"], s["rec"])


def rating_allowed(s):
    """Passer rating on throws into a defender's coverage."""
    att = s["tgt_allowed"]
    if not att:
        return 0.0
    a = max(0.0, min(2.375, (s["cmp_allowed"] / att - 0.3) * 5))
    b = max(0.0, min(2.375, (s["yds_allowed"] / att - 3) * 0.25))
    c = max(0.0, min(2.375, s["td_allowed"] / att * 20))
    d = max(0.0, min(2.375, 2.375 - s["def_int"] / att * 25))
    return round((a + b + c + d) / 6 * 100, 1)


def team_epa_per_play(s):
    return _div(s["epa"], s["epa_plays"])


def team_success(s):
    return 100.0 * _div(s["succ"], s["epa_plays"])
