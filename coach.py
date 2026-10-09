"""
coach.py — head coaches, their schemes, and coaching trees.

Coaches are a major driver of how the league *plays*. Each coach has an
offensive and defensive philosophy. When teams fire coaches they tend to
hire from the trees of recently successful coaches, so winning ideas spread
around the league — one of the ways eras emerge naturally.
"""
import random

import names

# Offensive philosophies: tendencies the coach starts from
#   pass_lean  : shifts neutral pass rate (-1 run heavy .. +1 pass heavy)
#   deep       : appetite for deep shots (-1 .. +1)
#   outside    : share of outside/zone runs vs inside/power (0..1)
#   qb_run     : designed QB runs / option (0..1)
#   heavy      : use of 2-TE / fullback personnel (0..1)
#   tempo      : pace (0 slow .. 1 hurry-up)
#   screen     : screen game usage (0..1)
OFFENSIVE_SCHEMES = {
    "West Coast":    dict(pass_lean=0.10, deep=-0.55, outside=0.45, qb_run=0.05,
                          heavy=0.30, tempo=0.45, screen=0.55),
    "Air Coryell":   dict(pass_lean=0.22, deep=0.75, outside=0.40, qb_run=0.05,
                          heavy=0.30, tempo=0.50, screen=0.25),
    "Air Raid":      dict(pass_lean=0.55, deep=0.05, outside=0.55, qb_run=0.10,
                          heavy=0.00, tempo=0.85, screen=0.55),
    "Run and Shoot": dict(pass_lean=0.55, deep=0.35, outside=0.50, qb_run=0.05,
                          heavy=0.00, tempo=0.65, screen=0.30),
    "Spread Option": dict(pass_lean=-0.10, deep=0.00, outside=0.60, qb_run=0.92,
                          heavy=0.10, tempo=0.75, screen=0.45),
    "Power Run":     dict(pass_lean=-0.50, deep=0.15, outside=0.20, qb_run=0.05,
                          heavy=0.80, tempo=0.25, screen=0.20),
    "Zone Run":      dict(pass_lean=-0.25, deep=0.00, outside=0.75, qb_run=0.10,
                          heavy=0.55, tempo=0.45, screen=0.35),
    "Pro Style":     dict(pass_lean=0.00, deep=0.05, outside=0.45, qb_run=0.05,
                          heavy=0.45, tempo=0.45, screen=0.35),
    # Systems borrowed from the college and high-school game
    "Pistol":        dict(pass_lean=-0.15, deep=0.10, outside=0.50, qb_run=0.55,
                          heavy=0.35, tempo=0.55, screen=0.35),
    "Wing-T":        dict(pass_lean=-0.80, deep=0.35, outside=0.55, qb_run=0.20,
                          heavy=0.85, tempo=0.30, screen=0.10),
    "Flexbone":      dict(pass_lean=-1.00, deep=0.80, outside=0.50, qb_run=0.90,
                          heavy=0.20, tempo=0.35, screen=0.05),
}

# How much each system splits carries between backs (0 = one bell-cow,
# 1 = full committee). Individual coaches vary around this.
SCHEME_COMMITTEE = {
    "West Coast": 0.50, "Air Coryell": 0.40, "Air Raid": 0.60, "Run and Shoot": 0.55,
    "Spread Option": 0.50, "Power Run": 0.22, "Zone Run": 0.50, "Pro Style": 0.38,
    "Pistol": 0.40, "Wing-T": 0.70, "Flexbone": 0.80,
}

# Concept mix by scheme: play-action rate, RPO rate, appetite for trick plays
SCHEME_CONCEPTS = {
    "West Coast":    dict(play_action=0.55, rpo=0.25, trick=0.35),
    "Pro Style":     dict(play_action=0.60, rpo=0.15, trick=0.30),
    "Zone Run":      dict(play_action=0.75, rpo=0.25, trick=0.30),
    "Air Coryell":   dict(play_action=0.50, rpo=0.10, trick=0.35),
    "Spread Option": dict(play_action=0.40, rpo=0.75, trick=0.50),
    "Power Run":     dict(play_action=0.55, rpo=0.10, trick=0.30),
    "Air Raid":      dict(play_action=0.25, rpo=0.55, trick=0.45),
    "Run and Shoot": dict(play_action=0.20, rpo=0.30, trick=0.45),
    "Pistol":        dict(play_action=0.60, rpo=0.60, trick=0.40),
    "Wing-T":        dict(play_action=0.80, rpo=0.05, trick=0.60),
    "Flexbone":      dict(play_action=0.85, rpo=0.05, trick=0.45),
}

# Situational play-calling by system (each coordinator varies around these):
#   sit_early : pass lean on 1st/2nd down        sit_short: pass lean on 3rd/4th & short
#   sit_rz    : pass lean in the red zone         sit_shot : appetite for shot plays on 1st down
#   sit_long  : screens and draws on 3rd & long ("take the points, punt it" calls)
SCHEME_SITUATIONAL = {
    "West Coast":    dict(sit_early=0.04, sit_short=0.06, sit_rz=0.04, sit_shot=0.25, sit_long=0.45),
    "Air Coryell":   dict(sit_early=0.04, sit_short=0.00, sit_rz=0.02, sit_shot=0.75, sit_long=0.20),
    "Air Raid":      dict(sit_early=0.06, sit_short=0.10, sit_rz=0.06, sit_shot=0.45, sit_long=0.30),
    "Run and Shoot": dict(sit_early=0.05, sit_short=0.08, sit_rz=0.05, sit_shot=0.55, sit_long=0.25),
    "Spread Option": dict(sit_early=-0.02, sit_short=-0.06, sit_rz=-0.03, sit_shot=0.40, sit_long=0.35),
    "Power Run":     dict(sit_early=-0.05, sit_short=-0.12, sit_rz=-0.08, sit_shot=0.50, sit_long=0.35),
    "Zone Run":      dict(sit_early=-0.03, sit_short=-0.08, sit_rz=-0.05, sit_shot=0.45, sit_long=0.30),
    "Pro Style":     dict(sit_early=0.00, sit_short=-0.04, sit_rz=0.00, sit_shot=0.45, sit_long=0.30),
    "Pistol":        dict(sit_early=-0.02, sit_short=-0.06, sit_rz=-0.03, sit_shot=0.45, sit_long=0.30),
    "Wing-T":        dict(sit_early=-0.06, sit_short=-0.15, sit_rz=-0.10, sit_shot=0.55, sit_long=0.30),
    "Flexbone":      dict(sit_early=-0.08, sit_short=-0.18, sit_rz=-0.12, sit_shot=0.70, sit_long=0.15),
}
SIT_KEYS = ("sit_early", "sit_short", "sit_rz", "sit_shot", "sit_long")

# What each system does especially well when it is run properly (small, opposite-signed
# edges so that no system is simply best):
#   short_comp / short_yac: timing and spacing on quick throws (completion %, YAC multiplier)
#   run_edge: blocking edge for its run game (misdirection teams are hard to prepare for)
SCHEME_EXECUTION = {
    "West Coast": dict(short_comp=0.03, short_yac=1.15, run_edge=0.0),
    "Air Raid": dict(short_comp=0.015, short_yac=1.05, run_edge=-0.05),
    "Run and Shoot": dict(short_comp=0.01, short_yac=1.05, run_edge=-0.05),
    "Wing-T": dict(short_comp=0.0, short_yac=1.0, run_edge=0.20),
    "Flexbone": dict(short_comp=0.0, short_yac=1.0, run_edge=0.24),
    "Power Run": dict(short_comp=0.0, short_yac=1.0, run_edge=0.08),
    "Zone Run": dict(short_comp=0.0, short_yac=1.0, run_edge=0.05),
    "Pistol": dict(short_comp=0.0, short_yac=1.0, run_edge=0.06),
    "Spread Option": dict(short_comp=0.01, short_yac=1.05, run_edge=0.05),
}


def sit_tendency(coach, key):
    """A coordinator's situational tendency (filled in from his system for older saves)."""
    t = coach.tendencies
    if key not in t:
        t[key] = SCHEME_SITUATIONAL.get(coach.off_scheme, SCHEME_SITUATIONAL["Pro Style"])[key]
    return t[key]


# Defensive philosophies
#   blitz : extra rushers rate (0..1)
#   zone  : zone vs man (0 man .. 1 zone)
#   front : "4-3" or "3-4" base front (affects who rushes)
#   two_high : how often two deep safeties (limits deep passes, softer vs run)
DEFENSIVE_SCHEMES = {
    "4-3 Over":      dict(blitz=0.25, zone=0.50, front="4-3", two_high=0.45),
    "3-4 Two Gap":   dict(blitz=0.30, zone=0.50, front="3-4", two_high=0.45),
    "Tampa 2":       dict(blitz=0.15, zone=0.85, front="4-3", two_high=0.80),
    "46 Blitz":      dict(blitz=0.55, zone=0.25, front="4-3", two_high=0.20),
    "Cover 3":       dict(blitz=0.25, zone=0.70, front="4-3", two_high=0.30),
    "Press Man":     dict(blitz=0.30, zone=0.20, front="3-4", two_high=0.35),
    "Two-High Match": dict(blitz=0.15, zone=0.70, front="3-4", two_high=0.85),
    "Zone Blitz":    dict(blitz=0.45, zone=0.65, front="3-4", two_high=0.40),
}

COACH_RATINGS = ["offense", "defense", "development", "motivation",
                 "game_management", "adaptability", "discipline"]

COACH_RATING_LABELS = {
    "offense": "Offensive Play-Calling",
    "defense": "Defensive Play-Calling",
    "development": "Player Development",
    "motivation": "Motivation",
    "game_management": "Game Management",
    "adaptability": "Adaptability",
    "discipline": "Discipline",
}


class Coach:
    youth_trust = None       # 0-1: how readily he plays young players (front_office.coach_youth_trust)

    def __init__(self, name=None, age=None):
        self.name = name or names.random_name()
        self.age = age or random.randint(36, 62)
        self.ratings = {r: random.randint(6, 17) for r in COACH_RATINGS}
        self.off_scheme = random.choice(list(OFFENSIVE_SCHEMES))
        self.def_scheme = random.choice(list(DEFENSIVE_SCHEMES))
        self.tendencies = {}
        self.reputation = random.randint(20, 60)
        self.career_wins = 0
        self.career_losses = 0
        self.career_ties = 0
        self.titles = 0
        self.seasons = 0
        self.team_seasons = 0          # seasons with current team
        self.mentor = None             # name of the coach whose tree he is from
        self.tree_origin = None        # team whose system he brought
        self.history = []              # [(season, team, w, l, t, result)]
        self.set_tendencies()

    def set_tendencies(self, base_off=None, base_def=None, noise=0.08):
        off = dict(base_off or OFFENSIVE_SCHEMES[self.off_scheme])
        de = dict(base_def or DEFENSIVE_SCHEMES[self.def_scheme])
        t = {}
        for k, v in off.items():
            if k.startswith("sit_") or not isinstance(v, (int, float)) or k in ("blitz", "zone", "two_high",
                                                                                "aggression", "committee",
                                                                                "play_action", "rpo", "trick"):
                continue
            lo, hi = (-1.0, 1.0) if k in ("pass_lean", "deep") else (0.0, 1.0)
            t[k] = max(lo, min(hi, v + random.gauss(0, noise)))
        for k in ("blitz", "zone", "two_high"):
            t[k] = max(0.0, min(1.0, de[k] + random.gauss(0, noise)))
        t["front"] = de["front"]
        t["aggression"] = max(0.0, min(1.0, random.gauss(0.45, 0.18)))
        base_c = (base_off or {}).get("committee", SCHEME_COMMITTEE.get(self.off_scheme, 0.45))
        t["committee"] = max(0.0, min(1.0, base_c + random.gauss(0, 0.16)))
        concepts = SCHEME_CONCEPTS.get(self.off_scheme, {})
        for k in ("play_action", "rpo", "trick"):
            b = (base_off or {}).get(k, concepts.get(k, 0.4))
            t[k] = max(0.0, min(1.0, b + random.gauss(0, 0.10)))
        sit = SCHEME_SITUATIONAL.get(self.off_scheme, SCHEME_SITUATIONAL["Pro Style"])
        for k in SIT_KEYS:
            b = (base_off or {}).get(k, sit[k])
            if k in ("sit_shot", "sit_long"):
                t[k] = max(0.0, min(1.0, b + random.gauss(0, noise * 1.5)))
            else:
                t[k] = max(-0.25, min(0.25, b + random.gauss(0, noise * 0.5)))
        self.tendencies = t

    def r(self, key):
        return self.ratings.get(key, 10)

    @property
    def overall(self):
        w = {"offense": 3, "defense": 3, "development": 2, "motivation": 1.5,
             "game_management": 2, "adaptability": 1.5, "discipline": 1}
        return sum(self.ratings[k] * v for k, v in w.items()) / sum(w.values())

    @property
    def record_str(self):
        s = f"{self.career_wins}-{self.career_losses}"
        return s + (f"-{self.career_ties}" if self.career_ties else "")

    @property
    def win_pct(self):
        g = self.career_wins + self.career_losses + self.career_ties
        return (self.career_wins + 0.5 * self.career_ties) / g if g else 0.0


def generate_coach(quality=None):
    c = Coach()
    if quality is not None:
        for r in COACH_RATINGS:
            c.ratings[r] = max(1, min(20, int(round(random.gauss(quality, 2.5)))))
    return c


def hire_from_tree(source_coach, source_team_abbr):
    """
    A new coach who learned under a successful coach. He brings a mutated
    version of the mentor's system.
    """
    c = generate_coach(quality=random.uniform(9, 15))
    c.age = random.randint(34, 50)
    c.off_scheme = source_coach.off_scheme
    c.def_scheme = source_coach.def_scheme if random.random() < 0.55 \
        else random.choice(list(DEFENSIVE_SCHEMES))
    base_off = {k: source_coach.tendencies.get(k, v)
                for k, v in OFFENSIVE_SCHEMES[c.off_scheme].items()}
    base_off["committee"] = source_coach.tendencies.get(
        "committee", SCHEME_COMMITTEE.get(c.off_scheme, 0.45))
    c.set_tendencies(base_off=base_off, noise=0.10)
    c.mentor = source_coach.name
    c.tree_origin = source_team_abbr
    c.reputation = random.randint(30, 55)
    return c
