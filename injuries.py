"""
injuries.py — injury types, durations and lasting effects.
"""
import random

from settings import settings

# name: (frequency, min weeks, max weeks, lasting damage level 0-3)
INJURY_TYPES = {
    "Bruised ribs":        (10, 0, 1, 0),
    "Quad contusion":      (8, 0, 1, 0),
    "Back spasms":         (5, 0, 2, 0),
    "Ankle sprain":        (14, 1, 3, 0),
    "Hamstring strain":    (12, 1, 4, 0),
    "Concussion":          (8, 1, 3, 0),
    "Shoulder sprain":     (7, 1, 4, 0),
    "Groin strain":        (6, 1, 3, 0),
    "Calf strain":         (5, 1, 3, 0),
    "High ankle sprain":   (6, 3, 7, 1),
    "Knee sprain (MCL)":   (6, 2, 6, 1),
    "Turf toe":            (3, 2, 7, 1),
    "Broken hand":         (3, 2, 5, 0),
    "Dislocated elbow":    (1, 3, 7, 1),
    "Torn meniscus":       (1.5, 4, 9, 1),
    "Broken collarbone":   (1.5, 6, 10, 1),
    "Broken leg":          (0.8, 10, 22, 2),
    "Torn pectoral":       (0.8, 12, 24, 1),
    "Torn ACL":            (1.4, 36, 48, 3),
    "Torn Achilles":       (0.8, 38, 52, 3),
}

# How much contact each role takes on one play, as a multiple of the base injury chance (the engine's
# _injury_check). A ball carrier is hit on every touch, but so is a lineman on every snap: in the NFL
# running backs are about a tenth of all injuries, the trenches about a third.
EXPOSURE = {
    "carrier": 0.28,      # whoever has the ball (runs, receptions, returns)
    "tackler": 0.46,      # the man who makes the tackle
    "target": 0.47,       # a contested incompletion: the receiver and his defender
    "route": 0.095,       # one receiver running his route on a pass play (pulled muscles)
    "cover": 0.11,        # one defensive back in coverage on a pass play (breaks, collisions)
    "blocker": 0.22,      # one blocker (a lineman, or a tight end on runs), every run, pass or sack
    "rusher": 0.155,      # one defensive lineman on the field, every run, pass or sack
    "sack": 0.80,         # the quarterback on a sack (times the rules' QB protection)
    "qb_hit": 0.30,       # the quarterback hit as he throws
}

_NAMES = list(INJURY_TYPES)
_WEIGHTS = [INJURY_TYPES[n][0] for n in _NAMES]


def roll_injury(player, weeks_left_in_season=17):
    """Create an injury dict for `player`."""
    name = random.choices(_NAMES, weights=_WEIGHTS, k=1)[0]
    _, lo, hi, damage = INJURY_TYPES[name]
    # Fragile players get hurt worse
    fragility = 1.0 + (60 - player.a("injury_resistance")) / 120.0
    weeks = random.uniform(lo, hi) * fragility * settings["injury_severity"]
    weeks = max(0, int(round(weeks)))
    return {
        "name": name,
        "weeks": weeks,
        "season_ending": weeks > weeks_left_in_season,
        "damage": damage,
    }


def apply_lasting_damage(player, injury):
    """Serious injuries can permanently sap athleticism and potential."""
    level = injury.get("damage", 0)
    if level <= 0:
        return []
    changes = []
    # Hard-working players rehab better
    rehab = 1.2 - player.hidden.get("work_rate", 50) / 120.0
    for attr in ("speed", "acceleration", "agility"):
        if random.random() < 0.35 * level:
            loss = int(round(random.uniform(1, 2.5 * level) * rehab))
            if loss > 0:
                player.attrs[attr] = max(1, player.attrs[attr] - loss)
                changes.append((attr, -loss))
    loss = int(round(random.uniform(1, 3 * level) * rehab))
    player.attrs["injury_resistance"] = max(1, player.attrs["injury_resistance"] - loss)
    changes.append(("injury_resistance", -loss))
    pa_loss = int(round(random.uniform(0, 4 * level) * rehab))
    player.pa = max(player.ca, player.pa - pa_loss)
    player.recalc()
    return changes
