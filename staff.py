"""
staff.py — the people around the roster: coordinators, position coaches,
scouts and the owner.

  * Coordinators call the plays. A team's play-calling strength blends the
    head coach with his coordinator (a defensive-minded head coach leans on
    his offensive coordinator, and vice versa).
  * Position coaches teach. Development at each position depends mostly on
    that room's coach, then the coordinator and the head coach.
  * Scouts cover regions of the college map. Every week of the season they
    learn more about the prospects in their region; teams can also put
    prospects on a focus list. The less a team knows about a prospect, the
    wider (and less reliable) its estimates.
  * The owner sets an expectation each season and judges the general
    manager (the player) against it. Fall far enough short and you're fired.
"""
import random
import zlib

import names
from settings import settings

# role: (title, positions taught, coordinator side)
STAFF_ROLES = {
    "OC":  ("Offensive Coordinator", ["QB", "RB", "FB", "WR", "TE", "OT", "IOL"], "off"),
    "DC":  ("Defensive Coordinator", ["DT", "EDGE", "LB", "CB", "S"], "def"),
    "QBC": ("Quarterbacks Coach", ["QB"], "off"),
    "RBC": ("Running Backs Coach", ["RB", "FB"], "off"),
    "WRC": ("Receivers Coach", ["WR", "TE"], "off"),
    "OLC": ("Offensive Line Coach", ["OT", "IOL"], "off"),
    "DLC": ("Defensive Line Coach", ["DT", "EDGE"], "def"),
    "LBC": ("Linebackers Coach", ["LB"], "def"),
    "DBC": ("Defensive Backs Coach", ["CB", "S"], "def"),
    "STC": ("Special Teams Coach", ["K", "P"], "st"),
}
POSITION_COACH = {pos: role for role, (_, poss, _) in STAFF_ROLES.items()
                  if role not in ("OC", "DC") for pos in poss}

REGIONS = ["West", "Southwest", "Midwest", "South", "Southeast", "Northeast"]
_COLLEGE_REGION = {
    "West": ["USC", "UCLA", "Stanford", "California", "Oregon", "Oregon State", "Washington",
             "Washington State", "Utah", "BYU", "Boise State", "San Diego State",
             "Fresno State", "Colorado", "Air Force", "Arizona", "Arizona State"],
    "Southwest": ["Texas", "Texas A&M", "Oklahoma", "Oklahoma State", "TCU", "Baylor",
                  "Texas Tech", "Houston", "SMU", "Kansas State", "Iowa State"],
    "Midwest": ["Ohio State", "Michigan", "Michigan State", "Notre Dame", "Wisconsin", "Iowa",
                "Nebraska", "Minnesota", "Purdue", "Illinois", "Northwestern", "Missouri",
                "Toledo", "Western Michigan", "Central Michigan", "Northern Illinois",
                "Cincinnati"],
    "South": ["Alabama", "LSU", "Auburn", "Ole Miss", "Mississippi St.", "Arkansas", "Tennessee",
              "Memphis", "Tulane", "Kentucky", "Louisville"],
    "Southeast": ["Georgia", "Florida", "Florida State", "Miami", "Clemson", "South Carolina",
                  "UCF", "Coastal Carolina", "Appalachian St.", "North Carolina", "NC State",
                  "Duke", "Wake Forest", "Virginia Tech", "Liberty"],
    "Northeast": ["Penn State", "Pittsburgh", "Maryland", "Rutgers", "Boston College",
                  "Syracuse", "West Virginia", "Marshall", "Navy"],
}
COLLEGE_REGION = {c: r for r, cs in _COLLEGE_REGION.items() for c in cs}


def college_region(college):
    if college in COLLEGE_REGION:
        return COLLEGE_REGION[college]
    return REGIONS[zlib.crc32((college or "").encode()) % len(REGIONS)]


def _clamp(v, lo=1, hi=20):
    return max(lo, min(hi, int(round(v))))


class StaffMember:
    def __init__(self, role, quality=None):
        self.name = names.random_name()
        self.role = role
        q = quality if quality is not None else random.gauss(10.5, 3.0)
        self.age = random.randint(30, 64)
        self.ratings = {
            "teaching": _clamp(random.gauss(q, 2.5)),
            "tactics": _clamp(random.gauss(q, 2.5)),
            "motivation": _clamp(random.gauss(q - 0.5, 3.0)),
        }
        self.reputation = _clamp(q * 4 + random.gauss(0, 8), 1, 100)
        self.seasons = 0

    def r(self, key):
        return self.ratings.get(key, 10)

    @property
    def title(self):
        return STAFF_ROLES[self.role][0]

    @property
    def overall(self):
        if self.role in ("OC", "DC"):
            return self.r("tactics") * 0.55 + self.r("teaching") * 0.30 + self.r("motivation") * 0.15
        return self.r("teaching") * 0.65 + self.r("tactics") * 0.20 + self.r("motivation") * 0.15


class Scout:
    def __init__(self, quality=None, region=None):
        self.name = names.random_name()
        q = quality if quality is not None else random.gauss(10.5, 3.2)
        self.age = random.randint(28, 66)
        self.ability = _clamp(random.gauss(q, 2.5))        # judging current ability
        self.potential = _clamp(random.gauss(q, 2.5))      # judging potential
        self.region = region or random.choice(REGIONS)
        self.reputation = _clamp(q * 4 + random.gauss(0, 8), 1, 100)

    @property
    def overall(self):
        return (self.ability + self.potential) / 2.0


class Owner:
    spending = None          # 1-20 (front_office.owner_traits fills these in for older saves)
    meddling = None

    def __init__(self):
        self.name = names.random_name()
        self.patience = _clamp(random.gauss(10, 4))       # 1 = trigger-happy, 20 = saint
        self.ambition = _clamp(random.gauss(11, 4))       # how high the bar is set


# ── Setup ─────────────────────────────────────────────────────────────────────

def ensure_staff(team, quality_bias=0.0):
    """Create coordinators, position coaches, scouts and an owner if missing."""
    if not getattr(team, "staff", None):
        base = 10.0 + (team.facilities - 12) * 0.15 + quality_bias
        team.staff = {role: StaffMember(role, random.gauss(base, 2.5)) for role in STAFF_ROLES}
    if getattr(team, "scouts", None) is None:
        n = 2 + (1 if team.scouting >= 10 else 0) + (1 if team.scouting >= 16 else 0)
        regions = random.sample(REGIONS, n)
        team.scouts = [Scout(random.gauss(8 + team.scouting * 0.3, 2.5), r) for r in regions]
    if getattr(team, "owner", None) is None:
        team.owner = Owner()
    if not hasattr(team, "scout_focus"):
        team.scout_focus = []


def ensure_league(lg):
    for t in lg.teams.values():
        ensure_staff(t)
    if not getattr(lg, "staff_pool", None):
        lg.staff_pool = [StaffMember(random.choice(list(STAFF_ROLES))) for _ in range(30)]
    if not getattr(lg, "scout_pool", None):
        lg.scout_pool = [Scout() for _ in range(12)]
    if not hasattr(lg, "scout_knowledge"):
        lg.scout_knowledge = {}
    if not hasattr(lg, "gm"):
        lg.gm = {"reputation": 45, "confidence": 60, "seasons": 0, "history": [],
                 "expectation": None, "fired": False, "offers": []}


# ── Effects on play and development ──────────────────────────────────────────

def off_calling(team):
    """Offensive play-calling (1-20): head coach blended with his coordinator."""
    st = getattr(team, "staff", None)
    hc = team.coach.r("offense")
    if not st:
        return hc
    return hc * 0.45 + st["OC"].r("tactics") * 0.55


def st_calling(team):
    """Special-teams coaching (1-20)."""
    st = getattr(team, "staff", None)
    if not st or "STC" not in st:
        return 10.0
    return st["STC"].r("tactics")


def def_calling(team):
    st = getattr(team, "staff", None)
    hc = team.coach.r("defense")
    if not st:
        return hc
    return hc * 0.45 + st["DC"].r("tactics") * 0.55


def dev_rating(team, position):
    """Teaching quality (1-20) a player at this position gets."""
    if team is None:
        return 8.0
    hc = team.coach.r("development")
    st = getattr(team, "staff", None)
    if not st:
        return hc
    pc = st.get(POSITION_COACH.get(position, "STC"))
    side = STAFF_ROLES[POSITION_COACH.get(position, "STC")][2]
    coord = st["OC"] if side == "off" else st["DC"] if side == "def" else None
    v = hc * 0.30 + (pc.r("teaching") if pc else hc) * 0.50
    v += (coord.r("teaching") if coord else hc) * 0.20
    return v


# ── Scouting knowledge ───────────────────────────────────────────────────────

FOCUS_LIMIT = 12


def knowledge(lg, team_abbr, pid):
    return getattr(lg, "scout_knowledge", {}).get(team_abbr, {}).get(pid, 0.0)


def _scout_skill(team, region, kind):
    best = [s for s in getattr(team, "scouts", []) or [] if s.region == region]
    if best:
        s = max(best, key=lambda x: x.overall)
        return s.ability if kind == "ca" else s.potential
    all_s = getattr(team, "scouts", []) or []
    if all_s:
        return sum(s.ability if kind == "ca" else s.potential for s in all_s) / len(all_s) * 0.8
    return team.scouting * 0.7


def weekly_scouting(lg):
    """Every team's scouts watch prospects in their regions."""
    ensure_league(lg)
    cls = lg.draft_class
    if not cls:
        return
    for team in lg.teams.values():
        kmap = lg.scout_knowledge.setdefault(team.abbr, {})
        covered = {}
        for s in getattr(team, "scouts", []) or []:
            covered[s.region] = max(covered.get(s.region, 0), s.overall)
        focus = set(getattr(team, "scout_focus", []))
        dept = team.scouting / 20.0
        for p in cls:
            region = college_region(p.college)
            k = kmap.get(p.id, 0.0)
            gain = 0.6 + dept * 0.6                      # film and word of mouth
            if region in covered:
                gain += 2.8 + covered[region] / 5.0
            if p.id in focus:
                gain += 5.0 + dept * 2.0
            kmap[p.id] = min(100.0, k + gain)


def combine_bump(lg):
    """The scouting combine: every team learns something about everyone."""
    ensure_league(lg)
    for team in lg.teams.values():
        kmap = lg.scout_knowledge.setdefault(team.abbr, {})
        for p in lg.draft_class:
            kmap[p.id] = min(100.0, kmap.get(p.id, 0.0) + 12 + team.scouting * 0.4)


def estimate(lg, team, p):
    """
    (est CA, est PA, error width CA, error width PA) a team believes about a
    prospect. Deterministic per team and prospect, so boards are stable.
    """
    k = knowledge(lg, team.abbr, p.id) / 100.0
    region = college_region(p.college)
    sk_ca = _scout_skill(team, region, "ca")
    sk_pa = _scout_skill(team, region, "pa")
    err_ca = 2.0 + (1.0 - k) * 14.0 + (20 - sk_ca) * 0.25
    err_pa = (4.0 + (1.0 - k) * 22.0 + (20 - sk_pa) * 0.45) * {"Raw": 1.3, "Normal": 1.0,
                                                               "Polished": 0.8}[p.dev_profile()]
    rng = random.Random(zlib.crc32(f"{team.abbr}:{p.id}".encode()))
    z1, z2 = rng.gauss(0, 1), rng.gauss(0, 1)
    # Knowledge shrinks the error *and* the bias of the estimate
    return (p.ca + z1 * err_ca * 0.6, p.pa + z2 * err_pa * 0.6, err_ca, err_pa)


def toggle_focus(lg, team, pid):
    ensure_staff(team)
    if pid in team.scout_focus:
        team.scout_focus.remove(pid)
        return True, "Removed from your scouting focus list."
    if len(team.scout_focus) >= FOCUS_LIMIT:
        return False, f"Your scouts can only focus on {FOCUS_LIMIT} prospects at a time."
    team.scout_focus.append(pid)
    return True, "Your scouts will make this prospect a priority."


def reset_scouting(lg):
    """A new draft class: start over."""
    lg.scout_knowledge = {}
    for t in lg.teams.values():
        t.scout_focus = []


# ── Hiring ────────────────────────────────────────────────────────────────────

def hire_staff(lg, team, member):
    old = team.staff.get(member.role)
    if member in lg.staff_pool:
        lg.staff_pool.remove(member)
    if old is not None:
        old.seasons = 0
        lg.staff_pool.append(old)
    team.staff[member.role] = member
    member.seasons = 0
    lg.add_news("Coaching", f"{team.full_name} hire {member.name} as {member.title.lower()}.",
                team.abbr)


def hire_scout(lg, team, scout, replace=None):
    if scout in lg.scout_pool:
        lg.scout_pool.remove(scout)
    if replace is not None and replace in team.scouts:
        team.scouts.remove(replace)
        lg.scout_pool.append(replace)
    elif len(team.scouts) >= 5:
        return False, "You already employ five scouts. Replace one instead."
    team.scouts.append(scout)
    return True, f"{scout.name} joins your scouting department ({scout.region})."


def staff_offseason(lg):
    """Ageing, retirements, poaching of good coordinators, and refilling pools."""
    ensure_league(lg)
    for team in lg.teams.values():
        for role, m in list(team.staff.items()):
            m.age += 1
            m.seasons += 1
            # Small growth for younger staff, decline for old
            for k in m.ratings:
                if m.age < 45 and random.random() < 0.25:
                    m.ratings[k] = _clamp(m.ratings[k] + 1)
                elif m.age > 62 and random.random() < 0.3:
                    m.ratings[k] = _clamp(m.ratings[k] - 1)
            leave = m.age >= 70 or (m.age >= 64 and random.random() < 0.25)
            if team.abbr != lg.user_abbr and not leave and random.random() < 0.10:
                leave = True                                   # moves on
            if leave:
                team.staff[role] = _best_from_pool(lg, role) or StaffMember(role)
                if team.abbr == lg.user_abbr:
                    lg.add_news("Coaching", f"Your {m.title.lower()} {m.name} has left the club. "
                                            f"{team.staff[role].name} takes over.", team.abbr)
        for s in getattr(team, "scouts", []):
            s.age += 1
    lg.staff_pool = [m for m in lg.staff_pool if m.age < 70]
    while len(lg.staff_pool) < 30:
        lg.staff_pool.append(StaffMember(random.choice(list(STAFF_ROLES))))
    lg.scout_pool = [s for s in lg.scout_pool if s.age < 72]
    while len(lg.scout_pool) < 12:
        lg.scout_pool.append(Scout())


def _best_from_pool(lg, role):
    cands = [m for m in lg.staff_pool if m.role == role]
    if not cands:
        return None
    m = max(cands, key=lambda x: x.overall + random.gauss(0, 1.5))
    lg.staff_pool.remove(m)
    return m


def peek_coordinator(lg, exclude_team):
    """A hot coordinator elsewhere who could be hired as a head coach: (team, member) or None."""
    best = []
    for t in lg.teams.values():
        if t is exclude_team:
            continue
        for role in ("OC", "DC"):
            m = t.staff.get(role)
            if m and m.overall >= 13:
                best.append((m.overall + t.overall / 40.0, t, m))
    if not best:
        return None
    best.sort(key=lambda x: -x[0])
    _, t, m = random.choice(best[:5])
    return t, m


def take_coordinator(lg, t, m):
    """Hire coordinator m away from team t (t refills the job from the pool)."""
    if t.staff.get(m.role) is m:
        t.staff[m.role] = _best_from_pool(lg, m.role) or StaffMember(m.role)


def promote_coordinator(lg, exclude_team):
    """A hot coordinator elsewhere gets a head-coaching job. Returns (team, member) or None."""
    best = []
    for t in lg.teams.values():
        if t is exclude_team:
            continue
        for role in ("OC", "DC"):
            m = t.staff.get(role)
            if m and m.overall >= 13:
                best.append((m.overall + t.overall / 40.0, t, m))
    if not best:
        return None
    best.sort(key=lambda x: -x[0])
    _, t, m = random.choice(best[:5])
    t.staff[m.role] = _best_from_pool(lg, m.role) or StaffMember(m.role)
    return t, m


# ── The owner and job security ────────────────────────────────────────────────

EXPECTATIONS = [
    # (label, minimum wins, playoff round needed: -1 none, 0 make, 2 divisional+, 9 title)
    ("Win the championship", 12, 8),
    ("Reach the conference championship", 11, 3),
    ("Win a playoff game", 10, 1),
    ("Make the playoffs", 9, 0),
    ("Finish with a winning record", 9, -1),
    ("Compete for a winning record", 8, -1),
    ("Show progress", 6, -1),
    ("Rebuild — develop young talent", 4, -1),
]


def set_expectation(lg):
    """Owner's goal for the user's team this season, from where the roster ranks."""
    ensure_league(lg)
    team = lg.user_team
    if team is None:
        return
    ranks = sorted(lg.teams.values(), key=lambda t: -t.overall)
    rank = ranks.index(team) + 1
    amb = team.owner.ambition
    shift = -1 if amb >= 15 else (1 if amb <= 6 else 0)
    idx = 0 if rank <= 2 else 1 if rank <= 5 else 2 if rank <= 9 else 3 if rank <= 14 else \
        4 if rank <= 18 else 5 if rank <= 23 else 6 if rank <= 28 else 7
    idx = max(0, min(len(EXPECTATIONS) - 1, idx + shift))
    label, wins, rnd = EXPECTATIONS[idx]
    lg.gm["expectation"] = {"year": lg.year, "label": label, "wins": wins, "round": rnd,
                            "rank": rank}


def weekly_confidence(lg, result):
    """Small swings after every game of the user's team."""
    ensure_league(lg)
    team = lg.user_team
    if team is None or result is None:
        return
    me = team.abbr
    won = result.winner == me
    lost = result.winner is not None and not won
    margin = result.score_of(me) - result.score_of(result.opponent(me))
    d = (1.0 if won else -1.4 if lost else 0.0) + max(-1.5, min(1.0, margin / 20.0))
    patience = team.owner.patience
    d *= 1.15 - patience / 40.0
    g = lg.gm
    g["confidence"] = max(0.0, min(100.0, g["confidence"] + d))


def season_review(lg):
    """
    End of season: the owner compares the season with his expectation.
    Returns (verdict text, fired bool).
    """
    ensure_league(lg)
    team = lg.user_team
    g = lg.gm
    if team is None:
        return "", False
    exp = g.get("expectation") or {"label": "Compete", "wins": 8, "round": -1}
    rec = lg.standings[team.abbr]
    exit_round = lg.playoff_exit.get(team.abbr, -1)
    wins = rec.w + rec.t * 0.5
    score = (wins - exp["wins"]) * 4.0
    if exp["round"] >= 0:
        reached = exit_round if exit_round >= 0 else -1
        score += 10 if reached >= exp["round"] else -8 - 3 * (exp["round"] - max(reached, -1))
    if exit_round == 9:
        score += 18
    elif exit_round >= 0:
        score += 4
    # A young team that improved gets some grace
    young = [p for p in team.roster if p.age <= 25 and p.ovr >= 75]
    score += min(6, len(young))
    patience = team.owner.patience
    score *= 1.15 - patience / 40.0
    g["confidence"] = max(0.0, min(100.0, g["confidence"] * 0.6 + 40 + score * 1.5 - 16))
    g["seasons"] += 1
    met = score >= 0
    g["reputation"] = max(1, min(100, g["reputation"] + (6 if met else -5)
                                + (10 if exit_round == 9 else 0)))
    g["history"].append({"year": lg.year, "team": team.abbr, "record": rec.wlt(),
                         "expectation": exp["label"], "met": met, "confidence": round(g["confidence"])})
    fired = g["confidence"] < 22 and g["seasons"] >= 2 and random.random() < 0.85
    if g["seasons"] < 2 and g["confidence"] < 10:
        fired = True
    if not settings["gm_can_be_fired"]:
        fired = False
    if fired:
        g["fired"] = True
        g["offers"] = job_offers(lg)
        text = (f"{team.owner.name} has fired you after a {rec.wlt()} season. "
                f"The goal was: {exp['label'].lower()}.")
        lg.add_news("Front Office", text, team.abbr)
        return text, True
    mood = "delighted" if g["confidence"] >= 80 else "pleased" if g["confidence"] >= 60 else \
        "concerned" if g["confidence"] >= 35 else "losing patience"
    text = (f"Owner {team.owner.name} is {mood} ({round(g['confidence'])}% confidence). "
            f"Goal was: {exp['label'].lower()} — {'met' if met else 'not met'}.")
    lg.add_news("Front Office", text, team.abbr)
    return text, False


def job_offers(lg):
    """Teams willing to hire the user, worst teams (and your reputation) first."""
    rep = lg.gm["reputation"]
    teams = [t for t in lg.teams.values() if t.abbr != lg.user_abbr]
    teams.sort(key=lambda t: t.overall)
    n = 2 + rep // 25
    pool = teams[: max(4, 16 - rep // 6)]
    random.shuffle(pool)
    return [t.abbr for t in pool[:n]]


def take_job(lg, abbr):
    old = lg.user_abbr
    lg.user_abbr = abbr
    g = lg.gm
    g["fired"] = False
    g["offers"] = []
    g["confidence"] = 55
    g["seasons"] = 0
    team = lg.teams[abbr]
    if team.tactics is None:
        from season import default_tactics
        team.tactics = default_tactics()
    lg.add_news("Front Office", f"You have been appointed general manager of the "
                               f"{team.full_name} (previously {old}).", abbr)
    set_expectation(lg)
