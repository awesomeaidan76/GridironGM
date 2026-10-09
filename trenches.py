"""
trenches.py — line play: individual blocking matchups on every snap.

No UI code. Each snap the offense assigns its blockers to the defenders who
come (slides, double teams, tight-end and back chips, blitz pickup), and each
assignment is a one-on-one contest decided by the two players' attributes.

Pass protection: every rusher has a chance to beat his blocker before the
ball is out (longer-developing plays give him more time). The first rusher to
win produces the pressure; the blocker he beat is charged with it.

Run blocking: blockers at the point of attack are paired with the defenders
there (doubles where there are spare blockers, unblocked defenders where there
are not). The average margin of those matchups is the play's blocking edge;
big wins are pancakes, lost blocks are run-defense wins for the defender.

Players can line up away from their own position, so every role check here
goes through `pos(player)` - the slot he is playing this snap - and players
who blew their assignment (`bust`, mostly ones still learning a position)
lose their matchup outright.
"""
import math
import random

# Offensive line order: LT, LG, C, RG, RT (the engine's side.ol list)
LT, LG, C, RG, RT = range(5)


def _sig(x):
    return 1.0 / (1.0 + math.exp(-x))


# ── Player values ─────────────────────────────────────────────────────────────

def rush_value(e, p, vs_style=None):
    """A pass rusher's strength in a one-on-one, from his own best move."""
    pw, fn = e(p, "power_move"), e(p, "finesse_move")
    best, other = max(pw, fn), min(pw, fn)
    return best * 0.34 + other * 0.10 + e(p, "pass_rush_iq") * 0.18 \
        + e(p, "acceleration") * 0.22 + e(p, "strength") * 0.16


def rush_style(e, p):
    return "power" if e(p, "power_move") >= e(p, "finesse_move") else "speed"


def block_value(e, p, style="power"):
    """Pass protection. Power rushers test strength and anchor, speed rushers test feet."""
    v = e(p, "pass_block") * 0.50 + e(p, "footwork") * 0.25 + e(p, "strength") * 0.12 \
        + e(p, "awareness") * 0.13
    if style == "power":
        v += (e(p, "strength") - 70) * 0.10
    else:
        v += (e(p, "footwork") - 70) * 0.06 + (e(p, "agility") - 60) * 0.05
    return v


def run_block_value(e, p, weights):
    return sum(e(p, a) * k for a, k in weights.items())


def _own(p):
    return p.position


def run_def_value(e, p, pos=_own):
    if pos(p) in ("LB", "S", "CB"):
        return e(p, "play_recognition") * 0.30 + e(p, "tackling") * 0.25 \
            + e(p, "block_shedding") * 0.20 + e(p, "pursuit") * 0.25
    return e(p, "run_stop") * 0.35 + e(p, "block_shedding") * 0.30 \
        + e(p, "strength") * 0.20 + e(p, "gap_awareness") * 0.15


# ── Pass protection ───────────────────────────────────────────────────────────

def assign_protection(ol, extra, rushers, rng=random, pos=_own):
    """
    ol: [LT, LG, C, RG, RT]; extra: kept-in TEs/backs; rushers: [(player, kind)]
    where kind is "edge", "inside" or "blitz". Returns a list of matchups
    {"rusher", "blockers": [...], "chip": bool} plus a list of unblocked rushers.
    """
    edges = [r for r, k in rushers if k == "edge"]
    inside = [r for r, k in rushers if k == "inside"]
    blitz = [r for r, k in rushers if k == "blitz"]
    rng.shuffle(blitz)
    m = []
    free_ol = list(ol)
    # Tackles take the edge rushers (left first)
    sides = [LT, RT]
    for i, r in enumerate(edges[:2]):
        idx = sides[i] if i < len(sides) else None
        b = ol[idx] if idx is not None and idx < len(ol) else None
        if b is not None and b in free_ol:
            free_ol.remove(b)
            m.append({"rusher": r, "blockers": [b], "chip": False})
        else:
            m.append({"rusher": r, "blockers": [], "chip": False})
    # Guards take the interior rushers
    for r in inside:
        g = next((ol[i] for i in (LG, RG, C) if i < len(ol) and ol[i] in free_ol), None)
        if g is None:
            m.append({"rusher": r, "blockers": [], "chip": False})
            continue
        free_ol.remove(g)
        m.append({"rusher": r, "blockers": [g], "chip": False})
    # Blitzers: spare linemen first (the center slides), then backs and tight ends
    helpers = list(extra)
    for r in blitz:
        if free_ol:
            m.append({"rusher": r, "blockers": [free_ol.pop(0)], "chip": False})
        elif helpers:
            m.append({"rusher": r, "blockers": [helpers.pop(0)], "chip": False, "pickup": True})
        else:
            m.append({"rusher": r, "blockers": [], "chip": False})
    # Spare blockers double the most dangerous rusher, or chip an edge
    spare = free_ol + helpers
    for b in spare:
        targets = [x for x in m if x["blockers"]]
        if not targets:
            break
        if pos(b) in ("OT", "IOL"):
            # the slide goes toward the most dangerous rusher (an elite edge gets help too)
            undoubled = [x for x in targets if len(x["blockers"]) == 1] or targets
            x = max(undoubled, key=lambda t: t["rusher"].ca + (8 if t["rusher"] in inside else 0))
            x["blockers"].append(b)
        else:
            edge_m = [x for x in targets if x["rusher"] in edges] or targets
            x = max(edge_m, key=lambda t: t["rusher"].ca)
            x["chip"] = True
            x.setdefault("chippers", []).append(b)
    return m


def contest_pass(e, m, base, time_req, stunt=0.0, rng=random):
    """
    Probability each rusher wins his matchup before the throw. Returns the list
    of (prob, margin) per matchup.
    """
    out = []
    for x in m:
        r = x["rusher"]
        style = rush_style(e, r)
        rv = rush_value(e, r, style)
        bl = x["blockers"]
        if not bl:
            # unblocked: he gets there unless the ball is out fast
            p = _sig(1.2 + time_req * 1.4)
            out.append((p, 25.0))
            continue
        bv = block_value(e, bl[0], style)
        if len(bl) > 1:
            bv += 9.0 + (block_value(e, bl[1], style) - 70) * 0.15     # double team
        if x.get("chip"):
            bv += 4.0
        if x.get("pickup"):
            # backs and tight ends picking up a blitzer
            b = bl[0]
            bv = e(b, "pass_block") * 0.55 + e(b, "awareness") * 0.25 + e(b, "strength") * 0.20
        margin = rv - bv + stunt
        p = _sig(base + margin / 15.0 + time_req)
        out.append((p, margin))
    return out


BEAT_FACTOR = 2.6       # a rusher "beats his block" far more often than he gets home


def resolve_pass_rush(e, m, probs, rng=random):
    """
    Who (if anyone) gets home first. Returns (winner matchup or None, list of
    matchups where the rusher beat his block). A rusher can win his rep without
    getting to the quarterback in time; only the fastest win becomes pressure.
    """
    winners, beat = [], []
    for x, pm in zip(m, probs):
        u = rng.random()
        if u < pm[0]:
            winners.append((x, pm))
        if u < min(0.95, pm[0] * BEAT_FACTOR):
            beat.append(x)
    if not winners:
        return None, beat
    first = max(winners, key=lambda w: w[1][1] + rng.gauss(0, 8))
    return first[0], beat


# ── Run blocking ──────────────────────────────────────────────────────────────

def run_matchups(e, ol, tes, fb, front, lbs, safeties, inside, side, weights, rng=random,
                 pos=_own, bust=()):
    """
    Pair blockers and defenders at the point of attack (and on the backside).
    side: -1 = left, +1 = right. Returns (bd, events) where bd is the blocking edge
    (about -1..+1) and events lists (blocker, defender, margin, at_poa).
    """
    if not ol:
        return 0.0, []
    order = list(ol)
    if side > 0:
        order = order[::-1]                   # playside first: tackle, guard, center ...
    if inside:
        poa_bl = order[1:4]                  # guard, center, other guard
    else:
        poa_bl = order[0:2] + tes[:1]        # tackle, guard, tight end
    back_bl = [b for b in order if b not in poa_bl]
    lead = [fb] if fb is not None else []
    # Defenders at the point of attack
    dts = [d for d in front if pos(d) == "DT"]
    eds = [d for d in front if pos(d) != "DT"]
    if inside:
        poa_d = dts + lbs[:1]
        back_d = eds + lbs[1:2]
    else:
        poa_d = eds[:1] + lbs[:1] + (safeties[:1] if len(lbs) < 2 else [])
        back_d = dts + eds[1:] + lbs[1:2]
    events = []
    tot, wsum = 0.0, 0.0

    def pair(blockers, defenders, weight, poa):
        nonlocal tot, wsum
        blockers = list(blockers)
        for d in defenders:
            dv = run_def_value(e, d, pos)
            if blockers:
                b = blockers.pop(0)
                if b.id in bust:
                    margin = -0.55 + rng.gauss(0, 0.2)      # he blocked the wrong man
                else:
                    bv = run_block_value(e, b, weights) if pos(b) in ("OT", "IOL") else \
                        e(b, "run_block") * 0.55 + e(b, "impact_block") * 0.25 + e(b, "strength") * 0.20
                    margin = (bv - dv) / 28.0 + rng.gauss(0, 0.30)
                if d.id in bust:
                    margin += 0.60                         # he ran himself out of his gap
                events.append((b, d, margin, poa))
            else:
                margin = -0.55 + rng.gauss(0, 0.2)          # nobody blocked him
                if d.id in bust:
                    margin += 0.60
                events.append((None, d, margin, poa))
            tot += margin * weight
            wsum += weight
        # spare blockers: double teams climb to the next level
        for b in blockers:
            tot += 0.12 * weight
            wsum += weight * 0.25

    pair(lead + poa_bl, poa_d, 1.0, True)
    pair(back_bl, back_d, 0.4, False)
    return (tot / wsum if wsum else 0.0), events
