"""
engine.py — the play-by-play match engine.

Every snap is simulated: personnel, play call, pass protection vs. the rush,
receiver vs. defender matchups, the quarterback's read, completion, yards
after catch, tackles, penalties, injuries and the game clock. Outcomes come
from attribute matchups fed through probability curves that were calibrated
against real NFL league-wide averages, so the stats a league produces are a
product of the talent in it — better quarterbacks league-wide genuinely
raise completion rates, weak run-blocking classes genuinely lower yards per
carry, and so on.
"""
import math
import random
from collections import Counter

from settings import settings
from injuries import roll_injury
import weather as wx
import committee
import staff as staff_mod
import playbook as pb
import defense as dfn_lib
import specialteams as st_lib
import advanced as adv_lib
import trenches
import grades
import situations as sit_lib
import position_fit as fit
import packages
import gameday
from coach import sit_tendency, SCHEME_EXECUTION

QUARTER = 900

OFF_POS = {"QB", "RB", "FB", "WR", "TE", "OT", "IOL"}
DEF_POS = {"DT", "EDGE", "LB", "CB", "S"}

# ── Fatigue ───────────────────────────────────────────────────────────────────
# Energy runs 0-100. Every snap on the field costs energy (big men and pass
# rushers burn it fastest); the huddle gives a little back, the sideline a lot.
# Tired players lose physical sharpness and get hurt more, so coaches rotate.
RUN_BLOCK_SHIFT = 0.0      # calibration offset for the matchup-based run blocking edge
PASS_RUSH_BASE = -2.46      # per-matchup log-odds of a rusher winning (calibrated to NFL pressure rates)
DRAIN = {"QB": 0.35, "RB": 1.9, "FB": 1.5, "WR": 1.25, "TE": 1.35, "OT": 0.75, "IOL": 0.75,
         "DT": 3.0, "EDGE": 2.6, "LB": 1.45, "CB": 1.1, "S": 1.0, "K": 0.0, "P": 0.0}
HUDDLE_REC = 0.6           # per snap, on the field, normal tempo
WEAR_FRAC = 0.32           # share of each snap's cost that only halftime (partly) gives back
SIDELINE_REC = 3.2         # per snap spent on the bench (either team's possession)
FAT_START = 86.0           # below this energy, attributes start to suffer
FAT_SLOPE = 0.17           # attribute points lost per point of energy below FAT_START
PHYSICAL = frozenset([
    "speed", "acceleration", "agility", "strength", "jumping", "stamina", "throw_power",
    "break_tackle", "contact_balance", "juke_spin", "stiff_arm", "release", "separation",
    "run_block", "pass_block", "impact_block", "pulling", "footwork", "power_move", "finesse_move",
    "block_shedding", "pursuit", "tackling", "hit_power", "man_coverage", "press_technique",
    "deep_route_running", "kick_power", "punt_power"])
# How readily coaches rotate a position group (multiplies the cost of fatigue
# when deciding whether a fresher backup is the better option right now)
ROTATION_STYLE = {"none": 0.3, "light": 0.65, "normal": 1.0, "heavy": 1.5}
POS_ROTATION = {"DT": 1.6, "EDGE": 1.6, "LB": 0.8, "CB": 0.55, "S": 0.55, "WR": 0.9, "TE": 0.9,
                "RB": 1.0, "OT": 0.3, "IOL": 0.3, "QB": 0.0}
ROT_GROUP = {"DT": "DL", "EDGE": "DL", "LB": "LB", "CB": "DB", "S": "DB", "WR": "WR", "TE": "TE",
             "RB": "RB", "OT": "OL", "IOL": "OL", "QB": "QB"}


def _sig(x):
    return 1.0 / (1.0 + math.exp(-x))


def _clip(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def _phi(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _short(name):
    parts = name.split(" ", 1)
    return f"{parts[0][0]}. {parts[1]}" if len(parts) == 2 else name


# ── Result container ──────────────────────────────────────────────────────────

class GameResult:
    def __init__(self, home, away, week, season, playoff=None):
        self.home = home
        self.away = away
        self.week = week
        self.season = season
        self.playoff = playoff            # None or round name
        self.home_score = 0
        self.away_score = 0
        self.quarters = {home: [0, 0, 0, 0], away: [0, 0, 0, 0]}
        self.overtime = False
        self.team_stats = {home: Counter(), away: Counter()}
        self.player_stats = {}            # pid -> Counter
        self.player_meta = {}             # pid -> (name, pos, team, jersey)
        self.plays = []                   # (q, clock, team, situation, text, kind)
        self.scoring = []                 # (q, clock, team, text, home, away)
        self.drives = {home: [], away: []}
        self.injuries = []                # (pid, name, team, injury name, weeks)
        self.starters = set()
        self.weather = None               # dict from weather.roll_weather
        # Parallel to plays: (offense yard line, down, to go, home score, away score,
        #                     home win prob x1000, momentum x100, home has ball)
        self.states = []
        self.diagrams = []                # parallel to plays: play diagram dict or None
        self.slot_snaps = {}              # pid -> {slot: snaps} for snaps away from his own position

    @property
    def winner(self):
        if self.home_score > self.away_score:
            return self.home
        if self.away_score > self.home_score:
            return self.away
        return None

    @property
    def loser(self):
        w = self.winner
        if w is None:
            return None
        return self.away if w == self.home else self.home

    def score_of(self, abbr):
        return self.home_score if abbr == self.home else self.away_score

    def opponent(self, abbr):
        return self.away if abbr == self.home else self.home

    def summary(self):
        ot = " (OT)" if self.overtime else ""
        return f"{self.away} {self.away_score} @ {self.home} {self.home_score}{ot}"


# ── Per-team game state ───────────────────────────────────────────────────────

class Side:
    def __init__(self, team, is_home, sim):
        self.team = team
        self.abbr = team.abbr
        self.is_home = is_home
        self.plan = team.gameplan()
        self.score = 0
        self.timeouts = 3
        self.sim = sim
        self.disc = team.discipline
        self.refresh_lineup()

    def refresh_lineup(self):
        t = self.team
        self.lu = {pos: t.lineup(pos, n) for pos, n in fit.GAME_DEPTH.items()}
        self._more = {}
        self.kr = t.returner("KR")
        self.pr = t.returner("PR")
        # The line: LT, LG, C, RG, RT - nobody twice (a player listed at tackle and guard
        # plays tackle, and the next guard on the list steps in)
        used = {p.id for p in self.lu["QB"][:1]}

        def take(pos, k):
            got = []
            for p in self.lu[pos] + self.more(pos):
                if len(got) >= k:
                    break
                if p.id not in used:
                    got.append(p)
                    used.add(p.id)
            return got
        ots = take("OT", 2)
        iol = take("IOL", 3)
        self.ol = ots[:1] + iol + ots[1:2]
        self.ol_slots = ["OT"] * len(ots[:1]) + ["IOL"] * len(iol) + ["OT"] * len(ots[1:2])
        # Package lists (third-down back, slot receivers, nickel backs...) and whether the user set them
        for slot in packages.PACKAGE_ORDER:
            self.lu[slot] = t.lineup(slot, packages.starters(slot) + 2)
        self.pk_set = {slot for slot in packages.PACKAGE_ORDER if t.depth_overrides.get(slot)}
        self.n_te = len(t.depth("TE"))
        self.last_pkg = getattr(self, "last_pkg", None)
        self._backfield()
        self.sim._prime(self)

    def more(self, pos):
        """A longer list for a slot, for when the same player is wanted in two places at once."""
        got = self._more.get(pos)
        if got is None:
            got = self.team.lineup(pos, fit.GAME_DEPTH.get(pos, 1) + 4)
            self._more[pos] = got
        return got

    def _backfield(self):
        """
        How this team splits the backfield today: the lead back's base share of
        snaps, plus situational specialists (a third-down back who catches and
        protects, a short-yardage hammer). Coach philosophy, the talent gap
        between backs, stamina and archetype all matter.
        """
        rbs = self.lu["RB"]
        self.rb1_streak = getattr(self, "rb1_streak", 0)
        if not rbs:
            self.bf = None
            return
        rb1 = rbs[0]
        rb2 = rbs[1] if len(rbs) > 1 else None
        c = self.plan.get("committee", 0.45)
        share = 1.04 - 0.30 * c
        if rb2 is not None:
            # the depth chart decides who leads; a better back behind him only means a closer split
            gap = rb1.rating_at("RB") - rb2.rating_at("RB")
            share += max(-0.05, min(0.16, gap / 65.0))
        share += (rb1.a("stamina") - 72) / 240.0
        share += {"Workhorse": 0.08, "Power Back": 0.02, "Elusive Back": -0.02,
                  "Receiving Back": -0.09}.get(rb1.archetype, 0.0)
        share = max(0.42, min(0.93, share))

        third = self._specialist("3DRB", rb1)
        goal = self._specialist("PWRB", rb1)
        self.bf = {"rb1": rb1, "rb2": rb2, "rb3": rbs[2] if len(rbs) > 2 else None,
                   "share": share, "third": third, "goal": goal, "committee": c}

    def _specialist(self, slot, rb1, margin=0.0):
        """
        The first man on a backfield package list, if he is not the lead back. The
        user's list is followed as set; a CPU staff uses him only when he is better
        in that role than the lead back.
        """
        lst = [p for p in self.lu.get(slot, []) if p is not rb1]
        if not lst:
            return None
        p = lst[0]
        if slot in self.pk_set:
            return None if self.lu[slot][0] is rb1 else p
        if p.rating_at(slot) < rb1.rating_at(slot) + margin:
            return None
        return p

    @property
    def qb(self):
        if len(self.lu["QB"]) > 1 and self.sim._garbage(self):
            return self.lu["QB"][1]          # mop-up duty in a blowout
        return self.lu["QB"][0]


# ── The simulation ────────────────────────────────────────────────────────────

class GameSim:
    def __init__(self, home, away, week=0, season=0, playoff=None,
                 neutral=False, keep_pbp=True, rules=None, diagrams=False,
                 user_abbr=None, scouting=None, iq=None):
        self.res = GameResult(home.abbr, away.abbr, week, season, playoff)
        self._adj = {}                  # pid -> {attr: change} at the slot he is playing (position_fit)
        self._adj_cache = {}            # (pid, slot) -> that dict
        self._fam = {}                  # (pid, slot) -> familiarity at kickoff
        self._slot_now = {}             # pid -> slot he lined up at on the latest snap
        self._bust = set()              # players who blew their assignment this snap
        self.home = Side(home, True, self)
        self.away = Side(away, False, self)
        # How sharp each staff is today: the user's own staff always works at the
        # realistic baseline; the league's CPU intelligence setting sharpens CPU staffs
        for side in (self.home, self.away):
            side.fx = gameday.effects(self._iq_for(side.abbr, user_abbr, iq))
        self.playoff = playoff
        self.neutral = neutral
        self.keep_pbp = keep_pbp

        self.rand_scale = settings["game_randomness"]
        self.to_rate = settings["turnover_rate"]
        self.sack_mult = settings["sack_rate"]
        self.big_play = settings["big_play_rate"]
        self.pen_rate = settings["penalty_rate"]
        self.fg_mult = settings["fg_accuracy"]
        self.inj_rate = settings["injury_rate"]
        self.go_mult = settings["fourth_down_aggression"]
        self.pat_dist = settings["pat_distance"]
        self.pass_shift = (settings["pass_tendency"] - 1.0) * 0.30
        self.pace = settings["pace"]
        self.comp_mult = settings["completion_rate"]
        self.run_mult = settings["run_efficiency"]
        self.rx = committee.effects(rules)
        self.diagrams = diagrams and keep_pbp
        self.cur_diag = None
        self.dcall = None
        self.st_def = None
        self._st_units = {}
        self.energy = {}                # pid -> 0..100
        self.wear = {}                  # pid -> fatigue that builds over the game
        self._rec = {}                  # pid -> sideline recovery per snap
        self._fat_slope = FAT_SLOPE * settings.get("fatigue_effect", 1.0)
        self._fat_rate = settings.get("fatigue_rate", 1.0)
        self.fat = {}                   # pid -> attribute penalty from fatigue
        self._rat = {}                  # (pid, pos) -> rating, cached for rotation decisions
        self.no_huddle = False
        self._motion_kind = None

        self.weather = wx.roll_weather(home.abbr, week, playoff, neutral) \
            if settings["weather"] else None
        self.res.weather = self.weather
        self.wx = wx.effects(self.weather)
        self.mom = 0.0                  # >0 favours the home side, range -1..1
        self.mom_scale = settings["momentum"]
        self.mom_sens = {}              # pid -> signed sensitivity to momentum
        self.mom_pts = 0.0

        # Weekly game plans: each staff studies the opponent's film (and its own)
        self.gstats = {home.abbr: Counter(), away.abbr: Counter()}
        self._spy_on = False
        self._ocall = None
        scouting = scouting or {}
        for side, opp in ((self.home, self.away), (self.away, self.home)):
            n = side.fx["film"]
            side.film_opp = gameday.film(scouting.get(opp.abbr) or [], opp.abbr, n)
            own = gameday.film(scouting.get(side.abbr) or [], side.abbr, n)
            side.self_read = gameday.read_offense(own, side.plan) if own["games"] else None
            side.dadj = {}
            side.oshift = 0.0
            side.blitz_adj = 0.0
        for side, opp in ((self.home, self.away), (self.away, self.home)):
            self._game_plan(side, opp)
            self._build_prefs(side)
        self.res.gameplans = {self.home.abbr: self.home.dgp, self.away.abbr: self.away.dgp}
        self.res.off_notes = {self.home.abbr: self.home.ogp["notes"], self.away.abbr: self.away.ogp["notes"]}
        self._spike_next = False
        for side, opp in ((self.home, self.away), (self.away, self.home)):
            u, v = side.team.unit_ratings(), opp.team.unit_ratings()
            side.conv_edge = _clip((u["OFF"] - v["DEF"]) / 250.0, -0.08, 0.08)

        self.form = {}
        self._build_form(self.home, home_edge=True)
        self._build_form(self.away, home_edge=False)
        # Pre-game strength edge in points (for the win-probability model)
        hfa_pts = 1.6 * settings["home_field_strength"] \
            if settings["home_field_advantage"] and not neutral else 0.0
        self.pre_edge = (home.overall - away.overall) * 0.68 + hfa_pts
        self.res.pre_edge = self.pre_edge

        self.quarter = 1
        self.clock = QUARTER
        self.poss = None
        self.dfn = None
        self.yl = 25
        self.down = 1
        self.togo = 10
        self.tmw = {2: False, 4: False}
        self.drive = None
        self.ot_possessions = set()
        self.game_over = False

    # ── Setup ────────────────────────────────────────────────────────────────

    @staticmethod
    def _iq_for(abbr, user_abbr, iq):
        if abbr == user_abbr:
            return gameday.DEFAULT_IQ
        if isinstance(iq, dict):
            iq = iq.get(abbr)
        if iq is None:
            iq = settings.get("cpu_intelligence", gameday.DEFAULT_IQ)
        return iq

    def _sharp(self, side, rating):
        return gameday.sharpen(rating, side.fx)

    def _game_plan(self, side, opp, defense=True, offense=True):
        """This staff's plan for the opponent: how to defend it and how to attack it."""
        fx = side.fx
        adapt = self._sharp(side, side.team.coach.r("adaptability"))
        if defense:
            dcall = self._sharp(side, staff_mod.def_calling(side.team))
            err = max(0.0, (20.0 - dcall) / 20.0) * 0.6 * fx["read"]
            rd = gameday.read_offense(side.film_opp, opp.plan, err)
            seen = dict(opp.plan)
            seen["pass_rate"] = rd["pass_rate"]
            side.dgp = dfn_lib.scout(side.team, opp.team, seen, calling=dcall, read_mult=fx["read"])
            side.dgp["read"] = rd
            side.dq = fx["plan"] * (dcall / 20.0) * (0.5 + adapt / 20.0)
        if offense:
            ocall = self._sharp(side, staff_mod.off_calling(side.team))
            side.ogp = gameday.offense_plan(side.team, opp.team, side.film_opp, ocall, adapt, fx, opp.plan)
            side.lr = 1.2 * (ocall / 20.0) * (0.5 + adapt / 40.0) * fx["learn"]
            side.dlr = 1.2 * (self._sharp(side, staff_mod.def_calling(side.team)) / 20.0) \
                * (0.5 + adapt / 40.0) * fx["learn"]

    def _build_prefs(self, side):
        """
        The call sheet weights for this series: the user's Featured / Removed plays, the
        weekly plan's featured concepts, and what has worked so far today.
        """
        prefs = dict(getattr(side.team, "play_prefs", None) or {})
        for name, m in side.ogp["concepts"].items():
            prefs[name] = prefs.get(name, 1.0) * m
        ts = self.res.team_stats[side.abbr]
        for name, m in gameday.learned(ts, "oc", side.ogp["concepts"], side.lr).items():
            prefs[name] = prefs.get(name, 1.0) * m
        for name, m in gameday.learned(ts, "oc", pb.RUN_CONCEPT_INFO, side.lr).items():
            prefs["run:" + name] = prefs.get("run:" + name, 1.0) * m
        for name, m in gameday.learned(ts, "dc", dfn_lib.COVERAGES, side.dlr, sign=-1.0).items():
            prefs["def:" + name] = prefs.get("def:" + name, 1.0) * m
        lp = gameday.learned(ts, "dc", ("Pressure (5+ rushers)", "Four-man rush"), side.dlr, sign=-1.0)
        if len(lp) == 2:
            side.blitz_adj = _clip(math.log(lp["Pressure (5+ rushers)"] / lp["Four-man rush"]) * 0.3, -0.08, 0.08)
        side.prefs = prefs

    def _build_form(self, side, home_edge):
        """
        Game-day form. Consistent players perform close to their attributes;
        inconsistent ones swing. Morale, coaching and home field shift
        everyone a little; big-game players rise in the playoffs.
        """
        team = side.team
        hfa = 0.0
        if settings["home_field_advantage"] and not self.neutral:
            hfa = 0.45 * settings["home_field_strength"] * (1 if home_edge else -0.4)
        morale = (team.team_morale - 60) / 40.0
        motivation = (team.coach.r("motivation") - 10) * 0.12
        # Leadership: the two strongest voices in the locker room lift everyone a little
        leaders = sorted((p.attrs.get("leadership", 40) for p in self._starter_list(side)), reverse=True)[:2]
        lead = (sum(leaders) / max(1, len(leaders)) - 70) / 30.0 * 0.6
        side.leadership = sum(leaders) / max(1, len(leaders))
        streak = _clip(settings["streakiness"], 0.0, 2.0)
        # Form carries over between games (hot and cold streaks): an AR(1)
        # process keeps the long-run spread the same while making good and bad
        # spells cluster together.
        rho = _clip(0.42 * streak, 0.0, 0.85)
        keep = math.sqrt(1.0 - rho * rho)
        rho_u = _clip(0.50 * streak, 0.0, 0.85)
        keep_u = math.sqrt(1.0 - rho_u * rho_u)
        prev_unit = getattr(team, "unit_form", None) or {}
        unit = {}
        for k in ("off", "def"):
            unit[k] = rho_u * prev_unit.get(k, 0.0) + keep_u * random.gauss(0, 1.55 * self.rand_scale)
        team.unit_form = unit
        sign = 1.0 if side.is_home else -1.0
        for p in team.roster:
            cons = p.hidden.get("consistency", 50)
            sd = (1.2 + (100 - cons) / 100.0 * 5.5) * self.rand_scale
            personal = rho * getattr(p, "form_carry", 0.0) + keep * random.gauss(0, sd)
            p.form_carry = personal
            p.form_z = personal / sd if sd > 0 else 0.0
            u = unit["off"] if p.position in OFF_POS else unit["def"] if p.position in DEF_POS else 0.0
            f = personal + u + hfa + morale + motivation + lead
            if self.playoff:
                f += (p.hidden.get("big_game", 50) - 50) / 50.0 * 2.5
            self.form[p.id] = f
            temper = p.hidden.get("temperament", 50)
            steady = (getattr(side, "leadership", 70) - 70) / 100.0
            self.mom_sens[p.id] = sign * (1.35 - temper / 100.0 * 0.8) * (1.0 - steady * 0.6)
        self.res.starters.update(pl.id for pl in self._starter_list(side))

    def _starter_list(self, side):
        lu = side.lu
        out = lu["QB"][:1] + lu["RB"][:1] + lu["WR"][:3] + lu["TE"][:1] + side.ol
        out += lu["DT"][:2] + lu["EDGE"][:2] + lu["LB"][:2] + lu["CB"][:3] + lu["S"][:2]
        out += lu["K"][:1] + lu["P"][:1]
        return out

    def e(self, p, attr):
        """Effective attribute for this game (talent + form + momentum - fatigue +/- slot fit)."""
        v = p.attrs.get(attr, 30) + self.form.get(p.id, 0.0) + \
            self.mom_sens.get(p.id, 0.0) * self.mom_pts
        pen = self.fat.get(p.id)
        if pen:
            v -= pen if attr in PHYSICAL else pen * 0.3
        adj = self._adj.get(p.id)
        if adj:
            v += adj.get(attr, 0.0)
        return v

    # ── Playing out of position (position_fit.py) ────────────────────────────

    def _at(self, p, slot):
        """He lines up at `slot` this snap: his size fit and familiarity there apply."""
        if p is None:
            return
        self._slot_now[p.id] = slot
        if slot == p.position and not p.converted_from:
            if p.id in self._adj:
                del self._adj[p.id]
            return
        key = (p.id, slot)
        adj = self._adj_cache.get(key)
        if adj is None:
            adj = fit.slot_deltas(p, slot)
            self._adj_cache[key] = adj
            self._fam[key] = fit.familiarity(p, slot)
        self._adj[p.id] = adj

    def _prime(self, side):
        """Kickers, punters and the starting quarterback play only their own slot."""
        lu = side.lu
        for slot in ("K", "P", "QB"):
            if lu.get(slot):
                self._at(lu[slot][0], slot)

    def _kicker(self, side):
        k = side.lu["K"][0]
        self._at(k, "K")
        return k

    def _punter(self, side):
        p = side.lu["P"][0]
        self._at(p, "P")
        return p

    def _pos(self, p):
        """The slot a player is playing right now (his own position if we don't know)."""
        return self._slot_now.get(p.id, p.position)

    def _flag_odds(self, side, unit):
        """(rate multiplier, unfamiliar players) for a unit's penalty chances this snap."""
        unf = getattr(side, "unf_off" if unit == "off" else "unf_def", None)
        if not unf:
            return 1.0, ()
        return 1.0 + fit.PENALTY_RATE * sum(u for _, u in unf), unf

    @staticmethod
    def _culprit(unf, mult, default):
        """Who drew the flag: an unfamiliar player in proportion to the extra risk he adds."""
        if unf and random.random() < 1.0 - 1.0 / mult:
            return random.choices([p for p, _ in unf], weights=[u for _, u in unf], k=1)[0]
        return default

    # ── Fatigue & rotation ───────────────────────────────────────────────────

    def energy_of(self, p):
        return self.energy.get(p.id, 100.0)

    def _set_energy(self, p, v):
        self._set_en(p.id, v)

    def _set_en(self, pid, v):
        v = 0.0 if v < 0.0 else 100.0 if v > 100.0 else v
        self.energy[pid] = v
        if v < FAT_START:
            self.fat[pid] = (FAT_START - v) * self._fat_slope
        else:
            self.fat.pop(pid, None)

    def _garbage(self, side):
        """Blowout late in the game: starters come out."""
        if self.quarter < 4 or self.clock > 420 or self.quarter > 4:
            return False
        return abs(side.score - self.other(side).score) >= 24

    def _rating(self, p, pos):
        key = (p.id, pos)
        r = self._rat.get(key)
        if r is None:
            r = p.rating_at(pos)
            self._rat[key] = r
        return r

    def _rotate(self, side, pos, n, lock=False, used=None):
        """
        The n players a position group puts on the field this snap (starters first).
        The depth chart's order wins: a player is never benched for a better player
        listed behind him, only rested when he is tired (each player counts as good
        as the best man listed below him). `used`: players already on the field at
        another slot this snap, who are skipped.
        """
        pool = side.lu.get(pos, [])
        rot_pos = packages.base_of(pos)
        if used:
            free = [p for p in pool if p.id not in used]
            if len(free) < len(pool) and len(free) < n + 1:
                # someone on this list is already on the field elsewhere: read further down it
                free += [p for p in side.more(pos) if p.id not in used and p not in free]
            pool = free
        out = list(pool[:n])
        if len(pool) > n:
            bench = list(pool[n:n + 3])
            if self._garbage(side):
                # mop-up time: the backups play
                if pos != "QB":
                    out = (bench + out)[:n]
            elif not lock:
                style = (getattr(side.team, "rotation", None) or {}).get(ROT_GROUP.get(rot_pos, ""), "normal")
                k = POS_ROTATION.get(rot_pos, 0.8) * ROTATION_STYLE.get(style, 1.0)
                if k > 0:
                    cand = out + bench
                    env = [self._rating(p, pos) for p in cand]
                    for i in range(len(env) - 2, -1, -1):
                        if env[i + 1] > env[i]:
                            env[i] = env[i + 1]
                    val = {}
                    for i, p in enumerate(cand):
                        en = self.energy_of(p)
                        val[p.id] = env[i] * (1.0 - k * max(0.0, 94.0 - en) / 100.0 * 1.15)
                    for i, s_ in enumerate(out):
                        if not bench:
                            break
                        b = max(bench, key=lambda x: val[x.id])
                        if val[b.id] > val[s_.id] * 1.03:
                            out[i] = b
                            bench.remove(b)
                            bench.append(s_)
        if used is not None:
            used.update(p.id for p in out)
        return out

    def _snap_units(self, off_players, def_players, off_slots=None, def_slots=None):
        """
        Everyone on the field takes a snap: snap counts, energy drain (by the slot he
        is playing), sideline recovery, and for anyone away from his own position his
        size fit and familiarity there - and the chance he blows his assignment.
        """
        heat = 1.0
        if self.weather:
            t = self.weather.get("temp", 60)
            heat = 1.22 if t >= 88 else 1.1 if t >= 80 else 0.95 if t <= 35 else 1.0
        rate = self._fat_rate
        huddle = HUDDLE_REC * (0.35 if self.no_huddle else 1.0)
        on = set()
        ps = self.res.player_stats
        bust = self._bust
        bust.clear()
        unf_off, unf_def = [], []
        if self.poss is not None:
            self.poss.unf_off = unf_off
            self.dfn.unf_def = unf_def
        for players, key, slots, unf in ((off_players, "off_snaps", off_slots, unf_off),
                                         (def_players, "def_snaps", def_slots, unf_def)):
            for i, p in enumerate(players):
                if p is None or p.id in on:
                    continue
                on.add(p.id)
                slot = slots[i] if slots is not None and i < len(slots) else p.position
                self._at(p, slot)
                if slot != p.position or p.converted_from:
                    ss = self.res.slot_snaps.setdefault(p.id, {})
                    ss[slot] = ss.get(slot, 0) + 1
                    f = self._fam.get((p.id, slot), 100.0)
                    if f < 100.0:
                        unf.append((p, (100.0 - f) / 100.0))
                        if random.random() < fit.BUST_RATE * ((100.0 - f) / 100.0) ** 1.2:
                            bust.add(p.id)
                            self.st(p, "busts")
                line = ps.get(p.id)
                if line is None:
                    self.st(p, key)
                else:
                    line[key] += 1
                stam = p.attrs.get("stamina", 60)
                cost = DRAIN.get(slot, 1.0) * (1.55 - stam / 100.0) * heat * rate
                self.wear[p.id] = self.wear.get(p.id, 0.0) + cost * WEAR_FRAC
                if p.id not in self._rec:
                    self._rec[p.id] = SIDELINE_REC * (0.7 + p.a("stamina") / 250.0)
                self._set_en(p.id, min(100.0 - self.wear[p.id], self.energy_of(p) - cost + huddle))
        wear = self.wear
        for pid, en in list(self.energy.items()):
            if pid in on:
                continue
            cap = 100.0 - wear.get(pid, 0.0)
            if en < cap:
                self._set_en(pid, min(cap, en + self._rec.get(pid, SIDELINE_REC)))
        self._on_field = on

    def _adjustments(self, halftime):
        """Coordinators adjust to what is working (halftime adjustments are the big ones)."""
        for side in (self.home, self.away):
            opp = self.other(side)
            calling = self._sharp(side, staff_mod.def_calling(side.team))
            if not halftime:
                calling *= 0.5
            side.dadj, note = dfn_lib.adjust(side.dadj, self.gstats[opp.abbr], calling,
                                             self._sharp(side, side.team.coach.r("adaptability")))
            # Update the read of their tendencies with what they have shown today
            today = self.res.team_stats[opp.abbr]
            seen = Counter((side.film_opp or {}).get("own", {}))
            w = 1.0 + side.fx["learn"]
            for k, v in today.items():
                if k.startswith("sit|"):
                    seen[k] += v * w
            err = max(0.0, (20.0 - calling) / 20.0) * 0.3 * side.fx["read"]
            side.dgp["read"] = gameday.read_offense({"own": seen}, opp.plan, err)
            if note and halftime:
                self.log(f"Halftime adjustment: the {side.team.name} "
                         f"defense {note}", "note")
            # Offence: lean toward what's working
            g = self.gstats[side.abbr]
            if g["run_n"] >= 6 and g["pass_n"] >= 8:
                gap = g["pass_epa"] / g["pass_n"] - g["run_epa"] / g["run_n"]
                q = self._sharp(side, staff_mod.off_calling(side.team)) / 20.0 * (1.0 if halftime else 0.5)
                side.oshift = _clip(side.oshift + _clip(gap, -0.3, 0.3) * 0.15 * q, -0.08, 0.08)

    def _exert(self, p, yards=0):
        """Extra cost for the ball carrier or a receiver who ran after the catch."""
        if p is not None:
            self._set_energy(p, self.energy_of(p) - 0.6 - max(0, yards) * 0.05)

    def _rest_all(self, amount):
        for pid in list(self.energy):
            self._set_en(pid, min(100.0 - self.wear.get(pid, 0.0), self.energy[pid] + amount))

    # ── Momentum & win probability ───────────────────────────────────────────

    def swing(self, side, amount):
        """Shift momentum toward `side`. Big swings fade over a dozen snaps."""
        if self.mom_scale <= 0 or side is None:
            return
        sign = 1.0 if side is self.home else -1.0
        crowd = 1.15 if (side.is_home and settings["home_field_advantage"] and not self.neutral) else 1.0
        # Diminishing returns when you already own the momentum
        delta = sign * amount * crowd * (1.0 - 0.5 * max(0.0, sign * self.mom))
        self.mom = _clip(self.mom + delta, -1.0, 1.0)
        self.mom_pts = self.mom * 1.6 * self.mom_scale

    def elapsed(self):
        if self.quarter > 4:
            return 3600.0
        return (self.quarter - 1) * QUARTER + (QUARTER - max(0, self.clock))

    def win_prob_home(self):
        if self.game_over or (self.quarter >= 4 and self.clock <= 0):
            d = self.home.score - self.away.score
            return 1.0 if d > 0 else 0.0 if d < 0 else 0.5
        rem = max(1.0, 3600.0 - self.elapsed()) if self.quarter <= 4 else 420.0
        diff = self.home.score - self.away.score
        if self.poss is not None:
            ep = -0.6 + 0.068 * self.yl
            diff += ep if self.poss is self.home else -ep
        sd = 13.4 * math.sqrt(rem / 3600.0) + 0.6
        return _clip(_phi((diff + self.pre_edge * rem / 3600.0) / sd), 0.001, 0.999)

    # ── Bookkeeping ──────────────────────────────────────────────────────────

    def st(self, p, key, val=1):
        if p is None:
            return
        line = self.res.player_stats.get(p.id)
        if line is None:
            line = Counter()
            self.res.player_stats[p.id] = line
            self.res.player_meta[p.id] = (p.name, p.position, p.team, p.jersey)
        if key.endswith("_long"):
            if val > line[key]:
                line[key] = val
        else:
            line[key] += val

    def ts(self, side, key, val=1):
        self.res.team_stats[side.abbr][key] += val

    def spot(self, yl=None, side=None):
        yl = self.yl if yl is None else yl
        side = side or self.poss
        other = self.dfn if side is self.poss else self.poss
        if yl == 50:
            return "midfield"
        if yl < 50:
            return f"{side.abbr} {yl}"
        return f"{other.abbr} {100 - yl}"

    def clock_str(self, clock=None):
        c = max(0, int(self.clock if clock is None else clock))
        return f"{c // 60}:{c % 60:02d}"

    def log(self, text, kind="play"):
        if not self.keep_pbp:
            return
        d = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}.get(self.down, "")
        if kind in ("play",):
            togo = "Goal" if self.yl + self.togo >= 100 else str(self.togo)
            sit = f"{d} & {togo} at {self.spot()}"
        else:
            sit = ""
        q = f"Q{self.quarter}" if self.quarter <= 4 else "OT"
        self.res.plays.append((q, self.clock_str(), self.poss.abbr if self.poss else "",
                               sit, text, kind))
        self.res.states.append((self.yl, self.down, self.togo, self.home.score, self.away.score,
                                int(self.win_prob_home() * 1000), int(self.mom * 100),
                                self.poss is self.home))
        diag = None
        if self.diagrams and kind == "play" and self.cur_diag is not None:
            diag = self.cur_diag
            diag["los"] = self.yl
            diag["home"] = self.poss is self.home
            self.cur_diag = None
        self.res.diagrams.append(diag)

    def add_score(self, side, pts, text):
        side.score += pts
        if side is self.home:
            self.res.home_score = side.score
        else:
            self.res.away_score = side.score
        qi = min(self.quarter, 5) - 1
        q = self.res.quarters[side.abbr]
        while len(q) <= qi:
            q.append(0)
        q[qi] += pts
        qn = f"Q{self.quarter}" if self.quarter <= 4 else "OT"
        self.res.scoring.append((qn, self.clock_str(), side.abbr, text,
                                 self.home.score, self.away.score))
        self.swing(side, {6: 0.30, 3: 0.08, 2: 0.22}.get(pts, 0.0))
        self.log(f"{text}  [{self.away.abbr} {self.away.score} - "
                 f"{self.home.abbr} {self.home.score}]", "score")

    def other(self, side):
        return self.away if side is self.home else self.home

    # ── Clock ────────────────────────────────────────────────────────────────

    def urgency(self, side):
        """'hurry', 'milk' or 'normal' for the offence."""
        diff = side.score - self.other(side).score
        if self.quarter == 2 and self.clock <= 120:
            return "hurry"
        if self.quarter >= 4:
            if diff < 0 and (self.clock <= 300 or diff < -8 and self.clock <= 480):
                return "hurry"
            if diff == 0 and (self.clock <= 120 or (self.quarter >= 5 and self.clock <= 300)):
                return "hurry"
            if diff > 0 and self.clock <= 420:
                return "milk"
        return "normal"

    def run_clock(self, play_time, clock_runs, oob=False):
        start = self.clock
        mode = self.urgency(self.poss)
        elapsed = play_time
        if clock_runs:
            if oob and not ((self.quarter == 2 and self.clock <= 120) or
                            (self.quarter >= 4 and self.clock <= 300)):
                clock_runs_after = True
                between = random.uniform(14, 22)
            elif oob:
                clock_runs_after = False
                between = 0
            else:
                clock_runs_after = True
                tempo = self.poss.plan["tempo"]
                if mode == "hurry":
                    # sloppy game managers lose seconds getting lined up
                    between = random.uniform(11, 17) + random.random() * (20 - self._gm(self.poss)) * 0.35
                elif mode == "milk":
                    between = random.uniform(37, 40)
                else:
                    between = random.gauss(38.0 - 9.0 * (tempo - 0.5), 2.0) / self.pace
            if clock_runs_after and between > 0:
                # Timeouts to stop the clock
                k = self._kicker(self.poss)
                fg_ok = 100 - self.yl + 17 <= self.fg_range(k)
                diff = self.poss.score - self.dfn.score
                after = self.clock - elapsed
                if self.quarter in (2, 4, 5) and sit_lib.offense_timeout(
                        after, self.yl, diff, self.poss.timeouts, mode, fg_ok, self._gm(self.poss)):
                    self.poss.timeouts -= 1
                    self._rest_all(2.5)
                    self.log(f"Timeout {self.poss.abbr}", "note")
                    between = 0
                elif self._defense_wants_timeout():
                    self.dfn.timeouts -= 1
                    self._rest_all(2.5)
                    self.log(f"Timeout {self.dfn.abbr}", "note")
                    between = 0
                elif self.quarter in (2, 4, 5) and sit_lib.spike(after, self.poss.timeouts, mode, self.down,
                                                                 self._gm(self.poss)):
                    between = 3
                    self._spike_next = True
            elapsed += between
        self.clock -= elapsed
        # Two-minute warning
        if self.quarter in (2, 4) and not self.tmw[self.quarter] \
                and start > 120 >= self.clock:
            self.tmw[self.quarter] = True
            if self.clock < 120 - play_time:
                self.clock = 120
            self.log("Two-minute warning", "note")
        self.ts(self.poss, "top", min(elapsed, start))

    def _defense_wants_timeout(self):
        if self.dfn.timeouts <= 0 or self.quarter < 2 or self.quarter == 3:
            return False
        diff = self.dfn.score - self.poss.score
        mode = self.urgency(self.poss)
        return sit_lib.defense_timeout(self.clock, diff, self.dfn.timeouts, mode, self.quarter,
                                       self._gm(self.dfn))

    # ── Main loop ────────────────────────────────────────────────────────────

    def play(self):
        first_receiver = random.choice([self.home, self.away])
        second_half_receiver = self.other(first_receiver)
        self.kickoff(self.other(first_receiver))
        while not self.game_over:
            if self.clock <= 0:
                if not self._end_quarter(second_half_receiver):
                    break
                continue
            self.snap()
        self._finish()
        return self.res

    def _end_quarter(self, second_half_receiver):
        if self.quarter in (1, 3):
            self._adjustments(halftime=False)
            self.quarter += 1
            self.clock = QUARTER
            self._rest_all(4.0)
            self.log(f"End of quarter {self.quarter - 1}", "note")
            return True
        if self.quarter == 2:
            self._adjustments(halftime=True)
            for pid in self.wear:
                self.wear[pid] *= 0.45
            self._rest_all(45.0)
            self._end_drive("End of half")
            self.quarter = 3
            self.clock = QUARTER
            self.home.timeouts = self.away.timeouts = 3
            self.log("Halftime", "note")
            self.kickoff(self.other(second_half_receiver))
            return True
        # End of regulation / overtime period
        if self.home.score != self.away.score:
            self._end_drive("End of game")
            return False
        rules = settings["overtime_rules"]
        if self.quarter >= 5 and not self.playoff:
            self._end_drive("End of game")
            return False          # regular season tie
        if self.quarter >= 9:
            self._end_drive("End of game")
            return False
        self._end_drive("End of regulation" if self.quarter == 4 else "End of period")
        self.quarter += 1
        self.res.overtime = True
        self.clock = 600 if (not self.playoff and rules == "modern") else QUARTER
        self.home.timeouts = self.away.timeouts = 2
        self.ot_possessions = set()
        self.log("Overtime", "note")
        self.kickoff(random.choice([self.home, self.away]))
        return True

    def _ot_check(self):
        """Apply sudden-death rules after any score in overtime."""
        if self.quarter < 5:
            return
        rules = settings["overtime_rules"]
        if rules == "full period":
            return
        if self.home.score == self.away.score:
            return
        if rules == "sudden death":
            self.game_over = True
            return
        # Modern: both teams get a possession, then sudden death
        if len(self.ot_possessions) >= 2:
            self.game_over = True

    # ── Drives ───────────────────────────────────────────────────────────────

    def _start_drive(self, side, yl):
        self.poss = side
        self.dfn = self.other(side)
        self.yl = yl
        self.down = 1
        self.togo = 10
        if self.quarter >= 5:
            if settings["overtime_rules"] == "modern" and len(self.ot_possessions) >= 2 \
                    and self.home.score != self.away.score:
                self.game_over = True
            self.ot_possessions.add(side.abbr)
        side.rb1_streak = 0
        self._build_prefs(side)
        self._build_prefs(self.dfn)
        self.drive = {"team": side.abbr, "start": yl, "plays": 0, "yards": 0,
                      "clock": self.clock, "quarter": self.quarter, "result": "",
                      "rz": False}
        self.ts(side, "drives")

    def _end_drive(self, result):
        d = self.drive
        if not d or d.get("result"):
            return
        d["result"] = result
        d["end"] = self.yl
        side = self.home if d["team"] == self.home.abbr else self.away
        self.res.drives[side.abbr].append(d)

    def turnover_on_spot(self, result, new_yl=None):
        self._end_drive(result)
        old = self.poss
        yl = 100 - self.yl if new_yl is None else new_yl
        self._start_drive(self.other(old), _clip(yl, 1, 99))

    # ── Kicks ────────────────────────────────────────────────────────────────

    # ── Special teams units ──────────────────────────────────────────────────

    def _st_unit(self, side):
        """Core special-teams players: the backups at linebacker, safety, corner, tight end and back."""
        v = self._st_units.get(side.abbr)
        if v is None:
            lu = side.lu
            core = lu["LB"][2:5] + lu["S"][2:4] + lu["CB"][3:5] + lu["TE"][1:3] + lu["RB"][1:3] + lu["WR"][4:6]
            core = core or (lu["LB"] + lu["S"])
            v = sum(p.a("speed") * 0.30 + p.a("tackling") * 0.20 + p.a("pursuit") * 0.15
                    + p.a("strength") * 0.15 + p.a("awareness") * 0.20 for p in core) / max(1, len(core))
            v += (staff_mod.st_calling(side.team) - 10) * 0.4
            self._st_units[side.abbr] = v
        return v

    def _st_edge(self, ret_side, cover_side):
        """Positive when the return unit is better than the coverage unit (about -2..+2)."""
        return _clip((self._st_unit(ret_side) - self._st_unit(cover_side)) / 6.0, -2.5, 2.5)

    def _st_cover_tackle(self, side):
        lu = side.lu
        pool = lu["LB"][2:5] + lu["S"][2:4] + lu["CB"][3:5] + lu["TE"][1:2] or lu["LB"]
        if pool:
            self.st(random.choice(pool), "st_tkl")

    def _st_def_call(self, kind):
        de, off = self.dfn, self.poss
        prefs = getattr(de.team, "play_prefs", None)
        if kind == "punt":
            sit = {"togo": self.togo, "to_goal": 100 - self.yl, "fake_threat": off.plan.get("trick", 0.4),
                   "returner": de.pr.return_rating if de.pr is not None else 75}
            return st_lib.choose_punt_return(sit, prefs)
        diff = de.score - off.score
        sit = {"togo": self.togo, "must_stop": self.quarter >= 4 and self.clock < 120 and -3 <= diff <= 2}
        return st_lib.choose_fg_defense(sit, prefs)

    def kickoff(self, kicking, onside=False, from_yl=35, free=False):
        """A kickoff, or (free=True) the free kick after a safety from the kicking team's 20."""
        recv = self.other(kicking)
        self.poss, self.dfn = kicking, recv
        k = self._kicker(kicking)
        needed = onside or (self.quarter == 4 and recv.score > kicking.score and
                            sit_lib.should_onside(recv.score - kicking.score, self.clock, kicking.timeouts))
        ret = recv.kr
        dyn = self.rx.get("dynamic_kickoff", False) and not free
        tb_spot = self.rx["touchback"]
        if free and not needed:
            kind = "Safety Punt"
            k = self._punter(kicking)
        else:
            kind = st_lib.choose_kickoff({"onside_needed": needed,
                                          "late_half": self.quarter in (2, 4) and self.clock <= 25,
                                          "aggression": kicking.team.coach.tendencies.get("aggression", 0.45),
                                          "lead": kicking.score - recv.score,
                                          "returner": ret.return_rating if ret is not None else 75,
                                          "dynamic": dyn, "tb_spot": tb_spot},
                                         getattr(kicking.team, "play_prefs", None))
            self.st(k, "ko")
            self.ts(kicking, "kickoffs")
        if kind in ("Onside Kick", "Surprise Onside"):
            hands = sum(self.e(p, "catching") * 0.5 + self.e(p, "awareness") * 0.5
                        for p in (recv.lu["WR"][:3] + recv.lu["TE"][:1] + recv.lu["RB"][:1])) / 5.0
            rec_chance = (0.08 if dyn else 0.10) if kind == "Onside Kick" else 0.48
            rec_chance += (self.e(k, "kick_accuracy") - 75) / 600.0 - (hands - 70) / 700.0
            what = "onside kick" if kind == "Onside Kick" else "SURPRISE onside kick"
            if random.random() < _clip(rec_chance, 0.03, 0.65):
                self.log(f"{_short(k.name)} {what} RECOVERED by {kicking.abbr}!", "note")
                self.swing(kicking, 0.25)
                self._start_drive(kicking, from_yl + 11)
                return
            self.log(f"{_short(k.name)} {what} recovered by {recv.abbr}", "note")
            self._start_drive(recv, 100 - (from_yl + 10))
            return
        power = self.e(k, "kick_power") + self.wx["kick_power"]
        acc = self.e(k, "kick_accuracy")
        fair_ok = False
        if kind == "Safety Punt":
            dist = random.gauss(45 + (self.e(k, "punt_power") - 70) * 0.15, 5)
            tb_p, fair_ok = 0.0, True
        elif dyn:
            # Dynamic kickoff: the kick has to land between the goal line and the 20
            if kind == "Deep Kickoff":
                short = random.random() < _clip((75 - power) / 60.0, 0.02, 0.35)
                land_at = random.uniform(0, 6) if short else -5      # receiving yard line where it lands
            elif kind == "Squib Kick":
                land_at = random.gauss(15, 4)
            else:
                land_at = random.gauss(7 - (acc - 70) * 0.03, _clip(5.5 - (acc - 60) / 20.0, 2.5, 7.0))
            if land_at < 0:
                self.st(k, "ko_tb")
                self.log(f"{_short(k.name)} kicks it into the end zone. Touchback to the {tb_spot}.", "note")
                self._start_drive(recv, tb_spot)
                self._ko_drive(recv, tb_spot)
                return
            if land_at > 20:
                self.ts(kicking, "ko_short")
                self.log(f"{_short(k.name)} kick lands short of the landing zone: ball at the {recv.abbr} 40.",
                         "note")
                self._start_drive(recv, 40)
                self._ko_drive(recv, 40)
                return
            if land_at < 3 and random.random() < 0.25:
                # it bounced into the end zone and the returner downed it
                self.log(f"{_short(k.name)} kicks off, downed in the end zone. Ball at the 20.", "note")
                self._start_drive(recv, 20)
                self._ko_drive(recv, 20)
                return
            dist = 100 - from_yl - land_at
            tb_p = 0.0
        else:
            dist = random.gauss(57 + (power - 70) * 0.35, 4.5)
            # a big leg puts it through the end zone; with the touchback out at the 30 kickers
            # hang it short of the goal line to force a return instead
            tb_p = _clip((power - 50) / 35.0, 0.05, 0.90) * (0.55 if tb_spot >= 30 else 1.0)
            if kind == "Directional Kickoff":
                dist -= 1.5
                tb_p *= 0.65
                if random.random() < 0.015 + max(0, 75 - acc) / 600.0:
                    self.log(f"{_short(k.name)} directional kick goes OUT OF BOUNDS.", "note")
                    self.ts(kicking, "ko_oob")
                    self._start_drive(recv, 40)
                    self._ko_drive(recv, 40)
                    return
            elif kind == "Squib Kick":
                dist, tb_p = random.gauss(41, 5), 0.0
            elif kind == "Pooch Kick":
                dist, tb_p = random.gauss(52, 3.5), 0.0
        land = from_yl + dist          # yards from kicking team's goal
        if not dyn and (land >= 100 + random.uniform(0, 3) or random.random() < tb_p):
            self.st(k, "ko_tb")
            self.log(f"{_short(k.name)} kicks off. Touchback.", "note")
            self._start_drive(recv, tb_spot)
            self._ko_drive(recv, tb_spot)
            return
        catch_at = max(-4, int(100 - land))          # receiving team yard line
        if (kind == "Pooch Kick" and random.random() < 0.55) or (fair_ok and random.random() < 0.30):
            spot = tb_spot if kind == "Pooch Kick" else max(1, catch_at)
            self.log(f"{_short(k.name)} {'pooch kick' if kind == 'Pooch Kick' else 'free kick'}, fair catch by "
                     f"{_short(ret.name)}.", "note")
            self._start_drive(recv, spot)
            self._ko_drive(recv, spot)
            if fair_ok:
                self._fair_catch_kick(recv, spot)
            return
        scheme = st_lib.choose_kick_return(getattr(recv.team, "play_prefs", None))
        mean_adj, sd, big = {"Middle Return": (0.0, 6.0, 1.0), "Sideline Wall": (-0.5, 6.5, 1.3),
                             "Wedge Return": (1.0, 5.0, 0.7), "Kickoff Reverse": (-2.5, 9.0, 2.4),
                             "Return to the Field": (-0.5, 6.0, 1.1), "Throwback": (-3.0, 10.0, 2.6)}[scheme]
        if kind == "Directional Kickoff":
            mean_adj -= 2.5
            if scheme == "Return to the Field":
                mean_adj += 3.0                 # the blockers were already set up away from the boundary
        elif kind == "Squib Kick":
            mean_adj -= 10.0 if not dyn else 6.0
            big *= 0.4
        elif kind == "Pooch Kick":
            mean_adj -= 6.0
        elif kind == "Safety Punt":
            mean_adj -= 10.5                   # a punt's hang time lets the coverage get down the field
        edge = self._st_edge(recv, kicking)
        rr = ret.return_rating + self.form.get(ret.id, 0)
        if dyn:
            # nobody moves until the ball lands: more like a scrimmage play than a footrace
            gain = max(0, int(random.gauss(23.5 + (rr - 75) * 0.28 + mean_adj + edge * 1.4, sd + 0.5)))
        else:
            gain = max(0, int(random.gauss(21 + (rr - 75) * 0.25 + mean_adj + edge * 1.2, sd)))
        if random.random() < (0.0048 + max(0, rr - 78) * 0.0005) * self.big_play * big * (1 + 0.15 * edge) \
                * (0.6 if dyn else 1.0):
            gain = 100 - catch_at
        yl = catch_at + gain
        self.st(ret, "kr")
        if not free:
            self.ts(kicking, "ko_returned")
        if yl >= 100:
            self.st(ret, "kr_yds", 100 - catch_at)
            self.st(ret, "kr_td")
            self.st(ret, "kr_long", 100 - catch_at)
            self._start_drive(recv, 99)
            self.add_score(recv, 6, f"{_short(ret.name)} {100 - catch_at}-yard kickoff return TOUCHDOWN")
            self._after_td(recv)
            return
        yl = max(1, yl)
        self.st(ret, "kr_yds", yl - catch_at)
        self.st(ret, "kr_long", yl - catch_at)
        self._st_cover_tackle(kicking)
        fum = 0.006 * (2.0 if scheme == "Kickoff Reverse" else 2.5 if scheme == "Throwback" else 1.0) \
            * (1.6 if kind == "Squib Kick" else 1.0)
        if random.random() < fum * self.to_rate:
            self.st(ret, "fumbles")
            self.st(ret, "fumbles_lost")
            self.log(f"{_short(ret.name)} FUMBLES the kickoff return — {kicking.abbr} recovers!", "note")
            self._start_drive(kicking, 100 - yl)
            return
        how = {"Squib Kick": "squib kicks", "Directional Kickoff": "kicks toward the sideline",
               "Pooch Kick": "pooch kicks", "Safety Punt": "free kicks after the safety",
               "Landing Zone Kick": "kicks into the landing zone"}.get(kind, "kicks off")
        extra = {"Kickoff Reverse": " on a reverse", "Sideline Wall": " behind a sideline wall",
                 "Throwback": " on a throwback lateral", "Return to the Field": " to the wide side"}.get(scheme, "") \
            if gain >= 30 else ""
        self.log(f"{_short(k.name)} {how}. {_short(ret.name)} returns{extra} to the "
                 f"{recv.abbr} {yl}.", "note")
        self._start_drive(recv, yl)
        self._ko_drive(recv, yl)

    def _ko_drive(self, recv, yl):
        """Starting field position after a kick (league averages tell the committee how kickoffs are going)."""
        self.ts(recv, "ko_start", yl)
        self.ts(recv, "ko_drives")

    def _fair_catch_kick(self, side, yl):
        """After a fair catch at the end of a half, the receiving team may take a free-kick field goal."""
        if self.quarter not in (2, 4) or self.clock > 6 or self.game_over:
            return False
        diff = side.score - self.other(side).score
        if self.quarter == 4 and not -3 <= diff <= 0:
            return False
        k = self._kicker(side)
        dist = 100 - yl + 10                     # kicked from the spot: no snap, no hold
        if dist > self.fg_range(k) + 4:
            return False
        self.st(k, "fga")
        self.ts(side, "fga")
        if random.random() < _clip(self.fg_probability(k, dist) + 0.04, 0.0, 0.97):
            self.st(k, "fgm")
            self.st(k, "fg_long", dist)
            self.ts(side, "fgm")
            self._end_drive("Field goal")
            self.add_score(side, 3, f"{_short(k.name)} {dist}-yard FAIR CATCH KICK is GOOD")
            self.run_clock(5, False)
            self._ot_check()
            if not self.game_over:
                self.kickoff(side)
        else:
            self.log(f"{_short(k.name)} {dist}-yard fair catch kick is NO GOOD", "play")
            self.run_clock(5, False)
            self.turnover_on_spot("Missed FG", max(20, 100 - yl))
        return True

    def punt(self):
        p = self._punter(self.poss)
        ret = self.dfn.pr
        rcall = self.st_def or self._st_def_call("punt")
        self.st_def = None
        to_goal = 100 - self.yl
        kind = st_lib.choose_punt({"to_goal": to_goal, "wind": (self.weather or {}).get("wind", 0),
                                   "accuracy": self.e(p, "punt_accuracy")},
                                  getattr(self.poss.team, "play_prefs", None))
        self.ts(self.poss, "punts")
        block_p = {"Punt Block": 0.022, "Punt Safe": 0.002, "Hold-Up Return": 0.0015}.get(rcall, 0.004)
        if kind == "Rugby Punt":
            block_p *= 0.5
        if random.random() < block_p * (1 + 0.2 * self._st_edge(self.dfn, self.poss)):
            self.st(p, "punts")
            self.ts(self.dfn, "punt_blocks")
            self.log(f"{_short(p.name)} punt is BLOCKED!", "play")
            self.turnover_on_spot("Blocked punt", 100 - max(1, self.yl - 8))
            return
        if rcall == "Punt Block" and random.random() < 0.018:
            # Roughing / running into the kicker: the punting team keeps the ball
            rough = random.random() < 0.4
            yds = 15 if rough else 5
            self.ts(self.dfn, "penalties")
            self.ts(self.dfn, "pen_yds", yds)
            self.log(f"PENALTY on {self.dfn.abbr}: {'roughing' if rough else 'running into'} the kicker, "
                     f"{yds} yards" + (", automatic first down" if rough or yds >= self.togo else ""), "play")
            self.yl = min(99, self.yl + yds)
            if rough or yds >= self.togo:
                self.down, self.togo = 1, min(10, 100 - self.yl)
            else:
                self.togo -= yds
            return
        if self.drive is not None and self.drive["plays"] <= 3:
            self.swing(self.dfn, 0.08)
        power = self.e(p, "punt_power")
        acc = self.e(p, "punt_accuracy")
        gross = int(round(random.gauss(41.0 + power * 0.125 + self.wx["punt"], 5.5)))
        if kind == "Directional Punt":
            gross -= 3
        elif kind == "Rugby Punt":
            gross += int(random.gauss(-4, 3))
        elif kind == "Pooch Punt":
            # aim for the 8-yard line; accuracy decides how close
            gross = int(round(to_goal - 8 + random.gauss(0, 9.5 - (acc - 60) / 10.0)))
        elif kind == "Coffin Corner Punt":
            # aim out of bounds at the 6: a sharper miss than a pooch, but no return when it works
            gross = int(round(to_goal - 6 + random.gauss(0, _clip(11.0 - (acc - 60) / 8.0, 4.0, 12.0))))
        self.st(p, "punts")
        if gross >= to_goal:
            # Pinning attempt: accuracy decides between downed deep or touchback
            if random.random() < _clip(0.25 + (acc - 60) / 80, 0.15, 0.80):
                spot = random.randint(2, 12)
                gross = to_goal - spot
                self.st(p, "punt_yds", gross)
                self.st(p, "punt_long", gross)
                self.st(p, "punts_in20")
                self.log(f"{_short(p.name)} punts {gross} yards, downed at the "
                         f"{self.dfn.abbr} {spot}.", "play")
                self.turnover_on_spot("Punt", spot)
                return
            self.st(p, "punt_yds", to_goal)
            self.st(p, "punt_long", to_goal)
            self.st(p, "punt_tb")
            self.log(f"{_short(p.name)} punts into the end zone. Touchback.", "play")
            self.turnover_on_spot("Punt", 20)
            return
        land = to_goal - gross                     # receiving yard line
        self.st(p, "punt_yds", gross)
        self.st(p, "punt_long", gross)
        fair_p = 0.30 + (acc - 70) / 150 + (0.25 if land < 15 else 0)
        fair_p += {"Punt Block": 0.15, "Punt Safe": 0.10, "Hold-Up Return": -0.12}.get(rcall, 0.0)
        if kind == "Pooch Punt":
            fair_p += 0.25
        oob = (kind == "Directional Punt" and random.random() < 0.22) or \
            (kind == "Coffin Corner Punt" and random.random() < _clip(0.45 + (acc - 70) / 60.0, 0.25, 0.85))
        rugby_dead = kind == "Rugby Punt" and random.random() < 0.40
        fair = False
        if oob or rugby_dead or random.random() < fair_p:
            yl = land
            fair = not (oob or rugby_dead)
            text = "out of bounds" if oob else "rolls dead" if rugby_dead else f"fair catch by {_short(ret.name)}"
        else:
            rr = ret.return_rating + self.form.get(ret.id, 0)
            mean_adj, big = {"Return Wall": (0.8, 1.25), "Punt Block": (-3.0, 0.6),
                             "Punt Safe": (-1.5, 0.8), "Hold-Up Return": (1.6, 1.2)}.get(rcall, (0.0, 1.0))
            if kind == "Directional Punt":
                mean_adj -= 2.5
            elif kind == "Rugby Punt":
                mean_adj -= 2.0
            edge = self._st_edge(self.dfn, self.poss)
            gain = max(-2, int(random.gauss(9.1 + (rr - 75) * 0.18 + mean_adj + edge * 0.6, 6)))
            if random.random() < (0.0085 + max(0, rr - 78) * 0.0007) * self.big_play * big * (1 + 0.15 * edge):
                gain = 100 - land
            self.st(ret, "pr")
            if land + gain >= 100:
                self.st(ret, "pr_yds", 100 - land)
                self.st(ret, "pr_td")
                self.log(f"{_short(p.name)} punts {gross} yards.", "play")
                self._end_drive("Punt")
                self._start_drive(self.dfn, 99)
                self.add_score(self.poss, 6, f"{_short(ret.name)} {100 - land}-yard punt return TOUCHDOWN")
                self._after_td(self.poss)
                return
            if rcall == "Hold-Up Return" and gain > 0 and random.random() < 0.06:
                # a block in the back: ten yards from the spot of the foul
                gain = max(-5, gain // 2 - 10)
                self.ts(self.dfn, "penalties")
                self.ts(self.dfn, "pen_yds", 10)
                self.log(f"PENALTY on {self.dfn.abbr}: illegal block in the back on the return, 10 yards", "play")
            self.st(ret, "pr_yds", gain)
            self._st_cover_tackle(self.poss)
            yl = max(1, land + gain)
            text = f"{_short(ret.name)} returns {gain} yards"
            if random.random() < 0.01 * self.to_rate:
                self.st(ret, "fumbles")
                self.st(ret, "fumbles_lost")
                self.log(f"{_short(p.name)} punts {gross} yards, {text} and FUMBLES! "
                         f"{self.poss.abbr} recovers.", "play")
                self._end_drive("Punt")
                self._start_drive(self.poss, 100 - yl)
                return
        if yl <= 20:
            self.st(p, "punts_in20")
        how = {"Rugby Punt": "rugby-style punt", "Directional Punt": "punts toward the sideline",
               "Pooch Punt": "pooch punt", "Coffin Corner Punt": "punts for the coffin corner"}.get(kind, "punts")
        self.log(f"{_short(p.name)} {how} {gross} yards, {text}.", "play")
        self.turnover_on_spot("Punt", yl)
        if fair:
            self._fair_catch_kick(self.poss, yl)

    def fg_probability(self, k, dist):
        acc = self.e(k, "kick_accuracy")
        power = self.e(k, "kick_power")
        comp = self.e(k, "composure")
        d50 = 56.0 + (acc - 69) * 0.50 + (power - 69) * 0.32 + (comp - 70) * 0.06
        d50 += (self.fg_mult - 1.0) * 30
        return _sig((d50 - dist - self.wx["fg_dist"]) / 7.0)

    def fg_range(self, k):
        return 55 + (self.e(k, "kick_power") - 69) * 0.42 - self.wx["fg_dist"]

    def field_goal(self):
        k = self._kicker(self.poss)
        dist = 100 - self.yl + 17
        dcall = self.st_def or self._st_def_call("fg")
        self.st_def = None
        if dcall == "Field Goal Block" and random.random() < 0.006:
            self.ts(self.dfn, "penalties")
            self.ts(self.dfn, "pen_yds", 15)
            self.log(f"PENALTY on {self.dfn.abbr}: roughing the kicker, 15 yards, automatic first down", "play")
            self.yl = min(99, self.yl + 15)
            self.down, self.togo = 1, min(10, 100 - self.yl)
            return
        prob = self.fg_probability(k, dist)
        diff = self.poss.score - self.dfn.score
        if self.quarter >= 4 and self.clock <= 120 and -3 <= diff <= 0 and self.dfn.timeouts > 0 \
                and random.random() < 0.25 + self.dfn.team.coach.tendencies.get("aggression", 0.45) * 0.4:
            self.dfn.timeouts -= 1
            self.log(f"Timeout {self.dfn.abbr} — icing the kicker", "note")
            prob -= 0.012 * (1.3 - self.e(k, "composure") / 100.0)
        bucket = "0_39" if dist < 40 else "40_49" if dist < 50 else "50"
        self.st(k, "fga")
        self.st(k, f"fga_{bucket}")
        self.ts(self.poss, "fga")
        blk = (0.019 if dcall == "Field Goal Block" else 0.007) * (1 + dist / 120.0)
        if random.random() < blk:
            self.ts(self.dfn, "fg_blocks")
            self.log(f"{_short(k.name)} {dist}-yard field goal attempt is BLOCKED", "play")
            self.swing(self.dfn, 0.35)
            self.turnover_on_spot("Blocked FG", 100 - self.yl + 7)
            return
        if random.random() < prob:
            self.st(k, "fgm")
            self.st(k, f"fgm_{bucket}")
            self.st(k, "fg_long", dist)
            self.ts(self.poss, "fgm")
            self._end_drive("Field goal")
            self.add_score(self.poss, 3, f"{_short(k.name)} {dist}-yard field goal is GOOD")
            self.run_clock(5, False)
            self._ot_check()
            if not self.game_over:
                self.kickoff(self.poss)
        else:
            side = random.choice(["wide left", "wide right", "short"]) if dist > 48 \
                else random.choice(["wide left", "wide right", "off the upright"])
            self.log(f"{_short(k.name)} {dist}-yard field goal is NO GOOD ({side})", "play")
            self.swing(self.dfn, 0.15)
            self.run_clock(5, False)
            self.turnover_on_spot("Missed FG", max(20, 107 - self.yl))

    def _after_td(self, side):
        """Extra point or two-point try, then kickoff."""
        self.ts(side, "tds")
        prob = self._two_prob(side)
        go_two = self._go_for_two(side, prob)
        if go_two:
            self.ts(side, "two_att")
            prefs = getattr(side.team, "play_prefs", None) or {}
            if random.random() < 0.05 * side.plan["trick"] * prefs.get("st:Swinging Gate", 1.0):
                # Swinging gate: the line splits out wide; a well-coached defense follows it
                read = random.random() < 0.35 + 0.4 * self._gm(self.other(side)) / 20.0
                prob += -0.08 if read else 0.14
                self.log(f"{side.abbr} line up in a swinging gate for the two-point try", "note")
            if random.random() < prob:
                self.ts(side, "two_conv")
                self.add_score(side, 2, "Two-point conversion is GOOD")
            else:
                self.log("Two-point conversion FAILS", "score")
        else:
            k = self._kicker(side)
            self.st(k, "xpa")
            if random.random() < self.fg_probability(k, self.pat_dist) * 0.995:
                self.st(k, "xpm")
                side.score += 1
                if side is self.home:
                    self.res.home_score = side.score
                else:
                    self.res.away_score = side.score
                qi = min(self.quarter, 5) - 1
                q = self.res.quarters[side.abbr]
                while len(q) <= qi:
                    q.append(0)
                q[qi] += 1
                if self.res.scoring:
                    qn, clk, ab, txt, _, _ = self.res.scoring[-1]
                    self.res.scoring[-1] = (qn, clk, ab, txt + " (kick good)",
                                            self.home.score, self.away.score)
            else:
                self.log(f"{_short(k.name)} extra point is NO GOOD", "score")
        self._ot_check()
        if not self.game_over:
            self.kickoff(side)

    def _two_prob(self, side):
        off_q = side.team.unit_ratings()["OFF"]
        def_q = self.other(side).team.unit_ratings()["DEF"]
        return _clip(0.47 + (off_q - def_q) / 300.0, 0.30, 0.65)

    def _go_for_two(self, side, prob=0.48):
        diff = side.score - self.other(side).score     # after the TD
        if self.quarter >= 5:
            return False
        k = self._kicker(side)
        xp = self.fg_probability(k, self.pat_dist) * 0.995
        secs = self._secs_left()
        if self.quarter <= 2:
            secs = max(secs, 2400.0)
        # the staff's estimate of its chance, blurred for a poor game manager
        est = _clip(prob + random.gauss(0, (20 - self._gm(side)) * 0.002), 0.2, 0.75)
        return sit_lib.two_point(diff, secs, xp, side.plan["aggression"] * self.go_mult, self._gm(side),
                                 two_prob=est, edge=self._edge_for(side),
                                 caution=sit_lib.TWO_CAUTION * gameday.caution(side.fx))

    # ── Situational decisions ────────────────────────────────────────────────

    def _kneel_ok(self):
        if self.quarter not in (2, 4, 5):
            return False
        diff = self.poss.score - self.dfn.score
        if self.quarter == 2:
            return self.clock <= 32 and self.yl < 45 and diff >= -3 and self.down >= 1
        if diff <= 0:
            return False
        downs_left = 4 - self.down + 1
        burn = 40 * downs_left - 40 * min(self.dfn.timeouts, downs_left - 1)
        return self.clock <= burn + 2

    def _fourth_down(self):
        """Return 'go', 'punt' or 'fg'."""
        k = self._kicker(self.poss)
        dist = 100 - self.yl + 17
        diff = self.poss.score - self.dfn.score
        in_range = dist <= self.fg_range(k)
        fg_p = self.fg_probability(k, dist) if in_range else 0.0
        late = self.quarter >= 4 and self.clock <= 240
        aggr = self.poss.plan["aggression"] * self.go_mult

        if late and diff < 0:
            if diff >= -3 and in_range and fg_p > 0.35:
                return "fg"
            return "go"
        if self.quarter >= 4 and self.clock <= 30 and -3 <= diff <= 0 and in_range:
            return "fg"
        if self.quarter >= 5 and diff == 0 and in_range and fg_p > 0.4:
            return "fg"
        if self.quarter >= 5 and -3 <= diff < 0 and in_range and fg_p > 0.5 and self.clock > 60:
            return "fg"
        if self.quarter == 2 and self.clock <= 30 and in_range and fg_p > 0.3:
            return "fg"

        # Everything else: compare win probability for going, punting and kicking,
        # bent by how much this coach trusts the numbers
        p = self._punter(self.poss)
        st = {"diff": diff, "secs": self._secs_left() if self.quarter <= 4 else 1800.0, "yl": self.yl,
              "togo": self.togo, "fg_prob": fg_p, "fg_range_ok": in_range and fg_p > 0.05,
              "punt_net": 39 + (p.a("punt_power") - 70) * 0.12 + self.wx["punt"] * 0.8,
              "edge": self._edge_for(self.poss),
              "off_edge": self.poss.conv_edge}
        if self.quarter <= 2:
            st["secs"] = max(st["secs"], 1800.0)        # first-half calls are about points, not the clock
        return sit_lib.choose_fourth(st, _clip(aggr, 0.0, 1.5), self._gm(self.poss),
                                     caution=sit_lib.FOURTH_CAUTION * gameday.caution(self.poss.fx))

    def _secs_left(self):
        if self.quarter > 4:
            return max(1.0, self.clock)
        return max(1.0, 3600.0 - self.elapsed())

    def _edge_for(self, side):
        """Pre-game strength edge (points over a full game) from this side's point of view."""
        return self.pre_edge if side is self.home else -self.pre_edge

    def _tired_front(self):
        """Extra chance to go no-huddle: a sharp staff keeps a gassed defensive front on the field."""
        if self.urgency(self.poss) != "normal":
            return 0.0
        lu = self.dfn.lu
        front = lu.get("DT", [])[:2] + lu.get("EDGE", [])[:2]
        if not front:
            return 0.0
        en = sum(self.energy.get(p.id, 100.0) for p in front) / len(front)
        return _clip((88.0 - en) / 100.0, 0.0, 0.08) * self.poss.ogp["g"] * 2.0

    def _gm(self, side):
        """Game management as this staff decides with it (the CPU difficulty dial sharpens it)."""
        return self._sharp(side, side.team.coach.r("game_management"))

    def _pass_probability(self):
        plan = self.poss.plan
        p = plan["pass_rate"]
        d, t = self.down, self.togo
        if d == 1:
            p -= 0.06 if t >= 10 else 0.10
        elif d == 2:
            p += 0.13 if t >= 8 else (-0.13 if t <= 3 else 0.0)
        elif d >= 3:
            if t >= 7:
                p += 0.36
            elif t >= 4:
                p += 0.22
            elif t <= 2:
                p -= 0.24
        if self.yl >= 97:
            p += 0.02
        elif self.yl >= 85:
            p += 0.04
        # The coordinator's own situational habits
        oc = self.poss.team.coach
        if d <= 2:
            p += sit_tendency(oc, "sit_early")
        elif t <= 2:
            p += sit_tendency(oc, "sit_short")
        if self.yl >= 80:
            p += sit_tendency(oc, "sit_rz")
        diff = self.poss.score - self.dfn.score
        mode = self.urgency(self.poss)
        if mode == "hurry":
            p += 0.24
        elif mode == "milk":
            p -= 0.22
        else:
            # Game script: protect leads on the ground, chase deficits through
            # the air. The pull grows as the clock runs; aggressive coaches
            # keep throwing with a lead.
            prog = _clip(self.elapsed() / 3600.0, 0.0, 1.0)
            s = diff / (7.0 + 14.0 * (1.0 - prog))
            lean = 0.21 * math.tanh(s) * (0.30 + 0.70 * prog)
            if diff > 0:
                lean *= 1.2 - 0.45 * plan["aggression"]
            p -= lean
        p += self.wx["pass_shift"] + self.pass_shift + self.poss.oshift
        if mode == "normal":
            p += self.poss.ogp["pass_shift"]
            # Self-scouting: a staff that knows the defense reads its tendencies breaks them
            own = self.poss.self_read
            if own is not None and self.dfn.dgp.get("read") is not None:
                b = self.sit_bucket(d, t, self.yl)
                p -= 0.5 * self.poss.ogp["g"] * gameday.sit_lean(own, b)
        return _clip(p, 0.05, 0.97)

    # ── A single snap ────────────────────────────────────────────────────────

    def snap(self):
        self.cur_diag = None
        self._adv = None
        self._adv_void = False
        self._ocall = None
        self._motion_kind = None
        self.dcall = None
        self._last_tackler = None
        self._rush_winner = None
        self._run_side = 1 if random.random() < self.poss.ogp["run_right"] else -1
        mid_drive = self.drive is not None and self.drive["plays"] >= 1
        self.no_huddle = mid_drive and (self.urgency(self.poss) == "hurry" or
                                        random.random() < self.poss.plan["tempo"] * 0.30 + self._tired_front())
        if self.mom:
            self.mom *= 0.92
            self.mom_pts = self.mom * 1.6 * self.mom_scale
        if self.drive is not None:
            self.drive["plays"] += 1
        if self.yl >= 80 and not self.drive["rz"]:
            self.drive["rz"] = True
            self.ts(self.poss, "rz_trips")

        # End-of-half / game situations
        if self._spike_next:
            self._spike_next = False
            self._spike()
            return
        if self._kneel_ok():
            self._kneel()
            return
        diff = self.poss.score - self.dfn.score
        k = self._kicker(self.poss)
        fg_dist = 100 - self.yl + 17
        in_range = fg_dist <= self.fg_range(k) + 3
        late_kick = self.clock <= 6 or (self.clock <= 14 and self.poss.timeouts == 0)
        if late_kick and in_range and (self.quarter == 2 or (self.quarter >= 4 and -3 <= diff <= 0)):
            self.field_goal()
            return
        if self.quarter >= 4 and self.clock <= 6 and -8 <= diff < 0 and self.yl < 45:
            self.resolve(self._laterals())
            return
        if self.drive is not None and self.drive["plays"] == 1 and self.quarter in (1, 2, 3) \
                and self.poss.timeouts > 0 and \
                random.random() < (20 - self._gm(self.poss)) / 20.0 * 0.035:
            # Sloppy operation: a timeout burned to avoid a delay-of-game flag
            self.poss.timeouts -= 1
            self.log(f"Timeout {self.poss.abbr} (to avoid a delay of game)", "note")
        if self.down == 4:
            choice = self._fourth_down()
            if choice in ("punt", "fg"):
                self.st_def = self._st_def_call(choice)
            if choice in ("punt", "fg") and self._fake_ok():
                pre = self._ep_pre()
                out = self._fake_kick(choice)
                self.resolve(out)
                self._credit_adv(pre, out)
                return
            if choice == "punt":
                self.run_clock(8, False)
                self.punt()
                return
            if choice == "fg":
                self.field_goal()
                return

        # Pre-snap penalty
        if self._pre_snap_penalty():
            return
        if self.down == 3 and self.togo >= 10 and 8 <= self.yl <= 35 and self.quarter <= 3 \
                and self.urgency(self.poss) == "normal" and random.random() < self._quick_kick_rate():
            self._quick_kick()
            return

        hail = (self.clock <= 8 and self.quarter in (2, 4) and 45 <= self.yl < 70
                and (self.quarter == 2 or -8 <= diff < 0))
        plan = self.poss.plan
        normal = not hail and self.urgency(self.poss) == "normal"
        if normal and self.down <= 2 and 25 <= self.yl <= 85 and \
                random.random() < 0.010 * plan["trick"]:
            out = self._trick_play()
        elif normal and self.down <= 3 and self.togo <= 10 and self.yl < 97 and \
                random.random() < plan["rpo"] * 0.16:
            out = self._rpo()
        elif hail or random.random() < self._pass_probability():
            out = self.pass_play(hail=hail)
        else:
            out = self.run_play()
        pre = self._ep_pre()
        self.resolve(out)
        self._credit_adv(pre, out)

    # ── Advanced stats: expected points added, success, air yards ────────────

    def _ep_pre(self):
        side = self.poss
        self._pre_sit = (self.down, self.togo, self.yl)
        return (side, self.other(side), adv_lib.expected_points(self.down, self.togo, self.yl),
                side.score, self.other(side).score, self.quarter, self.togo)

    @staticmethod
    def sit_bucket(down, togo, yl):
        if yl >= 80:
            return "Red zone"
        if down <= 2:
            return "1st & 2nd down"
        if togo <= 2:
            return "3rd/4th & short"
        if togo <= 6:
            return "3rd/4th & medium"
        return "3rd/4th & long"

    def _credit_adv(self, pre, out):
        if self._adv_void:
            return
        side, other, ep0, s0, o0, q0, togo0 = pre
        dpts = (side.score - s0) - (other.score - o0)
        if dpts:
            if out.get("safety"):
                post = dpts - adv_lib.KICKOFF_EP
            else:
                post = dpts + (-adv_lib.KICKOFF_EP if dpts > 0 else adv_lib.KICKOFF_EP)
        elif self.game_over or (self.quarter != q0 and q0 in (2, 4, 5)):
            post = 0.0
        elif self.poss is side:
            post = adv_lib.expected_points(self.down, self.togo, self.yl)
        else:
            post = -adv_lib.expected_points(self.down, self.togo, self.yl)
        e = round(post - ep0, 3)
        good = e > 0
        self.ts(side, "epa", e)
        self.ts(side, "epa_plays")
        if good:
            self.ts(side, "succ")
        # Play-calling report: how each call worked (offence and defence)
        ts_off = self.res.team_stats[side.abbr]
        ts_def = self.res.team_stats[other.abbr]
        if self._ocall:
            mo = getattr(self, "_motion_kind", None)
            for call in (self._ocall, f"Motion: {mo}" if mo else "No motion"):
                ts_off[f"oc|{call}|n"] += 1
                ts_off[f"oc|{call}|epa"] += e
                if good:
                    ts_off[f"oc|{call}|s"] += 1
        dc = self.dcall
        if dc is not None:
            for fam in (dc["cov"], "Pressure (5+ rushers)" if dc["blitz"] else
                        ("Line stunt" if dc["stunt"] else dc["sim"] if dc["sim"] else "Four-man rush"),
                        dc["front"] + " front"):
                ts_def[f"dc|{fam}|n"] += 1
                ts_def[f"dc|{fam}|epa"] += e
                if good:
                    ts_def[f"dc|{fam}|s"] += 1
        # Tendency tracking by situation (for scouting reports)
        a0 = self._adv or {}
        is_pass = out["kind"] in ("pass", "sack") or a0.get("qb") is not None
        b = self.sit_bucket(*getattr(self, "_pre_sit", (self.down, self.togo, self.yl)))
        ts_off[f"sit|{b}|n"] += 1
        if is_pass:
            ts_off[f"sit|{b}|p"] += 1
        g = self.gstats[side.abbr]
        if out["kind"] == "run" or (self._adv or {}).get("rusher") is not None:
            g["run_n"] += 1
            g["run_epa"] += e
        elif out["kind"] in ("pass", "sack", "turnover", "pick6"):
            g["pass_n"] += 1
            g["pass_epa"] += e
            if (self._adv or {}).get("air", 0) >= 15:
                g["deep_n"] += 1
                g["deep_epa"] += e
        a = self._adv
        if not a:
            return
        yards = out.get("yards", 0)
        self._exert(out.get("carrier"), yards)
        if not good and self._last_tackler is not None and out["kind"] in ("run", "pass") \
                and not out.get("incomplete"):
            self.st(self._last_tackler, "stops")
        moved = out.get("td") or (yards >= togo0 and out["kind"] in ("run", "pass"))
        if a.get("qb") is not None:
            qb = a["qb"]
            self.st(qb, "dropbacks")
            self.st(qb, "pass_epa", e)
            self.ts(side, "dropbacks")
            if good:
                self.st(qb, "pass_succ")
            if a.get("pressured"):
                self.st(qb, "pressured")
                self.ts(side, "pressured")
            rec = a.get("rec")
            if rec is not None and not a.get("scramble"):
                air = a.get("air", 0)
                self.st(qb, "iay", air)
                self.ts(side, "iay", air)
                self.st(rec, "rec_air", air)
                self.st(rec, "rec_epa", e)
                if out.get("complete"):
                    self.st(qb, "cay", air)
                    if moved:
                        self.st(qb, "pass_first")
                        self.st(rec, "rec_first")
                d = a.get("dfnd")
                if d is not None:
                    self.st(d, "tgt_allowed")
                    if out.get("complete"):
                        self.st(d, "cmp_allowed")
                        self.st(d, "yds_allowed", yards)
                        if out.get("td"):
                            self.st(d, "td_allowed")
        elif a.get("rusher") is not None:
            r = a["rusher"]
            self.st(r, "rush_epa", e)
            if good:
                self.st(r, "rush_succ")
            if moved:
                self.st(r, "rush_first")

    def _spike(self):
        qb = self.poss.qb
        self.st(qb, "pass_att")
        self.ts(self.poss, "pass_att")
        self.ts(self.poss, "spikes")
        self.log(f"{_short(qb.name)} spikes the ball to stop the clock")
        self.clock -= 1
        self.down += 1

    def _laterals(self):
        """Last play, out of range: the hook-and-lateral circus."""
        off = self.poss
        self.ts(off, "plays")
        qb = off.qb
        wrs = off.lu["WR"][:3] or off.lu["RB"][:1]
        carrier = max(wrs, key=lambda p: p.a("speed")) if wrs else qb
        to_goal = 100 - self.yl
        speed = (self.e(carrier, "speed") - 85) / 400.0
        self.clock = 0
        if random.random() < 0.025 + speed:
            self.st(qb, "pass_att")
            self.st(qb, "pass_cmp")
            self.st(qb, "pass_yds", to_goal)
            self.st(carrier, "targets")
            self.st(carrier, "rec")
            self.st(carrier, "rec_yds", to_goal)
            self.ts(off, "pass_att")
            self.ts(off, "pass_cmp")
            self.ts(off, "pass_yds", to_goal)
            return {"kind": "pass", "yards": to_goal, "time": 14, "clock_runs": True, "carrier": carrier,
                    "td": True, "complete": True, "ptype": "short", "air": 5,
                    "text": f"Laterals! {_short(carrier.name)} breaks free on a multi-lateral play — "
                            f"{to_goal} yards, TOUCHDOWN"}
        gain = min(random.randint(3, 25), to_goal - 1)
        self.st(carrier, "rush_att")
        self.st(carrier, "rush_yds", gain)
        self.ts(off, "rush_att")
        self.ts(off, "rush_yds", gain)
        return {"kind": "run", "yards": gain, "time": 12, "clock_runs": True, "carrier": carrier,
                "text": f"Lateral after lateral... {_short(carrier.name)} is finally dragged down after {gain} yards"}

    def _kneel(self):
        qb = self.poss.qb
        self.st(qb, "rush_att")
        self.st(qb, "rush_yds", -1)
        self.ts(self.poss, "rush_att")
        self.ts(self.poss, "rush_yds", -1)
        self.log(f"{_short(qb.name)} kneels.")
        self.yl = max(1, self.yl - 1)
        self.down += 1
        self.togo += 1
        stop = self.dfn.timeouts > 0 and self.dfn.score < self.poss.score
        if stop:
            self.dfn.timeouts -= 1
            self.run_clock(2, False)
        else:
            self.clock -= 41
            self.ts(self.poss, "top", 41)
        if self.down > 4 and self.clock > 0:
            self.turnover_on_spot("Downs")

    def _pre_snap_penalty(self):
        rate = 0.034 * self.pen_rate
        om, ounf = self._flag_odds(self.poss, "off")
        dm, dunf = self._flag_odds(self.dfn, "def")
        off_disc = (1.35 - self.poss.disc / 100.0 * 0.7) * om
        def_disc = (1.35 - self.dfn.disc / 100.0 * 0.7) * dm
        # Illegal motion / illegal shift: a cost of moving people before the snap
        mov = pb.motion_share(self.poss.plan.get("motion", 0.5))
        if random.random() < 0.0030 * mov * om * self.pen_rate:
            pool = self.poss.lu["WR"][:3] + self.poss.lu["TE"][:1]
            if pool:
                p = random.choices(pool, weights=[max(5, 105 - self.e(x, "awareness")) for x in pool])[0]
                name = random.choice(["Illegal motion", "Illegal shift"])
                self._penalty(self.poss, p, name, 5)
                self.yl = max(1, self.yl - 5)
                self.togo += 5
                self.log(f"PENALTY: {name}, {self.poss.abbr} ({_short(p.name)}), 5 yards", "play")
                self.run_clock(0, False)
                return True
        r = random.random()
        if r < rate * off_disc * 0.55:
            name = random.choice(["False start", "False start", "Delay of game",
                                  "Illegal formation"])
            p = random.choice(self.poss.ol) if name == "False start" else self.poss.qb
            p = self._culprit(ounf, om, p)
            self._penalty(self.poss, p, name, 5)
            self.yl = max(1, self.yl - 5)
            self.togo += 5
            self.log(f"PENALTY: {name}, {self.poss.abbr} ({_short(p.name)}), 5 yards", "play")
            self.run_clock(0, False)
            return True
        if r < rate * (off_disc * 0.55 + def_disc * 0.45):
            name = random.choice(["Offside", "Neutral zone infraction", "Encroachment"])
            p = random.choice(self.dfn.lu["DT"][:2] + self.dfn.lu["EDGE"][:2])
            p = self._culprit(dunf, dm, p)
            yds = min(5, (100 - self.yl) // 2) if self.yl > 90 else 5
            self._penalty(self.dfn, p, name, yds)
            self.yl += yds
            self.togo -= yds
            self.log(f"PENALTY: {name}, {self.dfn.abbr} ({_short(p.name)}), {yds} yards", "play")
            if self.togo <= 0:
                self._first_down(penalty=True)
            self.run_clock(0, False)
            return True
        return False

    def _penalty(self, side, player, name, yards):
        self.ts(side, "penalties")
        self.ts(side, "pen_yds", yards)
        self.st(player, "penalties")
        self.st(player, "pen_yds", yards)

    # ── Personnel ────────────────────────────────────────────────────────────

    def _personnel(self):
        plan = self.poss.plan
        heavy = plan["heavy"]
        short = self.togo <= 2 or self.yl >= 96
        side = self.poss
        has_fb = bool(side.team.players_at("FB"))
        three_te = side.n_te >= 3 or "JTE" in side.pk_set
        w = {
            "11": max(0.05, 0.64 - 0.38 * heavy),
            "12": 0.12 + 0.22 * heavy,
            "21": (0.03 + 0.14 * heavy) if has_fb else 0.0,
            "10": 0.03 + 0.10 * plan["tempo"] + 0.14 * max(0, plan["pass_rate"] - 0.58),
            "22": 0.01,
            "13": (0.02 + 0.07 * heavy) if three_te else 0.0,
            "20": 0.012 + 0.02 * plan["tempo"] if len(side.lu["RB"]) >= 2 else 0.0,
            "23": 0.0,
        }
        scheme = self.poss.team.coach.off_scheme
        if scheme == "Flexbone":
            w["10"] += 0.75                 # two slotbacks ("A-backs") flank the B-back
        elif scheme == "Wing-T" and w["21"]:
            w["21"] += 0.45
        elif scheme == "Run and Shoot":
            w["10"] += 0.30
        elif scheme == "Pistol":
            w["12"] += 0.08
            w["20"] += 0.02 if w["20"] else 0.0
        elif scheme == "Spread Option":
            w["20"] += 0.02 if w["20"] else 0.0
        if short:
            w["22"] += 0.35
            w["12"] += 0.25
            w["21"] += 0.15 if w["21"] else 0.0
            w["13"] += 0.12 if w["13"] else 0.0
            w["10"] *= 0.3
            w["20"] *= 0.3
            if self.yl >= 97 and has_fb and three_te:
                w["23"] += 0.22             # goal-line jumbo: three tight ends and two backs
        if self.urgency(self.poss) == "hurry":
            w["10"] += 0.25
            w["22"] = w["13"] = w["23"] = 0.0
        keys = list(w)
        return random.choices(keys, weights=[w[k] for k in keys], k=1)[0]

    def _adds(self, side, pkg, base, n_pkg, n_base, lock=False, used=None):
        """
        A package that puts extra men beside the base starters (slot receivers,
        nickel backs, a third safety or tight end). When the user has set the
        package list, its players are picked first and the base list fills around
        them; otherwise the base starters come first and the package adds the next men.
        """
        if n_pkg <= 0:
            return self._rotate(side, base, n_base, lock, used), []
        if pkg in side.pk_set:
            extra = self._fill(side, pkg, n_pkg, lock, used)
            core = self._rotate(side, base, n_base, lock, used)
        else:
            core = self._rotate(side, base, n_base, lock, used)
            extra = self._fill(side, pkg, n_pkg, lock, used)
        return core, extra

    def _fill(self, side, pos, n, lock=False, used=None):
        """_rotate, and a package list that runs short is topped up from its base position."""
        out = self._rotate(side, pos, n, lock, used)
        if len(out) < n and pos in packages.PACKAGE_SLOTS:
            out += self._rotate(side, packages.base_of(pos), n - len(out), lock, used)
        return out

    def _formation(self, pers):
        lu = self.poss.lu
        n_rb, te_n, wr_n = packages.personnel_counts(pers)
        fb = pers in ("21", "22", "23")
        two_rb = pers == "20"
        side = self.poss
        # One spot per player per snap: the quarterback and the line first, then the back,
        # tight ends and receivers; a player listed twice plays the first, the next man the other
        used = {p.id for p in side.ol}
        qb = side.qb
        if qb is not None:
            used.add(qb.id)
        rb = self._pick_rb()
        if rb is not None and rb.id in used:
            rb = next((p for p in lu["RB"] + side.more("RB") if p.id not in used), None)
        if rb is not None:
            used.add(rb.id)
        if te_n >= 3:
            tes, jumbo = self._adds(side, "JTE", "TE", te_n - 2, 2, used=used)
            tes = tes + jumbo
        else:
            tes = self._rotate(side, "TE", te_n, used=used) if te_n else []
        if wr_n >= 3:
            outs, slots = self._adds(side, "SLOT", "WR", wr_n - 2, 2, used=used)
            wrs = outs + slots
        else:
            wrs = self._rotate(side, "WR", wr_n, used=used) if wr_n else []
        if two_rb:
            # 20 personnel: a second running back (the third-down back if there is one) beside the first
            fbp = next((p for p in [side.bf["third"] if side.bf else None] + lu["RB"] + side.more("RB")
                        if p is not None and p.id not in used), None)
        else:
            fbp = next((p for p in lu["FB"] + side.more("FB") if p.id not in used), None) \
                if fb and lu["FB"] else None
        if fbp is not None:
            used.add(fbp.id)
        self._pers = pers
        return wrs, tes, rb, fbp

    def _off_slots(self, off, wrs, tes):
        """Slot labels for _snap_units, parallel to [qb] + ol + wrs + tes + [rb, fbp]."""
        return ["QB"] + off.ol_slots + ["WR"] * len(wrs) + ["TE"] * len(tes) + \
            ["RB", "RB" if getattr(self, "_pers", None) == "20" else "FB"]

    @staticmethod
    def _def_slots(dts, edges, lbs, cbs, ss):
        return ["DT"] * len(dts) + ["EDGE"] * len(edges) + ["LB"] * len(lbs) + \
            ["CB"] * len(cbs) + ["S"] * len(ss)

    def _pick_rb(self):
        side = self.poss
        rbs = side.lu["RB"]
        if not rbs:
            return None
        bf = side.bf
        if len(rbs) == 1 or bf is None:
            return rbs[0]
        rb1 = bf["rb1"]
        to_goal = 100 - self.yl
        # Situational specialists
        if bf["goal"] is not None and (to_goal <= 3 or (self.togo <= 1 and self.down >= 3)) \
                and random.random() < 0.40 + 0.25 * bf["committee"]:
            return bf["goal"]
        passing_down = (self.down == 3 and self.togo >= 5) or self.urgency(side) == "hurry" \
            or (self.down == 2 and self.togo >= 10)
        if bf["third"] is not None and passing_down and \
                random.random() < 0.30 + 0.45 * bf["committee"]:
            pick = bf["third"]
            side.rb1_streak = 0 if pick is not rb1 else side.rb1_streak
            return pick
        share = bf["share"]
        # Fatigue: a winded back gets a breather (energy falls with every snap he plays)
        share -= max(0.0, 88.0 - self.energy_of(rb1)) * 0.016
        if self._garbage(side):
            share *= 0.35
        # Ride the hot hand (or sit a struggling starter)
        line = self.res.player_stats.get(rb1.id)
        if line and line["rush_att"] >= 8:
            ypc = line["rush_yds"] / line["rush_att"]
            share += _clip((ypc - 4.3) * 0.025, -0.10, 0.08)
        # Closing out a win: feed the starter
        if self.quarter >= 4 and side.score - self.dfn.score >= 8:
            share += 0.06
        # Workload management: limit carries in a game and across a season
        if line and line["rush_att"] > 22:
            share -= (line["rush_att"] - 22) * 0.035
        ss = rb1.season_stats
        gp = ss.get("gp", 0)
        if gp >= 3:
            per_game = ss.get("rush_att", 0) / gp
            if per_game > 20.5:
                share -= (per_game - 20.5) * 0.05
        share = _clip(share, 0.25, 0.95)
        if random.random() < share:
            side.rb1_streak += 1
            return rb1
        side.rb1_streak = 0
        if bf["rb3"] is not None and random.random() < 0.07:
            return bf["rb3"]
        return bf["rb2"] or rb1

    def _slot_map(self, pers, wrs, tes, rb, fbp):
        """Which player lines up in which formation slot."""
        out = {}
        wr_slots = ["X"] if pers in ("22", "13") else [] if pers == "23" else ["X", "Z", "SL", "SL2"]
        for s, p in zip(wr_slots, wrs):
            out[s] = p
        for s, p in zip(["TE", "TE2", "TE3"], tes):
            out[s] = p
        if rb is not None:
            out["RB"] = rb
        if fbp is not None:
            out["FB"] = fbp
        return out

    def _passing_down(self):
        return (self.down == 3 and self.togo >= 7) or (self.down == 2 and self.togo >= 12) or \
            (self.down == 4 and self.togo >= 5) or self.urgency(self.poss) == "hurry"

    def _big_nickel_lean(self, d):
        """How much this coordinator likes a third safety against tight ends (0-1)."""
        s3 = d.lu.get("S3") or []
        lbs = d.lu.get("LB") or []
        if not s3:
            return 0.0
        lean = 0.15 + 0.35 * d.plan.get("two_high", 0.5)
        if "S3" in d.pk_set:
            lean += 0.25
        if d.team.coach.def_scheme == "Three-High":
            lean += 0.35                    # the system is built on a third safety
        if len(lbs) >= 3:
            lean += _clip((s3[0].rating_at("S3") - lbs[2].rating_at("LB")) / 40.0, -0.3, 0.3)
        return _clip(lean, 0.0, 0.9)

    def _defense_set(self, pers):
        """The defense's package for this snap (matched to the offense's personnel) and who plays."""
        d = self.dfn
        if pers == "10" and self.poss.team.coach.off_scheme == "Flexbone":
            pers = "21"                     # slotbacks are treated as backs: base defense
        lock = self.no_huddle             # no time to substitute against a no-huddle offense
        if lock and d.last_pkg:
            pkg = d.last_pkg
        else:
            to_goal = 100 - self.yl
            late_long = to_goal >= 35 and ((self.quarter in (2, 4) and self.clock <= 12) or
                                           (self.down == 4 and self.togo >= 15 and self.quarter == 4
                                            and self.clock <= 90 and self.poss.score < d.score))
            pkg = packages.choose_def_package(pers, d.plan["front"], to_goal, self.togo, self.down,
                                              late_long, self._big_nickel_lean(d), random)
            if pkg == "Nickel" and d.team.coach.def_scheme == "Three-High" and d.lu.get("S3") \
                    and random.random() < 0.5:
                pkg = "Big Nickel"          # the system's base: a third safety instead of a nickel corner
        d.last_pkg = pkg
        self.ts(d, f"dpkg|{pkg}")
        n_dt, n_edge, n_lb, n_cb, n_s = packages.DEF_PACKAGES[pkg]
        rush = self._passing_down() and pkg not in ("Goal Line", "Base", "3-4 Base")
        used = set()
        dts = self._fill(d, "RDT" if rush else "DT", n_dt, lock, used)
        edges = self._fill(d, "RE" if rush else "EDGE", n_edge, lock, used)
        sub = pkg in ("Nickel", "Big Nickel", "Dime", "Quarter")
        lbs = self._fill(d, "SUBLB" if sub else "LB", n_lb, lock, used)
        core, extra = self._adds(d, "NCB", "CB", n_cb - 2, min(2, n_cb), lock, used)
        cbs = core + extra
        core, extra = self._adds(d, "S3", "S", n_s - 2, min(2, n_s), lock, used)
        ss = core + extra
        self._dpkg = pkg
        return dts, edges, lbs, cbs, ss

    # ── Unit strengths ───────────────────────────────────────────────────────

    def _pass_pro(self, extra_blockers):
        e = self.e
        ol = self.poss.ol
        v = sum(e(p, "pass_block") * 0.50 + e(p, "footwork") * 0.25 + e(p, "strength") * 0.12
                + e(p, "awareness") * 0.13 for p in ol) / max(1, len(ol))
        for b in extra_blockers:
            v += (e(b, "pass_block") - 55) * 0.06
        v += (staff_mod.off_calling(self.poss.team) - 10) * 0.35
        return v

    def _def_call(self, n_cb, n_s=2):
        """The defensive coordinator's call for this snap (he never sees the offensive call)."""
        de = self.dfn
        sit = {"down": self.down, "togo": self.togo, "to_goal": 100 - self.yl,
               "hurry": self.urgency(self.poss) == "hurry",
               "late": (self.quarter == 4 and self.clock <= 150) or (self.quarter == 2 and self.clock <= 40),
               "lead": de.score - self.poss.score, "n_cb": n_cb, "n_s": n_s}
        dp = dict(de.plan)
        for k in ("blitz", "zone", "two_high"):
            dp[k] = _clip(dp[k] + de.dgp.get(k, 0.0) + de.dadj.get(k, 0.0), 0.0, 1.0)
        dp["blitz"] = _clip(dp["blitz"] + de.blitz_adj, 0.0, 1.0)
        call = dfn_lib.choose_call(dp, sit, scheme=de.team.coach.def_scheme, prefs=de.prefs)
        box = de.dgp.get("box", 0.0) + de.dadj.get("box", 0.0)
        rd = de.dgp.get("read")
        if rd is not None and not sit["hurry"]:
            # They throw here more (or less) than usual: lighten (or load) the box
            box -= gameday.sit_lean(rd, self.sit_bucket(self.down, self.togo, self.yl)) * 2.0 * de.dq
        call["box"] = _clip(box, -1.0, 1.0)
        self._spy_on = bool(de.dgp.get("spy")) and not call["blitz"] and random.random() < 0.75
        self.dcall = call
        return call

    def _pass_rush(self, rushers):
        e = self.e
        tot = 0.0
        wsum = 0.0
        for p, w in rushers:
            best = max(e(p, "power_move"), e(p, "finesse_move"))
            other = min(e(p, "power_move"), e(p, "finesse_move"))
            v = best * 0.34 + other * 0.10 + e(p, "pass_rush_iq") * 0.18 \
                + e(p, "acceleration") * 0.22 + e(p, "strength") * 0.16
            tot += v * w
            wsum += w
        v = tot / max(0.01, wsum)
        v += (staff_mod.def_calling(self.dfn.team) - 10) * 0.35
        return v

    # ── Pass play ────────────────────────────────────────────────────────────

    def pass_play(self, hail=False, call=None):
        call = call or {}
        e = self.e
        off, de = self.poss, self.dfn
        plan, dplan = off.plan, de.plan
        qb = off.qb
        self._adv = {"qb": qb, "pressured": False}
        pers = self._personnel()
        wrs, tes, rb, fbp = self._formation(pers)
        dts, edges, lbs, cbs, ss = self._defense_set(pers)
        self._snap_units([qb] + off.ol + wrs + tes + [rb, fbp], dts + edges + lbs + cbs + ss,
                         self._off_slots(off, wrs, tes), self._def_slots(dts, edges, lbs, cbs, ss))
        to_goal = 100 - self.yl
        self.ts(off, "plays")

        # Play type
        if hail:
            ptype = "hail"
        else:
            deep = 0.125 + 0.10 * plan["deep"] - 0.06 * dplan["two_high"] + off.ogp["deep_shift"]
            deep += (e(qb, "throw_power") - 75) / 600.0
            screen = max(0.005, 0.025 + 0.09 * plan["screen"] + off.ogp["screen_shift"])
            medium = 0.28 + 0.05 * plan["deep"]
            oc = off.team.coach
            if self.down == 1 and self.togo >= 10 and 30 <= self.yl <= 65:
                deep += 0.09 * sit_tendency(oc, "sit_shot")           # shot play
            if self.down >= 3 and self.togo >= 9:
                screen += 0.10 * sit_tendency(oc, "sit_long")         # give-up screen
            if self.togo >= 12:
                medium += 0.06
                deep += 0.03
            if to_goal <= 12:
                deep = 0.0 if to_goal < 6 else 0.10
                medium = 0.08 if to_goal <= 10 else medium
            if to_goal <= 20 and to_goal > 12:
                deep *= 0.4
            if self.urgency(off) == "hurry" and self.clock < 60:
                deep += 0.06
                screen *= 0.3
            short = max(0.25, 1.0 - deep - screen - medium)
            ptype = random.choices(["screen", "short", "medium", "deep"],
                                   weights=[screen, short, medium, deep], k=1)[0]
        if call.get("rpo"):
            ptype = "screen" if random.random() < 0.25 else "short"
        elif call.get("trick") == "flea":
            ptype = "deep"

        # Play-action: sell the run, freeze the linebackers, take a shot
        pa = False
        if call.get("trick") == "flea":
            pa = True
        elif not hail and not call and ptype != "screen" and self.down <= 2 and \
                self.urgency(off) == "normal" and to_goal > 4:
            line = self.res.team_stats[off.abbr]
            ypc = line["rush_yds"] / line["rush_att"] if line["rush_att"] >= 6 else 4.2
            cred = _clip(0.80 + (ypc - 4.2) * 0.10 + (0.55 - plan["pass_rate"]) * 0.8, 0.55, 1.25)
            if random.random() < plan["play_action"] * 0.62 * cred:
                pa = True
                if ptype == "short" and random.random() < 0.45:
                    ptype = "medium"
                elif ptype == "medium" and random.random() < 0.20:
                    ptype = "deep"

        # The call: a formation and a concept from the coach's system
        gun = 0.35 + 0.5 * plan["tempo"] + (0.3 if self.down >= 3 else 0.0)
        form_name = pb.choose_formation(pers, run=False, gun_bias=min(1.0, gun),
                                        scheme=off.team.coach.off_scheme)
        play = pb.choose_pass_play(off.team.coach.off_scheme, ptype, pa=pa,
                                   trick=call.get("trick") == "flea",
                                   prefs=off.prefs, rpo=bool(call.get("rpo")), form=form_name)
        self._ocall = play["name"]
        self._track_form(off, pers, form_name)
        if pa:
            self.ts(off, "pa_att")
        if ptype == "screen":
            self.ts(off, "screen_att")
        if call.get("rpo") or call.get("rpo_bad"):
            self.ts(off, "rpo_pass")
        slot_of = self._slot_map(pers, wrs, tes, rb, fbp)
        route_of = {p.id: pb.route_for(play, slot) for slot, p in slot_of.items()}

        # The defensive call
        dc = self._def_call(len(cbs), len(ss))
        blitz = dc["blitz"]
        # Backs with a protection assignment check-release when nobody comes
        if not blitz and not pa and not call.get("rpo"):
            for slot in ("RB", "FB"):
                p = slot_of.get(slot)
                if p is not None and route_of.get(p.id) == "block" and random.random() < 0.55:
                    route_of[p.id] = "checkdown"
        rushers = [(p, 1.0) for p in edges] + [(p, 0.62) for p in dts]
        kinds = {p.id: "edge" for p in edges}
        kinds.update({p.id: "inside" for p in dts})
        cov_lbs, cov_ss, cov_cbs = list(lbs), list(ss), list(cbs)
        for who in dc["who"]:
            if who == "CB":
                pool = cov_cbs[1:2] or cov_cbs      # the second corner comes off the edge
            else:
                pool = {"LB": cov_lbs, "S": cov_ss, "NB": cov_cbs[2:] or cov_lbs}[who]
            if pool:
                b = pool[-1]
                for lst in (cov_lbs, cov_ss, cov_cbs):
                    if b in lst:
                        lst.remove(b)
                if who == "CB" and cov_ss:
                    cov_cbs.insert(1, cov_ss.pop())   # a safety rotates down to the corner's man
                rushers.append((b, 0.55))
                kinds[b.id] = "blitz"
        if dc["rush"] == 3 and dts:
            rushers = [r for r in rushers if r[0] is not dts[-1]]
        if self._spy_on and cov_lbs:
            cov_lbs.pop(0)                       # the spy mirrors the quarterback
        sim = dc["sim"]
        if sim and dts and lbs and (sim == "Creeper" or random.random() < (0.6 if sim == "Amoeba" else 0.5)):
            # a linebacker comes and a lineman drops: four rushers, but not the four the line expected
            lb_in = lbs[-1] if sim != "Double Mug" else lbs[0]
            rushers = [r for r in rushers if r[0] is not dts[-1]] + [(lb_in, 0.62)]
            kinds[lb_in.id] = "blitz"
            if lb_in in cov_lbs:
                cov_lbs.remove(lb_in)
        keep_in = []
        if rb and random.random() < (0.22 if not blitz else 0.45):
            keep_in.append(rb)
        if tes and pers in ("12", "22", "13", "23") and random.random() < 0.35:
            keep_in.append(tes[-1])
        for slot in ("RB", "FB", "TE", "TE2", "TE3"):
            p = slot_of.get(slot)
            if p is not None and route_of.get(p.id) == "block" and p not in keep_in:
                keep_in.append(p)
        if dc["man"] and not blitz and rb in keep_in and cov_lbs:
            # Green dog: the linebacker on the back sees him stay in to block and rushes too
            gd = cov_lbs[-1]
            if random.random() < 0.5 * _clip((e(gd, "play_recognition") - 50) / 40.0, 0.2, 1.0):
                cov_lbs.remove(gd)
                rushers.append((gd, 0.45))
                kinds[gd.id] = "blitz"
        zone = not dc["man"]
        two_high = dc["two_high"]
        coverage = dc["cov"]
        if self.diagrams:
            self.cur_diag = {"form": form_name, "play": play["name"], "pers": pers,
                             "mirror": random.random() < 0.5,
                             "routes": {s: route_of.get(p.id, "block") for s, p in slot_of.items()},
                             "names": {s: (p.jersey, _short(p.name)) for s, p in slot_of.items()},
                             "cov": coverage, "front": dc["front"], "blitz": blitz, "dcall": dc["name"],
                             "n_lb": len(lbs), "n_cb": len(cbs), "n_s": len(ss), "pa": pa}
        # Pre-snap motion: the man in motion beats a press jam and shows the quarterback man or zone;
        # a three-high shell bumps its safeties instead of its linebackers and gives less away
        mo = self._motion(off, form_name, slot_of, run=False, play=play)
        mfac = 0.5 if coverage == "Three-High" else 1.0
        disguise = dfn_lib.DISGUISE.get(coverage, 0.0)

        # Targets & coverage: the receivers running routes in this concept
        cands = self._receivers(wrs, tes, rb, fbp, ptype)
        routed = []
        for r, role, prior in cands:
            rt = route_of.get(r.id, "block")
            if rt == "block" or r in keep_in:
                continue
            cls = pb.ROUTES[rt]["cls"]
            adj = 1.7 if cls == ptype else 0.85 if {cls, ptype} <= {"short", "medium"} or \
                {cls, ptype} <= {"medium", "deep"} or {cls, ptype} <= {"screen", "short"} else 0.55
            routed.append((r, role, prior * adj))
        if routed:
            cands = routed
        cov = self._coverage_map(cands, cov_cbs, cov_ss, cov_lbs, zone)
        # Defenses roll safety help toward the most dangerous receiver
        threats = [c for c in cands if c[1] != "RB" and c[1] != "FB"]
        star = max(threats, key=lambda c: c[0].ca)[0] if threats else None
        target = de.dgp.get("bracket_pid")
        marked = next((c[0] for c in threats if c[0].id == target), None)
        if marked is not None:
            star = marked
        p_bracket = de.dgp.get("bracket", 0.5) * (1.25 if two_high else 0.6)
        if coverage == "Cover 7":
            p_bracket = max(p_bracket, 0.9)        # the call is the bracket
        bracket = star is not None and random.random() < p_bracket
        scored = []
        pa_bonus = 0.0
        if pa:
            lb_bite = sum(e(p, "play_recognition") for p in lbs) / max(1, len(lbs))
            pa_bonus = _clip(5.0 - (lb_bite - 65) * 0.12 + (e(qb, "play_action") - 70) * 0.06, 1.0, 9.0)
            if mo is not None and mo["kind"] == "jet":
                pa_bonus *= 1.15                   # the jet fake and the hand-off fake together
            if coverage == "Three-High":
                pa_bonus *= 0.65                   # three deep: nobody is left alone behind the linebackers
            if call.get("trick") == "flea":
                pa_bonus += 9.0
        bust = self._bust
        for r, role, prior in cands:
            d = cov.get(r.id)
            o = self._openness(r, d, ptype, zone, blitz)
            if bust:
                if d is not None and d.id in bust:
                    o += 9.0                     # blown coverage: nobody went with him
                if r.id in bust:
                    o -= 7.0                     # he ran the wrong route
            if bracket:
                o += -9.0 if r is star else 2.5
            if pa:
                o += pa_bonus * (1.0 if ptype in ("medium", "deep") else 0.4)
            if mo is not None:
                if r is mo["man"]:
                    o += (2.0 + _clip((e(d, "press_technique") - 60) * 0.03, 0.0, 1.0)
                          if not zone and d is not None else 0.6) * mfac
                if ptype == "screen" and mo["kind"] in ("jet", "orbit"):
                    o += 1.5 * mfac                # the defense flows with the motion
            if call.get("rpo") and role.startswith(("WR", "TE")):
                o += 4.0          # the conflict defender can't play both
            if role.startswith(("WR", "TE")):
                o += dc["box"] * 1.2                  # an eighth man in the box is one fewer in coverage
            o += dfn_lib.route_edge(coverage, route_of.get(r.id, ""))
            scored.append((r, role, prior, o, d))
            # Every route is a rep: did he get open, did the defender stay on him?
            self.st(r, "routes")
            if o > 4.0:
                self.st(r, "route_wins")
            if d is not None:
                self.st(d, "cov_snaps")
                if o < -4.0:
                    self.st(d, "cov_wins")
        # Pre-snap: a sharp quarterback spots the pressure and sets a hot route
        hot = False
        if blitz:
            spot = _clip((e(qb, "decision_making") - 55) / 60.0 + (e(qb, "awareness") - 60) / 200.0, 0.05, 0.65)
            if random.random() < spot:
                hot = True
                self.st(qb, "audibles")
                scored = [(r, role, pr, o + (3.0 if pb.ROUTES.get(route_of.get(r.id, ""), {}).get("cls")
                                             in ("short", "screen") else 0.0), d)
                          for (r, role, pr, o, d) in scored]

        # The quarterback's progression: first read, second, third... then the checkdown.
        # A disguised coverage muddies what he sees; motion clears it up.
        rd_skill = _clip(((e(qb, "awareness") + e(qb, "progression_reads")) / 2.0 - 55) / 40.0, 0.0, 1.0)
        nm = 1.0 + 0.45 * disguise * (1.0 - rd_skill)
        if mo is not None:
            nm *= 1.0 - self.MOTION_READ[mo["kind"]] * (1.0 - disguise) * mfac
        prog = self._progression(qb, scored, ptype, hot, noise_mult=nm)
        time_req_extra = prog["time"]
        # Protection: every rusher against his blocker(s)
        edge_add = dfn_lib.FRONTS[dc["front"]]["rush"] \
            + (staff_mod.def_calling(de.team) - staff_mod.off_calling(off.team)) * 0.35
        ol_aw = sum(e(p, "awareness") for p in off.ol) / max(1, len(off.ol))
        if sim == "Creeper":
            edge_add += 2.0 - (e(qb, "progression_reads") - 70) * 0.10
        elif sim == "Amoeba":
            # nobody in a stance: the line has to guess which four are coming
            edge_add += 2.5 - (ol_aw - 70) * 0.12 - (e(qb, "awareness") - 70) * 0.04
        elif sim == "Double Mug":
            edge_add += 1.8 - (e(qb, "awareness") - 70) * 0.08
        if dc["name"] in ("Corner Blitz", "Edge Zone Blitz"):
            # pressure from the wide side is the hardest for a back to pick up
            edge_add += 1.0 - (e(qb, "awareness") - 70) * 0.05
        if dc["rush"] == 3:
            edge_add -= 6.0
        stunt = 0.0
        if dc["stunt"]:
            # Line games: a sharp, experienced line passes them off; a green one gives up a free rusher
            stunt = 1.5 - (ol_aw - 70) * 0.18 + random.gauss(0, 3.0)
        time_req = {"screen": -1.3, "short": -0.40, "medium": 0.18, "deep": 0.48,
                    "hail": 0.6}[ptype]
        if pa:
            time_req += 0.30 if not call.get("trick") else 0.55
        if call.get("rpo"):
            time_req -= 0.6
        # The quarterback's clock: quick processors get the ball out before the rush arrives;
        # every extra read (and holding the ball) gives the rush more time
        time_req += (70 - e(qb, "decision_making")) / 250.0 + time_req_extra
        if hot:
            time_req -= 0.30
        rlist = [(p, kinds.get(p.id, "blitz")) for p, _ in rushers]
        prot = trenches.assign_protection(off.ol, keep_in, rlist, pos=self._pos)
        if self._bust:
            # a blocker who blew his assignment leaves his man free (a double-team partner may still be there)
            for x in prot:
                if x["blockers"] and x["blockers"][0].id in self._bust:
                    x["blockers"] = x["blockers"][1:]
                    x["chip"] = False
        probs = trenches.contest_pass(e, prot, PASS_RUSH_BASE, time_req, stunt=stunt)
        probs = [(_sig(math.log(max(1e-6, p) / max(1e-6, 1 - p)) + edge_add / 15.0), mg + edge_add)
                 for p, mg in probs]
        # Offenses scheme help toward a rusher who is wrecking games this season
        adj = []
        for x, (pp, mg) in zip(prot, probs):
            ss_ = x["rusher"].season_stats
            gp_ = ss_.get("gp", 0)
            if gp_ >= 4:
                spg = ss_.get("sacks", 0) / gp_
                pp = pp / (1.0 + max(0.0, spg - 0.55) * 0.9)
            adj.append((pp, mg))
        probs = adj
        win_m, all_wins = trenches.resolve_pass_rush(e, prot, probs)
        pressured = win_m is not None
        self._prot_record(prot, all_wins, win_m)
        self._rush_winner = win_m

        # Sack / scramble / throwaway under pressure
        if pressured:
            self._adv["pressured"] = True
            escape = e(qb, "pocket_presence") * 0.5 + e(qb, "agility") * 0.25 \
                + e(qb, "speed") * 0.25
            p_sack = _clip(0.275 - (escape - 62) / 210.0, 0.07, 0.46) * self.sack_mult * self.rx["sack"]
            if random.random() < p_sack:
                return self._sack(qb, rushers)
            mob = (e(qb, "speed") - 60) / 75.0
            hit_rusher = win_m["rusher"]
            self.st(hit_rusher, "pressures")
            if random.random() < _clip(mob * 0.65, 0.03, 0.50) and not hail:
                self._adv["scramble"] = True
                if self.cur_diag is not None:
                    self.cur_diag.update(run="scramble", carrier="QB", dir=random.choice([-1, 1]))
                return self._qb_run(qb, scramble=True)
            if random.random() < 0.38:
                self.st(hit_rusher, "qb_hits")
                self._charge_block(win_m, "hits_allowed")
            if random.random() < 0.20 and not hail:
                self.st(qb, "pass_att")
                self.st(qb, "throwaways")
                self.ts(off, "pass_att")
                return {"kind": "pass", "yards": 0, "clock_runs": False, "time": 5,
                        "text": f"{_short(qb.name)} under pressure, throws it away"}

        tgt = prog["target"]
        if prog["kind"] == "throwaway" and not hail:
            self.st(qb, "pass_att")
            self.st(qb, "throwaways")
            self.ts(off, "pass_att")
            return {"kind": "pass", "yards": 0, "clock_runs": False, "time": 6,
                    "text": f"{_short(qb.name)} finds nobody open and throws it away"}
        if pressured and prog["reads"] >= 2:
            # the rush arrives mid-progression: dump it to the outlet if there is one
            outlet = [s_ for s_ in scored if s_[1] in ("RB", "TE1", "FB") and s_[0] is not tgt[0]]
            if outlet and random.random() < 0.45:
                tgt = max(outlet, key=lambda s_: s_[3] + random.gauss(0, 6))
                prog["kind"] = "checkdown"
        rec, role, _, openness, dfnd = tgt
        if prog["kind"] == "checkdown" and ptype in ("medium", "deep"):
            openness = max(openness, 2.0)
            ptype = "short"
        if prog["kind"] == "checkdown":
            self.st(qb, "checkdowns")
        if openness < -2.0:
            self.st(qb, "tight_windows")            # threw into coverage
        self.st(qb, "ttt", prog["ttt"])
        self.st(qb, "ttt_n")

        # Air yards
        if ptype == "screen":
            air = int(round(random.gauss(-1.5, 1.5)))
        elif ptype == "short":
            air = random.choice([1, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 8, 9])
        elif ptype == "medium":
            air = random.randint(10, 19)
        elif ptype == "deep":
            air = 20 + int(random.expovariate(1 / 8.5))
            arm = e(qb, "throw_power")
            air = min(air, int(36 + (arm - 60) * 0.55) + random.randint(0, 6))
        else:
            air = min(to_goal, random.randint(45, 60))
        rt = route_of.get(rec.id)
        if rt and pb.ROUTES[rt]["cls"] == ptype and ptype in ("screen", "short", "medium", "deep"):
            lo, hi = {"screen": (-3, 1), "short": (0, 9), "medium": (10, 19), "deep": (20, 48)}[ptype]
            sd = {"screen": 1.0, "short": 1.6, "medium": 2.2, "deep": 4.5}[ptype]
            air = int(round(_clip(pb.ROUTES[rt]["depth"] + random.gauss(0, sd), lo, hi)))
            if ptype == "deep":
                arm = e(qb, "throw_power")
                air = min(air, int(36 + (arm - 60) * 0.55) + random.randint(0, 6))
        air = min(air, to_goal)
        self._adv.update(rec=rec, air=air, dfnd=dfnd)
        if self.cur_diag is not None:
            slot = next((s for s, p in slot_of.items() if p is rec), None)
            self.cur_diag["target"] = slot
            self.cur_diag["air"] = air

        # Completion
        if ptype == "screen":
            acc = e(qb, "screen_accuracy")
        elif ptype == "short":
            acc = e(qb, "short_accuracy")
        elif ptype == "medium":
            acc = e(qb, "medium_accuracy") * 0.8 + e(qb, "touch") * 0.2
        else:
            acc = e(qb, "deep_accuracy") * 0.65 + e(qb, "throw_power") * 0.2 + e(qb, "touch") * 0.15
        acc += self.wx["acc"] + (self.wx["deep_acc"] if ptype in ("deep", "hail") else
                                 self.wx["deep_acc"] * 0.4 if ptype == "medium" else 0.0)
        base = {"screen": 0.75, "short": 0.655, "medium": 0.515, "deep": 0.355,
                "hail": 0.06}[ptype]
        catch = e(rec, "catching")
        if ptype in ("medium", "deep") or openness < -5:
            catch = catch * 0.5 + e(rec, "catch_in_traffic") * 0.22 \
                + e(rec, "spectacular_catch") * 0.13 + e(rec, "jumping") * 0.15
            if dfnd is not None and ptype in ("medium", "deep"):
                # Winning at the catch point: height of the jump vs the defender's
                catch += (e(rec, "jumping") - e(dfnd, "jumping")) * 0.06
        catch += self.wx["catch"]
        p_comp = base + 0.078 + (acc - 77) / 100.0 * 0.30 + openness / 100.0 * 0.46 \
            + (catch - 75) / 100.0 * 0.13
        if dfnd is not None and openness < 4:
            p_comp -= (e(dfnd, "pass_breakup") - 60) / 100.0 * 0.05
        if pressured:
            tup = e(qb, "throw_under_pressure")
            p_comp -= 0.19 * (1.25 - tup / 100.0)
        if to_goal <= 20 and ptype != "hail":
            p_comp -= 0.05 if to_goal > 10 else (0.16 if to_goal > 3 else 0.12)
        if hail:
            p_comp = 0.06
        ex = SCHEME_EXECUTION.get(off.team.coach.off_scheme)
        if ex and ptype in ("short", "screen"):
            p_comp += ex["short_comp"]
        p_comp = _clip(p_comp * self.comp_mult, 0.04, 0.94)

        # Interception
        int_base = {"screen": 0.005, "short": 0.018, "medium": 0.038, "deep": 0.068,
                    "hail": 0.18}[ptype]
        ball = (e(dfnd, "interception") * 0.6 + e(dfnd, "anticipation") * 0.4) if dfnd else 50
        dec = e(qb, "decision_making")
        p_int = int_base * (1 + (ball - dec) / 80.0) * (1.45 if pressured else 1.0)
        p_int *= (1 + max(0.0, -openness) / 35.0) * self.to_rate
        p_int = _clip(p_int, 0.002, 0.30)

        self.st(qb, "pass_att")
        self.ts(off, "pass_att")
        self.st(rec, "targets")
        r = random.random()
        if r < p_int:
            return self._interception(qb, rec, dfnd, cbs + ss + lbs, air, ptype)
        if r < p_int + p_comp:
            out = self._completion(qb, rec, dfnd, air, ptype, lbs + ss + cbs, pressured)
            if (pa or call) and "text" in out and out["kind"] == "pass":
                out["text"] = out["text"].replace(" pass ", " pass " + self._call_label(call, pa), 1)
            return out
        # Incomplete
        why = "incomplete"
        if random.random() < _clip(0.16 + (60 - catch) / 150.0, 0.04, 0.30) and openness > -6:
            self.st(rec, "drops")
            why = "DROPPED"
        elif dfnd and random.random() < _clip(0.22 + e(dfnd, "pass_breakup") / 250.0, 0.2, 0.62):
            self.st(dfnd, "pd")
            why = f"broken up by {_short(dfnd.name)}"
        depth = {"screen": "screen", "short": "short", "medium": "", "deep": "deep",
                 "hail": "Hail Mary"}[ptype]
        depth = self._call_label(call, pa) + depth
        side = random.choice(["left", "middle", "right"])
        out = {"kind": "pass", "yards": 0, "clock_runs": False, "time": 6,
               "text": f"{_short(qb.name)} pass {depth} {side} to {_short(rec.name)} {why}".replace("  ", " "),
               "air": air, "ptype": ptype, "incomplete": True, "def": dfnd}
        return out

    def _qb_aggression(self, qb):
        """0 = careful game manager .. 1 = gunslinger (derived from personality and arm)."""
        h = qb.hidden
        return _clip(0.35 + (h.get("ambition", 50) - 50) / 160.0 + (50 - h.get("temperament", 50)) / 220.0
                     + (qb.a("throw_power") - 80) / 120.0 + (60 - qb.a("decision_making")) / 260.0, 0.0, 1.0)

    def _progression(self, qb, scored, ptype, hot=False, noise_mult=1.0):
        """
        Work the reads in order. The concept decides the order (primary first); the
        quarterback sees how open each man is (better processors see it more
        clearly), throws when he likes what he sees, and otherwise moves on — to
        the checkdown, or he holds it, or he throws it away. Gunslingers throw
        into tighter windows; careful quarterbacks take the checkdown.
        """
        e = self.e
        reads = e(qb, "progression_reads")
        dm = e(qb, "decision_making")
        aggr = self._qb_aggression(qb)
        noise = _clip(8.0 - (dm - 60) / 6.0, 2.5, 11.0) * noise_mult
        max_reads = 2 + (reads >= 68) + (reads >= 82)
        order = sorted(scored, key=lambda s_: -(s_[2] * random.lognormvariate(0, 0.35)))
        if hot:
            order.sort(key=lambda s_: 0 if s_[1] in ("RB", "TE1", "FB") or s_[3] > 3 else 1)
        outlets = [s_ for s_ in scored if s_[1] in ("RB", "FB")] or \
            [s_ for s_ in scored if s_[1] == "TE1"]
        base_t = {"screen": 1.7, "short": 2.3, "medium": 2.75, "deep": 3.1, "hail": 3.4}[ptype]
        for k, cand in enumerate(order[:max_reads]):
            seen = cand[3] + random.gauss(0, noise)
            thr = 2.0 - 7.0 * aggr - 2.5 * k
            if seen >= thr:
                return {"target": cand, "reads": k + 1, "kind": "read", "time": 0.10 * k,
                        "ttt": base_t + 0.45 * k}
        k = min(max_reads, len(order))
        # Nobody he liked: checkdown, hold it and hope, force it, or throw it away
        if outlets and random.random() < 0.55 + 0.35 * (1 - aggr):
            out = max(outlets, key=lambda s_: s_[3] + random.gauss(0, noise))
            return {"target": out, "reads": k + 1, "kind": "checkdown", "time": 0.10 * k,
                    "ttt": base_t + 0.45 * k}
        best = max(order, key=lambda s_: s_[3] + random.gauss(0, noise))
        if random.random() < 0.15 + (dm - 50) / 90.0 * (1 - aggr) and ptype != "hail":
            return {"target": best, "reads": k + 1, "kind": "throwaway", "time": 0.16 * k + 0.25,
                    "ttt": base_t + 0.45 * k + 0.5}
        return {"target": best, "reads": k + 1, "kind": "force", "time": 0.16 * k + 0.35,
                "ttt": base_t + 0.45 * k + 0.7}

    def _receivers(self, wrs, tes, rb, fbp, ptype):
        out = []
        roles = ["WR1", "WR2", "WR3", "WR4"]
        prior_wr = [1.0, 0.90, 0.74, 0.52]
        def busy(p):
            line = self.res.player_stats.get(p.id)
            tg = line["targets"] if line else 0
            f = 1.0 / (1.0 + max(0, tg - 9) * 0.10)
            ss = p.season_stats
            if ss.get("gp", 0) >= 4:
                tpg = ss.get("targets", 0) / ss["gp"]
                f /= 1.0 + max(0.0, tpg - 8.5) * 0.26     # defenses scheme against a volume star
            return f
        tw = self.poss.ogp["targets"]
        for i, w in enumerate(wrs):
            pr = prior_wr[i] * (0.55 + 0.45 * w.rating_at("WR") / 130.0) * busy(w) * tw.get(w.id, 1.0)
            if ptype == "screen":
                pr *= 0.6
            out.append((w, roles[i], pr))
        for i, t in enumerate(tes):
            pr = (0.94 if i == 0 else 0.40 if i == 1 else 0.18) * (0.55 + 0.45 * t.rating_at("TE") / 130.0) \
                * busy(t)
            if ptype == "deep":
                pr *= 0.55
            out.append((t, "TE1" if i == 0 else "TE2", pr))
        if rb:
            pr = 1.85 * (0.45 + 0.55 * rb.a("catching") / 65.0) * busy(rb)
            if ptype == "screen":
                pr *= 2.6
            elif ptype == "medium":
                pr *= 0.35
            elif ptype in ("deep", "hail"):
                pr *= 0.08
            out.append((rb, "RB", pr))
        if fbp:
            if getattr(self, "_pers", None) == "20":
                # a second running back: a real outlet, less than the first
                pr = 0.9 * (0.45 + 0.55 * fbp.a("catching") / 65.0) * busy(fbp)
                pr *= 2.0 if ptype == "screen" else 0.35 if ptype == "medium" else 0.08 \
                    if ptype in ("deep", "hail") else 1.0
                out.append((fbp, "FB", pr))
            else:
                out.append((fbp, "FB", 0.15 if ptype in ("short", "screen") else 0.03))
        return out

    def _coverage_map(self, cands, cbs, ss, lbs, zone):
        cov = {}
        if len(cbs) >= 2 and (zone or not self.dfn.dgp.get("shadow", True)) and random.random() < 0.5:
            cbs = [cbs[1], cbs[0]] + list(cbs[2:])     # corners play sides, not the man
        cb_i = 0
        pool_s = list(ss)
        pool_lb = list(lbs)
        for r, role, _ in cands:
            if role.startswith("WR"):
                if cb_i < len(cbs):
                    cov[r.id] = cbs[cb_i]
                    cb_i += 1
                elif pool_s:
                    cov[r.id] = pool_s.pop()
                elif pool_lb:
                    cov[r.id] = pool_lb.pop()
        for r, role, _ in cands:
            if r.id in cov:
                continue
            if r.position in ("WR", "CB") and not role.startswith("WR") and pool_s:
                cov[r.id] = pool_s.pop(0)              # a receiver lined up in the backfield draws a safety
            elif role.startswith("TE"):
                if pool_s and random.random() < 0.5:
                    cov[r.id] = pool_s.pop(0)
                elif pool_lb:
                    cov[r.id] = pool_lb.pop(0)
                elif pool_s:
                    cov[r.id] = pool_s.pop(0)
            else:
                if pool_lb:
                    cov[r.id] = pool_lb.pop(0)
                elif pool_s:
                    cov[r.id] = pool_s.pop(0)
        return cov

    def _openness(self, r, d, ptype, zone, blitz):
        e = self.e
        if ptype == "screen":
            route = e(r, "agility") * 0.3 + e(r, "acceleration") * 0.3 + e(r, "catching") * 0.4
        elif ptype == "short":
            route = e(r, "short_route_running") * 0.45 + e(r, "separation") * 0.2 \
                + e(r, "agility") * 0.2 + e(r, "release") * 0.15
        elif ptype == "medium":
            route = e(r, "medium_route_running") * 0.45 + e(r, "separation") * 0.2 \
                + e(r, "speed") * 0.15 + e(r, "release") * 0.2
        else:
            route = e(r, "deep_route_running") * 0.35 + e(r, "speed") * 0.35 \
                + e(r, "separation") * 0.15 + e(r, "release") * 0.15
        if d is None:
            cover = 35.0
        elif zone:
            cover = e(d, "zone_coverage") * 0.55 + e(d, "anticipation") * 0.2 \
                + e(d, "play_recognition") * 0.1 + e(d, "speed") * 0.15
        else:
            cover = e(d, "man_coverage") * 0.55 + e(d, "press_technique") * 0.1 * (1 + self.rx["press"]) \
                + e(d, "speed") * 0.15 + e(d, "agility") * 0.1 + e(d, "anticipation") * 0.1
        if ptype == "deep" and d is not None:
            cover += (e(d, "speed") - e(r, "speed")) * 0.25
        o = (route - cover) * 0.72 + (4.0 if blitz else 0.0) + random.gauss(0, 9.0) + self.rx["openness"]
        if ptype == "screen":
            o += 6
        return o

    def _completion(self, qb, rec, dfnd, air, ptype, tacklers, pressured):
        e = self.e
        off = self.poss
        to_goal = 100 - self.yl
        yac_mean = {"screen": 5.5, "short": 3.45, "medium": 2.75, "deep": 3.0, "hail": 1.0}[ptype]
        ex = SCHEME_EXECUTION.get(off.team.coach.off_scheme)
        if ex and ptype in ("short", "screen"):
            yac_mean *= ex["short_yac"]
        skill = e(rec, "speed") * 0.28 + e(rec, "agility") * 0.22 + e(rec, "break_tackle") * 0.18 \
            + e(rec, "acceleration") * 0.17 + e(rec, "vision") * 0.15
        tk = sum(e(t, "tackling") * 0.6 + e(t, "pursuit") * 0.4 for t in tacklers[:5]) \
            / max(1, min(5, len(tacklers)))
        m = max(0.8, yac_mean * (1 + (skill - tk) / 135.0))
        yac = int(random.expovariate(1.0 / m))
        brk = (0.016 + (e(rec, "speed") - 85) / 900.0 + (skill - tk) / 2000.0) * self.big_play
        if ptype in ("screen", "short") and random.random() < max(0.004, brk):
            yac += 10 + int(random.expovariate(1 / 18.0))
        elif ptype in ("medium", "deep") and random.random() < max(0.004, brk * 1.3):
            yac += 8 + int(random.expovariate(1 / 20.0))
        yards = air + yac
        if self.yl + yards >= 100:
            yards = to_goal
            yac = max(0, yards - air)
        if self.yl + yards <= 0:
            yards = -self.yl + 1
        self.st(qb, "pass_cmp")
        self.st(qb, "pass_yds", yards)
        self.st(qb, "pass_long", yards)
        self.st(rec, "rec")
        self.st(rec, "rec_yds", yards)
        self.st(rec, "rec_long", yards)
        self.st(rec, "yac", yac)
        if yards >= 20:
            self.st(rec, "rec_20")
        self.ts(off, "pass_cmp")
        self.ts(off, "pass_yds", yards)
        td = self.yl + yards >= 100
        side = random.choice(["left", "middle", "right"])
        depth = {"screen": "screen", "short": "short", "medium": "", "deep": "deep",
                 "hail": "Hail Mary"}[ptype]
        text = f"{_short(qb.name)} pass {depth} {side} to {_short(rec.name)}".replace("  ", " ")
        out = {"kind": "pass", "yards": yards, "time": random.uniform(5, 7.5),
               "clock_runs": True, "text": text, "carrier": rec, "td": td,
               "complete": True, "qb": qb, "ptype": ptype, "air": air}
        if td:
            self.st(qb, "pass_td")
            self.st(rec, "rec_td")
            out["text"] += f" for {yards} yards, TOUCHDOWN"
            return out
        mode = self.urgency(off)
        out["oob"] = random.random() < ((0.26 if ptype != "screen" else 0.12) +
                                        (0.25 if mode == "hurry" else 0.0)) * (0.3 if mode == "milk" else 1.0)
        # Tackle & fumble
        tackler = dfnd if (dfnd and random.random() < 0.55) else random.choice(tacklers[:6]) \
            if tacklers else None
        self._missed(tacklers, yac)
        if not out["oob"]:
            self._tackle(tackler, tacklers)
        out["text"] += f" for {yards} yard{'s' if abs(yards) != 1 else ''}"
        hit = (1.0 + (e(tackler, "hit_power") - 60) / 120.0) if tackler is not None else 1.0
        if random.random() < 0.0075 * (1.5 - e(rec, "ball_security") / 100.0) * self.to_rate \
                * self.wx["fumble"] * hit:
            return self._fumble(out, rec, tackler)
        return out

    def _interception(self, qb, rec, dfnd, defenders, air, ptype):
        e = self.e
        picker = dfnd if dfnd and random.random() < 0.65 else random.choice(defenders[:6])
        self.st(qb, "pass_int")
        self.st(picker, "def_int")
        self.st(picker, "pd")
        self.ts(self.poss, "turnovers")
        spot = _clip(self.yl + air, 1, 99)           # offence yard line
        ret = max(0, int(random.gauss(7 + (e(picker, "speed") - 75) * 0.2, 9)))
        if random.random() < 0.055 * self.big_play:
            ret = spot
        self.st(picker, "int_yds", min(ret, spot))
        new_yl = (100 - spot) + ret
        text = f"{_short(qb.name)} pass intended for {_short(rec.name)} INTERCEPTED by " \
               f"{_short(picker.name)}"
        if new_yl >= 100:
            self.st(picker, "int_td")
            self.st(picker, "def_td")
            return {"kind": "pick6", "text": text + f", returned {spot} yards for a TOUCHDOWN",
                    "time": 7, "clock_runs": False, "scorer": picker}
        return {"kind": "turnover", "text": text + f" at the {self.spot(spot)}, returned {ret} yards",
                "new_yl": new_yl, "time": 7, "clock_runs": False, "what": "Interception"}

    def _fumble(self, out, carrier, forcer):
        self.st(carrier, "fumbles")
        if forcer:
            self.st(forcer, "ff")
        if random.random() < 0.52:
            self.st(carrier, "fumbles_lost")
            self.ts(self.poss, "turnovers")
            rec_by = random.choice(self.dfn.lu["LB"][:2] + self.dfn.lu["S"][:2] +
                                   self.dfn.lu["DT"][:2])
            self.st(rec_by, "fr")
            spot = _clip(self.yl + out.get("yards", 0), 1, 99)
            if random.random() < 0.05 * self.big_play:
                self.st(rec_by, "def_td")
                return {"kind": "pick6", "time": 6, "clock_runs": False, "scorer": rec_by,
                        "text": out["text"] + f" — FUMBLE recovered by {_short(rec_by.name)} "
                                              f"and returned for a TOUCHDOWN",
                        "pre_yards": out.get("yards", 0), "carrier_stats_done": True}
            return {"kind": "turnover", "time": 6, "clock_runs": False,
                    "new_yl": 100 - spot, "what": "Fumble",
                    "text": out["text"] + f" — FUMBLE, recovered by {_short(rec_by.name)}",
                    "pre_yards": out.get("yards", 0)}
        out["text"] += " (fumbled, recovered by offense)"
        return out

    def _sack(self, qb, rushers):
        win_m = getattr(self, "_rush_winner", None)
        sacker = win_m["rusher"] if win_m else self._weighted_rusher(rushers)
        coverage_sack = random.random() < 0.22
        if not coverage_sack and win_m:
            self._charge_block(win_m, "sacks_allowed")
        if coverage_sack:
            # Coverage sacks, delayed blitzes and clean-up by the second level
            extra = self.dfn.lu["LB"][:2] + self.dfn.lu["S"][:1] + self.dfn.lu["CB"][:1]
            if extra:
                sacker = random.choice(extra)
        loss = random.randint(4, 10)
        loss = min(loss, self.yl - 1) if self.yl > 1 else 0
        if random.random() < 0.12 and len(rushers) > 1:
            other = self._weighted_rusher([r for r in rushers if r[0] is not sacker])
            self.st(sacker, "sacks", 0.5)
            self.st(other, "sacks", 0.5)
            self.st(sacker, "tkl_ast")
            self.st(other, "tkl_ast")
            who = f"{_short(sacker.name)} and {_short(other.name)}"
        else:
            self.st(sacker, "sacks", 1)
            self.st(sacker, "tkl_solo")
            who = _short(sacker.name)
        self.st(sacker, "tfl")
        self.st(sacker, "qb_hits")
        self.st(sacker, "pressures")
        self.st(qb, "sacked")
        self.st(qb, "sack_yds", loss)
        self.ts(self.poss, "sacked")
        self.ts(self.poss, "sack_yds", loss)
        beat = ""
        if not coverage_sack and win_m and win_m["blockers"]:
            b = win_m["blockers"][0]
            beat = f" (beat {self._pos(b)} {_short(b.name)})"
        elif not coverage_sack and win_m and not win_m["blockers"]:
            beat = " (unblocked)"
        out = {"kind": "sack", "yards": -loss, "time": 6, "clock_runs": True,
               "text": f"{_short(qb.name)} SACKED by {who} for -{loss}{beat}"}
        if random.random() < 0.095 * (1.4 - self.e(qb, "ball_security") / 100.0) * self.to_rate:
            out["text"] = f"{_short(qb.name)} SACKED by {who}"
            return self._fumble(out, qb, sacker)
        if self.yl - loss <= 0:
            out["safety"] = True
        return out

    def _prot_record(self, prot, winners, first):
        """Pass-protection bookkeeping: snaps, wins, double teams, pressures allowed."""
        won = {id(x) for x in winners}
        for x in prot:
            r = x["rusher"]
            self.st(r, "pr_snaps")
            if id(x) in won:
                self.st(r, "pr_wins")
            if len(x["blockers"]) > 1:
                self.st(r, "double_teamed")
            for b in x["blockers"] + x.get("chippers", []):
                self.st(b, "pb_snaps")
        if first is not None:
            self._charge_block(first, "pressures_allowed")

    def _track_form(self, side, pers, form):
        """Personnel and shotgun usage (for scouting reports and scheme profiles)."""
        ts = self.res.team_stats[side.abbr]
        ts[f"pers|{pers}"] += 1
        if pb.FORMATIONS.get(form, {}).get("qb", -1) <= -4:
            ts["gun_snaps"] += 1

    def _record_run_blocks(self, events, yards):
        for b, d, margin, poa in events:
            if b is not None:
                self.st(b, "rb_snaps")
                if margin > 0:
                    self.st(b, "rb_wins")
                    if margin > 0.85 and yards >= 4 and random.random() < 0.5:
                        self.st(b, "pancakes")
            self.st(d, "rd_snaps")
            if margin < -0.25:
                self.st(d, "rd_wins")

    def _charge_block(self, m, key):
        if m and m["blockers"]:
            self.st(m["blockers"][0], key)

    def _weighted_rusher(self, rushers):
        ws = [max(5.0, max(self.e(p, "power_move"), self.e(p, "finesse_move")) + 100) * w
              for p, w in rushers]
        return random.choices([p for p, _ in rushers], weights=ws, k=1)[0]

    # ── Run play ─────────────────────────────────────────────────────────────

    # Run concepts: (blocking weights, bd bonus fn, yards sd mult, stuff add, big-play mult)
    RUN_BLOCK = {
        "inside zone":  {"run_block": 0.45, "impact_block": 0.20, "strength": 0.20, "awareness": 0.15},
        "power":        {"run_block": 0.40, "pulling": 0.25, "strength": 0.25, "impact_block": 0.10},
        "counter":      {"run_block": 0.35, "pulling": 0.35, "agility": 0.15, "awareness": 0.15},
        "draw":         {"pass_block": 0.35, "run_block": 0.35, "awareness": 0.30},
        "outside zone": {"run_block": 0.40, "pulling": 0.10, "agility": 0.30, "awareness": 0.20},
        "toss":         {"run_block": 0.30, "agility": 0.35, "pulling": 0.20, "awareness": 0.15},
        "jet sweep":    {"run_block": 0.30, "agility": 0.35, "pulling": 0.20, "awareness": 0.15},
        "reverse":      {"run_block": 0.30, "agility": 0.35, "pulling": 0.20, "awareness": 0.15},
    }
    RUN_BLOCK.update({
        "trap":          {"run_block": 0.35, "pulling": 0.30, "impact_block": 0.20, "awareness": 0.15},
        "lead":          {"run_block": 0.45, "impact_block": 0.25, "strength": 0.30},
        "buck sweep":    {"run_block": 0.30, "pulling": 0.40, "agility": 0.15, "awareness": 0.15},
        "zone read":     {"run_block": 0.45, "impact_block": 0.15, "strength": 0.15, "awareness": 0.25},
        "inverted veer": {"run_block": 0.35, "pulling": 0.30, "strength": 0.15, "awareness": 0.20},
        "triple option": {"run_block": 0.40, "agility": 0.25, "awareness": 0.35},
        "midline":       {"run_block": 0.40, "strength": 0.25, "impact_block": 0.15, "awareness": 0.20},
        "speed option":  {"run_block": 0.35, "agility": 0.35, "awareness": 0.30},
    })
    RUN_BLOCK.update({
        "duo":           {"run_block": 0.40, "strength": 0.30, "impact_block": 0.20, "awareness": 0.10},
        "split zone":    {"run_block": 0.45, "agility": 0.10, "strength": 0.15, "awareness": 0.30},
        "pin and pull":  {"run_block": 0.30, "pulling": 0.35, "agility": 0.25, "awareness": 0.10},
        "qb counter":    {"run_block": 0.35, "pulling": 0.35, "agility": 0.15, "awareness": 0.15},
        "qb power":      {"run_block": 0.40, "pulling": 0.25, "strength": 0.25, "impact_block": 0.10},
        "crack toss":    {"run_block": 0.30, "agility": 0.35, "pulling": 0.25, "awareness": 0.10},
        "wildcat":       {"run_block": 0.40, "pulling": 0.20, "strength": 0.25, "awareness": 0.15},
    })
    OUTSIDE = ("outside zone", "toss", "jet sweep", "reverse", "buck sweep", "speed option", "pin and pull",
               "crack toss")
    OPTION = ("zone read", "inverted veer", "triple option", "midline", "speed option")
    QB_DESIGNED = ("qb counter", "qb power")
    # How much each kind of motion sharpens the quarterback's pre-snap read (less read noise)
    MOTION_READ = {"jet": 0.12, "orbit": 0.12, "across": 0.18, "shift": 0.10}

    def _motion(self, side, form, slot_of, run, play=None, force=None):
        """Pre-snap motion on this snap: {"kind", "slot", "man"}, or None."""
        want = force or (play or {}).get("motion")
        kind = slot = None
        if want and want.get("slot") in slot_of:
            kind, slot = want["kind"], want["slot"]
        else:
            p = pb.motion_share(side.plan.get("motion", 0.5))
            if self.urgency(side) == "hurry":
                p *= 0.3                          # two-minute drill: no time to move people around
            elif self.no_huddle:
                p *= 0.6
            if random.random() < p:
                kind, slot = pb.choose_motion(side.team.coach.off_scheme, run, form, tuple(slot_of))
        if kind is None:
            return None
        man = slot_of[slot]
        self._set_energy(man, self.energy_of(man) - 0.2)
        self._motion_kind = kind
        self.ts(side, "motion_snaps")
        if self.cur_diag is not None:
            self.cur_diag["motion"] = {"slot": slot, "kind": kind}
        return {"kind": kind, "slot": slot, "man": man}

    def _call_label(self, call, pa):
        if call.get("trick") == "flea":
            return "flea-flicker "
        if call.get("rpo"):
            return "RPO "
        return "play-action " if pa else ""

    def _run_concept(self, plan, dplan, wrs, scheme=None, qb=None, fbp=None, tes=()):
        to_goal = 100 - self.yl
        short = self.togo <= 2 or to_goal <= 3
        out = plan["outside"]
        mob = _clip((self.e(qb, "speed") - 66) / 22.0, 0.0, 1.4) if qb is not None else 0.5
        w = {
            "trap": 0.10,
            "lead": 0.04 + (0.45 if fbp is not None else 0.0) * (0.5 + plan["heavy"]),
            "zone read": (0.03 + 0.55 * plan["qb_run"]) * mob,
            "inverted veer": (0.01 + 0.20 * plan["qb_run"]) * mob,
            "speed option": (0.005 + 0.08 * plan["qb_run"]) * mob,
        }
        w.update({
            "inside zone": 1.0 + 0.6 * (1.0 - out),
            "outside zone": 0.30 + 1.10 * out,
            "power": 0.25 + 0.70 * plan["heavy"] + (0.8 if short else 0.0),
            "counter": 0.15 + 0.25 * plan["trick"],
            "draw": 0.06 + (0.55 if self.down >= 2 and self.togo >= 7 else 0.0)
            + (0.6 * sit_tendency(self.poss.team.coach, "sit_long") if self.down >= 3 and self.togo >= 9 else 0.0)
            + 0.25 * max(0.0, plan["pass_rate"] - 0.5),
            "toss": 0.06 + 0.25 * out,
            "duo": 0.10 + 0.20 * plan["heavy"],
            "pin and pull": 0.04 + 0.12 * out,
            "qb counter": (0.004 + 0.10 * plan["qb_run"]) * mob,
            "qb power": (0.004 + 0.07 * plan["qb_run"]) * mob,
        })
        if fbp is not None or tes:
            w["split zone"] = 0.08 + 0.25 * out      # needs a tight end or fullback to come across
        if len(wrs) >= 2:
            w["crack toss"] = 0.03 + 0.05 * out      # needs receivers to crack down
        for k, add in pb.SCHEME_RUNS.get(scheme, {}).items():
            if (k in self.OPTION and k not in ("triple option", "midline")) or k in self.QB_DESIGNED:
                add *= max(0.25, mob)
            w[k] = max(0.02 if k in w else 0.0, w.get(k, 0.0) + add)
        prefs = self.poss.prefs
        if prefs:
            for k in list(w):
                w[k] *= prefs.get("run:" + k, 1.0)
        fast = max(wrs, key=lambda p: p.a("speed")) if wrs else None
        if fast is not None and fast.a("speed") >= 86 and not short:
            w["jet sweep"] = 0.015 + 0.06 * out * (0.5 + plan["trick"])
        if fast is not None:
            w["wildcat"] = (0.003 + 0.015 * plan["trick"]) * prefs.get("run:wildcat", 1.0)
        if short:
            for k in ("draw", "speed option", "toss", "buck sweep", "crack toss", "pin and pull"):
                if k in w:
                    w[k] *= 0.4
        if to_goal <= 3:
            gl = {"inside zone": 1.0, "power": 1.4, "toss": 0.15, "lead": 0.5 if fbp is not None else 0.0,
                  "duo": 0.5}
            for k in ("midline", "triple option", "zone read", "trap", "buck sweep", "qb power", "wildcat"):
                if w.get(k, 0) > 0.3:
                    gl[k] = w[k]
            w = gl
        keys = list(w)
        return random.choices(keys, weights=[w[k] for k in keys], k=1)[0], fast

    def run_play(self, call=None):
        call = call or {}
        e = self.e
        off, de = self.poss, self.dfn
        plan = off.plan
        qb = off.qb
        pers = self._personnel()
        wrs, tes, rb, fbp = self._formation(pers)
        dts, edges, lbs, cbs, ss = self._defense_set(pers)
        self._snap_units([qb] + off.ol + wrs + tes + [rb, fbp], dts + edges + lbs + cbs + ss,
                         self._off_slots(off, wrs, tes), self._def_slots(dts, edges, lbs, cbs, ss))
        self.ts(off, "plays")
        slot_of = self._slot_map(pers, wrs, tes, rb, fbp)
        dc = self._def_call(len(cbs), len(ss))
        gun = 0.25 + 0.5 * plan["tempo"] + 0.3 * plan["qb_run"]
        run_form = pb.choose_formation(pers, run=True, gun_bias=min(1.0, gun), scheme=off.team.coach.off_scheme)
        self._track_form(off, pers, run_form)
        if self.diagrams:
            self.cur_diag = {"form": run_form,
                             "pers": pers, "mirror": False, "routes": {},
                             "names": {s: (p.jersey, _short(p.name)) for s, p in slot_of.items()},
                             "cov": dc["cov"], "front": dc["front"], "blitz": dc["blitz"],
                             "dcall": dc["name"], "n_lb": len(lbs), "n_cb": len(cbs), "n_s": len(ss),
                             "dir": random.choice([-1, 1])}

        if not call:
            # Designed QB run?
            qb_mob = (e(qb, "speed") - 65) / 30.0
            if random.random() < plan["qb_run"] * 0.19 * _clip(0.5 + qb_mob, 0.2, 1.6):
                if self.cur_diag is not None:
                    self.cur_diag.update(run="qb run", carrier="QB", play="QB Keeper")
                return self._qb_run(qb, scramble=False, lbs=lbs, ss=ss, dts=dts)
            if self.togo <= 1 and self.down >= 3 and random.random() < 0.35:
                if self.cur_diag is not None:
                    self.cur_diag.update(run="sneak", carrier="QB", play="QB Sneak", dir=1)
                return self._qb_sneak(qb, dts + edges + lbs)

        scheme = off.team.coach.off_scheme
        concept, fast = self._run_concept(plan, de.plan, wrs, scheme=scheme, qb=qb, fbp=fbp, tes=tes)
        self._ocall = concept
        if call.get("concept"):
            concept = call["concept"]
        elif call.get("rpo"):
            concept = "inside zone" if random.random() < 0.65 else "outside zone"
        carrier = rb
        lead_blocker = None
        if concept in ("jet sweep", "reverse"):
            carrier = fast or (wrs[0] if wrs else rb)
        elif concept in self.QB_DESIGNED and qb is not None:
            carrier, lead_blocker = qb, rb      # the back becomes a lead blocker
        elif concept == "split zone":
            lead_blocker = fbp if fbp is not None else (tes[0] if tes else None)   # the kick-out man
        elif concept == "lead" and fbp is not None and random.random() < 0.06:
            carrier = fbp
        elif concept in ("midline", "triple option") and fbp is not None:
            carrier = fbp                       # the fullback / B-back takes the dive
        elif fbp and random.random() < (0.30 if concept in ("trap", "buck sweep") and scheme == "Wing-T"
                                        else 0.10):
            carrier = fbp
        if carrier is None:
            carrier = qb
        outside = concept in self.OUTSIDE
        path_key = concept

        # Option football: the QB reads an unblocked defender and gives, keeps or pitches
        read_edge = 0.0
        option_note = ""
        if concept in self.OPTION and carrier is not qb:
            key = edges[0] if edges else (lbs[0] if lbs else None)
            iq = (e(key, "play_recognition") - 65) / 200.0 if key is not None else 0.0
            sharp = _clip(0.60 + (e(qb, "decision_making") - 62) / 75.0 - iq, 0.45, 0.94)

            def read(take_qb_rate):
                crash = random.random() < take_qb_rate      # key defender takes the give
                if random.random() < sharp:
                    return crash, False
                keep_ = (not crash) and random.random() < 0.5
                return keep_, (crash and not keep_) or (not crash and keep_)

            keep, bad = read(0.32 if concept != "speed option" else 0.55)
            if concept == "zone read":
                if keep:
                    carrier, outside, path_key = qb, True, "keep"
            elif concept == "inverted veer":
                if keep:
                    carrier, outside, path_key = qb, False, "veer keep"
                else:
                    outside = True
            elif concept == "midline":
                if keep:
                    carrier, path_key = qb, "veer keep"
            elif concept == "speed option":
                if keep:
                    carrier, outside, path_key = qb, False, "veer keep"
                else:
                    path_key = "pitch"
            elif concept == "triple option":
                if keep:
                    # second read: the pitch key
                    pitch, bad2 = read(0.5)
                    bad = bad and bad2
                    if pitch:
                        pitch_man = fast or rb
                        if pitch_man is carrier:
                            pitch_man = rb if rb is not carrier else None
                        if pitch_man is not None:
                            carrier, outside, path_key = pitch_man, True, "pitch"
                        else:
                            carrier, outside, path_key = qb, True, "keep"
                    else:
                        carrier, outside, path_key = qb, True, "keep"
                else:
                    path_key = "dive"
            read_edge = -0.35 if bad else 0.40
            option_note = {True: " (keep)", False: ""}[carrier is qb]
            if path_key == "pitch":
                option_note = " (pitch)"
        elif concept == "wildcat" and carrier is not qb:
            # Direct snap to the back: he reads the end and keeps it or gives to the jet man
            crash = random.random() < 0.45
            smart = random.random() < _clip(0.55 + (e(carrier, "awareness") - 60) / 90.0, 0.4, 0.9)
            give = crash if smart else not crash
            if give and fast is not None and fast is not carrier:
                carrier, outside, path_key = fast, True, "jet sweep"
                option_note = " (jet give)"
            read_edge = 0.30 if smart else -0.30
        # Pre-snap motion (a jet sweep or a wildcat needs the jet man moving)
        force = None
        if concept in ("jet sweep", "wildcat") and fast is not None:
            fslot = next((s_ for s_, p in slot_of.items() if p is fast), None)
            if fslot is not None:
                force = {"kind": "jet", "slot": fslot}
        mo = self._motion(off, run_form, slot_of, run=True, force=force)
        if self.cur_diag is not None:
            cslot = next((s for s, p in slot_of.items() if p is carrier), "QB")
            self.cur_diag.update(run=path_key if path_key in pb.RUN_PATHS else concept, carrier=cslot,
                                 play=("RPO " if call.get("rpo") else "") + concept.title() + option_note)

        # Blocking: one-on-one matchups at the point of attack (and the backside)
        wts = self.RUN_BLOCK[concept]
        front = dts + edges
        lead = fbp if (fbp is not None and carrier is not fbp) else None
        if lead_blocker is not None and lead_blocker is not carrier:
            lead = lead_blocker
        bd, blk_events = trenches.run_matchups(e, off.ol, tes, lead, front, lbs, ss, not outside,
                                               self._run_side, wts, pos=self._pos, bust=self._bust)
        extra = sum((e(t, "run_block") - 55) * 0.05 for t in tes)
        extra += (staff_mod.off_calling(off.team) - 10) * 0.3
        box = {1: -5.0, 2: -2.5, 3: 0.0, 4: 1.5}.get(len(lbs), 0.0)
        box += dfn_lib.run_edge(dc, inside=not outside) + dc["box"] * 1.3
        extra -= box + (staff_mod.def_calling(de.team) - 10) * 0.3
        bd += extra / 28.0 + RUN_BLOCK_SHIFT
        ex = SCHEME_EXECUTION.get(off.team.coach.off_scheme)
        if ex:
            bd += ex["run_edge"]
        self._run_events = blk_events
        if mo is not None:
            lb_rec = sum(e(p, "play_recognition") for p in lbs) / max(1, len(lbs))
            mfac = 0.5 if dc["cov"] == "Three-High" else 1.0
            k = mo["kind"]
            if k == "jet" and concept not in ("jet sweep", "wildcat"):
                # the jet fake holds the backside: somebody has to respect the sweep
                bd += (0.10 + _clip((e(mo["man"], "speed") - 80) / 50.0, 0.0, 0.2)) * mfac \
                    - _clip((lb_rec - 70) * 0.004, -0.05, 0.08)
            elif k == "orbit":
                bd += (0.15 if concept in ("counter", "qb counter", "split zone", "reverse", "trap")
                       else 0.05) * mfac
            elif k == "across":
                bd += (0.08 if self._pos(mo["man"]) in ("TE", "FB") else 0.03) * mfac
            elif k == "shift":
                bd += _clip((70 - lb_rec) * 0.01, -0.05, 0.15) * mfac

        # Concept-specific edges
        sd_mult, stuff_add, big_mult, mean_add = 1.0, 0.0, 1.0, 0.0
        pass_down = self.down >= 2 and self.togo >= 7
        if concept == "power":
            bd += 0.30 if len(lbs) <= 2 else -0.05
            sd_mult, big_mult = 0.85, 0.85
            if self.togo <= 2:
                stuff_add -= 0.03
        elif concept == "counter":
            bd += 0.55 if dc["blitz"] else -0.05
            sd_mult, stuff_add, big_mult = 1.2, 0.02, 1.25
        elif concept == "draw":
            bd += 0.80 if pass_down else -0.55
            if dc["blitz"] or dc["rush"] == 3:
                bd += 0.4
            sd_mult, big_mult = 1.1, 1.1
        elif concept == "outside zone":
            sd_mult, stuff_add, big_mult = 1.12, 0.02, 1.15
        elif concept == "toss":
            sd_mult, stuff_add, big_mult = 1.3, 0.05, 1.40
        elif concept in ("jet sweep", "reverse"):
            sd_mult, stuff_add, big_mult, mean_add = 1.3, 0.04, 1.65, -0.6
            if concept == "reverse":
                stuff_add += 0.10
                big_mult = 2.2
        elif concept == "trap":
            # the trapped defender is invited upfield; aggressive fronts get punished
            bd += 0.05 + (0.50 if dc["blitz"] or dc["stunt"] else 0.0)
            sd_mult, stuff_add, big_mult = 1.05, 0.01, 1.05
        elif concept == "lead":
            bd += 0.15 if fbp is not None else -0.2
            sd_mult, big_mult = 0.85, 0.85
            if self.togo <= 2:
                stuff_add -= 0.02
        elif concept == "buck sweep":
            bd += 0.15
            sd_mult, stuff_add, big_mult = 1.2, 0.03, 1.25
        elif concept == "duo":
            # double teams everywhere: wins against a light two-high box, struggles against a loaded one
            bd += 0.25 if dc["two_high"] else -0.10
            sd_mult, big_mult = 0.9, 0.9
            if self.togo <= 2:
                stuff_add -= 0.02
        elif concept == "split zone":
            bd += 0.05 + ((e(lead, "impact_block") + e(lead, "run_block")) / 2.0 - 60) / 200.0 \
                if lead is not None else -0.15
            if dc["blitz"] or dc["stunt"]:
                bd += 0.15                   # the backside crash is exactly what the kick-out is for
            sd_mult, big_mult = 1.05, 1.05
        elif concept == "pin and pull":
            bd += 0.0 if not dc["blitz"] else -0.20   # a blitzer through the vacated gap blows it up
            sd_mult, stuff_add, big_mult = 1.15, 0.02, 1.15
        elif concept in self.QB_DESIGNED:
            bd += 0.25                       # the quarterback as the runner: one more blocker than defenders
            if concept == "qb counter":
                bd += 0.20 if dc["blitz"] else -0.05
                sd_mult, stuff_add, big_mult = 1.15, 0.02, 1.15
            else:
                sd_mult, big_mult = 0.9, 0.9
                if self.togo <= 2:
                    stuff_add -= 0.03
        elif concept == "crack toss":
            crackers = [w_ for w_ in wrs[:2]]
            bd += 0.05 + (sum(e(w_, "run_block") for w_ in crackers) / max(1, len(crackers)) - 55) * 0.008
            sd_mult, stuff_add, big_mult = 1.3, 0.04, 1.45
        elif concept == "wildcat":
            bd += 0.25 + read_edge           # an extra blocker, but the defense can play the run
            sd_mult, stuff_add, big_mult = 1.15, 0.02, 1.2
        elif concept in self.OPTION:
            bd += read_edge
            sd_mult, big_mult = 1.15, 1.25
            if concept == "midline":
                sd_mult, big_mult = 0.9, 0.9
                if self.togo <= 2:
                    stuff_add -= 0.03
            elif path_key == "pitch":
                sd_mult, stuff_add, big_mult = 1.35, 0.04, 1.45
        if dc["blitz"]:
            # run blitz: more plays blown up in the backfield, but a missed gap goes a long way
            stuff_add += 0.03
            big_mult *= 1.2
        elif dc["stunt"]:
            stuff_add += 0.01
            big_mult *= 1.1
        if call.get("rpo"):
            bd += 0.35

        if outside:
            rskill = e(carrier, "speed") * 0.24 + e(carrier, "acceleration") * 0.18 \
                + e(carrier, "agility") * 0.14 + e(carrier, "vision") * 0.18 \
                + e(carrier, "juke_spin") * 0.12 + e(carrier, "break_tackle") * 0.14
        else:
            rskill = e(carrier, "vision") * 0.24 + e(carrier, "break_tackle") * 0.18 \
                + e(carrier, "contact_balance") * 0.18 + e(carrier, "strength") * 0.10 \
                + e(carrier, "acceleration") * 0.14 + e(carrier, "juke_spin") * 0.08 \
                + e(carrier, "stiff_arm") * 0.08
        tacklers = lbs + ss + cbs[:2]
        tk = sum(e(t, "tackling") * 0.6 + e(t, "pursuit") * 0.4 for t in tacklers[:5]) \
            / max(1, min(5, len(tacklers)))
        rd = (rskill - tk) / 27.0

        to_goal = 100 - self.yl
        p_stuff = _clip(0.170 - 0.065 * bd - 0.025 * rd + stuff_add
                        + (0.10 if to_goal <= 5 else 0.0), 0.05, 0.45)
        ybc = None
        if random.random() < p_stuff:
            yards = random.choices([0, -1, -2, -3, -4], weights=[40, 25, 18, 10, 7])[0]
            if concept == "reverse":
                yards -= random.randint(1, 5)
            ybc = yards
        else:
            # A short, sure gain plus a long-tailed "what he makes of it" part: most runs go
            # for 1-5 yards, a few break for 10+ (NFL shape: median 3, mean ~4.3)
            push = self.togo <= 2 or to_goal <= 4         # short yardage: a pile-driving gain
            if push:
                base = max(0.5, random.gauss(2.6 + 0.6 * mean_add + 0.6 * bd, 1.0 * sd_mult))
                ext_m = 1.9
            else:
                base = max(0.5, random.gauss(2.4 + 0.6 * mean_add + 0.55 * bd - (0.4 if to_goal <= 10 else 0.0),
                                             1.3 * sd_mult))
                ext_m = 3.4 * (0.8 if to_goal <= 10 else 1.0)
            extra = random.expovariate(1.0 / max(0.6, (ext_m + 0.70 * rd + 0.45 * bd) * sd_mult ** 0.5))
            yards = (base + extra) * self.run_mult
            ybc = int(base * self.run_mult)
            brk = (0.026 + 0.009 * rd + 0.006 * bd + (e(carrier, "speed") - 85) / 1100.0) \
                * self.big_play * big_mult
            if random.random() < max(0.004, brk):
                yards += 9 + random.expovariate(1 / 14.0) * (e(carrier, "speed") / 88.0)
            yards = int(yards)
        yards = min(yards, to_goal)
        if self.yl + yards <= 0:
            yards = -self.yl
        side = "left" if self._run_side < 0 else "right"
        self._record_run_blocks(blk_events, yards)
        if carrier is not None and ybc is not None:
            self.st(carrier, "ybc", min(yards, ybc))
        if concept in ("inside zone", "power", "counter", "draw"):
            label = {"inside zone": random.choice(["up the middle", f"inside zone {side}"]),
                     "power": f"power {side}", "counter": f"counter {side}",
                     "draw": "draw up the middle"}[concept]
        elif concept in self.OPTION:
            label = f"{concept} {side}" + option_note
        else:
            label = f"{concept} {side}" + option_note
        if call.get("rpo"):
            label = "RPO handoff, " + label
        return self._finish_run(carrier, yards, outside, tacklers, dts + edges + lbs, label=label)

    # ── RPOs, trick plays and fakes ──────────────────────────────────────────

    def _rpo(self):
        """Run-pass option: the quarterback reads the conflict defender."""
        qb = self.poss.qb
        dplan = self.dfn.plan
        loaded_box = random.random() < _clip(0.62 - 0.45 * dplan["two_high"] + 0.15 * dplan["blitz"],
                                             0.1, 0.9)
        good_read = random.random() < _clip(0.55 + (self.e(qb, "decision_making") - 60) / 90.0, 0.4, 0.92)
        throw = loaded_box if good_read else not loaded_box
        if throw:
            return self.pass_play(call={"rpo": True} if good_read else {"rpo_bad": True})
        return self.run_play(call={"rpo": True} if good_read else {"concept": "inside zone"})

    def _trick_play(self):
        r = random.random()
        if r < 0.55:
            return self.pass_play(call={"trick": "flea"})
        return self.run_play(call={"concept": "reverse"})

    def _quick_kick_rate(self):
        """Old-school game managers sometimes punt on third and long from deep in their own end."""
        side = self.poss
        prefs = getattr(side.team, "play_prefs", None) or {}
        return 0.004 * (self._gm(side) / 20.0) * (1.0 - side.plan["aggression"]) * prefs.get("st:Quick Kick", 1.0)

    def _quick_kick(self):
        off = self.poss
        p = self._punter(off)
        to_goal = 100 - self.yl
        self.ts(off, "punts")
        self.ts(off, "quick_kicks")
        self.st(p, "punts")
        # nobody is back to field it, so it rolls
        gross = int(random.gauss(36 + (self.e(p, "punt_power") - 70) * 0.10, 6)) + random.randint(4, 16)
        self.run_clock(8, False)
        if gross >= to_goal:
            self.st(p, "punt_yds", to_goal)
            self.st(p, "punt_tb")
            self.log(f"QUICK KICK! {_short(p.name)} punts on third down from the shotgun. It rolls into the "
                     f"end zone. Touchback.", "play")
            self.turnover_on_spot("Punt", 20)
            return
        self.st(p, "punt_yds", gross)
        self.st(p, "punt_long", gross)
        spot = to_goal - gross
        if spot <= 20:
            self.st(p, "punts_in20")
        self.log(f"QUICK KICK! {_short(p.name)} punts on third down from the shotgun, {gross} yards, "
                 f"rolls dead at the {self.dfn.abbr} {spot}.", "play")
        self.turnover_on_spot("Punt", spot)

    def _fake_ok(self):
        plan = self.poss.plan
        if self.togo > 5 or self.quarter >= 5:
            return False
        if self.quarter == 4 and self.clock < 120:
            return False
        return random.random() < 0.06 * plan["trick"] * self.go_mult * (1.4 if self.togo <= 2 else 1.0)

    def _fake_kick(self, kind):
        """Fake punt or fake field goal: a run by the up-back or a pass from the holder."""
        off = self.poss
        self.ts(off, "plays")
        self.ts(off, "fakes")
        rc = self.st_def
        self.st_def = None
        watch = {"Punt Block": 0.15, "Punt Safe": -0.25, "Field Goal Block": 0.10,
                 "Field Goal Safe": -0.20}.get(rc, 0.0)
        surprise = _clip(0.58 + watch + random.gauss(0, 0.12)
                         - 0.15 * self.dfn.team.coach.r("game_management") / 20.0, 0.15, 0.85)
        what = "FAKE PUNT" if kind == "punt" else "FAKE FIELD GOAL"
        to_goal = 100 - self.yl
        holder = self._punter(off)                  # the punter holds for kicks too
        name = st_lib.choose_fake(kind, {"arm": self.e(holder, "throw_power"), "togo": self.togo},
                                  getattr(off.team, "play_prefs", None))
        self._ocall = "Fake: " + name
        if name in ("Up-Back Run", "Punter Run", "Holder Run"):
            if name == "Up-Back Run":
                runner = (off.lu["RB"][1:2] or off.lu["FB"][:1] or off.lu["RB"][:1] or [off.qb])[0]
                hit = surprise
            else:
                runner = holder                     # a kicker's teammate, not a runner: speed matters
                hit = surprise * _clip(0.55 + (self.e(holder, "speed") - 55) / 60.0, 0.4, 1.0)
            yards = int(random.gauss(self.togo + 2.5, 4.0)) if random.random() < hit \
                else random.choice([-2, -1, 0, 1, max(0, self.togo - 1)])
            yards = min(yards, to_goal)
            label = {"Up-Back Run": "direct snap to the up-back", "Punter Run": "the punter runs",
                     "Holder Run": "the holder runs"}[name]
            out = self._finish_run(runner, yards, True, self.dfn.lu["LB"][:2] + self.dfn.lu["S"][:2],
                                   self.dfn.lu["DT"][:2] + self.dfn.lu["LB"][:1], label=f"{what}, {label}")
            return out
        tgt = (off.lu["TE"][1:2] or off.lu["TE"][:1] or off.lu["RB"][:1] or off.lu["WR"][:1])[0]
        self.st(holder, "pass_att")
        self.ts(off, "pass_att")
        self.st(tgt, "targets")
        arm = _clip(0.85 + (self.e(holder, "throw_power") + self.e(holder, "short_accuracy") - 100) / 400.0,
                    0.8, 1.05)
        if random.random() < surprise * 0.95 * arm:
            yards = min(to_goal, max(self.togo, int(random.gauss(self.togo + 6, 5))))
            self.st(holder, "pass_cmp")
            self.st(holder, "pass_yds", yards)
            self.st(tgt, "rec")
            self.st(tgt, "rec_yds", yards)
            self.ts(off, "pass_cmp")
            self.ts(off, "pass_yds", yards)
            td = self.yl + yards >= 100
            if td:
                self.st(holder, "pass_td")
                self.st(tgt, "rec_td")
            return {"kind": "pass", "yards": yards, "time": 6, "clock_runs": True, "carrier": tgt,
                    "td": td, "complete": True, "ptype": "short", "air": yards,
                    "text": f"{what}! {_short(holder.name)} pass to {_short(tgt.name)} for {yards} yards"
                            + (", TOUCHDOWN" if td else "")}
        return {"kind": "pass", "yards": 0, "clock_runs": False, "time": 6, "incomplete": True,
                "ptype": "short", "air": 5,
                "text": f"{what}! {_short(holder.name)} pass to {_short(tgt.name)} incomplete"}

    def _finish_run(self, carrier, yards, outside, tacklers, front, label=None):
        off = self.poss
        if self._spy_on and carrier is not None and self._pos(carrier) == "QB" and yards > 2:
            yards = int(yards * 0.7)              # the spy was waiting for him
        if self._adv is None:
            self._adv = {"rusher": carrier}
        self.st(carrier, "rush_att")
        self.st(carrier, "rush_yds", yards)
        self.st(carrier, "rush_long", yards)
        if yards >= 20:
            self.st(carrier, "rush_20")
        self.ts(off, "rush_att")
        self.ts(off, "rush_yds", yards)
        direction = label or (random.choice(["left end", "right end", "left tackle", "right tackle"])
                              if outside else random.choice(["up the middle", "left guard",
                                                             "right guard"]))
        text = f"{_short(carrier.name)} rush {direction}"
        td = self.yl + yards >= 100
        out = {"kind": "run", "yards": yards, "time": random.uniform(4.5, 6.5),
               "clock_runs": True, "carrier": carrier, "td": td, "text": text}
        if td:
            self.st(carrier, "rush_td")
            out["text"] += f" for {yards} yard{'s' if yards != 1 else ''}, TOUCHDOWN"
            return out
        if yards < 0 and self.yl + yards <= 0:
            out["safety"] = True
        mode = self.urgency(off)
        oob_p = 0.17 if outside else 0.04
        if mode == "hurry":
            oob_p *= 2.2               # get out of bounds
        elif mode == "milk":
            oob_p *= 0.25              # stay in bounds, keep the clock running
        out["oob"] = random.random() < oob_p
        if yards <= 2:
            pool = front
        elif yards <= 9:
            pool = tacklers[:4] + front[-2:]
        else:
            pool = tacklers[-4:]
        tackler = random.choice(pool) if pool else None
        self._missed(tacklers, yards)
        if not out["oob"]:
            self._tackle(tackler, pool, tfl=yards < 0)
        out["text"] += f" for {yards} yard{'s' if abs(yards) != 1 else ''}"
        hit = (1.0 + (self.e(tackler, "hit_power") - 60) / 120.0) if tackler is not None else 1.0
        if random.random() < 0.0185 * (1.45 - self.e(carrier, "ball_security") / 100.0) \
                * self.to_rate * self.wx["fumble"] * hit:
            return self._fumble(out, carrier, tackler)
        return out

    def _qb_sneak(self, qb, front):
        e = self.e
        push = (sum(e(p, "strength") + e(p, "run_block") for p in self.poss.ol) / 10.0
                - sum(e(p, "strength") + e(p, "run_stop") for p in front[:4]) / 8.0)
        p = _clip(0.80 + push / 120.0 + (e(qb, "strength") - 55) / 400.0, 0.55, 0.95)
        yards = random.choice([1, 1, 1, 2, 2, 3]) if random.random() < p else random.choice([0, 0, -1])
        yards = min(yards, 100 - self.yl)
        return self._finish_run(qb, yards, False, front, front, label="sneak")

    def _qb_run(self, qb, scramble, lbs=None, ss=None, dts=None):
        e = self.e
        de = self.dfn
        lbs = lbs if lbs is not None else de.lu["LB"][:2]
        ss = ss if ss is not None else de.lu["S"][:2]
        dts = dts if dts is not None else de.lu["DT"][:2]
        spd = e(qb, "speed")
        mean = 3.6 + (spd - 70) / 5.5 + (2.0 if scramble else 0.0)
        yards = random.gauss(mean, 4.0)
        if random.random() < (0.035 + (spd - 80) / 300.0) * self.big_play:
            yards += 10 + random.expovariate(1 / 14.0)
        yards = int(max(-3, yards))
        yards = min(yards, 100 - self.yl)
        if self.yl + yards <= 0:
            yards = -self.yl
        if scramble:
            self.ts(self.poss, "scrambles")
        label = "scrambles" if scramble else random.choice(["keeper left", "keeper right",
                                                           "option right", "draw"])
        out = self._finish_run(qb, yards, True, lbs + ss, dts + lbs, label=label)
        out["oob"] = out.get("oob") or (random.random() < 0.35)
        return out

    def _missed(self, pool, gain):
        """On a big gain somebody usually whiffed: blame falls on the poorer tacklers."""
        if gain < 6 or not pool or random.random() > 0.55 + min(0.4, gain / 60.0):
            return
        w = [max(1.0, 105.0 - self.e(p, "tackling")) for p in pool[:6]]
        self.st(random.choices(pool[:6], weights=w, k=1)[0], "missed_tkl")

    def _tackle(self, tackler, pool, tfl=False):
        self._last_tackler = tackler
        if tackler is None:
            return
        if random.random() < 0.28 and len(pool) > 1:
            other = random.choice([p for p in pool if p is not tackler])
            self.st(tackler, "tkl_ast")
            self.st(other, "tkl_ast")
        else:
            self.st(tackler, "tkl_solo")
        if tfl:
            self.st(tackler, "tfl")
        self._injury_check(tackler, 0.5)

    # ── Resolving a play ─────────────────────────────────────────────────────

    def resolve(self, out):
        off = self.poss
        kind = out["kind"]
        if self.cur_diag is not None:
            d = self.cur_diag
            d["kind"] = kind
            d["yards"] = out.get("yards", 0)
            d["td"] = bool(out.get("td"))
            d["inc"] = bool(out.get("incomplete"))
            if kind in ("turnover", "pick6"):
                d["to"] = out.get("what", "Interception" if "INTERCEPT" in out.get("text", "") else "Turnover")
            if kind == "sack":
                d["sack"] = True
        if self.drive is not None and kind not in ("pick6",):
            self.drive["yards"] += out.get("yards", 0)

        # Post-snap penalties
        if kind in ("run", "pass", "sack") and self._post_snap_penalty(out):
            return
        if self.down == 3:
            self.ts(off, "third_att")
        elif self.down == 4:
            self.ts(off, "fourth_att")

        if kind == "pick6":
            self._end_drive("Turnover TD")
            scorer_side = self.dfn
            self.swing(scorer_side, 0.20)
            self.run_clock(out["time"], False)
            self.log(out["text"], "play")
            self.poss, self.dfn = self.dfn, self.poss
            self.add_score(scorer_side, 6, f"{_short(out['scorer'].name)} defensive TOUCHDOWN")
            self._after_td(scorer_side)
            return
        if kind == "turnover":
            self.log(out["text"], "play")
            self.swing(self.dfn, 0.40)
            self.run_clock(out["time"], False)
            self.turnover_on_spot(out["what"], out["new_yl"])
            return

        yards = out.get("yards", 0)
        self.log(out["text"], "play")
        if kind == "sack":
            self.swing(self.dfn, 0.10)
        elif yards >= 40:
            self.swing(off, 0.25)
        elif yards >= 20:
            self.swing(off, 0.13)
        carrier = out.get("carrier")
        if carrier is not None:
            self._injury_check(carrier, 1.0)
        if kind == "sack":
            self._injury_check(off.qb, 0.8 * self.rx["qb_injury"])
        elif kind == "pass" and out.get("complete") is None and random.random() < 0.05:
            self._injury_check(off.qb, 0.3)
        if random.random() < 0.25:
            self._injury_check(random.choice(off.ol), 0.35)

        if out.get("safety"):
            self.run_clock(out["time"], False)
            self._end_drive("Safety")
            scoring = self.dfn
            self.add_score(scoring, 2, "SAFETY")
            self._ot_check()
            if not self.game_over:
                self.kickoff(off, from_yl=20, free=True)      # free kick from the 20
            return

        if out.get("td"):
            self.run_clock(out["time"], False)
            self._end_drive("Touchdown")
            self.add_score(off, 6, out["text"])
            self._after_td(off)
            return

        self.yl += yards
        self.togo -= yards
        clock_runs = out.get("clock_runs", True)
        if out.get("incomplete"):
            clock_runs = False
        if self.togo <= 0:
            self._first_down()
            if self.down == 1 and self.prev_down == 3:
                self.ts(off, "third_conv")
            elif self.down == 1 and self.prev_down == 4:
                self.ts(off, "fourth_conv")
        else:
            self.prev_down = self.down
            self.down += 1
        self.run_clock(out["time"], clock_runs, out.get("oob", False))
        if self.down > 4:
            self.swing(self.dfn, 0.30)
            self.log(f"Turnover on downs", "note")
            self.turnover_on_spot("Downs")

    prev_down = 1

    def _first_down(self, penalty=False):
        self.prev_down = self.down
        self.down = 1
        to_goal = 100 - self.yl
        self.togo = min(10, to_goal)
        self.ts(self.poss, "first_downs")
        if penalty:
            self.ts(self.poss, "first_downs_pen")

    def _post_snap_penalty(self, out):
        rate = 0.058 * self.pen_rate
        om, ounf = self._flag_odds(self.poss, "off")
        dm, dunf = self._flag_odds(self.dfn, "def")
        off_disc = (1.35 - self.poss.disc / 100.0 * 0.7) * om
        def_disc = (1.35 - self.dfn.disc / 100.0 * 0.7) * dm
        r = random.random()
        yards = out.get("yards", 0)
        hold = self.rx["holding"]
        if r < rate * off_disc * 0.52 * hold:
            # Offensive holding / OPI — negates the play (declined if the play lost yards)
            if yards <= 0 and out["kind"] != "pass":
                return False
            is_pass = out["kind"] == "pass"
            if is_pass and random.random() < 0.25 and out.get("ptype") in ("medium", "deep"):
                name, p = "Offensive pass interference", out.get("carrier") or self.poss.lu["WR"][0]
            else:
                name, p = "Offensive holding", random.choice(self.poss.ol + self.poss.lu["TE"][:1])
                p = self._culprit(ounf, om, p)
            yds = 10 if self.yl > 20 else max(1, self.yl // 2)
            self._undo_play_stats(out)
            self._penalty(self.poss, p, name, yds)
            self.log(f"{out['text']} — PENALTY: {name}, {self.poss.abbr} "
                     f"({_short(p.name)}), {yds} yards, replay down", "play")
            self.yl -= yds
            self.togo += yds
            self.run_clock(out["time"], False)
            return True
        if r < rate * (off_disc * 0.52 * hold + def_disc * 0.48):
            is_pass = out["kind"] == "pass"
            if is_pass and out.get("incomplete") and out.get("air", 0) >= 8 and \
                    random.random() < 0.55 * self.rx["dpi"]:
                name = "Defensive pass interference"
                p = out.get("def") or random.choice(self.dfn.lu["CB"][:2])
                yds = max(1, min(out.get("air", 10), 99 - self.yl))
                if self.yl + yds >= 100:
                    yds = max(1, 99 - self.yl)
            else:
                name = random.choices(["Defensive holding", "Illegal contact", "Unnecessary roughness",
                                       "Roughing the passer", "Face mask"],
                                      weights=[1, 1, 1, self.rx["roughing"], 1])[0] if is_pass else \
                    random.choice(["Face mask", "Unnecessary roughness", "Defensive holding"])
                p = random.choice(self.dfn.lu["CB"][:2] + self.dfn.lu["LB"][:2] + self.dfn.lu["EDGE"][:2])
                p = self._culprit(dunf, dm, p)
                yds = 5 if name in ("Defensive holding", "Illegal contact") else 15
                # Declined if the play gained more and moved the chains
                if yards >= yds and yards >= self.togo and name in ("Defensive holding", "Illegal contact"):
                    return False
                if name in ("Unnecessary roughness", "Face mask", "Roughing the passer") \
                        and not out.get("incomplete") and out["kind"] != "sack":
                    # Added to the end of the play
                    if self.yl + yards + yds >= 100:
                        yds = max(1, (100 - self.yl - yards) // 2)
                    self._penalty(self.dfn, p, name, yds)
                    out["text"] += f" (+{yds} {name}, {self.dfn.abbr})"
                    out["yards"] = yards + yds
                    out["penalty_first"] = True
                    out["td"] = out.get("td") or self.yl + out["yards"] >= 100
                    if not out["td"]:
                        self.togo = min(self.togo, yards + yds)
                    return False
            if self.yl + yds >= 100:
                yds = max(1, (100 - self.yl) // 2)
            self._undo_play_stats(out)
            self._penalty(self.dfn, p, name, yds)
            self.log(f"{out['text']} — PENALTY: {name}, {self.dfn.abbr} "
                     f"({_short(p.name)}), {yds} yards, automatic first down", "play")
            self.yl += yds
            self._first_down(penalty=True)
            self.run_clock(out["time"], False)
            return True
        return False

    def _undo_play_stats(self, out):
        """A penalty wiped out the play — remove what it added to the stat sheet."""
        self._adv_void = True
        y = out.get("yards", 0)
        kind = out["kind"]
        ps = self.res.player_stats
        if kind == "run" and out.get("carrier"):
            c = ps.get(out["carrier"].id)
            if c:
                c["rush_att"] -= 1
                c["rush_yds"] -= y
            self.ts(self.poss, "rush_att", -1)
            self.ts(self.poss, "rush_yds", -y)
        elif kind == "pass":
            qb = self.poss.qb
            q = ps.get(qb.id)
            if q:
                q["pass_att"] -= 1
                if out.get("complete"):
                    q["pass_cmp"] -= 1
                    q["pass_yds"] -= y
            self.ts(self.poss, "pass_att", -1)
            if out.get("complete"):
                self.ts(self.poss, "pass_cmp", -1)
                self.ts(self.poss, "pass_yds", -y)
                c = ps.get(out["carrier"].id)
                if c:
                    c["rec"] -= 1
                    c["rec_yds"] -= y
                    c["targets"] -= 1
        elif kind == "sack":
            q = ps.get(self.poss.qb.id)
            if q:
                q["sacked"] -= 1
                q["sack_yds"] += y
            self.ts(self.poss, "sacked", -1)
            self.ts(self.poss, "sack_yds", y)
        if self.drive is not None:
            self.drive["yards"] -= y

    # ── Injuries ─────────────────────────────────────────────────────────────

    def _injury_check(self, player, exposure):
        if player is None or player.is_injured or self.inj_rate <= 0:
            return
        res = player.a("injury_resistance")
        tired = 1.0 + max(0.0, 80.0 - self.energy_of(player)) / 60.0     # tired bodies break down
        p = 0.0125 * exposure * (1.55 - res / 100.0) * self.inj_rate * tired
        if random.random() >= p:
            return
        weeks_left = 17
        inj = roll_injury(player, weeks_left)
        player.injury = inj
        side = self.home if player.team == self.home.abbr else self.away
        self.res.injuries.append((player.id, player.name, side.abbr, inj["name"], inj["weeks"]))
        self.log(f"INJURY: {player.name} ({player.position}, {side.abbr}) — {inj['name']}", "note")
        qb_before = side.lu["QB"][0] if side.lu["QB"] else None
        side.refresh_lineup()
        self._replan(side, player, qb_before)

    def _replan(self, side, player, qb_before):
        """After an injury both staffs adjust: the hurt side's plan, and the opponent's plan for it."""
        opp = self.other(side)
        pos = player.position
        if pos in ("QB", "RB", "WR", "TE", "OT", "IOL"):
            side.plan = side.team.gameplan()
            read = opp.dgp.get("read")
            self._game_plan(opp, side, offense=False)      # they re-scout the offense
            if read is not None:
                opp.dgp["read"] = read                     # what they have seen today still counts
            self._game_plan(side, opp, defense=False)
            qb = side.lu["QB"][0] if side.lu["QB"] else None
            if qb is not None and qb is not qb_before:
                self.log(f"The {opp.team.name} defense adjusts for backup QB {qb.name}", "note")
        elif pos in ("CB", "S", "LB", "EDGE", "DT"):
            self._game_plan(opp, side, defense=False)       # attack the replacement

    # ── Finish ───────────────────────────────────────────────────────────────

    def _finish(self):
        self._end_drive("End of game")
        res = self.res
        for side in (self.home, self.away):
            # Games played / started
            played = set(res.starters)
            for p in side.team.roster:
                if p.id in res.player_stats:          # took a snap or recorded a stat
                    played.add(p.id)
            for p in side.team.roster:
                if p.id in played:
                    self.st(p, "gp")
                    if p.id in res.starters:
                        self.st(p, "gs")
            ts = res.team_stats[side.abbr]
            ts["points"] = side.score
            ts["total_yds"] = ts["pass_yds"] - ts["sack_yds"] + ts["rush_yds"]
            # Red zone TDs
            ts["rz_td"] = sum(1 for d in res.drives[side.abbr]
                              if d.get("rz") and d["result"] == "Touchdown")
        res.home_score = self.home.score
        res.away_score = self.away.score
        # Game grades for everyone who played
        for pid, line in res.player_stats.items():
            grades.stamp(line, res.player_meta[pid][1])


def simulate_game(home, away, week=0, season=0, playoff=None, neutral=False,
                  keep_pbp=True, rules=None, diagrams=False, user_abbr=None, scouting=None, iq=None):
    """
    user_abbr: the user's club (its staff works at the realistic baseline);
    scouting: {abbr: that club's games so far this season} (the film both staffs study); iq: CPU intelligence
    (a number, or {abbr: number}; default the league setting).
    """
    return GameSim(home, away, week, season, playoff, neutral, keep_pbp, rules, diagrams,
                   user_abbr=user_abbr, scouting=scouting, iq=iq).play()
