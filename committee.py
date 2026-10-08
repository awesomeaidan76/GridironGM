"""
committee.py — the league's competition committee.

Real football eras are not only talent cycles. The rules move too, and
they move in response to the league itself: when defenses smother
passing games, the committee restricts contact downfield (as with the
1978 and 2004 rule changes in the real league); when quarterbacks keep
getting hurt, it protects them; when scoring runs away, it gives some
latitude back. Nothing is scheduled. The committee meets every
offseason, looks at the last few seasons and decides whether anything
needs to change.

Each rule is a small dial (an integer step). The match engine reads the
dials through `effects(rules)`.
"""
import random

RULES = {
    # key: (label, min step, max step)
    "coverage": ("Downfield contact", -2, 3),
    "qb_protection": ("Quarterback protection", 0, 3),
    "holding": ("Holding enforcement", -1, 2),
    "kickoff": ("Kickoff touchback spot", 0, 1),
}

DESCRIBE = {
    ("coverage", 1): "restricts contact on receivers beyond five yards; illegal contact "
                     "will be enforced strictly",
    ("coverage", -1): "gives defenders more latitude to contest receivers downfield",
    ("qb_protection", 1): "expands protection for quarterbacks in the pocket; low and "
                          "late hits will be flagged",
    ("holding", 1): "relaxes offensive holding enforcement on the line of scrimmage",
    ("holding", -1): "orders officials to call offensive holding more strictly",
    ("kickoff", 1): "moves the touchback on kickoffs out to the 30-yard line",
}


def default_rules():
    return {k: 0 for k in RULES}


def effects(rules):
    """Translate rule steps into match-engine modifiers."""
    r = rules or {}
    cov = r.get("coverage", 0)
    qbp = r.get("qb_protection", 0)
    hold = r.get("holding", 0)
    return {
        "openness": 1.6 * cov,                    # receivers' separation vs coverage
        "press": -0.06 * cov,                     # effectiveness of press technique
        "dpi": 1.0 + 0.10 * cov,                  # defensive contact flags
        "sack": 1.0 - 0.035 * qbp,                # pocket hits that become sacks
        "qb_injury": 1.0 - 0.14 * qbp,
        "roughing": 1.0 + 0.25 * qbp,
        "holding": 1.0 - 0.10 * hold,
        "touchback": 30 if r.get("kickoff", 0) >= 1 else 25,
    }


def _avg(values):
    return sum(values) / len(values) if values else 0.0


def review(lg):
    """Called once per offseason. Returns a list of (key, step) changes made."""
    rules = getattr(lg, "rules", None)
    if rules is None:
        rules = lg.rules = default_rules()
    if not hasattr(lg, "rule_history"):
        lg.rule_history = []
    if not hasattr(lg, "qb_injury_history"):
        lg.qb_injury_history = []
    hist = [h.get("averages") or {} for h in lg.history[-3:]]
    hist = [h for h in hist if h]
    if len(hist) < 2:
        return []
    last_change = max((y for y, *_ in lg.rule_history), default=-99)
    if lg.year - last_change < 2:
        return []

    ppg = _avg([h.get("ppg", 21.5) for h in hist])
    nya = _avg([h.get("ny_a", 6.0) for h in hist])
    qb_inj = _avg(lg.qb_injury_history[-3:])          # long QB injuries per team-season
    candidates = []
    # Offense starved: open up the passing game
    if (ppg < 19.8 or nya < 5.5) and rules["coverage"] < RULES["coverage"][2]:
        candidates.append(("coverage", 1, 0.55 + (19.8 - ppg) * 0.15))
    if ppg < 20.3 and rules["holding"] < RULES["holding"][2]:
        candidates.append(("holding", 1, 0.25))
    # Quarterbacks getting hurt
    if qb_inj > 0.45 and rules["qb_protection"] < RULES["qb_protection"][2]:
        candidates.append(("qb_protection", 1, 0.35 + (qb_inj - 0.45)))
    # Scoring out of hand: some latitude goes back to defenses (rarer)
    if ppg > 26.0 and rules["coverage"] > RULES["coverage"][1]:
        candidates.append(("coverage", -1, 0.20 + (ppg - 26.0) * 0.08))
    if ppg > 26.5 and rules["holding"] > RULES["holding"][1]:
        candidates.append(("holding", -1, 0.15))
    # Player-safety housekeeping now and then
    if rules["kickoff"] < 1 and random.random() < 0.04:
        candidates.append(("kickoff", 1, 1.0))

    random.shuffle(candidates)
    for key, step, prob in candidates:
        if random.random() < max(0.0, min(0.9, prob)):
            rules[key] += step
            text = DESCRIBE.get((key, step), f"adjusts the {RULES[key][0].lower()} rule")
            lg.rule_history.append((lg.year, key, step, text))
            lg.add_news("League", f"Competition Committee {text}.")
            return [(key, step)]
    return []


def record_season_injuries(lg, results):
    """Track serious quarterback injuries (3+ weeks) per team-season."""
    n = 0
    for g in results:
        for pid, _name, _team, _inj, weeks in g.injuries:
            meta = g.player_meta.get(pid)
            if meta and meta[1] == "QB" and weeks >= 3:
                n += 1
    teams = max(1, len(lg.teams))
    if not hasattr(lg, "qb_injury_history"):
        lg.qb_injury_history = []
    lg.qb_injury_history.append(n / teams)
