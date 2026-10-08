"""
development.py — how players grow, peak and decline.

A player's yearly change is driven by many factors, each mattering more or
less depending on where he is in his career:

  Age & position curve   Running backs peak early and fall fast; quarterbacks,
                          linemen and kickers last longer.
  Talent gap (PA - CA)    Room left to grow.
  Work rate & ambition    Hard workers develop faster and decline slower.
  Coaching & facilities   The head coach's development rating and the
                          team's training facilities.
  Playing time            Starters develop faster than players stuck on the
                          bench.
  Durability & injuries   Missed time stunts growth; fragile bodies age worse.
  Reputation              Famous players with a poor work ethic can get
                          complacent.
  Morale                  Unhappy players develop slower.
  Chance                  Late bloomers, breakouts and busts happen.

Growth goes into real attributes: young players add strength and technique,
veterans keep their football IQ while their speed fades.
"""
import math
import random

from ratings import (POSITION_WEIGHTS, PHYSICAL_ATTRS, MENTAL_ATTRS, ATHLETIC_ATTRS,
                     AGE_CURVES, compute_ca)
from settings import settings


def _weights_for_change(player, growing):
    from ratings import ATTRIBUTES
    w = {}
    pos_w = POSITION_WEIGHTS[player.position]
    focus = getattr(player, "training_focus", None)
    for attr in player.attrs:
        base = pos_w.get(attr, 0.0)
        if growing:
            if base <= 0:
                continue
            if attr in ATHLETIC_ATTRS:
                base *= 0.9 if player.age <= 23 else 0.25
            elif attr == "strength":
                base *= 1.4 if player.age <= 25 else 0.6
            elif attr in MENTAL_ATTRS:
                base *= 1.2 if player.age >= 24 else 0.9
            if focus and ATTRIBUTES[attr][2] == focus:
                base *= 2.5
            w[attr] = base
        else:
            if attr in ATHLETIC_ATTRS:
                mult = 3.2
            elif attr in ("stamina", "strength"):
                mult = 1.6
            elif attr == "injury_resistance":
                mult = 1.2
            elif attr in MENTAL_ATTRS:
                mult = 0.15
            elif attr in PHYSICAL_ATTRS:
                mult = 1.0
            else:
                mult = 0.7
            if focus and ATTRIBUTES[attr][2] == focus:
                mult *= 0.5
            w[attr] = (base + 0.4) * mult
    return w


def _apply_ca_change(player, target):
    """Move attributes one point at a time until CA reaches `target`."""
    pos = player.position
    current = compute_ca(player.attrs, pos)
    growing = target > current
    weights = _weights_for_change(player, growing)
    keys = list(weights)
    vals = [weights[k] for k in keys]
    if not keys:
        return
    guard = 0
    while guard < 400:
        guard += 1
        current = compute_ca(player.attrs, pos)
        if growing and current >= target:
            break
        if not growing and current <= target:
            break
        attr = random.choices(keys, weights=vals, k=1)[0]
        step = 1 if growing else -1
        nv = player.attrs[attr] + step
        if 1 <= nv <= 99:
            player.attrs[attr] = nv


# ── Scheme fit ────────────────────────────────────────────────────────────────
# Archetypes a system gets the most out of (+) and ones it wastes (-).
SCHEME_FIT = {
    "Air Raid":      {"+": {"Slot", "Route Technician", "Pocket Passer", "Gunslinger", "Receiving Back",
                            "Pass Protector", "Pass Pro"},
                      "-": {"Blocking TE", "Lead Blocker", "Power Back", "Mauler"}},
    "West Coast":    {"+": {"Field General", "Possession", "Route Technician", "Receiving Back", "Complete TE"},
                      "-": {"Gunslinger", "Deep Threat"}},
    "Pro Style":     {"+": {"Pocket Passer", "Field General", "Complete TE", "Workhorse", "Balanced"},
                      "-": {"Scrambler"}},
    "Air Coryell":   {"+": {"Gunslinger", "Deep Threat", "Vertical Threat", "Contested Catch"},
                      "-": {"Game Manager"}},
    "Run and Shoot": {"+": {"Slot", "Deep Threat", "Route Technician"},
                      "-": {"Blocking TE", "Lead Blocker"}},
    "Spread Option": {"+": {"Dual Threat", "Scrambler", "Speed Back", "Elusive Back", "Zone Mover"},
                      "-": {"Pocket Passer", "Lead Blocker"}},
    "Power Run":     {"+": {"Power Back", "Workhorse", "Mauler", "Road Grader", "Blocking TE", "Lead Blocker"},
                      "-": {"Slot", "Receiving Back"}},
    "Zone Run":      {"+": {"Zone Mover", "Elusive Back", "Workhorse", "Complete TE"},
                      "-": {"Mauler"}},
    "4-3 Over":      {"+": {"Penetrator", "Complete Edge", "Mike", "Sideline to Sideline"}, "-": {"Nose Tackle"}},
    "3-4 Two Gap":   {"+": {"Nose Tackle", "Power Rusher", "Thumper", "Edge Setter"}, "-": {"Penetrator"}},
    "Tampa 2":       {"+": {"Zone Corner", "Coverage LB", "Speed Rusher", "Free Safety"}, "-": {"Press Corner"}},
    "46 Blitz":      {"+": {"Blitzer", "Strong Safety", "Man Corner", "Penetrator"}, "-": {"Zone Corner"}},
    "Cover 3":       {"+": {"Zone Corner", "Free Safety", "Speed Rusher"}, "-": {"Slot Corner"}},
    "Press Man":     {"+": {"Press Corner", "Man Corner", "Hybrid"}, "-": {"Zone Corner"}},
    "Two-High Match": {"+": {"Hybrid", "Coverage LB", "Slot Corner", "Free Safety"}, "-": {"Thumper"}},
    "Zone Blitz":    {"+": {"Blitzer", "Interior Rusher", "Zone Corner", "Complete Edge"}, "-": {"Nose Tackle"}},
}

OFF_POS = {"QB", "RB", "FB", "WR", "TE", "OT", "IOL"}


def scheme_fit(player, team):
    if team is None or not player.archetype:
        return 0
    scheme = team.coach.off_scheme if player.position in OFF_POS else team.coach.def_scheme
    fit = SCHEME_FIT.get(scheme, {})
    if player.archetype in fit.get("+", ()):
        return 1
    if player.archetype in fit.get("-", ()):
        return -1
    return 0


def _mentor(player, team):
    """A respected veteran at the same position who takes a young player under his wing."""
    if team is None or player.age > 25:
        return None
    for v in team.roster:
        if v is player or v.position != player.position or v.age < 29:
            continue
        if v.attrs.get("leadership", 50) >= 70 and v.hidden.get("work_rate", 50) >= 65:
            return v
    return None


def _ca_to_ovr_delta(player, d_ca):
    from ratings import OVR_ANCHORS, OVR_SPREAD
    return d_ca * OVR_SPREAD / OVR_ANCHORS[player.position][1]


FACTOR_LABELS = {
    "age": "Age & career stage", "talent": "Untapped potential", "work": "Work ethic",
    "ambition": "Ambition", "coaching": "Coaching", "facilities": "Facilities",
    "playing_time": "Playing time", "production": "On-field production",
    "injury": "Injuries", "morale": "Morale", "complacency": "Complacency",
    "scheme": "Scheme fit", "mentor": "Veteran mentor", "contract": "Contract year",
    "culture": "Team culture", "durability": "Durability", "luck": "Natural variation",
}


def yearly_change(player, team, gp=None, gs=None, last_season=None, detail=False):
    """
    Expected CA change this offseason (can be negative).
    With detail=True returns (change, base, {factor: multiplier}).
    """
    grow, prime_end, severity = player.curve()
    age = player.age
    h = player.hidden
    gap = max(0, player.pa - player.ca)
    work = h.get("work_rate", 50)
    amb = h.get("ambition", 50)
    gp = player.last_season_gp if gp is None else gp
    gs = player.last_season_gs if gs is None else gs

    import staff as staff_mod
    coach_dev = staff_mod.dev_rating(team, player.position) if team else 8
    facilities = team.facilities if team else 6
    ev = getattr(player, "season_eval", None) or {}
    if ev.get("year") != last_season:
        ev = {}

    m = {}
    m["work"] = 0.55 + work / 100.0 * 0.75
    m["ambition"] = 0.85 + amb / 100.0 * 0.30
    m["coaching"] = 0.80 + coach_dev / 20.0 * 0.35
    m["facilities"] = 0.90 + facilities / 20.0 * 0.20
    # Playing time: snaps matter more than the depth chart
    share = min(1.0, gs / 17.0) if gs else min(0.5, gp / 34.0)
    if getattr(player, "was_ps", None) == last_season and gp < 4:
        m["playing_time"] = 0.97
    elif player.years_pro == 0 and gp == 0:
        m["playing_time"] = 0.95
    else:
        m["playing_time"] = 0.82 + share * 0.36
    # Production relative to his ability (outplaying his rating builds confidence)
    if ev.get("prod_pct") is not None and gp >= 4:
        m["production"] = 1.0 + (ev["prod_pct"] - ev.get("ca_pct", 0.5)) * 0.35
    weeks_missed = sum(w for (yr, _, w) in player.injury_history if yr == last_season)
    if weeks_missed >= 4:
        m["injury"] = 0.95 if weeks_missed < 10 else 0.80
    m["morale"] = 0.9 + player.morale / 100.0 * 0.2
    if player.reputation > 70 and work < 45:
        m["complacency"] = 0.85
    fit = scheme_fit(player, team)
    if fit:
        m["scheme"] = 1.06 if fit > 0 else 0.95
    if _mentor(player, team) is not None:
        m["mentor"] = 1.06
    if getattr(player, "contract_year", None) == last_season:
        m["contract"] = 1.0 + amb / 100.0 * 0.10
    if team is not None and team.history and team.history[-1]["year"] == last_season:
        hist = team.history[-1]
        g = max(1, hist["w"] + hist["l"] + hist["t"])
        pct = (hist["w"] + 0.5 * hist["t"]) / g
        if pct >= 0.65:
            m["culture"] = 1.03
        elif pct <= 0.30:
            m["culture"] = 0.97

    mult = 1.0
    for v in m.values():
        mult *= v

    if age < grow:
        years_left = max(1.0, grow - age + 1)
        base = gap / years_left * 0.95 * settings["growth_rate"]
        expected = base * mult
        change = expected * random.lognormvariate(0, 0.38)
    elif age <= prime_end:
        wear = 0.0 if age < grow + 2 else 0.8 + (age - grow - 2) * 0.35
        base = gap * 0.20 * settings["growth_rate"]
        expected = base * mult - wear
        m["age"] = None
        base_age = -wear
        change = expected + random.gauss(0, 2.2)
    else:
        years_past = age - prime_end
        # Decline eases in rather than starting on a set birthday
        loss = severity * (0.55 + 0.45 * years_past) if years_past < 1 else \
            severity * (1 + 0.35 * (years_past - 1))
        base = -loss * settings["decline_rate"]
        # In decline the multipliers mostly *slow the fall*
        slow = (1.25 - work / 100.0 * 0.5) * (1.12 - player.a("injury_resistance") / 100.0 * 0.25)
        if m.get("production"):
            slow *= max(0.75, min(1.15, 2.0 - m["production"]))
        slow *= 1.0 - (coach_dev - 10) * 0.012
        expected = base * slow
        change = -max(0.0, random.gauss(-expected, -expected * 0.35 + 1.0))
        m = {"work": None, "durability": None, "production": m.get("production"),
             "coaching": None}
        if not detail:
            return change
        return change, expected, {"__decline__": slow, **{k: v for k, v in m.items() if v is not None}}
    if not detail:
        return change
    out = {k: v for k, v in m.items() if v is not None}
    if age >= grow and age <= prime_end:
        out["__wear__"] = base_age
    return change, expected, out


def _report(player, team, year, change_ca, expected_ca, factors, note, stage):
    """
    The staff's explanation of the offseason. Accuracy depends on the coaches:
    good development staff see the real causes, poor ones guess.
    """
    import staff as staff_mod
    acc = staff_mod.dev_rating(team, player.position) if team else 6
    noise = max(0.2, (20 - acc) / 20.0 * 1.6)
    items = []
    total_ovr = _ca_to_ovr_delta(player, change_ca)
    exp_ovr = _ca_to_ovr_delta(player, expected_ca)
    if stage == "decline":
        items.append(("age", -abs(exp_ovr) if exp_ovr < 0 else exp_ovr))
        slow = factors.get("__decline__", 1.0)
        # Work ethic / durability slowing the decline show up as positives
        if slow < 1.0:
            items.append(("work", abs(exp_ovr) * (1 - slow) * 0.6))
            items.append(("durability", abs(exp_ovr) * (1 - slow) * 0.4))
        elif slow > 1.0:
            items.append(("work", -abs(exp_ovr) * (slow - 1) * 0.6))
            items.append(("durability", -abs(exp_ovr) * (slow - 1) * 0.4))
    else:
        mults = {k: v for k, v in factors.items() if not k.startswith("__")}
        wear_ovr = _ca_to_ovr_delta(player, factors.get("__wear__", 0.0))
        gross = exp_ovr - wear_ovr
        total_mult = 1.0
        for v in mults.values():
            total_mult *= v
        base_ovr = gross / max(0.2, total_mult)
        items.append(("talent", base_ovr))
        first = {k: base_ovr * (v - 1.0) for k, v in mults.items()}
        tot = sum(first.values())
        target = gross - base_ovr
        scale = target / tot if abs(tot) > 1e-6 else 0.0
        for k, v in first.items():
            items.append((k, v * scale))
        if wear_ovr:
            items.append(("age", wear_ovr))
    items.append(("luck", total_ovr - sum(v for _, v in items)))
    # The staff's (imperfect) view
    seen = []
    for k, v in items:
        est = v + random.gauss(0, noise)
        if abs(est) < 0.35 and k not in ("age", "talent"):
            continue
        seen.append((FACTOR_LABELS.get(k, k), round(est, 1)))
    seen.sort(key=lambda x: -abs(x[1]))
    rep = {"year": year, "ovr_change": round(total_ovr), "factors": seen[:7], "note": note,
           "coach": (team.staff.get(staff_mod.POSITION_COACH.get(player.position, "STC")).name
                     if team is not None and getattr(team, "staff", None) else "Scouts"),
           "accuracy": acc, "text": _staff_quote(player, total_ovr, seen, note, stage)}
    player.dev_reports = (getattr(player, "dev_reports", None) or [])[-9:] + [rep]
    return rep


def _staff_quote(player, ovr_change, seen, note, stage):
    first = player.name.split(" ")[0]
    if note == "breakout":
        return f"Something clicked for {first} this offseason. He looks like a different player."
    if note == "bust":
        return f"We're worried {first} has hit his ceiling. The tools haven't translated."
    top = seen[0][0].lower() if seen else "natural development"
    if stage == "decline":
        if ovr_change <= -4:
            return f"Father Time is catching up with {first}. He's lost a step."
        return f"{first} is managing the decline well — the experience shows."
    if ovr_change >= 4:
        return f"Big jump for {first}. {top.capitalize()} made the difference."
    if ovr_change >= 1:
        return f"Steady progress from {first}; {top} helped most."
    if ovr_change <= -2:
        return f"A frustrating year for {first}. {top.capitalize()} held him back."
    return f"{first} more or less held his level."


def _drift_potential(player, team, last_season, surprise):
    """
    A young player's ceiling isn't fixed. Every offseason before his peak it
    moves: hard work, good coaching, real snaps and strong play push it up;
    injuries, idleness and poor habits pull it down — and the younger he is,
    the more it can move.
    """
    grow = player.curve()[0]
    years = grow - player.age
    if years <= 0:
        return 0
    h = player.hidden
    import staff as staff_mod
    dev = staff_mod.dev_rating(team, player.position) if team else 8
    gs = player.last_season_gs or 0
    share = min(1.0, gs / 17.0)
    weeks_missed = sum(w for (yr, _, w) in player.injury_history if yr == last_season)
    mu = (h.get("work_rate", 50) - 50) / 50.0 * 1.2 + (h.get("ambition", 50) - 50) / 50.0 * 0.5 \
        + (dev - 10) / 10.0 * 0.8 + surprise * 2.0
    if player.years_pro > 0:
        mu += (share - 0.4) * 1.5
    if weeks_missed >= 8:
        mu -= 1.5
    sd = 1.0 + min(8.0, years) * 0.75
    d = random.gauss(mu - 0.6, sd)           # centred so the league's ceiling doesn't creep up
    if d > 0 and player.pa >= 160:
        d *= 0.5                             # the very top is hard to raise further
    d = int(round(d))
    player.pa = max(player.ca, min(200, player.pa + d))
    player.pa_change = (last_season, d)
    return d


def develop(player, team, last_season=None):
    """Run one offseason of development. Returns (old_ca, new_ca, note)."""
    old = player.ca
    note = None
    age = player.age
    grow, prime_end, _ = player.curve()

    # Breakouts and busts (young players only) — more likely after a big or a bad year
    ev = getattr(player, "season_eval", None) or {}
    surprise = (ev.get("prod_pct", 0.5) - ev.get("ca_pct", 0.5)) if ev.get("year") == last_season else 0.0
    _drift_potential(player, team, last_season, surprise)
    if age <= grow - 1 and random.random() < (0.02 + max(0.0, surprise) * 0.05) * settings["breakout_rate"]:
        bump = random.randint(4, 15)
        player.pa = min(200, player.pa + bump)
        note = "breakout"
    elif age <= grow - 2 and random.random() < (0.03 + max(0.0, -surprise) * 0.04) * settings["bust_rate"]:
        player.pa = max(player.ca, player.pa - random.randint(8, 25))
        note = "bust"

    change, expected, factors = yearly_change(player, team, last_season=last_season, detail=True)
    if note == "breakout":
        change += max(0, player.pa - player.ca) * 0.35
    target = int(round(player.ca + change))
    if change > 0:
        target = min(target, player.pa)
    target = max(1, min(200, target))
    if target != player.ca:
        _apply_ca_change(player, target)

    # Experience: football IQ keeps growing with snaps
    if age <= 33 and player.last_season_gp >= 6:
        for attr in random.sample(MENTAL_ATTRS, 2):
            if POSITION_WEIGHTS[player.position].get(attr, 0) > 0 and random.random() < 0.6:
                player.attrs[attr] = min(99, player.attrs[attr] + 1)
    # Ageing bodies get more fragile
    if age >= 29:
        player.attrs["injury_resistance"] = max(1, player.attrs["injury_resistance"]
                                                - random.choice([0, 1, 1, 2]))
    player.recalc()
    if player.ca > player.pa:
        player.pa = player.ca
    if age > prime_end:
        player.pa = player.ca          # past his prime, his ceiling is what he is
    player.last_change = player.ca - old
    stage = "decline" if age > prime_end else "growth" if age < grow else "prime"
    _report(player, team, last_season, player.ca - old, expected, factors, note, stage)
    return old, player.ca, note


def midseason(player, team, year):
    """
    A smaller in-season change for young players: a rookie who's thriving can
    take a jump by mid-season; one who's struggling can regress.
    """
    grow, _, _ = player.curve()
    if player.age >= grow + 1:
        return 0
    s = player.season_stats
    if s["gp"] < 4:
        return 0
    gap = max(0, player.pa - player.ca)
    work = player.hidden.get("work_rate", 50)
    snaps = s["gs"] / max(1, s["gp"])
    base = gap * 0.06 * (0.6 + work / 100.0 * 0.6) * (0.7 + snaps * 0.5) * settings["growth_rate"]
    form = getattr(player, "form_carry", 0.0)
    change = base + form * 0.25 + random.gauss(0, 1.2)
    target = int(round(player.ca + change))
    target = max(1, min(player.pa, target)) if change > 0 else max(1, target)
    if target == player.ca:
        return 0
    old = player.ca
    _apply_ca_change(player, target)
    player.recalc()
    d = player.ca - old
    player.midseason_change = (year, d)
    return d


# ── Retirement ────────────────────────────────────────────────────────────────

TYPICAL_RETIREMENT = {
    "QB": 37, "RB": 30, "FB": 31, "WR": 33, "TE": 33, "OT": 34, "IOL": 34,
    "DT": 33, "EDGE": 33, "LB": 32, "CB": 32, "S": 33, "K": 39, "P": 39,
}


def retirement_chance(player, unsigned=False):
    age = player.age
    typical = TYPICAL_RETIREMENT[player.position] + settings["retirement_age_shift"]
    p = 0.0
    if age >= typical - 3:
        p = 1.0 / (1.0 + pow(2.718, -(age - typical) / 1.4))
    # Fading players walk away earlier; stars hang on
    if player.ca < 95 and age >= 29:
        p += 0.20
    if player.ca >= 150:
        p *= 0.55
    if unsigned and age >= 27:
        p += 0.35 if player.ca < 110 else 0.15
    if player.injury and player.injury.get("weeks", 0) > 20 and age >= 29:
        p += 0.25
    amb = player.hidden.get("ambition", 50)
    p *= 1.15 - amb / 100.0 * 0.3
    return max(0.0, min(0.98, p))
