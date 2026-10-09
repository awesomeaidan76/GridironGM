"""
position_fit.py — playing a player somewhere other than his own position.

No UI code. Any player can be put at any depth-chart slot (Madden style). His
rating there is that slot's own formula applied to his own attributes, so the
formula does most of the work: a receiver at running back is judged on vision,
breaking tackles and balance, which receivers rarely have. Two things are added
on top, and they apply in the match engine exactly as they do in the rating:

  * Size fit. Every slot has a normal build (player.SIZE). A player well
    outside it pays for it: too light and he loses strength, blocking,
    shedding and tackle-breaking (a 245 lb linebacker gets moved by 315 lb
    guards); too heavy and he loses speed, quickness and agility. Inside the
    normal range there is no effect, and a player's own position never has one.

  * Familiarity (0-100). A player knows his own position completely (100). At
    any other slot he starts with what carries over (a tackle already knows a
    lot about guard; a receiver knows very little about corner) and learns it
    through practice reps (being on that slot's depth list) and game snaps
    there. Low familiarity costs mental attributes in full, plus the
    techniques of the new slot that his own position never uses. Technique he
    already uses (a tackle's pass blocking at guard) is not penalised.
    Unfamiliar players also commit more penalties and blow more assignments.

POT at a slot assumes he has learned it and grows the way he is growing at
his own position, in proportion to how much the two positions share.

Everything here is plain tables and small functions so it ports cleanly.
"""
import math

from ratings import (POSITIONS, POSITION_WEIGHTS, MENTAL_ATTRS, PHYSICAL_ATTRS, compute_ca,
                     ovr_from_ca)

# ── Depth-chart slots ─────────────────────────────────────────────────────────

DEPTH_SLOTS = POSITIONS + ["KR", "PR"]
RETURN_SLOTS = ("KR", "PR")
# How many players each slot puts on the field in the base lineup
STARTERS = {"QB": 1, "RB": 1, "FB": 1, "WR": 3, "TE": 1, "OT": 2, "IOL": 3, "DT": 2,
            "EDGE": 2, "LB": 3, "CB": 3, "S": 2, "K": 1, "P": 1, "KR": 1, "PR": 1}
# How deep the engine reads each slot's list on game day
GAME_DEPTH = {"QB": 2, "RB": 3, "FB": 1, "WR": 5, "TE": 3, "OT": 2, "IOL": 3, "DT": 4,
              "EDGE": 4, "LB": 4, "CB": 4, "S": 3, "K": 1, "P": 1}
OFFENSE_SLOTS = ("QB", "RB", "FB", "WR", "TE", "OT", "IOL")
DEFENSE_SLOTS = ("DT", "EDGE", "LB", "CB", "S")
SPECIAL_SLOTS = ("K", "P", "KR", "PR")


def unit_of(slot):
    return "off" if slot in OFFENSE_SLOTS else "def" if slot in DEFENSE_SLOTS else "st"


# ── Familiarity ───────────────────────────────────────────────────────────────
# What a player knows about another position before he has ever practised there
# (0-100), by his own position. Pairs not listed start at DEFAULT_START.

RELATED = {
    "QB":   {"RB": 15, "WR": 15, "TE": 10, "S": 10, "P": 15, "K": 10},
    "RB":   {"FB": 60, "WR": 40, "TE": 15, "CB": 15, "S": 15, "LB": 10, "QB": 10},
    "FB":   {"RB": 55, "TE": 60, "LB": 30, "IOL": 15, "OT": 10, "DT": 10},
    "WR":   {"TE": 30, "RB": 30, "CB": 20, "S": 15, "QB": 5},
    "TE":   {"FB": 65, "WR": 40, "OT": 30, "IOL": 20, "RB": 15, "EDGE": 20, "LB": 15, "DT": 10},
    "OT":   {"IOL": 70, "TE": 25, "FB": 20, "DT": 15},
    "IOL":  {"OT": 55, "FB": 20, "TE": 15, "DT": 15},
    "DT":   {"EDGE": 50, "LB": 20, "IOL": 15, "FB": 15, "OT": 10},
    "EDGE": {"DT": 50, "LB": 55, "TE": 15, "S": 10},
    "LB":   {"EDGE": 50, "S": 40, "FB": 30, "DT": 20, "CB": 10, "TE": 10},
    "CB":   {"S": 65, "WR": 20, "LB": 10, "RB": 10},
    "S":    {"CB": 50, "LB": 50, "WR": 10, "RB": 10},
    "K":    {"P": 50},
    "P":    {"K": 50, "QB": 10},
}
DEFAULT_START = 5

FAMILIARITY_LABELS = [(100, "Natural"), (90, "Accomplished"), (70, "Competent"),
                      (45, "Learning"), (20, "Awkward"), (0, "Unfamiliar")]

# Attribute points lost at zero familiarity: mental attributes in full,
# techniques his own position never uses at NEW_TECH of it, and techniques he
# already uses (pass blocking for a tackle moved to guard) at KNOWN_TECH. The
# curve is convex: the first weeks at a new spot cost the most, the last few
# points very little.
FAM_MAX = 18.0
FAM_CURVE = 1.35
NEW_TECH = 0.7
KNOWN_TECH = 0.3

# Weekly learning with a full load of reps (starter's practice reps plus a full
# game there), before the player's adaptability is applied. A related move
# (tackle to guard) takes about four weeks; an unrelated one (receiver to
# corner) more than a season.
LEARN_BASE = 3.0
LEARN_RELATED = 0.12
PRACTICE_SHARE = 0.5          # the rest comes from game snaps
FULL_GAME_SNAPS = 45          # snaps at the slot that count as a full game of reps
# Practice reps by place on the slot's depth list: starters, the next man, the one after him
PRACTICE_REPS = (1.0, 0.6, 0.3)
# Chance per snap that a player with no familiarity at all blows his assignment
# (scaled down as he learns: a missed block, a blown coverage, the wrong gap)
BUST_RATE = 0.05
# Extra penalties (false starts, holding, offside) per unfamiliar player on the field
PENALTY_RATE = 0.30
# What is kept of the familiarity learned above a player's starting point each
# offseason, if he got reps there last season or not
KEEP_USED = 0.90
KEEP_UNUSED = 0.65

_TECHNIQUE = {}
for _pos, _w in POSITION_WEIGHTS.items():
    _TECHNIQUE[_pos] = {a for a in _w if a not in MENTAL_ATTRS and a not in PHYSICAL_ATTRS}
_MENTAL = set(MENTAL_ATTRS)
_PHYSICAL = set(PHYSICAL_ATTRS)


def start_familiarity(own, slot):
    if own == slot:
        return 100.0
    return float(RELATED.get(own, {}).get(slot, DEFAULT_START))


def familiarity(p, slot):
    """How well this player knows a slot (0-100). His own position is always 100."""
    if slot == p.position or slot in RETURN_SLOTS:
        return 100.0
    fam = getattr(p, "familiarity", None)
    if fam and slot in fam:
        return fam[slot]
    return start_familiarity(p.position, slot)


def familiarity_label(value):
    for floor, name in FAMILIARITY_LABELS:
        if value >= floor:
            return name
    return "Unfamiliar"


def fam_penalty(value):
    """Attribute points a player loses at a slot he knows this well."""
    if value >= 100.0:
        return 0.0
    return FAM_MAX * ((100.0 - max(0.0, value)) / 100.0) ** FAM_CURVE


def _known_techniques(p):
    """Techniques he already uses: his own position's, and any slot he has fully learned."""
    known = set(_TECHNIQUE.get(p.position, ()))
    fam = getattr(p, "familiarity", None)
    if fam:
        for s, v in fam.items():
            if v >= 90.0 and s in _TECHNIQUE:
                known |= _TECHNIQUE[s]
    return known


def learn_rate(p, slot):
    """Familiarity gained in a week of full reps at a slot."""
    adapt = p.hidden.get("adaptability", 50)
    iq = p.attrs.get("awareness", 60)
    mult = 0.55 + adapt / 100.0 * 0.9 + (iq - 60) / 200.0
    return (LEARN_BASE + LEARN_RELATED * start_familiarity(p.position, slot)) * max(0.4, mult)


def add_familiarity(p, slot, amount, year=None):
    """Raise a player's familiarity at a slot (capped at 100)."""
    if slot == p.position or slot in RETURN_SLOTS or amount <= 0:
        return
    if getattr(p, "familiarity", None) is None:
        p.familiarity = {}
    cur = familiarity(p, slot)
    p.familiarity[slot] = round(min(100.0, cur + amount), 2)
    if year is not None:
        if getattr(p, "fam_used", None) is None:
            p.fam_used = {}
        p.fam_used[slot] = year
    clear_cache(p)


def offseason_decay(p, last_season):
    """Skills at another position fade a little without reps."""
    fam = getattr(p, "familiarity", None)
    if not fam:
        return
    used = getattr(p, "fam_used", None) or {}
    for slot in list(fam):
        if slot == p.position:
            del fam[slot]
            continue
        base = start_familiarity(p.position, slot)
        keep = KEEP_USED if used.get(slot) == last_season else KEEP_UNUSED
        v = base + (fam[slot] - base) * keep
        if v <= base + 0.5:
            del fam[slot]
        else:
            fam[slot] = round(v, 2)
    clear_cache(p)


# ── Size fit ──────────────────────────────────────────────────────────────────
# Weight outside a slot's normal range (mean ± SIZE_TOL standard deviations of
# that position's build) costs attribute points per standard deviation beyond
# the range: everything the slot asks of him a little (FRAME: he is playing
# out of his body type), plus the attributes mass decides much more - contact
# and leverage when he is too light, quickness when he is too heavy. The effect
# flattens out (SIZE_CAP) so absurd moves stay finite.

SIZE_TOL = 1.25
SIZE_CAP = 4.0
FRAME = 2.2
UNDER_ATTRS = {"strength": 4.5, "run_block": 3.5, "pass_block": 3.5, "impact_block": 3.5,
               "block_shedding": 3.5, "run_stop": 3.5, "power_move": 2.0, "break_tackle": 3.0,
               "contact_balance": 3.0, "hit_power": 2.0, "tackling": 1.2}
OVER_ATTRS = {"speed": 3.0, "acceleration": 3.4, "agility": 3.6, "jumping": 2.0, "stamina": 1.5}
NO_SIZE = {"K", "P", "QB"}


def _soft(u):
    return SIZE_CAP * (1.0 - math.exp(-u / SIZE_CAP)) if u > 0 else 0.0


def size_gap(p, slot):
    """(too light, too heavy) in standard deviations beyond the slot's normal range."""
    if slot == p.position or slot in NO_SIZE or slot in RETURN_SLOTS:
        return 0.0, 0.0
    from player import SIZE
    (_, _), (w_mu, w_sd) = SIZE[slot]
    z = (p.weight - w_mu) / w_sd
    return _soft(max(0.0, -z - SIZE_TOL)), _soft(max(0.0, z - SIZE_TOL))


def size_note(p, slot):
    under, over = size_gap(p, slot)
    from player import SIZE
    if slot not in SIZE:
        return ""
    w_mu, w_sd = SIZE[slot][1]
    if under > 0.05:
        return f"light for {slot} ({p.weight} lb, most are {int(w_mu - SIZE_TOL * w_sd)}+)"
    if over > 0.05:
        return f"heavy for {slot} ({p.weight} lb, most are under {int(w_mu + SIZE_TOL * w_sd)})"
    return ""


# ── Slot ratings ──────────────────────────────────────────────────────────────

def clear_cache(p):
    p.__dict__.pop("_fit_cache", None)


def slot_deltas(p, slot, fam=None):
    """
    {attribute: change} for this player at a slot that isn't his own position:
    the size fit plus the familiarity penalty. The match engine adds these to
    his attributes on every snap he plays there, and slot ratings use them too.
    """
    if slot == p.position or slot in RETURN_SLOTS:
        return {}
    d = {}
    under, over = size_gap(p, slot)
    if under or over:
        u = under + over
        for a in POSITION_WEIGHTS[slot]:
            if a not in _MENTAL:
                d[a] = -FRAME * u
        for a, k in UNDER_ATTRS.items():
            if under:
                d[a] = d.get(a, 0.0) - k * under
        for a, k in OVER_ATTRS.items():
            if over:
                d[a] = d.get(a, 0.0) - k * over
    pen = fam_penalty(familiarity(p, slot) if fam is None else fam)
    if pen > 0:
        known = _known_techniques(p)
        new_t, old_t = pen * NEW_TECH, pen * KNOWN_TECH
        for a in p.attrs:
            if a in _PHYSICAL:
                continue
            cut = pen if a in _MENTAL else old_t if a in known else new_t
            d[a] = d.get(a, 0.0) - cut
    return d


def _adjusted(p, deltas):
    if not deltas:
        return p.attrs
    a = dict(p.attrs)
    for k, v in deltas.items():
        a[k] = max(1.0, a.get(k, 30) + v)
    return a


def _cached(p, key, fn):
    c = p.__dict__.get("_fit_cache")
    if c is None:
        c = {}
        p.__dict__["_fit_cache"] = c
    v = c.get(key)
    if v is None:
        v = fn()
        c[key] = v
    return v


def slot_ca(p, slot):
    """Current ability (1-200) at a slot: the slot's formula on his attributes, size and familiarity."""
    if slot == p.position:
        return p.ca
    return _cached(p, ("ca", slot), lambda: compute_ca(_adjusted(p, slot_deltas(p, slot)), slot))


def formula_ca(p, slot):
    """The slot's formula on his raw attributes alone (no size fit, no familiarity)."""
    if slot == p.position:
        return p.ca
    return _cached(p, ("raw", slot), lambda: compute_ca(p.attrs, slot))


def learned_ca(p, slot):
    """Rating once he has fully learned the slot (size still counts)."""
    if slot == p.position:
        return p.ca
    return _cached(p, ("full", slot),
                   lambda: compute_ca(_adjusted(p, slot_deltas(p, slot, fam=100.0)), slot))


def coverage(own, slot):
    """Share of a slot's formula that his own position's development also builds."""
    w_own = POSITION_WEIGHTS[own]
    w = POSITION_WEIGHTS[slot]
    tot = float(sum(w.values()))
    return sum(v for a, v in w.items() if a in w_own) / tot if tot else 0.0


def slot_pot_ca(p, slot):
    """Projected peak at a slot: learned, and growing as he is growing at his own position."""
    if slot == p.position:
        return max(p.pa, p.ca)
    if p.years_to_peak() <= 0:
        return learned_ca(p, slot)
    grow = max(0, p.pa - p.ca) * coverage(p.position, slot)
    return min(200, int(round(learned_ca(p, slot) + grow)))


def breakdown(p, slot):
    """
    Why he is rated what he is at a slot: the formula on his attributes, what
    size and familiarity take off, and the attributes that matter most there.
    """
    raw = formula_ca(p, slot)
    full = learned_ca(p, slot)
    now = slot_ca(p, slot)
    fam = familiarity(p, slot)
    w = POSITION_WEIGHTS[slot]
    tot = float(sum(w.values()))
    d = slot_deltas(p, slot)
    keys = sorted(w, key=lambda a: -w[a])
    attrs = [(a, w[a] / tot, p.attrs.get(a, 30), d.get(a, 0.0)) for a in keys]
    return {
        "slot": slot, "natural": slot == p.position,
        "formula": ovr_from_ca(raw, slot), "after_size": ovr_from_ca(full, slot),
        "ovr": ovr_from_ca(now, slot), "pot": ovr_from_ca(slot_pot_ca(p, slot), slot),
        "familiarity": fam, "fam_label": familiarity_label(fam),
        "size": size_note(p, slot), "attrs": attrs,
        "weeks_to_learn": weeks_to_learn(p, slot),
    }


def weeks_to_learn(p, slot):
    """Rough weeks of full reps until he is Accomplished (90) at a slot."""
    fam = familiarity(p, slot)
    if fam >= 90.0:
        return 0
    return int(math.ceil((90.0 - fam) / max(0.5, learn_rate(p, slot))))


# ── Weekly learning ───────────────────────────────────────────────────────────

def weekly_learning(team, slot_snaps, year):
    """
    After a week: players listed at a slot other than their own position learn
    it from practice reps (more for starters), and from the snaps they played
    there (slot_snaps: {player id: {slot: snaps}}).
    """
    for slot in POSITIONS:
        order = team.depth(slot)
        n = STARTERS.get(slot, 1)
        for i, p in enumerate(order[:n + 2]):
            if p.position == slot:
                continue
            reps = PRACTICE_REPS[0] if i < n else PRACTICE_REPS[1] if i == n else PRACTICE_REPS[2]
            add_familiarity(p, slot, learn_rate(p, slot) * PRACTICE_SHARE * reps, year)
    for p in team.roster:
        played = slot_snaps.get(p.id)
        if not played:
            continue
        for slot, snaps in played.items():
            if slot == p.position:
                continue
            share = min(1.0, snaps / float(FULL_GAME_SNAPS))
            add_familiarity(p, slot, learn_rate(p, slot) * (1.0 - PRACTICE_SHARE) * share, year)
