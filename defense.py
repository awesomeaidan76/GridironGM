"""
Defensive call library: fronts, coverages, pressures and stunts.

The ideas come from published coaching material (Seattle-style Cover 3 and
Cover 1 defenses, Tampa 2, quarters/pattern-match teams, fire-zone pressure
packages and the usual line games). They are written here as data the match
engine reads; nothing in this file draws anything or imports UI code.

A call is chosen before every snap from the defensive coordinator's
tendencies (blitz / zone / two-high rates), the situation and the user's
playbook preferences. Each part of the call has small, opposite-signed
effects, so no call is simply "best": a fire zone gets home but leaves hot
throws open, quarters shuts down verticals but softens underneath, a Bear
front clogs the middle but leaves the edges thin.
"""
import random

# ── Coverages ─────────────────────────────────────────────────────────────────
# name: (man?, deep safeties, description)
COVERAGES = {
    "Cover 0": (True, 0, "All-out man with no deep help; comes with a six-man pressure"),
    "Cover 1": (True, 1, "Man coverage with a single deep safety in the middle of the field"),
    "Cover 1 Robber": (True, 1, "Cover 1 with the second safety 'robbing' the intermediate middle"),
    "2-Man": (True, 2, "Trail man coverage underneath with two deep safeties over the top"),
    "Cover 2": (False, 2, "Two deep halves and five underneath zones; corners squat in the flats"),
    "Tampa 2": (False, 2, "Cover 2 with the middle linebacker running the deep middle"),
    "Cover 3": (False, 1, "Three deep thirds and four underneath zones"),
    "Cover 3 Sky": (False, 1, "Cover 3 with the strong safety rolling down to the curl/flat"),
    "Cover 3 Buzz": (False, 1, "Cover 3 with a safety 'buzzing' down to the hook zone"),
    "Cover 3 Match": (False, 1, "Pattern-matching Cover 3: zones that turn into man once routes declare"),
    "Cover 4": (False, 2, "Quarters: four deep defenders who read the inside receivers"),
    "Cover 6": (False, 2, "Quarter-quarter-half: Cover 4 to the strong side, Cover 2 to the weak side"),
    "Fire Zone": (False, 1, "Five-man zone pressure: three deep, three underneath"),
    "Prevent": (False, 2, "Three-man rush and deep zones; gives up the underneath to stop the big play"),
    "Cover 2 Invert": (False, 2, "Shows Cover 2, then the corners bail to the deep halves and the safeties "
                                 "drop into the flats: takes away the smash corner and quick outs"),
    "Palms": (False, 2, "Quarters 2-Read: the corner jumps the flat when the inside receiver breaks out "
                        "and the safety takes the outside man deep"),
    "Cover 7": (True, 2, "Man-match bracket: two defenders squeeze the best receiver, everyone else plays "
                         "man with a safety over the top"),
    "Cover 8": (False, 2, "The mirror of Cover 6: a cloud corner and a half-field safety to the strength, "
                          "quarters to the weak side"),
    "Cover 9": (False, 1, "Shows two deep safeties, then one spins down at the snap into a three-deep zone: "
                          "a disguise for the quarterback who read two-high"),
    "Three-High": (False, 3, "Three safeties deep (big nickel): the deep middle and both halves are capped, "
                             "but the run and the short middle are softer"),
}
# Coverages added by custom playbooks (name -> base selection weight); each joins the
# calls of its family (man or zone, one or two-plus deep safeties)
EXTRA_COVERAGES = {}
# How much a coverage changes after the snap from what it showed before (0-1). Disguise
# muddies the quarterback's pre-snap read and the man/zone "tell" that motion gives him.
DISGUISE = {"Cover 9": 1.0, "Cover 2 Invert": 0.7, "Cover 8": 0.35, "Palms": 0.3, "Three-High": 0.35,
            "Cover 3 Match": 0.25, "Cover 1 Robber": 0.15}

# Openness adjustments (in engine openness points; ~9 = one standard deviation)
# for routes against each coverage. These encode the classic "beaters":
# Smash/corner routes vs Cover 2, seams and flood routes vs Cover 3,
# crossers vs man, hitches and flats vs quarters, hot throws vs pressure.
COV_EDGE = {
    "Cover 0": {"slant": 4, "hitch": 3, "quick out": 3, "go": 3, "fade": 3, "drag": 3, "choice": 3,
                "option": 3, "bubble": 2, "spot": 2, "stick": 2},
    "Cover 1": {"drag": 3, "cross": 3, "slant": 2, "wheel": 3, "choice": 2, "option": 2, "whip": 3,
                "out": 1, "post": -3, "skinny post": -2, "seam": -1, "dig": -1, "curl": -1},
    "Cover 1 Robber": {"dig": -4, "cross": -2, "curl": -2, "drag": 1, "go": 2, "fade": 2,
                       "corner": 2, "wheel": 3, "out": 1, "post": -2},
    "2-Man": {"go": -3, "seam": -3, "post": -3, "slant": -2, "out": -2, "quick out": -1, "drag": 3,
              "checkdown": 3, "flat": 2, "wheel": 2, "angle": 3, "choice": 1},
    "Cover 2": {"corner": 5, "seam": 4, "fade": 2, "post": 3, "dig": 2, "hook": 1, "sluggo": 2,
                "flat": -4, "out": -3, "quick out": -3, "hitch": -1, "bubble": -2, "arrow": -2},
    "Tampa 2": {"corner": 5, "dig": 3, "curl": 1, "post-corner": 3, "seam": -2, "post": -2,
                "flat": -3, "out": -2, "quick out": -2, "drag": -1},
    "Cover 3": {"seam": 4, "flat": 3, "curl": 2, "out": 2, "comeback": 2, "hitch": 1, "spot": 1,
                "go": -3, "post": -2, "fade": -3, "corner": -1, "dig": -1},
    "Cover 3 Sky": {"seam": 3, "curl": 1, "dig": 2, "hook": 2, "flat": -1, "out": 2, "go": -3,
                    "fade": -3, "post": -2},
    "Cover 3 Buzz": {"seam": 2, "flat": 3, "out": 3, "arrow": 2, "dig": -2, "hook": -2, "curl": -1,
                     "go": -3, "post": -2},
    "Cover 3 Match": {"seam": -2, "curl": -1, "flat": 2, "drag": 3, "cross": 2, "whip": 3,
                      "go": -3, "post": -1, "fade": -2},
    "Cover 4": {"go": -5, "post": -3, "seam": -3, "skinny post": -3, "fade": -3, "sluggo": -2,
                "hitch": 3, "flat": 3, "slant": 2, "drag": 3, "out": 2, "curl": 2, "stick": 2,
                "post-corner": 2},
    "Cover 6": {"go": -3, "post": -2, "seam": -1, "hitch": 2, "corner": 2, "flat": 1, "drag": 2,
                "curl": 1},
    "Fire Zone": {"hitch": 3, "slant": 3, "stick": 3, "spot": 2, "flat": 2, "seam": 2, "go": -2,
                  "post": -2, "dig": -1, "corner": -1},
    "Prevent": {"go": -8, "post": -6, "fade": -6, "seam": -5, "corner": -4, "sluggo": -6,
                "post-corner": -5, "out-and-up": -6, "dig": 2, "curl": 4, "hitch": 5, "flat": 5,
                "checkdown": 6, "drag": 5, "out": 3},
    "Cover 2 Invert": {"corner": -1, "sail": -1, "flat": -2, "quick out": -2, "arrow": -2, "bubble": -1,
                       "go": -1, "fade": -1, "seam": 3, "hitch": 2, "curl": 2, "dig": 2, "post": 2},
    "Palms": {"flat": -3, "quick out": -3, "arrow": -2, "out": -2, "bubble": -2, "go": -2, "seam": -2,
              "post": -2, "wheel": 3, "corner": 2, "post-corner": 2, "drag": 2, "dig": 1},
    "Cover 7": {"go": -1, "post": -1, "slant": 1, "drag": 3, "cross": 3, "whip": 2, "wheel": 2, "angle": 2,
                "checkdown": 2},
    "Cover 8": {"go": -3, "post": -2, "seam": -2, "corner": -1, "flat": -1, "hitch": 2, "curl": 2, "dig": 1,
                "drag": 2, "out": 1},
    "Cover 9": {"seam": 3, "flat": 2, "curl": 1, "hook": 1, "go": -2, "post": -2, "fade": -2},
    "Three-High": {"go": -5, "post": -4, "seam": -4, "skinny post": -4, "fade": -3, "corner": -3,
                   "sluggo": -3, "post-corner": -3, "leak": -2, "dig": -1, "hitch": 3, "curl": 3, "drag": 3,
                   "flat": 2, "stick": 2, "spot": 2, "checkdown": 3, "angle": 2, "out": 1},
}
# The newer routes against the classic shells
for _cov, _edges in {
    "Cover 0": {"jailbreak": 2, "pop": 2}, "Cover 1": {"leak": 2, "banana": 1, "pop": 1},
    "Cover 3": {"banana": 2, "leak": 2, "pop": 2}, "Cover 2": {"banana": 2, "leak": 1},
    "Cover 4": {"banana": -1, "leak": -1, "pop": -2}, "Fire Zone": {"jailbreak": 2, "pop": 2},
    "Cover 3 Match": {"leak": -1}, "Palms": {"banana": 2}, "Prevent": {"jailbreak": 3},
}.items():
    COV_EDGE[_cov].update(_edges)

# ── Fronts ────────────────────────────────────────────────────────────────────
# run_in / run_out: change to run defence (engine points) against inside and
# outside runs; rush: change to the pass rush.
FRONTS = {
    "Over":      {"three": False, "run_in": 0.5, "run_out": 0.5, "rush": 0.0,
                  "desc": "4-3 front shaded to the tight end side; balanced"},
    "Under":     {"three": False, "run_in": 1.5, "run_out": -1.0, "rush": 0.5,
                  "desc": "4-3 front shaded away from the tight end; strong against inside runs"},
    "Wide 9":    {"three": False, "run_in": -2.0, "run_out": 1.0, "rush": 2.5,
                  "desc": "Ends aligned far outside the tackles: a speed rush that opens inside lanes"},
    "Bear":      {"three": False, "run_in": 3.5, "run_out": -2.5, "rush": 1.0,
                  "desc": "46-style front covering the center and both guards; clogs the middle"},
    "Odd":       {"three": True, "run_in": 0.0, "run_out": 0.5, "rush": -0.5,
                  "desc": "3-4 front: nose tackle, two ends and two outside linebackers"},
    "Tite":      {"three": True, "run_in": 2.0, "run_out": -1.0, "rush": 0.5,
                  "desc": "Three-man front with the ends inside the tackles (4i-0-4i) to stop zone runs"},
    "Goal Line": {"three": False, "run_in": 4.0, "run_out": -1.0, "rush": 0.5,
                  "desc": "Heavy goal-line front with extra linemen and linebackers"},
    "Penny":     {"three": True, "run_in": 2.5, "run_out": -0.5, "rush": 0.0,
                  "desc": "Five on the line (a nose and two 4i tackles between the edges) and one linebacker: "
                          "how a three-safety defense stops the run"},
}

# ── Pressures and line games ──────────────────────────────────────────────────
PRESSURES = {
    "Fire Zone":        {"rush": 5, "cov": "Fire Zone", "who": ["LB"],
                         "desc": "Linebacker blitz with an end dropping into the flat; zone behind it"},
    "Nickel Fire Zone": {"rush": 5, "cov": "Fire Zone", "who": ["NB"],
                         "desc": "Slot corner blitz off the edge with zone behind it"},
    "Cover 1 Blitz":    {"rush": 5, "cov": "Cover 1", "who": ["LB"],
                         "desc": "Linebacker blitz with man coverage and one deep safety"},
    "Safety Blitz":     {"rush": 5, "cov": "Cover 1", "who": ["S"],
                         "desc": "Strong safety blitz; the free safety plays the deep middle"},
    "Double A-Gap":     {"rush": 6, "cov": "Cover 0", "who": ["LB", "LB"],
                         "desc": "Both linebackers walk up into the A gaps and come; man with no help"},
    "Cover 0 Blitz":    {"rush": 6, "cov": "Cover 0", "who": ["LB", "S"],
                         "desc": "Six-man pressure; everyone else is in man coverage"},
    "Corner Blitz":     {"rush": 5, "cov": "Cover 3", "who": ["CB"],
                         "desc": "A corner blitzes off the edge and a safety rotates over to his receiver; "
                                 "three deep behind it"},
    "Edge Zone Blitz":  {"rush": 5, "cov": "Fire Zone", "who": ["LB"], "edge": True,
                         "desc": "Five-man zone pressure from the wide side: a linebacker comes off the edge "
                                 "and the end drops into the flat"},
}
SIM_PRESSURE = {
    "Creeper": "Four-man pressure from an unexpected spot while a lineman drops into coverage",
    "Amoeba": "Third-down look with nobody in a stance: everyone mills around the line and the protection "
              "has to guess which four come",
    "Double Mug": "Both linebackers walk up into the A gaps, then one or both drop out at the snap; "
                  "the center has to call the protection right",
}
STUNTS = {
    "TEX": "Tackle slants out, end loops inside behind him",
    "ET": "End crashes inside, tackle loops around to the edge",
    "Twist": "Interior tackles exchange gaps",
    "Pirate": "Three-man line all slant the same way with the backer filling behind",
}

ALL_CALLS = (sorted(COVERAGES) + sorted(PRESSURES) + sorted(SIM_PRESSURE)
             + ["Stunt: " + s for s in sorted(STUNTS)] + sorted(FRONTS))


def describe(name):
    if name in PRESSURES:
        return PRESSURES[name]["desc"]
    if name in COVERAGES:
        return COVERAGES[name][2]
    if name in SIM_PRESSURE:
        return SIM_PRESSURE[name]
    if name.startswith("Stunt: "):
        return STUNTS.get(name[7:], "")
    if name in FRONTS:
        return FRONTS[name]["desc"]
    return ""


# What each defensive system likes (multiplies selection weights)
SCHEME_CALLS = {
    "4-3 Over": {"Over": 2.0, "Cover 3": 1.5, "Cover 1": 1.3},
    "3-4 Two Gap": {"Odd": 2.0, "Cover 3 Match": 1.3, "Cover 1": 1.2},
    "Tampa 2": {"Tampa 2": 4.0, "Cover 2": 2.0, "Wide 9": 1.6, "Stunt: TEX": 1.5},
    "46 Blitz": {"Bear": 3.0, "Cover 0 Blitz": 2.0, "Double A-Gap": 2.0, "Cover 1 Blitz": 1.5,
                 "Safety Blitz": 1.5},
    "Cover 3": {"Cover 3 Sky": 2.0, "Cover 3 Buzz": 1.6, "Cover 3": 1.6, "Cover 1": 1.4, "Under": 1.5},
    "Press Man": {"Cover 1": 2.0, "2-Man": 1.8, "Cover 1 Robber": 1.6, "Cover 1 Blitz": 1.4},
    "Two-High Match": {"Cover 4": 2.6, "Cover 6": 2.0, "Tite": 2.2, "Creeper": 1.8},
    "Zone Blitz": {"Fire Zone": 2.5, "Nickel Fire Zone": 2.0, "Creeper": 2.5, "Odd": 1.5},
    "Three-High": {"Three-High": 3.0, "Cover 9": 2.0, "Cover 4": 1.5, "Palms": 1.5, "Penny": 2.5,
                   "Tite": 1.5, "Creeper": 1.6, "Amoeba": 1.4},
}
SCHEME_CALLS["Two-High Match"].update({"Palms": 2.0, "Cover 8": 1.6, "Cover 9": 1.4, "Cover 7": 1.3})
SCHEME_CALLS["Tampa 2"].update({"Cover 2 Invert": 1.6})
SCHEME_CALLS["Cover 3"].update({"Cover 9": 1.3, "Corner Blitz": 1.3})
SCHEME_CALLS["Press Man"].update({"Cover 7": 1.8})
SCHEME_CALLS["Zone Blitz"].update({"Edge Zone Blitz": 2.2, "Corner Blitz": 1.6, "Amoeba": 1.6, "Double Mug": 1.3})
SCHEME_CALLS["46 Blitz"].update({"Double Mug": 1.6, "Corner Blitz": 1.3})
SCHEME_CALLS["3-4 Two Gap"].update({"Edge Zone Blitz": 1.3})
SCHEME_CALLS["4-3 Over"].update({"Cover 9": 1.2})


def _pick(rng, opts, likes, prefs):
    names = list(opts)
    w = [max(0.0, opts[n] * likes.get(n, 1.0) * prefs.get("def:" + n, 1.0)) for n in names]
    if sum(w) <= 0:
        w = [opts[n] for n in names]
    return rng.choices(names, weights=w, k=1)[0]


def choose_call(dplan, sit, scheme=None, prefs=None, rng=random):
    """
    sit: dict with down, togo, to_goal, hurry (offense in two-minute mode),
    lead (defense's lead in points), late (final minutes of a half),
    n_cb / n_s (corners and safeties on the field) - the defence never sees
    the offensive call.
    Returns a dict describing the call.
    """
    prefs = prefs or {}
    likes = SCHEME_CALLS.get(scheme, {})
    down, togo, to_goal = sit["down"], sit["togo"], sit["to_goal"]
    pass_down = (down == 3 and togo >= 6) or (down == 2 and togo >= 10)
    short = togo <= 2 and down >= 3
    goal_line = to_goal <= 3

    # Front
    if goal_line or (short and to_goal <= 10):
        front = "Goal Line" if goal_line else "Bear"
    elif dplan.get("front") == "3-4":
        opts = {"Odd": 3.0, "Tite": 2.0 + (1.5 if sit.get("n_cb", 2) >= 3 else 0.0)}
        if sit.get("n_s", 2) >= 3:
            opts["Penny"] = 1.2
        if short:
            opts["Bear"] = 3.0
        front = _pick(rng, opts, likes, prefs)
    else:
        opts = {"Over": 3.0, "Under": 2.5, "Wide 9": 0.8 + (2.0 if pass_down else 0.0)}
        if short:
            opts["Bear"] = 2.5
        front = _pick(rng, opts, likes, prefs)

    # Prevent at the end of a half when protecting a lead
    if sit.get("hurry") and sit.get("late") and 1 <= sit.get("lead", 0) <= 16 and to_goal >= 30 \
            and rng.random() < 0.35 * prefs.get("def:Prevent", 1.0):
        return {"name": "Prevent", "cov": "Prevent", "man": False, "two_high": True, "rush": 3,
                "blitz": False, "who": [], "sim": False, "stunt": None, "front": front}

    # Pressure?
    mult = 1.0
    if pass_down:
        mult *= 1.35
    elif down == 1:
        mult *= 0.85
    if short:
        mult *= 1.2
    if to_goal <= 10:
        mult *= 1.2
    if sit.get("hurry"):
        mult *= 0.55
    p_press = dplan["blitz"] * 0.55 * mult
    zone = rng.random() < dplan["zone"]
    two_high = rng.random() < dplan["two_high"]
    if rng.random() < p_press:
        nickel = sit.get("n_cb", 2) >= 3
        if zone:
            opts = {"Fire Zone": 3.0, "Nickel Fire Zone": 2.0 if nickel else 0.0, "Edge Zone Blitz": 1.4,
                    "Corner Blitz": 0.8}
        else:
            six = 0.35 + (0.25 if goal_line else 0.0)
            opts = {"Cover 1 Blitz": 3.0 * (1 - six), "Safety Blitz": 1.5 * (1 - six),
                    "Double A-Gap": 1.5 * six * (1.5 if pass_down else 1.0), "Cover 0 Blitz": 2.0 * six}
        name = _pick(rng, opts, likes, prefs)
        pz = PRESSURES[name]
        return {"name": name, "cov": pz["cov"], "man": COVERAGES[pz["cov"]][0], "two_high": False,
                "rush": pz["rush"], "blitz": True, "who": list(pz["who"]), "sim": False,
                "stunt": None, "front": front}

    # Four-man rush: name the coverage
    if zone and two_high:
        opts = {"Cover 2": 3.0, "Cover 4": 4.0, "Cover 6": 2.0, "Tampa 2": 1.5, "Palms": 1.2, "Cover 8": 0.8,
                "Cover 2 Invert": 0.6, "Cover 9": 0.6}
    elif zone:
        opts = {"Cover 3": 2.0, "Cover 3 Sky": 1.5, "Cover 3 Buzz": 1.2, "Cover 3 Match": 1.0}
    elif two_high:
        # most man teams play it with one safety deep; 2-Man is a long-yardage call
        opts = {"2-Man": 1.0 + (1.5 if pass_down else 0.0), "Cover 1": 1.8, "Cover 1 Robber": 0.6,
                "Cover 7": 0.7}
    else:
        opts = {"Cover 1": 3.0, "Cover 1 Robber": 1.3}
    if zone and sit.get("n_s", 2) >= 3:
        opts["Three-High"] = 2.5 if two_high else 1.2       # a third safety on the field caps everything deep
    for name, w in EXTRA_COVERAGES.items():
        man_, deep_ = COVERAGES[name][0], COVERAGES[name][1]
        if man_ != zone and (deep_ >= 2) == two_high:
            opts[name] = w
    cov = _pick(rng, opts, likes, prefs)
    call = {"name": cov, "cov": cov, "man": COVERAGES[cov][0], "two_high": COVERAGES[cov][1] >= 2,
            "rush": 4, "blitz": False, "who": [], "sim": False, "stunt": None, "front": front}
    # Simulated pressure (a creeper, or a third-down look that makes the protection guess) or a line game
    sims = {"Creeper": 1.0, "Amoeba": 0.8 if pass_down and down >= 3 else 0.0,
            "Double Mug": 0.5 if pass_down else 0.15}
    sim_w = sum(v * likes.get(k, 1.0) * prefs.get("def:" + k, 1.0) for k, v in sims.items()) \
        / (1.8 if pass_down else 1.15) * 0.06 * (1.6 if pass_down else 1.0)
    if rng.random() < sim_w:
        call["sim"] = _pick(rng, sims, likes, prefs)
        call["name"] = f"{call['sim']} ({cov})"
        return call
    st_w = 0.16 * (1.5 if pass_down else 1.0)
    if rng.random() < st_w:
        three = FRONTS[front]["three"]
        opts = {"TEX": 2.0, "ET": 1.5, "Twist": 1.5, "Pirate": 2.5 if three else 0.0}
        names = list(opts)
        w = [opts[n] * likes.get("Stunt: " + n, 1.0) * prefs.get("def:Stunt: " + n, 1.0) for n in names]
        if sum(w) > 0:
            call["stunt"] = rng.choices(names, weights=w, k=1)[0]
            call["name"] = f"{cov} · {call['stunt']} stunt"
    return call


def route_edge(cov, route):
    return COV_EDGE.get(cov, {}).get(route, 0.0)


def run_edge(call, inside):
    """Change to run defence from the front and the call."""
    f = FRONTS.get(call["front"], FRONTS["Over"])
    v = f["run_in"] if inside else f["run_out"]
    cov = call["cov"]
    if call["blitz"]:
        v += 1.5                         # an extra man in the box
    elif call["two_high"]:
        # quarters safeties (and a third safety) still fit the run; a Cover 2 invert's safeties set the edge
        v -= 1.5 if cov in ("Cover 4", "Cover 6", "Palms", "Cover 8") else 1.6 if cov == "Three-High" \
            else 1.0 if cov == "Cover 2 Invert" else 3.0
    elif cov in ("Cover 3 Sky", "Cover 3 Buzz", "Cover 1 Robber", "Cover 9"):
        v += 0.6                         # a safety rotated down
    if cov == "Prevent":
        v -= 3.0
    if call.get("sim") == "Amoeba":
        v -= 1.5                         # nobody is in his gap at the snap
    elif call.get("sim") == "Double Mug":
        v += 1.0 if inside else -0.5     # both A gaps are full
    return v


# ── Weekly game plans and in-game adjustments ─────────────────────────────────

GAMEPLAN_OPTIONS = {
    # key: (label, choices) - "auto" lets the defensive coordinator decide
    "shadow": ("Shadow their No. 1 receiver with your best corner", ["auto", "yes", "no"]),
    "bracket": ("Double-team (bracket) their top target", ["auto", "never", "sometimes", "often"]),
    "spy": ("Spy the quarterback with a linebacker", ["auto", "yes", "no"]),
    "box": ("Run defence", ["auto", "light box", "normal", "stack the box"]),
    "pressure": ("Pressure", ["auto", "conservative", "normal", "aggressive"]),
    "shell": ("Coverage shell", ["auto", "single-high", "balanced", "two-high"]),
}
BRACKET_FREQ = {"never": 0.0, "sometimes": 0.45, "often": 0.85}
BOX_VAL = {"light box": -0.6, "normal": 0.0, "stack the box": 0.8}
PRESSURE_VAL = {"conservative": -0.12, "normal": 0.0, "aggressive": 0.14}
SHELL_VAL = {"single-high": -0.2, "balanced": 0.0, "two-high": 0.2}


def _z(v, mu, sd):
    return (v - mu) / sd


def scout(def_team, off_team, off_plan, calling=10.0, rng=random):
    """
    The defensive coordinator's plan for this opponent. Better coordinators
    read the opponent more accurately; poor ones sometimes over- or under-react.
    Returns adjustments plus plain-English notes for the scouting report.
    """
    err = max(0.0, (20.0 - calling) / 20.0) * 0.6          # 0 (perfect read) .. 0.57
    noise = lambda: rng.gauss(0, err * 0.12)                # noqa: E731
    qbs = off_team.lineup("QB", 1)
    qb = qbs[0] if qbs else None
    wrs = off_team.lineup("WR", 3)
    tes = off_team.lineup("TE", 1)
    rbs = off_team.lineup("RB", 1)
    cbs = def_team.lineup("CB", 3)
    notes = []
    plan = {"blitz": 0.0, "zone": 0.0, "two_high": 0.0, "box": 0.0, "spy": False,
            "bracket": 0.5, "bracket_pid": None, "shadow": True}
    pass_lean = off_plan.get("pass_rate", 0.55) - 0.56
    deep = off_plan.get("deep", 0.0)
    # Receivers: who is the threat?
    targets = [(p, p.rating_at("WR")) for p in wrs] + [(p, p.rating_at("TE") * 0.95) for p in tes]
    if targets:
        star, sr = max(targets, key=lambda t: t[1])
        z = _z(sr, 140, 14)
        if z > 0.6:
            plan["bracket"] = min(0.8, 0.5 + 0.2 * z)
            plan["bracket_pid"] = star.id
            notes.append(f"Roll coverage toward {star.name}, their top target")
        fast = max(p.a("speed") for p, _ in targets)
        deep += max(0.0, fast - 90) / 20.0
    # QB
    if qb is not None:
        mob = qb.a("speed")
        if mob >= 84 and off_plan.get("qb_run", 0) >= 0.35:
            plan["spy"] = True
            plan["blitz"] -= 0.06               # rushers lose contain against runners
            notes.append(f"Spy {qb.name} — he hurts you with his legs")
        arm = _z(qb.rating_at("QB"), 146, 16)
        if arm < -0.6:
            plan["blitz"] += 0.10
            plan["zone"] -= 0.08
            notes.append(f"Pressure {qb.name} and play tight man: he struggles to beat it")
        elif arm > 1.0:
            plan["zone"] += 0.08
            plan["blitz"] -= 0.05
            notes.append(f"Mix coverages — {qb.name} carves up the blitz")
    # Run game
    rb_z = _z(rbs[0].rating_at("RB"), 128, 16) if rbs else 0.0
    box = -pass_lean * 2.2 + rb_z * 0.25
    plan["box"] = max(-1.0, min(1.0, box))
    if plan["box"] > 0.35:
        notes.append("Load the box: they want to run" + (f" behind {rbs[0].name}" if rbs else ""))
    elif plan["box"] < -0.35:
        notes.append("Play light boxes and defend the pass")
    # Shell
    plan["two_high"] += 0.10 * deep + 0.10 * max(0.0, pass_lean) * 3
    if deep > 0.4:
        notes.append("Keep two safeties deep: they take shots")
    # Shadow corner: only worth it if your No. 1 corner is clearly your best
    if len(cbs) >= 2:
        plan["shadow"] = cbs[0].rating_at("CB") - cbs[1].rating_at("CB") >= 6
    for k in ("blitz", "zone", "two_high"):
        plan[k] += noise()
    plan["box"] = max(-1.0, min(1.0, plan["box"] + noise() * 3))
    plan["notes"] = notes
    # The user's own choices override the coordinator
    mine = getattr(def_team, "def_gameplan", None) or {}
    if mine.get("shadow", "auto") != "auto":
        plan["shadow"] = mine["shadow"] == "yes"
    if mine.get("spy", "auto") != "auto":
        plan["spy"] = mine["spy"] == "yes"
    if mine.get("bracket", "auto") != "auto":
        plan["bracket"] = BRACKET_FREQ[mine["bracket"]]
        if plan["bracket_pid"] is None and targets:
            plan["bracket_pid"] = max(targets, key=lambda t: t[1])[0].id
    if mine.get("box", "auto") != "auto":
        plan["box"] = BOX_VAL[mine["box"]]
    if mine.get("pressure", "auto") != "auto":
        plan["blitz"] = PRESSURE_VAL[mine["pressure"]]
    if mine.get("shell", "auto") != "auto":
        plan["two_high"] = SHELL_VAL[mine["shell"]]
    return plan


def adjust(own, opp_off, calling, adaptability):
    """
    In-game adjustment at a quarter break. own: this defence's current in-game
    adjustments; opp_off: what the opposing offence has done so far
    ({run_n, run_epa, pass_n, pass_epa, deep_n, deep_epa, sacks, dropbacks}).
    Returns (new adjustments, note or None).
    """
    q = (calling / 20.0) * (0.5 + adaptability / 40.0)       # how sharp the coordinator is
    adj = dict(own)
    note = None
    rn, pn = opp_off.get("run_n", 0), opp_off.get("pass_n", 0)
    r_epa = opp_off.get("run_epa", 0.0) / rn if rn >= 6 else 0.0
    p_epa = opp_off.get("pass_epa", 0.0) / pn if pn >= 8 else 0.0
    d_epa = opp_off.get("deep_epa", 0.0) / max(1, opp_off.get("deep_n", 0)) if opp_off.get("deep_n", 0) >= 3 else 0.0
    if r_epa > 0.10 and r_epa > p_epa:
        adj["box"] = min(1.0, adj.get("box", 0.0) + 0.45 * q)
        adj["two_high"] = adj.get("two_high", 0.0) - 0.08 * q
        note = "loads the box to slow the run"
    elif p_epa > 0.15 and p_epa > r_epa:
        adj["box"] = max(-1.0, adj.get("box", 0.0) - 0.35 * q)
        if d_epa > 0.4:
            adj["two_high"] = adj.get("two_high", 0.0) + 0.15 * q
            note = "rolls a second safety deep to take away the big play"
        else:
            adj["zone"] = adj.get("zone", 0.0) - 0.10 * q
            adj["blitz"] = adj.get("blitz", 0.0) + 0.08 * q
            note = "gets tighter in coverage and sends more pressure"
    elif rn + pn >= 16 and r_epa < -0.1 and p_epa < -0.1:
        note = None                                  # it's working: no change
    for k in ("blitz", "zone", "two_high"):
        adj[k] = max(-0.3, min(0.3, adj.get(k, 0.0)))
    return adj, note
