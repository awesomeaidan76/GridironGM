"""
Game-day weather. Each stadium has a climate; the week of the season sets the
month. Weather nudges passing accuracy, ball security, kicking and play calling,
which gives the occasional snow-globe slugfest or windy field-goal adventure.
"""
import random

# Stadium climates. "dome" games are always perfect conditions.
#   (sep_temp_F, dec_temp_F, precip_chance, snow_ok, wind_mean_mph, altitude)
CLIMATES = {
    "dome":      None,
    "cold":      (68, 30, 0.22, True, 11, False),
    "lake":      (66, 27, 0.25, True, 13, False),
    "mild_east": (74, 40, 0.24, True, 10, False),
    "rainy":     (68, 44, 0.38, False, 9, False),
    "warm":      (86, 66, 0.25, False, 9, False),
    "coastal":   (72, 58, 0.12, False, 10, False),
    "mountain":  (70, 32, 0.15, True, 9, True),
}

STADIUMS = {
    # Domes / roofs
    "DET": "dome", "MIN": "dome", "HOU": "dome", "NOL": "dome", "IND": "dome",
    "ATL": "dome", "LVG": "dome", "DAL": "dome", "LAC": "dome", "PHX": "dome",
    # Open air
    "PIT": "cold", "CLE": "lake", "PHI": "mild_east", "NYS": "mild_east",
    "BOS": "cold", "WAS": "mild_east", "DEN": "mountain", "MIA": "warm",
    "JAX": "warm", "CHI": "lake", "GBY": "cold", "MIL": "lake", "NAS": "mild_east",
    "CHA": "mild_east", "TAM": "warm", "NWK": "mild_east", "BAL": "mild_east",
    "RIC": "mild_east", "BUF": "lake", "SFO": "coastal", "SEA": "rainy",
    "SDG": "coastal",
}


def climate_for(abbr):
    return STADIUMS.get(abbr, "mild_east")


def roll_weather(home_abbr, week, playoff=None, neutral=False):
    """Return a weather dict for a game. Week 0 = September opener."""
    kind = "dome" if neutral else climate_for(home_abbr)
    if kind == "dome":
        return {"cond": "Dome", "temp": 72, "wind": 0, "precip": None, "altitude": False,
                "dome": True}
    sep, dec, pchance, snow_ok, wind_mean, alt = CLIMATES[kind]
    wk = week if not playoff else 19 + {"Wild Card": 0, "Divisional": 1,
                                        "Conference": 2}.get(playoff, 3)
    frac = min(1.0, max(0.0, wk / 17.0))
    temp = int(round(random.gauss(sep + (dec - sep) * frac, 7)))
    wind = max(0, int(round(random.gammavariate(2.2, wind_mean / 2.2))))
    precip = None
    if random.random() < pchance:
        precip = "snow" if (snow_ok and temp <= 33) else "rain"
        if precip == "rain" and random.random() < 0.35:
            precip = "heavy rain"
    if precip == "snow" and random.random() < 0.3:
        precip = "heavy snow"
    if precip:
        cond = precip.title()
    elif wind >= 20:
        cond = "Windy"
    elif temp <= 25:
        cond = "Frigid"
    elif temp >= 90:
        cond = "Hot"
    else:
        cond = random.choice(["Clear", "Clear", "Partly cloudy", "Overcast"])
    return {"cond": cond, "temp": temp, "wind": wind, "precip": precip, "altitude": alt,
            "dome": False}


def effects(w):
    """Translate weather into engine modifiers."""
    if not w or w.get("dome"):
        return {"acc": 0.0, "deep_acc": 0.0, "catch": 0.0, "fumble": 1.0, "fg_dist": 0.0,
                "punt": 0.0, "pass_shift": 0.0, "kick_power": 0.0}
    wind = w.get("wind", 0)
    p = w.get("precip")
    temp = w.get("temp", 60)
    acc = deep = catch = fg = punt = shift = 0.0
    fum = 1.0
    if wind > 12:
        deep -= (wind - 12) * 0.55
        acc -= (wind - 12) * 0.18
        fg += (wind - 12) * 0.45
        punt -= (wind - 12) * 0.25
        shift -= max(0.0, wind - 16) * 0.006
    if p == "rain":
        acc -= 1.5; deep -= 1.5; catch -= 2.0; fum *= 1.25; fg += 1.5; shift -= 0.015
    elif p == "heavy rain":
        acc -= 3.5; deep -= 3.5; catch -= 4.0; fum *= 1.45; fg += 3.0; punt -= 2; shift -= 0.04
    elif p == "snow":
        acc -= 2.5; deep -= 3.0; catch -= 3.0; fum *= 1.3; fg += 3.0; punt -= 2; shift -= 0.035
    elif p == "heavy snow":
        acc -= 5.0; deep -= 6.0; catch -= 5.0; fum *= 1.5; fg += 6.0; punt -= 4; shift -= 0.07
    if temp <= 20:
        catch -= 1.5; fum *= 1.1; fg += 2.0; punt -= 1.5
    kick_power = 0.0
    if w.get("altitude"):
        fg -= 3.5
        punt += 2.5
        kick_power = 6.0
    return {"acc": acc, "deep_acc": deep, "catch": catch, "fumble": fum, "fg_dist": fg,
            "punt": punt, "pass_shift": shift, "kick_power": kick_power}


def describe(w):
    if not w:
        return ""
    if w.get("dome"):
        return "Indoors"
    s = f"{w['cond']}, {w['temp']}°F"
    if w.get("wind", 0) >= 8:
        s += f", wind {w['wind']} mph"
    if w.get("altitude"):
        s += ", altitude"
    return s
