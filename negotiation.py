"""
negotiation.py — contract talks with agents, contract structure and holdouts.

No UI code. A contract has:
  salary      cap hit per season (average per year; prorated bonus included)
  years       seasons left
  length      seasons at signing
  bonus       signing bonus (paid up front, spread over the cap evenly)
  guaranteed  total guaranteed money (bonus included)
  guar_left   guaranteed salary still to be paid (after the bonus)

Talks run in rounds. Each player has an agent (hardball, business-like or
easy-going) with limited patience, and his own priorities: money, security
(guarantees and years), winning, a starting role and loyalty to his club.
Lowball offers use up patience fast; when it runs out the agent stops
talking until the next phase of the calendar.
"""
import random
import zlib

from contracts import asking_salary, contract_length, fmt_money, market_value, min_salary

AGENT_STYLES = {
    "Hardball":  {"tough": 0.85, "patience": 4, "drop": 0.010,
                  "desc": "Squeezes every dollar and walks away from lowballs"},
    "Business":  {"tough": 0.55, "patience": 5, "drop": 0.018,
                  "desc": "Wants a fair market deal; will meet in the middle"},
    "Easygoing": {"tough": 0.30, "patience": 6, "drop": 0.025,
                  "desc": "Values the relationship; flexible on structure"},
}
_AGENT_FIRST = ["Drew", "Jordan", "Casey", "Morgan", "Riley", "Avery", "Quinn", "Parker", "Reese", "Rowan",
                "Taylor", "Blake", "Cameron", "Dakota", "Emerson", "Finley", "Harper", "Jules", "Kendall", "Logan"]
_AGENT_LAST = ["Rosenhaus", "Segal", "Hollins", "Mercer", "Dunn", "Kaplan", "Whitfield", "Brandt", "Okafor",
               "Lindqvist", "Marsh", "Castellano", "Pryor", "Vance", "Holloway", "Nakamura", "Barrett", "Sloane"]


def _rng(p, tag):
    return random.Random(zlib.crc32(f"{tag}:{p.id}".encode()))


def agent(p):
    """The player's agent (stable for his career)."""
    r = _rng(p, "agent")
    amb = p.hidden.get("ambition", 50)
    w = {"Hardball": 0.6 + amb / 60.0, "Business": 1.6, "Easygoing": 1.4 - amb / 100.0}
    names = list(w)
    style = r.choices(names, weights=[w[n] for n in names])[0]
    return {"name": f"{r.choice(_AGENT_FIRST)} {r.choice(_AGENT_LAST)}", "style": style, **AGENT_STYLES[style]}


def priorities(lg, team, p, resign):
    """Weights (sum 1) the player puts on money, security, winning, role and loyalty."""
    amb = p.hidden.get("ambition", 50) / 100.0
    inj = min(1.0, len(getattr(p, "injury_history", [])) / 4.0)
    age = p.age
    pr = {
        "money": 0.30 + 0.25 * amb,
        "security": 0.12 + (0.18 if age >= 29 else 0.0) + 0.12 * inj,
        "winning": 0.08 + (0.14 if age >= 30 else 0.0) + 0.06 * amb,
        "role": 0.10 + (0.10 if age <= 26 else 0.0),
        "loyalty": (0.05 + max(0.0, (p.morale - 55) / 150.0)) if resign else 0.0,
    }
    tot = sum(pr.values())
    return {k: v / tot for k, v in pr.items()}


def _quality(p):
    return max(0.0, min(1.0, (p.ca - 95) / 90.0))


def default_structure(p, salary, years):
    """Bonus and guarantees a typical deal of this size carries (used for AI deals)."""
    q = _quality(p)
    total = salary * years
    g_share = 0.10 + 0.50 * q ** 1.2
    if p.age >= 31:
        g_share *= 0.75
    guar = int(total * min(0.9, g_share))
    bonus = int(guar * (0.45 + 0.15 * q))
    return bonus, guar


def make(salary, years, season, bonus=0, guaranteed=0):
    bonus = max(0, int(bonus))
    guaranteed = max(bonus, int(guaranteed))
    base = salary - bonus / max(1, years)
    return {"salary": int(salary), "years": int(years), "signed": season, "length": int(years),
            "bonus": bonus, "guaranteed": guaranteed,
            "guar_left": int(max(0, min(guaranteed - bonus, base * years)))}


def tick(contract):
    """Called when a season ends: a year of salary has been paid."""
    if contract and "length" in contract:
        base = contract["salary"] - contract.get("bonus", 0) / max(1, contract["length"])
        contract["guar_left"] = int(max(0, contract.get("guar_left", 0) - base))


def dead_money(contract, in_season):
    """Cap charge left behind if the player is released now."""
    if not contract:
        return 0
    if "length" not in contract:          # older contracts: the original rule of thumb
        frac = 0.5 if in_season else 0.25
        if contract["years"] > 1:
            frac += 0.15
        return int(contract["salary"] * frac)
    pro = contract.get("bonus", 0) / max(1, contract["length"]) * max(0, contract["years"])
    return int(pro + contract.get("guar_left", 0))


# ── Talks ─────────────────────────────────────────────────────────────────────

def _state(lg, team, p, resign):
    talks = lg.negotiations if getattr(lg, "negotiations", None) is not None else {}
    lg.negotiations = talks
    key = f"{p.id}"
    st = talks.get(key)
    stamp = (lg.year, lg.phase)
    if st is None or st.get("stamp") != stamp or st.get("team") != team.abbr:
        ag = agent(p)
        yrs = contract_length(p) if not resign else max(1, min(5, contract_length(p) + (1 if p.age >= 29 else 0)))
        st = {"stamp": stamp, "team": team.abbr, "round": 0, "patience": ag["patience"], "closed": False,
              "years_pref": yrs, "resign": resign, "history": []}
        talks[key] = st
    return st


def demands(lg, team, p, resign, mood=1.0):
    """What the player wants: average per year, years, guaranteed share and bonus share."""
    from free_agency import team_appeal
    cap = lg.salary_cap
    ask = asking_salary(p, cap, mood)
    if resign:
        ask *= 1.0 - (p.morale - 60) / 400.0          # hometown discount for a happy player
    else:
        ask *= 1.10 - (team_appeal(lg, team, p) - 0.8) * 0.5
    ag = agent(p)
    ask *= 0.97 + ag["tough"] * 0.08
    st = _state(lg, team, p, resign)
    q = _quality(p)
    pr = priorities(lg, team, p, resign)
    g_pref = min(0.85, 0.12 + 0.50 * q ** 1.2 + pr["security"] * 0.35)
    return {"apy": max(min_salary(cap), int(ask)), "years": st["years_pref"],
            "guar": g_pref, "bonus": g_pref * 0.55, "prio": pr, "agent": ag}


def offer_value(lg, team, p, dem, apy, years, bonus, guaranteed, resign):
    """What an offer is worth to the player, in 'APY he'd accept' terms."""
    from free_agency import team_appeal
    pr = dem["prio"]
    total = max(1, apy * years)
    g = guaranteed / total
    b = bonus / total
    v = apy
    v *= 1.0 + (g - dem["guar"]) * (0.25 + 0.9 * pr["security"])
    v *= 1.0 + (b - dem["bonus"]) * 0.10
    off = years - dem["years"]
    if off < 0:
        v *= 1.0 + off * (0.02 + 0.10 * pr["security"])       # fewer years than he wants
    elif off > 0:
        v *= 1.0 - off * (0.035 if p.age <= 27 else 0.0)        # young players don't want to be locked in
    if not resign:
        appeal = team_appeal(lg, team, p)
        v *= 1.0 + (appeal - 1.0) * (pr["winning"] + pr["role"])
    return v


def respond(lg, team, p, apy, years, bonus, guaranteed, resign, mood=1.0):
    """
    One round of talks. Returns (result, message, counter) where result is
    'accept', 'counter' or 'walk'. counter is a suggested offer dict or None.
    """
    st = _state(lg, team, p, resign)
    dem = demands(lg, team, p, resign, mood)
    ag = dem["agent"]
    if st["closed"]:
        return "walk", (f"{ag['name']} ({p.name}'s agent) isn't taking your calls any more. "
                        f"Try again later in the year."), None
    if years < 1 or years > 5:
        return "counter", "Contracts must be 1-5 years.", None
    if bonus > apy * years or guaranteed > apy * years:
        return "counter", "Bonus and guarantees can't exceed the total value of the deal.", None
    st["round"] += 1
    need = dem["apy"] * (1.0 - ag["drop"] * (st["round"] - 1))
    val = offer_value(lg, team, p, dem, apy, years, bonus, guaranteed, resign)
    ratio = val / max(1, need)
    st["history"].append((apy, years, bonus, guaranteed, round(ratio, 3)))
    if ratio >= 1.0:
        return "accept", f"{p.name} accepts: {years} yr / {fmt_money(apy)} per year " \
                         f"({fmt_money(guaranteed)} guaranteed).", None
    st["patience"] -= 2 if ratio < 0.80 else 1
    if st["patience"] <= 0:
        st["closed"] = True
        return "walk", (f"{ag['name']} ends the talks: \"We're too far apart.\" "
                        f"{p.name} won't negotiate with you again until later in the year."), None
    # Counter-proposal: the agent asks for what would get it done
    want_g = dem["guar"]
    c_years = dem["years"]
    c_apy = int(need * (1.0 + max(0.0, 0.03 * (1.0 - ag["tough"]))))
    counter = {"apy": c_apy, "years": c_years, "guaranteed": int(c_apy * c_years * want_g),
               "bonus": int(c_apy * c_years * dem["bonus"])}
    tone = ("That's insulting." if ratio < 0.80 else "We're getting closer." if ratio > 0.93
            else "Not there yet.")
    gap = need - val
    msg = (f"{ag['name']} ({ag['style'].lower()} agent): \"{tone}\" Worth about {fmt_money(int(val))} a year "
           f"to his client — about {fmt_money(int(max(0, gap)))} short. They'd sign for "
           f"{c_years} yr / {fmt_money(c_apy)} with {fmt_money(counter['guaranteed'])} guaranteed. "
           f"Patience left: {st['patience']}.")
    return "counter", msg, counter


# ── Holdouts ──────────────────────────────────────────────────────────────────

def holdout_candidates(lg):
    """Underpaid stars under contract who may stay away from camp."""
    out = []
    cap = lg.salary_cap
    for t in lg.teams.values():
        for p in t.roster:
            c = p.contract
            if not c or c["years"] < 1 or p.age > 30 or p.ca < 140 or getattr(p, "holdout", False):
                continue
            if p.on_rookie_deal and p.years_pro < 3:
                continue
            mv = market_value(p, cap)
            if mv < c["salary"] * 1.8:
                continue
            amb = p.hidden.get("ambition", 50)
            chance = 0.06 + max(0, amb - 55) / 150.0 + (0.08 if mv > c["salary"] * 3 else 0.0)
            chance *= agent(p)["tough"] + 0.3
            if random.random() < chance:
                out.append((t, p))
    return out


def start_holdouts(lg):
    """Training camp: underpaid stars stay away. AI teams usually settle quickly."""
    news = []
    cands = holdout_candidates(lg)
    random.shuffle(cands)
    from settings import settings
    rate = settings["holdout_rate"]
    limit = int(round(random.choice([0, 1, 1, 2, 2, 3]) * rate))   # real holdouts are rare: 0-3 a season
    for t, p in cands:
        if len(news) >= limit:
            break
        if t.abbr != lg.user_abbr and random.random() < 0.6:
            settle(lg, t, p, quiet=False)        # a new deal before camp: no holdout
            continue
        p.holdout = True
        p.morale = max(1, p.morale - 8)
        news.append((t, p))
        lg.add_news("Contract", f"{p.name} ({p.position}, {t.abbr}) is holding out for a new contract",
                    t.abbr)
    return news


def settle(lg, team, p, quiet=True):
    """AI resolution: a new deal near market value."""
    cap = lg.salary_cap
    apy = int(market_value(p, cap) * random.uniform(0.92, 1.02))
    years = max(2, min(5, contract_length(p) + 1))
    bonus, guar = default_structure(p, apy, years)
    p.contract = make(apy, years, lg.year, bonus, guar)
    p.on_rookie_deal = False
    p.holdout = False
    p.morale = min(100, p.morale + 8)
    if not quiet:
        lg.add_transaction(f"{team.abbr} gave {p.position} {p.name} a new deal "
                           f"({years} yr, {fmt_money(apy)}/yr)")
        lg.add_news("Contract", f"{team.full_name} sign {p.name} to a {years}-year extension "
                                f"({fmt_money(apy)}/yr), ending his holdout", team.abbr)


def weekly_holdouts(lg):
    """Each week a holdout may give in and report; AI teams may settle."""
    for t in lg.teams.values():
        for p in t.roster:
            if not getattr(p, "holdout", False):
                continue
            p.morale = max(1, p.morale - 3)
            weeks = getattr(p, "holdout_weeks", 0) + 1
            p.holdout_weeks = weeks
            if t.abbr != lg.user_abbr and random.random() < 0.35:
                settle(lg, t, p, quiet=False)
            elif random.random() < 0.12 + 0.08 * weeks:
                p.holdout = False
                lg.add_news("Contract", f"{p.name} ({t.abbr}) ends his holdout and reports to the team",
                            t.abbr)
