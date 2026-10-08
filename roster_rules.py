"""
roster_rules.py — the league's roster rules beyond the 53-man limit.

  * Injured reserve: players hurt for 4+ weeks can be moved off the active
    roster. They must stay there at least 4 weeks, and a team may bring back
    a limited number of players per season.
  * Practice squad: young players (and a few veterans) who practise but don't
    count against the 53. Other teams can sign them to their active roster.
  * Franchise tag: once a year, during the re-signing window, a team can keep
    one expiring player on a one-year deal priced at the top of his position.
  * Compensatory picks: teams that lose more free agents than they sign get
    extra picks at the end of rounds 3-7 of the next draft.
  * Draft picks as assets: the next two drafts' picks can be traded.

Players on the practice squad or IR stay in `team.roster` with a flag
(`p.ps`, `p.ir`), so payroll, development and contracts keep working; only
availability (depth chart, roster count) looks at the flags.
"""
import math
import random

from contracts import make_contract, min_salary, fmt_money
from settings import settings

IR_MIN_WEEKS = 4
IR_RETURNS = 8
PS_VET_LIMIT = 6


# ── Availability helpers ──────────────────────────────────────────────────────

def is_active(p):
    """On the active roster (not practice squad, not injured reserve)."""
    return not getattr(p, "ps", False) and not getattr(p, "ir", None)


def practice_squad(team):
    return [p for p in team.roster if getattr(p, "ps", False)]


def injured_reserve(team):
    return [p for p in team.roster if getattr(p, "ir", None)]


def ps_size():
    return settings["practice_squad_size"]


def ps_salary(cap):
    return int(cap * 0.0011)


# ── Injured reserve ───────────────────────────────────────────────────────────

def can_place_ir(lg, p):
    if lg.phase not in ("regular", "playoffs"):
        return False, "Injured reserve is only used during the season."
    if getattr(p, "ir", None):
        return False, f"{p.name} is already on injured reserve."
    if getattr(p, "ps", False):
        return False, "Practice squad players can't be placed on IR."
    if not p.injury or p.injury.get("weeks", 0) < IR_MIN_WEEKS:
        return False, f"Only players out {IR_MIN_WEEKS}+ weeks can go on IR."
    return True, ""


def place_ir(lg, team, p, quiet=False):
    ok, msg = can_place_ir(lg, p)
    if not ok:
        return False, msg
    remaining = max(0, len(lg.schedule) - lg.week)
    p.ir = {"year": lg.year, "week": lg.week,
            "season_ending": p.injury.get("weeks", 0) >= remaining}
    if not quiet:
        lg.add_transaction(f"{team.abbr} placed {p.position} {p.name} on injured reserve")
    return True, f"{p.name} placed on injured reserve."


def can_activate_ir(lg, team, p):
    ir = getattr(p, "ir", None)
    if not ir:
        return False, f"{p.name} is not on injured reserve."
    if p.is_injured:
        return False, f"{p.name} is still injured ({p.injury['weeks']} wk)."
    if ir.get("year") == lg.year and lg.week - ir.get("week", 0) < IR_MIN_WEEKS:
        return False, f"Players must spend at least {IR_MIN_WEEKS} weeks on IR."
    if getattr(team, "ir_returns", (None, 0))[0] == lg.year and team.ir_returns[1] >= IR_RETURNS:
        return False, f"You have used all {IR_RETURNS} return designations this season."
    from free_agency import active_count
    if active_count(team) >= settings["roster_size"]:
        return False, "Your active roster is full. Release or move someone first."
    return True, ""


def activate_ir(lg, team, p, quiet=False):
    ok, msg = can_activate_ir(lg, team, p)
    if not ok:
        return False, msg
    p.ir = None
    yr, n = getattr(team, "ir_returns", (lg.year, 0))
    team.ir_returns = (lg.year, (n if yr == lg.year else 0) + 1)
    if not quiet:
        lg.add_transaction(f"{team.abbr} activated {p.position} {p.name} from injured reserve")
    return True, f"{p.name} is back on the active roster."


def clear_ir(team):
    """New season: anyone left on IR returns to the roster."""
    for p in team.roster:
        p.ir = None
    team.ir_returns = (None, 0)


# ── Practice squad ────────────────────────────────────────────────────────────

def ps_eligible(team, p):
    if p.years_pro <= 2:
        return True, ""
    vets = sum(1 for x in practice_squad(team) if x.years_pro > 2)
    if vets >= PS_VET_LIMIT:
        return False, f"Only {PS_VET_LIMIT} veterans (3+ seasons) are allowed on the practice squad."
    if p.ovr >= 72:
        return False, f"{p.name} is too established for the practice squad."
    return True, ""


def can_move_to_ps(lg, team, p):
    if getattr(p, "ps", False):
        return False, f"{p.name} is already on the practice squad."
    if getattr(p, "ir", None):
        return False, "Players on injured reserve can't join the practice squad."
    if len(practice_squad(team)) >= ps_size():
        return False, f"The practice squad is full ({ps_size()})."
    return ps_eligible(team, p)


def move_to_ps(lg, team, p, quiet=False):
    ok, msg = can_move_to_ps(lg, team, p)
    if not ok:
        return False, msg
    if p.contract and not p.on_rookie_deal and p.salary > ps_salary(lg.salary_cap):
        # A real contract is torn up: part of it lands as dead money
        frac = 0.35 if lg.phase in ("regular", "playoffs") else 0.15
        team.dead_cap += int((p.salary - ps_salary(lg.salary_cap)) * frac)
    p.contract = make_contract(ps_salary(lg.salary_cap), 1, lg.year)
    p.ps = True
    for ids in team.depth_overrides.values():
        if p.id in ids:
            ids.remove(p.id)
    if not quiet:
        lg.add_transaction(f"{team.abbr} signed {p.position} {p.name} to the practice squad")
    return True, f"{p.name} moved to the practice squad."


def can_promote(lg, team, p):
    if not getattr(p, "ps", False):
        return False, f"{p.name} is not on the practice squad."
    from free_agency import active_count, roster_limit
    if active_count(team) >= roster_limit(lg):
        return False, "Your active roster is full. Release or move someone first."
    sal = min_salary(lg.salary_cap)
    if settings["hard_cap"] and team.cap_space(lg.salary_cap) < sal - p.salary:
        return False, "Not enough cap space to promote him."
    return True, ""


def promote(lg, team, p, quiet=False):
    ok, msg = can_promote(lg, team, p)
    if not ok:
        return False, msg
    p.ps = False
    p.contract = make_contract(min_salary(lg.salary_cap), max(1, 2 if p.age <= 24 else 1), lg.year)
    p.morale = min(100, p.morale + 12)
    if not quiet:
        lg.add_transaction(f"{team.abbr} promoted {p.position} {p.name} to the active roster")
    return True, f"{p.name} promoted to the active roster."


def ai_build_practice_squad(lg, team):
    """Fill the practice squad with the best young upside players available."""
    room = ps_size() - len(practice_squad(team))
    if room <= 0:
        return
    pool = [p for p in lg.free_agents if p.years_pro <= 2 and p.age <= 25 and not p.is_injured]
    pool.sort(key=lambda p: -(p.pa * 0.7 + p.ca * 0.3))
    needs = team.needs()
    for p in pool[: room * 3]:
        if room <= 0:
            break
        if random.random() < 0.55 + min(0.4, needs.get(p.position, 0) * 0.2):
            lg.free_agents.remove(p)
            team.add_player(p)
            p.on_rookie_deal = False
            p.contract = make_contract(ps_salary(lg.salary_cap), 1, lg.year)
            p.ps = True
            room -= 1


def seed_practice_squads(lg):
    """New league: every team starts with a practice squad of young prospects."""
    from player import generate_player
    from ratings import ROSTER_TEMPLATE, POSITIONS
    for team in lg.teams.values():
        n = min(ps_size(), 12)
        for _ in range(n):
            pos = random.choices(POSITIONS, weights=[ROSTER_TEMPLATE[x] for x in POSITIONS])[0]
            age = random.randint(22, 24)
            ca = int(max(45, min(110, random.gauss(80, 12))))
            pa = int(min(190, ca + max(6, random.gauss(26, 14))))
            p = generate_player(pos, age, ca, pa=pa,
                                archetype_weights=lg.archetype_weights.get(pos))
            p.years_pro = random.randint(0, 2)
            p.contract = make_contract(ps_salary(lg.salary_cap), 1, lg.year)
            p.ps = True
            team.add_player(p)


def fill_active_roster(lg, team):
    """AI keeps 53 on the active roster: promote from the practice squad, else sign the best cheap free agent."""
    from free_agency import active_count, sign
    limit = settings["roster_size"]
    guard = 0
    while active_count(team) < limit and guard < 12:
        guard += 1
        needs = team.needs()
        ps = sorted(practice_squad(team), key=lambda x: -(needs.get(x.position, 0) * 40 + x.ca))
        if ps:
            ok, _ = promote(lg, team, ps[0], quiet=True)
            if ok:
                continue
        pos = max(needs, key=needs.get)
        cands = [p for p in lg.free_agents if p.position == pos and not p.is_injured] or \
                [p for p in lg.free_agents if not p.is_injured]
        if not cands:
            break
        p = max(cands, key=lambda x: x.ca)
        sign(lg, team, p, min_salary(lg.salary_cap), 1, quiet=True)


def ai_poach(lg, team, pos):
    """Sign another team's practice-squad player to fill a hole. Returns the player or None."""
    cands = []
    for other in lg.teams.values():
        if other is team:
            continue
        cands += [p for p in practice_squad(other) if p.position == pos and not p.is_injured]
    if not cands:
        return None
    p = max(cands, key=lambda x: x.ca + max(0, x.pa - x.ca) * 0.3)
    if random.random() > 0.35:
        return None
    old = lg.teams[p.team]
    old.remove_player(p)
    p.ps = False
    p.contract = make_contract(int(min_salary(lg.salary_cap) * 1.15), 2, lg.year)
    team.add_player(p)
    lg.add_transaction(f"{team.abbr} signed {p.position} {p.name} off the {old.abbr} practice squad")
    if old.abbr == lg.user_abbr:
        lg.add_news("Roster", f"{team.full_name} signed {p.position} {p.name} away from your "
                              f"practice squad.", old.abbr)
    return p


def season_end_ps(lg):
    """
    Practice-squad deals end with the season. Promising players are kept on
    reserve/future contracts and join the offseason roster; the rest are let go
    when the re-signing window closes.
    """
    for team in lg.teams.values():
        auto = team.abbr != lg.user_abbr or settings["auto_roster_moves"]
        for p in practice_squad(team):
            p.ps = False
            p.was_ps = lg.year
            if auto and p.age <= 26 and (p.pa - p.ca >= 6 or p.ovr >= 60):
                p.contract = make_contract(min_salary(lg.salary_cap), 1, lg.year + 1)
                if p.id in lg.expiring:
                    lg.expiring.remove(p.id)


# ── Franchise tag ─────────────────────────────────────────────────────────────

def tag_amount(lg, p):
    sal = sorted((x.salary for t in lg.teams.values() for x in t.roster
                  if x.position == p.position and x.contract), reverse=True)[:5]
    avg = sum(sal) / len(sal) if sal else min_salary(lg.salary_cap) * 10
    return int(max(avg, p.salary * 1.2))


def can_tag(lg, team, p):
    if lg.phase not in ("season_end", "resign"):
        return False, "The franchise tag can only be used in the re-signing window."
    if getattr(team, "tag_year", None) == lg.year:
        return False, "You have already used the franchise tag this year."
    if p.id not in lg.expiring:
        return False, f"{p.name}'s contract isn't expiring."
    amt = tag_amount(lg, p)
    space = team.cap_space(lg.salary_cap) + p.salary
    if settings["hard_cap"] and amt > space:
        return False, f"The tag costs {fmt_money(amt)} — not enough cap space."
    return True, ""


def apply_tag(lg, team, p, quiet=False):
    ok, msg = can_tag(lg, team, p)
    if not ok:
        return False, msg
    amt = tag_amount(lg, p)
    p.contract = make_contract(amt, 1, lg.year)
    p.on_rookie_deal = False
    p.tag_count = getattr(p, "tag_count", 0) + 1
    team.tag_year = lg.year
    if p.hidden.get("ambition", 50) >= 60:
        p.morale = max(1, p.morale - 12)        # wanted a long-term deal
    if p.id in lg.expiring:
        lg.expiring.remove(p.id)
    lg.add_transaction(f"{team.abbr} placed the franchise tag on {p.position} {p.name} "
                       f"({fmt_money(amt)})")
    if not quiet or team.abbr == lg.user_abbr:
        lg.add_news("Contract", f"{team.full_name} franchise-tag {p.position} {p.name} "
                                f"({fmt_money(amt)} for one year)", team.abbr)
    return True, f"{p.name} is franchise-tagged: one year, {fmt_money(amt)}."


def ai_tags(lg):
    for team in lg.teams.values():
        if team.abbr == lg.user_abbr:
            continue
        exp = [p for p in team.roster if p.id in lg.expiring]
        exp = [p for p in exp if p.ovr >= 86 and p.age <= 30]
        if not exp or random.random() > 0.35:
            continue
        p = max(exp, key=lambda x: x.ovr)
        apply_tag(lg, team, p, quiet=True)


# ── Draft picks as assets ─────────────────────────────────────────────────────

def next_draft_year(lg):
    if lg.phase in ("regular", "playoffs", "season_end", "resign", "draft"):
        return lg.year + 1
    return lg.year + 2


def pick_key(year, rnd, orig):
    return f"{year}-{rnd}-{orig}"


def pick_owner(lg, year, rnd, orig):
    return getattr(lg, "pick_owner", {}).get(pick_key(year, rnd, orig), orig)


def tradable_picks(lg, abbr):
    """Picks this team currently owns in the next two drafts: [(year, rnd, orig)]."""
    from draft import draft_rounds
    y0 = next_draft_year(lg)
    used = set()
    if lg.phase == "draft":
        used = {(y0, r, o) for (r, _pk, _ow), o in zip(lg.draft_order[:lg.draft_index],
                                                        getattr(lg, "draft_orig", []))}
    out = []
    for year in (y0, y0 + 1):
        for rnd in range(1, draft_rounds() + 1):
            for orig in lg.teams:
                if pick_owner(lg, year, rnd, orig) == abbr and (year, rnd, orig) not in used:
                    out.append((year, rnd, orig))
    return out


def projected_pick(lg, year, rnd, orig):
    """Overall pick number: actual if the order is set, else projected from team strength."""
    if year == lg.year + 1 and lg.draft_order and getattr(lg, "draft_orig", None):
        for (r, pk, _own), o in zip(lg.draft_order, lg.draft_orig):
            if r == rnd and o == orig:
                return pk
    ranks = lg.strength_order()[::-1]
    slot = ranks.index(orig) + 1 if orig in ranks else 16
    return (rnd - 1) * 32 + slot


def pick_value(lg, year, rnd, orig):
    """Trade value of a pick, on the same scale as trades.trade_value."""
    pk = projected_pick(lg, year, rnd, orig)
    v = 52.0 * math.exp(-0.0185 * (pk - 1)) + 1.0
    years_out = year - next_draft_year(lg)
    if years_out >= 1:
        v *= 0.80 ** years_out
        v = v * 0.85 + (52.0 * math.exp(-0.0185 * ((rnd - 1) * 32 + 16)) + 1.0) * 0.15
    return v


def pick_label(lg, year, rnd, orig, owner=None):
    own = owner or pick_owner(lg, year, rnd, orig)
    suffix = "" if orig == own else f" (from {orig})"
    if year == lg.year + 1 and lg.draft_order and getattr(lg, "draft_orig", None):
        pk = projected_pick(lg, year, rnd, orig)
        return f"{year} R{rnd} #{pk}{suffix}"
    return f"{year} Round {rnd}{suffix}"


def transfer_pick(lg, year, rnd, orig, new_owner):
    if not hasattr(lg, "pick_owner"):
        lg.pick_owner = {}
    lg.pick_owner[pick_key(year, rnd, orig)] = new_owner
    # If the order for that draft is already set, update it too
    if getattr(lg, "draft_orig", None) and year == lg.year + 1:
        for i, ((r, pk, own), o) in enumerate(zip(lg.draft_order, lg.draft_orig)):
            if r == rnd and o == orig and i >= lg.draft_index:
                lg.draft_order[i] = (r, pk, new_owner)


# ── Compensatory picks ────────────────────────────────────────────────────────

def record_fa_move(lg, p, to_abbr, salary):
    origin = getattr(p, "fa_origin", None)
    p.fa_origin = None
    if not origin or lg.phase != "free_agency":
        return
    from_abbr, year = origin
    if from_abbr == to_abbr or year != lg.year:
        return
    if not hasattr(lg, "fa_moves"):
        lg.fa_moves = []
    lg.fa_moves.append((lg.year, from_abbr, to_abbr, int(salary), p.name, p.position))


def _comp_round(share):
    if share >= 0.05:
        return 3
    if share >= 0.025:
        return 4
    if share >= 0.012:
        return 5
    if share >= 0.007:
        return 6
    return 7


def compensatory_picks(lg, fa_year):
    """[(round, team, apy, player name)] earned from the free agency of `fa_year`."""
    moves = [m for m in getattr(lg, "fa_moves", []) if m[0] == fa_year]
    floor = lg.salary_cap * 0.004
    out = []
    for abbr in lg.teams:
        losses = sorted((m for m in moves if m[1] == abbr and m[3] >= floor), key=lambda m: -m[3])
        gains = sorted((m for m in moves if m[2] == abbr and m[3] >= floor), key=lambda m: -m[3])
        net = losses[len(gains):]
        for m in net[:4]:
            out.append((_comp_round(m[3] / lg.salary_cap), abbr, m[3], m[4]))
    out.sort(key=lambda x: (x[0], -x[2]))
    return out[:32]


def prune_old(lg):
    """Forget pick ownership and FA records that no longer matter."""
    y0 = lg.year
    if hasattr(lg, "pick_owner"):
        lg.pick_owner = {k: v for k, v in lg.pick_owner.items() if int(k.split("-")[0]) > y0}
    if hasattr(lg, "fa_moves"):
        lg.fa_moves = [m for m in lg.fa_moves if m[0] >= y0 - 2]
