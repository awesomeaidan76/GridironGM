"""
inbox.py — the user's to-do list: decisions waiting on the GM, kept apart from
the news feed. No UI code; screens read `action_items(lg)` and call
`act(lg, item, action)` for the actions that can be taken inline.

Each item is a plain dict:
    kind      'offer', 'holdout', 'expiring', 'extension', 'ir', 'depth', 'roster', 'cap', 'draft'
    priority  1 = act now (something happens automatically if you don't), 2 = soon, 3 = worth a look
    title     one line
    detail    one or two sentences of context
    pid       player id, when the item is about one player
    offer     the trade offer dict, for 'offer' items
    actions   [(action id, button label)] — inline actions first, then navigation
"""
import free_agency as fa
import market
import roster_rules as rr
import trades
from contracts import fmt_money
from settings import settings

# Starters per position, as in Team.starters()
STARTERS = {"QB": 1, "RB": 1, "WR": 3, "TE": 1, "OT": 2, "IOL": 3, "DT": 2, "EDGE": 2,
            "LB": 3, "CB": 3, "S": 2, "K": 1, "P": 1}

IN_SEASON = ("regular", "playoffs")

# Navigation actions: action id -> screen key
GO = {"go_trades": "trades", "go_finances": "finances", "go_roster": "roster",
      "go_depth": "depth", "go_draft": "draft", "go_fa": "fa"}


def _item(kind, priority, title, detail, actions, pid=None, offer=None):
    return {"kind": kind, "priority": priority, "title": title, "detail": detail,
            "actions": actions, "pid": pid, "offer": offer}


def _starter_ids(team):
    return {p.id for players in team.starters().values() for p in players}


def action_items(lg):
    """Everything waiting on the user, most urgent first."""
    team = lg.user_team
    if team is None:
        return []
    out = []
    ph = lg.phase
    starters = _starter_ids(team)

    # Trade offers from other clubs
    clock = market._clock(lg)
    for o in getattr(lg, "trade_offers", []) or []:
        if o.get("expires", 0) < clock:
            continue
        give, get = market.offer_assets(lg, o)
        if any(a is None for a in give + get):
            continue
        club = lg.teams[o["from"]].full_name
        left = o.get("expires", clock) - clock
        out.append(_item(
            "offer", 1, f"Trade offer from the {club}",
            f"They give {', '.join(trades.asset_label(lg, a) for a in give)} for "
            f"{', '.join(trades.asset_label(lg, a) for a in get)}. "
            + ("Expires this week." if left <= 0 else f"Open for {left + 1} more weeks."),
            [("accept_offer", "Accept"), ("decline_offer", "Decline"), ("go_trades", "Trades")],
            offer=o))

    # Holdouts
    for p in team.roster:
        if getattr(p, "holdout", False):
            wks = getattr(p, "holdout_weeks", 0)
            out.append(_item(
                "holdout", 1, f"{p.position} {p.name} is holding out",
                f"He wants a new deal (now {fmt_money(p.salary)}/yr)"
                + (f" and has missed {wks} weeks." if wks else ".")
                + " He won't play until he signs or gives in.",
                [("negotiate", "Negotiate"), ("open_player", "Profile")], pid=p.id))

    # Re-signing window: expiring contracts
    if ph in ("season_end", "resign"):
        exp = sorted((p for p in team.roster if p.id in lg.expiring), key=lambda p: -fa.player_value(p))
        tag_ok = getattr(team, "tag_year", None) != lg.year
        key = [p for p in exp if p.id in starters or p.ovr >= 70]
        for p in key:
            actions = [("negotiate", "Re-sign")]
            if tag_ok:
                actions.append(("tag", "Tag"))
            actions.append(("open_player", "Profile"))
            starter = p.id in starters
            out.append(_item(
                "expiring", 1 if starter else 2,
                f"{p.position} {p.name}'s contract is expiring",
                f"Age {p.age}, OVR {p.ovr}{', a starter' if starter else ''}. He becomes a free "
                f"agent when the re-signing window closes unless you re-sign or tag him.",
                actions, pid=p.id))
        rest = [p for p in exp if p not in key]
        if rest:
            out.append(_item(
                "expiring", 3, f"{len(rest)} more expiring contract{'s' if len(rest) > 1 else ''} (depth players)",
                ", ".join(f"{p.position} {p.name}" for p in rest[:6]) + ("…" if len(rest) > 6 else "")
                + ". Re-sign any you want to keep on the Finances screen.",
                [("go_finances", "Finances")]))

    # In season: final-year starters who can be extended now
    if ph in IN_SEASON:
        for p in team.roster:
            if p.id in starters and p.contract and p.contract["years"] <= 1 and p.ovr >= 74 \
                    and not getattr(p, "holdout", False):
                out.append(_item(
                    "extension", 3, f"{p.position} {p.name} is in the last year of his deal",
                    f"OVR {p.ovr}, age {p.age}. Extending now avoids the re-signing window.",
                    [("negotiate", "Extend"), ("open_player", "Profile")], pid=p.id))

    # Injured players who could free a roster spot on injured reserve
    if ph in IN_SEASON:
        for p in team.roster:
            ok, _ = rr.can_place_ir(lg, p)
            if ok:
                wk = p.injury.get("weeks", 0)
                out.append(_item(
                    "ir", 2, f"{p.position} {p.name} could go on injured reserve",
                    f"Out {'for the season' if p.injury.get('season_ending') else f'{wk} weeks'} "
                    f"({p.injury['name']}). IR frees his roster spot.",
                    [("place_ir", "Place on IR"), ("go_roster", "Roster")], pid=p.id))

    # Depth chart: positions without enough healthy players to start
    if ph in IN_SEASON or ph == "preseason":
        for pos, need in STARTERS.items():
            have = len(team.depth(pos))
            if have < need:
                out.append(_item(
                    "depth", 1 if pos in ("QB", "K", "P") or have == 0 else 2,
                    f"Short at {pos}: {have} healthy for {need} starting spot{'s' if need > 1 else ''}",
                    "Players from other positions will fill in. Sign a free agent, promote "
                    "from the practice squad or reorder the depth chart.",
                    [("go_depth", "Depth Chart"), ("go_fa", "Free Agents")]))

    # Roster limit
    if ph in ("preseason",) + IN_SEASON:
        over = fa.active_count(team) - settings["roster_size"]
        if over > 0:
            out.append(_item(
                "roster", 1, f"{over} over the {settings['roster_size']}-man roster limit",
                "Release players or move young ones to the practice squad. "
                + ("The lowest-value players are cut automatically when camp ends."
                   if ph == "preseason" else ""),
                [("go_roster", "Roster")]))

    # Salary cap
    space = team.cap_space(lg.salary_cap)
    if space < 0:
        out.append(_item(
            "cap", 1, f"{fmt_money(-space)} over the salary cap",
            "Release or trade players to get under the cap.",
            [("go_finances", "Finances")]))

    # Draft day
    if ph == "draft":
        mine = [(r, pk) for r, pk, a in lg.draft_order[lg.draft_index:] if a == team.abbr]
        if mine:
            out.append(_item(
                "draft", 1, f"{len(mine)} draft pick{'s' if len(mine) > 1 else ''} to make",
                "Next: " + ", ".join(f"R{r} #{pk}" for r, pk in mine[:5])
                + ". Continuing auto-drafts any picks you haven't used.",
                [("go_draft", "Draft")]))

    out.sort(key=lambda it: it["priority"])
    return out


def urgent_count(lg):
    return sum(1 for it in action_items(lg) if it["priority"] == 1)


def act(lg, item, action):
    """Run an inline action that needs no dialog. Returns (ok, message)."""
    if action == "accept_offer":
        return market.accept_offer(lg, item["offer"])
    if action == "decline_offer":
        market.decline_offer(lg, item["offer"])
        return True, "Offer declined."
    p = lg.find_player(item["pid"]) if item.get("pid") is not None else None
    if p is None:
        return False, "That player is no longer here."
    if action == "place_ir":
        return rr.place_ir(lg, lg.user_team, p)
    if action == "tag":
        return rr.apply_tag(lg, lg.user_team, p)
    return False, f"Unknown action {action}"
