"""
player.py — the Player model and player generation.

Generation works backwards from a target Current Ability: we build a
realistic attribute profile for the position, archetype and age, then
nudge the relevant attributes until the computed CA hits the target. That
gives real variety inside a tier (two 150-CA receivers can look completely
different) while keeping quality gaps between tiers clear.
"""
import random
from collections import Counter

import names
import position_fit
from ratings import (ATTRIBUTES, PHYSICAL_ATTRS, MENTAL_ATTRS, ATHLETIC_ATTRS,
                     POSITION_WEIGHTS, HIDDEN_TRAITS, AGE_CURVES,
                     compute_ca, average_for_ca, stars_for, ca_tier,
                     ovr_from_ca, ovr_tier, stars_for_ovr, role_ratings)

# ── Player ids (persisted in saves) ───────────────────────────────────────────

_next_id = [1]


def next_player_id():
    pid = _next_id[0]
    _next_id[0] += 1
    return pid


def get_id_counter():
    return _next_id[0]


def set_id_counter(value):
    _next_id[0] = max(_next_id[0], int(value))


# ── Physical profiles ─────────────────────────────────────────────────────────
# Mean physical attributes for an average NFL starter at each position.

PHYS_MEANS = {
    #        SPD ACC AGI STR JMP STA INJ
    "QB":   (66, 68, 66, 52, 55, 76, 70),
    "RB":   (87, 88, 86, 66, 72, 80, 68),
    "FB":   (70, 72, 66, 80, 60, 80, 74),
    "WR":   (89, 88, 86, 52, 78, 80, 70),
    "TE":   (77, 78, 72, 72, 72, 80, 72),
    "OT":   (48, 62, 60, 84, 45, 82, 74),
    "IOL":  (45, 60, 56, 88, 40, 82, 76),
    "DT":   (55, 70, 58, 88, 52, 76, 74),
    "EDGE": (76, 82, 72, 76, 66, 78, 72),
    "LB":   (78, 80, 74, 72, 68, 82, 72),
    "CB":   (90, 90, 88, 50, 80, 82, 70),
    "S":    (86, 86, 82, 62, 76, 82, 72),
    "K":    (52, 55, 52, 50, 48, 70, 84),
    "P":    (52, 55, 52, 52, 48, 70, 84),
}
_PHYS_KEYS = ["speed", "acceleration", "agility", "strength", "jumping",
              "stamina", "injury_resistance"]

# Skills a position isn't rated on but realistically has some of
# (value = offset from the player's quality level)
CROSS_SKILLS = {
    "QB":   {"vision": -14, "juke_spin": -22, "break_tackle": -26},
    "RB":   {"release": -18, "separation": -12, "medium_route_running": -16,
             "catch_in_traffic": -16, "spectacular_catch": -18,
             "run_block": -22, "impact_block": -24},
    "FB":   {"short_route_running": -14, "release": -22, "vision": -10,
             "stiff_arm": -16},
    "WR":   {"vision": -16, "juke_spin": -12, "contact_balance": -20,
             "stiff_arm": -24, "run_block": -26, "impact_block": -30},
    "TE":   {"vision": -16, "break_tackle": -10, "contact_balance": -12,
             "stiff_arm": -14, "footwork": -20},
    "OT":   {"run_stop": -40},
    "IOL":  {"run_stop": -40},
    "DT":   {"pursuit": -12, "hit_power": -10, "zone_coverage": -38},
    "EDGE": {"hit_power": -8, "zone_coverage": -26, "man_coverage": -32},
    "LB":   {"interception": -18, "pass_breakup": -14, "anticipation": -8,
             "gap_awareness": -6, "finesse_move": -18},
    "CB":   {"catching": -16, "vision": -18, "ball_security": -18,
             "pursuit": -6, "hit_power": -18, "juke_spin": -20},
    "S":    {"catching": -18, "vision": -22, "ball_security": -20,
             "press_technique": -14, "block_shedding": -18},
    "K":    {"punt_power": -18, "punt_accuracy": -22},
    "P":    {"kick_power": -14, "kick_accuracy": -24},
}

# ── Archetypes ────────────────────────────────────────────────────────────────
# name: (base frequency, {attribute: modifier}, description)

ARCHETYPES = {
    "QB": {
        "Pocket Passer": (32, {"short_accuracy": 5, "medium_accuracy": 5, "deep_accuracy": 2,
                               "pocket_presence": 6, "decision_making": 5,
                               "progression_reads": 7, "touch": 4, "speed": -10,
                               "agility": -8, "acceleration": -8},
                          "Surgical from the pocket, reads the whole field, rarely runs"),
        "Field General": (12, {"decision_making": 7, "progression_reads": 8, "awareness": 6,
                               "leadership": 10, "composure": 6, "throw_power": -5,
                               "speed": -6},
                          "Elite processor and leader who wins before the snap"),
        "Gunslinger":    (20, {"throw_power": 12, "deep_accuracy": 8, "short_accuracy": -5,
                               "touch": -4, "decision_making": -4, "composure": 2},
                          "Cannon arm, attacks downfield, takes risks"),
        "Scrambler":     (18, {"speed": 16, "acceleration": 14, "agility": 12,
                               "short_accuracy": -4, "medium_accuracy": -4,
                               "progression_reads": -6, "pocket_presence": -6,
                               "vision": 10},
                          "Extends plays and gashes defenses with his legs"),
        "Dual Threat":   (10, {"speed": 10, "acceleration": 8, "agility": 8, "throw_power": 3,
                               "play_action": 6, "progression_reads": -3, "vision": 6},
                          "Balanced runner and thrower, deadly in the option game"),
        "Game Manager":  (8, {"short_accuracy": 4, "screen_accuracy": 6, "decision_making": 6,
                              "deep_accuracy": -8, "throw_power": -8},
                          "Protects the ball and keeps the offence on schedule"),
    },
    "RB": {
        "Power Back":     (25, {"break_tackle": 8, "contact_balance": 8, "stiff_arm": 8,
                                "strength": 10, "juke_spin": -6, "agility": -6, "speed": -4},
                           "Downhill hammer who finishes every run"),
        "Elusive Back":   (28, {"juke_spin": 10, "agility": 6, "acceleration": 6, "vision": 4,
                                "strength": -8, "break_tackle": -4, "stiff_arm": -6},
                           "Makes defenders miss in a phone booth"),
        "Receiving Back": (18, {"catching": 12, "short_route_running": 12, "pass_block": 4,
                                "break_tackle": -6, "strength": -6},
                           "A matchup weapon out of the backfield"),
        "Speed Back":     (14, {"speed": 8, "acceleration": 8, "vision": -4,
                                "contact_balance": -4, "break_tackle": -4},
                           "Home-run threat any time he finds a crease"),
        "Workhorse":      (15, {"stamina": 10, "vision": 4, "ball_security": 6,
                                "contact_balance": 3},
                           "Durable every-down back who can carry 25 times"),
    },
    "FB": {
        "Lead Blocker": (70, {"run_block": 8, "impact_block": 6, "catching": -6},
                         "Clears the way for the tailback"),
        "H-Back":       (30, {"catching": 8, "short_route_running": 8, "run_block": -4},
                         "Versatile chess piece who catches passes"),
    },
    "WR": {
        "Deep Threat":       (24, {"speed": 6, "deep_route_running": 8, "release": 4,
                                   "short_route_running": -6, "catch_in_traffic": -6,
                                   "strength": -4},
                              "Takes the top off defences"),
        "Possession":        (18, {"catching": 6, "catch_in_traffic": 8,
                                   "short_route_running": 6, "speed": -6},
                              "Sure hands that move the chains"),
        "Slot":              (22, {"agility": 6, "short_route_running": 8, "separation": 6,
                                   "acceleration": 4, "deep_route_running": -6,
                                   "jumping": -6},
                              "Quick and slippery working the middle"),
        "Contested Catch":   (18, {"spectacular_catch": 8, "catch_in_traffic": 6,
                                   "jumping": 8, "strength": 12, "separation": -6,
                                   "agility": -4},
                              "Big body who wins 50-50 balls"),
        "Route Technician":  (18, {"short_route_running": 6, "medium_route_running": 6,
                                   "deep_route_running": 6, "release": 6, "separation": 6,
                                   "speed": -4},
                              "Gets open against anyone"),
    },
    "TE": {
        "Receiving TE":   (32, {"catching": 6, "short_route_running": 6,
                                "medium_route_running": 6, "separation": 5, "speed": 4,
                                "run_block": -8, "pass_block": -6, "impact_block": -6},
                           "Mismatch weapon flexed out wide"),
        "Blocking TE":    (28, {"run_block": 10, "pass_block": 8, "impact_block": 8,
                                "strength": 8, "catching": -8, "medium_route_running": -8,
                                "speed": -6},
                           "Sixth offensive lineman"),
        "Complete TE":    (22, {"catching": 2, "run_block": 2, "awareness": 3},
                           "Does both jobs well"),
        "Vertical Threat": (18, {"speed": 8, "deep_route_running": 8, "spectacular_catch": 6,
                                 "jumping": 6, "run_block": -6},
                            "Stretches the seam"),
    },
    "OT": {
        "Pass Protector": (40, {"pass_block": 8, "footwork": 8, "agility": 4,
                                "run_block": -4, "impact_block": -4},
                           "Blind-side anchor"),
        "Road Grader":    (30, {"run_block": 8, "impact_block": 8, "strength": 6,
                                "footwork": -4, "agility": -4},
                           "Drives defenders off the ball"),
        "Balanced":       (30, {"awareness": 3}, "No glaring weakness"),
    },
    "IOL": {
        "Mauler":     (35, {"run_block": 8, "impact_block": 8, "strength": 6,
                            "pass_block": -4, "agility": -3},
                       "Physical people-mover"),
        "Pass Pro":   (30, {"pass_block": 8, "footwork": 6, "awareness": 4, "impact_block": -4},
                       "Keeps the pocket clean"),
        "Zone Mover": (35, {"pulling": 10, "agility": 6, "acceleration": 6, "footwork": 4,
                            "strength": -6},
                       "Athletic lineman built for zone schemes"),
    },
    "DT": {
        "Nose Tackle":  (30, {"run_stop": 8, "strength": 8, "block_shedding": 5,
                              "finesse_move": -8, "speed": -6, "acceleration": -6},
                         "Space eater who demands double teams"),
        "Penetrator":   (35, {"acceleration": 8, "finesse_move": 8, "pass_rush_iq": 6,
                              "strength": -4, "run_stop": -4},
                         "Quick first step, lives in the backfield"),
        "Interior Rusher": (35, {"power_move": 8, "strength": 6, "pass_rush_iq": 4,
                                 "finesse_move": -4},
                            "Collapses the pocket from inside"),
    },
    "EDGE": {
        "Speed Rusher":  (32, {"speed": 6, "acceleration": 8, "finesse_move": 10,
                               "agility": 4, "strength": -8, "power_move": -6,
                               "run_stop": -6},
                          "Bends the edge with pure explosiveness"),
        "Power Rusher":  (28, {"power_move": 10, "strength": 8, "block_shedding": 4,
                               "finesse_move": -6, "speed": -4},
                          "Bull-rushes tackles into the quarterback"),
        "Complete Edge": (22, {"pass_rush_iq": 6, "power_move": 2, "finesse_move": 2},
                          "Full arsenal of moves"),
        "Edge Setter":   (18, {"run_stop": 10, "block_shedding": 6, "tackling": 4,
                               "finesse_move": -6, "pass_rush_iq": -4},
                          "Sets a hard edge against the run"),
    },
    "LB": {
        "Coverage LB":  (25, {"zone_coverage": 8, "man_coverage": 8, "speed": 4,
                              "agility": 4, "block_shedding": -6, "run_stop": -4,
                              "strength": -4},
                         "Runs with backs and tight ends"),
        "Thumper":      (30, {"run_stop": 8, "tackling": 6, "hit_power": 8,
                              "block_shedding": 6, "zone_coverage": -6,
                              "man_coverage": -8, "speed": -4},
                         "Fills the hole and punishes ball carriers"),
        "Blitzer":      (15, {"power_move": 10, "pass_rush_iq": 10, "acceleration": 4,
                              "zone_coverage": -6, "man_coverage": -6},
                         "Pressure package specialist"),
        "Mike":         (15, {"play_recognition": 8, "awareness": 8, "leadership": 10,
                              "zone_coverage": 2},
                         "Quarterback of the defence"),
        "Sideline to Sideline": (15, {"pursuit": 8, "speed": 6, "acceleration": 4},
                                 "Range to make plays everywhere"),
    },
    "CB": {
        "Man Corner":   (35, {"man_coverage": 8, "press_technique": 6, "speed": 3,
                              "zone_coverage": -6, "play_recognition": -4},
                         "Shadows the opponent's best receiver"),
        "Zone Corner":  (30, {"zone_coverage": 8, "anticipation": 8, "interception": 6,
                              "man_coverage": -6, "press_technique": -6},
                         "Baits throws and jumps routes"),
        "Slot Corner":  (20, {"agility": 8, "acceleration": 4, "man_coverage": 4,
                              "jumping": -6, "press_technique": -4},
                         "Sticky in short areas"),
        "Press Corner": (15, {"press_technique": 10, "strength": 10, "jumping": 4,
                              "speed": -2, "agility": -4},
                         "Physical at the line"),
    },
    "S": {
        "Free Safety":   (38, {"zone_coverage": 8, "anticipation": 6, "interception": 6,
                               "speed": 4, "tackling": -6, "hit_power": -6,
                               "strength": -6},
                          "Centre fielder with range"),
        "Strong Safety": (38, {"tackling": 8, "hit_power": 8, "strength": 8,
                               "play_recognition": 4, "zone_coverage": -6,
                               "interception": -6, "speed": -4},
                          "Enforcer near the line"),
        "Hybrid":        (24, {"man_coverage": 6, "agility": 4},
                          "Matches up with tight ends and slots"),
    },
    "K": {
        "Big Leg":  (40, {"kick_power": 10, "kick_accuracy": -5},
                     "Range from 60 yards"),
        "Accurate": (60, {"kick_accuracy": 6, "kick_power": -5, "composure": 4},
                     "Money inside 50"),
    },
    "P": {
        "Big Leg":     (50, {"punt_power": 8, "punt_accuracy": -5},
                        "Booming hang time"),
        "Directional": (50, {"punt_accuracy": 8, "punt_power": -5},
                        "Pins opponents deep"),
    },
}

ARCHETYPE_SIZE = {   # (height in, weight lb) adjustments
    "Power Back": (0, 14), "Elusive Back": (-1, -8), "Speed Back": (0, -6),
    "Contested Catch": (2, 14), "Slot": (-2, -12), "Deep Threat": (0, -6),
    "Blocking TE": (0, 10), "Receiving TE": (0, -8), "Nose Tackle": (0, 30),
    "Penetrator": (0, -12), "Speed Rusher": (0, -12), "Power Rusher": (0, 10),
    "Thumper": (0, 8), "Coverage LB": (0, -8), "Press Corner": (1, 6),
    "Slot Corner": (-1, -6), "Strong Safety": (0, 8), "Scrambler": (-1, -6),
    "Zone Mover": (0, -10), "Mauler": (0, 10),
}

SIZE = {   # (height mean, sd), (weight mean, sd)
    "QB": ((75.0, 1.5), (222, 10)), "RB": ((70.5, 1.5), (213, 12)),
    "FB": ((73.0, 1.2), (245, 8)), "WR": ((73.0, 2.0), (200, 12)),
    "TE": ((76.5, 1.0), (252, 8)), "OT": ((77.5, 1.0), (315, 10)),
    "IOL": ((76.0, 1.0), (312, 10)), "DT": ((75.5, 1.2), (305, 15)),
    "EDGE": ((76.0, 1.0), (258, 10)), "LB": ((74.0, 1.0), (238, 8)),
    "CB": ((71.5, 1.3), (195, 7)), "S": ((72.5, 1.2), (205, 8)),
    "K": ((72.0, 2.0), (195, 12)), "P": ((74.0, 2.0), (210, 12)),
}


def _clamp(v, lo=1, hi=99):
    return max(lo, min(hi, int(round(v))))


def choose_archetype(position, weights=None):
    table = ARCHETYPES.get(position, {})
    if not table:
        return None
    names_ = list(table.keys())
    w = [max(0.5, (weights or {}).get(n, table[n][0])) for n in names_]
    return random.choices(names_, weights=w, k=1)[0]


# ── The Player ────────────────────────────────────────────────────────────────

class Player:
    # Roster-status defaults (class level so older saves pick them up too)
    ps = False              # on the practice squad
    ir = None               # {"year", "week", "season_ending"} while on injured reserve
    tag_count = 0           # times franchise-tagged
    potw = 0                # Player of the Week awards
    holdout = False         # staying away from the team over his contract
    holdout_weeks = 0
    fa_origin = None        # (team, year) when he left a team in free agency
    familiarity = None      # {slot: 0-100} learned at other positions (position_fit.py)
    fam_used = None         # {slot: season} last season he got reps there

    def __init__(self, name, position, age):
        self.id = next_player_id()
        self.name = name
        self.position = position
        self.age = age
        self.archetype = None
        self.attrs = {}
        self.hidden = {}
        self.pa = 100
        self._ca = 1
        self.height = 72
        self.weight = 200
        self.college = names.random_college()
        self.hometown = names.random_hometown()
        self.jersey = 0

        # Career / contract state
        self.team = None              # team abbreviation or None (FA)
        self.contract = None          # {"salary", "years", "signed"}
        self.draft = None             # {"year", "round", "pick", "team"}
        self.years_pro = 0
        self.retired = False
        self.retired_year = None
        self.hall_of_fame = False

        # Dynamic state
        self.morale = 65              # 1-100
        self.reputation = 10          # 0-100 fame / respect
        self.injury = None            # {"name", "weeks", "season_ending"}
        self.injury_history = []      # [(season, name, weeks)]
        self.last_change = 0          # CA change at last development tick
        self.scout_noise = (random.gauss(0, 1), random.gauss(0, 1))
        self.on_rookie_deal = False

        # Stats
        self.season_stats = Counter()
        self.playoff_stats = Counter()
        self.game_log = []            # [(week, opponent, home, result, Counter)]
        self.combine = None
        self.proj_round = None
        self.proj_rank = None
        self.career = {}              # season -> {"team", "stats"}
        self.awards = []              # [(season, award)]
        self.ca_history = {}          # season -> CA
        self.last_season_gp = 0
        self.last_season_gs = 0

    # ── Ratings ──────────────────────────────────────────────────────────────

    def __getstate__(self):
        state = dict(self.__dict__)
        state.pop("_fit_cache", None)
        return state

    def recalc(self):
        self._ca = compute_ca(self.attrs, self.position)
        if self._ca > self.pa:
            self.pa = self._ca
        self.__dict__.pop("_fit_cache", None)
        return self._ca

    @property
    def ca(self):
        return self._ca

    def rating_at(self, position):
        """CA at any slot: his own position, or that slot's formula with size fit and familiarity."""
        if position == self.position:
            return self._ca
        return position_fit.slot_ca(self, position)

    # ── Display ratings (1-99, position-relative) ────────────────────────────
    @property
    def ovr(self):
        return ovr_from_ca(self._ca, self.position)

    @property
    def pot(self):
        """Projected peak rating. Past his prime a player's ceiling is what he is now."""
        if self.years_to_peak() <= 0:
            return self.ovr
        return ovr_from_ca(max(self.pa, self._ca), self.position)

    def ovr_at(self, position):
        return ovr_from_ca(self.rating_at(position), position)

    def pot_at(self, position):
        """Projected peak rating at a slot, once he has learned it."""
        if position == self.position:
            return self.pot
        return ovr_from_ca(position_fit.slot_pot_ca(self, position), position)

    def pot_range_at(self, position, scouting=10):
        """The scouts' potential range at a slot (what he could be there once he has learned it)."""
        if position == self.position:
            return self.scouted_pot_range(scouting)
        base = position_fit.learned_ca(self, position)
        if self.age > self.curve()[1] or self.years_to_peak() <= 0:
            v = ovr_from_ca(base, position)
            return (v, v)
        lo, hi = self.scouted_pa_range(scouting)
        cov = position_fit.coverage(self.position, position)
        return tuple(ovr_from_ca(min(200, base + max(0, b - self._ca) * cov), position) for b in (lo, hi))

    @property
    def roles(self):
        return role_ratings(self.attrs, self.position)

    @property
    def best_role(self):
        r = self.roles
        return r[0] if r else (self.archetype or self.position, self.ovr)

    @property
    def stars(self):
        return stars_for_ovr(self.ovr)

    @property
    def pa_stars(self):
        return stars_for_ovr(self.pot)

    @property
    def tier(self):
        return ovr_tier(self.ovr)

    def scouted_ovr(self, scouting=10):
        return ovr_from_ca(self.scouted_ca(scouting), self.position)

    def scouted_pot_range(self, scouting=10):
        if self.age > self.curve()[1] or self.years_to_peak() <= 0:
            return (self.ovr, self.ovr)
        lo, hi = self.scouted_pa_range(scouting)
        return (ovr_from_ca(lo, self.position), ovr_from_ca(hi, self.position))

    def a(self, key):
        return self.attrs.get(key, 30)

    @property
    def return_rating(self):
        g = self.attrs.get
        return int(round((g("speed", 50) * 23 + g("acceleration", 50) * 18
                          + g("agility", 50) * 18 + g("catching", 40) * 13
                          + g("vision", 40) * 13 + g("stamina", 60) * 10
                          + g("stiff_arm", 30) * 5) / 100))

    @property
    def is_injured(self):
        return self.injury is not None

    @property
    def height_str(self):
        return f"{self.height // 12}'{self.height % 12}\""

    @property
    def salary(self):
        return self.contract["salary"] if self.contract else 0

    @property
    def contract_years(self):
        return self.contract["years"] if self.contract else 0

    @property
    def peak(self):
        return self.curve()

    def curve(self):
        """
        This player's own career curve: (growth ends, decline starts after,
        decline severity). The league averages in ratings.AGE_CURVES are shifted
        per player — some bloom late, some peak early, some age gracefully.
        Hard workers and durable bodies tend to last a little longer.
        """
        grow, prime_end, sev = AGE_CURVES[self.position]
        shifts = getattr(self, "curve_shift", None)
        if shifts is None:
            import zlib
            rng = random.Random(zlib.crc32(f"curve:{self.id}".encode()))
            work = self.hidden.get("work_rate", 50)
            dur = self.attrs.get("injury_resistance", 60)
            g = max(-2.5, min(2.5, rng.gauss(0, 1.0)))
            d = max(-3.0, min(3.0, rng.gauss(0, 1.2) + (work - 50) / 50.0 * 0.6 + (dur - 60) / 40.0 * 0.4))
            shifts = (round(g, 2), round(d, 2))
            self.curve_shift = shifts
        g, d = shifts
        grow_p = grow + g
        prime_p = max(grow_p, prime_end + d)
        return grow_p, prime_p, sev

    def dev_profile(self):
        """
        How predictable his development is: "Raw" players (about one in six) keep
        a wide range of outcomes - and a wide scouted potential - until they are
        close to their peak; "Polished" players are much easier to project (a
        higher floor and a lower ceiling); the rest sit in between.
        """
        prof = getattr(self, "_dev_profile", None)
        if prof is None:
            import zlib
            u = random.Random(zlib.crc32(f"devprof:{self.id}".encode())).random()
            prof = "Raw" if u < 0.18 else "Polished" if u >= 0.55 else "Normal"
            self._dev_profile = prof
        return prof

    def years_to_peak(self):
        return max(0.0, self.curve()[0] - self.age)

    def development_stage(self):
        grow, prime_end, _ = self.curve()
        if self.age < grow:
            return "Developing"
        if self.age <= prime_end:
            return "Prime"
        return "Declining"

    # Scouted estimates — the manager never sees true PA, only an estimate
    # whose accuracy depends on his scouts and how long the player has been
    # in the league.
    def scouted_ca(self, scouting=10):
        if self.years_pro >= 1:
            return self._ca
        err = max(2.0, 16 - scouting * 0.7)
        return int(max(1, min(200, self._ca + self.scout_noise[0] * err)))

    def scouted_pa_range(self, scouting=10):
        """
        Nobody knows a young player's ceiling. The range is wide for a
        21-year-old and narrows as he approaches his peak; better scouting
        narrows it further and centres it closer to the truth.
        """
        years = self.years_to_peak()
        if years <= 0 or self.pa - self._ca <= 1:
            return (self._ca, self._ca)
        prof = self.dev_profile()
        if prof == "Raw":
            years = max(years, min(4.5, years + 2.5))     # stays hard to read for longer
        err = (2.5 + years * 2.6) * (1.3 - scouting / 20.0 * 0.6) * DEV_RANGE[prof]
        if self.years_pro == 0:
            err *= 1.15
        mid = self.pa + self.scout_noise[1] * err * 0.45
        lo = int(max(self._ca, mid - err))
        hi = int(min(200, max(lo + 2, mid + err)))
        return (lo, hi)

    def __repr__(self):
        return f"<{self.position} {self.name} {self.age}y CA{self._ca} PA{self.pa}>"


# Width of the scouted potential range by development profile (see Player.dev_profile)
DEV_RANGE = {"Raw": 1.25, "Normal": 0.90, "Polished": 0.72}
# How far a player's true ceiling moves each offseason, and how often he breaks out or busts
DEV_SWING = {"Raw": 1.45, "Normal": 1.0, "Polished": 0.75}
DEV_SURPRISE = {"Raw": 1.6, "Normal": 1.0, "Polished": 0.6}


# ── Generation ────────────────────────────────────────────────────────────────

def _age_modifier(attr, position, age):
    grow, prime_end, _ = AGE_CURVES[position]
    if attr in ATHLETIC_ATTRS:
        if age > prime_end:
            return -(age - prime_end) * 2.5
        return 0.0
    if attr == "strength":
        return -(24 - age) * 2.0 if age < 24 else 0.0
    if attr == "injury_resistance":
        return -(age - 28) * 1.5 if age > 28 else 0.0
    if attr == "stamina":
        return -(age - 30) * 1.5 if age > 30 else 0.0
    if attr in MENTAL_ATTRS:
        return (min(age, 32) - 25) * 1.4
    if attr in PHYSICAL_ATTRS:
        return 0.0
    return (min(age, 30) - 25) * 0.8


def generate_player(position, age, target_ca, pa=None, archetype=None,
                    archetype_weights=None, name=None):
    """Create a player at `position` whose CA lands on `target_ca`."""
    p = Player(name or names.random_name(), position, age)
    p.archetype = archetype or choose_archetype(position, archetype_weights)
    arch_mods = ARCHETYPES.get(position, {}).get(p.archetype, (0, {}, ""))[1]
    weights = POSITION_WEIGHTS[position]
    cross = CROSS_SKILLS.get(position, {})
    phys = dict(zip(_PHYS_KEYS, PHYS_MEANS[position]))

    q = average_for_ca(target_ca)
    attrs = {}
    for attr in ATTRIBUTES:
        mod = arch_mods.get(attr, 0) + _age_modifier(attr, position, age)
        if attr in phys:
            scale = 0.45 if attr in weights else 0.3
            mean = phys[attr] + scale * (q - 70) + mod
            sd = 4.5
        elif attr in weights:
            mean = q + mod
            sd = 5.5
        elif attr in cross:
            mean = q + cross[attr] + mod
            sd = 7.0
        elif attr in MENTAL_ATTRS:
            mean = 45 + 0.5 * (q - 70) + mod
            sd = 8.0
        elif attr.startswith(("kick_", "punt_")):
            mean = 22
            sd = 7.0
        else:
            mean = 26 + mod * 0.3
            sd = 7.0
        attrs[attr] = _clamp(random.gauss(mean, sd), 5, 99)
    p.attrs = attrs

    # Nudge relevant attributes until CA lands on target
    for _ in range(8):
        ca = compute_ca(attrs, position)
        diff = target_ca - ca
        if abs(diff) <= 1:
            break
        shift = diff / 2.6
        for attr in weights:
            factor = 0.6 if attr in phys else 1.0
            attrs[attr] = _clamp(attrs[attr] + shift * factor + random.uniform(-0.4, 0.4))
    p.recalc()

    # Hidden personality
    for trait in HIDDEN_TRAITS:
        base = 55 + (target_ca - 120) * 0.06
        p.hidden[trait] = _clamp(random.gauss(base, 16), 5, 99)

    # Potential
    if pa is None:
        grow = AGE_CURVES[position][0]
        years = max(0, grow - age + 1)
        if years > 0:
            # Growth is front-loaded: ~5 a year while young, tapering in the last seasons before
            # the peak (matches what development.py actually produces)
            exp_growth = sum({0: 0.8, 1: 2.0, 2: 3.5}.get(grow - a, 5.0) for a in range(age, grow + 1))
            gap = max(0.0, random.gauss(exp_growth, exp_growth * 0.42 + 3))
            if random.random() < 0.10:
                gap += abs(random.gauss(12, 6))
        else:
            gap = max(0.0, random.gauss(2, 3))
        # Players who are already very good have less headroom left
        gap *= max(0.25, min(1.1, (190 - p.ca) / 90.0))
        pa = p.ca + int(gap)
    p.pa = int(max(p.ca, min(200, pa)))

    # Size
    (hm, hs), (wm, ws) = SIZE[position]
    dh, dw = ARCHETYPE_SIZE.get(p.archetype, (0, 0))
    p.height = int(round(random.gauss(hm + dh, hs)))
    p.weight = int(round(random.gauss(wm + dw + (attrs["strength"] - 70) * 0.4, ws)))

    # Reputation scales with ability and experience
    p.years_pro = max(0, age - 22 + random.randint(-1, 1))
    p.reputation = int(max(1, min(95, (p.ca - 70) * 0.55 + p.years_pro * 1.5
                                  + random.gauss(0, 6))))
    return p


def jersey_for(position, taken):
    ranges = {
        "QB": [(1, 19)], "RB": [(20, 39), (0, 9)], "FB": [(30, 49)],
        "WR": [(10, 19), (80, 89), (0, 9)], "TE": [(80, 89), (40, 49)],
        "OT": [(60, 79)], "IOL": [(50, 79)], "DT": [(90, 99), (50, 79)],
        "EDGE": [(40, 59), (90, 99)], "LB": [(40, 59), (0, 9)],
        "CB": [(20, 39), (0, 9)], "S": [(20, 49), (0, 9)],
        "K": [(1, 19)], "P": [(1, 19)],
    }
    options = [n for lo, hi in ranges.get(position, [(1, 99)])
               for n in range(lo, hi + 1) if n not in taken]
    return random.choice(options) if options else random.randint(1, 99)
