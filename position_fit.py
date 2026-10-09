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

A permanent position change (`move`) makes the new slot his listed position:
contracts, roster counts and development follow it from then on. Until he has
learned it he is "converting" (`Player.converted_from` keeps the position his
frame and instincts were built for), so his rating at his new position still
carries the size and familiarity costs, and he keeps practising it. Each
offseason his conditioning moves his weight toward the new position's range
(`offseason_conditioning`); once he knows the position and fits it, he is
settled and it becomes his natural position.

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
# Reps a player gets at a second position he trains (or the new position of a
# conversion) when he isn't high enough on that slot's depth list to get more
TRAIN_REPS = 0.6
# Weeks of practice reps in training camp before the season starts
CAMP_WEEKS = 3
# Familiarity at which a converting player has learned his new position
SETTLED = 99.5
SETTLE_SIZE = 0.25            # size gap (in sd) a settled player may still have

_TECHNIQUE = {}
for _pos, _w in POSITION_WEIGHTS.items():
    _TECHNIQUE[_pos] = {a for a in _w if a not in MENTAL_ATTRS and a not in PHYSICAL_ATTRS}
_MENTAL = set(MENTAL_ATTRS)
_PHYSICAL = set(PHYSICAL_ATTRS)


def home(p):
    """The position his frame and instincts were built for (his own, unless he is converting)."""
    return getattr(p, "converted_from", None) or p.position


def natural(p, slot):
    """True when he plays a slot with no adjustments at all: his own position, fully his."""
    return slot in RETURN_SLOTS or (slot == p.position and not getattr(p, "converted_from", None))


def start_familiarity(own, slot):
    if own == slot:
        return 100.0
    return float(RELATED.get(own, {}).get(slot, DEFAULT_START))


def familiarity(p, slot):
    """How well this player knows a slot (0-100). His own position is 100 unless he is still learning it."""
    if slot in RETURN_SLOTS:
        return 100.0
    fam = getattr(p, "familiarity", None)
    if fam and slot in fam:
        return fam[slot]
    if slot == p.position:
        return 100.0
    return start_familiarity(home(p), slot)


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
    known = set(_TECHNIQUE.get(home(p), ()))
    fam = getattr(p, "familiarity", None)
    if fam:
        for s, v in fam.items():
            if v >= 90.0 and s in _TECHNIQUE:
                known |= _TECHNIQUE[s]
    return known


def coaching_mult(team, slot):
    """How much faster good position coaches teach a slot (0.85 to 1.15)."""
    if team is None:
        return 1.0
    import staff as staff_mod
    return 0.85 + staff_mod.dev_rating(team, slot) / 20.0 * 0.30


def learn_rate(p, slot, team=None):
    """Familiarity gained in a week of full reps at a slot."""
    adapt = p.hidden.get("adaptability", 50)
    iq = p.attrs.get("awareness", 60)
    mult = 0.55 + adapt / 100.0 * 0.9 + (iq - 60) / 200.0
    return (LEARN_BASE + LEARN_RELATED * start_familiarity(home(p), slot)) * max(0.4, mult) * \
        coaching_mult(team, slot)


def add_familiarity(p, slot, amount, year=None):
    """Raise a player's familiarity at a slot (capped at 100)."""
    if natural(p, slot) or amount <= 0:
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
    if slot == p.position:
        p.recalc()                  # his rating at his new position moves as he learns it
        settle(p)


def offseason_decay(p, last_season):
    """Skills at another position fade a little without reps."""
    fam = getattr(p, "familiarity", None)
    if not fam:
        return
    used = getattr(p, "fam_used", None) or {}
    for slot in list(fam):
        if slot == p.position:
            if not getattr(p, "converted_from", None):
                del fam[slot]
            continue                # a position he is converting to is practised every day
        base = start_familiarity(home(p), slot)
        keep = KEEP_USED if used.get(slot) == last_season else KEEP_UNUSED
        v = base + (fam[slot] - base) * keep
        if v <= base + 0.5:
            del fam[slot]
        else:
            fam[slot] = round(v, 2)
    clear_cache(p)
    settle(p)


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


def weight_range(slot):
    """(lightest, heaviest) normal weight at a slot."""
    from player import SIZE
    w_mu, w_sd = SIZE[slot][1]
    return w_mu - SIZE_TOL * w_sd, w_mu + SIZE_TOL * w_sd


def size_gap(p, slot, weight=None):
    """(too light, too heavy) in standard deviations beyond the slot's normal range."""
    if slot == home(p) or slot in NO_SIZE or slot in RETURN_SLOTS:
        return 0.0, 0.0
    from player import SIZE
    (_, _), (w_mu, w_sd) = SIZE[slot]
    z = ((p.weight if weight is None else weight) - w_mu) / w_sd
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


def slot_deltas(p, slot, fam=None, weight=None):
    """
    {attribute: change} for this player at a slot that isn't naturally his:
    the size fit plus the familiarity penalty. The match engine adds these to
    his attributes on every snap he plays there, and slot ratings use them too.
    """
    if natural(p, slot):
        return {}
    d = {}
    under, over = size_gap(p, slot, weight)
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


def converted_ca(p):
    """CA at his listed position while he is still converting to it (Player.recalc)."""
    return compute_ca(_adjusted(p, slot_deltas(p, p.position)), p.position)


def slot_ca(p, slot):
    """Current ability (1-200) at a slot: the slot's formula on his attributes, size and familiarity."""
    if slot == p.position:
        return p.ca
    return _cached(p, ("ca", slot), lambda: compute_ca(_adjusted(p, slot_deltas(p, slot)), slot))


def formula_ca(p, slot):
    """The slot's formula on his raw attributes alone (no size fit, no familiarity)."""
    if natural(p, slot):
        return p.ca
    return _cached(p, ("raw", slot), lambda: compute_ca(p.attrs, slot))


def learned_ca(p, slot, conditioned=False):
    """
    Rating once he has fully learned the slot (size still counts). With
    conditioned=True, also once a conversion's conditioning has moved his
    weight as far toward the slot's range as it can.
    """
    if natural(p, slot):
        return p.ca
    if conditioned:
        w = target_weight(p, slot)
        if w != p.weight:
            return _cached(p, ("cond", slot),
                           lambda: compute_ca(_adjusted(p, slot_deltas(p, slot, fam=100.0, weight=w)), slot))
    return _cached(p, ("full", slot),
                   lambda: compute_ca(_adjusted(p, slot_deltas(p, slot, fam=100.0)), slot))


def coverage(own, slot):
    """Share of a slot's formula that his own position's development also builds."""
    w_own = POSITION_WEIGHTS[own]
    w = POSITION_WEIGHTS[slot]
    tot = float(sum(w.values()))
    return sum(v for a, v in w.items() if a in w_own) / tot if tot else 0.0


def slot_pot_ca(p, slot):
    """Projected peak at a slot: learned (and conditioned), growing as he is growing at his own position."""
    if slot == p.position:
        return max(p.pa, p.ca)
    base = learned_ca(p, slot, conditioned=True)
    if p.years_to_peak() <= 0:
        return base
    grow = max(0, p.pa - p.ca) * coverage(p.position, slot)
    return min(200, int(round(base + grow)))


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
        "slot": slot, "natural": natural(p, slot),
        "formula": ovr_from_ca(raw, slot), "after_size": ovr_from_ca(full, slot),
        "ovr": ovr_from_ca(now, slot), "pot": ovr_from_ca(slot_pot_ca(p, slot), slot),
        "familiarity": fam, "fam_label": familiarity_label(fam),
        "size": size_note(p, slot), "attrs": attrs,
        "weeks_to_learn": weeks_to_learn(p, slot),
    }


def weeks_to_learn(p, slot, team=None):
    """Rough weeks of full reps until he is Accomplished (90) at a slot."""
    fam = familiarity(p, slot)
    if fam >= 90.0:
        return 0
    return int(math.ceil((90.0 - fam) / max(0.5, learn_rate(p, slot, team))))


# ── Weekly learning ───────────────────────────────────────────────────────────

def weekly_learning(team, slot_snaps, year, weeks=1.0):
    """
    After a week: players listed at a slot that isn't naturally theirs learn it
    from practice reps (more for starters), and from the snaps they played
    there (slot_snaps: {player id: {slot: snaps}}). A player converting to a
    new position, or training a second one, always gets at least a backup's
    reps there. weeks > 1 with no snaps is training camp.
    """
    given = {}
    for slot in POSITIONS:
        order = team.depth(slot)
        n = STARTERS.get(slot, 1)
        for i, p in enumerate(order[:n + 2]):
            if natural(p, slot):
                continue
            reps = PRACTICE_REPS[0] if i < n else PRACTICE_REPS[1] if i == n else PRACTICE_REPS[2]
            given[(p.id, slot)] = reps
            add_familiarity(p, slot, learn_rate(p, slot, team) * PRACTICE_SHARE * reps * weeks, year)
    for p in team.roster:
        targets = []
        if getattr(p, "converted_from", None):
            targets.append(p.position)
        tp = getattr(p, "train_pos", None)
        if tp and tp not in targets:
            targets.append(tp)
        for slot in targets:
            if natural(p, slot) or p.ir:
                continue
            extra = TRAIN_REPS - given.get((p.id, slot), 0.0)
            if extra > 0:
                add_familiarity(p, slot, learn_rate(p, slot, team) * PRACTICE_SHARE * extra * weeks, year)
        played = slot_snaps.get(p.id)
        if not played:
            continue
        for slot, snaps in played.items():
            if natural(p, slot):
                continue
            share = min(1.0, snaps / float(FULL_GAME_SNAPS))
            add_familiarity(p, slot, learn_rate(p, slot, team) * (1.0 - PRACTICE_SHARE) * share, year)


def training_camp(team, year):
    """Preseason practice: CAMP_WEEKS of reps for everyone learning a slot, before week 1."""
    weekly_learning(team, {}, year, weeks=CAMP_WEEKS)


# ── Permanent position changes ────────────────────────────────────────────────
# Conditioning: each offseason a converting player's weight moves toward his
# new position's normal range, by more when he is young, never more than
# CONDITION_MAX from where he started. Mass costs quickness and adds strength;
# losing it does the opposite.

CONDITION_MAX = 25            # lb a conversion can add or take off in all
CONDITION_STEP = ((25, 14), (29, 10), (99, 6))   # (up to age, lb per offseason)
GAIN_COST = {"speed": 0.08, "acceleration": 0.08, "agility": 0.06}
GAIN_BONUS = {"strength": 0.08}
LOSS_COST = {"strength": 0.08}
LOSS_BONUS = {"acceleration": 0.04, "agility": 0.04}


def target_weight(p, slot):
    """The weight a conversion to `slot` would get him to: the slot's range, within CONDITION_MAX."""
    if slot in NO_SIZE or slot in RETURN_SLOTS or slot == home(p):
        return p.weight
    lo, hi = weight_range(slot)
    base = getattr(p, "base_weight", None) or p.weight
    want = lo if p.weight < lo else hi if p.weight > hi else p.weight
    return int(round(max(base - CONDITION_MAX, min(base + CONDITION_MAX, want))))


def offseason_conditioning(p):
    """A converting player's offseason program. Returns the weight change in lb."""
    if not getattr(p, "converted_from", None):
        return 0
    goal = target_weight(p, p.position)
    if goal == p.weight:
        return 0
    step = next(lb for age, lb in CONDITION_STEP if p.age <= age)
    d = max(-step, min(step, goal - p.weight))
    p.weight += d
    cost, bonus = (GAIN_COST, GAIN_BONUS) if d > 0 else (LOSS_COST, LOSS_BONUS)
    for a, k in cost.items():
        p.attrs[a] = max(1, int(round(p.attrs.get(a, 50) - k * abs(d))))
    for a, k in bonus.items():
        p.attrs[a] = min(99, int(round(p.attrs.get(a, 50) + k * abs(d))))
    p.recalc()
    settle(p)
    return d


def settle(p):
    """A converting player who knows his new position and fits it is now a natural there."""
    origin = getattr(p, "converted_from", None)
    if not origin:
        return False
    if familiarity(p, p.position) < SETTLED or max(size_gap(p, p.position)) > SETTLE_SIZE:
        return False
    fam = p.familiarity if p.familiarity is not None else {}
    fam[origin] = familiarity(p, origin)        # he still knows where he came from
    fam.pop(p.position, None)
    p.familiarity = fam
    p.converted_from = None
    p.base_weight = None
    p.recalc()
    return True


def move(p, new, year=None):
    """
    Make `new` his listed position. What he knows of it carries over (he keeps
    learning it), his old position stays known, his potential is re-set to his
    projected peak at the new position, and his role is re-read for it.
    """
    old = p.position
    if new == old or new not in POSITIONS:
        return False
    origin = home(p)
    fam_new = familiarity(p, new)
    fam_old = familiarity(p, old)
    pot = slot_pot_ca(p, new)
    fam = dict(p.familiarity or {})
    fam[old] = fam_old
    if new == origin:
        fam.pop(new, None)
        p.converted_from = None
        p.base_weight = None
    else:
        fam[new] = fam_new
        p.converted_from = origin
        if getattr(p, "base_weight", None) is None:
            p.base_weight = p.weight
    p.familiarity = fam
    p.position = new
    p.position_history = list(getattr(p, "position_history", None) or []) + [(year, old, new)]
    if getattr(p, "train_pos", None) == new:
        p.train_pos = None
    p.recalc()
    p.pa = max(p.ca, min(200, int(pot)))
    roles = p.roles
    if roles:
        p.archetype = roles[0][0]
    settle(p)
    return True


def would_start(team, p, slot, learned=True):
    """Would he be one of the starters at `slot` (once he has learned it, by default)?"""
    if team is None:
        return False
    n = STARTERS.get(slot, 1)
    others = [q for q in team.depth(slot) if q.id != p.id]
    if len(others) < n:
        return True
    v = learned_ca(p, slot, conditioned=True) if learned else slot_ca(p, slot)
    return v > min(q.rating_at(slot) for q in others[:n])


def change_position(lg, team, p, slot):
    """
    A club's permanent move of one of its players: his reaction (morale), the
    move itself, his depth chart places and a transaction. Returns (morale
    change, his reaction in a few words).
    """
    old = p.position
    before = team is not None and p in team.depth(old)[:STARTERS.get(old, 1)]
    after = would_start(team, p, slot)
    d, word = move_mood(p, slot, before, after)
    if not move(p, slot, lg.year):
        return 0, ""
    p.morale = int(max(1, min(100, p.morale + d)))
    if team is not None:
        ov = team.depth_overrides
        if p.id in ov.get(old, []):
            ov[old] = [i for i in ov[old] if i != p.id]
        locks = team.depth_locks or {}
        if p.id in locks.get(old, []):
            locks[old] = [i for i in locks[old] if i != p.id]
        if slot in ov and p.id not in ov[slot]:
            score = team.depth_score(p, slot)
            ids = ov[slot]
            byid = {q.id: q for q in team.roster}
            i = next((k for k, pid in enumerate(ids)
                      if pid in byid and team.depth_score(byid[pid], slot) < score), len(ids))
            ov[slot] = ids[:i] + [p.id] + ids[i:]
        lg.add_transaction(f"{team.abbr} moved {p.name} from {old} to {slot}")
    return d, word


def conversion_status(p):
    """One line on a converting player: where he came from, how well he knows it, his conditioning."""
    origin = getattr(p, "converted_from", None)
    if not origin:
        return ""
    fam = familiarity(p, p.position)
    parts = [f"Converted from {origin}"]
    if fam < SETTLED:
        parts.append(f"knows {p.position}: {familiarity_label(fam)} {fam:.0f}")
    goal = target_weight(p, p.position)
    if goal != p.weight:
        parts.append(f"conditioning to {goal} lb")
    else:
        note = size_note(p, p.position)
        if note:
            parts.append(note)
    return " · ".join(parts)


# ── How players take it ───────────────────────────────────────────────────────
# Mild morale effects that depend on who he is: adaptable players enjoy a new
# challenge, ambitious ones hate a move to a position that is paid less, stars
# don't like being moved off their spot, and everyone likes a chance to start.

def move_mood(p, new, starts_before=False, starts_after=False):
    """(morale change, his reaction in a few words) to a permanent move to `new`."""
    from contracts import POSITION_MAX_SHARE
    h = p.hidden
    adapt, amb, temper = h.get("adaptability", 50), h.get("ambition", 50), h.get("temperament", 50)
    d = (adapt - 50) / 12.0
    pay = POSITION_MAX_SHARE.get(new, 0.06) / POSITION_MAX_SHARE.get(p.position, 0.06)
    if pay < 1.0:
        d -= (1.0 - pay) * 8.0 * (0.5 + amb / 100.0)
    else:
        d += min(3.0, (pay - 1.0) * 3.0) * amb / 100.0
    if starts_after and not starts_before:
        d += 4.0
    elif starts_before and not starts_after:
        d -= 5.0
    if starts_before and p.reputation >= 60:
        d -= (p.reputation - 60) / 10.0
    d *= 1.3 - temper / 100.0 * 0.6
    d = int(round(max(-12.0, min(8.0, d))))
    word = ("excited about it" if d >= 4 else "open to it" if d >= 1 else "fine with it" if d >= -1
            else "not happy about it" if d >= -5 else "upset about it")
    return d, word


def snaps_mood(p):
    """Weekly morale change for a player who spent real time away from his listed position."""
    h = p.hidden
    adapt, amb, temper = h.get("adaptability", 50), h.get("ambition", 50), h.get("temperament", 50)
    d = (adapt - 50) / 50.0 * 0.6
    if p.reputation >= 50:
        d -= max(0, amb - 60) / 40.0 * 0.6
    return d * (1.3 - temper / 100.0 * 0.6)


# ── The staff's view of other positions ──────────────────────────────────────

def _verdict(own_ovr, learned, weeks):
    if learned >= own_ovr - 2:
        return "Natural fit" if weeks <= 6 else "Worth the work"
    if learned >= own_ovr - 7:
        return "Could make the switch" if weeks <= 17 else "Long project"
    if learned >= own_ovr - 12:
        return "Emergency option"
    return "Not suited"


def staff_report(p, team, year, slots=None, n=5):
    """
    What the coaches think he could be at other positions: rows of
    {slot, now, learned, pot, familiarity, label, weeks, size, verdict, accuracy}.
    It is their opinion: ratings carry an error that shrinks with the quality of
    the position coach for that slot (the same error all season).
    """
    import random as _random
    import staff as staff_mod
    cand = [s for s in POSITIONS if s != p.position and s not in ("K", "P")] if slots is None else \
        [s for s in slots if s != p.position]
    rows = []
    own = ovr_from_ca(p.ca, p.position) if p.converted_from is None else \
        ovr_from_ca(learned_ca(p, p.position, conditioned=True), p.position)
    for s in cand:
        acc = staff_mod.dev_rating(team, s) if team is not None else 6.0
        err = max(0.5, (20.0 - acc) / 20.0 * 5.0)
        r = _random.Random(f"{p.id}:{s}:{year}")
        e = r.gauss(0, err)
        now = ovr_from_ca(slot_ca(p, s), s)
        full = ovr_from_ca(learned_ca(p, s, conditioned=True), s)
        pot = ovr_from_ca(slot_pot_ca(p, s), s)
        fam = familiarity(p, s)
        weeks = weeks_to_learn(p, s, team)
        rows.append({"slot": s, "now": int(round(now + e)), "learned": int(round(full + e)),
                     "pot": int(round(pot + e)), "familiarity": fam, "label": familiarity_label(fam),
                     "weeks": weeks, "size": size_note(p, s), "accuracy": acc,
                     "weight": target_weight(p, s),
                     "verdict": _verdict(own, full + e, weeks)})
    rows.sort(key=lambda x: -x["learned"])
    return rows if slots is not None else rows[:n]
