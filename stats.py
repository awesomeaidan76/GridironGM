"""
stats.py — stat lines and derived stat formulas.

A stat line is a collections.Counter (missing keys read as 0, and it is
picklable). Keys ending in "_long" are maxima rather than sums.
"""
from collections import Counter

# Keys stored on a stat line
PASSING = ["pass_att", "pass_cmp", "pass_yds", "pass_td", "pass_int",
           "pass_long", "sacked", "sack_yds"]
RUSHING = ["rush_att", "rush_yds", "rush_td", "rush_long", "rush_20",
           "fumbles", "fumbles_lost"]
RECEIVING = ["targets", "rec", "rec_yds", "rec_td", "rec_long", "yac",
             "drops", "rec_20"]
DEFENSE = ["tkl_solo", "tkl_ast", "tfl", "sacks", "qb_hits", "def_int",
           "int_yds", "int_td", "pd", "ff", "fr", "def_td"]
KICKING = ["fgm", "fga", "fg_long", "fgm_0_39", "fga_0_39", "fgm_40_49",
           "fga_40_49", "fgm_50", "fga_50", "xpm", "xpa", "punts",
           "punt_yds", "punt_long", "punts_in20", "punt_tb", "ko", "ko_tb"]
RETURNS = ["kr", "kr_yds", "kr_td", "kr_long", "pr", "pr_yds", "pr_td"]
MISC = ["gp", "gs", "penalties", "pen_yds"]


def new_line():
    return Counter()


def merge(into, other):
    """Add stat line `other` into `into` in place."""
    for k, v in other.items():
        if k.endswith("_long"):
            if v > into.get(k, 0):
                into[k] = v
        else:
            into[k] += v
    return into


def total_tackles(s):
    return s["tkl_solo"] + s["tkl_ast"]


def comp_pct(s):
    return 100.0 * s["pass_cmp"] / s["pass_att"] if s["pass_att"] else 0.0


def ypa(s):
    return s["pass_yds"] / s["pass_att"] if s["pass_att"] else 0.0


def ypc(s):
    return s["rush_yds"] / s["rush_att"] if s["rush_att"] else 0.0


def ypr(s):
    return s["rec_yds"] / s["rec"] if s["rec"] else 0.0


def fg_pct(s):
    return 100.0 * s["fgm"] / s["fga"] if s["fga"] else 0.0


def punt_avg(s):
    return s["punt_yds"] / s["punts"] if s["punts"] else 0.0


def passer_rating(s):
    att = s["pass_att"]
    if att == 0:
        return 0.0
    a = max(0.0, min(2.375, (s["pass_cmp"] / att - 0.3) * 5))
    b = max(0.0, min(2.375, (s["pass_yds"] / att - 3) * 0.25))
    c = max(0.0, min(2.375, s["pass_td"] / att * 20))
    d = max(0.0, min(2.375, 2.375 - s["pass_int"] / att * 25))
    return round((a + b + c + d) / 6 * 100, 1)


def scrimmage_yards(s):
    return s["rush_yds"] + s["rec_yds"]


def total_td(s):
    return s["rush_td"] + s["rec_td"] + s["kr_td"] + s["pr_td"] + s["def_td"] \
        + s["int_td"]


def fantasy_like_value(s):
    """A single number for 'how productive was this stat line'."""
    return (s["pass_yds"] * 0.04 + s["pass_td"] * 4 - s["pass_int"] * 2
            + s["rush_yds"] * 0.1 + s["rush_td"] * 6 + s["rec_yds"] * 0.1
            + s["rec_td"] * 6 + s["rec"] * 0.5 - s["fumbles_lost"] * 2
            + total_tackles(s) * 1.0 + s["sacks"] * 4 + s["def_int"] * 5
            + s["pd"] * 1.5 + s["ff"] * 3 + s["fr"] * 2 + s["def_td"] * 6
            + s["int_td"] * 6 + s["tfl"] * 1.5 + s["qb_hits"] * 0.7)


def summary_line(s, position):
    """Short human readable summary for news and game logs."""
    parts = []
    if s["pass_att"]:
        parts.append(f"{s['pass_cmp']}/{s['pass_att']}, {s['pass_yds']} yds, "
                     f"{s['pass_td']} TD, {s['pass_int']} INT")
    if s["rush_att"] and (position in ("RB", "FB", "QB") or s["rush_att"] >= 3):
        parts.append(f"{s['rush_att']} car, {s['rush_yds']} yds"
                     + (f", {s['rush_td']} TD" if s["rush_td"] else ""))
    if s["targets"]:
        parts.append(f"{s['rec']} rec, {s['rec_yds']} yds"
                     + (f", {s['rec_td']} TD" if s["rec_td"] else ""))
    tk = total_tackles(s)
    if tk or s["sacks"] or s["def_int"]:
        bits = [f"{tk} tkl"]
        if s["sacks"]:
            bits.append(f"{s['sacks']:g} sk")
        if s["def_int"]:
            bits.append(f"{s['def_int']} INT")
        if s["pd"]:
            bits.append(f"{s['pd']} PD")
        parts.append(", ".join(bits))
    if s["fga"] or s["xpa"]:
        parts.append(f"{s['fgm']}/{s['fga']} FG, {s['xpm']}/{s['xpa']} XP")
    if s["punts"]:
        parts.append(f"{s['punts']} punts, {punt_avg(s):.1f} avg")
    return "; ".join(parts) if parts else "—"
