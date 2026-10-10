"""
Substitutions: who plays which snaps, and how staffs look after their players.

Every head coach has a substitution identity: a rotation style (how freely each
position group rotates) and how protective he is with banged-up players. The
engine asks this module on every snap (situational rotation, blowouts, players
coming back from a knock); the front office asks it every week (who plays through a
questionable injury). Workload carries over from game to game, so a coach who rides
his starters gets more out of them on Sunday and has more tired legs by December.

The same rules run for the user's club: its head coach decides, unless the user
picks a rotation or an injury policy on the Depth Chart. Plain tables and small
functions, so the port can copy them as they are.
"""


def _clip(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


GROUPS = ("DL", "LB", "DB", "WR", "TE", "RB")

# ── Rotation identity ─────────────────────────────────────────────────────────

# How freely each style rotates a group (multiplies the engine's POS_ROTATION). The
# styles are scaled below so the league as a whole rotates at the realistic baseline.
ROTATION_STYLES = {
    "Rides his starters":      {"DL": 0.60, "LB": 0.60, "DB": 0.60, "WR": 0.62, "TE": 0.70, "RB": 0.75},
    "Balanced":                {"DL": 1.00, "LB": 1.00, "DB": 1.00, "WR": 1.00, "TE": 1.00, "RB": 1.00},
    "Rotates the front":       {"DL": 1.50, "LB": 1.10, "DB": 0.95, "WR": 0.92, "TE": 0.95, "RB": 1.00},
    "Rotates the skill spots": {"DL": 0.95, "LB": 0.95, "DB": 1.00, "WR": 1.45, "TE": 1.25, "RB": 1.30},
    "Fresh legs everywhere":   {"DL": 1.30, "LB": 1.30, "DB": 1.25, "WR": 1.35, "TE": 1.25, "RB": 1.30},
}
STYLE_WEIGHTS = {"Rides his starters": 0.20, "Balanced": 0.36, "Rotates the front": 0.18,
                 "Rotates the skill spots": 0.14, "Fresh legs everywhere": 0.12}
STYLE_NOTES = {
    "Rides his starters": "rides his starters",
    "Balanced": "",
    "Rotates the front": "rotates his defensive line",
    "Rotates the skill spots": "rotates his backs and receivers",
    "Fresh legs everywhere": "rotates heavily",
}
for _g in GROUPS:
    _m = sum(STYLE_WEIGHTS[s] * ROTATION_STYLES[s][_g] for s in ROTATION_STYLES)
    for _s in ROTATION_STYLES:
        ROTATION_STYLES[_s][_g] = round(ROTATION_STYLES[_s][_g] / _m, 3)


def style_weights(off_scheme, front, age):
    """
    The odds of each rotation style for a head coach: attacking 4-3 fronts rotate
    their linemen, spread systems their receivers, older coaches ride their starters.
    """
    w = dict(STYLE_WEIGHTS)
    if front == "4-3":
        w["Rotates the front"] *= 1.35
    if off_scheme in ("Air Raid", "Run and Shoot", "Spread Option", "Wide Zone", "Zone Run"):
        w["Rotates the skill spots"] *= 1.35
    if age >= 58:
        w["Rides his starters"] *= 1.4
    elif age <= 44:
        w["Fresh legs everywhere"] *= 1.3
    return w


def group_rotation(style, group):
    """How freely a coach of this rotation style rotates a group (1.0 = the league norm)."""
    return ROTATION_STYLES.get(style, ROTATION_STYLES["Balanced"]).get(group, 1.0)


def protect_label(protect):
    if protect >= 0.66:
        return "protects banged-up players"
    if protect <= 0.34:
        return "plays through pain"
    return ""


# ── Situational rotation ──────────────────────────────────────────────────────

# Coaches keep their best players on the field when the snap matters and rotate on
# early downs. A coach's game management sets how sharply he does it.
LEVERAGE = {"high": 0.50, "normal": 1.0, "low": 1.30}


def leverage(down, yl, quarter, clock, diff):
    """How much this snap matters: "high" (3rd/4th down, red zone, end of a half, a close 4th quarter)."""
    if quarter >= 5 or down >= 3 or yl >= 80 or (quarter in (2, 4) and clock <= 120) \
            or (quarter == 4 and abs(diff) <= 8):
        return "high"
    if down == 1 and (quarter <= 3 or abs(diff) >= 17):
        return "low"
    return "normal"


def leverage_mult(level, game_management):
    """Multiplier on a group's rotation for this snap: sharper game managers lean harder."""
    aware = 0.3 + 0.6 * _clip(game_management, 1, 20) / 20.0
    return 1.0 + (LEVERAGE[level] - 1.0) * aware


# Development snaps: a staff that wants to play its young players gives a prospect with
# real upside early-down reps behind the starter (value bonus per point of youth credit).
DEV_REPS = 0.006


def dev_rep_bonus(credit, age, gap):
    """Rotation value bonus for a young prospect (age 24 or under, 8+ points below his ceiling)."""
    if credit <= 0 or age > 24 or gap < 8:
        return 0.0
    return DEV_REPS * credit * min(1.5, gap / 15.0)


# ── Blowouts ──────────────────────────────────────────────────────────────────

GARBAGE_CLOCK = 60        # starters stay in until the final minute (owner rule)
GARBAGE_LEAD = 17         # a three-score game with a minute left is over


def garbage_margin(protect, kids, playoff, leading, policy=None):
    """
    The margin at which a staff sends in its backups in the final minute. Protective
    coaches and clubs playing their kids go sooner; a trailing team and playoff teams later.
    """
    m = GARBAGE_LEAD + (0.5 - protect) * 6.0 - min(3.0, kids * 0.5)
    if not leading:
        m += 4.0
    if playoff:
        m += 4.0
    if policy == "ride":
        m += 7.0
    elif policy == "protect":
        m -= 2.0
    return m


# ── Workload (wear that carries over between games) ───────────────────────────

# Fatigue a full-time starter carries out of a normal game (the engine's end-of-game wear).
# Only the part above this builds workload; rest takes it away.
TYPICAL_WEAR = {"QB": 4.7, "RB": 20.5, "FB": 4.0, "WR": 14.3, "TE": 13.9, "OT": 10.2, "IOL": 10.2,
                "DT": 29.0, "EDGE": 27.5, "LB": 16.5, "CB": 12.4, "S": 12.6, "K": 99.0, "P": 99.0}
LOAD_KEEP = 0.65          # share of his workload still in his legs a week later
LOAD_REST = 0.35          # share kept through a week without a game (bye, injury)
LOAD_CARRY = 0.25         # energy missing at kickoff per point of workload
LOAD_MAX = 40.0
WEAR_CAP = 10.0           # at most this much energy missing at kickoff


def update_load(load, game_wear, position):
    """His workload after a game in which he played."""
    excess = game_wear - TYPICAL_WEAR.get(position, 12.0)
    return round(_clip(load * LOAD_KEEP + excess, 0.0, LOAD_MAX), 2)


def rest_load(load):
    """His workload after a week without a game."""
    return round(load * LOAD_REST, 2)


def kickoff_wear(load):
    """Energy he is missing at kickoff (halftime gives some back, like any wear)."""
    return min(WEAR_CAP, load * LOAD_CARRY) if load > 0 else 0.0


def load_label(load):
    if load >= 22:
        return "Worn down"
    if load >= 10:
        return "Heavy workload"
    return ""


# ── Knocks during a game ──────────────────────────────────────────────────────

KNOCK_SNAPS = (6, 18)     # snaps a player misses while the trainers look at a knock


def knock_return_chance(protect, diff, playoff, kids, policy=None):
    """
    The chance a player with a minor knock (no games to miss) goes back in. Close and
    playoff games bring him back; blowouts, lost seasons and protective coaches don't.
    """
    c = 0.55 + (0.5 - protect) * 0.4
    if abs(diff) <= 8:
        c += 0.12
    elif abs(diff) >= 17:
        c -= 0.30
    if playoff:
        c += 0.15
    c -= kids * 0.02
    if policy == "ride":
        c += 0.20
    elif policy == "protect":
        c -= 0.25
    return _clip(c, 0.05, 0.95)


# ── Questionable players (one game left on the injury clock) ─────────────────

HURT_FORM = 3.0           # form a player playing hurt gives up (every attribute)
HURT_EXPOSURE = 1.5       # his injury odds while he plays hurt (he can aggravate it)
NEVER_PLAY_THROUGH = ("Concussion",)                       # protocol: he sits
RISKY = {"Hamstring strain": -0.15, "Groin strain": -0.10, "Calf strain": -0.10,
         "High ankle sprain": -0.10}                        # strains come back worse


def play_hurt_chance(name, gap, protect, stakes, policy=None):
    """
    The chance a staff plays a questionable starter. gap: how much better he is than the
    healthy man behind him (rating at his slot); stakes: -1 (a lost season) to 1 (playoffs).
    """
    if name in NEVER_PLAY_THROUGH or policy == "protect":
        return 0.0
    c = 0.25 + _clip(gap / 40.0, -0.10, 0.35) + stakes * 0.15 + (0.5 - protect) * 0.4 + RISKY.get(name, 0.0)
    if policy == "ride":
        c += 0.25
    return _clip(c, 0.0, 0.9)
