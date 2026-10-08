"""
playbook.py — formations, routes, plays and defensive coverages.

Everything here is built from standard football vocabulary (formations,
route trees, run schemes and coverage shells that every coach uses), so it
can be extended freely. Coaches' systems weight the concepts they like, and
extra plays can be dropped into the `playbooks/` folder as JSON files (see
docs/PLAYBOOK_FORMAT.md).

Coordinates are in yards from the ball, from the offense's point of view:
x is left (-) / right (+), y is downfield (+) / backfield (-).
Field width is 53.3 yards, so the sidelines are at about x = ±26.6.
"""
import json
import os
import random

# ── Formations ────────────────────────────────────────────────────────────────
# Skill slots: X (split end), Z (flanker), SL / SL2 (slots), TE / TE2, RB, FB.
# Linemen and the QB are added automatically.

OL = {"LT": (-4.4, -0.6), "LG": (-2.2, -0.5), "C": (0.0, -0.4), "RG": (2.2, -0.5), "RT": (4.4, -0.6)}

FORMATIONS = {
    # 11 personnel
    "Gun Doubles":      {"pers": "11", "qb": -5, "slots": {"X": (-22, -0.5), "SL": (-12, -1.2), "Z": (21, -1.2),
                                                           "TE": (6.6, -0.6), "RB": (1.5, -5.2)}},
    "Gun Trips Right":  {"pers": "11", "qb": -5, "slots": {"X": (-22, -0.5), "SL": (11, -1.2), "Z": (21, -1.2),
                                                           "TE": (6.6, -0.6), "RB": (-1.5, -5.2)}},
    "Gun Bunch Right":  {"pers": "11", "qb": -5, "slots": {"X": (-22, -0.5), "TE": (8.5, -0.8), "SL": (10, -2.2),
                                                           "Z": (11.5, -0.8), "RB": (-1.5, -5.2)}},
    "Singleback Trips": {"pers": "11", "qb": -1, "slots": {"X": (-22, -0.5), "SL": (11, -1.2), "Z": (20, -1.2),
                                                           "TE": (6.6, -0.6), "RB": (0, -7)}},
    "Pistol Doubles":   {"pers": "11", "qb": -4, "slots": {"X": (-22, -0.5), "SL": (-11, -1.2), "Z": (21, -1.2),
                                                           "TE": (6.6, -0.6), "RB": (0, -7)}},
    # 12 personnel
    "Singleback Ace":   {"pers": "12", "qb": -1, "slots": {"X": (-21, -0.5), "TE": (-6.6, -0.6), "TE2": (6.6, -0.6),
                                                           "Z": (21, -1.2), "RB": (0, -7)}},
    "Gun Y-Trips":      {"pers": "12", "qb": -5, "slots": {"X": (-22, -0.5), "TE2": (-6.6, -0.6), "TE": (10, -1.2),
                                                           "Z": (20, -1.2), "RB": (1.5, -5.2)}},
    "Singleback Wing":  {"pers": "12", "qb": -1, "slots": {"X": (-21, -0.5), "TE": (6.6, -0.6), "TE2": (8.2, -1.6),
                                                           "Z": (21, -1.2), "RB": (0, -7)}},
    # 21 / 22 personnel
    "I-Form Pro":       {"pers": "21", "qb": -1, "slots": {"X": (-21, -0.5), "TE": (6.6, -0.6), "Z": (20, -1.2),
                                                           "FB": (0, -4.5), "RB": (0, -7)}},
    "Strong I":         {"pers": "21", "qb": -1, "slots": {"X": (-21, -0.5), "TE": (6.6, -0.6), "Z": (20, -1.2),
                                                           "FB": (2.4, -4.5), "RB": (0, -7)}},
    "I-Form Heavy":     {"pers": "22", "qb": -1, "slots": {"X": (-18, -0.5), "TE": (-6.6, -0.6), "TE2": (6.6, -0.6),
                                                           "FB": (0, -4.5), "RB": (0, -7)}},
    # 10 personnel
    "Gun Spread":       {"pers": "10", "qb": -5, "slots": {"X": (-22, -0.5), "SL": (-12, -1.2), "SL2": (12, -1.2),
                                                           "Z": (22, -1.2), "RB": (1.5, -5.2)}},
    "Gun Trips Empty":  {"pers": "10", "qb": -5, "slots": {"X": (-22, -0.5), "RB": (-12, -1.2), "SL": (9, -1.2),
                                                           "SL2": (15, -1.2), "Z": (22, -1.2)}},
    "Gun Twins":        {"pers": "11", "qb": -5, "slots": {"X": (-22, -0.5), "SL": (-15, -1.2), "Z": (21, -1.2),
                                                           "TE": (6.6, -0.6), "RB": (1.5, -5.2)}},
    "Gun Wing":         {"pers": "11", "qb": -5, "slots": {"X": (-22, -0.5), "SL": (-12, -1.2), "Z": (21, -1.2),
                                                           "TE": (8.2, -1.6), "RB": (-1.5, -5.2)}},
    "Singleback Bunch": {"pers": "11", "qb": -1, "slots": {"X": (-21, -0.5), "TE": (8.5, -0.8), "SL": (10, -2.2),
                                                           "Z": (11.5, -0.8), "RB": (0, -7)}},
    "Pistol Ace":       {"pers": "12", "qb": -4, "slots": {"X": (-21, -0.5), "TE": (-6.6, -0.6), "TE2": (6.6, -0.6),
                                                           "Z": (21, -1.2), "RB": (0, -7)}},
    "Pistol Wing":      {"pers": "12", "qb": -4, "slots": {"X": (-21, -0.5), "TE": (6.6, -0.6), "TE2": (8.2, -1.6),
                                                           "Z": (21, -1.2), "RB": (0, -7)}},
    "Pro Set":          {"pers": "21", "qb": -1, "slots": {"X": (-21, -0.5), "TE": (6.6, -0.6), "Z": (20, -1.2),
                                                           "FB": (-2.4, -5), "RB": (2.4, -5)}},
    "Wing-T":           {"pers": "21", "qb": -1, "slots": {"X": (-20, -0.5), "TE": (6.6, -0.6), "Z": (8.4, -1.6),
                                                           "FB": (0, -4.5), "RB": (-2.6, -5)}},
    "Flexbone":         {"pers": "10", "qb": -1, "slots": {"X": (-20, -0.5), "SL": (-6.2, -1.4), "SL2": (6.2, -1.4),
                                                           "Z": (20, -0.5), "RB": (0, -4.5)}},
    "Gun Quads":        {"pers": "10", "qb": -5, "slots": {"X": (-22, -0.5), "SL": (8, -1.2), "SL2": (13, -1.2),
                                                           "Z": (21, -1.2), "RB": (17, -0.5)}},
}

PERSONNEL_SLOTS = {"11": ["X", "Z", "SL", "TE", "RB"], "12": ["X", "Z", "TE", "TE2", "RB"],
                   "21": ["X", "Z", "TE", "FB", "RB"], "22": ["X", "TE", "TE2", "FB", "RB"],
                   "10": ["X", "Z", "SL", "SL2", "RB"]}

# ── Routes ────────────────────────────────────────────────────────────────────
# Waypoints relative to the receiver's alignment. dx > 0 means *toward the
# sideline on his side* ("outside"), dx < 0 toward the middle. Each route has a
# depth class the engine understands and a nominal catch depth.
ROUTES = {
    "go":        {"cls": "deep",   "depth": 24, "path": [(0, 0), (0.5, 10), (0.5, 32)]},
    "post":      {"cls": "deep",   "depth": 20, "path": [(0, 0), (0, 12), (-8, 26)]},
    "corner":    {"cls": "deep",   "depth": 18, "path": [(0, 0), (0, 11), (8, 22)]},
    "seam":      {"cls": "deep",   "depth": 18, "path": [(0, 0), (0, 28)]},
    "wheel":     {"cls": "deep",   "depth": 18, "path": [(0, 0), (5, 2), (8, 7), (8, 26)]},
    "dig":       {"cls": "medium", "depth": 13, "path": [(0, 0), (0, 13), (-13, 13)]},
    "deep out":  {"cls": "medium", "depth": 12, "path": [(0, 0), (0, 12), (7, 12)]},
    "comeback":  {"cls": "medium", "depth": 13, "path": [(0, 0), (0, 16), (3, 13)]},
    "curl":      {"cls": "medium", "depth": 11, "path": [(0, 0), (0, 12), (-1.5, 10)]},
    "cross":     {"cls": "medium", "depth": 14, "path": [(0, 0), (0, 6), (-26, 15)]},
    "sail":      {"cls": "medium", "depth": 13, "path": [(0, 0), (0, 8), (8, 14)]},
    "hitch":     {"cls": "short",  "depth": 6,  "path": [(0, 0), (0, 7), (0, 5.5)]},
    "slant":     {"cls": "short",  "depth": 6,  "path": [(0, 0), (0, 2), (-7, 9)]},
    "quick out": {"cls": "short",  "depth": 5,  "path": [(0, 0), (0, 5), (6, 5)]},
    "stick":     {"cls": "short",  "depth": 6,  "path": [(0, 0), (0, 6), (1, 5)]},
    "drag":      {"cls": "short",  "depth": 4,  "path": [(0, 0), (-1, 2), (-20, 5)]},
    "flat":      {"cls": "short",  "depth": 2,  "path": [(0, 0), (4, 1), (11, 3)]},
    "angle":     {"cls": "short",  "depth": 4,  "path": [(0, 0), (4, 1), (1, 6)]},
    "checkdown": {"cls": "short",  "depth": 3,  "path": [(0, 0), (1, 2), (-2, 4)]},
    "swing":     {"cls": "screen", "depth": -1, "path": [(0, 0), (5, -1.5), (10, 0)]},
    "bubble":    {"cls": "screen", "depth": 0,  "path": [(0, 0), (3, -1.5), (6, -0.5)]},
    "screen":    {"cls": "screen", "depth": -1, "path": [(0, 0), (-3, -2), (-2, -1)]},
    "skinny post": {"cls": "deep", "depth": 18, "path": [(0, 0), (0, 10), (-3, 24)]},
    "fade":      {"cls": "deep",   "depth": 20, "path": [(0, 0), (2, 8), (4, 26)]},
    "sluggo":    {"cls": "deep",   "depth": 22, "path": [(0, 0), (0, 2), (-3, 5), (-2, 8), (0, 30)]},
    "out-and-up": {"cls": "deep",  "depth": 20, "path": [(0, 0), (0, 6), (4, 7), (4, 28)]},
    "post-corner": {"cls": "deep", "depth": 20, "path": [(0, 0), (0, 10), (-3, 14), (5, 23)]},
    "climb":     {"cls": "medium", "depth": 14, "path": [(0, 0), (-3, 8), (-4, 15), (-4, 14)]},
    "bench":     {"cls": "medium", "depth": 12, "path": [(0, 0), (0, 9), (8, 14)]},
    "hook":      {"cls": "medium", "depth": 10, "path": [(0, 0), (0, 11), (-1, 9)]},
    "spot":      {"cls": "short",  "depth": 5,  "path": [(0, 0), (-1, 4), (-3, 5.5)]},
    "whip":      {"cls": "short",  "depth": 5,  "path": [(0, 0), (-3, 4), (3, 5)]},
    "choice":    {"cls": "short",  "depth": 7,  "path": [(0, 0), (0, 7), (-1, 7)]},
    "option":    {"cls": "short",  "depth": 6,  "path": [(0, 0), (0, 5), (2, 6)]},
    "arrow":     {"cls": "short",  "depth": 3,  "path": [(0, 0), (6, 3), (11, 4)]},
    "tunnel":    {"cls": "screen", "depth": -1, "path": [(0, 0), (-3, -1), (-6, 1)]},
    "slip":      {"cls": "screen", "depth": -1, "path": [(0, 0), (1, 1), (-2, -1), (-4, 0)]},
    "block":     {"cls": "block",  "depth": 0,  "path": []},
}

# ── Pass concepts ─────────────────────────────────────────────────────────────
# routes by slot; any slot not listed stays in to block. "cls" is the depth the
# concept is built to attack (matches the engine's call); tags help filtering.

PASS_PLAYS = [
    {"name": "Four Verticals", "cls": "deep", "routes": {"X": "go", "Z": "go", "SL": "seam", "SL2": "seam",
                                                         "TE": "seam", "TE2": "seam", "RB": "checkdown"}},
    {"name": "Post-Dig", "cls": "deep", "routes": {"X": "dig", "Z": "post", "SL": "go", "TE": "drag",
                                                   "TE2": "flat", "RB": "checkdown", "FB": "flat"}},
    {"name": "Go-Corner", "cls": "deep", "routes": {"X": "go", "Z": "corner", "SL": "corner", "TE": "seam",
                                                    "TE2": "flat", "RB": "flat"}},
    {"name": "Dagger", "cls": "medium", "routes": {"X": "go", "SL": "seam", "Z": "dig", "TE": "dig",
                                                   "TE2": "flat", "RB": "checkdown", "SL2": "dig"}},
    {"name": "Smash", "cls": "medium", "routes": {"X": "hitch", "SL": "corner", "Z": "hitch", "TE": "corner",
                                                  "SL2": "corner", "RB": "flat", "TE2": "flat"}},
    {"name": "Flood", "cls": "medium", "routes": {"Z": "go", "SL": "deep out", "TE": "flat", "X": "post",
                                                  "SL2": "deep out", "TE2": "deep out", "RB": "checkdown"}},
    {"name": "Levels", "cls": "medium", "routes": {"X": "go", "SL": "dig", "TE": "drag", "Z": "deep out",
                                                   "SL2": "dig", "TE2": "drag", "RB": "angle"}},
    {"name": "Curl-Flat", "cls": "medium", "routes": {"X": "curl", "Z": "curl", "SL": "flat", "TE": "flat",
                                                      "SL2": "curl", "TE2": "curl", "RB": "checkdown"}},
    {"name": "Y-Cross", "cls": "medium", "routes": {"X": "go", "Z": "post", "TE": "cross", "SL": "sail",
                                                    "SL2": "drag", "TE2": "flat", "RB": "checkdown"}},
    {"name": "Comeback", "cls": "medium", "routes": {"X": "comeback", "Z": "comeback", "SL": "seam",
                                                     "TE": "drag", "SL2": "seam", "RB": "flat"}},
    {"name": "Mesh", "cls": "short", "routes": {"SL": "drag", "TE": "drag", "X": "corner", "Z": "sail",
                                                "SL2": "drag", "TE2": "flat", "RB": "angle"}},
    {"name": "Stick", "cls": "short", "routes": {"TE": "stick", "SL": "flat", "Z": "go", "X": "slant",
                                                 "SL2": "stick", "TE2": "flat", "RB": "swing"}},
    {"name": "Slant-Flat", "cls": "short", "routes": {"X": "slant", "Z": "slant", "SL": "flat", "TE": "seam",
                                                      "SL2": "flat", "TE2": "flat", "RB": "checkdown", "FB": "flat"}},
    {"name": "All Hitch", "cls": "short", "routes": {"X": "hitch", "Z": "hitch", "SL": "hitch", "SL2": "hitch",
                                                     "TE": "stick", "TE2": "hitch", "RB": "checkdown"}},
    {"name": "Shallow Cross", "cls": "short", "routes": {"SL": "drag", "TE": "dig", "X": "go", "Z": "curl",
                                                         "SL2": "drag", "TE2": "flat", "RB": "checkdown"}},
    {"name": "Quick Outs", "cls": "short", "routes": {"X": "quick out", "Z": "quick out", "SL": "slant",
                                                      "SL2": "slant", "TE": "stick", "RB": "flat"}},
    {"name": "RB Screen", "cls": "screen", "routes": {"RB": "screen", "X": "go", "Z": "go", "SL": "drag",
                                                      "TE": "block"}},
    {"name": "Bubble Screen", "cls": "screen", "routes": {"SL": "bubble", "SL2": "bubble", "X": "block",
                                                          "Z": "block", "TE": "block", "RB": "block"}},
    {"name": "Swing", "cls": "screen", "routes": {"RB": "swing", "X": "go", "Z": "slant", "SL": "hitch",
                                                  "TE": "drag", "FB": "flat"}},
    # Play-action
    {"name": "PA Boot", "cls": "medium", "pa": True, "routes": {"X": "dig", "Z": "go", "TE": "flat",
                                                                 "FB": "flat", "TE2": "cross", "SL": "corner"}},
    {"name": "PA Shot", "cls": "deep", "pa": True, "routes": {"X": "post", "Z": "go", "TE": "corner",
                                                               "SL": "go", "TE2": "block"}},
    {"name": "PA Crossers", "cls": "medium", "pa": True, "routes": {"X": "cross", "Z": "dig", "TE": "drag",
                                                                     "SL": "go", "TE2": "flat", "FB": "flat"}},
    # ── Air Raid ──
    {"name": "Snag", "cls": "short", "routes": {"SL": "spot", "Z": "corner", "RB": "arrow", "X": "slant",
                                                "TE": "spot", "SL2": "spot", "TE2": "arrow"}},
    {"name": "Y-Option", "cls": "short", "routes": {"TE": "option", "X": "go", "Z": "go", "SL": "hitch",
                                                    "SL2": "option", "RB": "swing"}},
    {"name": "Shallow", "cls": "short", "routes": {"SL": "drag", "TE": "dig", "X": "skinny post", "Z": "curl",
                                                   "SL2": "dig", "TE2": "drag", "RB": "checkdown"}},
    # ── West Coast ──
    {"name": "Spacing", "cls": "short", "routes": {"X": "hitch", "SL": "hitch", "TE": "stick", "Z": "curl",
                                                   "SL2": "hitch", "TE2": "flat", "RB": "flat", "FB": "flat"}},
    {"name": "Drive", "cls": "short", "routes": {"SL": "drag", "TE": "dig", "X": "go", "Z": "curl",
                                                 "SL2": "drag", "TE2": "flat", "RB": "checkdown"}},
    {"name": "Hank", "cls": "medium", "routes": {"X": "curl", "Z": "curl", "SL": "hook", "TE": "hook",
                                                 "SL2": "hook", "TE2": "flat", "RB": "swing"}},
    {"name": "Texas", "cls": "short", "routes": {"RB": "angle", "TE": "seam", "X": "curl", "Z": "curl",
                                                 "SL": "seam", "TE2": "flat", "FB": "flat"}},
    {"name": "Sluggo", "cls": "deep", "routes": {"X": "sluggo", "Z": "go", "SL": "curl", "TE": "drag",
                                                 "SL2": "curl", "RB": "checkdown"}},
    # ── Run and Shoot ──
    {"name": "Choice", "cls": "short", "forms": ["Gun Spread", "Gun Trips Empty"],
     "routes": {"SL": "choice", "SL2": "choice", "X": "go", "Z": "go", "RB": "checkdown", "TE": "choice"}},
    {"name": "Go", "cls": "deep", "forms": ["Gun Spread", "Gun Quads"],
     "routes": {"X": "go", "Z": "go", "SL": "bench", "SL2": "hitch", "RB": "checkdown", "TE": "bench"}},
    {"name": "Switch", "cls": "deep", "forms": ["Gun Spread", "Gun Twins"],
     "routes": {"X": "out-and-up", "SL": "fade", "Z": "post-corner", "SL2": "seam", "TE": "seam",
                "RB": "checkdown"}},
    # ── Pro Style / Coryell ──
    {"name": "Yankee", "cls": "deep", "pa": True, "routes": {"X": "post", "Z": "cross", "TE": "block",
                                                             "RB": "block", "SL": "go", "TE2": "flat", "FB": "flat"}},
    {"name": "Mills", "cls": "deep", "routes": {"Z": "post", "SL": "dig", "X": "go", "TE": "dig",
                                                "SL2": "dig", "RB": "checkdown"}},
    {"name": "Hi-Lo", "cls": "medium", "routes": {"SL": "drag", "TE": "dig", "X": "go", "Z": "curl",
                                                  "SL2": "dig", "RB": "flat"}},
    # ── Spread / RPO ──
    {"name": "Glance RPO", "cls": "short", "rpo": True, "routes": {"X": "skinny post", "Z": "hitch",
                                                                   "SL": "seam", "TE": "block", "RB": "block"}},
    {"name": "Bubble RPO", "cls": "screen", "rpo": True, "routes": {"SL": "bubble", "SL2": "bubble",
                                                                    "X": "block", "Z": "block", "TE": "block",
                                                                    "RB": "block"}},
    {"name": "Stick RPO", "cls": "short", "rpo": True, "routes": {"TE": "stick", "SL": "stick", "SL2": "stick",
                                                                  "X": "go", "Z": "slant", "RB": "block"}},
    {"name": "Slant RPO", "cls": "short", "rpo": True, "routes": {"X": "slant", "Z": "slant", "SL": "slant",
                                                                  "TE": "block", "RB": "block"}},
    {"name": "Climb", "cls": "medium", "routes": {"Z": "go", "SL": "quick out", "X": "cross", "SL2": "climb",
                                                  "TE": "climb", "RB": "checkdown"}},
    {"name": "Spot", "cls": "short", "routes": {"X": "go", "SL": "spot", "TE": "arrow", "Z": "corner",
                                                "SL2": "spot", "RB": "flat"}},
    # ── Wing-T / Flexbone ──
    {"name": "Waggle", "cls": "medium", "pa": True, "forms": ["Wing-T"],
     "routes": {"X": "post", "TE": "corner", "Z": "flat", "FB": "flat", "RB": "block"}},
    {"name": "Keep Pass", "cls": "short", "pa": True, "forms": ["Wing-T"],
     "routes": {"TE": "drag", "Z": "corner", "X": "go", "FB": "flat", "RB": "block"}},
    {"name": "Option Pass", "cls": "deep", "pa": True, "forms": ["Flexbone"],
     "routes": {"SL": "wheel", "SL2": "seam", "X": "post", "Z": "go", "RB": "block"}},
    {"name": "Flexbone Seams", "cls": "medium", "pa": True, "forms": ["Flexbone"],
     "routes": {"SL": "seam", "SL2": "seam", "X": "curl", "Z": "curl", "RB": "block"}},
    # ── Screens ──
    {"name": "Tunnel Screen", "cls": "screen", "routes": {"Z": "tunnel", "X": "block", "SL": "block",
                                                          "TE": "block", "RB": "block"}},
    {"name": "TE Slip Screen", "cls": "screen", "routes": {"TE": "slip", "X": "go", "Z": "go", "SL": "drag",
                                                           "RB": "flat"}},
    # Specials
    {"name": "Flea Flicker", "cls": "deep", "pa": True, "trick": True,
     "routes": {"X": "post", "Z": "go", "TE": "block", "SL": "go", "TE2": "block"}},
    {"name": "Hail Mary", "cls": "hail", "routes": {"X": "go", "Z": "go", "SL": "go", "SL2": "go",
                                                    "TE": "go", "TE2": "go", "RB": "checkdown"}},
]

# ── Run plays ─────────────────────────────────────────────────────────────────
# path: the ball carrier's track (relative to his alignment, x toward play side)
RUN_PATHS = {
    "inside zone":  [(0, 0), (1.5, 2), (2.5, 6), (2, 12)],
    "outside zone": [(0, 0), (5, 2.5), (9, 6), (11, 12)],
    "power":        [(0, 0), (2, 3), (3, 7), (3.5, 12)],
    "counter":      [(0, 0), (-1.5, 1), (2.5, 4), (4, 11)],
    "draw":         [(0, 0), (0, 1.5), (0.5, 6), (0, 12)],
    "toss":         [(0, 0), (6, 1), (11, 4), (14, 12)],
    "jet sweep":    [(0, 0), (-10, -2), (-18, 0), (-20, 8)],
    "reverse":      [(0, 0), (-8, -3), (-18, -1), (-22, 8)],
    "sneak":        [(0, 0), (0, 1.5), (0, 2.5)],
    "trap":         [(0, 0), (0.5, 2), (0.5, 6), (0, 12)],
    "lead":         [(0, 0), (1.5, 3), (2, 7), (2, 12)],
    "buck sweep":   [(0, 0), (-2, -1), (6, 1), (12, 5), (14, 12)],
    "pitch":        [(0, 0), (8, 0), (14, 4), (16, 12)],
    "dive":         [(0, 0), (1, 2), (1.5, 6), (1, 12)],
    "qb run":       [(0, 0), (3, 1), (5, 5), (6, 12)],
    "zone read":    [(0, 0), (1.5, 2), (2.5, 6), (2, 12)],
    "keep":         [(0, 0), (-3, 0.5), (-6, 4), (-7, 12)],
    "inverted veer": [(0, 0), (7, 0), (12, 4), (14, 12)],
    "veer keep":    [(0, 0), (1, 1.5), (1.5, 6), (1, 12)],
    "midline":      [(0, 0), (0.3, 2), (0.5, 6), (0, 12)],
    "speed option": [(0, 0), (4, 1), (7, 4), (8, 12)],
    "scramble":     [(0, 0), (-3, -2), (6, 2), (8, 10)],
}

# Run concepts the engine can call (key = engine name)
RUN_CONCEPT_INFO = {
    "inside zone": "Linemen step playside together; the back reads the first down lineman and cuts",
    "outside zone": "Stretch play: the line reaches toward the sideline and the back bends it back or bounces",
    "power": "Gap scheme with the backside guard pulling to lead through the hole",
    "counter": "Misdirection: the back steps away, then follows two pullers back the other way",
    "draw": "Linemen show pass, then the back takes a delayed hand-off; good against pass rushes",
    "toss": "Quick pitch to the back running for the edge",
    "jet sweep": "A receiver in motion takes the hand-off at full speed to the perimeter",
    "trap": "A defensive lineman is let through and kicked out by a pulling guard",
    "lead": "Iso / lead: the fullback leads through the hole and takes on the linebacker",
    "buck sweep": "Wing-T staple: both guards pull and the tailback follows them around the end",
    "zone read": "Inside zone where the QB reads the backside end: hand off, or keep it himself",
    "inverted veer": "The back runs wide while the QB reads the end and keeps it inside behind a pulling guard",
    "triple option": "Flexbone option: give to the dive back, keep, or pitch to the trailing back",
    "midline": "Option off the defensive tackle: give inside to the fullback or the QB keeps up the middle",
    "speed option": "QB attacks the edge and pitches to the back when the end commits",
}

# Which formations each personnel group uses for runs and passes
RUN_FORMS = {"11": ["Gun Doubles", "Singleback Trips", "Pistol Doubles", "Gun Trips Right", "Gun Twins",
                    "Gun Wing"],
             "12": ["Singleback Ace", "Singleback Wing", "Pistol Ace", "Pistol Wing"],
             "21": ["I-Form Pro", "Strong I", "Pro Set", "Wing-T"],
             "22": ["I-Form Heavy"], "10": ["Gun Spread", "Flexbone"]}
PASS_FORMS = {"11": ["Gun Doubles", "Gun Trips Right", "Gun Bunch Right", "Singleback Trips", "Pistol Doubles",
                     "Gun Twins", "Gun Wing", "Singleback Bunch"],
              "12": ["Singleback Ace", "Gun Y-Trips", "Singleback Wing", "Pistol Ace", "Pistol Wing"],
              "21": ["I-Form Pro", "Strong I", "Pro Set", "Wing-T"],
              "22": ["I-Form Heavy"], "10": ["Gun Spread", "Gun Trips Empty", "Gun Quads", "Flexbone"]}

# Systems: how much each scheme likes each pass concept (default 1.0)
SCHEME_CONCEPTS = {
    "Air Raid":      {"Mesh": 3.0, "Four Verticals": 2.5, "Y-Cross": 2.2, "Stick": 1.8, "Shallow Cross": 1.6},
    "West Coast":    {"Slant-Flat": 2.4, "Curl-Flat": 2.0, "Shallow Cross": 2.0, "Stick": 1.6, "Swing": 1.8},
    "Pro Style":     {"Dagger": 1.8, "Smash": 1.8, "PA Boot": 1.6, "Levels": 1.4},
    "Air Coryell":   {"Post-Dig": 2.6, "Go-Corner": 2.2, "Comeback": 2.2, "Dagger": 1.6},
    "Run and Shoot": {"Four Verticals": 2.0, "Flood": 1.8, "Quick Outs": 1.8, "All Hitch": 1.6},
    "Spread Option": {"Bubble Screen": 2.4, "Slant-Flat": 1.6, "Stick": 1.5, "Four Verticals": 1.3},
    "Power Run":     {"PA Boot": 2.4, "PA Shot": 2.0, "Curl-Flat": 1.5, "Flood": 1.4},
    "Zone Run":      {"PA Boot": 2.6, "PA Crossers": 2.4, "Shallow Cross": 1.5, "Dagger": 1.3, "Yankee": 1.6},
    "Pistol":        {"PA Boot": 2.0, "Glance RPO": 2.2, "Stick RPO": 1.8, "Spot": 1.6, "Climb": 1.6,
                      "Sluggo": 1.4},
    "Wing-T":        {"Waggle": 6.0, "Keep Pass": 4.0, "PA Boot": 2.0, "Yankee": 1.5},
    "Flexbone":      {"Option Pass": 6.0, "Flexbone Seams": 4.0, "PA Shot": 2.0},
}
SCHEME_CONCEPTS["Air Raid"].update({"Snag": 1.8, "Y-Option": 1.6, "Shallow": 2.6})
SCHEME_CONCEPTS["West Coast"].update({"Spacing": 2.2, "Drive": 2.2, "Hank": 1.8, "Texas": 1.8})
SCHEME_CONCEPTS["Run and Shoot"].update({"Choice": 3.0, "Go": 2.4, "Switch": 1.8})
SCHEME_CONCEPTS["Pro Style"].update({"Yankee": 1.8, "Mills": 1.6, "Hi-Lo": 1.6, "Drive": 1.3})
SCHEME_CONCEPTS["Air Coryell"].update({"Mills": 2.4, "Yankee": 2.0, "Sluggo": 1.6})
SCHEME_CONCEPTS["Spread Option"].update({"Glance RPO": 2.4, "Bubble RPO": 2.4, "Stick RPO": 2.0,
                                         "Slant RPO": 1.8, "Climb": 1.8, "Spot": 1.6, "Tunnel Screen": 1.6})
SCHEME_CONCEPTS["Power Run"].update({"Yankee": 2.0})

# Formation preferences by system (multiplies the base weight)
SCHEME_FORMS = {
    "Air Raid": {"Gun Doubles": 2.0, "Gun Trips Right": 2.0, "Gun Spread": 2.0, "Gun Twins": 1.5},
    "Run and Shoot": {"Gun Spread": 4.0, "Gun Twins": 2.0, "Gun Quads": 1.5},
    "Spread Option": {"Gun Doubles": 1.5, "Gun Trips Right": 1.5, "Gun Spread": 1.5, "Pistol Doubles": 1.5},
    "Pistol": {"Pistol Doubles": 4.0, "Pistol Ace": 4.0, "Pistol Wing": 3.0},
    "Power Run": {"I-Form Pro": 2.0, "Strong I": 2.0, "I-Form Heavy": 2.0, "Pro Set": 1.5},
    "Pro Style": {"I-Form Pro": 1.5, "Singleback Ace": 1.5, "Pro Set": 1.5, "Singleback Trips": 1.3},
    "Zone Run": {"Singleback Ace": 2.0, "Singleback Wing": 2.0, "Gun Wing": 1.5, "Pistol Wing": 1.5},
    "West Coast": {"Singleback Trips": 1.5, "Gun Doubles": 1.3, "Pro Set": 1.5, "Singleback Bunch": 1.5},
    "Air Coryell": {"Singleback Ace": 1.5, "I-Form Pro": 1.5, "Gun Doubles": 1.3},
    "Wing-T": {"Wing-T": 12.0},
    "Flexbone": {"Flexbone": 12.0},
}

# Run game by system: extra weight added to the engine's base run-concept mix
SCHEME_RUNS = {
    "Power Run": {"power": 0.9, "lead": 0.6, "counter": 0.3, "trap": 0.2},
    "Zone Run": {"inside zone": 0.6, "outside zone": 0.9},
    "Spread Option": {"zone read": 1.2, "inverted veer": 0.6, "speed option": 0.3, "draw": 0.2},
    "Pistol": {"zone read": 0.9, "inverted veer": 0.4, "power": 0.3, "counter": 0.2},
    "Wing-T": {"buck sweep": 1.4, "trap": 0.9, "counter": 0.7, "inside zone": -0.4, "lead": 0.3},
    "Flexbone": {"triple option": 2.4, "midline": 0.9, "toss": 0.5, "trap": 0.4, "inside zone": -0.6,
                 "outside zone": -0.4},
    "Air Raid": {"draw": 0.4, "zone read": 0.2},
    "Run and Shoot": {"draw": 0.5, "trap": 0.2},
    "Pro Style": {"lead": 0.3, "power": 0.2},
    "West Coast": {"outside zone": 0.2, "trap": 0.2},
    "Air Coryell": {"power": 0.2, "lead": 0.2},
}

# ── Defense ───────────────────────────────────────────────────────────────────
from defense import COVERAGES, FRONTS  # noqa: E402  (the full defensive library lives there)


def pick_coverage(zone, two_high, blitz, rng=random):
    if zone:
        if two_high:
            return rng.choices(["Cover 2", "Cover 4", "Cover 6", "Tampa 2"], weights=[3, 4, 2, 1.5])[0]
        return "Cover 3"
    if blitz and not two_high and rng.random() < 0.35:
        return "Cover 0"
    return "2-Man" if two_high else "Cover 1"


def defense_alignment(front, n_lb, n_cb, n_s, coverage):
    """Pre-snap spots for the defense: [(role, x, y)] with y > 0 = defensive side."""
    out = []
    three = front == "3-4" or FRONTS.get(front, {}).get("three", False)
    dl = {"Under": [(-6.5, 1), (-1, 1), (2.5, 1), (5.5, 1)],
          "Wide 9": [(-9, 1.2), (-2, 1), (2, 1), (9, 1.2)],
          "Bear": [(-5, 1), (-2.5, 1), (0, 1), (2.5, 1)],
          "Goal Line": [(-4.5, 1), (-1.5, 1), (1.5, 1), (4.5, 1)],
          "Tite": [(-3.2, 1), (0, 1), (3.2, 1)]}.get(front)
    if dl is None:
        dl = [(-4.5, 1), (0, 1), (4.5, 1)] if three else [(-5.5, 1), (-2, 1), (2, 1), (5.5, 1)]
    for x, y in dl:
        out.append(("DL", x, y))
    if three:
        out += [("EDGE", -7.5, 1.2), ("EDGE", 7.5, 1.2)]
        n_lb = max(0, n_lb - 2)
    lb_x = {1: [0], 2: [-3, 3], 3: [-4.5, 0, 4.5], 4: [-6, -2, 2, 6]}.get(n_lb, [])
    for x in lb_x:
        out.append(("LB", x, 5))
    cb_x = [-21, 21, 11, -11][:n_cb]
    press = COVERAGES.get(coverage, (False,))[0]
    for x in cb_x:
        out.append(("CB", x, 1.5 if press else 6.5))
    deep = COVERAGES.get(coverage, (False, 2, ""))[1]
    s_spots = {0: [(-8, 7), (8, 7)], 1: [(0, 13), (6, 7)], 2: [(-10, 13), (10, 13)]}[deep]
    for i in range(n_s):
        x, y = s_spots[i] if i < len(s_spots) else (0, 9)
        out.append(("S", x, y))
    return out


# ── Library & selection ───────────────────────────────────────────────────────

_EXTRA_LOADED = False
USER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "playbooks")


def load_user_plays():
    """Merge any JSON playbooks found in the playbooks/ folder. Bad files are skipped."""
    global _EXTRA_LOADED
    if _EXTRA_LOADED:
        return []
    _EXTRA_LOADED = True
    loaded = []
    if not os.path.isdir(USER_DIR):
        return loaded
    for fn in sorted(os.listdir(USER_DIR)):
        if not fn.lower().endswith(".json"):
            continue
        try:
            with open(os.path.join(USER_DIR, fn), "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            continue
        for name, form in (data.get("formations") or {}).items():
            if isinstance(form, dict) and form.get("pers") in PERSONNEL_SLOTS and "slots" in form:
                form["slots"] = {k: tuple(v) for k, v in form["slots"].items()}
                FORMATIONS[name] = form
                for table in (RUN_FORMS, PASS_FORMS):
                    table.setdefault(form["pers"], []).append(name)
        for name, r in (data.get("routes") or {}).items():
            if isinstance(r, dict) and r.get("cls") in ("deep", "medium", "short", "screen", "block"):
                r["path"] = [tuple(p) for p in r.get("path", [])]
                ROUTES[name] = r
        for play in data.get("plays") or []:
            if not isinstance(play, dict) or "name" not in play or "routes" not in play:
                continue
            if play.get("cls") not in ("deep", "medium", "short", "screen"):
                continue
            if all(rt in ROUTES for rt in play["routes"].values()):
                PASS_PLAYS.append(play)
                for scheme, w in (play.get("schemes") or {}).items():
                    SCHEME_CONCEPTS.setdefault(scheme, {})[play["name"]] = float(w)
                loaded.append(play["name"])
    return loaded


def choose_formation(pers, run, gun_bias=0.5, rng=random, scheme=None):
    forms = (RUN_FORMS if run else PASS_FORMS).get(pers) or ["Gun Doubles"]
    prefs = SCHEME_FORMS.get(scheme, {})
    weights = []
    for f in forms:
        gun = FORMATIONS[f]["qb"] <= -4
        w = 1.0 + (gun_bias if gun else (1 - gun_bias)) * 1.5
        if f in ("Wing-T", "Flexbone") and f not in prefs:
            w *= 0.05                       # only option/Wing-T teams line up like this
        weights.append(w * prefs.get(f, 1.0))
    return rng.choices(forms, weights=weights)[0]


def choose_pass_play(scheme, cls, pa=False, trick=False, rng=random, prefs=None, rpo=False, form=None):
    if trick:
        return next(p for p in PASS_PLAYS if p.get("trick"))
    if cls == "hail":
        return next(p for p in PASS_PLAYS if p["cls"] == "hail")
    likes = SCHEME_CONCEPTS.get(scheme, {})
    cands = [p for p in PASS_PLAYS if p["cls"] == cls and not p.get("trick")
             and bool(p.get("pa")) == bool(pa) and bool(p.get("rpo")) == bool(rpo)
             and (not p.get("forms") or form is None or form in p["forms"])]
    if rpo and not cands:
        cands = [p for p in PASS_PLAYS if p.get("rpo")]
    if not cands:
        cands = [p for p in PASS_PLAYS if p["cls"] == cls and not p.get("trick")] or PASS_PLAYS[:1]
    prefs = prefs or {}
    weights = [likes.get(p["name"], 1.0) * prefs.get(p["name"], 1.0) for p in cands]
    if sum(weights) <= 0:
        weights = [likes.get(p["name"], 1.0) for p in cands]
    return rng.choices(cands, weights=weights)[0]


def side_of(x):
    return 1 if x >= 0 else -1


def route_points(slot_xy, route_name, flip=1):
    """Absolute field points (x, y) for a route run from an alignment."""
    r = ROUTES.get(route_name)
    if not r or not r["path"]:
        return []
    x0, y0 = slot_xy
    s = side_of(x0) * flip
    return [(x0 + dx * s, y0 + dy) for dx, dy in r["path"]]
