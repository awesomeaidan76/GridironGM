"""
trades.py — player and draft-pick trades: valuation and AI acceptance.

A trade asset is either a Player or a pick tuple ("pick", year, round, original team).
"""
import math

from contracts import market_value, fmt_money
from ratings import POSITION_VALUE, ROSTER_MINIMUM, AGE_CURVES, ovr_from_ca
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


# A player's worth, on the same scale as the draft-pick chart (roster_rules.pick_value: the #1 pick
# is about 53, the 32nd about 30, a mid third-rounder about 13). Value grows exponentially with
# his position-relative rating, so a star is worth several good starters: a 74 OVR (average) EDGE
# is worth about a third-round pick, an 85 about the first overall pick, a 90 about two firsts.
TV_BASE = 26.0        # an average starting quarterback (74 OVR) in his prime
TV_SCALE = 10.0       # OVR points that multiply a player's value by e
TV_KNEE = 16.0        # above 90 OVR the curve flattens (nobody trades a 99 for ten firsts)
UPSIDE_SHARE = 0.65   # share of the gap to his projected peak that a club pays for now
UPSIDE_DECAY = 0.92   # ...discounted for each year until he gets there
AGE_DECAY = 0.14      # value lost per year past his position's usual prime (ratings.AGE_CURVES)


def talent_value(ovr, pos):
    """What a player of this rating at this position is worth, in his prime, before his contract."""
    x = ovr - 74.0
    if x > TV_KNEE:
        x = TV_KNEE + (x - TV_KNEE) * 0.6
    return TV_BASE * math.exp(x / TV_SCALE) * POSITION_VALUE[pos]


def trade_value(p, lg, team=None):
    """How much a team values acquiring this player or pick (pick-chart units)."""
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
    v = talent_value(p.ovr, p.position)
    # Upside: what he could become, as far as this club's scouts can tell
    peak = fo.seen_pa(lg, team, p)
    if peak > p.ca and p.age <= 27:
        fut = talent_value(ovr_from_ca(peak, p.position), p.position)
        v += (fut - v) * UPSIDE_SHARE * UPSIDE_DECAY ** max(1.0, p.years_to_peak())
    v *= max(0.2, 1.0 - max(0, p.age - AGE_CURVES[p.position][1]) * AGE_DECAY)
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
    gp, tp = _players(give), _players(get)
    val_in, val_out = package_values(lg, ai_team, give, get)
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


def package_values(lg, team, incoming, outgoing):
    """
    A club's view of a deal: (value of what it gets, value of what it gives up).
    What it gets is worth what each piece adds to its roster (front_office.package_in).
    What it gives up is valued half through its own eyes (a rebuilding club lets veterans go
    cheaply, a loyal GM hates parting with his own players) and half at the market price,
    plus, for a club trying to win now, the hole the deal leaves in this season's lineup.
    """
    val_in = fo.package_in(lg, team, incoming, outgoing, lambda a: trade_value(a, lg, team))
    val_out = sum(trade_value(a, lg, team) for a in outgoing) * 0.5 + \
        sum(trade_value(a, lg, None) for a in outgoing) * 0.5
    if fo.gm_of(team) is not None:
        val_out += fo.lineup_loss(lg, team, _players(incoming), _players(outgoing),
                                  lambda p: talent_value(p.ovr, p.position))
    return val_in, val_out


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
