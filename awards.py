"""
awards.py — end-of-season awards and All-Pro teams.
"""
from stats import fantasy_like_value, total_tackles, passer_rating, fg_pct, punt_avg

OFFENSE = {"QB", "RB", "FB", "WR", "TE", "OT", "IOL"}
DEFENSE = {"DT", "EDGE", "LB", "CB", "S"}

ALL_PRO_SLOTS = [("QB", 1), ("RB", 1), ("WR", 3), ("TE", 1), ("OT", 2), ("IOL", 3),
                 ("EDGE", 2), ("DT", 2), ("LB", 3), ("CB", 2), ("S", 2), ("K", 1), ("P", 1)]


def def_score(s):
    return (s["sacks"] * 5 + s["def_int"] * 6 + total_tackles(s) * 0.7 + s["pd"] * 1.6
            + s["ff"] * 4 + s["fr"] * 2 + s["tfl"] * 1.5 + s["qb_hits"] * 0.8 + s["def_td"] * 8)


def off_score(s, pos):
    v = fantasy_like_value(s)
    if pos == "QB":
        v += (passer_rating(s) - 85) * 1.2
    return v


def position_score(p, lg):
    s = p.season_stats
    gs = s["gs"]
    if p.position in ("OT", "IOL", "FB"):
        return p.ca * 0.8 + gs * 4
    if p.position == "K":
        return s["fgm"] * 3 + fg_pct(s) * 1.2 + s["fg_long"] * 0.3 + p.ca * 0.2
    if p.position == "P":
        return punt_avg(s) * 4 + s["punts_in20"] * 1.5 + p.ca * 0.2
    if p.position in DEFENSE:
        return def_score(s) + p.ca * 0.25
    return off_score(s, p.position) + p.ca * 0.15


def _eligible(lg, min_gp=8):
    out = []
    for t in lg.teams.values():
        for p in t.roster:
            if p.season_stats["gp"] >= min_gp:
                out.append((p, t))
    return out


def compute(lg):
    players = _eligible(lg)
    if not players:
        return {}
    wpct = {a: lg.standings[a].pct for a in lg.teams}
    res = {}

    def best(cands, key):
        if not cands:
            return None
        p, t = max(cands, key=key)
        return {"pid": p.id, "name": p.name, "pos": p.position, "team": t.abbr,
                "line": _line(p)}

    res["MVP"] = best(players, lambda pt: (off_score(pt[0].season_stats, pt[0].position)
                                           * (1.15 if pt[0].position == "QB" else 0.9)
                                           if pt[0].position in OFFENSE else
                                           def_score(pt[0].season_stats) * 0.8)
                      + wpct[pt[1].abbr] * 90 + pt[0].ca * 0.1)
    res["Offensive Player of the Year"] = best(
        [pt for pt in players if pt[0].position in OFFENSE and pt[0].position not in ("OT", "IOL")],
        lambda pt: off_score(pt[0].season_stats, pt[0].position)
        * (0.8 if pt[0].position == "QB" else 1.0) + pt[0].ca * 0.1)
    res["Defensive Player of the Year"] = best(
        [pt for pt in players if pt[0].position in DEFENSE],
        lambda pt: def_score(pt[0].season_stats) + pt[0].ca * 0.15 + wpct[pt[1].abbr] * 8)
    rookies = [pt for pt in players if pt[0].years_pro == 0]
    res["Offensive Rookie of the Year"] = best(
        [pt for pt in rookies if pt[0].position in OFFENSE],
        lambda pt: position_score(pt[0], lg))
    res["Defensive Rookie of the Year"] = best(
        [pt for pt in rookies if pt[0].position in DEFENSE],
        lambda pt: position_score(pt[0], lg))

    # Comeback Player of the Year: back from injury or a lost season
    def comeback(pt):
        p = pt[0]
        prev = p.career.get(lg.year - 1)
        if not prev or p.years_pro < 2:
            return None
        now_v = fantasy_like_value(p.season_stats) / max(1, p.season_stats["gp"])
        ps = prev["stats"]
        prev_v = fantasy_like_value(ps) / max(1, ps["gp"]) if ps["gp"] else 0.0
        missed = max(0, 12 - ps["gp"])
        if missed < 6 and prev_v > now_v * 0.6:
            return None
        return now_v * 2.0 + missed * 1.2 - prev_v * 0.8 + p.season_stats["gp"] * 0.5
    cb = [(comeback(pt), pt) for pt in players if pt[0].position not in ("OT", "IOL", "K", "P")]
    cb = [(v, pt) for v, pt in cb if v is not None and v > 15]
    if cb:
        _, (p, t) = max(cb, key=lambda x: x[0])
        res["Comeback Player of the Year"] = {"pid": p.id, "name": p.name, "pos": p.position,
                                              "team": t.abbr, "line": _line(p)}

    # Special Teams Player of the Year: kickers, punters, returners, coverage men
    def st_value(pt):
        p, s = pt[0], pt[0].season_stats
        if p.position == "K":
            return s["fgm"] * 2.0 + (fg_pct(s) - 80) * 1.5 + s["fg_long"] * 0.3 + s["fgm_50"] * 3
        if p.position == "P":
            return (punt_avg(s) - 44) * 6 + s["punts_in20"] * 1.3
        return s["kr_yds"] / 25 + s["pr_yds"] / 9 + 30 * (s["kr_td"] + s["pr_td"]) + s["st_tkl"] * 2.5
    res["Special Teams Player of the Year"] = best(players, st_value)

    # Coach of the Year: overachievement vs roster + improvement
    best_c = None
    for t in lg.teams.values():
        prev = t.history[-1]["w"] if t.history else 8
        rec = lg.standings[t.abbr]
        exp = 8.5 + (t.overall - 135) / 4.0
        score = (rec.w - exp) * 1.2 + (rec.w - prev) * 0.8 + rec.pct * 4
        if best_c is None or score > best_c[0]:
            best_c = (score, t)
    if best_c:
        t = best_c[1]
        res["Coach of the Year"] = {"pid": None, "name": t.coach.name, "pos": "HC",
                                    "team": t.abbr, "line": lg.standings[t.abbr].wlt()}

    # All-Pro first team
    all_pro = []
    used = set()
    for pos, n in ALL_PRO_SLOTS:
        cands = [pt for pt in players if pt[0].position == pos and pt[0].id not in used]
        cands.sort(key=lambda pt: position_score(pt[0], lg), reverse=True)
        for p, t in cands[:n]:
            used.add(p.id)
            all_pro.append({"pid": p.id, "name": p.name, "pos": pos, "team": t.abbr,
                            "line": _line(p)})
    res["All-Pro"] = all_pro
    return res


def _line(p):
    from stats import summary_line
    return summary_line(p.season_stats, p.position)


REPUTATION_BUMP = {"MVP": 14, "Offensive Player of the Year": 9,
                   "Defensive Player of the Year": 9, "Offensive Rookie of the Year": 8,
                   "Defensive Rookie of the Year": 8, "Comeback Player of the Year": 6,
                   "Special Teams Player of the Year": 5}


def player_of_the_week(lg, results):
    """Offensive, defensive and special-teams Player of the Week after each regular-season week."""
    best = {"Offensive": None, "Defensive": None, "Special Teams": None}
    for res in results:
        for pid, line in res.player_stats.items():
            name, pos, abbr, _ = res.player_meta[pid]
            won = res.score_of(abbr) > res.score_of(res.opponent(abbr)) if abbr in (res.home, res.away) else False
            bonus = 1.1 if won else 1.0
            if pos in OFFENSE:
                v = (line["pass_yds"] * 0.04 + line["pass_td"] * 4 - line["pass_int"] * 3
                     + line["rush_yds"] * 0.1 + line["rush_td"] * 6 + line["rec_yds"] * 0.1
                     + line["rec_td"] * 6 - line["fumbles_lost"] * 3) * bonus
                kind = "Offensive"
            elif pos in DEFENSE:
                v = def_score(line) * bonus
                kind = "Defensive"
            else:
                v = (line["fgm"] * 3 + line["fgm_50"] * 2 + line["punts_in20"] * 1.5) * bonus
                kind = "Special Teams"
            if line["kr_td"] + line["pr_td"]:
                v2 = (line["kr_yds"] / 10 + line["pr_yds"] / 5 + 18 * (line["kr_td"] + line["pr_td"])) * bonus
                if best["Special Teams"] is None or v2 > best["Special Teams"][0]:
                    best["Special Teams"] = (v2, pid, name, pos, abbr, line)
            if best[kind] is None or v > best[kind][0]:
                best[kind] = (v, pid, name, pos, abbr, line)
    from stats import summary_line
    out = []
    for kind, b in best.items():
        if b is None or b[0] <= 0:
            continue
        v, pid, name, pos, abbr, line = b
        text = summary_line(line, pos)
        if kind == "Special Teams" and (line["kr_td"] + line["pr_td"]):
            text = f"{line['kr_yds'] + line['pr_yds']} return yards, {line['kr_td'] + line['pr_td']} TD"
        out.append((lg.year, lg.week, f"{kind} Player of the Week", pid, name, pos, abbr, text))
        p = lg.find_player(pid)
        if p is not None:
            p.potw = getattr(p, "potw", 0) + 1
            p.morale = min(100, p.morale + 3)
    if not hasattr(lg, "weekly_awards") or lg.weekly_awards is None:
        lg.weekly_awards = []
    lg.weekly_awards.extend(out)
    return out


def apply(lg, awards):
    for name, info in awards.items():
        if name == "All-Pro":
            for row in info:
                p = lg.find_player(row["pid"])
                if p:
                    p.awards.append((lg.year, "All-Pro"))
                    p.reputation = min(100, p.reputation + 4)
            continue
        if not info or info.get("pid") is None:
            if info and name == "Coach of the Year":
                c = lg.teams[info["team"]].coach
                c.reputation = min(100, c.reputation + 8)
            continue
        p = lg.find_player(info["pid"])
        if p:
            p.awards.append((lg.year, name))
            p.reputation = min(100, p.reputation + REPUTATION_BUMP.get(name, 5))
            p.morale = min(100, p.morale + 10)
        lg.add_news("Awards", f"{name}: {info['name']} ({info['pos']}, {info['team']}) — "
                              f"{info['line']}", info["team"])
