"""
situations.py — situational football: win probability, 4th-down and 2-point
decisions, timeouts, onside timing and the two-minute / four-minute clock.

No UI code. Decisions compare win probability for each option, then bend it
by the head coach: aggressive coaches go for it on closer calls, timid ones
kick unless the numbers scream. Poor game managers make noisier choices and
waste time and timeouts. Because coaches' aggressiveness drifts with what
works around the league, an "analytics era" can arrive - or not - on its own.
"""
import math
import random

import advanced as adv

FG_SNAP = 17          # kick distance = yards to goal + 17
# Real coaches are more cautious than the win-probability math: how much extra
# win probability they want before going for it / going for two.
FOURTH_CAUTION = 0.032
TWO_CAUTION = 0.012


def _phi(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def win_prob(diff, secs_left, ep_with_ball=0.0, edge=0.0):
    """
    Probability the team with the ball wins. diff: its lead; ep_with_ball: the
    expected points of its possession; edge: pre-game strength edge (points over a game).
    """
    secs = max(1.0, secs_left)
    sd = 13.4 * math.sqrt(secs / 3600.0) + 0.6
    return min(0.999, max(0.001, _phi((diff + ep_with_ball + edge * secs / 3600.0) / sd)))


def _after_kick_wp(diff, secs, opp_yl, edge):
    """Our win chance when the opponent gets the ball 1st-and-10 at opp_yl (their own yard line)."""
    opp_ep = adv.expected_points(1, 10, opp_yl)
    return 1.0 - win_prob(-diff, secs, opp_ep, -edge)


def conversion_prob(togo, yl, off_edge=0.0):
    """Chance to convert on 4th down (NFL-like), nudged by the offense/defense matchup."""
    base = {1: 0.68, 2: 0.58, 3: 0.53, 4: 0.48, 5: 0.45, 6: 0.41, 7: 0.38, 8: 0.35, 9: 0.33, 10: 0.31}
    p = base.get(togo, max(0.12, 0.31 - (togo - 10) * 0.018))
    if yl >= 95:                         # goal-line: compressed field
        p -= 0.04
    return min(0.9, max(0.05, p + off_edge))


def fourth_down_values(st):
    """
    st: dict with diff, secs, yl, togo, fg_prob, fg_range_ok, punt_net, edge, off_edge.
    Returns {"go": wp, "punt": wp, "fg": wp or None}.
    """
    diff, secs, yl, togo, edge = st["diff"], st["secs"], st["yl"], st["togo"], st.get("edge", 0.0)
    p = conversion_prob(togo, yl, st.get("off_edge", 0.0))
    gain = togo + 2.0
    new_yl = min(99, yl + gain)
    if new_yl >= 100 or yl + togo >= 100:
        succ = win_prob(diff + 7, secs - 6, -adv.KICKOFF_EP, edge) if yl + togo >= 100 else None
    else:
        succ = None
    if succ is None:
        succ = win_prob(diff, secs - 6, adv.expected_points(1, min(10, 100 - new_yl), new_yl), edge)
    fail = _after_kick_wp(diff, secs - 6, 100 - yl, edge)
    go = p * succ + (1 - p) * fail
    net = st.get("punt_net", 40)
    land = yl + net
    opp_yl = 20 if land >= 100 else max(1, 100 - land)
    punt = _after_kick_wp(diff, secs - 8, opp_yl, edge)
    fg = None
    if st.get("fg_range_ok"):
        fp = st["fg_prob"]
        make = 1.0 - win_prob(-(diff + 3), secs - 5, adv.KICKOFF_EP, -edge)
        miss = _after_kick_wp(diff, secs - 5, max(20, 100 - yl - 7), edge)
        fg = fp * make + (1 - fp) * miss
    return {"go": go, "punt": punt, "fg": fg}


def choose_fourth(st, aggression, game_mgmt, rng=random):
    """
    aggression 0-1 (coach tendency x league setting), game_mgmt 1-20.
    Returns "go", "punt" or "fg".
    """
    if st.get("fg_range_ok") and st["fg_prob"] < 0.45 and st["secs"] > 150:
        st = dict(st, fg_range_ok=False)       # coaches don't trust long-shot kicks until the end
    v = fourth_down_values(st)
    # Coaches don't trust the math equally: conservative ones demand a margin
    bias = (aggression - 0.5) * 0.04 - FOURTH_CAUTION
    noise = rng.gauss(0, 0.004 + (20 - game_mgmt) * 0.0012)
    kick = max(v["punt"], v["fg"] if v["fg"] is not None else -1)
    if v["go"] + bias + noise > kick:
        return "go"
    if v["fg"] is not None and v["fg"] >= v["punt"] - 0.002:
        return "fg"
    return "punt"


def two_point(diff_after_td, secs, xp_prob, aggression, game_mgmt, two_prob=0.48, edge=0.0, rng=random):
    """Kick the extra point or go for two (diff_after_td: our lead after the 6)."""
    xp = xp_prob * (1 - win_prob(-(diff_after_td + 1), secs, adv.KICKOFF_EP, -edge)) \
        + (1 - xp_prob) * (1 - win_prob(-diff_after_td, secs, adv.KICKOFF_EP, -edge))
    two = two_prob * (1 - win_prob(-(diff_after_td + 2), secs, adv.KICKOFF_EP, -edge)) \
        + (1 - two_prob) * (1 - win_prob(-diff_after_td, secs, adv.KICKOFF_EP, -edge))
    bias = (aggression - 0.5) * 0.012 - TWO_CAUTION
    noise = rng.gauss(0, 0.002 + (20 - game_mgmt) * 0.0006)
    return two + bias + noise > xp


def possessions_needed(deficit):
    return 0 if deficit <= 0 else (deficit + 7) // 8


def should_onside(deficit, secs, timeouts, rng=random):
    """
    Trailing team after a score: kick deep (and hope to get the ball back) or
    onside now? Deep only works if there's time to stop them and score again.
    """
    need = possessions_needed(deficit)
    if need <= 0:
        return False
    # time the opponent can burn if we kick deep and they run three times
    burn = max(0, 3 * 40 - 40 * min(3, timeouts) - 10)
    left_for_us = secs - burn - 25           # punt and return
    per_drive = 75.0                         # a hurried scoring drive
    if left_for_us >= need * per_drive:
        return False
    return need >= 2 or left_for_us < per_drive * 0.6


def offense_timeout(secs_after, yl, diff, timeouts, mode, fg_range_ok, game_mgmt, rng=random):
    """Two-minute drill: stop the clock after a play in bounds?"""
    if timeouts <= 0 or mode != "hurry":
        return False
    # Keep one for the field goal unit if we're already in range and only need 3
    if fg_range_ok and -3 <= diff <= 0 and timeouts == 1 and secs_after > 20:
        return False
    need = 100 - yl
    plays_left = secs_after / 25.0
    urgent = secs_after <= 90 or need / max(1.0, plays_left) > 9.0
    if not urgent:
        return False
    miss = max(0.0, (20 - game_mgmt) / 60.0)          # poor clock managers sit on timeouts
    return rng.random() > miss


def defense_timeout(secs, diff_def, timeouts, offense_mode, quarter, game_mgmt, rng=random):
    """Trailing defense stops the clock to get the ball back (or before half to get a last shot)."""
    if timeouts <= 0:
        return False
    miss = max(0.0, (20 - game_mgmt) / 70.0)
    if quarter >= 4 and diff_def < 0 and diff_def >= -16:
        need = possessions_needed(-diff_def)
        window = 60 * need + 40 * timeouts + 40
        return secs <= window and rng.random() > miss
    if quarter == 2 and offense_mode == "milk_half" and secs <= 120:
        return rng.random() < 0.35
    return False


def spike(secs, timeouts, mode, down, game_mgmt, rng=random):
    """Clock running in the hurry-up with no timeouts: spike it?"""
    if mode != "hurry" or timeouts > 0 or down >= 4:
        return False
    if secs > 45 or secs < 3:
        return False
    return rng.random() < 0.55 + game_mgmt / 60.0
