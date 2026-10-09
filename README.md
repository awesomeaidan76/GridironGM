# Gridiron GM

A Football Manager–style American football general manager game: run a franchise, scout and
draft, negotiate contracts, set depth charts, tactics and weekly game plans, and watch a
play-by-play simulation built to behave like real NFL football — for one season or a hundred.

## How to play (Windows)
1. Install Python 3 from python.org (tick "Add python.exe to PATH").
2. Download this repository (Code → Download ZIP) and unzip it into a new folder.
   To keep your careers, copy the `saves` folder from your previous version into it.
3. Double-click `Play.bat`. The first launch installs PyQt6 (about a minute).

On other systems: `pip install PyQt6` then `python main.py`.

## Controls
- Continue = Ctrl+Space, Save = Ctrl+S. The Sim menu jumps further ahead.
- Game menu: Save As, Load, Export League to JSON, Settings.

## Latest changes (version 6)
- **Line play.** Every pass rusher is matched against the blocker assigned to him (double teams,
  chips, blitz pickups); the blocker he beats is charged with the pressure or sack. Run plays pair
  blockers and defenders at the point of attack. New stats: pressures/sacks allowed, pass-rush win
  rate, double-team rate, run-block win rate, pancakes, yards before/after contact.
- **Game grades (0-100)** for every player every game, with season grades. They drive the All-Pro
  team and awards (linemen are finally judged on how they played).
- **Situational football.** 4th-down and 2-point calls based on win probability and each coach's
  aggressiveness (which drifts league-wide with results), two- and four-minute offense, smarter
  timeouts, spikes, hurried field goals, icing the kicker, onside timing, last-play laterals, and
  sloppy clock management from poor game managers.
- **Offense.** Each coordinator has his own situational habits (early downs, short yardage, red zone,
  shot plays, 3rd-and-long screens and draws), shown on the Game Plan scouting report. Systems now
  look clearly different (Air Raid ~70% passing from the shotgun, Flexbone ~28%). Quarterbacks work
  through progressions, spot blitzes, check down or force throws depending on who they are; new
  QB Decisions stats (time to throw, checkdown %, tight-window %, throwaways).

Version 5: fatigue and rotation, snap counts, defensive game plans, per-league settings.

## Folders
- `saves/` careers, autosaves and JSON exports (created on first run)
- `playbooks/` your custom plays (JSON) — see `docs/PLAYBOOK_FORMAT.md`
- `docs/` `ARCHITECTURE.md` (how the sim works, notes for the Unreal/C++ port)
- `tools/` calibration scripts comparing the sim with NFL numbers, and the UI test
- `tests/fakeqt/` a strict fake PyQt6 used by `tools/ui_test.py`
