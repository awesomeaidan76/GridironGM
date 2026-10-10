# Gridiron GM — architecture and porting notes

This document explains how the game is put together, so that the simulation
can later be rebuilt in C++ inside Unreal Engine. The Python code is the
working design prototype. Every rule below already exists and is tested
there, so porting is a matter of translating it, not inventing it.

## 1. Layers

```
┌──────────────────────────────────────────────────────────────┐
│ UI (PyQt6 today, Unreal UMG later)                           │
│   ui_main.py, ui_screens_*.py, ui_dialogs.py, ui_live.py,    │
│   ui_widgets.py, ui_theme.py, ui_stats.py                    │
├──────────────────────────────────────────────────────────────┤
│ Game flow (no UI code at all)                                │
│   season.py   — the Continue button: weeks, playoffs, phases │
│   inbox.py    — decisions waiting on the user (to-do list)   │
│   save_manager.py — save / load / JSON export                │
├──────────────────────────────────────────────────────────────┤
│ League systems                                               │
│   free_agency.py, trades.py, market.py, draft.py,            │
│   roster_rules.py, staff.py, development.py, awards.py,      │
│   records.py, eras.py, committee.py, schedule.py,            │
│   contracts.py, negotiation.py, capplan.py, glossary.py      │
├──────────────────────────────────────────────────────────────┤
│ Match engine                                                 │
│   engine.py (+ playbook.py, defense.py, specialteams.py,     │
│   advanced.py, weather.py, injuries.py)                      │
├──────────────────────────────────────────────────────────────┤
│ Data model                                                   │
│   player.py, team.py, coach.py, league.py, ratings.py,       │
│   stats.py, settings.py, names.py, worldgen.py               │
└──────────────────────────────────────────────────────────────┘
```

Rule of thumb: nothing below the UI line imports PyQt. In Unreal, the
bottom four layers become a C++ module (a `UGameInstanceSubsystem` or plain
C++ classes). Widgets read from it and call its commands.

## 2. Data model

| Object | Key fields |
|---|---|
| **Player** | `attrs` (≈60 attributes, 1-100), `hidden` traits (consistency, work_rate, temperament, adaptability, ambition, big_game), `pa`, cached `_ca` (1-200), position, archetype, age, `curve_shift` (personal growth/decline ages), contract `{salary, years, signed, length, bonus, guaranteed, guar_left}`, injury, morale, reputation, `season_stats`/`playoff_stats` (counters), `career` {year: stats}, flags `ps` (practice squad), `ir` (injured reserve), `holdout`, `potw` |
| **Team** | roster (list of Player; PS and IR players stay in it with flags), `depth_overrides`, `tactics` (user sliders 0-100), coach, `staff` {role: StaffMember}, `scouts`, `owner`, facilities, scouting, dead_cap, history |
| **Coach** | ratings 1-20 (offense, defense, development, motivation, game_management, adaptability, discipline), offensive and defensive scheme, `tendencies` (pass_lean, deep, outside, qb_run, heavy, tempo, screen, committee, play_action, rpo, trick, blitz, zone, two_high, aggression) |
| **League** | teams, structure (conference → division → teams), phase, week, schedule, results, standings, draft class and order (`draft_order` (round, pick, owner), `draft_orig`, `draft_comp`), `pick_owner`, free_agents, history, news, `pipeline` (talent per position group), `archetype_weights`, `rules` (competition committee), `gm` (owner confidence, reputation, history), `game_records`, `weekly_awards`, `negotiations` |

**Ratings.** `ca = (weighted_avg(attrs, position) - 20) * 2.6`, clamped to
1-200. The displayed OVR is position-relative:
`74 + 8.7 * (ca - mean_pos) / sd_pos`, softened above 86. Each position is
anchored to the distribution of its starters (`ratings.OVR_ANCHORS`).

**Role ratings** re-weight a position's attribute weights with the
archetype's modifiers (`ratings._role_weights`).

## 2b. Depth charts and playing out of position: `position_fit.py`, `team.py`

**Slots.** The depth chart has the 14 positions plus KR and PR
(`position_fit.DEPTH_SLOTS`, starters per slot in `STARTERS`, how deep the
engine reads each list in `GAME_DEPTH`). Any player can be listed at any slot.
A slot's pool is the players whose own position it is plus anyone listed there
(`Team.depth_overrides[slot]`, the user's order) or chosen by a CPU staff
(`Team.cpu_oop`). `Team.depth(slot)` returns the pool in order: listed players
first, then the rest by `depth_score` (rating at the slot, `NATURAL_BONUS` = 8
CA at his own position, plus the youth boost for CPU clubs).
`Team.depth_auto` keeps every slot sorted by that score; `depth_locks[slot]`
holds players at their place whenever a slot is sorted. `auto_order` adds a
player from another position only when he beats the weakest natural starter by
the bonus and doesn't start anywhere else.

**Slot rating.** `Player.rating_at(slot)` is the player's own CA at his
position, and elsewhere `position_fit.slot_ca`: the slot's formula
(`ratings.compute_ca`) on his attributes plus `slot_deltas(p, slot)`:

- *Size fit.* Weight beyond the slot's normal range (`player.SIZE` mean ±
  `SIZE_TOL` = 1.25 sd), in sd, softly capped at `SIZE_CAP` = 4: every
  non-mental attribute the slot weights loses `FRAME` (2.2) per sd, plus
  `UNDER_ATTRS` (strength, blocking, shedding, run stopping, tackle-breaking,
  balance, hit power, tackling) when light, or `OVER_ATTRS` (speed,
  acceleration, agility, jumping, stamina) when heavy. QB, K and P ignore size.
- *Familiarity* (0-100; 100 at his own position). `Player.familiarity`
  {slot: value} holds what he has learned; otherwise he starts at
  `RELATED[own][slot]` (`DEFAULT_START` = 5). The penalty is
  `FAM_MAX (18) × ((100 - f) / 100) ^ 1.35` attribute points: mental attributes
  in full, techniques his own position never uses (or any slot he knows at 90+)
  at `NEW_TECH` (0.7), the ones it does at `KNOWN_TECH` (0.3). Physical
  attributes are never affected.

The match engine adds the same `slot_deltas` to his attributes on every snap he
plays at that slot, so the rating and the sim agree. Natural ratings never
change. POT at a slot (`slot_pot_ca`, `Player.pot_range_at`) is the rating at
full familiarity plus his remaining growth × the share of the slot's formula
his own position's weights cover (`coverage`). Results are cached per player
(`_fit_cache`, cleared by `recalc` and familiarity changes, never saved).

**Learning** (`weekly_learning`, called from `season._post_week` and after
each playoff round): a player on a slot's list who isn't natural there gains
`learn_rate × PRACTICE_SHARE (0.5) × reps` a week (reps 1.0 for starters, 0.6
for the next man, 0.3 for the one after him), plus `learn_rate × 0.5 × min(1, snaps/45)`
from the snaps he played there (`GameResult.slot_snaps`). `learn_rate =
(3 + 0.12 × starting familiarity) × max(0.4, 0.55 + 0.9 × adaptability/100 +
(awareness - 60)/200)` (adaptability is a hidden trait): about four weeks for tackle to guard, more than a season for
receiver to corner. Each offseason (`offseason_decay`) a player keeps 90% of
what he learned above his starting point at a slot he played last season, 65%
otherwise.

**CPU clubs** (`front_office.weekly_depth`, weekly and at season start): any
non-starter who rates at least `oop_margin` CA above the weakest natural
starter at a slot starts there (`OOP_MARGIN` 17, minus up to 6 for reputation
over 50, minus 0.4 per point of the head coach's adaptability over 10, at
least 7). One move per slot, one slot per player; news on each new move.
Injury cover on game day stays in `Team.lineup` (`FALLBACK` positions, then
the whole roster, by rating at the slot).

**Two-way roles** (`front_office._two_way`, in the same weekly pass, stored in
`Team.cpu_role` {slot: [player id, place]}): at most one per club. A healthy
starter with stamina 70+, OVR 85+ or reputation 70+, not a QB, K, P or lineman,
who rates 78+ OVR at one of `TWO_WAY_SLOTS`, is no more than `TWO_WAY_NEAR` (2)
CA below that slot's weakest starter and at least `two_way_margin` (12, minus
up to 4 for reputation, minus 0.4 per point of coach adaptability over 10, at
least 3; 3 less to keep last week's role) above its first backup, is listed at
that place (`STARTERS[slot]`, the first backup) by `Team.full_depth`. Moves
whose starting familiarity is 50+ (corner and safety, edge and linebacker) are
left to game-day cover.

**Permanent position changes** (`position_fit.move`, `change_position` for a
club's move: morale, depth lists, transaction). The new slot becomes
`p.position`; `p.converted_from` holds the position he came up at
(`home(p)`), `p.base_weight` his weight at the move and `p.position_history`
[(year, old, new)] every move. `natural(p, slot)` is true only at a position
he isn't converting to, so while converting `p.ca` (`converted_ca`) is the
slot formula plus `slot_deltas` at his listed position: OVR, contract value
(Q20a) and development all follow the new position, with the penalty.
`Player.recalc` rebuilds it; `development._apply_ca_change` shifts its targets
by the same offset. `p.pa` is reset to `slot_pot_ca` at the move; a converting
veteran's POT is his conditioned, learned rating there. Moving back to
`converted_from` clears the conversion. A converting player gets at least
`TRAIN_REPS` (0.6) practice reps a week at his listed position, training
camp (`training_camp`, `CAMP_WEEKS` = 3 weeks of reps at season start) counts,
and `coaching_mult` (0.85 + position-coach development/20 × 0.3) scales all
learning. Each offseason `offseason_conditioning` moves his weight toward
`target_weight` (the slot's range, at most `CONDITION_MAX` = 25 lb from
`base_weight`, 14/10/6 lb a year by age): each lb gained costs 0.08 speed and
acceleration and 0.06 agility and adds 0.08 strength; each lb lost costs 0.08
strength and adds 0.04 acceleration and agility. `settle` makes him a natural
once familiarity is `SETTLED` (99.5) and his size gap is at most `SETTLE_SIZE`
(0.25 sd); his old position keeps its familiarity.

**Second position** (`p.train_pos`, user only): `weekly_learning` gives at
least `TRAIN_REPS` there, and when he grows `development._weights_for_change`
also spreads points over that slot's skills his own position doesn't use (35%
of the slot's weights; athletic attributes excluded). Those points don't count
toward his CA change; the development factor `second_position` (× 0.93) is the
cost.

**CPU conversions** (`front_office.offseason_conversions`, each offseason before
camp, seeded per club and year): `conversion_options` lists "start" moves
(projected learned and conditioned CA at the slot beats its weakest starter by
`convert_margin`: 15, minus 0.4 per point of coach adaptability and 0.2 of
development over 10, minus up to 3 for a risk-taking GM, at least 5, and the
gain × position value beats what the club loses at his old spot) and "depth"
moves (a backup who projects 0.6 × margin better there and at least as good as
its first backup). Skipped: QB, K, P, practice squad, IR, holdouts, players
already converting or moved in the last `CONVERT_COOLDOWN` (2) seasons, moves
that break the roster minimum, unrelated moves (starting familiarity under 15)
after 24, and starters the club would only start back at their old spot
(`oop_margin`). Each option passes with 25% + 3% per point of coach
adaptability over 10 (10-70%), at most `MAX_CONVERSIONS` (2) a club and one per
destination. News ("Position Change") with his reaction.

**Morale** (`move_mood`): ±(adaptability − 50)/12, minus up to 8 × (0.5 +
ambition) for a move to a position with a lower `contracts.POSITION_MAX_SHARE`
(a little plus for a higher one), +4 for becoming a starter, −5 for losing a
start, minus (reputation − 60)/10 for a star moved off his spot, × (1.3 − 0.6
× temperament), clamped −12..+8. Weekly, a player with 10+ snaps away from his
listed position gets `snaps_mood` (adaptability helps, ambitious stars mind).

**Staff Position Report** (`staff_report`): per slot today, learned
(conditioned), slot POT, familiarity, weeks to learn, size note and a verdict,
each rating with a fixed-per-season error of max(0.5, (20 − position coach
development)/20 × 5).

## 2c. Package slots and personnel: `packages.py`

**Package slots** are extra depth lists (`PACKAGE_SLOTS`: slot → base
position, role formulas, players on the field, adds-or-replaces, label):
3DRB and PWRB (RB), SLOT (WR), JTE (TE), RE (EDGE), RDT (DT), SUBLB (LB), NCB
(CB) and S3 (S). They are in `position_fit.DEPTH_SLOTS`, so the user's
overrides, locks and auto sort work on them. A package plays its base
position: `base_of(slot)` maps it before every familiarity, size, deltas and
learning call, and the engine labels its players with the base position.
`package_ca` is the best of its `ratings.role_ca` formulas on his attributes
with that base position's `slot_deltas` (`Player.rating_at` / `ovr_at` use
it); a package's POT is the base position's POT shifted by (package OVR − base
OVR). The natural pool is `POOL` (PWRB also takes fullbacks).
`weekly_learning` gives package reps at the base position, only above what
the base list already gave.

"Adds" packages (SLOT, JTE, NCB, S3) put men on beside the base starters
(`BASE_STARTERS` = 2 of the base list). Auto order (`Team._package_last`)
lists the base starters last, so a package left alone adds the next best men
and the CPU plays as before. When the user has set the list
(`Side.pk_set`), `GameSim._adds` picks the package players first and the base
list fills around them. `_fill` tops a short package list up from its base
position. "Replace" packages: `_backfield` takes the third-down and power
backs from 3DRB/PWRB (the user's list as set; a CPU staff only when the
package rating beats the lead back's); on passing downs
(`_passing_down`: 3rd and 7+, 2nd and 12+, 4th and 5+, hurry-up) the defense plays its
RDT and RE lists; nickel, big nickel, dime and quarter take their linebackers
from SUBLB.

**Personnel** codes are backs then tight ends (`personnel_counts`; receivers
are the rest of five). `_personnel` weights 11/12/21/22/10 plus 13 (0.02 +
0.07 × heavy, if the club has three tight ends or a JTE list; +0.12 in short
yardage), 20 (0.012 + 0.02 × tempo with two backs; Pistol and Spread Option
+0.02) and 23 (goal line at the 3 or closer with a fullback and three tight
ends). `playbook.PERSONNEL_SLOTS` has the slots for each (TE3 for the third
tight end; in 20 the FB slot is the second back) and `playbook.route_for`
gives TE3 the SL or Z route when a play has none for him.

**Defensive packages** (`DEF_PACKAGES`: DT, EDGE, LB, CB, S counts) are picked
by `choose_def_package` from the offense's personnel, never its play: Quarter
late and long, Goal Line at the 2 or in short yardage against heavy sets, Dime
against four or more receivers, Nickel against three (Big Nickel 4-20% of the
time), Big Nickel against two or three tight ends by the coordinator's lean
(`_big_nickel_lean`: two-high coverage tendency and the third safety's
rating), Nickel on 3rd and 7+ against two receivers (55%), otherwise Base or
3-4 Base. A no-huddle snap keeps the last package. Team stats count `pers|`
and `dpkg|` snaps.

## 3. A game: `engine.GameSim`

1. **Setup.**
   - Each side gets a game plan from `Team.gameplan()`: coach tendencies, plus what the roster is good at, plus the user's sliders.
   - Each player gets a **game-day form** value. It comes from consistency, morale, motivation, home field and big-game ability, carried over from his last game (an AR(1) process) so that hot and cold streaks form.
   - The weather is rolled.
2. **Every snap** (`snap()`):
   1. Handle kneel-downs, end-of-half field goals and fourth-down decisions (go for it, punt, field goal, or a fake).
   2. Check for a pre-snap penalty.
   3. Choose the call: a trick play, an RPO, a pass, or a run. The pass probability depends on down, distance, field position, game script (score × time remaining), urgency and weather.
   3b. The defence makes its own call without seeing the offence's (`defense.choose_call`): a front (Over, Under, Wide 9, Bear, Odd, Tite, Goal Line), a named coverage (Cover 0/1/1 Robber/2/Tampa 2/2-Man/3 Sky/Buzz/Match/4/6, Prevent), and sometimes a pressure (fire zone, nickel fire, Cover 1 and safety blitzes, double A-gap, Cover 0), a simulated pressure (Creeper) or a line stunt (TEX, ET, Twist, Pirate). Each has small opposite-signed effects: coverage-vs-route "beaters" (`defense.COV_EDGE`), run-fit changes by front and shell, extra rushers who leave receivers uncovered, stunts that a sharp line passes off.
   4. Pick personnel and formation, then the defensive package (section 2c).
   5. **Pass:** choose the concept (screen/short/medium/deep, play-action, flea-flicker). Pressure is a sigmoid of pass rush minus protection; under pressure the QB is sacked, scrambles or throws it away. Each receiver gets an *openness* score from route skill vs coverage. The QB's read is a softmax over the receivers, sharper for better processors. Then roll completion, interception and drops, and draw yards after the catch from an exponential distribution plus breakaway chances.
   6. **Run:** choose the concept (inside/outside zone, power, counter, trap, lead, draw, toss, buck sweep, jet sweep, reverse, and the option family: zone read, inverted veer, midline, speed and triple option) from the coach's system (`playbook.SCHEME_RUNS`). Option plays read an unblocked defender: the QB's decision making against the defender's recognition decides give, keep or pitch and whether the read was right. Blocking vs the front (plus the defensive call) gives `bd`; carrier skill vs tacklers gives `rd`. These set the stuff chance, a short "sure" gain (Gaussian), a long-tailed extra (exponential) and breakaway chances — the NFL shape: median 3 yards, mean ~4.3, about 10% of runs going for 10+.
   7. Resolve: post-snap penalties, injuries, momentum swings, the clock, first downs and turnovers.
3. **Fatigue and rotation.** Every player has an energy value (0-100) for the game. Each snap on the
   field costs energy by position (`engine.DRAIN`, scaled by stamina, heat and the fatigue sliders); the huddle
   gives a little back (less in a no-huddle), the sideline a lot, quarter breaks, timeouts and halftime more.
   Part of each snap's cost is "wear" that caps recovery until halftime. Below 86 energy, physical attributes
   lose `FAT_SLOPE` points per point (mental ones 30% of that) and injury risk rises. Before every snap
   `_rotate` compares each starter's value with fresher backups (position and user rotation style set how
   readily) and the better option plays. The depth order wins: a player's value is the best rating at or
   below his place on the list, discounted by his own fatigue, so a backup only comes in to rest a tired
   starter, never because he rates higher. Snap counts are recorded. Blowouts late in the fourth quarter
   send the backups in.
4. **Slots on every snap.** `_formation` and `_defense_set` fill the field in order (QB and line, back,
   tight ends, receivers; defensive line, linebackers, corners, safeties) and skip anyone already placed,
   so a player listed at two slots plays one per snap and the next man takes the other. `_snap_units`
   receives the slot of every player: drain is by slot (`DRAIN`), `GameSim._at` applies his
   `position_fit.slot_deltas` (read by `e()`), snaps away from his position are counted in
   `GameResult.slot_snaps`, and each unfamiliar player blows his assignment with probability
   `BUST_RATE (0.05) × unfamiliarity ^ 1.2`. A bust loses his pass-protection rep (his rusher comes free),
   his run-blocking or run-fit matchup (`trenches.run_matchups(bust=...)`) or his coverage (+9 openness for
   the receiver); a receiver who busts ran the wrong route (-7). A receiver lined up at back or tight end
   draws a safety in coverage when one is free. Unfamiliar players also raise their unit's
   penalty odds (`PENALTY_RATE` 0.30 × unfamiliarity each) and are likelier to be the one flagged. The
   trenches code asks `pos(player)`, the slot he is playing, for every role check.
5. **Game plans.** At kickoff each defensive coordinator scouts the opponent (`defense.scout`): pressure,
   coverage and shell leans, box count, QB spy, bracket target, shadow corner, with errors that shrink with
   the coordinator's rating. The user's Game Plan choices override it. At quarter breaks (mostly halftime)
   `defense.adjust` leans the defence against what is working and the offence leans toward it.
6. **Line play** (`trenches.py`). Pass protection assigns every rusher a blocker (tackles on edges,
   guards on interior rushers, spare linemen slide toward the most dangerous rusher, TEs/backs chip or pick up
   blitzers); each matchup is a one-on-one won on the two players' attributes, with more time for the rush on
   longer-developing plays (`PASS_RUSH_BASE` calibrates the pressure rate). The first winner is the pressure
   and the beaten blocker is charged. Run blocking pairs blockers and defenders at the point of attack (and on
   the backside); the average margin is the blocking edge `bd`.
7. **Quarterback decisions.** `_progression` orders the concept's reads, the QB perceives openness with noise
   that shrinks with decision making, throws when a read clears his threshold (gunslingers lower, later reads
   lower), else checks down, forces it or throws it away. Each extra read adds time for the rush. Smart QBs
   spot blitzes pre-snap and throw hot.
8. **Situations** (`situations.py`). A win-probability model (lead, time, expected points of the possession,
   pre-game edge) drives 4th-down and 2-point decisions, bent by each coach's aggression and game management
   (`FOURTH_CAUTION`, `TWO_CAUTION`). Timeouts, spikes, onside timing and the two-/four-minute clock are
   decided there too. Coaches' aggression drifts with league-wide 4th-down results (`eras.adapt_coaching`).
9. **Grades** (`grades.py`) turn each game's stat line into a 0-100 grade per player (per-position baseline and
   scale in `POS_NORM`), stored merge-safely as `grade_pts`/`grade_n`.
10. **Momentum** is a single value from -1 to +1 that shifts on big plays and turnovers, then fades. It nudges effective attributes, scaled by each player's temperament.

Every probability in the engine has a **calibration constant**. The NFL
targets are checked by `tools/calibrate.py` (league averages) and
`tools/usage.py` (player-level distributions: carry shares, target shares,
1,000-yard seasons, stat leaders, upset rates). Port those two harnesses
first. If the C++ engine reproduces their numbers, the port is correct.

**Plays.** For a pass, the engine:
1. picks the depth of the call;
2. picks a formation for the personnel group;
3. picks a concept from `playbook.py`, weighted by the coach's system and the user's playbook preferences.

The concept's routes then shape the passing play:
- Receivers whose routes match the call are the primary reads.
- Players assigned "block" help protection.
- The target's route depth sets the air yards.

Runs pick a run concept and a formation the same way. For the user's games
every snap stores a small diagram dict (formation, routes, defensive call,
result), which the live viewer animates.

**Special teams** (`specialteams.py`): kickoff types (deep, directional,
squib, pooch, onside, surprise onside) and returns (middle, sideline wall,
wedge, reverse); punt types (spread, directional, rugby, pooch) against
return calls (return, wall, block, safe/fake-watch); field-goal block vs
safe. Core special-teams players (backup linebackers, safeties, corners,
tight ends and backs) plus the special-teams coach make a unit rating that
moves return yardage on both sides.

**Advanced stats** (`advanced.py`): every scrimmage snap is valued with an
expected-points model (down, distance, yard line) fitted to this engine by
`tools/fit_ep.py`. EPA, success rate, air yards (aDOT, CAY), pressures,
coverage allowed and first downs are credited to players and teams.

**Development** (`development.py`) works out an expected change from age
and potential, multiplied by these factors:
- work rate and ambition;
- coaching and facilities;
- playing time;
- production vs ability (percentiles computed at season end);
- injuries and morale;
- complacency;
- scheme fit;
- a veteran mentor;
- contract year;
- team culture.

A random draw is then applied on top. The report shown to the user splits
the change between those factors. The staff's view gets noisier the weaker
the coaches are. Young players also get a smaller mid-season change after
week 9.

**Settings.** Match Engine, League, Development and AI settings are stored in each league
(`League.custom_settings`, activated by `settings.use_league`), like ZenGM's league settings; 1.0
everywhere is the realistic baseline.

**Contracts** (`negotiation.py`): contracts carry a signing bonus (spread
evenly over the cap) and guaranteed money; releasing a player leaves the
unamortised bonus plus unpaid guarantees as dead money. User negotiations run
in rounds against an agent (Hardball, Business, Easygoing) with limited
patience; the player's priorities (money, security, winning, role, loyalty)
change how he values an offer's years, guarantees and destination. Underpaid
stars may hold out at training camp (unavailable for games until they settle,
report, or are extended).

## 4. The season loop: `season.advance()`

```
preseason → regular (18 weeks) → playoffs (6 per conference) → season_end
          → resign → draft → free_agency → preseason …
```

Each step is a pure function of the league state. Things that happen
weekly, in `_post_week` (plus single-game records after every game):
- injuries heal;
- morale moves;
- news is written;
- scouts learn about prospects;
- the owner's confidence moves;
- players learn the slots they are listed at away from their own position, converting players their new
  position and anyone training a second position (`position_fit.weekly_learning`);
- morale reacts a little to snaps away from his position (`position_fit.snaps_mood`);
- CPU staffs review out-of-position starters and two-way roles (`front_office.weekly_depth`);
- AI teams manage IR and the practice squad and sign depth;
- AI teams trade with each other;
- holdouts settle, report or drag on;
- Players of the Week are named.

At `end_season`:
- awards are given and history is recorded;
- front offices review the season (GM records, draft learning, owner sales, GM firings and hirings);
- the coaching carousel runs (coordinators can be promoted to head coach);
- contracts tick down;
- every CPU club sets its plan for the coming year;
- **eras evolve** (talent pipelines, coaching adaptation, scarcity feedback);
- **the competition committee meets**;
- the combine takes place;
- the draft order is set (traded picks and compensatory picks included);
- staff turn over;
- the **owner reviews** the season and may fire you.

## 4b. Front offices: `front_office.py`

Every CPU club has three decision makers, all plain data plus small functions:

- **Owner** (`staff.Owner` plus `owner_traits`): patience, ambition, spending and meddling (1-20). Labelled with an owner type (Win-at-All-Costs, Patient Steward, Penny-Pincher, Meddler, Hands-Off, Showman, Trigger-Happy, Traditionalist). Each club also has a power structure: GM-led, Coach-led or Owner-run.
- **General manager** (`GM`): 12 traits (0-1) seeded from one of 12 archetypes (`GM_ARCHETYPES`) plus noise. Judgement (1-20) is kept separate from style. The GM also carries a career record, draft picks and `pos_belief`, which is learned from his own draft hits and misses.
- **Head coach**: a style label from his strongest rating, and `youth_trust`, which nudges close depth-chart calls toward young players.

**Plans** (`PLANS`):
- Each plan sets multipliers on pick, youth and veteran value, appetite to buy and sell, free-agent spending and playing time for the kids.
- `choose_plan` scores every plan from an assessment of the club: roster rank, last record, core age, young starters, stars, QB status, next year's cap load, owner mood and GM traits.
- It adds noise and hysteresis (the current plan gets a bonus, more while it is committed).
- Plans are set after each season and reviewed two weeks before the trade deadline (`update_plans`).

**One valuation feeds every decision:**
- `player_mult` covers age by plan and trait, position value, stars or depth, loyalty to his own players, QB search, injury risk, coach-led scheme fit and a hot-seat veteran bias, plus a judgement error that stays fixed for the season.
- Position value blends a traditional table with an analytics table and leans with the league's pass rate. Analytics GMs read the last three seasons; old-school GMs read the last fifteen.
- `pick_mult` uses the plan and patience. `demand` uses hardness.

**Where the valuation is used:**
- `trades.trade_value` and `evaluate`: the CPU side values what it gives up through its own eyes.
- `market.py`:
  - buyers and sellers are chosen by plan and activity;
  - blockbusters for stars by all-in clubs;
  - salary dumps by clubs resetting their cap;
  - gamblers trade up, analytics GMs trade down;
  - both sides must agree;
  - the user's trading block (`block_offers`): each club's budget is the most it would give and
    still pass `trades.evaluate`, and it fills that with the best players or picks for the user;
  - `make_it_work` searches the user's picks and players for the cheapest addition that passes `evaluate`.
- `draft.board_value`: risk weights ceiling over polish, the BPA trait weights need, and QB search adds weight to quarterbacks.
- Draft-day trade-downs and trade-ups.
- `free_agency.ai_free_agency_wave`:
  - spend factor (plan × owner wallet × GM);
  - star-chasers go after the top names;
  - value hunters chase bargains;
  - rebuilders skip 29+;
  - analytics GMs protect compensatory picks.
- `ai_resign`: loyalty, cap discipline and plan age limits.
- `hire_coach`: a slate of candidates, scored by `coach_fit`.
- Coach firing: owner patience, rebuild grace, and new GMs bringing their own coach.

**Seasonal review** (`season_end`):
- GM records are updated.
- Draft learning: picks from four drafts ago are graded against the same round.
- Copycat drift toward the champion's GM.
- Owner sales (2% a year).
- The GM carousel: firing by owner patience and ambition. Replacements come from the pool, a successful front office's lieutenant, or a new archetype weighted by recent champions, the owner's taste, scarcity, and contrast with the man who failed.

Settings: `gm_hot_seat` and `ai_personality_strength`, alongside the existing AI sliders.

## 5. How eras emerge (no presets)

- `eras.evolve`:
  - Each position group's talent pipeline drifts. Kids chase prestige (fame plus money relative to a long-run baseline). Scarcity pulls the other way: thin positions attract talent.
  - Archetype popularity follows success.
  - `adapt_coaching` moves every coach's pass lean toward whatever is more efficient (net yards per attempt vs yards per carry). Defenses answer pass-heavy leagues with two-high shells, which soften run defense.
- Slow drift: each group also has a generational wave (`pipeline_wave`, a very persistent random walk), and the league's football culture (`style_drift`) drifts with what has been working. Coaches settle back toward their scheme *plus* that culture, so a passing (or running) generation can last decades.
- Front offices: analytics GMs re-value positions as the league changes, and GM styles spread when they win titles and fade when they fail (see 4b).
- `committee.review` changes rules (downfield contact, QB protection, holding, kickoff touchbacks) when scoring dries up or quarterbacks keep getting hurt.
- Coaching trees: successful coaches' assistants get hired elsewhere and take their mentor's tendencies with them. Innovators counter the trend.

## 6. Suggested porting order for Unreal

1. Data model and ratings, with unit tests that compare against the Python outputs.
2. `engine.py` with `playbook.py`, `defense.py`, `specialteams.py` and `advanced.py` (all plain data
   tables plus small selection functions), then validate it with the calibration harness, running
   headless in a commandlet. Re-fit the EP table with `tools/fit_ep.py` if the engine changes.
3. `season.py` and the league systems.
4. Save and load. A JSON schema mirroring `save_manager.export_json` is the easiest path; it is also what a local AI model can read.
5. UI. Keep the screen structure (sidebar plus screens). UMG `ListView`s with sortable headers replace the Qt tables.

Random numbers: the Python code uses `random`. For deterministic replays in
C++, give the league one seeded RNG stream (for example PCG32) and pass it
explicitly.
