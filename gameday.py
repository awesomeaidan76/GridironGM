"""
Game-day coaching: film study, weekly game plans, learning during a game, and the
CPU intelligence (difficulty) dial.

Every staff runs this, the user's included (the user's coordinators call the user's
plays). How well a staff does it comes from its own people: coordinator play
calling, head-coach adaptability and game management. The league's
`cpu_intelligence` setting then sharpens or dulls the CPU staffs only. It changes
how well they read film, how hard they lean into what they find and how quickly
they adjust. It never touches a player's ratings or the play-calling bonuses.

Plain tables and small functions, so the port can copy them as they are.
"""
import math
import random
import zlib
from collections import Counter

import defense as dfn_lib
import playbook as pb


def _clip(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


# ── The difficulty dial ───────────────────────────────────────────────────────

LEVELS = ((0.0, "Intern"), (0.5, "Rookie"), (1.0, "Pro"), (1.5, "All-Pro"), (2.0, "Hall of Fame"))
DEFAULT_IQ = 1.0


def level_name(iq):
    """The nearest named level for a setting value (Pro = 1.0, the realistic baseline)."""
    return min(LEVELS, key=lambda lv: abs(lv[0] - iq))[1]


def effects(iq=DEFAULT_IQ):
    """
    What the dial does, as plain numbers. Every value is neutral at 1.0 (Pro):
      sharp  - moves a coach's decision ratings toward 20 (or toward 0 below Pro)
      film   - games of film the staff studies before a game
      read   - multiplier on scouting error (lower reads the opponent better)
      plan   - how hard the weekly plan leans into what the film shows
      learn  - how quickly the staff adjusts to what is working during a game
    """
    iq = _clip(iq if iq is not None else DEFAULT_IQ, 0.0, 2.0)
    d = iq - 1.0
    return {"iq": iq, "sharp": 0.6 * d, "film": int(round(2 + 2 * iq)),
            "read": _clip(1.0 - 0.45 * d, 0.3, 1.6), "plan": 0.4 + 0.6 * iq, "learn": 0.4 + 0.6 * iq}


NEUTRAL = effects(DEFAULT_IQ)


def sharpen(rating, fx):
    """A 1-20 decision rating as this staff uses it: closer to 20 above Pro, lower below."""
    s = fx["sharp"]
    if s >= 0:
        return rating + (20.0 - rating) * s
    return max(1.0, rating * (1.0 + s))


def caution(fx):
    """
    How much extra win probability a staff wants before it trusts the numbers on 4th
    down and two-point tries (1.0 = a typical real staff). Sharper staffs trust the math more.
    """
    s = fx["sharp"]
    return max(0.2, 1.0 - 0.8 * s) if s >= 0 else 1.0 - s


# ── Film study ────────────────────────────────────────────────────────────────

OWN_SCALARS = ("plays", "pass_att", "rush_att", "dropbacks", "iay", "screen_att", "pa_att",
               "motion_snaps", "gun_snaps", "pressured")
ALLOWED_SCALARS = ("plays", "pass_att", "pass_yds", "rush_att", "rush_yds", "epa", "epa_plays",
                   "dropbacks", "pressured")


def film(games, abbr, n=4):
    """
    What a club has put on film in its last n games: its own tendencies (situational
    pass rates, personnel, defensive calls) and what offenses did against it.
    games: that club's GameResults this season, oldest first. Counts only.
    """
    own, allowed = Counter(), Counter()
    used = 0
    for g in games[-n:] if n > 0 else []:
        ts = g.team_stats.get(abbr)
        if not ts:
            continue
        used += 1
        for k, v in ts.items():
            if k.startswith(("sit|", "pers|", "dpkg|")) or (k.startswith("dc|") and k.endswith("|n")):
                own[k] += v
        for k in OWN_SCALARS:
            own[k] += ts.get(k, 0)
        opp = g.team_stats.get(g.opponent(abbr), {})
        for k in ALLOWED_SCALARS:
            allowed[k] += opp.get(k, 0)
    return {"games": used, "own": own, "allowed": allowed}


# League-normal situational pass rates (this engine, 2026 baseline)
SIT_BASE = {"1st & 2nd down": 0.54, "3rd/4th & short": 0.30, "3rd/4th & medium": 0.72,
            "3rd/4th & long": 0.88, "Red zone": 0.53}
PASS_BASE = 0.571                 # all snaps
YPA_BASE, YPC_BASE = 6.7, 4.2
SIT_PRIOR = 25.0                  # snaps of "what we knew about his system" per bucket
PASS_PRIOR = 120.0
COV_PRIOR = 150.0


def read_offense(report, plan, err=0.0, rng=random):
    """
    A defensive staff's read of an offense: its overall pass lean and its pass rate in
    each situation, film blended with what is known of the coach's system (his plan).
    err widens the read (a poor staff, or little film).
    """
    own = report.get("own", {}) if report else {}
    sys_pass = plan.get("pass_rate", 0.55)
    n = sum(own.get(f"sit|{b}|n", 0) for b in SIT_BASE)
    p = sum(own.get(f"sit|{b}|p", 0) for b in SIT_BASE)
    prior = PASS_BASE + (sys_pass - 0.55)
    overall = (prior * PASS_PRIOR + p) / (PASS_PRIOR + n)
    overall = _clip(overall + rng.gauss(0, err * 0.05), 0.2, 0.9)
    sit = {}
    for b, base in SIT_BASE.items():
        nb, pb_ = own.get(f"sit|{b}|n", 0), own.get(f"sit|{b}|p", 0)
        pri = _clip(base + (sys_pass - 0.55) * 0.8, 0.05, 0.97)
        sit[b] = _clip((pri * SIT_PRIOR + pb_) / (SIT_PRIOR + nb) + rng.gauss(0, err * 0.06), 0.02, 0.98)
    return {"pass_rate": overall + 0.55 - PASS_BASE, "sit_pass": sit, "overall": overall, "snaps": n}


def sit_lean(read, bucket):
    """How much more (or less) than usual this offense throws in this situation, beyond its overall lean."""
    if not read:
        return 0.0
    q = read["sit_pass"].get(bucket)
    if q is None:
        return 0.0
    return (q - SIT_BASE[bucket]) - (read["overall"] - PASS_BASE)


_PRIOR_CACHE = {}
_PRIOR_SITS = ((1, 10, 70), (1, 10, 40), (2, 7, 60), (2, 3, 45), (3, 8, 55), (3, 2, 50), (2, 6, 15), (3, 5, 30))


def coverage_prior(scheme, plan):
    """
    What a defense's system and habits say it will play: its coordinator's call mix
    over a spread of situations. Cached per system and rounded habits.
    """
    key = (scheme, plan.get("front"), round(plan.get("blitz", 0.3), 1), round(plan.get("zone", 0.5), 1),
           round(plan.get("two_high", 0.4), 1))
    got = _PRIOR_CACHE.get(key)
    if got is not None:
        return got
    rng = random.Random(zlib.crc32(repr(key).encode()))
    dp = {"front": key[1], "blitz": key[2], "zone": key[3], "two_high": key[4]}
    mix = Counter()
    for down, togo, to_goal in _PRIOR_SITS:
        for _ in range(16):
            c = dfn_lib.choose_call(dp, {"down": down, "togo": togo, "to_goal": to_goal, "n_cb": 3, "n_s": 2},
                                    scheme=scheme, rng=rng)
            mix[c["cov"]] += 1
            if c["blitz"]:
                mix["|press"] += 1
    _PRIOR_CACHE[key] = mix
    return mix


def coverage_mix(report, prior):
    """Share of each coverage the defense is expected to play (film blended with its system)."""
    own = report.get("own", {}) if report else {}
    seen = {c: own.get(f"dc|{c}|n", 0) for c in dfn_lib.COVERAGES}
    n_seen = sum(seen.values())
    n_pri = sum(v for k, v in prior.items() if not k.startswith("|")) or 1
    mix = {}
    for c in dfn_lib.COVERAGES:
        mix[c] = (prior.get(c, 0) / n_pri * COV_PRIOR + seen[c]) / (COV_PRIOR + n_seen)
    press_seen = own.get("dc|Pressure (5+ rushers)|n", 0)
    rush_seen = press_seen + own.get("dc|Four-man rush|n", 0) + own.get("dc|Line stunt|n", 0) \
        + sum(own.get(f"dc|{s}|n", 0) for s in ("Creeper", "Amoeba", "Double Mug"))
    press = (prior.get("|press", 0) / n_pri * COV_PRIOR + press_seen) / (COV_PRIOR + rush_seen)
    two = sum(v for c, v in mix.items() if dfn_lib.COVERAGES[c][1] >= 2)
    man = sum(v for c, v in mix.items() if dfn_lib.COVERAGES[c][0])
    return {"cov": mix, "press": press, "two_high": two, "man": man, "snaps": n_seen}


_EDGE_TABLE = {}                  # play name -> {coverage: edge}, built once per play


def _play_edges(play):
    got = _EDGE_TABLE.get(play["name"])
    if got is None:
        routes = [r for r in play["routes"].values() if r != "block"] or ["checkdown"]
        got = {}
        for cov in dfn_lib.COVERAGES:
            edges = [dfn_lib.route_edge(cov, r) for r in routes]
            # the quarterback throws to the open man: the best route counts as much as the rest
            v = 0.5 * sum(edges) / len(edges) + 0.5 * max(edges)
            if v:
                got[cov] = v
        _EDGE_TABLE[play["name"]] = got
    return got


def concept_edges(cov_mix):
    """Expected coverage-beater edge of every pass concept against this coverage mix, relative to
    the other concepts of its depth (screen, short, medium, deep)."""
    mix = [(c, p) for c, p in cov_mix.items() if p > 0.001]
    out, by_cls = {}, {}
    for play in pb.PASS_PLAYS:
        t = _play_edges(play)
        e = 0.0
        for c, p in mix:
            v = t.get(c)
            if v:
                e += p * v
        out[play["name"]] = (play["cls"], e)
        by_cls.setdefault(play["cls"], []).append(e)
    mean = {k: sum(v) / len(v) for k, v in by_cls.items()}
    return {n: e - mean[cls] for n, (cls, e) in out.items()}


# Typical starting unit ratings in this engine (for "is their pass defense weak?")
UNIT_BASE = {"DL": 134.0, "LB": 123.5, "DB": 129.0}


def offense_plan(off_team, def_team, report, calling, adapt, fx, def_plan, scheme=None, rng=random):
    """
    The offensive coordinator's weekly plan for this defense. Better staffs read the
    film more accurately; adaptable coaches lean further into it ("game-plan
    coaches"), stubborn ones stick to their system.
      pass_shift   - more or less passing than usual
      deep_shift / screen_shift - shots and screens against this coverage and pressure
      concepts     - pass concepts that beat what they play (name -> weight)
      targets      - receivers with a good matchup (pid -> weight)
      run_right    - chance a run goes right (toward the stronger side of our line)
      notes        - plain-English summary for the scouting report
    """
    err = max(0.0, (20.0 - calling) / 20.0) * 0.6 * fx["read"]
    g = fx["plan"] * (calling / 20.0) * (0.5 + adapt / 20.0)      # about 0.5 for an average staff
    notes = []
    plan = {"pass_shift": 0.0, "deep_shift": 0.0, "screen_shift": 0.0, "concepts": {}, "targets": {},
            "run_right": 0.5, "notes": notes, "g": g}
    if def_team is None:
        return plan
    prior = coverage_prior(def_team.coach.def_scheme, def_plan)
    mix = coverage_mix(report, prior)
    # Noise: a poor staff misreads what it sees on film
    cov = {c: max(0.0, p * (1.0 + rng.gauss(0, err * 0.5))) for c, p in mix["cov"].items()}
    tot = sum(cov.values()) or 1.0
    cov = {c: p / tot for c, p in cov.items()}
    press = _clip(mix["press"] + rng.gauss(0, err * 0.05), 0.0, 0.8)
    two = sum(p for c, p in cov.items() if dfn_lib.COVERAGES[c][1] >= 2)
    man = sum(p for c, p in cov.items() if dfn_lib.COVERAGES[c][0])

    # Concepts that beat their coverages
    rel = concept_edges(cov)
    for name, r in rel.items():
        plan["concepts"][name] = _clip(math.exp(g * 0.55 * r), 0.6, 1.8)
    plain = {p["name"] for p in pb.PASS_PLAYS if not (p.get("rpo") or p.get("trick") or p.get("pa"))
             and p["cls"] != "hail"}
    top = sorted((n for n in rel if n in plain and plan["concepts"][n] > 1.12), key=lambda n: -rel[n])[:2]
    main = max(cov, key=cov.get)
    if top:
        notes.append(f"They live in {main} ({cov[main]:.0%} of snaps): feature {' and '.join(top)}")
    # Shell and pressure
    plan["deep_shift"] = _clip(-(two - 0.32) * 0.20 * g, -0.05, 0.05)
    if two < 0.22 and g > 0.3:
        notes.append("Single-high most of the time: take shots outside")
    elif two > 0.45 and g > 0.3:
        notes.append("Two deep safeties: be patient, work underneath")
    plan["screen_shift"] = _clip((press - 0.22) * 0.25 * g, -0.03, 0.06)
    if press > 0.30 and g > 0.3:
        notes.append(f"They pressure a lot ({press:.0%} of dropbacks): screens and quick throws")

    # Run or pass: their weaker unit, on film and on paper
    u = def_team.unit_ratings()
    pass_d = (u["DB"] - UNIT_BASE["DB"]) * 0.65 + (u["DL"] - UNIT_BASE["DL"]) * 0.35 + rng.gauss(0, err * 6)
    run_d = (u["DL"] - UNIT_BASE["DL"]) * 0.55 + (u["LB"] - UNIT_BASE["LB"]) * 0.45 + rng.gauss(0, err * 6)
    paper = (run_d - pass_d) / 60.0
    al = report.get("allowed", {}) if report else {}
    w = min(1.0, al.get("plays", 0) / 240.0)            # film counts once there is enough of it
    ypa = al.get("pass_yds", 0) / al["pass_att"] if al.get("pass_att", 0) >= 20 else YPA_BASE
    ypc = al.get("rush_yds", 0) / al["rush_att"] if al.get("rush_att", 0) >= 15 else YPC_BASE
    seen = (ypa / YPA_BASE - ypc / YPC_BASE) * 0.5
    lean = paper * (1.0 - 0.5 * w) + seen * 0.5 * w
    plan["pass_shift"] = _clip(lean * 0.25 * g, -0.06, 0.06)
    if plan["pass_shift"] > 0.02:
        notes.append("Their pass defense is the weak spot: throw it")
    elif plan["pass_shift"] < -0.02:
        notes.append("They can be run on: lean on the ground game")

    # Receiver matchups: our receivers against the corners likely to cover them
    wrs = off_team.lineup("WR", 3)
    cbs = def_team.lineup("CB", 3)
    if wrs and cbs:
        def seen_r(p, pos):
            return p.rating_at(pos) + rng.gauss(0, err * 10)
        cb_r = sorted((seen_r(c, "CB") for c in cbs), reverse=True)
        best = None
        for i, wr in enumerate(wrs):
            if i >= len(cb_r):
                break
            edge = (seen_r(wr, "WR") - cb_r[i]) / 10.0
            plan["targets"][wr.id] = _clip(math.exp(g * 0.16 * edge), 0.85, 1.22)
            if best is None or edge > best[1]:
                best = (wr, edge)
        if best is not None and best[1] > 1.0 and g > 0.3:
            notes.append(f"Get {best[0].name} the ball: he has the best matchup")

    # Run side: the stronger side of our line
    ol = off_team.lineup("OT", 2), off_team.lineup("IOL", 3)
    if len(ol[0]) >= 2 and len(ol[1]) >= 3:
        lt, rt = ol[0][0], ol[0][1]
        lg, rg = ol[1][0], ol[1][2]

        def rb(p):
            return p.a("run_block") * 0.7 + p.a("strength") * 0.3 + rng.gauss(0, err * 4)
        diff = (rb(rt) + rb(rg)) - (rb(lt) + rb(lg))
        plan["run_right"] = _clip(0.5 + diff / 40.0 * g, 0.32, 0.68)
    return plan


def learned(ts, prefix, keys, lr, sign=1.0):
    """
    In-game learning: a weight for each call from how it has worked today (EPA per
    snap, shrunk toward zero while there are few snaps). sign=-1 for a defense
    (its calls are graded by what the offense gained).
    """
    out = {}
    if lr <= 0:
        return out
    for k in keys:
        n = ts.get(f"{prefix}|{k}|n", 0)
        if n < 2:
            continue
        m = ts.get(f"{prefix}|{k}|epa", 0.0) / (n + 3.0)
        out[k] = _clip(math.exp(sign * lr * _clip(m, -0.8, 0.8)), 0.72, 1.35)
    return out
