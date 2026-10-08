"""
contracts.py — salaries, market value and rookie scale.

All money is in whole dollars. Salaries scale with the salary cap so the
economy stays consistent if the cap grows or is changed in settings.
"""
import random

# Top-of-market salary at each position as a fraction of the cap
POSITION_MAX_SHARE = {
    "QB": 0.215, "EDGE": 0.140, "WR": 0.135, "DT": 0.120, "OT": 0.110,
    "CB": 0.100, "S": 0.080, "LB": 0.080, "IOL": 0.080, "TE": 0.070,
    "RB": 0.060, "FB": 0.016, "K": 0.022, "P": 0.014,
}
MIN_SHARE = 0.0036          # league minimum (~$0.9m on a $255m cap)


def min_salary(cap):
    return int(cap * MIN_SHARE)


def market_value(player, cap):
    """What a player would command on the open market, per season."""
    lo = MIN_SHARE
    hi = POSITION_MAX_SHARE.get(player.position, 0.06)
    x = max(0.0, min(1.0, (player.ca - 95) / 100.0))
    share = lo + (hi - lo) * (x ** 1.35)
    # Age: teams pay less for players about to decline
    if player.age >= 30:
        share *= max(0.45, 1.0 - 0.08 * (player.age - 29))
    elif player.age <= 25 and player.pa - player.ca > 15:
        share *= 1.08
    # Fame adds a premium
    share *= 1.0 + player.reputation / 100.0 * 0.15
    return max(min_salary(cap), int(cap * share))


def asking_salary(player, cap, mood=1.0):
    """What a free agent asks for (ambitious players ask for more)."""
    amb = player.hidden.get("ambition", 50)
    ask = market_value(player, cap) * (1.0 + (amb - 50) / 300.0) * mood
    return max(min_salary(cap), int(ask))


def contract_length(player):
    if player.age <= 25:
        return random.randint(3, 5)
    if player.age <= 28:
        return random.randint(2, 4)
    if player.age <= 31:
        return random.randint(1, 3)
    return random.randint(1, 2)


def rookie_salary(pick, cap):
    """Rookie wage scale by overall pick number (1 = first overall)."""
    import math
    lo = MIN_SHARE
    share = lo + (0.040 - lo) * math.exp(-(pick - 1) / 22.0)
    return int(cap * share)


def make_contract(salary, years, season):
    return {"salary": int(salary), "years": int(years), "signed": season}


def fmt_money(amount):
    if amount >= 1_000_000:
        return f"${amount / 1_000_000:.1f}M"
    if amount >= 1_000:
        return f"${amount / 1_000:.0f}K"
    return f"${amount}"
