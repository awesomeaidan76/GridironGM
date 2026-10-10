"""
worldgen.py — create a brand-new league.

Every team is built slot by slot (QB1, QB2, ... CB6) from a team strength
roll, so some franchises start loaded and others are rebuilding, with clear
gaps between them rather than 32 near-identical rosters.
"""
import random

import names
from coach import Coach, OFFENSIVE_SCHEMES, DEFENSIVE_SCHEMES
from contracts import market_value, rookie_salary, make_contract, contract_length
from eras import FOUNDING_LABEL, POS_GROUP, archetype_weights_for, random_landscape
from league import League, TEAM_DATA
from player import generate_player
from position_fit import STARTERS
from ratings import ROSTER_TEMPLATE, POSITIONS
from settings import settings
from team import Team

# Mean CA by depth slot for an average team
SLOT_MEANS = {
    "QB":   [146, 102, 82],
    "RB":   [128, 108, 92, 78],
    "FB":   [102],
    "WR":   [146, 131, 116, 101, 90, 80],
    "TE":   [128, 104, 88],
    "OT":   [142, 132, 102, 86],
    "IOL":  [133, 127, 121, 100, 86],
    "DT":   [138, 124, 108, 95, 82],
    "EDGE": [146, 129, 109, 95, 82],
    "LB":   [132, 121, 104, 90, 80],
    "CB":   [142, 130, 116, 101, 88, 78],
    "S":    [132, 120, 99, 85],
    "K":    [128],
    "P":    [124],
}

# Age profiles: (mean, sd) for starters vs depth
AGE_PROFILE = {
    "QB": (28, 4), "RB": (25, 2.2), "FB": (26, 2.5), "WR": (26, 3),
    "TE": (27, 3), "OT": (27, 3), "IOL": (27, 3), "DT": (27, 3),
    "EDGE": (26, 3), "LB": (26, 2.8), "CB": (26, 2.6), "S": (26, 2.8),
    "K": (29, 5), "P": (29, 5),
}


def _age_for(pos, depth_index):
    mean, sd = AGE_PROFILE[pos]
    if depth_index >= 2:
        mean -= 1.5           # depth skews young (with some old vets)
    age = int(round(random.gauss(mean, sd)))
    lo = 21
    hi = 40 if pos in ("QB", "K", "P") else 35
    if age < lo:
        age = lo + random.randint(0, 3)      # re-spread instead of piling everyone up at 21
    return max(lo, min(hi, age))


def build_roster(team, strength, era, league):
    arch_w = league.archetype_weights
    for pos, n in ROSTER_TEMPLATE.items():
        shift = league.pipeline.get(POS_GROUP[pos], 0.0)
        for i in range(n):
            mean = SLOT_MEANS[pos][min(i, len(SLOT_MEANS[pos]) - 1)]
            sd = 15 if i == 0 else 11
            target = int(round(random.gauss(mean + strength * (1.0 if i < 2 else 0.6) + shift, sd)))
            target = max(45, min(198, target))
            age = _age_for(pos, i)
            # Young stars are rarer than prime-age stars
            if age <= 23 and target > 138:
                target -= random.randint(5, 20)
            p = generate_player(pos, age, target, archetype_weights=arch_w.get(pos),
                                youth=i >= STARTERS.get(pos, 1))
            team.add_player(p)


def assign_initial_contracts(team, cap, year):
    for p in team.roster:
        if p.years_pro <= 3 and p.age <= 25:
            # Still on a rookie deal
            pick = random.randint(1, 260)
            sal = rookie_salary(pick, cap) if pick <= 224 else int(cap * 0.0036)
            p.contract = make_contract(sal, random.randint(1, 4 - min(3, p.years_pro)), year)
            p.on_rookie_deal = True
            rnd = (pick - 1) // 32 + 1
            if pick <= 224:
                p.draft = {"year": year - p.years_pro, "round": rnd,
                           "pick": pick, "team": team.abbr}
        else:
            sal = int(market_value(p, cap) * random.uniform(0.75, 1.15))
            p.contract = make_contract(sal, contract_length(p), year)
            if random.random() < 0.85:
                pick = random.randint(1, 300)
                if pick <= 224:
                    p.draft = {"year": year - p.years_pro, "round": (pick - 1) // 32 + 1,
                               "pick": pick, "team": random.choice(list(TEAM_ABBRS))}
    # Squeeze veterans' pay if the team is over the cap
    limit = cap * random.uniform(0.86, 0.97)
    payroll = sum(p.salary for p in team.roster)
    if payroll > limit:
        vets = [p for p in team.roster if not p.on_rookie_deal]
        vet_pay = sum(p.salary for p in vets)
        rookie_pay = payroll - vet_pay
        scale = max(0.3, (limit - rookie_pay) / max(1, vet_pay))
        for p in vets:
            p.contract["salary"] = max(int(cap * 0.0036), int(p.contract["salary"] * scale))


TEAM_ABBRS = [t[0] for c in TEAM_DATA.values() for d in c.values() for t in d]


def _weighted_choice(table):
    keys = [k for k, v in table.items() if v > 0]
    return random.choices(keys, weights=[table[k] for k in keys], k=1)[0]


def make_coach(preset):
    c = Coach()
    c.off_scheme = _weighted_choice(preset["schemes"])
    c.def_scheme = _weighted_choice(preset["defenses"])
    c.set_tendencies()
    c.tendencies["aggression"] = max(0.0, min(1.0, random.gauss(preset["aggression"], 0.15)))
    c.seasons = random.randint(0, 14)
    c.team_seasons = random.randint(0, min(6, c.seasons))
    g = c.seasons * 17
    c.career_wins = int(g * random.uniform(0.38, 0.62))
    c.career_losses = g - c.career_wins
    c.reputation = int(max(10, min(95, 30 + c.overall * 2.5 + c.seasons * 1.2
                                   + random.gauss(0, 8))))
    return c


def new_league(name="Gridiron Football League", user_abbr=None, seed=None, year=2026):
    if seed is not None:
        random.seed(seed)
    preset = random_landscape()
    era = FOUNDING_LABEL
    lg = League(name, era)
    lg.year = year
    lg.founded = year
    lg.salary_cap = settings["salary_cap"]
    lg.pipeline = dict(preset["pipeline"])
    lg.pipeline_drift = {g: v * 0.3 for g, v in preset["pipeline"].items()}
    lg.archetype_weights = archetype_weights_for(preset)

    # Team strengths: spread so there are real contenders and real rebuilders
    strengths = sorted([random.gauss(0, 6) for _ in range(32)])
    random.shuffle(strengths)
    i = 0
    for conf, divs in TEAM_DATA.items():
        lg.structure[conf] = {}
        for div, teams in divs.items():
            lg.structure[conf][div] = []
            for abbr, city, nick, colors in teams:
                t = Team(abbr, city, nick, conf, div, colors)
                t.coach = make_coach(preset)
                build_roster(t, strengths[i], era, lg)
                assign_initial_contracts(t, lg.salary_cap, lg.year)
                lg.teams[abbr] = t
                lg.structure[conf][div].append(abbr)
                i += 1

    # Free-agent pool: veterans and fringe players nobody signed
    for _ in range(140):
        pos = random.choices(POSITIONS, weights=[ROSTER_TEMPLATE[p] for p in POSITIONS])[0]
        age = random.randint(23, 34)
        target = int(max(45, min(140, random.gauss(92, 15))))
        p = generate_player(pos, age, target, archetype_weights=lg.archetype_weights.get(pos))
        lg.free_agents.append(p)

    # Unemployed coaches
    lg.coach_pool = [make_coach(preset) for _ in range(12)]
    for c in lg.coach_pool:
        c.team_seasons = 0

    import roster_rules
    import staff as staff_mod
    roster_rules.seed_practice_squads(lg)
    staff_mod.ensure_league(lg)
    if user_abbr:
        lg.user_abbr = user_abbr
    from season import start_new_season
    start_new_season(lg, first=True)
    return lg
