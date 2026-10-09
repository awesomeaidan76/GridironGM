"""
draft.py — draft class generation, draft order and draft-day AI.

Class strength varies year to year, and each position group's depth follows
the league's talent pipelines (see eras.py). Every team sees prospects
through its own scouting department, so boards differ and steals happen.
"""
import random
import zlib

from contracts import rookie_salary, make_contract
from eras import POS_GROUP
from player import generate_player
from ratings import POSITION_VALUE
from settings import settings

PA_MEAN = 103.0
PA_SD = 23.5
# Positions where teams need more top-end talent than the raw draft supplies
PA_POS_OFFSET = {"QB": 16, "RB": 14, "FB": -20, "WR": 6, "TE": 3, "OT": 5, "IOL": 1,
                 "DT": 6, "EDGE": 10, "LB": 8, "CB": 7, "S": 3, "K": 11, "P": 6}
AGE_GAP = {21: (31, 9), 22: (25, 8), 23: (19, 7), 24: (13, 6)}

DRAFT_POS_DIST = {"QB": 4, "RB": 7, "FB": 1, "WR": 14, "TE": 6, "OT": 8, "IOL": 9,
                  "DT": 9, "EDGE": 9, "LB": 9, "CB": 12, "S": 8, "K": 1.5, "P": 1.5}


def draft_rounds():
    return 7


def combine_numbers(p):
    """Combine results from attributes, scaled to real NFL combine averages by position."""
    a = p.attrs
    forty = 4.48 + (77 - a["speed"]) * 0.019 + (76 - a["acceleration"]) * 0.006 + random.gauss(0, 0.03)
    bench = int(max(4, min(45, 14 + (a["strength"] - 36) * 0.32 + random.gauss(0, 2))))
    vert = round(max(20.0, min(45.0, 35.5 + (a["jumping"] - 66) * 0.27 + random.gauss(0, 1.2))), 1)
    cone = round(6.95 + (74 - a["agility"]) * 0.018 + random.gauss(0, 0.05), 2)
    return {"forty": round(forty, 2), "bench": bench, "vertical": vert, "cone": cone}


def generate_class(lg):
    n = draft_rounds() * 32 + 90
    strength = random.gauss(0, 4.5)
    lg.class_strength = strength
    scale = settings["draft_class_strength"]
    positions = list(DRAFT_POS_DIST)
    weights = [DRAFT_POS_DIST[p] for p in positions]
    out = []
    for _ in range(n):
        pos = random.choices(positions, weights=weights, k=1)[0]
        age = random.choices([21, 22, 23, 24], weights=[30, 45, 20, 5], k=1)[0]
        pipe = lg.pipeline.get(POS_GROUP[pos], 0.0)
        pa = random.gauss(PA_MEAN + PA_POS_OFFSET[pos] + strength + pipe, PA_SD)
        if random.random() < 0.035:
            pa += random.uniform(22, 45)          # elite ceiling
        pa = 100 + (pa - 100) * scale
        pa = int(max(60, min(200, pa)))
        gap = max(4.0, random.gauss(*AGE_GAP[age]))
        ca = int(max(45, min(pa, pa - gap)))
        p = generate_player(pos, age, ca, pa=pa,
                            archetype_weights=lg.archetype_weights.get(pos))
        p.years_pro = 0
        p.reputation = int(max(1, min(60, (p.ca - 60) * 0.35 + random.gauss(0, 6))))
        p.combine = combine_numbers(p)
        p.contract = None
        p.team = None
        p.draft = None
        out.append(p)
    # Media consensus big board (with noise) -> projected round
    def consensus(p):
        return p.ca * 0.5 + p.pa * 0.5 + POSITION_VALUE[p.position] * 18 \
            + random.gauss(0, 9) - (p.age - 21) * 2
    ranked = sorted(out, key=consensus, reverse=True)
    for i, p in enumerate(ranked):
        p.proj_rank = i + 1
        p.proj_round = min(8, i // 32 + 1)
    lg.draft_class = ranked
    import staff as staff_mod
    staff_mod.reset_scouting(lg)
    return ranked


def compute_order(lg):
    """
    Worst record picks first; playoff teams ordered by how far they went.
    Traded picks go to their new owners, and compensatory picks for last
    year's free-agent losses are added at the end of rounds 3-7.
    lg.draft_order holds (round, overall pick, owner); lg.draft_orig the
    original team for each slot and lg.draft_comp the comp-pick slots.
    """
    import roster_rules as rr
    exit_round = getattr(lg, "playoff_exit", {})

    def key(abbr):
        rec = lg.standings[abbr]
        return (exit_round.get(abbr, -1), rec.pct, rec.diff, random.random())
    order = sorted(lg.teams, key=key)
    year = lg.year + 1
    comp = rr.compensatory_picks(lg, lg.year - 1)
    lg.draft_order, lg.draft_orig, lg.draft_comp = [], [], set()
    pick = 1
    for rnd in range(1, draft_rounds() + 1):
        for abbr in order:
            lg.draft_order.append((rnd, pick, rr.pick_owner(lg, year, rnd, abbr)))
            lg.draft_orig.append(abbr)
            pick += 1
        for c_rnd, abbr, _apy, _name in comp:
            if c_rnd == rnd:
                lg.draft_comp.add(pick)
                lg.draft_order.append((rnd, pick, abbr))
                lg.draft_orig.append(abbr)
                pick += 1
    lg.comp_awards = comp
    for c_rnd, abbr, apy, name in comp:
        if abbr == lg.user_abbr:
            lg.add_news("Draft", f"You were awarded a round {c_rnd} compensatory pick for losing "
                                 f"{name} in free agency.", abbr)
    lg.draft_index = 0
    lg.draft_log = []


def _seed(abbr, pid):
    return zlib.crc32(f"{abbr}:{pid}".encode())


def scouted_values(lg, team, p):
    """What this team's scouts believe: (est CA, est PA). See staff.estimate."""
    import staff as staff_mod
    est_ca, est_pa, _, _ = staff_mod.estimate(lg, team, p)
    return est_ca, est_pa


def board_value(lg, team, p, needs):
    est_ca, est_pa = scouted_values(lg, team, p)
    if getattr(team, "gm", None) is not None:
        import front_office as fo
        return fo.board_value(lg, team, p, needs, est_ca, est_pa)
    v = est_ca * 0.45 + est_pa * 0.55 + POSITION_VALUE[p.position] * 22 - (p.age - 21) * 2.0
    v += needs.get(p.position, 0) * 9
    if p.position in ("K", "P"):
        v -= 22
    if p.position == "FB":
        v -= 12
    return v


def current_pick(lg):
    if lg.draft_index >= len(lg.draft_order):
        return None
    return lg.draft_order[lg.draft_index]


def make_pick(lg, abbr, player):
    rnd, pick, _ = lg.draft_order[lg.draft_index]
    team = lg.teams[abbr]
    lg.draft_class.remove(player)
    player.draft = {"year": lg.year, "round": rnd, "pick": pick, "team": abbr}
    player.contract = make_contract(rookie_salary(pick, lg.salary_cap), 4, lg.year)
    player.on_rookie_deal = True
    team.add_player(player)
    lg.draft_log.append((rnd, pick, abbr, player.id, player.name, player.position))
    import front_office as fo
    fo.record_pick(lg, team, player, rnd, pick)
    lg.draft_index += 1
    if rnd == 1 or abbr == lg.user_abbr:
        lg.add_news("Draft", f"Pick {pick} (Rd {rnd}): {team.full_name} select "
                             f"{player.position} {player.name}, {player.college}", abbr)
    return player


def ai_pick(lg):
    import market
    market.draft_day_trade(lg)
    rnd, pick, abbr = lg.draft_order[lg.draft_index]
    team = lg.teams[abbr]
    needs = team.needs()
    pool = lg.draft_class[:90] if len(lg.draft_class) > 90 else lg.draft_class
    best = max(pool, key=lambda p: board_value(lg, team, p, needs))
    return make_pick(lg, abbr, best)


def sim_until_user(lg):
    """AI picks until it's the user's turn or the draft ends."""
    made = []
    while lg.draft_index < len(lg.draft_order) and lg.draft_class:
        _, _, abbr = lg.draft_order[lg.draft_index]
        if abbr == lg.user_abbr:
            break
        made.append(ai_pick(lg))
    return made


def auto_pick_for_user(lg):
    rnd, pick, abbr = lg.draft_order[lg.draft_index]
    return ai_pick(lg)


def finish_draft(lg):
    while lg.draft_index < len(lg.draft_order) and lg.draft_class:
        ai_pick(lg)
    # Undrafted prospects become free agents
    for p in lg.draft_class:
        p.draft = None
        lg.free_agents.append(p)
    lg.draft_class = []
