"""
team.py — teams, depth charts, team ratings and game plans.
"""
import random

from ratings import (POSITIONS, ROSTER_TEMPLATE, ROSTER_MINIMUM, POSITION_VALUE,
                     stars_for)
from coach import Coach

# When a position runs dry (injuries), who can fill in
FALLBACK = {
    "QB": ["RB", "WR"], "RB": ["FB", "WR"], "FB": ["RB", "TE"],
    "WR": ["TE", "RB", "CB"], "TE": ["FB", "OT", "WR"], "OT": ["IOL", "DT"],
    "IOL": ["OT", "DT"], "DT": ["EDGE", "IOL"], "EDGE": ["DT", "LB"],
    "LB": ["EDGE", "S"], "CB": ["S", "WR"], "S": ["CB", "LB"],
    "K": ["P"], "P": ["K"],
}

# User tactic sliders (0-100, 50 = follow the coach's natural tendency)
TACTIC_SLIDERS = {
    "pass_run":     ("Run  ◄  Play Balance  ►  Pass",
                     "Shifts how often you throw on neutral downs"),
    "deep_short":   ("Short  ◄  Passing Depth  ►  Deep",
                     "Quick game vs. shots downfield"),
    "run_direction": ("Inside  ◄  Run Style  ►  Outside",
                      "Power/gap runs vs. outside zone and sweeps"),
    "tempo":        ("Slow  ◄  Tempo  ►  Hurry-up",
                     "Time between snaps (more or fewer plays per game)"),
    "rb_usage":     ("Bell-cow  ◄  Backfield  ►  Committee",
                     "Ride your lead back or rotate running backs"),
    "play_action":  ("Rarely  ◄  Play-Action & RPO  ►  Often",
                     "Fakes off the run game: play-action shots and run-pass options"),
    "trickery":     ("Never  ◄  Trick Plays  ►  Often",
                     "Flea-flickers, reverses, fake punts and fake field goals"),
    "aggression":   ("Conservative  ◄  4th Down / 2-pt  ►  Aggressive",
                     "Going for it on 4th down and two-point tries"),
    "qb_runs":      ("Never  ◄  Designed QB Runs  ►  Often",
                     "Option and designed quarterback runs"),
    "screens":      ("Rarely  ◄  Screen Game  ►  Often",
                     "Screens to backs and receivers"),
    "blitz":        ("Coverage  ◄  Blitz Rate  ►  Pressure",
                     "Sending extra rushers"),
    "coverage":     ("Man  ◄  Coverage  ►  Zone",
                     "Man-to-man vs. zone coverage"),
    "safeties":     ("Single-High  ◄  Shell  ►  Two-High",
                     "Two deep safeties limit big plays but soften run defense"),
}


def _active(p):
    return not p.ps and not p.ir and not p.holdout


class Team:
    tag_year = None          # season the franchise tag was last used
    rotation = None          # {"DL": "heavy", ...} how freely each group substitutes (None = normal)
    def_gameplan = None      # the user's defensive game-plan choices (defense.GAMEPLAN_OPTIONS)
    ir_returns = (None, 0)   # (season, players activated from IR)

    def __init__(self, abbr, city, name, conference, division, colors):
        self.abbr = abbr
        self.city = city
        self.name = name
        self.conference = conference
        self.division = division
        self.colors = colors                  # (primary hex, secondary hex)
        self.roster = []
        self.coach = Coach()
        self.facilities = random.randint(6, 18)    # 1-20 training facilities
        self.scouting = random.randint(6, 18)      # 1-20 scouting department
        self.fan_support = random.randint(40, 90)  # 1-100
        self.depth_overrides = {}             # pos -> [player ids] (user order)
        self.tactics = None                   # user sliders dict or None (AI)
        self.history = []                     # season summaries
        self.titles = 0
        self.conf_titles = 0
        self.playoff_apps = 0
        self.division_titles = 0
        self.dead_cap = 0                     # this season only

    # ── Identity ─────────────────────────────────────────────────────────────

    @property
    def full_name(self):
        return f"{self.city} {self.name}"

    def __repr__(self):
        return f"<Team {self.abbr}>"

    # ── Roster ───────────────────────────────────────────────────────────────

    def players_at(self, pos, healthy_only=False, include_inactive=False):
        return [p for p in self.roster if p.position == pos
                and (include_inactive or _active(p))
                and (not healthy_only or not p.is_injured)]

    def players_at_any(self):
        return list(self.roster)

    def get_player(self, pid):
        for p in self.roster:
            if p.id == pid:
                return p
        return None

    def add_player(self, player):
        player.team = self.abbr
        taken = {p.jersey for p in self.roster}
        if player.jersey == 0 or player.jersey in taken:
            from player import jersey_for
            player.jersey = jersey_for(player.position, taken)
        self.roster.append(player)

    def remove_player(self, player):
        if player in self.roster:
            self.roster.remove(player)
        for pos, ids in self.depth_overrides.items():
            if player.id in ids:
                ids.remove(player.id)
        player.team = None

    @property
    def payroll(self):
        return sum(p.salary for p in self.roster) + self.dead_cap

    def cap_space(self, cap):
        return cap - self.payroll

    def position_counts(self, include_inactive=False):
        counts = {pos: 0 for pos in POSITIONS}
        for p in self.roster:
            if include_inactive or _active(p):
                counts[p.position] += 1
        return counts

    def needs(self):
        """Positions ranked by how badly the team needs help (higher = more)."""
        out = {}
        counts = self.position_counts()
        for pos in POSITIONS:
            want = ROSTER_TEMPLATE[pos]
            have = counts[pos]
            group = sorted((p.ca for p in self.players_at(pos)), reverse=True)
            starters_needed = {"WR": 3, "OT": 2, "IOL": 3, "DT": 2, "EDGE": 2,
                               "LB": 3, "CB": 3, "S": 2}.get(pos, 1)
            starter_q = (sum(group[:starters_needed]) / starters_needed
                         if len(group) >= starters_needed else
                         (sum(group) / starters_needed if group else 0))
            quality_need = max(0.0, (140 - starter_q) / 60.0)
            count_need = max(0, ROSTER_MINIMUM[pos] - have) * 0.6 \
                + max(0, want - have) * 0.15
            out[pos] = (quality_need + count_need) * (0.5 + POSITION_VALUE[pos])
        return out

    # ── Depth chart ──────────────────────────────────────────────────────────

    def depth(self, pos, include_injured=False):
        """Players at a position in depth order (user overrides first)."""
        group = [p for p in self.roster if p.position == pos and not p.ps
                 and (include_injured or (not p.is_injured and not p.ir and not p.holdout))]
        order = self.depth_overrides.get(pos, [])
        rank = {pid: i for i, pid in enumerate(order)}
        return sorted(group, key=lambda p: (rank.get(p.id, 999), -p.ca))

    def lineup(self, pos, n):
        """n healthy players for a position, borrowing from others if short."""
        out = self.depth(pos)[:n]
        if len(out) < n:
            used = {p.id for p in out}
            pool = []
            for alt in FALLBACK.get(pos, []):
                pool += [p for p in self.depth(alt) if p.id not in used]
            pool.sort(key=lambda p: -p.rating_at(pos))
            out += pool[:n - len(out)]
        if len(out) < n:
            used = {p.id for p in out}
            rest = sorted((p for p in self.roster
                           if not p.is_injured and _active(p) and p.id not in used),
                          key=lambda p: -p.rating_at(pos))
            out += rest[:n - len(out)]
        return out

    def returner(self, kind="KR"):
        key = kind
        order = self.depth_overrides.get(key)
        if order:
            for pid in order:
                p = self.get_player(pid)
                if p and not p.is_injured and _active(p):
                    return p
        cands = [p for p in self.roster if not p.is_injured and _active(p)
                 and p.position in ("RB", "WR", "CB", "S")]
        if not cands:
            cands = [p for p in self.roster if not p.is_injured and _active(p)]
        # Teams avoid using their stars as returners
        def score(p):
            star_penalty = 12 if p.ca >= 160 else 0
            return p.return_rating - star_penalty
        cands.sort(key=score, reverse=True)
        if kind == "PR" and len(cands) > 1:
            return cands[1] if cands[1].return_rating >= cands[0].return_rating - 3 \
                else cands[0]
        return cands[0] if cands else None

    def starters(self):
        """The base lineup used for display and team ratings."""
        return {
            "QB": self.lineup("QB", 1), "RB": self.lineup("RB", 1),
            "WR": self.lineup("WR", 3), "TE": self.lineup("TE", 1),
            "OT": self.lineup("OT", 2), "IOL": self.lineup("IOL", 3),
            "DT": self.lineup("DT", 2), "EDGE": self.lineup("EDGE", 2),
            "LB": self.lineup("LB", 3), "CB": self.lineup("CB", 3),
            "S": self.lineup("S", 2), "K": self.lineup("K", 1),
            "P": self.lineup("P", 1),
        }

    # ── Ratings ──────────────────────────────────────────────────────────────

    def unit_ratings(self):
        s = self.starters()

        def avg(players, pos):
            return sum(p.rating_at(pos) for p in players) / len(players) if players else 50

        qb = avg(s["QB"], "QB")
        rb = avg(s["RB"], "RB")
        wr = avg(s["WR"], "WR")
        te = avg(s["TE"], "TE")
        ol = (avg(s["OT"], "OT") * 2 + avg(s["IOL"], "IOL") * 3) / 5
        dl = (avg(s["DT"], "DT") + avg(s["EDGE"], "EDGE") * 1.2) / 2.2
        lb = avg(s["LB"], "LB")
        db = (avg(s["CB"], "CB") * 3 + avg(s["S"], "S") * 2) / 5
        st = (avg(s["K"], "K") + avg(s["P"], "P")) / 2
        offense = qb * 0.34 + rb * 0.08 + wr * 0.20 + te * 0.08 + ol * 0.30
        defense = dl * 0.38 + lb * 0.22 + db * 0.40
        overall = offense * 0.50 + defense * 0.44 + st * 0.06
        return {"QB": qb, "RB": rb, "WR": wr, "TE": te, "OL": ol, "DL": dl,
                "LB": lb, "DB": db, "ST": st, "OFF": offense, "DEF": defense,
                "OVR": overall}

    @property
    def overall(self):
        return int(round(self.unit_ratings()["OVR"]))

    @property
    def stars(self):
        return stars_for(self.overall)

    # ── Game plan ────────────────────────────────────────────────────────────

    def gameplan(self):
        """
        Translate coach philosophy + roster strengths (+ user tactics) into
        the numbers the match engine reads.
        """
        c = self.coach
        t = c.tendencies
        u = self.unit_ratings()

        # Smart coaches lean into what their roster does well
        adapt = 0.4 + c.r("adaptability") / 20.0 * 0.6
        # Compare each unit to a league-normal baseline so the lean reflects
        # genuine strengths (a great QB, a weak backfield), not position scale.
        pass_score = (u["QB"] - 146) * 0.6 + ((u["WR"] - 131) * 0.7 + (u["TE"] - 128) * 0.3) * 0.4
        run_score = (u["RB"] - 128) * 0.55 + (u["OL"] - 131) * 0.45
        roster_lean = max(-0.07, min(0.07, (pass_score - run_score) / 150.0)) * adapt

        plan = {
            "pass_rate": 0.52 + 0.21 * t["pass_lean"] + roster_lean,
            "deep": t["deep"],
            "outside": t["outside"],
            "qb_run": t["qb_run"],
            "heavy": t["heavy"],
            "tempo": t["tempo"],
            "screen": t["screen"],
            "aggression": t["aggression"],
            "blitz": t["blitz"],
            "zone": t["zone"],
            "two_high": t["two_high"],
            "front": t["front"],
            "committee": t.get("committee", 0.45),
            "play_action": t.get("play_action", 0.45),
            "rpo": t.get("rpo", 0.30),
            "trick": t.get("trick", 0.35),
        }
        # Mobile quarterbacks get more designed runs if the coach adapts
        qbs = self.lineup("QB", 1)
        if qbs:
            mob = (qbs[0].a("speed") - 70) / 30.0
            plan["qb_run"] = max(0.0, min(1.0, plan["qb_run"] + mob * 0.35 * adapt))

        if self.tactics:
            tac = self.tactics
            plan["pass_rate"] += (tac.get("pass_run", 50) - 50) / 50.0 * 0.16
            plan["deep"] += (tac.get("deep_short", 50) - 50) / 50.0 * 0.8
            plan["outside"] += (tac.get("run_direction", 50) - 50) / 50.0 * 0.45
            plan["tempo"] += (tac.get("tempo", 50) - 50) / 50.0 * 0.5
            plan["aggression"] += (tac.get("aggression", 50) - 50) / 50.0 * 0.5
            plan["qb_run"] += (tac.get("qb_runs", 50) - 50) / 50.0 * 0.5
            plan["screen"] += (tac.get("screens", 50) - 50) / 50.0 * 0.5
            plan["blitz"] += (tac.get("blitz", 50) - 50) / 50.0 * 0.45
            plan["zone"] += (tac.get("coverage", 50) - 50) / 50.0 * 0.5
            plan["two_high"] += (tac.get("safeties", 50) - 50) / 50.0 * 0.5
            plan["committee"] += (tac.get("rb_usage", 50) - 50) / 50.0 * 0.5
            plan["play_action"] += (tac.get("play_action", 50) - 50) / 50.0 * 0.45
            plan["rpo"] += (tac.get("play_action", 50) - 50) / 50.0 * 0.35
            plan["trick"] += (tac.get("trickery", 50) - 50) / 50.0 * 0.6

        plan["pass_rate"] = max(0.28, min(0.74, plan["pass_rate"]))
        plan["deep"] = max(-1.0, min(1.0, plan["deep"]))
        for k in ("outside", "qb_run", "heavy", "tempo", "screen", "aggression",
                  "blitz", "zone", "two_high", "committee", "play_action", "rpo", "trick"):
            plan[k] = max(0.0, min(1.0, plan[k]))
        return plan

    # ── Morale & chemistry ───────────────────────────────────────────────────

    @property
    def team_morale(self):
        if not self.roster:
            return 50
        top = sorted(self.roster, key=lambda p: -p.ca)[:30]
        base = sum(p.morale for p in top) / len(top)
        # Respected leaders keep the room together when things go wrong
        lead = sorted((p.attrs.get("leadership", 40) for p in top), reverse=True)[:3]
        lead = sum(lead) / max(1, len(lead))
        return base + (60 - base) * max(0.0, (lead - 70) / 100.0)

    @property
    def discipline(self):
        """0-100, drives penalty rates."""
        top = sorted(self.roster, key=lambda p: -p.ca)[:30]
        temper = sum(p.hidden.get("temperament", 50) for p in top) / max(1, len(top))
        return temper * 0.6 + self.coach.r("discipline") * 2.0
