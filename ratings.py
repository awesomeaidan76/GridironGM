"""
ratings.py — the rating system for Gridiron GM.

Every player has the SAME full set of attributes (FM style). Each position
weights those attributes differently, and Current Ability (CA, 1-200) is
derived from the position-weighted attributes. That means:

  * CA is never stored separately from attributes — it is always computed,
    so development and decline happen to real attributes and CA follows.
  * A player can be rated at any position (useful for depth charts).

Attribute scale (1-100)
    90-99  World class — among the very best in the league at this skill
    75-89  Quality     — clearly above an average NFL starter
    60-74  Solid       — average NFL starter
    45-59  Backup      — fringe roster / rotational
     1-44  Poor        — developmental or out of position

Current Ability scale (1-200, FM style)
    180-200 World Class
    140-179 Quality
    100-139 Solid
      1-99  Poor
"""
import math


# ── Positions ─────────────────────────────────────────────────────────────────

POSITIONS = ["QB", "RB", "FB", "WR", "TE", "OT", "IOL",
             "DT", "EDGE", "LB", "CB", "S", "K", "P"]

POSITION_NAMES = {
    "QB": "Quarterback", "RB": "Running Back", "FB": "Fullback",
    "WR": "Wide Receiver", "TE": "Tight End", "OT": "Offensive Tackle",
    "IOL": "Interior Lineman", "DT": "Defensive Tackle",
    "EDGE": "Edge Rusher", "LB": "Linebacker", "CB": "Cornerback",
    "S": "Safety", "K": "Kicker", "P": "Punter",
}

OFFENSE_POSITIONS = {"QB", "RB", "FB", "WR", "TE", "OT", "IOL"}
DEFENSE_POSITIONS = {"DT", "EDGE", "LB", "CB", "S"}
SPECIAL_POSITIONS = {"K", "P"}

# Standard 53-man roster
ROSTER_TEMPLATE = {
    "QB": 3, "RB": 4, "FB": 1, "WR": 6, "TE": 3, "OT": 4, "IOL": 5,
    "DT": 5, "EDGE": 5, "LB": 5, "CB": 6, "S": 4, "K": 1, "P": 1,
}

# Minimum we try to keep at each position (AI roster building)
ROSTER_MINIMUM = {
    "QB": 2, "RB": 3, "FB": 0, "WR": 5, "TE": 2, "OT": 3, "IOL": 4,
    "DT": 4, "EDGE": 4, "LB": 4, "CB": 5, "S": 3, "K": 1, "P": 1,
}

# Relative importance of each position to winning (used by AI + awards)
POSITION_VALUE = {
    "QB": 1.00, "EDGE": 0.62, "OT": 0.58, "WR": 0.56, "CB": 0.55,
    "DT": 0.52, "IOL": 0.45, "S": 0.44, "LB": 0.42, "TE": 0.42,
    "RB": 0.36, "FB": 0.12, "K": 0.15, "P": 0.10,
}

# ── Attributes ────────────────────────────────────────────────────────────────
# key: (display name, abbreviation, group)

ATTRIBUTES = {
    # Physical
    "speed":                ("Speed",                 "SPD", "Physical"),
    "acceleration":         ("Acceleration",          "ACC", "Physical"),
    "agility":              ("Agility",               "AGI", "Physical"),
    "strength":             ("Strength",              "STR", "Physical"),
    "jumping":              ("Jumping",               "JMP", "Physical"),
    "stamina":              ("Stamina",               "STA", "Physical"),
    "injury_resistance":    ("Injury Resistance",     "INJ", "Physical"),
    # Passing
    "throw_power":          ("Throw Power",           "THP", "Passing"),
    "short_accuracy":       ("Short Accuracy",        "SAC", "Passing"),
    "medium_accuracy":      ("Medium Accuracy",       "MAC", "Passing"),
    "deep_accuracy":        ("Deep Accuracy",         "DAC", "Passing"),
    "throw_under_pressure": ("Throw Under Pressure",  "TUP", "Passing"),
    "touch":                ("Touch",                 "TCH", "Passing"),
    "play_action":          ("Play Action",           "PAC", "Passing"),
    "screen_accuracy":      ("Screen Accuracy",       "SCR", "Passing"),
    # Ball carrying
    "vision":               ("Vision",                "VIS", "Ball Carrying"),
    "break_tackle":         ("Break Tackle",          "BTK", "Ball Carrying"),
    "contact_balance":      ("Contact Balance",       "CTB", "Ball Carrying"),
    "juke_spin":            ("Juke / Spin",           "JKM", "Ball Carrying"),
    "stiff_arm":            ("Stiff Arm",             "SFA", "Ball Carrying"),
    "ball_security":        ("Ball Security",         "BSC", "Ball Carrying"),
    # Receiving
    "catching":             ("Catching",              "CTH", "Receiving"),
    "catch_in_traffic":     ("Catch in Traffic",      "CIT", "Receiving"),
    "spectacular_catch":    ("Spectacular Catch",     "SPC", "Receiving"),
    "short_route_running":  ("Short Routes",          "SRR", "Receiving"),
    "medium_route_running": ("Medium Routes",         "MRR", "Receiving"),
    "deep_route_running":   ("Deep Routes",           "DRR", "Receiving"),
    "release":              ("Release",               "REL", "Receiving"),
    "separation":           ("Separation",            "SEP", "Receiving"),
    # Blocking
    "pass_block":           ("Pass Block",            "PBK", "Blocking"),
    "run_block":            ("Run Block",             "RBK", "Blocking"),
    "impact_block":         ("Impact Block",          "IBK", "Blocking"),
    "pulling":              ("Pulling",               "PUL", "Blocking"),
    "footwork":             ("Footwork",              "FTW", "Blocking"),
    # Pass rush
    "power_move":           ("Power Moves",           "PMV", "Pass Rush"),
    "finesse_move":         ("Finesse Moves",         "FMV", "Pass Rush"),
    "pass_rush_iq":         ("Pass Rush IQ",          "PRQ", "Pass Rush"),
    # Run defense / tackling
    "block_shedding":       ("Block Shedding",        "BSH", "Run Defense"),
    "run_stop":             ("Run Stopping",          "RST", "Run Defense"),
    "tackling":             ("Tackling",              "TAK", "Run Defense"),
    "hit_power":            ("Hit Power",             "POW", "Run Defense"),
    "pursuit":              ("Pursuit",               "PUR", "Run Defense"),
    # Coverage
    "man_coverage":         ("Man Coverage",          "MCV", "Coverage"),
    "zone_coverage":        ("Zone Coverage",         "ZCV", "Coverage"),
    "press_technique":      ("Press",                 "PRS", "Coverage"),
    "interception":         ("Ball Skills",           "BSK", "Coverage"),
    "pass_breakup":         ("Pass Breakup",          "PBU", "Coverage"),
    # Kicking
    "kick_power":           ("Kick Power",            "KPW", "Kicking"),
    "kick_accuracy":        ("Kick Accuracy",         "KAC", "Kicking"),
    "punt_power":           ("Punt Power",            "PPW", "Kicking"),
    "punt_accuracy":        ("Punt Accuracy",         "PAC", "Kicking"),
    # Mental
    "awareness":            ("Awareness",             "AWR", "Mental"),
    "decision_making":      ("Decision Making",       "DEC", "Mental"),
    "progression_reads":    ("Progression Reads",     "PRG", "Mental"),
    "pocket_presence":      ("Pocket Presence",       "PKT", "Mental"),
    "composure":            ("Composure",             "CMP", "Mental"),
    "leadership":           ("Leadership",            "LDR", "Mental"),
    "play_recognition":     ("Play Recognition",      "PRC", "Mental"),
    "anticipation":         ("Anticipation",          "ANT", "Mental"),
    "gap_awareness":        ("Gap Awareness",         "GAP", "Mental"),
}

ATTRIBUTE_GROUPS = ["Physical", "Passing", "Ball Carrying", "Receiving",
                    "Blocking", "Pass Rush", "Run Defense", "Coverage",
                    "Kicking", "Mental"]

PHYSICAL_ATTRS = [a for a, v in ATTRIBUTES.items() if v[2] == "Physical"]
MENTAL_ATTRS = [a for a, v in ATTRIBUTES.items() if v[2] == "Mental"]
# Physical attributes that fade with age (strength & stamina fade slower)
ATHLETIC_ATTRS = ["speed", "acceleration", "agility", "jumping"]

# Hidden personality traits (1-100). Morale and reputation are dynamic
# state on the player, not traits.
HIDDEN_TRAITS = {
    "consistency":  "How reliably he performs to his ability each game",
    "work_rate":    "Effort in training — drives development and slows decline",
    "temperament":  "Discipline and composure — affects penalties and morale swings",
    "adaptability": "How quickly he learns a new scheme or team",
    "ambition":     "Drive to improve and win — affects development and contract demands",
    "big_game":     "Raises or lowers his level in playoff and prime-time games",
}

# Which attribute groups to show on a profile for each position
POSITION_DISPLAY_GROUPS = {
    "QB":   ["Passing", "Mental", "Physical", "Ball Carrying"],
    "RB":   ["Ball Carrying", "Receiving", "Physical", "Blocking", "Mental"],
    "FB":   ["Blocking", "Ball Carrying", "Receiving", "Physical", "Mental"],
    "WR":   ["Receiving", "Physical", "Ball Carrying", "Mental"],
    "TE":   ["Receiving", "Blocking", "Physical", "Ball Carrying", "Mental"],
    "OT":   ["Blocking", "Physical", "Mental"],
    "IOL":  ["Blocking", "Physical", "Mental"],
    "DT":   ["Run Defense", "Pass Rush", "Physical", "Mental"],
    "EDGE": ["Pass Rush", "Run Defense", "Physical", "Mental"],
    "LB":   ["Run Defense", "Coverage", "Pass Rush", "Physical", "Mental"],
    "CB":   ["Coverage", "Physical", "Run Defense", "Mental"],
    "S":    ["Coverage", "Run Defense", "Physical", "Mental"],
    "K":    ["Kicking", "Physical", "Mental"],
    "P":    ["Kicking", "Physical", "Mental"],
}

# ── Position weights ──────────────────────────────────────────────────────────
# How much each attribute contributes to CA at each position.

POSITION_WEIGHTS = {
    "QB": {
        "short_accuracy": 9, "medium_accuracy": 9, "deep_accuracy": 6,
        "throw_power": 6, "throw_under_pressure": 6, "touch": 4,
        "play_action": 2, "screen_accuracy": 1, "decision_making": 9,
        "progression_reads": 7, "pocket_presence": 6, "awareness": 5,
        "composure": 4, "leadership": 2, "speed": 2, "agility": 2,
        "acceleration": 1.5, "strength": 1, "ball_security": 2,
    },
    "RB": {
        "vision": 8, "break_tackle": 6, "contact_balance": 6,
        "juke_spin": 5, "stiff_arm": 2, "ball_security": 4, "speed": 8,
        "acceleration": 8, "agility": 7, "strength": 3, "catching": 4,
        "short_route_running": 2, "pass_block": 2, "stamina": 2,
        "awareness": 2,
    },
    "FB": {
        "run_block": 9, "impact_block": 5, "pass_block": 4, "strength": 7,
        "catching": 3, "break_tackle": 3, "contact_balance": 2,
        "ball_security": 2, "awareness": 3, "acceleration": 2, "speed": 1,
        "vision": 1, "stamina": 1,
    },
    "WR": {
        "catching": 8, "short_route_running": 6, "medium_route_running": 7,
        "deep_route_running": 6, "release": 6, "separation": 6,
        "catch_in_traffic": 5, "spectacular_catch": 3, "speed": 8,
        "acceleration": 7, "agility": 5, "jumping": 3, "ball_security": 2,
        "awareness": 3, "break_tackle": 1, "strength": 1,
    },
    "TE": {
        "catching": 7, "catch_in_traffic": 5, "short_route_running": 4,
        "medium_route_running": 5, "deep_route_running": 2, "release": 3,
        "separation": 3, "spectacular_catch": 2, "run_block": 6,
        "pass_block": 4, "impact_block": 2, "strength": 4, "speed": 4,
        "acceleration": 3, "agility": 2, "jumping": 2, "awareness": 2,
        "ball_security": 1,
    },
    "OT": {
        "pass_block": 10, "run_block": 6, "footwork": 8, "impact_block": 3,
        "pulling": 1, "strength": 7, "agility": 4, "acceleration": 2,
        "awareness": 5, "stamina": 1,
    },
    "IOL": {
        "run_block": 9, "pass_block": 8, "impact_block": 5, "pulling": 3,
        "footwork": 5, "strength": 8, "agility": 2, "acceleration": 1,
        "awareness": 6, "stamina": 1,
    },
    "DT": {
        "block_shedding": 8, "run_stop": 8, "power_move": 7,
        "finesse_move": 4, "pass_rush_iq": 4, "gap_awareness": 6,
        "tackling": 5, "strength": 9, "acceleration": 4, "agility": 2,
        "speed": 1, "play_recognition": 2, "stamina": 1,
    },
    "EDGE": {
        "power_move": 7, "finesse_move": 7, "pass_rush_iq": 6,
        "block_shedding": 6, "run_stop": 5, "tackling": 5,
        "gap_awareness": 3, "acceleration": 8, "speed": 6, "agility": 5,
        "strength": 6, "pursuit": 3, "play_recognition": 2,
    },
    "LB": {
        "tackling": 8, "play_recognition": 7, "pursuit": 6,
        "block_shedding": 5, "run_stop": 4, "zone_coverage": 6,
        "man_coverage": 3, "hit_power": 3, "pass_rush_iq": 2,
        "power_move": 1, "awareness": 5, "speed": 6, "acceleration": 5,
        "agility": 3, "strength": 4,
    },
    "CB": {
        "man_coverage": 9, "zone_coverage": 8, "press_technique": 5,
        "anticipation": 6, "pass_breakup": 5, "interception": 4,
        "tackling": 3, "speed": 9, "acceleration": 8, "agility": 7,
        "jumping": 3, "awareness": 3, "play_recognition": 2,
    },
    "S": {
        "zone_coverage": 8, "man_coverage": 5, "anticipation": 6,
        "play_recognition": 5, "interception": 4, "pass_breakup": 4,
        "tackling": 7, "hit_power": 4, "pursuit": 5, "speed": 7,
        "acceleration": 6, "agility": 4, "jumping": 2, "awareness": 4,
        "strength": 2,
    },
    "K": {"kick_power": 10, "kick_accuracy": 12, "composure": 4},
    "P": {"punt_power": 10, "punt_accuracy": 9, "composure": 3},
}

# Pre-normalised weights for speed
_NORM_WEIGHTS = {}
for _pos, _w in POSITION_WEIGHTS.items():
    _tot = float(sum(_w.values()))
    _NORM_WEIGHTS[_pos] = [(a, v / _tot) for a, v in _w.items()]


def weighted_average(attrs, position):
    """Position-weighted average of a player's attributes (1-100 scale)."""
    return sum(attrs.get(a, 30) * w for a, w in _NORM_WEIGHTS[position])


def ca_from_average(wavg):
    """Map a weighted attribute average (1-100) to Current Ability (1-200)."""
    return max(1, min(200, int(round((wavg - 20.0) * 2.6))))


def average_for_ca(ca):
    """Inverse of ca_from_average."""
    return ca / 2.6 + 20.0


def compute_ca(attrs, position):
    return ca_from_average(weighted_average(attrs, position))


# ── Labels & tiers ────────────────────────────────────────────────────────────

CA_TIERS = [
    (180, "World Class"),
    (140, "Quality"),
    (100, "Solid"),
    (0,   "Poor"),
]

ATTR_TIERS = [
    (90, "World Class"),
    (75, "Quality"),
    (60, "Solid"),
    (45, "Backup"),
    (0,  "Poor"),
]


def ca_tier(ca):
    for floor, name in CA_TIERS:
        if ca >= floor:
            return name
    return "Poor"


def attr_tier(value):
    for floor, name in ATTR_TIERS:
        if value >= floor:
            return name
    return "Poor"


def stars_for(ca):
    """CA (1-200) to a 0.5-10 star rating in half-star steps."""
    return max(0.5, min(10.0, round(ca / 10.0) / 2.0))


def stars_text(stars):
    full = int(stars)
    half = stars - full >= 0.5
    return "★" * full + ("½" if half else "") + "☆" * (10 - full - (1 if half else 0))


def attr_label(key):
    return ATTRIBUTES[key][0]


def attr_abbr(key):
    return ATTRIBUTES[key][1]


def key_attributes(position, n=4):
    """The n most heavily weighted attributes for a position."""
    w = POSITION_WEIGHTS[position]
    return [a for a, _ in sorted(w.items(), key=lambda kv: -kv[1])[:n]]


# ── Display ratings: OVR / POT (1-99), position-relative ─────────────────────
# Internally every player has Current Ability (1-200). What the manager sees is
# a 1-99 rating where the same number means the same standing at every
# position: 75 is a league-average starter, 85 a Pro Bowl level player, 90+
# elite. Each position is anchored to the distribution of starters there
# (mean CA, spread), measured from freshly generated leagues. Anchors are fixed,
# so when an era produces a deep or thin crop at a position the ratings show it.

OVR_ANCHORS = {
    "QB": (146.1, 16.1), "RB": (128.5, 15.1), "FB": (101.5, 17.2), "WR": (130.2, 16.5),
    "TE": (128.5, 14.7), "OT": (136.4, 15.6), "IOL": (127.9, 14.7), "DT": (130.2, 15.3),
    "EDGE": (136.5, 16.3), "LB": (128.8, 14.7), "CB": (128.3, 16.1), "S": (125.1, 14.8),
    "K": (126.2, 16.4), "P": (122.7, 17.5),
}
UNIT_ANCHORS = {
    "QB": (146.1, 16.1), "RB": (128.5, 15.1), "WR": (130.2, 8.7), "TE": (128.5, 14.7),
    "OL": (131.3, 9.0), "DL": (133.6, 8.6), "LB": (121.0, 8.9), "DB": (127.0, 8.1),
    "ST": (124.5, 13.2), "OFF": (135.7, 8.6), "DEF": (128.2, 7.0), "OVR": (131.7, 7.0),
}

OVR_TIERS = [
    (90, "Elite"),
    (82, "Pro Bowl"),
    (72, "Starter"),
    (64, "Rotation"),
    (55, "Backup"),
    (0,  "Fringe"),
]


def _soft_top(x):
    if x > 86.0:
        x = 86.0 + 13.0 * (1.0 - math.exp(-(x - 86.0) / 13.0))
    elif x < SOFT_FLOOR:
        # Below backup level the scale is compressed: fringe players read in the 40s,
        # not the 20s, while their order (and their real ability) is unchanged
        x = SOFT_FLOOR - (SOFT_FLOOR - x) * FLOOR_SQUEEZE
    return x


SOFT_FLOOR = 62.0
FLOOR_SQUEEZE = 0.62


OVR_MID = 74.0      # rating of a league-average starter
OVR_SPREAD = 8.7    # rating points per standard deviation among starters


def ovr_from_ca(ca, position):
    """Current Ability (1-200) to the 1-99 position-relative rating."""
    mu, sd = OVR_ANCHORS.get(position, (130.0, 16.0))
    x = OVR_MID + OVR_SPREAD * (ca - mu) / sd
    return int(round(max(1.0, min(99.0, _soft_top(x)))))


def ca_from_ovr(ovr, position):
    """Inverse of ovr_from_ca (ignoring the soft top)."""
    mu, sd = OVR_ANCHORS.get(position, (130.0, 16.0))
    if ovr < SOFT_FLOOR:
        ovr = SOFT_FLOOR - (SOFT_FLOOR - ovr) / FLOOR_SQUEEZE
    return mu + (ovr - OVR_MID) * sd / OVR_SPREAD


def unit_ovr(value, unit):
    """Team unit strength (CA scale) to a 1-99 team rating (75 = league average)."""
    mu, sd = UNIT_ANCHORS.get(unit, (130.0, 9.0))
    x = OVR_MID + 6.5 * (value - mu) / sd
    return int(round(max(1.0, min(99.0, _soft_top(x)))))


def ovr_tier(ovr):
    for floor, name in OVR_TIERS:
        if ovr >= floor:
            return name
    return "Fringe"


def stars_for_ovr(ovr):
    """1-99 rating to a 0.5-10 star rating in half-star steps."""
    return max(0.5, min(10.0, round(ovr / 5.0) / 2.0))


# ── Role ratings ──────────────────────────────────────────────────────────────
# Every archetype is also a role. A role re-weights the position's attributes
# toward what that job needs (a Power Back is judged more on strength and
# breaking tackles, a Receiving Back on hands and routes), so one player can
# rate 81 as a Receiving Back and 66 as a Power Back.

_ROLE_WEIGHTS = {}


def _role_weights(position, role):
    key = (position, role)
    if key not in _ROLE_WEIGHTS:
        from player import ARCHETYPES
        base = dict(POSITION_WEIGHTS[position])
        mods = ARCHETYPES.get(position, {}).get(role, (0, {}, ""))[1]
        for a, m in mods.items():
            if m > 0:
                base[a] = base.get(a, 0.0) + m * 0.55
            elif a in base:
                base[a] = base[a] * max(0.3, 1.0 + m / 16.0)
        tot = float(sum(base.values()))
        _ROLE_WEIGHTS[key] = [(a, v / tot) for a, v in base.items()]
    return _ROLE_WEIGHTS[key]


def role_ca(attrs, position, role):
    wavg = sum(attrs.get(a, 30) * w for a, w in _role_weights(position, role))
    return ca_from_average(wavg)


def role_ratings(attrs, position):
    """[(role, rating 1-99)] for every role at this position, best first."""
    from player import ARCHETYPES
    out = [(r, ovr_from_ca(role_ca(attrs, position, r), position))
           for r in ARCHETYPES.get(position, {})]
    out.sort(key=lambda x: -x[1])
    return out


# ── Age curves ────────────────────────────────────────────────────────────────
# (growth ends / prime starts, prime ends / decline starts, decline severity)
# Severity is the approximate CA lost in the first decline year; it grows
# each year after.

AGE_CURVES = {
    # (growth usually ends, decline usually starts after, first-year decline)
    # These are league averages: every player gets his own shift (see Player.curve).
    "QB":   (29, 34, 4.0),
    "RB":   (25, 27, 9.0),
    "FB":   (26, 29, 6.0),
    "WR":   (27, 29, 6.0),
    "TE":   (27, 30, 6.0),
    "OT":   (28, 31, 5.0),
    "IOL":  (28, 31, 5.0),
    "DT":   (27, 29, 6.0),
    "EDGE": (27, 29, 6.5),
    "LB":   (26, 29, 6.5),
    "CB":   (26, 29, 7.5),
    "S":    (27, 29, 6.5),
    "K":    (29, 36, 3.0),
    "P":    (29, 36, 3.0),
}
