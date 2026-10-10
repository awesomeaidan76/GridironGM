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
- deep: go, post, skinny post, corner, seam, wheel, fade, sluggo, out-and-up, post-corner
- medium: dig, deep out, comeback, curl, cross, sail, climb, bench, hook
- short: hitch, slant, quick out, stick, drag, flat, angle, checkdown, spot, whip, choice, option, arrow
- screen: swing, bubble, screen, tunnel, slip
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
  Power Run, Zone Run, Wing-T, Flexbone.
- `pa: true` (optional) makes it a play-action pass; `rpo: true` makes it the pass half of a
  run-pass option; `forms: ["Wing-T"]` (optional) limits it to those formations.

Built-in formations include Gun Doubles/Trips/Bunch/Spread/Empty/Twins/Wing/Quads, Pistol
Doubles/Ace/Wing, Singleback Ace/Wing/Trips/Bunch, I-Form Pro/Heavy, Strong I, Pro Set, Wing-T
and Flexbone.

Runs, defensive calls and special-teams calls are built in (see Tactics → Playbook and the
Glossary). They can be featured or removed in game but not yet defined in JSON.

How plays affect the simulation:
- Receivers whose route matches the call are the quarterback's main reads.
- Blockers help pass protection.
- Each route's depth sets where the ball is caught.
- The live game viewer draws the formation, every route, the defense's shell and the result of each play.
