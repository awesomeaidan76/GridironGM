# Custom playbooks

The game ships with an original library of formations, routes, pass concepts,
run schemes and coverages (`playbook.py`). You can add your own plays without
touching any code: put a `.json` file in the `playbooks` folder next to
`main.py`. Every file is loaded when the game starts. A file with a mistake is
skipped rather than crashing the game.

See `playbooks/example_custom_plays.json` for a working example.

## Coordinates

Positions and route points are in **yards from the ball**, seen from the
offense:

- `x` runs left (negative) to right (positive). The sidelines are at about ±26.6, and wide receivers usually line up between ±19 and ±23.
- `y` runs downfield (positive) to the backfield (negative). The line of scrimmage is 0, a QB in the shotgun is at -5, under center he is at -1, and a tailback in the I-form is at -7.

## Formations

```json
"formations": {
  "Gun Twins Left": {"pers": "11", "qb": -5,
                     "slots": {"X": [-21, -0.5], "SL": [-14, -1.2], "Z": [21, -1.2],
                               "TE": [6.6, -0.6], "RB": [1.5, -5.2]}}
}
```

`pers` is the personnel group. It decides which slots exist:

| pers | slots |
|---|---|
| 11 | X, Z, SL, TE, RB |
| 12 | X, Z, TE, TE2, RB |
| 21 | X, Z, TE, FB, RB |
| 22 | X, TE, TE2, FB, RB |
| 10 | X, Z, SL, SL2, RB |
| 13 | X, TE, TE2, TE3, RB |
| 20 | X, Z, SL, FB, RB |
| 23 | TE, TE2, TE3, FB, RB |

A formation may also limit the pre-snap motion it uses with `"motion": ["jet", "orbit"]` (any of
`jet`, `orbit`, `across`, `shift`; an empty list means no motion from it).

The offensive line is added automatically. X is the split end, Z the
flanker, SL/SL2 the slot receivers, and TE/TE2/TE3 the tight ends. In 20
personnel the FB spot is a second running back. A pass play with no route for
TE3 gives him the SL route (or Z's); a slot with no route at all blocks.

## Routes

A route is a list of points **relative to the receiver's spot**.

- `dx` is positive *toward his own sideline* and negative toward the middle, so the same route works from either side of the field.
- `cls` must be one of `deep`, `medium`, `short`, `screen` or `block`.
- `depth` is the usual catch depth in yards.

```json
"routes": {"whip out": {"cls": "short", "depth": 5, "path": [[0,0], [-3,4], [4,5]]}}
```

Built-in routes:
- deep: go, post, skinny post, corner, seam, wheel, fade, sluggo, out-and-up, post-corner, leak
- medium: dig, deep out, comeback, curl, cross, sail, climb, bench, hook, banana
- short: hitch, slant, quick out, stick, drag, flat, angle, checkdown, spot, whip, choice, option, arrow, pop
- screen: swing, bubble, screen, tunnel, slip, jailbreak
- block

A custom route with the same name as a built-in one replaces it.

## Pass plays

```json
{"name": "Twins Whip", "cls": "short",
 "routes": {"X": "go", "SL": "whip", "Z": "slant", "TE": "stick", "RB": "flat"},
 "schemes": {"West Coast": 1.5}}
```

- `cls` is the depth the play attacks. The match engine calls plays of the depth that suits the situation.
- Slots without a route stay in to block. Backs with a blocking assignment sometimes check-release
  into the flat when no one blitzes.
- `schemes` (optional) makes coaches of those systems call the play more often; 1.0 is normal.
- Scheme names: Air Raid, West Coast, Pro Style, Air Coryell, Run and Shoot, Spread Option, Pistol,
  Power Run, Zone Run, Wide Zone, Wing-T, Flexbone.
- `pa: true` (optional) makes it a play-action pass; `rpo: true` makes it the pass half of a
  run-pass option; `forms: ["Wing-T"]` (optional) limits it to those formations.
- `motion: {"slot": "SL", "kind": "jet"}` (optional) puts that player in motion every time the play
  is called (when the slot is on the field). Otherwise the coach's motion tendency and system decide.

## Pre-snap motion

| kind | what it is |
|---|---|
| jet | a receiver sprints across just before the snap: sets up the jet sweep and holds the backside on runs |
| orbit | a loop behind the quarterback: screens and misdirection |
| across | a tight end or receiver walks to the other side: moves the strength, adds a blocker on runs |
| shift | two or more players reset: catches slow-reading linebackers |

Every kind helps the quarterback read the coverage (less against disguised coverages) and gets the
man in motion a free release against man coverage.

## Coverages

```json
"coverages": {
  "Cover 3 Cloud": {"man": false, "deep": 1, "disguise": 0.3, "weight": 1.0,
                    "desc": "Cover 3 with the corner squatting in the flat to the boundary",
                    "edges": {"flat": -3, "quick out": -2, "corner": 2, "seam": 2},
                    "schemes": {"Cover 3": 1.6}}
}
```

- `man` and `deep` (0-3 safeties deep) put the coverage in its family: it is called alongside the
  built-in coverages of the same kind (man or zone, single-high or two-high).
- `edges` are openness changes for routes against it (about ±6 at most; 9 is one standard deviation).
- `disguise` (0-1) is how much it changes after the snap: it clouds the quarterback's read and what
  motion tells him.
- `weight` is how often it is picked within its family (1.0 = like a built-in call); `schemes` makes
  defensive systems of those names call it more (4-3 Over, 3-4 Two Gap, Cover 3, Tampa 2, Press Man,
  Two-High Match, Zone Blitz, 46 Blitz, Three-High).
- Built-in coverages can't be replaced.

Built-in formations include Gun Doubles/Trips/Bunch/Spread/Empty/Twins/Wing/Quads/Y-Trips/Split
Backs/Trey, Pistol Doubles/Ace/Wing/Pony, Singleback Ace/Wing/Trips/Bunch/Jumbo, I-Form Pro/Heavy,
Strong I, Pro Set, Goal Line, Wing-T and Flexbone.

Runs, fronts, pressures and special-teams calls are built in (see Tactics → Playbook and the
Glossary). They can be featured or removed in game but not yet defined in JSON.

How plays affect the simulation:
- Receivers whose route matches the call are the quarterback's main reads.
- Blockers help pass protection.
- Each route's depth sets where the ball is caught.
- The live game viewer draws the formation, every route, the defense's shell and the result of each play.
