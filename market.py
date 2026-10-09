"""
market.py — the league's transaction market: AI-to-AI trades of players and
picks, draft-day trades, in-season depth churn and trade offers to the user.

Every AI deal is built the same way: one side has a reason (a hole at a
position, a rebuild, a contender's push, cap trouble), it finds a partner,
and the package is balanced with draft picks until both sides' valuations
(trades.trade_value) are within a tolerance. AI teams don't fleece each other;
the reasons make deals happen, not bad valuations.
"""
import random

import front_office as fo
import roster_rules as rr
from settings import settings
from trades import trade_value, execute, is_pick, asset_label

TRADE_TOL = 0.22          # how close the two sides' values must be


def _ai_teams(lg):
    return [t for t in lg.teams.values() if t.abbr != lg.user_abbr]


def _ranks(lg):
    return lg.strength_order()


def _mode(lg, team):
    """'contend', 'middle' or 'rebuild' from the club's front-office plan."""
    if fo.gm_of(team) is None:
        rank = _ranks(lg).index(team.abbr)
        return "contend" if rank < 10 else "rebuild" if rank >= 22 else "middle"
    m = fo.plan_of(team)
    return "contend" if m in fo.BUYERS else "rebuild" if m in fo.SELLERS else "middle"


def _weighted(teams, fn):
    w = [max(0.0, fn(t)) for t in teams]
    if sum(w) <= 0:
        return None
    return random.choices(teams, weights=w)[0]


def _agrees(lg, team, gets, gives, slack=0.0):
    """Does this club's GM see the deal as worth it from his side?"""
    vin = _value(lg, gets, team)
    vout = _value(lg, gives, team)
    return vin >= vout * (fo.demand(team) - slack) - 0.5


def _cap_ok(lg, team, incoming, outgoing):
    if not settings["hard_cap"]:
        return True
    pay = team.payroll + sum(p.salary for p in incoming if not is_pick(p)) \
        - sum(p.salary for p in outgoing if not is_pick(p))
    return pay <= lg.salary_cap


def _value(lg, assets, team):
    return sum(trade_value(a, lg, team) for a in assets)


def _balance_with_picks(lg, payer, want_value, have_value, exclude=()):
    """Add payer's picks (smallest that close the gap first) until values meet. Returns picks or None."""
    picks = [("pick", y, r, o) for y, r, o in rr.tradable_picks(lg, payer.abbr)]
    picks = [p for p in picks if p not in exclude]
    picks.sort(key=lambda k: rr.pick_value(lg, k[1], k[2], k[3]))
    out = []
    gap = want_value - have_value
    while gap > want_value * TRADE_TOL * 0.5 and picks:
        fit = [k for k in picks if rr.pick_value(lg, k[1], k[2], k[3]) >= gap * 0.6]
        k = fit[0] if fit else picks[-1]
        picks.remove(k)
        out.append(k)
        gap -= rr.pick_value(lg, k[1], k[2], k[3])
        if len(out) >= 3:
            break
    return out if gap <= want_value * TRADE_TOL else None


def _sellable(team, min_ovr=0):
    return [p for p in team.roster if rr.is_active(p) and not p.is_injured and p.ovr >= min_ovr]


# ── Deal types ────────────────────────────────────────────────────────────────

def _need_swap(lg, teams):
    """Two teams with complementary holes swap players, picks balance it."""
    a, b = random.sample(teams, 2)
    na, nb = a.needs(), b.needs()
    pa_pos = max(nb, key=nb.get)      # what b wants (from a)
    pb_pos = max(na, key=na.get)      # what a wants (from b)
    if pa_pos == pb_pos:
        return None
    a_has = sorted(a.players_at(pa_pos), key=lambda p: -p.ca)
    b_has = sorted(b.players_at(pb_pos), key=lambda p: -p.ca)
    if len(a_has) < 2 or len(b_has) < 2:
        return None
    x = a_has[random.randint(1, min(2, len(a_has) - 1))]
    y = b_has[random.randint(1, min(2, len(b_has) - 1))]
    vx, vy = trade_value(x, lg, b), trade_value(y, lg, a)
    if min(vx, vy) <= 1:
        return None
    a_gets, b_gets = [y], [x]
    if vx < vy * (1 - TRADE_TOL):           # a must add
        add = _balance_with_picks(lg, a, vy, vx)
        if add is None:
            return None
        b_gets += add
    elif vy < vx * (1 - TRADE_TOL):
        add = _balance_with_picks(lg, b, vx, vy)
        if add is None:
            return None
        a_gets += add
    if not (_cap_ok(lg, a, [y], [x]) and _cap_ok(lg, b, [x], [y])):
        return None
    if not (_agrees(lg, a, a_gets, b_gets, 0.15) and _agrees(lg, b, b_gets, a_gets, 0.15)):
        return None
    execute(lg, a, b, [g for g in b_gets], [g for g in a_gets],
            why=f"A swap of needs: {a.name} wanted a {y.position}, {b.name} a {x.position}.")
    return True


def _buyer_w(lg, t):
    return fo.param(t, "buy") * (0.4 + fo.activity(t)) if fo.gm_of(t) else 0.0


def _seller_w(lg, t):
    return fo.param(t, "sell") * (0.4 + fo.activity(t)) if fo.gm_of(t) else 0.0


def _raw_picks_for(lg, seller, value):
    """Convert value in the seller's eyes into raw pick value (sellers prize picks)."""
    return value / fo.pick_mult(lg, seller, lg.year + 1)


def _contender_buys(lg, teams):
    """A buyer (contending / all-in club) sends picks to a seller (rebuilding club) for a veteran."""
    buyer = _weighted(teams, lambda t: _buyer_w(lg, t))
    seller = _weighted([t for t in teams if t is not buyer], lambda t: _seller_w(lg, t))
    if buyer is None or seller is None:
        return None
    needs = buyer.needs()
    cands = [p for p in _sellable(seller, 72) if p.age >= 26 and p.position not in ("K", "P", "FB")]
    if not cands:
        return None
    cands.sort(key=lambda p: -(needs.get(p.position, 0) * 30 + p.ovr))
    target = cands[0]
    have = sorted((x.ovr for x in buyer.players_at(target.position)), reverse=True)
    if have and target.ovr <= have[0] - 2 and needs.get(target.position, 0) < 0.3:
        return None
    want = trade_value(target, lg, seller) * 1.05 * fo.demand(seller)
    picks = _balance_with_picks(lg, buyer, _raw_picks_for(lg, seller, want), 0.0)
    if not picks:
        return None
    if not _cap_ok(lg, buyer, [target], []):
        return None
    if not _agrees(lg, buyer, [target], picks, 0.10):
        return None
    execute(lg, seller, buyer, [target], picks, why=fo.trade_note(seller, buyer))
    return True


def _blockbuster(lg, teams):
    """An all-in club (or a star-chasing GM) pays a premium - first-round picks - for a star."""
    def w(t):
        g = fo.gm_of(t)
        if g is None:
            return 0.0
        base = {"All-In": 1.0, "Last Dance": 0.8, "Contend": 0.25}.get(fo.plan_of(t), 0.0)
        return base * (0.3 + g.t("stars") + g.t("risk") * 0.5)
    buyer = _weighted(teams, w)
    if buyer is None:
        return None
    sellers = [t for t in teams if t is not buyer and fo.plan_of(t) in fo.SELLERS]
    if not sellers:
        return None
    seller = _weighted(sellers, lambda t: _seller_w(lg, t))
    stars = [p for p in _sellable(seller, 83) if p.age <= 31]
    if not stars:
        return None
    target = max(stars, key=lambda p: p.ovr + fo.position_value(lg, buyer, p.position) * 6)
    want = trade_value(target, lg, seller) * 1.10 * fo.demand(seller)
    give = []
    young = [p for p in _sellable(buyer, 66) if p.age <= 25 and p.position != target.position
             and p.ovr < 82]
    if young:
        y = max(young, key=lambda p: trade_value(p, lg, seller))
        if trade_value(y, lg, seller) < want * 0.6:
            give.append(y)
    have = _value(lg, give, seller)
    picks = []
    raw = rr.tradable_picks(lg, buyer.abbr)
    firsts = sorted((("pick", *k) for k in raw if k[1] == 1), key=lambda k: k[1])
    for k in firsts:
        if have >= want * (1 - TRADE_TOL * 0.5) or len(picks) >= 2:
            break
        picks.append(k)
        have += trade_value(k, lg, seller)
    if have < want * (1 - TRADE_TOL):
        extra = _balance_with_picks(lg, buyer, _raw_picks_for(lg, seller, want - have), 0.0,
                                    exclude=picks)
        if extra is None:
            return None
        picks += extra
    give += picks
    if not give or not _cap_ok(lg, buyer, [target], [g for g in give if not is_pick(g)]):
        return None
    if not _agrees(lg, buyer, [target], give, 0.20):
        return None
    execute(lg, seller, buyer, [target], give,
            why=f"Blockbuster: the {fo.describe(buyer)} {buyer.name} push their chips in for a star.")
    return True


def _salary_dump(lg, teams):
    """A team pressed against the cap moves a veteran contract for a late pick."""
    tight = [t for t in teams if t.cap_space(lg.salary_cap) < lg.salary_cap * 0.02
             or fo.plan_of(t) == "Cap Reset"]
    roomy = [t for t in teams if t.cap_space(lg.salary_cap) > lg.salary_cap * 0.08]
    if not tight or not roomy:
        return None
    a = _weighted(tight, lambda t: 3.0 if fo.plan_of(t) == "Cap Reset" else 1.0)
    b = _weighted(roomy, lambda t: 0.5 + fo.activity(t))
    vets = [p for p in _sellable(a, 65) if p.salary > lg.salary_cap * 0.02 and p.age >= 28]
    if not vets:
        return None
    p = random.choice(vets)
    v = trade_value(p, lg, b)
    if v <= 0:
        return None
    picks = sorted(rr.tradable_picks(lg, b.abbr), key=lambda k: abs(rr.pick_value(lg, *k) - v))
    pick = [("pick", *picks[0])] if picks and rr.pick_value(lg, *picks[0]) <= v * 1.1 else []
    if not _cap_ok(lg, b, [p], []):
        return None
    execute(lg, a, b, [p], pick, why=f"A salary dump: the {fo.describe(a)} {a.name} clear cap space.")
    return True


def _pick_swap(lg, teams):
    """Teams move up or down in a future draft: gamblers move up, analytics GMs trade down."""
    a = _weighted(teams, lambda t: 0.3 + (fo.gm_of(t).t("risk") if fo.gm_of(t) else 0.5))
    b = _weighted([t for t in teams if t is not a],
                  lambda t: 0.3 + (fo.gm_of(t).t("analytics") if fo.gm_of(t) else 0.5))
    if a is None or b is None:
        return None
    pa = [k for k in rr.tradable_picks(lg, a.abbr)]
    pb = [k for k in rr.tradable_picks(lg, b.abbr)]
    if not pa or not pb:
        return None
    x = random.choice(pa)
    vx = rr.pick_value(lg, *x)
    better = [k for k in pb if rr.pick_value(lg, *k) > vx * 1.15]
    if not better:
        return None
    y = min(better, key=lambda k: rr.pick_value(lg, *k))
    vy = rr.pick_value(lg, *y)
    add = _balance_with_picks(lg, a, vy, vx, exclude=[("pick", *x)])
    if add is None:
        return None
    execute(lg, a, b, [("pick", *x)] + add, [("pick", *y)],
            why=f"{b.name} trade down for extra picks.")
    return True


DEALS = [(_need_swap, 0.36), (_contender_buys, 0.30), (_blockbuster, 0.06), (_salary_dump, 0.11),
         (_pick_swap, 0.17)]


def ai_trades(lg, attempts):
    """Run several deal attempts. Returns the number of completed trades."""
    teams = _ai_teams(lg)
    if len(teams) < 4:
        return 0
    will = settings["ai_trade_willingness"]
    done = 0
    for _ in range(attempts):
        if random.random() > min(1.0, 0.6 * will):
            continue
        fn = random.choices([d for d, _ in DEALS], weights=[w for _, w in DEALS])[0]
        try:
            if fn(lg, teams):
                done += 1
        except (ValueError, IndexError):
            continue
    return done


def weekly(lg):
    """In-season market activity (called after each regular-season week)."""
    fo.ensure(lg)
    if lg.phase == "regular" and lg.week + 2 == settings["trade_deadline_week"]:
        fo.update_plans(lg, midseason=True)       # buyers and sellers declare themselves
    if lg.phase == "regular" and lg.week + 1 < settings["trade_deadline_week"]:
        # More action as the deadline approaches
        attempts = 2 + (3 if lg.week + 2 >= settings["trade_deadline_week"] else 0)
        ai_trades(lg, attempts)
        maybe_offer_user(lg)
    depth_churn(lg)


def offseason(lg, phase):
    """Offseason trade windows: around re-signing, before the draft and in free agency."""
    fo.ensure(lg)
    attempts = {"resign": 4, "draft": 5, "free_agency": 6, "preseason": 3}.get(phase, 0)
    ai_trades(lg, attempts)
    if phase in ("resign", "free_agency", "preseason"):
        maybe_offer_user(lg, chance=0.6)


def depth_churn(lg):
    """AI teams swap their worst depth player for a better free agent now and then."""
    import free_agency as fa
    from contracts import min_salary
    for team in _ai_teams(lg):
        if random.random() > 0.16:
            continue
        needs = team.needs()
        pos = max(needs, key=needs.get)
        mine = sorted(team.players_at(pos), key=lambda p: p.ca)
        cands = [p for p in lg.free_agents if p.position == pos and not p.is_injured]
        if not mine or not cands:
            continue
        best = max(cands, key=lambda p: p.ca)
        worst = mine[0]
        if best.ca <= worst.ca + 6:
            continue
        cost = max(min_salary(lg.salary_cap), int(fa.asking(lg, best) * 0.7))
        if settings["hard_cap"] and team.cap_space(lg.salary_cap) < cost:
            continue
        fa.release(lg, team, worst, quiet=True)
        fa.sign(lg, team, best, cost, 1, quiet=True)
        lg.add_transaction(f"{team.abbr} signed {best.position} {best.name}, released {worst.name}")


# ── Draft-day trades ──────────────────────────────────────────────────────────

def draft_day_trade(lg):
    """
    Before an AI pick: the team on the clock may trade down with a team that
    wants to move up. Returns True if the pick changed hands.
    """
    if lg.draft_index >= len(lg.draft_order):
        return False
    rnd, pk, owner = lg.draft_order[lg.draft_index]
    if owner == lg.user_abbr:
        return False
    chance = {1: 0.14, 2: 0.10, 3: 0.07}.get(rnd, 0.04) * settings["ai_trade_willingness"]
    sg = fo.gm_of(lg.teams[owner])
    if sg is not None:
        # analytics-minded and patient GMs love to trade down
        chance *= 0.45 + sg.t("analytics") * 0.7 + sg.t("patience") * 0.3
    if random.random() > chance:
        return False
    year = lg.year + 1
    orig = lg.draft_orig[lg.draft_index] if getattr(lg, "draft_orig", None) else owner
    cur_v = rr.pick_value(lg, year, rnd, orig)
    # Teams picking later in this draft
    later = {}
    for i in range(lg.draft_index + 1, min(len(lg.draft_order), lg.draft_index + 40)):
        r2, pk2, own2 = lg.draft_order[i]
        if own2 in (owner, lg.user_abbr) or own2 in later:
            continue
        later[own2] = (i, r2, lg.draft_orig[i] if getattr(lg, "draft_orig", None) else own2)
    if not later:
        return False
    # Who wants to jump up? Gamblers, and anyone hunting a quarterback when one is on the board
    top_qb = any(p.position == "QB" and p.proj_rank and p.proj_rank <= lg.draft_index + 6
                 for p in lg.draft_class[:8])

    def jump(abbr):
        t = lg.teams[abbr]
        g = fo.gm_of(t)
        w = 0.3 + (g.t("risk") if g else 0.5)
        if top_qb and rnd == 1 and "Find a franchise QB" in (getattr(t, "plan", None) or {}).get("focus", ()):
            w += 1.5
        return w
    cands = list(later)
    buyer_abbr = random.choices(cands, weights=[jump(a) for a in cands])[0]
    i, r2, o2 = later[buyer_abbr]
    their = ("pick", year, r2, o2)
    their_v = rr.pick_value(lg, year, r2, o2)
    buyer = lg.teams[buyer_abbr]
    add = _balance_with_picks(lg, buyer, cur_v * 1.05, their_v, exclude=[their])
    if add is None:
        return False
    seller = lg.teams[owner]
    execute(lg, buyer, seller, [their] + add, [("pick", year, rnd, orig)])
    lg.add_news("Draft", f"Trade: {buyer.full_name} move up to pick {pk}, sending "
                         f"{', '.join(asset_label(lg, a) for a in [their] + add)} to "
                         f"{seller.full_name}"
                         + (f" ({fo.gm_of(seller).name} trades down again)." if fo.gm_of(seller) and
                            fo.gm_of(seller).t("analytics") >= 0.7 else "."), buyer_abbr)
    return True


# ── Offers to the user ────────────────────────────────────────────────────────

def maybe_offer_user(lg, chance=0.35):
    """An AI team proposes a deal for one of your players."""
    user = lg.user_team
    if user is None or random.random() > chance * settings["ai_trade_willingness"]:
        return None
    if not hasattr(lg, "trade_offers"):
        lg.trade_offers = []
    lg.trade_offers = [o for o in lg.trade_offers if o.get("expires", 0) >= _clock(lg)]
    if len(lg.trade_offers) >= 4:
        return None
    team = random.choice(_ai_teams(lg))
    needs = team.needs()
    cands = [p for p in _sellable(user, 66) if needs.get(p.position, 0) > 0.15]
    if not cands:
        return None
    target = max(cands, key=lambda p: needs.get(p.position, 0) * 30 + p.ovr + random.uniform(0, 8))
    want = trade_value(target, lg, None) * random.uniform(1.0, 1.15)
    # Offer a player at a position the user needs, topped up with picks
    un = user.needs()
    give = []
    pool = sorted(_sellable(team, 60), key=lambda p: -(un.get(p.position, 0) * 25 + p.ovr))
    for p in pool[:3]:
        if p.position != target.position and trade_value(p, lg, user) < want * 0.9:
            give.append(p)
            break
    have = _value(lg, give, user)
    picks = _balance_with_picks(lg, team, want, have)
    if picks is None:
        return None
    give += picks
    if not give:
        return None
    if not _cap_ok(lg, team, [target], [g for g in give if not is_pick(g)]):
        return None
    offer = {"from": team.abbr, "give": [_ref(a) for a in give], "get": [_ref(target)],
             "expires": _clock(lg) + 2, "made": lg.week_label}
    lg.trade_offers.append(offer)
    lg.add_news("Trade", f"{team.full_name} offer {', '.join(asset_label(lg, a) for a in give)} "
                         f"for {target.position} {target.name}. See the Trades screen.", user.abbr)
    return offer


def _clock(lg):
    """A simple counter that moves with weeks and offseason phases."""
    order = ["regular", "playoffs", "season_end", "resign", "draft", "free_agency", "preseason"]
    return lg.year * 100 + order.index(lg.phase) * 20 + (lg.week if lg.phase == "regular" else 0)


def _ref(asset):
    return list(asset) if is_pick(asset) else asset.id


def resolve_ref(lg, ref):
    if isinstance(ref, (list, tuple)):
        return tuple(ref)
    return lg.find_player(ref)


def offer_assets(lg, offer):
    give = [resolve_ref(lg, r) for r in offer["give"]]
    get = [resolve_ref(lg, r) for r in offer["get"]]
    return give, get


def accept_offer(lg, offer):
    """Execute an AI offer the user accepted. Returns (ok, message)."""
    from trades import evaluate
    team = lg.teams[offer["from"]]
    give, get = offer_assets(lg, offer)
    if any(a is None for a in give + get):
        return False, "The offer is no longer valid."
    # The user gives `get`, receives `give`
    ok, msg, _, _ = evaluate(lg, lg.user_team, team, get, give)
    if not ok and "accept" not in msg:
        # The AI made the offer, so it accepts; only legality checks matter
        if "deadline" in msg or "playoffs" in msg or "cap" in msg or "roster" in msg or "own" in msg:
            return False, msg
    execute(lg, lg.user_team, team, get, give)
    lg.trade_offers.remove(offer)
    return True, "Trade completed."


def decline_offer(lg, offer):
    if offer in getattr(lg, "trade_offers", []):
        lg.trade_offers.remove(offer)
