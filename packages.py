"""
packages.py — package slots and defensive packages (plain data + small functions).

A package slot is a depth chart list for one job inside a personnel group:
the third-down back, the slot receiver, the nickel corner and so on. Each one
plays a base position (the slot labels, familiarity, size fit and learning are
that position's) and is rated with that position's role formula (a third-down
back is judged as a Receiving Back). Anyone can be listed; the natural pool is
the players at the positions in POOL.

"Adds" packages put extra men on the field beside the base starters (a slot
receiver in 3-receiver sets, a nickel corner, a third safety, a third tight
end). Their players are picked first and the base list fills around them, so
listing your best receiver first at SLOT moves him inside. Auto order lists
the base starters last, so by default a package adds the next best man.
"Replace" packages swap for base players in their situation (a third-down
back for the lead back, pass-rush ends and tackles on passing downs, the
linebackers who stay on in nickel and dime).
"""
from ratings import ovr_from_ca, role_ca

# slot: (base position, roles (best one counts), starters, adds, label, when)
PACKAGE_SLOTS = {
    "3DRB":  ("RB", ("Receiving Back",), 1, False, "Third-Down Back",
              "Takes over at running back on passing downs and in the two-minute drill"),
    "PWRB":  ("RB", ("Power Back",), 1, False, "Power Back",
              "Takes over at running back in short yardage and at the goal line"),
    "SLOT":  ("WR", ("Slot",), 2, True, "Slot Receivers",
              "The inside receivers in three- and four-receiver sets"),
    "JTE":   ("TE", ("Blocking TE",), 1, True, "Jumbo Tight End",
              "The third tight end in 13 personnel and goal-line sets (a lineman can report eligible)"),
    "RE":    ("EDGE", ("Speed Rusher", "Power Rusher", "Complete Edge"), 2, False, "Pass-Rush Ends",
              "The ends on obvious passing downs"),
    "RDT":   ("DT", ("Penetrator", "Interior Rusher"), 2, False, "Pass-Rush Tackles",
              "The tackles on obvious passing downs"),
    "SUBLB": ("LB", ("Coverage LB",), 2, False, "Sub Linebackers",
              "The linebackers who stay on in nickel (two) and dime (one)"),
    "NCB":   ("CB", ("Slot Corner",), 2, True, "Nickel and Dime Backs",
              "The fifth and sixth defensive backs in nickel, dime and quarter"),
    "S3":    ("S", ("Hybrid",), 1, True, "Third Safety",
              "The extra safety in big nickel and quarter"),
}
PACKAGE_ORDER = list(PACKAGE_SLOTS)
# Positions whose players are on a package's list without being added by hand
POOL = {"3DRB": ("RB",), "PWRB": ("RB", "FB"), "SLOT": ("WR",), "JTE": ("TE",),
        "RE": ("EDGE",), "RDT": ("DT",), "SUBLB": ("LB",), "NCB": ("CB",), "S3": ("S",)}
# Base list the starters of an "adds" package come on beside
BASE_STARTERS = {"SLOT": 2, "JTE": 2, "NCB": 2, "S3": 2}


def is_package(slot):
    return slot in PACKAGE_SLOTS


def base_of(slot):
    """The position a slot plays: a package slot's base position, otherwise the slot itself."""
    pk = PACKAGE_SLOTS.get(slot)
    return pk[0] if pk else slot


def starters(slot):
    return PACKAGE_SLOTS[slot][2]


def label(slot):
    return PACKAGE_SLOTS[slot][4]


def in_pool(p, slot):
    return p.position in POOL.get(slot, ())


def package_ca(p, slot):
    """CA as this package's role: the best of its role formulas on his attributes at the base position."""
    import position_fit as fit
    base, roles = PACKAGE_SLOTS[slot][0], PACKAGE_SLOTS[slot][1]

    def calc():
        attrs = fit._adjusted(p, fit.slot_deltas(p, base))
        return max(role_ca(attrs, base, r) for r in roles)
    return fit._cached(p, ("pkg", slot), calc)


def package_ovr(p, slot):
    return ovr_from_ca(package_ca(p, slot), base_of(slot))


def best_role(p, slot):
    """The role formula his package rating comes from (the best of the package's roles for him)."""
    import position_fit as fit
    base, roles = PACKAGE_SLOTS[slot][0], PACKAGE_SLOTS[slot][1]
    if len(roles) == 1:
        return roles[0]
    attrs = fit._adjusted(p, fit.slot_deltas(p, base))
    return max(roles, key=lambda r: role_ca(attrs, base, r))


def when(slot):
    return PACKAGE_SLOTS[slot][5]


# ── Defensive packages ────────────────────────────────────────────────────────
# name: (DT, EDGE, LB, CB, S). Corners and safeties beyond two come from the
# NCB and S3 lists; the linebackers in nickel and dime from SUBLB.
DEF_PACKAGES = {
    "Base":       (2, 2, 3, 2, 2),
    "3-4 Base":   (1, 2, 4, 2, 2),
    "Nickel":     (2, 2, 2, 3, 2),
    "Big Nickel": (2, 2, 2, 2, 3),
    "Dime":       (2, 2, 1, 4, 2),
    "Quarter":    (1, 2, 1, 4, 3),
    "Goal Line":  (3, 2, 3, 2, 1),
}
DEF_PACKAGE_DESC = {
    "Base": "Four linemen, three linebackers, two corners and two safeties, against two-receiver sets.",
    "3-4 Base": "Three linemen (a nose tackle and two ends) and four linebackers.",
    "Nickel": "A fifth defensive back (the nickel corner) replaces a linebacker, against three receivers.",
    "Big Nickel": "A third safety instead of the nickel corner: coverage without losing size against "
                  "tight ends. Two-high coordinators with a good third safety use it most.",
    "Dime": "Six defensive backs and one linebacker, against four or more receivers.",
    "Quarter": "Seven defensive backs for Hail Marys and very long passing downs late.",
    "Goal Line": "Three tackles, two ends, three linebackers: everybody big near the goal line.",
}


def personnel_counts(pers):
    """(backs, tight ends, receivers) for a personnel code like '12' (one back, two tight ends)."""
    rb, te = int(pers[0]), int(pers[1])
    return rb, te, 5 - rb - te


def choose_def_package(pers, front, to_goal, togo, down, late_long, big_nickel_lean, rng):
    """
    The defense's personnel for this snap, matched to the offense's personnel
    (it sees who comes on the field, never the play). big_nickel_lean 0-1 is how
    much this coordinator likes a third safety against tight ends.
    """
    rb, te, wr = personnel_counts(pers)
    if late_long:
        return "Quarter"
    if to_goal <= 2 or (wr <= 1 and togo <= 1):
        return "Goal Line"
    if wr >= 4:
        return "Dime"
    if wr == 3:
        return "Nickel" if rng.random() > 0.04 + 0.16 * big_nickel_lean else "Big Nickel"
    if te >= 2 and rng.random() < big_nickel_lean * (0.55 if te == 2 else 0.35):
        return "Big Nickel"
    if wr == 2 and down >= 3 and togo >= 7 and rng.random() < 0.55:
        return "Nickel"
    return "3-4 Base" if front == "3-4" else "Base"
