"""
ui_stats.py — stat column definitions shared by profiles, leaderboards and
box scores.
"""
from stats import (comp_pct, passer_rating, ypa, ypc, ypr, total_tackles, fg_pct,
                   punt_avg)
from ui_widgets import cell
import advanced as adv


def _f1(v):
    return f"{v:.1f}"


GROUPS = {
    "Passing": (["Cmp", "Att", "Pct", "Yds", "Y/A", "TD", "Int", "Lng", "Sck", "Rate"],
                lambda s: [s["pass_cmp"], s["pass_att"], cell(_f1(comp_pct(s)), comp_pct(s)),
                           s["pass_yds"], cell(_f1(ypa(s)), ypa(s)), s["pass_td"],
                           s["pass_int"], s["pass_long"], s["sacked"],
                           cell(_f1(passer_rating(s)), passer_rating(s), bold=True)]),
    "Rushing": (["Att", "Yds", "Avg", "TD", "Lng", "20+", "Fum"],
                lambda s: [s["rush_att"], s["rush_yds"], cell(_f1(ypc(s)), ypc(s)), s["rush_td"],
                           s["rush_long"], s["rush_20"], s["fumbles"]]),
    "Receiving": (["Tgt", "Rec", "Yds", "Avg", "TD", "Lng", "YAC", "Drop"],
                  lambda s: [s["targets"], s["rec"], s["rec_yds"], cell(_f1(ypr(s)), ypr(s)),
                             s["rec_td"], s["rec_long"], s["yac"], s["drops"]]),
    "Defense": (["Tkl", "Solo", "Ast", "TFL", "Sck", "QBH", "Int", "PD", "FF", "FR", "TD"],
                lambda s: [total_tackles(s), s["tkl_solo"], s["tkl_ast"], s["tfl"],
                           cell(f"{s['sacks']:g}", s["sacks"]), s["qb_hits"], s["def_int"],
                           s["pd"], s["ff"], s["fr"], s["def_td"]]),
    "Kicking": (["FGM", "FGA", "Pct", "Lng", "0-39", "40-49", "50+", "XPM", "XPA"],
                lambda s: [s["fgm"], s["fga"], cell(_f1(fg_pct(s)), fg_pct(s)), s["fg_long"],
                           f"{s['fgm_0_39']}/{s['fga_0_39']}", f"{s['fgm_40_49']}/{s['fga_40_49']}",
                           f"{s['fgm_50']}/{s['fga_50']}", s["xpm"], s["xpa"]]),
    "Punting": (["Punts", "Yds", "Avg", "Lng", "In20", "TB"],
                lambda s: [s["punts"], s["punt_yds"], cell(_f1(punt_avg(s)), punt_avg(s)),
                           s["punt_long"], s["punts_in20"], s["punt_tb"]]),
    "Snaps": (["Off Snaps", "Def Snaps", "ST Tkl"],
              lambda s: [s["off_snaps"], s["def_snaps"], s["st_tkl"]]),
    "Returns": (["KR", "KR Yds", "KR TD", "PR", "PR Yds", "PR TD"],
                lambda s: [s["kr"], s["kr_yds"], s["kr_td"], s["pr"], s["pr_yds"], s["pr_td"]]),
}

def _f2(v):
    return f"{v:+.2f}"


def _pct(v):
    return f"{v:.1f}%"


# Advanced groups take (stat line, context); context["team_tgt"] = team targets
ADV_GROUPS = {
    "AdvPass": (["Dropbacks", "EPA", "EPA/DB", "Success", "aDOT", "CAY/Cmp", "Pressured", "1st Dn", "Rate"],
                lambda s, c: [s["dropbacks"], cell(f"{s['pass_epa']:+.1f}", s["pass_epa"]),
                              cell(_f2(adv.epa_per_dropback(s)), adv.epa_per_dropback(s), bold=True),
                              cell(_pct(adv.pass_success(s)), adv.pass_success(s)),
                              cell(_f1(adv.adot(s)), adv.adot(s)),
                              cell(_f1(s["cay"] / s["pass_cmp"] if s["pass_cmp"] else 0.0),
                                   s["cay"] / s["pass_cmp"] if s["pass_cmp"] else 0.0),
                              cell(_pct(adv.pressure_rate(s)), adv.pressure_rate(s)),
                              s["pass_first"], cell(_f1(passer_rating(s)), passer_rating(s))]),
    "AdvRush": (["Att", "Yds", "EPA", "EPA/Att", "Success", "1st Dn", "20+", "Avg"],
                lambda s, c: [s["rush_att"], s["rush_yds"], cell(f"{s['rush_epa']:+.1f}", s["rush_epa"]),
                              cell(_f2(adv.epa_per_rush(s)), adv.epa_per_rush(s), bold=True),
                              cell(_pct(adv.rush_success(s)), adv.rush_success(s)),
                              s["rush_first"], s["rush_20"], cell(_f1(ypc(s)), ypc(s))]),
    "AdvRec": (["Tgt", "Tgt Share", "aDOT", "Catch%", "YAC/Rec", "EPA", "EPA/Tgt", "1st Dn", "Drop"],
               lambda s, c: [s["targets"],
                             cell(_pct(100.0 * s["targets"] / c.get("team_tgt", 0)) if c.get("team_tgt") else "—",
                                  s["targets"] / c["team_tgt"] if c.get("team_tgt") else 0),
                             cell(_f1(adv.rec_adot(s)), adv.rec_adot(s)),
                             cell(_pct(adv.catch_rate(s)), adv.catch_rate(s)),
                             cell(_f1(adv.yac_per_rec(s)), adv.yac_per_rec(s)),
                             cell(f"{s['rec_epa']:+.1f}", s["rec_epa"]),
                             cell(_f2(adv.epa_per_target(s)), adv.epa_per_target(s), bold=True),
                             s["rec_first"], s["drops"]]),
    "RunDef": (["Tkl", "Stops", "TFL", "Missed", "Miss %"],
               lambda s, c: [total_tackles(s), cell(s["stops"], s["stops"], bold=True), s["tfl"], s["missed_tkl"],
                             cell(_pct(100.0 * s["missed_tkl"] / max(1, s["missed_tkl"] + total_tackles(s))),
                                  -s["missed_tkl"] / max(1, s["missed_tkl"] + total_tackles(s)))]),
    "PassRush": (["Pressures", "Sacks", "QB Hits", "TFL", "FF"],
                 lambda s, c: [cell(s["pressures"], s["pressures"], bold=True),
                               cell(f"{s['sacks']:g}", s["sacks"]), s["qb_hits"], s["tfl"], s["ff"]]),
    "Coverage": (["Tgt", "Cmp", "Cmp%", "Yds", "Y/Tgt", "TD", "Int", "PD", "Rating"],
                 lambda s, c: [s["tgt_allowed"], s["cmp_allowed"],
                               cell(_pct(100.0 * s["cmp_allowed"] / s["tgt_allowed"]) if s["tgt_allowed"] else "—",
                                    s["cmp_allowed"] / s["tgt_allowed"] if s["tgt_allowed"] else 0),
                               s["yds_allowed"],
                               cell(_f1(s["yds_allowed"] / s["tgt_allowed"]) if s["tgt_allowed"] else "—",
                                    s["yds_allowed"] / s["tgt_allowed"] if s["tgt_allowed"] else 0),
                               s["td_allowed"], s["def_int"], s["pd"],
                               cell(_f1(adv.rating_allowed(s)), -adv.rating_allowed(s), bold=True)]),
}

POSITION_GROUPS = {
    "QB": ["Passing", "AdvPass", "Rushing"], "RB": ["Rushing", "AdvRush", "Receiving"],
    "FB": ["Rushing", "Receiving"], "WR": ["Receiving", "AdvRec", "Rushing"],
    "TE": ["Receiving", "AdvRec"], "OT": [], "IOL": [], "DT": ["Defense", "PassRush", "RunDef"],
    "EDGE": ["Defense", "PassRush", "RunDef"], "LB": ["Defense", "RunDef", "Coverage"],
    "CB": ["Defense", "Coverage"], "S": ["Defense", "RunDef", "Coverage"], "K": ["Kicking"], "P": ["Punting"],
}


def groups_for(player):
    g = list(POSITION_GROUPS[player.position])
    if player.position not in ("K", "P"):
        g.append("Snaps")
    if player.position in ("RB", "WR", "CB", "S"):
        tot = sum(s["stats"]["kr"] + s["stats"]["pr"] for s in player.career.values())
        if tot or player.season_stats["kr"] or player.season_stats["pr"]:
            g.append("Returns")
    return g


def columns(group):
    return (ADV_GROUPS.get(group) or GROUPS[group])[0]


def values(group, s, ctx=None):
    if group in ADV_GROUPS:
        return ADV_GROUPS[group][1](s, ctx or {})
    return GROUPS[group][1](s)


# Leaderboard definitions: (title, group, qualifier fn, default sort column)
LEADERBOARDS = {
    "Passing": ("Passing", lambda s, g: s["pass_att"] >= max(1, g) * 12, "Yds"),
    "Rushing": ("Rushing", lambda s, g: s["rush_att"] >= max(1, g) * 4, "Yds"),
    "Receiving": ("Receiving", lambda s, g: s["targets"] >= max(1, g) * 2, "Yds"),
    "Defense": ("Defense", lambda s, g: total_tackles(s) + s["sacks"] + s["def_int"] > 0, "Tkl"),
    "Kicking": ("Kicking", lambda s, g: s["fga"] + s["xpa"] > 0, "FGM"),
    "Punting": ("Punting", lambda s, g: s["punts"] > 0, "Yds"),
    "Returns": ("Returns", lambda s, g: s["kr"] + s["pr"] > 0, "KR Yds"),
    "AdvPass": ("Advanced passing", lambda s, g: s["dropbacks"] >= max(1, g) * 14, "EPA"),
    "AdvRush": ("Advanced rushing", lambda s, g: s["rush_att"] >= max(1, g) * 4, "EPA"),
    "AdvRec": ("Advanced receiving", lambda s, g: s["targets"] >= max(1, g) * 2, "EPA"),
    "PassRush": ("Pass rush", lambda s, g: s["pressures"] >= max(1, g) * 0.8, "Pressures"),
    "RunDef": ("Tackling", lambda s, g: total_tackles(s) >= max(1, g) * 2, "Stops"),
    "Coverage": ("Coverage", lambda s, g: s["tgt_allowed"] >= max(1, g) * 2.5, "Tgt"),
}
