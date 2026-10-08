"""
free_agency.py — contracts on the open market, releases and AI roster moves.
"""
import random

from contracts import (asking_salary, market_value, make_contract, contract_length,
                       min_salary, fmt_money)
from ratings import ROSTER_MINIMUM, ROSTER_TEMPLATE, POSITION_VALUE, POSITIONS
from settings import settings
import roster_rules as rr
import negotiation as nego

OFFSEASON_ROSTER_MAX = 75


def roster_limit(lg):
    return settings["roster_size"] if lg.phase in ("regular", "playoffs") \
        else OFFSEASON_ROSTER_MAX


def active_count(team):
    """Players counting against the roster limit (not practice squad or injured reserve)."""
    return sum(1 for p in team.roster if rr.is_active(p))


def mood(lg):
    """Free agents get cheaper the longer they sit unsigned."""
    if lg.phase == "regular":
        return 0.80 if lg.week > 3 else 0.9
    if lg.phase == "preseason":
        return 0.88
    return 1.0 + max(0, 2 - lg.fa_wave) * 0.04


def asking(lg, p):
    return asking_salary(p, lg.salary_cap, mood(lg))


def team_appeal(lg, team, p):
    """0.8 (unattractive) .. 1.2 (dream destination) for this player."""
    rank = lg.league_rank() if lg.standings and any(r.games for r in lg.standings.values()) \
        else lg.strength_order()
    pos_in_rank = rank.index(team.abbr) / 31.0 if team.abbr in rank else 0.5
    contender = 1.0 - pos_in_rank                         # 1 = best team
    at_pos = sorted((x.ca for x in team.players_at(p.position)), reverse=True)
    starters = {"WR": 3, "OT": 2, "IOL": 3, "DT": 2, "EDGE": 2, "LB": 3, "CB": 3, "S": 2}.get(p.position, 1)
    would_start = len(at_pos) < starters or p.ca > at_pos[starters - 1]
    amb = p.hidden.get("ambition", 50) / 100.0
    appeal = 0.92 + contender * 0.12 * (0.5 + amb) + (0.08 if would_start else -0.04)
    appeal += (team.coach.reputation - 50) / 500.0 + (team.fan_support - 60) / 800.0
    return max(0.8, min(1.2, appeal))


def evaluate_offer(lg, team, p, salary, years):
    ask = asking(lg, p)
    appeal = team_appeal(lg, team, p)
    needed = ask * (1.10 - (appeal - 0.8) * 0.5)          # 0.90x - 1.10x of ask
    if years < 1 or years > 5:
        return False, "Contracts must be 1-5 years."
    if p.age >= 31 and years > 3:
        needed *= 0.96          # veterans like security
    if p.age <= 25 and years <= 1:
        needed *= 1.08          # young players want longer deals or more money
    cap_ok, msg = can_afford(lg, team, salary)
    if not cap_ok:
        return False, msg
    if active_count(team) >= roster_limit(lg):
        return False, f"Your roster is full ({roster_limit(lg)} max). Release someone first."
    if salary >= needed:
        return True, f"{p.name} accepts: {years} yr / {fmt_money(salary)} per year."
    short = needed - salary
    return False, (f"{p.name} turns it down. He's looking for about "
                   f"{fmt_money(int(needed))} per year ({fmt_money(int(short))} more).")


def can_afford(lg, team, salary):
    if not settings["hard_cap"]:
        return True, ""
    space = team.cap_space(lg.salary_cap)
    if salary > space:
        return False, f"Not enough cap space ({fmt_money(space)} available)."
    return True, ""


def sign(lg, team, p, salary, years, quiet=False, bonus=None, guaranteed=None):
    if p in lg.free_agents:
        lg.free_agents.remove(p)
    if bonus is None or guaranteed is None:
        bonus, guaranteed = nego.default_structure(p, salary, years)
    p.contract = nego.make(salary, years, lg.year, bonus, guaranteed)
    p.on_rookie_deal = False
    p.ps = False
    p.ir = None
    rr.record_fa_move(lg, p, team.abbr, salary)
    team.add_player(p)
    p.morale = min(100, p.morale + 10)
    if not quiet:
        lg.add_transaction(f"{team.abbr} signed {p.position} {p.name} "
                           f"({years} yr, {fmt_money(salary)}/yr)")
        if p.ca >= 140 or team.abbr == lg.user_abbr:
            lg.add_news("Signing", f"{team.full_name} sign {p.position} {p.name} "
                                   f"({years} yr, {fmt_money(salary)}/yr)", team.abbr)
    return p


def release(lg, team, p, quiet=False):
    if p.contract:
        team.dead_cap += nego.dead_money(p.contract, lg.phase in ("regular", "playoffs"))
    p.holdout = False
    team.remove_player(p)
    p.contract = None
    p.on_rookie_deal = False
    p.ps = False
    p.ir = None
    p.morale = max(1, p.morale - 15)
    lg.free_agents.append(p)
    if not quiet:
        lg.add_transaction(f"{team.abbr} released {p.position} {p.name}")
        if team.abbr == lg.user_abbr or p.ca >= 140:
            lg.add_news("Release", f"{team.full_name} release {p.position} {p.name}", team.abbr)


def player_value(p):
    """Rough keep/cut value: ability now plus upside for young players."""
    upside = max(0, p.pa - p.ca) * max(0, 26 - p.age) * 0.08
    return p.ca + upside - max(0, p.age - 30) * 2


# ── AI roster management ──────────────────────────────────────────────────────

def ai_resign(lg, team):
    """AI decides which expiring contracts to keep."""
    kept = []
    for p in list(team.roster):
        if p.contract and p.contract["years"] <= 0:
            at_pos = sorted(team.players_at(p.position), key=lambda x: -player_value(x))
            idx = at_pos.index(p)
            keep_depth = max(1, ROSTER_TEMPLATE[p.position] - 1)
            wants = idx < keep_depth and (p.age <= 32 or p.position in ("QB", "K", "P") and p.age <= 37)
            if p.ca < 80:
                wants = False
            ask = asking_salary(p, lg.salary_cap, 1.0) * random.uniform(0.9, 1.02)
            space = team.cap_space(lg.salary_cap) + p.salary
            if wants and ask <= space * 0.6 and random.random() < 0.85:
                yrs = contract_length(p)
                bonus, guar = nego.default_structure(p, int(ask), yrs)
                p.contract = nego.make(int(ask), yrs, lg.year, bonus, guar)
                p.on_rookie_deal = False
                kept.append(p)
                if p.ca >= 145:
                    lg.add_transaction(f"{team.abbr} re-signed {p.position} {p.name}")
            else:
                team.remove_player(p)
                p.contract = None
                p.fa_origin = (team.abbr, lg.year)
                lg.free_agents.append(p)
    return kept


def ai_free_agency_wave(lg, max_signings=3):
    """Each AI team tries to plug its biggest holes with free agents."""
    teams = [t for t in lg.teams.values() if t.abbr != lg.user_abbr]
    random.shuffle(teams)
    teams.sort(key=lambda t: -t.cap_space(lg.salary_cap) * random.uniform(0.6, 1.4))
    aggr = settings["ai_fa_aggression"]
    signed = 0
    for team in teams:
        needs = team.needs()
        ranked = sorted(needs.items(), key=lambda kv: -kv[1])
        n = 0
        for pos, need in ranked[:8]:
            if n >= max_signings or need < 0.10 / aggr:
                break
            if active_count(team) >= roster_limit(lg):
                break
            at_pos = sorted((x.ca for x in team.players_at(pos)), reverse=True)
            starters = {"WR": 3, "OT": 2, "IOL": 3, "DT": 2, "EDGE": 2, "LB": 3,
                        "CB": 3, "S": 2}.get(pos, 1)
            bar = at_pos[starters - 1] if len(at_pos) >= starters else 0
            if len(at_pos) < ROSTER_MINIMUM[pos]:
                bar = min(bar, 70)
            cands = [p for p in lg.free_agents if p.position == pos and p.ca > bar + 3]
            if not cands:
                continue
            space = team.cap_space(lg.salary_cap) - min_salary(lg.salary_cap) * 4
            cands.sort(key=lambda p: -(player_value(p)))
            for p in cands[:6]:
                ask = asking(lg, p)
                appeal = team_appeal(lg, team, p)
                price = int(ask * (1.08 - (appeal - 0.8) * 0.4) * random.uniform(0.95, 1.08))
                if price <= space and random.random() < 0.75 * aggr:
                    sign(lg, team, p, price, contract_length(p))
                    n += 1
                    signed += 1
                    break
    return signed


def ai_fill_minimums(lg, team):
    """Make sure the roster can field a team: sign cheap bodies if short."""
    counts = team.position_counts()
    for pos in POSITIONS:
        while counts[pos] < ROSTER_MINIMUM[pos]:
            cands = [p for p in lg.free_agents if p.position == pos]
            if not cands:
                from player import generate_player
                p = generate_player(pos, random.randint(23, 28), random.randint(60, 85))
                p.years_pro = random.randint(1, 4)
                lg.free_agents.append(p)
                cands = [p]
            p = max(cands, key=player_value)
            sal = min_salary(lg.salary_cap)
            sign(lg, team, p, sal, 1, quiet=True)
            lg.add_transaction(f"{team.abbr} signed {p.position} {p.name} (minimum)")
            counts[pos] += 1


def ai_cutdown(lg, team, limit=None):
    """Trim to the roster limit, keeping positional minimums."""
    limit = limit or settings["roster_size"]
    while active_count(team) > limit:
        counts = team.position_counts()
        cands = [p for p in team.roster if rr.is_active(p)
                 and counts[p.position] > ROSTER_MINIMUM[p.position]]
        if not cands:
            break
        # Cut the least valuable relative to cost and positional surplus
        def cut_score(p):
            surplus = counts[p.position] - ROSTER_TEMPLATE[p.position]
            return player_value(p) - surplus * 6 - (p.salary / lg.salary_cap) * 60
        victim = min(cands, key=cut_score)
        ok, _ = rr.can_move_to_ps(lg, team, victim)
        if ok and victim.age <= 25 and victim.pa >= victim.ca + 8:
            rr.move_to_ps(lg, team, victim, quiet=True)
        else:
            release(lg, team, victim, quiet=True)


def ir_moves(lg, team, allow_cuts=True):
    """Staff-run injured reserve: stash long injuries, bring healthy players back."""
    for p in list(team.roster):
        if p.injury and p.injury.get("weeks", 0) >= rr.IR_MIN_WEEKS + 1 and not p.ir and not p.ps:
            rr.place_ir(lg, team, p, quiet=True)
    for p in sorted(rr.injured_reserve(team), key=lambda x: -x.ca):
        ok, _ = rr.can_activate_ir(lg, team, p)
        if not ok and not p.is_injured and active_count(team) >= settings["roster_size"]:
            # Make room for a healthy starter-quality player
            if p.ovr >= 70 and allow_cuts:
                ai_cutdown(lg, team, settings["roster_size"] - 1)
                ok, _ = rr.can_activate_ir(lg, team, p)
        if ok:
            rr.activate_ir(lg, team, p, quiet=True)


def in_season_moves(lg):
    """AI teams manage IR and sign emergency depth when injuries pile up."""
    auto_user = settings["auto_roster_moves"]
    for team in lg.teams.values():
        user = team.abbr == lg.user_abbr
        if user and not auto_user:
            continue
        ir_moves(lg, team, allow_cuts=not user)
        if user:
            # Fill IR vacancies from the practice squad (never cuts, never signs)
            while active_count(team) < settings["roster_size"]:
                needs = team.needs()
                ps = sorted(rr.practice_squad(team), key=lambda x: -(needs.get(x.position, 0) * 40 + x.ca))
                if not ps or not rr.promote(lg, team, ps[0])[0]:
                    break
            continue
        rr.fill_active_roster(lg, team)
        healthy = {pos: len(team.players_at(pos, healthy_only=True)) for pos in POSITIONS}
        need = {"QB": 2, "RB": 2, "WR": 4, "TE": 2, "OT": 2, "IOL": 4, "DT": 3, "EDGE": 3,
                "LB": 3, "CB": 4, "S": 3, "K": 1, "P": 1}
        for pos, n in need.items():
            if healthy[pos] >= n:
                continue
            if active_count(team) >= settings["roster_size"]:
                ai_cutdown(lg, team, settings["roster_size"] - 1)
            # 1) promote from our own practice squad
            own = [p for p in rr.practice_squad(team) if p.position == pos and not p.is_injured]
            if own:
                p = max(own, key=lambda x: x.ca)
                ok, _ = rr.promote(lg, team, p, quiet=True)
                if ok:
                    lg.add_transaction(f"{team.abbr} promoted {p.position} {p.name} from the practice squad")
                    continue
            # 2) sometimes poach another team's practice squad
            if rr.ai_poach(lg, team, pos):
                continue
            # 3) the street
            cands = [p for p in lg.free_agents if p.position == pos and not p.is_injured]
            if not cands:
                continue
            p = max(cands, key=lambda x: x.ca)
            sign(lg, team, p, max(min_salary(lg.salary_cap), int(asking(lg, p) * 0.6)), 1,
                 quiet=True)
            lg.add_transaction(f"{team.abbr} signed {p.position} {p.name} (injury replacement)")


def trim_free_agent_pool(lg, keep=450):
    """Players nobody wants eventually leave the sport."""
    if len(lg.free_agents) <= keep:
        return
    lg.free_agents.sort(key=player_value, reverse=True)
    lg.free_agents = lg.free_agents[:keep]


def evaluate_resign(lg, team, p, salary, years):
    """Re-signing one of your own players. Happy players give a hometown discount."""
    ask = asking_salary(p, lg.salary_cap, 1.0)
    discount = (p.morale - 60) / 400.0          # up to ~10% off for a happy player
    needed = ask * (1.0 - discount)
    if years < 1 or years > 5:
        return False, "Contracts must be 1-5 years."
    if p.age <= 25 and years <= 1:
        needed *= 1.06
    space = team.cap_space(lg.salary_cap) + p.salary
    if settings["hard_cap"] and salary > space:
        return False, f"Not enough cap space ({fmt_money(space)} available)."
    if salary >= needed:
        return True, f"{p.name} agrees: {years} yr / {fmt_money(salary)} per year."
    return False, (f"{p.name} wants about {fmt_money(int(needed))} per year "
                   f"({fmt_money(int(needed - salary))} more).")


def resign(lg, team, p, salary, years, bonus=None, guaranteed=None):
    if bonus is None or guaranteed is None:
        bonus, guaranteed = nego.default_structure(p, salary, years)
    # an extension replaces the old deal: unamortised bonus from it stays on the books
    if p.contract and p.contract.get("years", 0) > 0 and "length" in p.contract:
        team.dead_cap += int(p.contract.get("bonus", 0) / max(1, p.contract["length"])
                             * max(0, p.contract["years"] - 1))
    p.contract = nego.make(salary, years, lg.year, bonus, guaranteed)
    p.on_rookie_deal = False
    if getattr(p, "holdout", False):
        p.holdout = False
        lg.add_news("Contract", f"{p.name} signs his new deal and ends his holdout", team.abbr)
    p.morale = min(100, p.morale + 6)
    if p.id in lg.expiring:
        lg.expiring.remove(p.id)
    lg.add_transaction(f"{team.abbr} re-signed {p.position} {p.name} ({years} yr, {fmt_money(salary)}/yr)")
    lg.add_news("Contract", f"{team.full_name} re-sign {p.position} {p.name} "
                            f"({years} yr, {fmt_money(salary)}/yr)", team.abbr)
