"""
Special teams library: kickoff and punt types, return schemes and the
receiving side's calls (punt block, safe/fake-watch, field-goal block).

Like the offensive and defensive libraries this is plain data plus small
selection functions; the match engine applies the effects. The concepts are
the standard ones from special-teams coaching manuals: lane coverage with
gunners and contain men, middle/sideline-wall/wedge returns, spread and
rugby punts, punt-block and safe returns, hands-team onside recoveries.
"""
import random

KICKOFFS = {
    "Deep Kickoff": "Kick for the end zone; the coverage team runs its lanes",
    "Directional Kickoff": "Kick toward a sideline so the boundary acts as an extra defender",
    "Squib Kick": "Low, bouncing kick that can't be returned far; used late in a half",
    "Pooch Kick": "High, short kick meant to be fair-caught or downed short of the goal line",
    "Onside Kick": "Short kick the kicking team tries to recover; the receivers send their hands team",
    "Surprise Onside": "An onside kick when nobody expects it",
    "Landing Zone Kick": "Dynamic kickoff: a high kick placed between the goal line and the 20, which has "
                         "to be returned; short of the zone gives the ball away at the 40, in the end zone "
                         "in the air is a touchback",
}
FREE_KICKS = {
    "Safety Punt": "After a safety the team that gave it up punts (or kicks) from its own 20; it can be "
                   "returned or fair-caught like a punt",
    "Fair Catch Kick": "After a fair catch the receiving team may try a free-kick field goal from the spot, "
                       "with no rush; a rare end-of-half play",
}
KICK_RETURNS = {
    "Middle Return": "Blockers build a seam up the middle of the field",
    "Sideline Wall": "Blockers form a wall along one hash and the returner breaks for the sideline",
    "Wedge Return": "Blockers form a wedge in front of the returner; steady, rarely explosive",
    "Kickoff Reverse": "Hand-off to a second returner going the other way; boom or bust",
    "Return to the Field": "Blockers set up away from the sideline the kick is aimed at; beats directional "
                           "kicks, a little worse against a kick down the middle",
    "Throwback": "The returner draws the coverage to one side, then throws a lateral across the field to "
                 "a teammate; big plays and the odd fumble",
}
PUNTS = {
    "Spread Punt": "Standard spread formation with two gunners and a personal protector",
    "Directional Punt": "Aim for the sideline to limit the return",
    "Rugby Punt": "The punter rolls out and kicks on the run; a low, bouncing ball that is hard to return",
    "Pooch Punt": "Short, high punt near midfield, aimed to pin the ball inside the 10",
    "Coffin Corner Punt": "Aim the punt out of bounds inside the 10: no return, but a miss is a touchback "
                          "or a short punt",
    "Quick Kick": "A surprise punt on third down from the shotgun: nobody is back to return it, so it rolls",
}
PUNT_RETURNS = {
    "Punt Return": "Hold up the gunners and set up a return",
    "Return Wall": "Set up a wall to one sideline",
    "Punt Block": "Bring extra rushers to block the punt; risky against a fake",
    "Punt Safe": "Keep the defence on the field and watch for a fake",
    "Hold-Up Return": "Double-team both gunners: fewer fair catches and longer returns, but more "
                      "block-in-the-back flags and no rush on the punter",
}
FG_DEFENSE = {
    "Field Goal Block": "Overload one side to try to block the kick",
    "Field Goal Safe": "Rush conservatively and watch for a fake",
}

FAKES = {
    "Up-Back Run": "Fake punt: the ball is snapped straight to the up-back, who runs behind the wing blockers",
    "Punter Pass": "Fake punt: the punter throws to a gunner or wing who sneaks out",
    "Punter Run": "Fake punt: the punter takes off around the edge when the rush overcommits",
    "Holder Run": "Fake field goal: the holder keeps the snap and runs for the corner",
    "Holder Pass": "Fake field goal: the holder throws to a tight end or wing who leaks out",
    "Swinging Gate": "Two-point try from a field-goal look: the line shifts out wide and the ball is snapped "
                     "to a runner or passer if the defense doesn't follow",
}

ALL_CALLS = sorted(KICKOFFS) + sorted(KICK_RETURNS) + sorted(PUNTS) + sorted(PUNT_RETURNS) + sorted(FG_DEFENSE) \
    + sorted(FAKES)


def describe(name):
    for d in (KICKOFFS, KICK_RETURNS, PUNTS, PUNT_RETURNS, FG_DEFENSE, FAKES, FREE_KICKS):
        if name in d:
            return d[name]
    return ""


def _pick(rng, opts, prefs):
    names = list(opts)
    w = [max(0.0, opts[n] * prefs.get("st:" + n, 1.0)) for n in names]
    if sum(w) <= 0:
        w = [opts[n] for n in names]
    return rng.choices(names, weights=w, k=1)[0]


def choose_kickoff(sit, prefs=None, rng=random):
    """sit: late_half (bool), onside_needed (bool), aggression (0-1), lead, returner (rating),
    dynamic (the dynamic kickoff rule is in force), tb_spot (where a touchback is placed)."""
    prefs = prefs or {}
    if sit.get("onside_needed"):
        return "Onside Kick"
    danger = max(0.0, sit.get("returner", 75) - 90) / 6.0
    if sit.get("dynamic"):
        # onside kicks must be declared, so no surprises; a touchback is worth more the further out it goes
        tb = sit.get("tb_spot", 30)
        opts = {"Landing Zone Kick": 6.0, "Deep Kickoff": 0.6 + 2.5 * danger + max(0, 35 - tb) * 1.5,
                "Squib Kick": 0.15 + (2.5 if sit.get("late_half") else 0.0) + 0.3 * danger}
        return _pick(rng, opts, prefs)
    surprise = 0.0012 * (0.4 + 1.6 * sit.get("aggression", 0.45)) * prefs.get("st:Surprise Onside", 1.0)
    if sit.get("lead", 0) < 10 and rng.random() < surprise:
        return "Surprise Onside"
    opts = {"Deep Kickoff": 6.0, "Directional Kickoff": 0.9 + 2.0 * danger, "Pooch Kick": 0.35,
            "Squib Kick": 0.10 + (3.0 if sit.get("late_half") else 0.0) + 0.4 * danger}
    return _pick(rng, opts, prefs)


def choose_kick_return(prefs=None, rng=random):
    opts = {"Middle Return": 3.0, "Sideline Wall": 2.2, "Wedge Return": 1.0, "Kickoff Reverse": 0.12,
            "Return to the Field": 1.0, "Throwback": 0.08}
    return _pick(rng, opts, prefs or {})


def choose_punt(sit, prefs=None, rng=random):
    """sit: to_goal (yards to the receiving goal line), wind (mph), accuracy (punter)."""
    prefs = prefs or {}
    tg = sit["to_goal"]
    opts = {"Spread Punt": 6.0, "Directional Punt": 1.5, "Rugby Punt": 0.4}
    if tg <= 48:
        opts["Pooch Punt"] = 5.0
        opts["Directional Punt"] += 2.0
    if 30 <= tg <= 58:
        opts["Coffin Corner Punt"] = 0.25 + max(0.0, sit.get("accuracy", 70) - 75) * 0.05
    if sit.get("wind", 0) >= 15:
        opts["Rugby Punt"] += 1.0
    return _pick(rng, opts, prefs)


def choose_punt_return(sit, prefs=None, rng=random):
    """sit: togo, to_goal (punting team's yards to the opponent's goal), fake_threat (0-1)."""
    prefs = prefs or {}
    opts = {"Punt Return": 4.5, "Return Wall": 2.5, "Punt Block": 0.8, "Punt Safe": 0.6,
            "Hold-Up Return": 1.0 + max(0.0, sit.get("returner", 75) - 85) / 5.0}
    if sit["togo"] <= 4 and 35 <= sit["to_goal"] <= 70:
        opts["Punt Safe"] += 3.0 * (0.5 + sit.get("fake_threat", 0.5))
    if sit["to_goal"] >= 85:
        opts["Punt Block"] += 1.5            # punting from deep in his own end
    return _pick(rng, opts, prefs)


def choose_fg_defense(sit, prefs=None, rng=random):
    prefs = prefs or {}
    opts = {"Field Goal Block": 1.0 + (0.8 if sit.get("must_stop") else 0.0),
            "Field Goal Safe": 1.4 + (1.2 if sit["togo"] <= 3 else 0.0)}
    return _pick(rng, opts, prefs)


def choose_fake(kind, sit=None, prefs=None, rng=random):
    """kind: "punt", "fg" or "two" (a two-point try). sit: arm (the punter's throwing), togo."""
    prefs = prefs or {}
    sit = sit or {}
    if kind == "punt":
        opts = {"Up-Back Run": 3.0 + (1.5 if sit.get("togo", 5) <= 2 else 0.0),
                "Punter Pass": 1.2 + max(0.0, sit.get("arm", 40) - 50) / 20.0, "Punter Run": 0.5}
    elif kind == "fg":
        opts = {"Holder Pass": 2.0 + max(0.0, sit.get("arm", 40) - 50) / 20.0, "Holder Run": 1.6}
    else:
        opts = {"Swinging Gate": 1.0}
    return _pick(rng, opts, prefs)
