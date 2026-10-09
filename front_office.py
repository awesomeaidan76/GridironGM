"""
front_office.py — the brains of every CPU front office.

No UI code. Each club has three people who shape its roster:

  * The OWNER sets the budget and the mood: how much he spends, how long he
    waits, how high the bar is and how much he meddles. He hires and fires.
  * The GENERAL MANAGER has a personality: a set of traits (patience, appetite
    for risk, how often he deals, analytics vs. old-school, youth vs.
    veterans, cap discipline, loyalty, stars vs. depth, best-player vs. need,
    trenches, defense vs. offense, how hard he bargains) plus judgement - how
    good he is at it, which is separate from his style. Every GM comes from
    an archetype ("Draft-and-Develop Builder", "Win-Now Aggressor", ...) with
    his own twist on it.
  * The HEAD COACH has a style (players' coach, disciplinarian, teacher ...)
    and a level of trust in young players.

Every offseason (and again before the trade deadline) the GM chooses a PLAN
for the club - All-In, Contend, Last Dance, Playoff Push, Stay the Course,
Retool, Youth Movement, Rebuild, Tank or Cap Reset - from where the roster
stands, its age, its quarterback, its cap sheet, the owner's mandate and his
own personality. Plans stick for a while (a rebuild isn't abandoned after one
good month). The plan and the personality feed one valuation that every
decision uses: trades, draft boards, free agency, re-signings and depth
charts.

GMs remember how their picks turned out and trust positions where they have
hit, distrust ones where they have missed. Owners fire GMs and coaches who
miss the mark (patient owners wait longer); new hires tend to be unlike the
man they replace, and copy whatever front offices have been winning titles -
so front-office fashions come and go on their own over the decades.

Everything here is plain tables and small functions so it ports cleanly.
"""
import random
import zlib

import names
from settings import settings

# ── GM personality ────────────────────────────────────────────────────────────

TRAITS = ("patience", "risk", "activity", "analytics", "youth", "cap_disc", "loyalty", "stars",
          "bpa", "trenches", "defense", "hardness")

TRAIT_INFO = {
    # key: (low label, high label, what it does)
    "patience":  ("Impatient", "Patient",
                  "How far ahead he plans. Patient GMs value picks and young players and will sit "
                  "through a rebuild; impatient ones want results this year."),
    "risk":      ("Cautious", "Gambler",
                  "Appetite for boom-or-bust moves: trading up, drafting upside over polish, betting "
                  "on injured or raw players."),
    "activity":  ("Quiet", "Wheeler-dealer",
                  "How often he makes trades and chases free agents."),
    "analytics": ("Old-school", "Analytics-driven",
                  "Reads the league's current numbers when valuing positions, trades down, avoids "
                  "paying running backs and off-ball linebackers; old-school GMs trust traditional "
                  "values and what used to win."),
    "youth":     ("Trusts veterans", "Youth-focused",
                  "Premium on young players versus proven veterans."),
    "cap_disc":  ("Spends freely", "Cap-disciplined",
                  "Keeps money in reserve and avoids big contracts, or pushes the cap to the limit."),
    "loyalty":   ("Unsentimental", "Loyal",
                  "Keeps and re-signs his own players, rarely trades them."),
    "stars":     ("Builds depth", "Star-chaser",
                  "Consolidates resources into a few stars, or spreads them across a deep roster."),
    "bpa":       ("Drafts for need", "Best player available",
                  "On draft day: take the highest player on the board or fill the biggest hole."),
    "trenches":  ("Skill-position focus", "Builds the trenches",
                  "Extra value on linemen on both sides of the ball."),
    "defense":   ("Offense-first", "Defense-first",
                  "Which side of the ball he invests in."),
    "hardness":  ("Easy to deal with", "Hard bargainer",
                  "How much extra he demands before saying yes to a trade."),
}

# Archetype: (description, base traits, how common)
GM_ARCHETYPES = {
    "Analytics Disruptor": (
        "Trusts the numbers. Trades down for extra picks, lets mid-priced veterans walk for "
        "compensatory picks, won't pay running backs, and hires aggressive 4th-down coaches.",
        dict(patience=0.70, risk=0.45, activity=0.75, analytics=0.92, youth=0.65, cap_disc=0.80,
             loyalty=0.30, stars=0.45, bpa=0.80, trenches=0.50, defense=0.50, hardness=0.65), 1.0),
    "Draft-and-Develop Builder": (
        "Builds through the draft, re-signs his own, barely touches free agency and is happy to "
        "wait for young players to grow.",
        dict(patience=0.90, risk=0.40, activity=0.30, analytics=0.55, youth=0.82, cap_disc=0.82,
             loyalty=0.78, stars=0.40, bpa=0.82, trenches=0.55, defense=0.50, hardness=0.55), 1.3),
    "Win-Now Aggressor": (
        "Picks are for trading. Chases stars, pushes the cap to the limit and lives for this "
        "season's title run.",
        dict(patience=0.12, risk=0.80, activity=0.90, analytics=0.50, youth=0.22, cap_disc=0.18,
             loyalty=0.40, stars=0.92, bpa=0.40, trenches=0.45, defense=0.50, hardness=0.40), 1.0),
    "Old-School Football Man": (
        "Football is won up front. Builds the lines, values toughness and veterans, drafts the "
        "player he can see on tape and doesn't care what the spreadsheets say.",
        dict(patience=0.55, risk=0.35, activity=0.40, analytics=0.12, youth=0.38, cap_disc=0.55,
             loyalty=0.65, stars=0.45, bpa=0.45, trenches=0.88, defense=0.62, hardness=0.55), 1.2),
    "Wheeler-Dealer": (
        "Never stops working the phones. More trades than anyone, creative with the cap, always "
        "looking to buy low and sell high.",
        dict(patience=0.50, risk=0.65, activity=1.00, analytics=0.62, youth=0.50, cap_disc=0.40,
             loyalty=0.22, stars=0.60, bpa=0.55, trenches=0.50, defense=0.50, hardness=0.60), 0.9),
    "Moneyball Value Hunter": (
        "Hates overpaying. Hunts bargains in the middle of free agency, avoids big contracts and "
        "spreads money across a deep roster.",
        dict(patience=0.62, risk=0.40, activity=0.62, analytics=0.78, youth=0.58, cap_disc=0.95,
             loyalty=0.35, stars=0.18, bpa=0.65, trenches=0.50, defense=0.50, hardness=0.75), 1.0),
    "Star Chaser": (
        "Makes the splash signing. The biggest name on the market is his first call, and he'll "
        "worry about the bill later.",
        dict(patience=0.32, risk=0.70, activity=0.75, analytics=0.40, youth=0.38, cap_disc=0.22,
             loyalty=0.45, stars=0.95, bpa=0.50, trenches=0.35, defense=0.45, hardness=0.45), 0.9),
    "Loyalist": (
        "Pays his own. Re-signs the players he drafted, hates trading them and builds a culture "
        "of continuity.",
        dict(patience=0.68, risk=0.30, activity=0.25, analytics=0.45, youth=0.55, cap_disc=0.50,
             loyalty=0.95, stars=0.55, bpa=0.60, trenches=0.55, defense=0.50, hardness=0.50), 1.0),
    "Boom-or-Bust Gambler": (
        "Swings for the fences: trades up for raw talent, takes chances on injured stars and "
        "high-ceiling prospects.",
        dict(patience=0.45, risk=0.95, activity=0.70, analytics=0.40, youth=0.62, cap_disc=0.40,
             loyalty=0.40, stars=0.75, bpa=0.62, trenches=0.45, defense=0.50, hardness=0.45), 0.8),
    "Steady Caretaker": (
        "Avoids mistakes rather than chasing glory. Few trades, sensible contracts, a balanced "
        "roster.",
        dict(patience=0.58, risk=0.15, activity=0.20, analytics=0.45, youth=0.50, cap_disc=0.72,
             loyalty=0.62, stars=0.42, bpa=0.55, trenches=0.52, defense=0.50, hardness=0.62), 1.1),
    "Defense-First Architect": (
        "Defense wins championships. Pass rushers and cover men first, an offense that doesn't "
        "lose the game second.",
        dict(patience=0.60, risk=0.45, activity=0.50, analytics=0.50, youth=0.55, cap_disc=0.60,
             loyalty=0.55, stars=0.55, bpa=0.55, trenches=0.65, defense=0.92, hardness=0.55), 0.9),
    "Quarterback Whisperer": (
        "Everything starts at quarterback. Spends whatever it takes at the position and builds "
        "weapons around him.",
        dict(patience=0.55, risk=0.62, activity=0.55, analytics=0.62, youth=0.55, cap_disc=0.45,
             loyalty=0.55, stars=0.68, bpa=0.50, trenches=0.40, defense=0.25, hardness=0.50), 0.9),
}

ARCH_QB_FOCUS = {"Quarterback Whisperer": 1.25}

# ── Owners ────────────────────────────────────────────────────────────────────

OWNER_TYPES = {
    # label: description
    "Win-at-All-Costs": "Spends to the cap, expects titles and runs out of patience fast.",
    "Patient Steward": "Gives his football people time and backs a long-term plan.",
    "Penny-Pincher": "Watches every dollar; free agency budgets are tight.",
    "Meddler": "Has opinions on everything, pushes for big names and vetoes trading fan favourites.",
    "Hands-Off": "Hires people and lets them work.",
    "Showman": "Wants stars and headlines to fill the stadium.",
    "Trigger-Happy": "Fires coaches and GMs at the first sign of trouble.",
    "Traditionalist": "Values stability and loyalty; rarely makes a change.",
}

POWER_TYPES = {
    "GM-led": "The general manager controls the roster; the coach coaches.",
    "Coach-led": "The head coach has the final say on personnel - he wants players who fit his "
                 "scheme, and veterans when his job is on the line.",
    "Owner-run": "The owner effectively acts as GM: star signings, sentimental decisions.",
}

# ── Coaches ───────────────────────────────────────────────────────────────────

COACH_STYLES = {
    "offense": "Offensive Mastermind",
    "defense": "Defensive Mastermind",
    "development": "Teacher and Developer",
    "motivation": "Players' Coach",
    "game_management": "Game-Day Tactician",
    "adaptability": "Adaptable Problem-Solver",
    "discipline": "Disciplinarian",
}

# ── Plans ─────────────────────────────────────────────────────────────────────
#   pick : value of draft picks         youth: value of players 25 and under
#   vet  : value of players 29+         buy  : appetite to add veterans by trade
#   sell : appetite to sell veterans    fa   : free-agent spending
#   kids : how much playing time young players get (CA points on the depth chart)
#   commit: seasons a plan is kept before it's reconsidered
PLANS = {
    "All-In": dict(pick=0.62, youth=0.85, vet=1.28, buy=1.00, sell=0.00, fa=1.30, kids=0.0, commit=1,
                   desc="Championship or bust: future picks and prospects are currency for stars "
                        "who help right now."),
    "Contend": dict(pick=0.85, youth=0.95, vet=1.12, buy=0.70, sell=0.08, fa=1.12, kids=0.0, commit=1,
                    desc="A contender protecting its window: adds at the deadline, keeps its "
                         "best young players."),
    "Last Dance": dict(pick=0.60, youth=0.78, vet=1.32, buy=0.90, sell=0.00, fa=1.20, kids=0.0, commit=1,
                       desc="An ageing core gets one more run before the bill comes due."),
    "Playoff Push": dict(pick=0.95, youth=1.00, vet=1.06, buy=0.45, sell=0.12, fa=1.02, kids=0.0, commit=1,
                         desc="On the fringe of the playoffs and buying modestly to get in."),
    "Stay the Course": dict(pick=1.00, youth=1.00, vet=1.00, buy=0.22, sell=0.22, fa=0.95, kids=0.0,
                            commit=1, desc="No big swings: keep the roster together and see."),
    "Retool": dict(pick=1.10, youth=1.10, vet=0.88, buy=0.12, sell=0.45, fa=0.85, kids=1.5, commit=1,
                   desc="Getting younger on the fly: selling some veterans while trying to stay "
                        "competitive."),
    "Youth Movement": dict(pick=1.15, youth=1.25, vet=0.80, buy=0.08, sell=0.40, fa=0.72, kids=3.5, commit=2,
                           desc="A young core is the future: playing time for the kids, no "
                                "expensive veterans."),
    "Rebuild": dict(pick=1.30, youth=1.30, vet=0.66, buy=0.00, sell=0.80, fa=0.60, kids=4.0, commit=2,
                    desc="Selling veterans for picks and young players; wins can wait."),
    "Tank": dict(pick=1.45, youth=1.35, vet=0.52, buy=0.00, sell=1.00, fa=0.45, kids=6.0, commit=2,
                 desc="A full teardown aimed at the top of the draft."),
    "Cap Reset": dict(pick=1.10, youth=1.10, vet=0.80, buy=0.00, sell=0.60, fa=0.40, kids=2.0, commit=1,
                      desc="Too much money committed: shedding salary and avoiding new contracts."),
}
BUYERS = ("All-In", "Contend", "Last Dance", "Playoff Push")
SELLERS = ("Rebuild", "Tank", "Retool", "Cap Reset", "Youth Movement")
NEUTRAL_PLAN = "Stay the Course"

# Analytics GMs value positions by today's game, old-school GMs by tradition
TRADITIONAL_VALUE = {"QB": 1.00, "EDGE": 0.58, "OT": 0.60, "WR": 0.50, "CB": 0.52, "DT": 0.56,
                     "IOL": 0.52, "S": 0.44, "LB": 0.50, "TE": 0.46, "RB": 0.48, "FB": 0.18,
                     "K": 0.15, "P": 0.10}
ANALYTICS_VALUE = {"QB": 1.10, "EDGE": 0.66, "OT": 0.58, "WR": 0.60, "CB": 0.58, "DT": 0.50,
                   "IOL": 0.40, "S": 0.42, "LB": 0.34, "TE": 0.40, "RB": 0.26, "FB": 0.06,
                   "K": 0.14, "P": 0.10}
# How much each position's value rises when the league throws more (per 10 points of pass rate)
PASS_SENSITIVITY = {"QB": 0.06, "WR": 0.10, "TE": 0.02, "OT": 0.06, "CB": 0.10, "S": 0.05,
                    "EDGE": 0.07, "RB": -0.12, "FB": -0.15, "IOL": -0.05, "DT": -0.06, "LB": -0.07}
TRENCH = {"OT", "IOL", "DT", "EDGE"}
DEFENSE = {"DT", "EDGE", "LB", "CB", "S"}
OFFENSE = {"QB", "RB", "FB", "WR", "TE", "OT", "IOL"}


def _clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


# ── People ────────────────────────────────────────────────────────────────────

class GM:
    club_wins = club_losses = club_ties = 0

    def __init__(self, archetype=None, rng=random, base=None):
        self.name = names.random_name()
        self.age = rng.randint(36, 60)
        if archetype is None:
            arch = list(GM_ARCHETYPES)
            archetype = rng.choices(arch, weights=[GM_ARCHETYPES[a][2] for a in arch])[0]
        self.archetype = archetype
        src = base if base is not None else GM_ARCHETYPES[archetype][1]
        spread = settings["ai_personality_strength"]
        self.traits = {k: round(_clamp(0.5 + (src.get(k, 0.5) - 0.5) * spread + rng.gauss(0, 0.09)), 3)
                       for k in TRAITS}
        self.judgement = int(_clamp(round(rng.gauss(11, 3.2)), 3, 20))   # 1-20 competence
        self.reputation = int(_clamp(rng.gauss(40, 12), 5, 95))
        self.team = None
        self.hired = None
        self.seasons = 0                 # seasons with the current club
        self.career_seasons = 0
        self.wins = self.losses = self.ties = 0
        self.titles = 0
        self.playoffs = 0
        self.club_wins = self.club_losses = self.club_ties = 0     # with his current club
        self.mentor = None               # "Name (ABBR)" whose front office he came from
        self.history = []                # [(year, team, record, plan, result)]
        self.picks = []                  # [(year, pid, round, pick, pos)]
        self.pos_belief = {}             # pos -> trust multiplier from his own draft record
        self.draft_hits = 0
        self.draft_misses = 0
        self.draft_graded = 0

    def t(self, key):
        return self.traits.get(key, 0.5)

    @property
    def record_str(self):
        s = f"{self.wins}-{self.losses}"
        return s + (f"-{self.ties}" if self.ties else "")

    @property
    def club_record(self):
        s = f"{self.club_wins}-{self.club_losses}"
        return s + (f"-{self.club_ties}" if self.club_ties else "")

    @property
    def win_pct(self):
        g = self.wins + self.losses + self.ties
        return (self.wins + 0.5 * self.ties) / g if g else 0.0

    def trait_words(self, n=4):
        """The most distinctive traits as words, strongest first."""
        out = []
        for k in sorted(TRAITS, key=lambda k: -abs(self.t(k) - 0.5)):
            d = self.t(k) - 0.5
            if abs(d) < 0.17:
                break
            lo, hi, _ = TRAIT_INFO[k]
            out.append(hi if d > 0 else lo)
            if len(out) >= n:
                break
        return out


def owner_traits(o, rng=random):
    """Owners from older saves only know patience and ambition; fill in the rest."""
    if getattr(o, "spending", None) is None:
        seed = zlib.crc32(f"owner:{o.name}".encode())
        r = random.Random(seed)
        o.spending = int(_clamp(round(r.gauss(10.5, 4)), 1, 20))      # 1 = cheap, 20 = spends anything
        o.meddling = int(_clamp(round(r.gauss(8, 4.5)), 1, 20))       # 1 = hands-off, 20 = runs the team
    return o


def owner_type(o):
    owner_traits(o)
    if o.meddling >= 16:
        return "Meddler" if o.spending < 14 else "Showman"
    if o.ambition >= 15 and o.spending >= 13:
        return "Win-at-All-Costs"
    if o.patience <= 5:
        return "Trigger-Happy"
    if o.spending <= 6:
        return "Penny-Pincher"
    if o.patience >= 15:
        return "Patient Steward" if o.ambition >= 9 else "Traditionalist"
    if o.meddling <= 4:
        return "Hands-Off"
    if o.ambition >= 14:
        return "Showman" if o.meddling >= 11 else "Win-at-All-Costs"
    return "Traditionalist" if o.patience >= 12 else "Hands-Off"


def coach_youth_trust(c):
    v = getattr(c, "youth_trust", None)
    if v is None:
        r = random.Random(zlib.crc32(f"coach:{c.name}:{c.age}".encode()))
        v = round(_clamp(r.gauss(0.5, 0.18) + (c.r("development") - 10) * 0.015), 3)
        c.youth_trust = v
    return v


def coach_style(c):
    best = max(COACH_STYLES, key=lambda k: c.r(k) + (0.4 if k in ("offense", "defense") else 0))
    style = COACH_STYLES[best]
    extra = []
    aggr = c.tendencies.get("aggression", 0.45)
    if aggr >= 0.62:
        extra.append("aggressive on 4th down")
    elif aggr <= 0.28:
        extra.append("conservative")
    yt = coach_youth_trust(c)
    if yt >= 0.66:
        extra.append("plays young players")
    elif yt <= 0.34:
        extra.append("trusts veterans")
    return style + (f" ({', '.join(extra)})" if extra else "")


# ── Setup ─────────────────────────────────────────────────────────────────────

def ensure(lg):
    """Give every CPU club a GM, every owner a full personality, and the league its pools."""
    if not hasattr(lg, "gm_pool") or lg.gm_pool is None:
        lg.gm_pool = []
    if not hasattr(lg, "fo_log") or lg.fo_log is None:
        lg.fo_log = []
    for t in lg.teams.values():
        o = getattr(t, "owner", None)
        if o is not None:
            owner_traits(o)
        if getattr(t, "power", None) is None:
            t.power = _roll_power(o)
        coach_youth_trust(t.coach)
        if t.abbr == lg.user_abbr:
            if getattr(t, "gm", None) is not None:
                old = t.gm
                old.team = None
                lg.gm_pool.append(old)
                t.gm = None
            continue
        if getattr(t, "gm", None) is None:
            g = GM()
            g.team = t.abbr
            g.hired = lg.year
            g.seasons = random.randint(0, 6)
            g.career_seasons = g.seasons + random.randint(0, 6)
            t.gm = g
        if getattr(t, "plan", None) is None:
            t.plan = choose_plan(lg, t, initial=True)


def _roll_power(o):
    meddle = getattr(o, "meddling", 8) if o is not None else 8
    r = random.random()
    if meddle >= 17 and r < 0.6:
        return "Owner-run"
    if r < 0.14:
        return "Coach-led"
    return "GM-led"


def gm_of(team):
    return getattr(team, "gm", None)


def plan_of(team):
    p = getattr(team, "plan", None)
    return p["mode"] if p else NEUTRAL_PLAN


def param(team, key):
    return PLANS[plan_of(team)][key]


# ── Situation assessment ──────────────────────────────────────────────────────

def _qb_status(team):
    qbs = sorted(team.players_at("QB", include_inactive=True), key=lambda p: -p.ovr)
    if not qbs:
        return "searching", None
    q = qbs[0]
    young = [p for p in qbs if p.age <= 24 and p.pot >= 78]
    if q.ovr >= 80 and q.age >= 35:
        return "ageing star", q
    if q.ovr >= 80:
        return "franchise", q
    if young:
        return "developing", young[0]
    if q.ovr >= 73:
        return "bridge", q
    return "searching", q


def assess(lg, team, midseason=False):
    order = lg.strength_order()
    rank = order.index(team.abbr) if team.abbr in order else 16
    n = max(1, len(order) - 1)
    s = 1.0 - rank / n
    rec = lg.standings.get(team.abbr)
    w = 0.5
    if rec is not None and rec.games >= (4 if midseason else 10):
        w = rec.pct
    elif team.history:
        h = team.history[-1]
        g = h["w"] + h["l"] + h["t"]
        w = (h["w"] + 0.5 * h["t"]) / g if g else 0.5
    c = 0.62 * s + 0.38 * w if not midseason else 0.45 * s + 0.55 * w
    top = sorted(team.roster, key=lambda p: -p.ovr)[:22]
    core_age = sum(p.age for p in top) / len(top) if top else 27.0
    young = sum(1 for p in team.roster if p.age <= 25 and p.ovr >= 74)
    stars = sum(1 for p in top if p.ovr >= 85)
    qb_status, qb = _qb_status(team)
    cap = lg.salary_cap
    committed = sum(p.salary for p in team.roster if p.contract and p.contract.get("years", 0) >= 1)
    if lg.phase in ("regular", "playoffs"):
        committed = sum(p.salary for p in team.roster if p.contract and p.contract.get("years", 0) >= 2)
    return dict(rank=rank + 1, s=s, w=w, c=c, core_age=core_age, young=young, stars=stars,
                qb_status=qb_status, qb=qb, cap_load=committed / cap if cap else 0.0)


def _utilities(lg, team, a):
    g = gm_of(team)
    o = owner_traits(team.owner) if getattr(team, "owner", None) else None
    gt = g.t if g else (lambda k: 0.5)
    amb = ((o.ambition if o else 10) - 10) / 10.0
    pat = ((o.patience if o else 10) - 10) / 10.0
    med = ((o.meddling if o else 8) - 8) / 10.0
    c, age, qs = a["c"], a["core_age"], a["qb_status"]
    u = {
        "All-In": 3.0 * (c - 0.70) + 0.55 * (0.5 - gt("patience")) + 0.30 * (gt("risk") - 0.5)
        + 0.25 * amb + (0.25 if qs == "ageing star" else 0.0) + 0.03 * a["stars"] - 0.13,
        "Contend": 3.0 * (c - 0.62) + 0.10,
        "Last Dance": 3.0 * (c - 0.62) + 0.9 * (age - 28.2) + (0.35 if qs == "ageing star" else 0.0) - 0.15,
        "Playoff Push": 0.45 - 5.0 * abs(c - 0.56) + 0.20 * amb + 0.15 * (gt("activity") - 0.5),
        "Stay the Course": 0.42 - 3.0 * abs(c - 0.50) + 0.35 * (0.5 - gt("activity"))
        + 0.25 * (0.5 - gt("risk")),
        "Retool": 0.30 - 4.5 * abs(c - 0.45) + 0.8 * (age - 27.6) + 0.20 * (gt("patience") - 0.5),
        "Youth Movement": 0.20 - 4.0 * abs(c - 0.36) + 0.10 * (a["young"] - 4)
        + (0.35 if qs == "developing" else 0.0) + 0.30 * (gt("youth") - 0.5) + 0.2 * pat,
        "Rebuild": 3.0 * (0.33 - c) + 0.30 * (age - 27.3) + 0.15 * pat + 0.20 * (gt("patience") - 0.5),
        "Tank": 5.0 * (0.24 - c) - 0.12 + 0.65 * (gt("patience") - 0.5) + 0.30 * pat - 0.40 * amb
        - 0.45 * max(0.0, med) + (0.35 if qs == "searching" else 0.0) - (0.4 if qs == "franchise" else 0.0),
        "Cap Reset": 7.0 * (a["cap_load"] - 0.96) - 0.25 - 1.5 * max(0.0, c - 0.60)
        + 0.40 * (gt("cap_disc") - 0.5),
    }
    return u


def _focus(a, mode):
    out = []
    qs = a["qb_status"]
    if qs == "searching" or (qs == "bridge" and mode not in BUYERS):
        out.append("Find a franchise QB")
    elif qs == "ageing star":
        out.append("Groom the QB's successor")
    elif qs == "developing":
        out.append("Develop the young QB")
    if a["cap_load"] > 0.95 and mode != "Cap Reset":
        out.append("Cap is tight")
    if a["core_age"] >= 29.0 and mode in BUYERS:
        out.append("Window is closing")
    if a["young"] >= 7:
        out.append("Lock up the young core")
    return out


def _reason(lg, team, a, mode):
    o = team.owner
    bits = [f"#{a['rank']} roster"]
    if a["core_age"] >= 28.8:
        bits.append(f"veteran core (avg age {a['core_age']:.1f})")
    elif a["core_age"] <= 26.3:
        bits.append(f"young core (avg age {a['core_age']:.1f})")
    q = a["qb"]
    qs = a["qb_status"]
    if q is not None:
        word = {"franchise": "franchise QB", "ageing star": "ageing star QB", "developing": "young QB",
                "bridge": "stopgap QB", "searching": "no answer at QB"}[qs]
        bits.append(f"{word} {q.name}" if qs != "searching" else word)
    if a["cap_load"] > 0.95:
        bits.append(f"{a['cap_load'] * 100:.0f}% of next year's cap committed")
    ot = owner_type(o)
    if ot in ("Win-at-All-Costs", "Showman", "Trigger-Happy") and mode in BUYERS:
        bits.append(f"owner {o.name} wants to win now")
    elif ot in ("Patient Steward", "Traditionalist") and mode in SELLERS:
        bits.append(f"owner {o.name} is willing to wait")
    return "; ".join(bits)


def choose_plan(lg, team, initial=False, midseason=False):
    a = assess(lg, team, midseason=midseason)
    u = _utilities(lg, team, a)
    cur = getattr(team, "plan", None)
    for k in u:
        u[k] += random.gauss(0, 0.10)
    if cur and not initial:
        held = cur["mode"]
        if held in u:
            locked = cur.get("commit_until", 0) >= lg.year
            u[held] += 0.40 if locked else 0.15
            if midseason:
                u[held] += 0.45          # in-season changes need a real surprise
    mode = max(u, key=u.get)
    if cur and cur["mode"] == mode and not initial:
        plan = dict(cur)
        plan["focus"] = _focus(a, mode)
        plan["reason"] = _reason(lg, team, a, mode)
        plan["rank"] = a["rank"]
        return plan
    return {"mode": mode, "since": lg.year, "commit_until": lg.year + PLANS[mode]["commit"] - 1,
            "focus": _focus(a, mode), "reason": _reason(lg, team, a, mode), "rank": a["rank"],
            "history": list((cur or {}).get("history", []))[-12:]}


def _bucket(mode):
    return "buy" if mode in BUYERS else "sell" if mode in SELLERS else "hold"


def update_plans(lg, midseason=False):
    """Every CPU club sets (or reconsiders) its plan. Returns the clubs that changed course."""
    ensure(lg)
    changed = []
    for t in lg.teams.values():
        if t.abbr == lg.user_abbr:
            continue
        old = plan_of(t)
        new = choose_plan(lg, t, midseason=midseason)
        if midseason and new["mode"] != old and _bucket(new["mode"]) == _bucket(old):
            new = dict(t.plan, focus=new["focus"], reason=new["reason"])   # only buy/sell flips mid-season
        if new["mode"] != old:
            new.setdefault("history", []).append((lg.year, old))
            changed.append((t, old, new["mode"]))
            if midseason or new["mode"] in ("Tank", "All-In", "Last Dance", "Rebuild", "Cap Reset"):
                lg.add_news("Front Office", f"{t.full_name} change course: {old} → {new['mode']}. "
                                            f"{PLANS[new['mode']]['desc']} ({new['reason']})", t.abbr)
        t.plan = new
        t.youth_boost = PLANS[new["mode"]]["kids"]
    lg.fo_log.append((lg.year, "midseason" if midseason else "offseason",
                      {t.abbr: plan_of(t) for t in lg.teams.values() if t.abbr != lg.user_abbr}))
    lg.fo_log = lg.fo_log[-60:]
    return changed


# ── Valuation ─────────────────────────────────────────────────────────────────

def _league_pass_rate(lg, years):
    rows = [h.get("averages") or {} for h in lg.history[-years:]]
    vals = [r.get("pass_rate") for r in rows if r.get("pass_rate")]
    return sum(vals) / len(vals) if vals else 56.5


def position_value(lg, team, pos):
    """How much this club's GM values a position (QB = 1.0 scale, like ratings.POSITION_VALUE)."""
    from ratings import POSITION_VALUE
    g = gm_of(team)
    if g is None:
        return POSITION_VALUE[pos]
    an = g.t("analytics")
    v = TRADITIONAL_VALUE[pos] * (1 - an) + ANALYTICS_VALUE[pos] * an
    # Analytics GMs read the last three seasons; old-school ones remember the last fifteen
    pr = _league_pass_rate(lg, 3) if an >= 0.5 else _league_pass_rate(lg, 15)
    v *= 1.0 + PASS_SENSITIVITY.get(pos, 0.0) * (pr - 56.5) / 10.0
    if pos in TRENCH:
        v *= 1.0 + (g.t("trenches") - 0.5) * 0.35
    if pos in DEFENSE:
        v *= 1.0 + (g.t("defense") - 0.5) * 0.30
    elif pos in OFFENSE:
        v *= 1.0 - (g.t("defense") - 0.5) * 0.20
    if pos == "QB":
        v *= ARCH_QB_FOCUS.get(g.archetype, 1.0)
    v *= g.pos_belief.get(pos, 1.0)
    return v


def _noise(g, pid, year):
    """His judgement: a stable personal error on each player each season."""
    sd = (20 - g.judgement) * 0.011
    if sd <= 0:
        return 1.0
    r = random.Random(zlib.crc32(f"{g.name}:{pid}:{year}".encode()))
    return max(0.6, 1.0 + r.gauss(0, sd))


def player_mult(lg, team, p):
    """Multiplier on a player's trade value for this club (1.0 = neutral)."""
    g = gm_of(team)
    if g is None:
        return 1.0
    plan = PLANS[plan_of(team)]
    m = 1.0
    if p.age <= 25:
        m *= plan["youth"] * (1.0 + (g.t("youth") - 0.5) * 0.30)
    elif p.age >= 29:
        k = min(1.0, (p.age - 28) / 3.0)
        m *= (plan["vet"] * (1.0 - (g.t("youth") - 0.5) * 0.30)) ** k
    from ratings import POSITION_VALUE
    m *= (position_value(lg, team, p.position) / POSITION_VALUE[p.position]) ** 0.6
    if p.ovr >= 85:
        m *= 1.0 + (g.t("stars") - 0.5) * 0.40
    elif p.ovr < 72:
        m *= 1.0 - (g.t("stars") - 0.5) * 0.30
    if p.team == team.abbr:
        m *= 1.0 + (g.t("loyalty") - 0.5) * 0.40
        if team.power == "Owner-run" and p.reputation >= 65:
            m *= 1.30                      # the owner won't let a fan favourite go cheaply
    if p.position == "QB" and "Find a franchise QB" in (team.plan or {}).get("focus", ()) and p.ovr >= 76:
        m *= 1.30
    if p.is_injured:
        m *= 1.0 + (g.t("risk") - 0.5) * 0.4
    if team.power == "Coach-led":
        from development import scheme_fit
        m *= 1.0 + 0.08 * scheme_fit(p, team)
        rec = lg.standings.get(team.abbr)
        if team.coach.team_seasons >= 2 and rec is not None and rec.games >= 4 and rec.pct < 0.5:
            m *= 1.10 if p.age >= 28 else 0.94    # a coach on the hot seat wants proven players
    m *= _noise(g, p.id, lg.year)
    return max(0.25, min(2.5, m))


def pick_mult(lg, team, year):
    g = gm_of(team)
    if g is None:
        return 1.0
    m = PLANS[plan_of(team)]["pick"] * (1.0 + (g.t("patience") - 0.5) * 0.40)
    # A GM values his own far-off picks more: nobody knows where he'll be in two years
    if year >= lg.year + 2:
        m *= 1.0 + (g.t("patience") - 0.5) * 0.15
    return max(0.35, min(2.0, m))


def demand(team):
    """Extra value a GM wants before saying yes to a trade (1.0 = even)."""
    g = gm_of(team)
    if g is None:
        return 1.0
    return 1.0 + (g.t("hardness") - 0.5) * 0.18


def activity(team):
    g = gm_of(team)
    return 0.5 if g is None else g.t("activity")


def spend_factor(team):
    """Free-agency budget multiplier: plan x owner wallet x GM appetite."""
    g = gm_of(team)
    o = owner_traits(team.owner)
    f = PLANS[plan_of(team)]["fa"] * (0.72 + o.spending / 20.0 * 0.56)
    if g is not None:
        f *= 1.0 + (g.t("stars") - 0.5) * 0.30 - (g.t("cap_disc") - 0.5) * 0.30
    if team.power == "Owner-run":
        f *= 1.10
    return max(0.25, min(2.0, f))


def cap_reserve(lg, team):
    """Cap space a GM keeps in reserve (dollars)."""
    g = gm_of(team)
    if g is None:
        return 0
    return int(lg.salary_cap * max(0.0, (g.t("cap_disc") - 0.35) * 0.05))


# ── Plan-aware draft board ───────────────────────────────────────────────────

def board_value(lg, team, p, needs, est_ca, est_pa):
    g = gm_of(team)
    risk = g.t("risk") if g else 0.5
    mode = plan_of(team)
    w_pa = 0.42 + 0.26 * risk + (0.06 if mode in ("Rebuild", "Tank", "Youth Movement") else 0.0) \
        - (0.06 if mode in ("All-In", "Last Dance") else 0.0)
    v = est_ca * (1 - w_pa) + est_pa * w_pa + position_value(lg, team, p.position) * 22
    v -= (p.age - 21) * (1.2 + (g.t("youth") if g else 0.5) * 1.6)
    bpa = g.t("bpa") if g else 0.5
    v += needs.get(p.position, 0) * 9 * (1.6 - 1.2 * bpa)
    if p.position == "QB" and "Find a franchise QB" in (getattr(team, "plan", None) or {}).get("focus", ()):
        v += 6
    if p.position in ("K", "P"):
        v -= 22
    if p.position == "FB":
        v -= 12
    if g is not None:
        v *= _noise(g, p.id, lg.year) ** 0.35
    return v


def record_pick(lg, team, player, rnd, pick):
    g = gm_of(team)
    if g is not None:
        g.picks.append((lg.year, player.id, rnd, pick, player.position))
        g.picks = g.picks[-80:]


# ── Trade-deal flavour text ───────────────────────────────────────────────────

def describe(team):
    mode = plan_of(team)
    return {"All-In": "all-in", "Contend": "contending", "Last Dance": "last-dance",
            "Playoff Push": "playoff-chasing", "Stay the Course": "steady", "Retool": "retooling",
            "Youth Movement": "youth-movement", "Rebuild": "rebuilding", "Tank": "tanking",
            "Cap Reset": "cap-strapped"}[mode]


def trade_note(seller, buyer):
    return (f"The {describe(seller)} {seller.name} cash in; the {describe(buyer)} {buyer.name} "
            f"load up.")


# ── Seasonal review: records, learning, hiring and firing ────────────────────

def _recent_pct(team, n=3):
    h = team.history[-n:]
    g = sum(x["w"] + x["l"] + x["t"] for x in h)
    return sum(x["w"] + 0.5 * x["t"] for x in h) / g if g else 0.5


# ── Depth charts: starting a player out of position ───────────────────────────
# CPU staffs fill their depth charts by position, and cover injuries from other
# positions on game day (team.lineup). Once a week they also look for a player
# who would be overwhelmingly better somewhere else than the man starting there
# (OOP_MARGIN CA points, about ten rating points) and start him there. Stars get
# the benefit of the doubt (reputation), and adaptable head coaches try it sooner;
# a player still learning the slot is judged on what he can do there today.

OOP_MARGIN = 17.0
OOP_SLOTS = ("RB", "FB", "WR", "TE", "OT", "IOL", "DT", "EDGE", "LB", "CB", "S")


def oop_margin(team, p):
    """CA points better than the starter a player must be before this staff moves him."""
    m = OOP_MARGIN
    rep = getattr(p, "reputation", 10)
    if rep > 50:
        m -= (rep - 50) / 50.0 * 6.0          # a big name gets the benefit of the doubt
    m -= (team.coach.r("adaptability") - 10) * 0.4
    return max(7.0, m)


def weekly_depth(lg, team, news=True):
    """A CPU staff's out-of-position starters for this week (team.cpu_oop), with news when it changes."""
    if team.abbr == lg.user_abbr:
        team.cpu_oop = None
        return
    old = team.cpu_oop or {}
    team.cpu_oop = {}
    from position_fit import STARTERS
    busy = team.starter_ids()
    pool = [p for p in team.roster if p.id not in busy and not p.ps and not p.ir and not p.holdout
            and not p.is_injured]
    picks = []
    for slot in OOP_SLOTS:
        start = team.depth(slot)[:STARTERS[slot]]
        if len(start) < STARTERS[slot]:
            continue                            # short-handed: game-day cover handles it
        weakest = min(start, key=lambda q: q.rating_at(slot))
        bar = weakest.rating_at(slot)
        for p in pool:
            if p.position == slot:
                continue
            gain = p.rating_at(slot) - bar
            m = oop_margin(team, p)
            if gain >= m:
                picks.append((gain - m, p, slot, weakest))
    picks.sort(key=lambda x: -x[0])
    taken, filled = set(), set()
    for _, p, slot, weakest in picks:
        if p.id in taken or slot in filled:
            continue
        taken.add(p.id)
        filled.add(slot)
        team.cpu_oop[slot] = [p.id]
        if news and p.id not in old.get(slot, []):
            lg.add_news("Depth Chart", f"The {team.name} are starting {p.position} {p.name} at {slot}: "
                                       f"he rates {p.ovr_at(slot)} there, ahead of {weakest.name} "
                                       f"({weakest.ovr_at(slot)}).", team.abbr)
    # A multi-role star also gets a part-time role at a second slot
    old_role = team.cpu_role or {}
    team.cpu_role = {}
    pick = _two_way(team, taken, old_role)
    if pick is not None:
        p, slot, idx, backup = pick
        team.cpu_role[slot] = [p.id, idx]
        if news and (old_role.get(slot) or [None])[0] != p.id:
            behind = f", ahead of {backup.name} ({backup.ovr_at(slot)})" if backup is not None else ""
            lg.add_news("Depth Chart", f"The {team.name} will also use {p.position} {p.name} at {slot}: "
                                       f"he rates {p.ovr_at(slot)} there{behind}.", team.abbr)


def weekly_depth_all(lg, news=True):
    for t in lg.teams.values():
        weekly_depth(lg, t, news)


# ── Two-way and multi-role players ────────────────────────────────────────────
# A star who starts at his own position, is about as good as the starters at a
# second slot and clearly better than its first backup gets that backup role too
# (a receiver who takes handoffs, a corner who plays some receiver, a linebacker
# at tight end on short yardage). He plays one slot per snap and his fatigue
# counts both. Only stars with the stamina for it qualify; adaptable coaches try
# it sooner. Closely related moves (corner and safety, edge and linebacker) are
# left to game-day injury cover.

TWO_WAY_MARGIN = 12.0         # CA points better than the slot's first backup
TWO_WAY_NEAR = 2.0            # ...and no more than this below its weakest starter
TWO_WAY_SLOTS = ("RB", "WR", "TE", "LB", "CB", "S")
TWO_WAY_STAMINA = 70
TWO_WAY_OVR = 85              # a Pro Bowl level player...
TWO_WAY_REP = 70              # ...or a big name
TWO_WAY_SLOT_OVR = 78         # who would be a good starter at the second slot
TWO_WAY_RELATED = 50          # starting familiarity at which a move counts as closely related


def two_way_margin(team, p):
    m = TWO_WAY_MARGIN
    if p.reputation > 50:
        m -= (p.reputation - 50) / 50.0 * 4.0
    m -= (team.coach.r("adaptability") - 10) * 0.4
    return max(3.0, m)


def _two_way(team, taken, old_role):
    from position_fit import STARTERS, start_familiarity
    from ratings import ovr_from_ca
    starters = team.starter_ids()
    keep = {v[0]: s for s, v in old_role.items()}
    best = None
    for p in team.roster:
        if p.id not in starters or p.id in taken or p.ps or p.ir or p.holdout or p.is_injured:
            continue
        if p.position in ("QB", "K", "P", "OT", "IOL", "DT") or p.attrs.get("stamina", 60) < TWO_WAY_STAMINA:
            continue
        if p.ovr < TWO_WAY_OVR and p.reputation < TWO_WAY_REP:
            continue
        for slot in TWO_WAY_SLOTS:
            if slot == p.position or start_familiarity(p.position, slot) >= TWO_WAY_RELATED:
                continue
            n = STARTERS[slot]
            order = [q for q in team.depth(slot) if q.id != p.id]
            v = p.rating_at(slot)
            if ovr_from_ca(v, slot) < TWO_WAY_SLOT_OVR or len(order) < n:
                continue
            if v < min(q.rating_at(slot) for q in order[:n]) - TWO_WAY_NEAR:
                continue
            backup = order[n] if len(order) > n else None
            gain = v - (backup.rating_at(slot) if backup is not None else 0)
            m = two_way_margin(team, p)
            if keep.get(p.id) == slot:
                m -= 3.0                        # the staff stick with a role that is working
            if gain >= m and (best is None or gain - m > best[0]):
                best = (gain - m, p, slot, n, backup)
    return None if best is None else best[1:]


# ── Permanent position changes ────────────────────────────────────────────────
# Each offseason a staff may move a player to a new position for good: a corner
# who has lost a step to safety, a tackle inside to guard, a big receiver to
# tight end, a depth player to where he is better. They judge him on what he
# should be there once he has learned it (and built up or slimmed down for it),
# against what the team loses where he was. Adaptable coaches and teachers, and
# risk-taking GMs, do it more readily. The player's reaction depends on his
# personality (position_fit.move_mood).

CONVERT_MARGIN = 15.0
CONVERT_SLOTS = OOP_SLOTS
MAX_CONVERSIONS = 2
CONVERT_COOLDOWN = 2          # seasons before a staff will move the same player again
# Moves to a position that asks less of his legs: the usual way to extend a veteran's career
AGE_MOVES = {("CB", "S"), ("CB", "LB"), ("S", "LB"), ("EDGE", "LB"), ("EDGE", "DT"), ("LB", "DT"),
             ("WR", "TE"), ("RB", "FB"), ("RB", "TE"), ("TE", "FB"), ("OT", "IOL")}


def convert_margin(team):
    """CA points a conversion must add where he goes before this staff makes it."""
    m = CONVERT_MARGIN
    m -= (team.coach.r("adaptability") - 10) * 0.4
    m -= (team.coach.r("development") - 10) * 0.2
    g = gm_of(team)
    if g is not None:
        m -= (g.t("risk") - 0.5) * 6.0
    return max(5.0, m)


def conversion_options(lg, team):
    """[(score, player, slot, why, projected CA, the man he passes or None)] best first."""
    from position_fit import STARTERS, learned_ca, start_familiarity
    from ratings import ROSTER_MINIMUM
    counts = team.position_counts()
    depth = {s: team.depth(s) for s in CONVERT_SLOTS}
    m = convert_margin(team)
    out = []
    for p in team.roster:
        if p.ps or p.ir or p.holdout or p.position not in CONVERT_SLOTS or p.converted_from:
            continue
        hist = p.position_history or []
        if hist and hist[-1][0] is not None and lg.year - hist[-1][0] < CONVERT_COOLDOWN:
            continue
        if counts[p.position] - 1 < ROSTER_MINIMUM[p.position]:
            continue
        own = depth[p.position]
        n_own = STARTERS[p.position]
        rank = own.index(p) if p in own else len(own)
        cost = 0.0
        if rank < n_own:
            nxt = own[n_own] if len(own) > n_own else None
            cost = p.ca - (nxt.ca if nxt is not None else 40)
            if cost >= oop_margin(team, p):
                continue                        # he would only be started back there out of position
        pv_own = position_value(lg, team, p.position)
        for slot in CONVERT_SLOTS:
            if slot == p.position or (start_familiarity(p.position, slot) < 15 and p.age > 24):
                continue
            fut = learned_ca(p, slot, conditioned=True)
            dest = depth[slot]
            n = STARTERS[slot]
            starters = dest[:n]
            weakest = min(starters, key=lambda q: q.rating_at(slot)) if len(starters) >= n else None
            gain = fut - (weakest.rating_at(slot) if weakest is not None else 0)
            pv = position_value(lg, team, slot)
            if gain >= m and gain * pv > cost * pv_own:
                out.append((gain * pv - cost * pv_own, p, slot, "start", fut, weakest))
            elif rank >= n_own and fut >= p.ca + m * 0.6:
                first_backup = dest[n].rating_at(slot) if len(dest) > n else 0
                if fut >= first_backup:
                    out.append(((fut - p.ca) * pv * 0.5, p, slot, "depth", fut, None))
    out.sort(key=lambda x: -x[0])
    return out


def offseason_conversions(lg):
    """CPU staffs' permanent position changes for the coming season, with news."""
    from position_fit import change_position
    from ratings import POSITION_NAMES, ovr_from_ca
    for team in lg.teams.values():
        if team.abbr == lg.user_abbr:
            continue
        rng = random.Random(zlib.crc32(f"convert:{team.abbr}:{lg.year}".encode()))
        chance = max(0.10, min(0.7, 0.25 + (team.coach.r("adaptability") - 10) * 0.03))
        done, slots = set(), set()
        for _, p, slot, why, fut, weakest in conversion_options(lg, team):
            if len(done) >= MAX_CONVERSIONS:
                break
            if p.id in done or slot in slots or rng.random() > chance:
                continue
            old = p.position
            age = p.age
            d, word = change_position(lg, team, p, slot)
            if not word:
                continue
            done.add(p.id)
            slots.add(slot)
            proj = ovr_from_ca(fut, slot)
            new_name = POSITION_NAMES[slot].lower()
            if why == "start":
                text = (f"The {team.name} are moving {old} {p.name} to {new_name}. The staff expect him "
                        f"to rate about {proj} there once he has learned it")
                if weakest is not None:
                    text += f", ahead of {weakest.name} ({weakest.ovr_at(slot)})"
                text += "."
                if age >= 29 and (old, slot) in AGE_MOVES:
                    text += f" At {age} he has lost a step at {POSITION_NAMES[old].lower()}."
            else:
                text = (f"The {team.name} are moving {old} {p.name} to {new_name}: stuck on the bench at "
                        f"{POSITION_NAMES[old].lower()}, he projects to about {proj} there.")
            lg.add_news("Position Change", f"{text} He is {word}.", team.abbr)


def season_end(lg):
    """After the season: GM records, learning, copycat drift, owner and GM turnover."""
    ensure(lg)
    for t in lg.teams.values():
        g = gm_of(t)
        if g is None:
            continue
        rec = lg.standings[t.abbr]
        g.wins += rec.w
        g.losses += rec.l
        g.ties += rec.t
        g.club_wins += rec.w
        g.club_losses += rec.l
        g.club_ties += rec.t
        g.seasons += 1
        g.career_seasons += 1
        g.age += 1
        ex = lg.playoff_exit.get(t.abbr, -1)
        if ex >= 0:
            g.playoffs += 1
        if ex == 9:
            g.titles += 1
        g.reputation = int(_clamp(g.reputation + (rec.pct - 0.5) * 10 + (5 if ex >= 2 else 0)
                                  + (10 if ex == 9 else 0), 1, 100))
        g.history.append((lg.year, t.abbr, rec.wlt(), plan_of(t),
                          t.history[-1]["result"] if t.history else ""))
        g.history = g.history[-40:]
    _learn_from_drafts(lg)
    _copycat(lg)
    _owner_turnover(lg)
    _gm_carousel(lg)


def _learn_from_drafts(lg):
    """Grade each GM's picks from four drafts ago against everyone else's picks in that round."""
    target = lg.year - 4
    by_id = {p.id: p for p in lg.all_players(include_fa=True)}
    for p in lg.retired[-600:]:
        by_id.setdefault(p.id, p)
    picks = []
    for t in lg.teams.values():
        g = gm_of(t)
        if g is None:
            continue
        for (y, pid, rnd, pk, pos) in g.picks:
            if y == target:
                p = by_id.get(pid)
                picks.append((g, rnd, pos, p.ovr if p is not None and not p.retired else 45))
    if not picks:
        return
    by_round = {}
    for _, rnd, _, ovr in picks:
        by_round.setdefault(rnd, []).append(ovr)
    for g, rnd, pos, ovr in picks:
        vals = by_round[rnd]
        diff = ovr - sum(vals) / len(vals)
        g.draft_graded += 1
        if diff >= 5:
            g.draft_hits += 1
        elif diff <= -6:
            g.draft_misses += 1
        b = g.pos_belief.get(pos, 1.0)
        b *= 1.0 + max(-0.04, min(0.04, diff / 200.0))
        g.pos_belief[pos] = round(_clamp(b, 0.85, 1.15), 3)
    for t in lg.teams.values():
        g = gm_of(t)
        if g is None:
            continue
        for pos in list(g.pos_belief):
            g.pos_belief[pos] = round(1.0 + (g.pos_belief[pos] - 1.0) * 0.96, 3)   # memories fade


def _copycat(lg):
    """The league copies its champions: every GM drifts a little toward the title winner's ideas."""
    if not lg.history:
        return
    champ = lg.teams.get(lg.history[-1].get("champion"))
    model = gm_of(champ) if champ else None
    if model is None:
        return
    for t in lg.teams.values():
        g = gm_of(t)
        if g is None or g is model:
            continue
        k = 0.02 + (0.02 if g.t("analytics") >= 0.6 else 0.0)
        for key in ("analytics", "trenches", "defense", "stars", "youth", "risk"):
            g.traits[key] = round(g.t(key) + (model.t(key) - g.t(key)) * k, 3)


def _owner_turnover(lg):
    from staff import Owner
    for t in lg.teams.values():
        if random.random() < 0.02:
            old = t.owner
            t.owner = owner_traits(Owner())
            t.power = _roll_power(t.owner)
            lg.add_news("Front Office", f"{t.full_name} have a new owner: {t.owner.name} "
                                        f"({owner_type(t.owner)}) buys the club from {old.name}.", t.abbr)


def _gm_carousel(lg):
    """Owners judge their GMs; the fired go to the pool, and replacements come with new ideas."""
    hot = settings["gm_hot_seat"]
    order = lg.strength_order()
    for t in lg.teams.values():
        g = gm_of(t)
        if g is None:
            continue
        o = owner_traits(t.owner)
        recent = _recent_pct(t, 3)
        rec = lg.standings[t.abbr]
        apps = sum(1 for h in t.history[-4:] if h["exit"] >= 0)
        titles_recent = sum(1 for h in t.history[-3:] if h["exit"] == 9)
        bar = 0.50 + (o.ambition - 10) * 0.012
        p = 0.0
        if g.seasons >= 3 and not titles_recent:
            p = max(0.0, (bar - recent) * 3.0)
            if apps == 0 and g.seasons >= 5:
                p += 0.15
            if plan_of(t) in ("Rebuild", "Tank", "Youth Movement") and g.seasons <= 4:
                p *= 0.5                    # the owner signed off on the rebuild
            # a talented roster that keeps losing is the GM's fault too
            rank = order.index(t.abbr) if t.abbr in order else 16
            if rank < 10 and rec.pct < 0.45:
                p += 0.10
        p *= (1.45 - o.patience * 0.045) * hot
        retiring = g.age >= 70 or (g.age >= 64 and random.random() < 0.15)
        if not retiring and random.random() >= min(0.85, p):
            continue
        if retiring:
            lg.add_news("Front Office", f"{t.full_name} general manager {g.name} retires "
                                        f"({g.record_str} as a GM, {g.titles} titles).", t.abbr)
        else:
            lg.add_news("Front Office", f"{t.full_name} fire general manager {g.name} after "
                                        f"{g.seasons} seasons ({g.club_record}).", t.abbr)
            if g.age < 66:
                g.team = None
                g.reputation = max(1, g.reputation - 10)
                lg.gm_pool.append(g)
        t.gm = hire_gm(lg, t, predecessor=g)
        t.plan = choose_plan(lg, t, initial=True)
        t.youth_boost = PLANS[t.plan["mode"]]["kids"]
    lg.gm_pool = sorted(lg.gm_pool, key=lambda x: -x.reputation)[:16]


def _archetype_weights(lg, team, predecessor):
    arch = list(GM_ARCHETYPES)
    w = {a: GM_ARCHETYPES[a][2] for a in arch}
    # Copy the front offices that have been winning titles
    for h in lg.history[-6:]:
        champ = lg.teams.get(h.get("champion"))
        cg = gm_of(champ) if champ else None
        if cg is not None and cg.archetype in w:
            w[cg.archetype] *= 1.30
    o = owner_traits(team.owner)
    if o.ambition >= 14 or o.patience <= 6:
        for a in ("Win-Now Aggressor", "Star Chaser", "Wheeler-Dealer", "Boom-or-Bust Gambler"):
            w[a] *= 1.5
    if o.patience >= 14:
        for a in ("Draft-and-Develop Builder", "Loyalist", "Analytics Disruptor"):
            w[a] *= 1.5
    if o.spending <= 6:
        for a in ("Moneyball Value Hunter", "Draft-and-Develop Builder", "Analytics Disruptor"):
            w[a] *= 1.6
    # Scarcity: a style nobody else is using looks like an edge
    count = {}
    for t in lg.teams.values():
        g = gm_of(t)
        if g is not None:
            count[g.archetype] = count.get(g.archetype, 0) + 1
    for a in arch:
        w[a] /= 1.0 + count.get(a, 0) * 0.25
    if predecessor is not None:
        w[predecessor.archetype] *= 0.35          # owners rarely hire the same man twice
        # ...and lean the opposite way from what just failed
        pv = predecessor.traits
        for a in arch:
            base = GM_ARCHETYPES[a][1]
            dist = sum(abs(base[k] - pv.get(k, 0.5)) for k in ("patience", "risk", "stars", "analytics"))
            w[a] *= 0.7 + dist * 0.5
    return w


def hire_gm(lg, team, predecessor=None):
    roll = random.random()
    new = None
    how = ""
    pool = [g for g in lg.gm_pool if g is not predecessor]
    if pool and roll < 0.30:
        new = max(pool, key=lambda x: x.reputation + x.judgement * 2 + random.uniform(0, 15))
        lg.gm_pool.remove(new)
        how = f"(previously {new.record_str} as a GM)"
    elif roll < 0.62:
        # A lieutenant from a successful front office brings its philosophy with him
        good = sorted((t for t in lg.teams.values() if gm_of(t) is not None and t is not team),
                      key=lambda t: -(_recent_pct(t, 3) + t.titles * 0.01))[:8]
        if good:
            src = random.choice(good)
            sg = gm_of(src)
            if predecessor is not None and sg.archetype == predecessor.archetype:
                good = [t for t in good if gm_of(t).archetype != predecessor.archetype] or [src]
                src = random.choice(good)
                sg = gm_of(src)
            new = GM(archetype=sg.archetype, base=sg.traits)
            new.age = random.randint(34, 48)
            new.judgement = int(_clamp(round(random.gauss(sg.judgement - 1, 3)), 3, 20))
            new.mentor = f"{sg.name} ({src.abbr})"
            how = f"from the {src.full_name} front office under {sg.name}"
    if new is None:
        w = _archetype_weights(lg, team, predecessor)
        arch = random.choices(list(w), weights=list(w.values()))[0]
        new = GM(archetype=arch)
        new.age = random.randint(34, 52)
        how = "a first-time general manager"
    new.team = team.abbr
    new.hired = lg.year
    new.seasons = 0
    new.club_wins = new.club_losses = new.club_ties = 0
    lg.add_news("Front Office", f"{team.full_name} hire {new.name} as general manager — {how}. "
                                f"Style: {new.archetype}.", team.abbr)
    return new


# ── Coach hiring preferences ─────────────────────────────────────────────────

def coach_fit(lg, team, coach):
    """How well a head-coach candidate fits this club's GM and plan (higher = better)."""
    g = gm_of(team)
    mode = plan_of(team)
    v = coach.overall + coach.reputation / 12.0
    if mode in ("Rebuild", "Tank", "Youth Movement", "Retool"):
        v += (coach.r("development") - 10) * 0.35 + (coach_youth_trust(coach) - 0.5) * 3
    elif mode in BUYERS:
        v += (coach.r("game_management") - 10) * 0.25 + coach.reputation / 25.0
    if g is not None:
        aggr = coach.tendencies.get("aggression", 0.45)
        v += (g.t("analytics") - 0.5) * (aggr - 0.45) * 8
        if g.t("defense") >= 0.7:
            v += (coach.r("defense") - coach.r("offense")) * 0.2
        elif g.t("defense") <= 0.3:
            v += (coach.r("offense") - coach.r("defense")) * 0.2
    return v


def owner_coach_patience(team):
    """Multiplier on the chance a struggling coach is fired."""
    o = owner_traits(team.owner)
    f = 1.75 - o.patience * 0.05
    if plan_of(team) in ("Rebuild", "Tank", "Youth Movement") and team.plan.get("since", 0) >= 0:
        f *= 0.6
    g = gm_of(team)
    if g is not None and g.seasons == 0:
        f += 0.35                    # a new GM often wants his own coach
    return f


# ── Summaries for the UI ──────────────────────────────────────────────────────

def plan_summary(lg):
    """Count of CPU clubs on each plan."""
    out = {}
    for t in lg.teams.values():
        if t.abbr == lg.user_abbr:
            continue
        m = plan_of(t)
        out[m] = out.get(m, 0) + 1
    return out


def draft_record(g):
    if not g.draft_graded:
        return "No graded drafts yet"
    return (f"{g.draft_hits} hits, {g.draft_misses} misses in {g.draft_graded} graded picks "
            f"({(g.draft_hits - g.draft_misses) / g.draft_graded * 100:+.0f} net)")
