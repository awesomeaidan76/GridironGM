"""
trades.py — player and draft-pick trades: valuation and AI acceptance.

A trade asset is either a Player or a pick tuple ("pick", year, round, original team).
"""
import random

from contracts import market_value, fmt_money
from ratings import POSITION_VALUE, ROSTER_MINIMUM
from settings import settings
import roster_rules as rr
import front_office as fo


def is_pick(asset):
    return isinstance(asset, tuple) and len(asset) == 4 and asset[0] == "pick"


def asset_label(lg, asset):
    if is_pick(asset):
        _, y, r, o = asset
        return rr.pick_label(lg, y, r, o) + " pick"
    return f"{asset.position} {asset.name}"


def trade_value(p, lg, team=None):
    """How much a team values acquiring this player or pick (arbitrary units)."""
    if is_pick(p):
        _, y, r, o = p
        v = rr.pick_value(lg, y, r, o)
        if team is not None and fo.gm_of(team) is not None:
            return v * fo.pick_mult(lg, team, y)
        if team is not None:
            # Rebuilding teams love picks, contenders less so
            ranks = lg.strength_order()
            pos = ranks.index(team.abbr) / 31.0 if team.abbr in ranks else 0.5
            v *= 0.85 + 0.30 * pos
        return v
    ability = max(0.0, p.ca - 70) ** 1.55 / 12.0
    youth = max(0, p.pa - p.ca) * max(0, 27 - p.age) * 0.06
    age_mult = 1.0 - max(0, p.age - 29) * 0.10
    pos = POSITION_VALUE[p.position] ** 0.6
    v = (ability + youth) * max(0.25, age_mult) * pos
    if p.contract:
        surplus = (market_value(p, lg.salary_cap) - p.salary) / lg.salary_cap * 100
        v += surplus * min(3, p.contract["years"]) * 0.6
    if team is not None:
        need = team.needs().get(p.position, 0)
        v *= 1.0 + min(0.4, need * 0.15)
        if fo.gm_of(team) is not None:
            v *= fo.player_mult(lg, team, p)
        elif team.abbr != p.team:
            ranks = lg.strength_order()
            rebuilding = ranks.index(team.abbr) >= 20 if team.abbr in ranks else False
            if rebuilding and p.age >= 30:
                v *= 0.7          # rebuilding teams don't want old veterans
    if p.is_injured and p.injury.get("weeks", 0) > 6:
        v *= 0.6
    return max(0.0, v)


def _players(assets):
    return [a for a in assets if not is_pick(a)]


def _picks(assets):
    return [a for a in assets if is_pick(a)]


def evaluate(lg, user_team, ai_team, give, get):
    """
    give: assets the user sends; get: assets the user receives.
    Returns (accepted, message, value_to_ai_in, value_to_ai_out).
    """
    if lg.phase == "regular" and lg.week >= settings["trade_deadline_week"]:
        return False, "The trade deadline has passed.", 0, 0
    if lg.phase == "playoffs":
        return False, "Trades are not allowed during the playoffs.", 0, 0
    if not give and not get:
        return False, "Add players or picks to the trade.", 0, 0
    for _, y, r, o in _picks(give):
        if rr.pick_owner(lg, y, r, o) != user_team.abbr:
            return False, "You no longer own one of those picks.", 0, 0
    for _, y, r, o in _picks(get):
        if rr.pick_owner(lg, y, r, o) != ai_team.abbr:
            return False, f"{ai_team.full_name} no longer own one of those picks.", 0, 0
    val_in = sum(trade_value(a, lg, ai_team) for a in give)
    # What the AI gives up, valued through its own eyes (a rebuilding club lets veterans go cheaply,
    # a loyal GM hates parting with his own players)
    val_out = sum(trade_value(a, lg, ai_team) for a in get) * 0.5 + \
        sum(trade_value(a, lg, None) for a in get) * 0.5
    gp, tp = _players(give), _players(get)
    # Cap check for both sides
    if settings["hard_cap"]:
        user_after = user_team.payroll - sum(p.salary for p in gp) + sum(p.salary for p in tp)
        ai_after = ai_team.payroll + sum(p.salary for p in gp) - sum(p.salary for p in tp)
        if user_after > lg.salary_cap and tp:
            return False, "This trade would put you over the salary cap.", val_in, val_out
        if ai_after > lg.salary_cap and gp:
            return False, f"{ai_team.full_name} can't fit the incoming salary under the cap.", \
                val_in, val_out
    # Active roster limit for the user (in season)
    if lg.phase in ("regular", "playoffs"):
        from free_agency import active_count
        after = active_count(user_team) - len([p for p in gp if rr.is_active(p)]) + len(tp)
        if after > settings["roster_size"]:
            return False, (f"You'd have {after} players on the active roster "
                           f"(limit {settings['roster_size']}). Make room first."), val_in, val_out
    # Roster minimums for the AI side
    counts = ai_team.position_counts()
    for p in tp:
        counts[p.position] -= 1
    for p in gp:
        counts[p.position] += 1
    for pos, n in counts.items():
        if n < ROSTER_MINIMUM[pos] - 1:
            return False, f"{ai_team.full_name} won't go that thin at {pos}.", val_in, val_out
    will = max(0.05, settings["ai_trade_willingness"])
    threshold = val_out * (1.10 / will) * fo.demand(ai_team) + 1.0
    if val_in >= threshold:
        return True, f"{ai_team.full_name} accept the trade.", val_in, val_out
    gap = threshold - val_in
    if gap < val_out * 0.15:
        msg = "They're close — add a little more value."
    elif gap < val_out * 0.5:
        msg = "They want significantly more in return."
    else:
        msg = "Not interested. That's nowhere near enough."
    return False, msg, val_in, val_out


def execute(lg, team_a, team_b, a_gives, b_gives, why=None):
    for a in a_gives:
        if is_pick(a):
            rr.transfer_pick(lg, a[1], a[2], a[3], team_b.abbr)
            continue
        team_a.remove_player(a)
        a.ps = False
        a.ir = None
        team_b.add_player(a)
        a.morale = max(1, a.morale - 8)
    for a in b_gives:
        if is_pick(a):
            rr.transfer_pick(lg, a[1], a[2], a[3], team_a.abbr)
            continue
        team_b.remove_player(a)
        a.ps = False
        a.ir = None
        team_a.add_player(a)
        a.morale = max(1, a.morale - 8)
    if lg.phase in ("regular", "playoffs"):
        from free_agency import active_count, ai_cutdown
        for t in (team_a, team_b):
            if t.abbr != lg.user_abbr and active_count(t) > settings["roster_size"]:
                ai_cutdown(lg, t, settings["roster_size"])
    a_names = ", ".join(asset_label(lg, x) for x in a_gives) or "nothing"
    b_names = ", ".join(asset_label(lg, x) for x in b_gives) or "nothing"
    text = f"TRADE: {team_a.abbr} send {a_names} to {team_b.abbr} for {b_names}"
    lg.add_transaction(text)
    lg.add_news("Trade", text + (f". {why}" if why else ""), team_a.abbr)


def ai_trade_market(lg, chance=0.18):
    """Occasional AI-to-AI trades so the league feels alive."""
    teams = [t for t in lg.teams.values() if t.abbr != lg.user_abbr]
    if len(teams) < 2:
        return None
    if random.random() < 0.22 * settings["ai_trade_willingness"]:
        _veteran_for_pick(lg, teams)
    if random.random() > chance * settings["ai_trade_willingness"]:
        return None
    a, b = random.sample(teams, 2)
    na, nb = a.needs(), b.needs()
    pos_b_needs = max(nb, key=nb.get)
    pos_a_needs = max(na, key=na.get)
    if pos_a_needs == pos_b_needs:
        return None
    a_has = sorted(a.players_at(pos_b_needs), key=lambda p: -p.ca)
    b_has = sorted(b.players_at(pos_a_needs), key=lambda p: -p.ca)
    if len(a_has) < 2 or len(b_has) < 2:
        return None
    pa_, pb_ = a_has[1], b_has[1]
    va, vb = trade_value(pa_, lg, b), trade_value(pb_, lg, a)
    if min(va, vb) <= 0 or max(va, vb) / max(0.01, min(va, vb)) > 1.25:
        return None
    if settings["hard_cap"] and (a.payroll - pa_.salary + pb_.salary > lg.salary_cap or
                                 b.payroll - pb_.salary + pa_.salary > lg.salary_cap):
        return None
    execute(lg, a, b, [pa_], [pb_])
    return (a.abbr, b.abbr)


def _veteran_for_pick(lg, teams):
    """A rebuilding team sells a good veteran to a contender for a draft pick."""
    ranks = sorted(teams, key=lambda t: -t.overall)
    contenders, sellers = ranks[:8], ranks[-10:]
    seller = random.choice(sellers)
    buyer = random.choice(contenders)
    vets = [p for p in seller.players_at_any() if p.age >= 28 and p.ovr >= 76 and rr.is_active(p)]
    if not vets:
        return None
    p = random.choice(vets)
    need = buyer.needs().get(p.position, 0)
    have = [x.ovr for x in buyer.players_at(p.position)]
    upgrade = not have or p.ovr > sorted(have, reverse=True)[min(len(have), 2) - 1]
    if need < 0.08 and not upgrade:
        return None
    if settings["hard_cap"] and buyer.payroll + p.salary > lg.salary_cap:
        return None
    want = trade_value(p, lg, buyer)
    picks = sorted(rr.tradable_picks(lg, buyer.abbr),
                   key=lambda k: abs(rr.pick_value(lg, *k) - want))
    if not picks:
        return None
    y, r, o = picks[0]
    pv = rr.pick_value(lg, y, r, o)
    if not (0.6 * want <= pv <= 1.5 * want):
        return None
    execute(lg, seller, buyer, [p], [("pick", y, r, o)])
    return (seller.abbr, buyer.abbr)
