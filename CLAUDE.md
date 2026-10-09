# Gridiron GM — notes for working on this project

A Football Manager–style American football GM game. Python 3 + PyQt6 today; the
simulation will later be ported to C++ inside Unreal Engine, so the sim must
stay UI-free (see `docs/ARCHITECTURE.md`).

## Running and testing
- Play: `python main.py` (Windows users run `Play.bat`, which makes a venv and installs PyQt6).
- UI smoke test (no display needed, uses the strict fake PyQt6 in `tests/fakeqt`):
  `python tools/ui_test.py` — clicks through every screen over two seasons. Must pass before committing.
- Sim calibration vs NFL averages: `python tools/calibrate.py [games] [seed]`.
- Player-level distributions (carry/target shares, 1,000-yard seasons, leaders):
  `python tools/usage.py`.
- Long-run stability / economy: `tools/longsim.py`, `tools/economy.py`.
- Expected-points table refit (after big engine changes): `python tools/fit_ep.py`.
- Offensive system identity (pass rate, depth, personnel, shotgun, QB runs per system): `python tools/schemes.py`.
- Check several calibrate seeds before trusting a change: league talent landscapes vary a lot.

## Design rules the owner has set
- Realism first, but outcomes must stay unpredictable and every attribute must matter.
  The base sim is fixed and refined; users can bend it only through settings sliders
  (per league, ZenGM-style, 1.0 = realistic baseline).
- Eras emerge naturally from what happens in each league (talent pipelines, coaching
  trends, rule changes by the competition committee). Never add era presets/options.
- Ratings: OVR/POT 1-99, position-relative; 74 = average starter, 82+ Pro Bowl, 90+ elite
  (roughly 40-60 players league-wide). Fringe players sit in the 40s, not lower. No star ratings.
- Potential is a range for young players (wider the younger), and it moves season to season.
  Growth/decline ages vary by player around position averages (QB/K late, RB early).
- Development breakdowns are shown but are the staff's (imperfect) opinion.
- Glossary must explain every rating, stat and call in plain football language.
- Holdouts: rare (0-3 a season). Playbooks encode real coaching concepts in our own data
  format; never copy third-party playbook files or diagrams into the game.
- The 22-man animated viewer and in-game play calling wait for the Unreal version.
- End goal: deep enough that one week can take an hour, and still engaging over 100+ seasons.

## Conventions
- Plain data tables + small functions for anything the C++ port will need (playbook.py,
  defense.py, specialteams.py, advanced.py, negotiation.py).
- New saved attributes need defaults for old saves (class attributes on Player/Team,
  `League.__init__` defaults are merged in `League.__setstate__`).
- Keep `docs/ARCHITECTURE.md` and the in-game glossary up to date with sim changes.
