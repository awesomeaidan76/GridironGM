"""
grades.py — game grades (0-100) for every player, PFF-style.

No UI code. A player's grade for a game comes from what he did on the plays
he was on the field for, measured against what an average player at his
position does with the same number of snaps: blocks won and lost, pressures
allowed, rushes won, coverage targets, tackles and missed tackles, yards
after contact, catches over expectation, EPA as a passer, kicks made...

Scale (same as the popular grading services): 90+ elite, 80-89 high quality,
70-79 above average, 60-69 average, 50-59 below average, under 50 poor.
A season grade is the snap-weighted average of the game grades.
"""
import math

# Base rates the engine produces for an average player (measured with the
# calibration teams); a player is graded on how far he beats or misses them.
RD_WIN_BASE = {"DT": 0.35, "EDGE": 0.27, "LB": 0.60, "S": 0.90, "CB": 0.5}
PR_WIN_BASE = {"DT": 0.23, "EDGE": 0.23, "LB": 0.20, "S": 0.08, "CB": 0.03}
REC_EPA_BASE = {"WR": 0.30, "TE": 0.28, "RB": 0.0, "FB": 0.0}
CATCH_BASE = {"WR": 0.64, "TE": 0.68, "RB": 0.70, "FB": 0.70}

ROUTE_BASE = {"WR": 0.48, "TE": 0.42, "RB": 0.34, "FB": 0.34}
COV_BASE = {"CB": 0.29, "S": 0.38, "LB": 0.39}

# Per position: (average points per snap, scale) — fitted with the calibration teams so
# an average player grades ~64 and game grades spread like the real services (sd ~13).
POS_NORM = {'CB': (-0.0158, 1.15), 'DT': (0.0569, 0.85), 'EDGE': (0.0233, 0.8), 'FB': (-0.0243, 4.3),
            'IOL': (0.0042, 1.1), 'K': (0.0113, 1.55), 'LB': (0.0175, 1.6), 'OT': (0.0004, 0.9),
            'P': (0.0237, 1.75), 'QB': (0.0682, 0.4), 'RB': (0.0131, 1.0), 'S': (-0.0002, 2.85),
            'TE': (0.0004, 1.45), 'WR': (0.0082, 1.0)}

MID = 64.0
SPREAD = 26.0


def snaps(s):
    return s["off_snaps"] + s["def_snaps"]


def _blocking(s, scale=1.0):
    pb = s["pb_snaps"]
    pts = 0.045 * pb - 0.75 * s["pressures_allowed"] - 0.55 * s["hits_allowed"] - 1.2 * s["sacks_allowed"]
    rb = s["rb_snaps"]
    pts += 0.18 * s["rb_wins"] - 0.16 * (rb - s["rb_wins"]) + 0.35 * s["pancakes"]
    return pts * scale


def _rush(s, pos):
    base = PR_WIN_BASE.get(pos, 0.1)
    return 0.55 * (s["pr_wins"] - base * s["pr_snaps"]) + 0.55 * s["pressures"] + 1.1 * s["sacks"] \
        + 0.3 * s["qb_hits"] + 0.12 * s["double_teamed"]


def _run_d(s, pos):
    base = RD_WIN_BASE.get(pos, 0.4)
    w = 0.4 if pos in ("DT", "EDGE") else 0.15      # second-level defenders are often unblocked by design
    return w * (s["rd_wins"] - base * s["rd_snaps"]) + 0.35 * s["stops"] + 0.08 * (s["tkl_solo"] + s["tkl_ast"]) \
        + 0.6 * s["tfl"] - 0.65 * s["missed_tkl"] + 2.0 * s["ff"] + 0.8 * s["fr"]


def _coverage(s, weight=1.0, pos="CB"):
    t = s["tgt_allowed"]
    pts = 0.45 * (t - s["cmp_allowed"]) - 0.045 * s["yds_allowed"] - 0.9 * s["td_allowed"] \
        + 2.2 * s["def_int"] + 0.5 * s["pd"] + 2.0 * s["def_td"]
    pts += 0.3 * (s["cov_wins"] - COV_BASE.get(pos, 0.33) * s["cov_snaps"])   # every rep in coverage
    return pts * weight


def points(s, pos):
    """Grade points for one game's stat line."""
    pts = -0.8 * s["penalties"]
    if pos in ("OT", "IOL"):
        pts += _blocking(s)
    elif pos == "QB":
        pts += 0.9 * (s["pass_epa"] + 0.55 * s["sacked"]) + 0.6 * s["rush_epa"] \
            - 0.6 * s["pass_int"] - 1.0 * s["fumbles_lost"]
    elif pos in ("RB", "FB"):
        after = s["rush_yds"] - s["ybc"]
        pts += 0.12 * (after - 2.9 * s["rush_att"]) + 0.3 * s["rush_epa"] + 0.1 * s["rush_first"]
        pts += 0.5 * (s["rec_epa"] - REC_EPA_BASE[pos] * s["targets"]) - 1.2 * s["drops"]
        pts += 0.3 * (s["route_wins"] - ROUTE_BASE[pos] * s["routes"])
        pts += _blocking(s, 0.6) - 1.6 * s["fumbles_lost"]
    elif pos in ("WR", "TE"):
        pts += 0.6 * (s["rec_epa"] - REC_EPA_BASE[pos] * s["targets"]) \
            + 0.3 * (s["rec"] - CATCH_BASE[pos] * s["targets"]) - 1.2 * s["drops"] \
            + 0.04 * s["yac"] + 0.1 * s["rush_epa"] - 1.6 * s["fumbles_lost"] \
            + 0.3 * (s["route_wins"] - ROUTE_BASE[pos] * s["routes"])
        if pos == "TE":
            pts += _blocking(s, 0.7)
    elif pos in ("DT", "EDGE"):
        pts += _rush(s, pos) + _run_d(s, pos)
    elif pos == "LB":
        pts += _run_d(s, pos) + _rush(s, pos) * 0.8 + _coverage(s, 0.8, pos)
    elif pos in ("CB", "S"):
        pts += _coverage(s, 1.0, pos) + _run_d(s, pos) * 0.7 + _rush(s, pos) * 0.6
    elif pos == "K":
        pts += 0.6 * s["fgm"] - 1.4 * (s["fga"] - s["fgm"]) + 0.4 * s["fgm_50"] - 1.2 * (s["xpa"] - s["xpm"])
    elif pos == "P":
        pts += 0.06 * (s["punt_yds"] - 45 * s["punts"]) + 0.45 * s["punts_in20"] - 0.5 * s["punt_tb"]
    return pts


def volume(s, pos):
    if pos == "K":
        return s["fga"] * 4 + s["xpa"] * 2
    if pos == "P":
        return s["punts"] * 5
    return snaps(s)


def game_grade(s, pos):
    """0-100 grade for one game (None if he barely played)."""
    n = volume(s, pos)
    if n < 5:
        return None
    off, scale = POS_NORM.get(pos, (0.0, 1.0))
    pts = (points(s, pos) - off * n) * scale
    g = MID + SPREAD * math.tanh(pts / (0.55 * math.sqrt(max(8, n)) + 1.0))
    return max(1.0, min(99.0, g))


def stamp(s, pos):
    """Write the game grade into a game stat line in a merge-safe form."""
    g = game_grade(s, pos)
    if g is None:
        return None
    n = volume(s, pos)
    s["grade_pts"] = round(g * n, 1)
    s["grade_n"] = n
    return g


def grade_of(s):
    """Grade from a (game or season) stat line, or None."""
    return s["grade_pts"] / s["grade_n"] if s["grade_n"] else None


def label(g):
    if g is None:
        return "—"
    return ("Elite" if g >= 90 else "High quality" if g >= 80 else "Above average" if g >= 70
            else "Average" if g >= 60 else "Below average" if g >= 50 else "Poor")
