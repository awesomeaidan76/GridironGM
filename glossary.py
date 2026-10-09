"""
glossary.py — plain-English explanations of every attribute, trait and rating.
Written for someone who knows football but is new to the game.
"""

ATTRIBUTE_DESC = {
    # Physical
    "speed": "Top-end speed once a player is moving. Wins footraces on deep balls, breakaway runs and pursuit angles.",
    "acceleration": "How fast he reaches top speed. Bursting through a hole, getting off the snap, closing on a ball carrier.",
    "agility": "Change of direction without losing speed. Cuts, route breaks, mirroring a receiver, dodging a rusher.",
    "strength": "Raw power. Holding the point of attack, pushing the pile, shedding blocks, breaking arm tackles.",
    "jumping": "Vertical leap. Wins jump balls and contested catches, and helps defenders contest them.",
    "stamina": "How long he plays at full effort. Low stamina means more rotation (especially running backs).",
    "injury_resistance": "Durability. Lowers the chance of getting hurt and slows the toll ageing takes on the body.",
    # Passing
    "throw_power": "Arm strength. How far and how fast he can throw — needed for deep shots and tight windows.",
    "short_accuracy": "Accuracy on quick throws under 10 yards: slants, flats, hitches.",
    "medium_accuracy": "Accuracy on 10-20 yard throws: digs, outs, crossers, seams.",
    "deep_accuracy": "Accuracy on throws 20+ yards downfield.",
    "throw_under_pressure": "Keeps accuracy when the pocket collapses or he's hit as he throws.",
    "touch": "Ability to drop a ball over a defender and into a receiver's hands — key on medium and deep throws.",
    "play_action": "How convincingly he sells the run fake. Better fakes freeze linebackers and open the field behind them.",
    "screen_accuracy": "Timing and placement on screens and quick throws behind the line.",
    # Ball carrying
    "vision": "Seeing the hole and the cutback lane before it opens. The most important trait for a runner.",
    "break_tackle": "Running through arm tackles and first contact.",
    "contact_balance": "Staying upright after contact to keep gaining yards.",
    "juke_spin": "Making defenders miss in space with jukes, spins and hesitation moves.",
    "stiff_arm": "Using the off arm to keep tacklers away.",
    "ball_security": "Protecting the football. Low ball security means more fumbles.",
    # Receiving
    "catching": "Reliable hands on routine catches. Low catching means drops.",
    "catch_in_traffic": "Holding on when a defender is draped on him or a hit is coming.",
    "spectacular_catch": "Highlight catches — one-handed, diving, toe-tap — when the throw isn't perfect.",
    "short_route_running": "Precision on short routes (slants, outs, hitches, drags).",
    "medium_route_running": "Precision on intermediate routes (digs, curls, comebacks, seams).",
    "deep_route_running": "Selling and stemming deep routes (posts, corners, go routes).",
    "release": "Getting off the line against press coverage without being jammed.",
    "separation": "Creating space at the top of the route — how open he is when the ball arrives.",
    # Blocking
    "pass_block": "Pass protection technique. Keeps rushers off the quarterback.",
    "run_block": "Run blocking technique: drive blocks, reach blocks, combination blocks.",
    "impact_block": "Knock-back power on contact — moving a defender off his spot.",
    "pulling": "Getting out of a stance and leading through the hole on power, counter and sweeps.",
    "footwork": "Kick-slide and balance in pass protection; especially important for tackles against speed.",
    # Pass rush
    "power_move": "Bull rush, long arm and other strength-based rushes.",
    "finesse_move": "Swim, spin, rip and speed-based rushes to win around blockers.",
    "pass_rush_iq": "Setting up moves, counters and timing — wins on third down when everyone knows he's coming.",
    # Run defense
    "block_shedding": "Disengaging from blockers to make the play.",
    "run_stop": "Holding the line against the run and controlling his gap.",
    "tackling": "Wrapping up and finishing tackles — fewer missed tackles and broken plays.",
    "hit_power": "How hard he hits. Big hitters force more fumbles.",
    "pursuit": "Taking good angles and chasing plays down from behind.",
    # Coverage
    "man_coverage": "Staying in a receiver's hip pocket in man-to-man coverage.",
    "zone_coverage": "Reading the quarterback and passing receivers off in zone coverage.",
    "press_technique": "Jamming a receiver at the line to disrupt his timing.",
    "interception": "Ball skills: turning a contested pass into an interception.",
    "pass_breakup": "Getting a hand in to knock the ball away; also makes contested catches harder.",
    # Kicking
    "kick_power": "Leg strength for field goals and kickoffs — longer range and more touchbacks.",
    "kick_accuracy": "Making the kick he has the leg for.",
    "punt_power": "Distance on punts.",
    "punt_accuracy": "Placement: pinning teams deep and avoiding touchbacks.",
    # Mental
    "awareness": "General football IQ: knowing the situation, the assignment and where everyone is.",
    "decision_making": "A quarterback's judgment — throwing to the right man, avoiding interceptions.",
    "progression_reads": "Working through reads 1-2-3 to find the open receiver instead of locking on.",
    "pocket_presence": "Feeling pressure and sliding away from it instead of taking sacks.",
    "composure": "Staying calm in big moments — clutch kicks, late-game drives.",
    "leadership": "Respect in the locker room. Leaders lift team morale and settle the team when momentum turns.",
    "play_recognition": "Diagnosing run or pass quickly; seeing through play-action and misdirection.",
    "anticipation": "Breaking on the ball before it's thrown — leads to interceptions and pass breakups.",
    "gap_awareness": "Defensive linemen and linebackers staying disciplined in their run gaps.",
}

TRAIT_DESC = {
    "consistency": "How close to his ability he plays each week. Inconsistent players have big highs and lows.",
    "work_rate": "Effort in practice and the weight room. The biggest driver of development and of how slowly he declines.",
    "temperament": "Discipline and composure. Low temperament means more penalties and bigger momentum swings.",
    "adaptability": "How quickly he learns a new scheme, team or role.",
    "ambition": "Drive to be great. Speeds up development and raises contract demands; ambitious players dislike long losing spells.",
    "big_game": "Rises (or shrinks) in the playoffs.",
}

RATING_DESC = [
    ("OVR (Overall)", "How good the player is right now at his position, 1-99. The scale is the same at "
                      "every position: 74 is an average starter, 82+ Pro Bowl level, 90+ elite. "
                      "A 74 kicker and a 74 quarterback are equally good at their jobs, not equally valuable."),
    ("POT (Potential)", "The best he is ever likely to be. For players you haven't seen much of it is a scouted "
                        "range. Past his prime a player's potential is simply his current rating."),
    ("Role ratings", "How well a player fits each role at his position (for example Power Back vs Receiving "
                     "Back). They use the same 1-99 scale but weight the attributes that role needs."),
    ("Tiers", "Elite 90+, Pro Bowl 82-89, Starter 72-81, Rotation 64-71, Backup 55-63, Fringe below 55."),
    ("Attributes (1-100)", "90+ world class, 75-89 quality, 60-74 solid starter level, 45-59 backup, below 45 poor."),
    ("Development", "Each offseason a player grows, holds or declines depending on age, potential, work ethic, "
                    "coaching, playing time, production, injuries, scheme fit, mentors and some luck. Your "
                    "staff's report on his profile explains it — better coaches read it more accurately."),
]

STATS_DESC = [
    ("EPA (Expected Points Added)", "Every down, distance and field position is worth a number of points "
     "on average (1st-and-10 at your own 25 is worth about +0.8, 1st-and-goal at the 2 about +5.5). EPA is how "
     "much a play changed that number. A 4-yard run on 3rd-and-6 has negative EPA even though it gained "
     "yards; a 12-yard catch on 3rd-and-10 has a big positive EPA. The values come from this game's own "
     "simulation, so they match how the league actually plays."),
    ("EPA per play / per dropback", "Average EPA. Around 0 is average; +0.10 is a very good offence; "
     "for a defence, lower (negative) is better."),
    ("Success rate", "Share of plays with positive EPA. Good offences are above 50%."),
    ("Dropbacks", "Pass attempts plus sacks plus scrambles: every time the quarterback dropped back to pass."),
    ("aDOT (average depth of target)", "How far past the line of scrimmage the passes travel on average, "
     "caught or not. High aDOT = vertical passer or deep threat; low = quick game, check-downs."),
    ("CAY/Cmp", "Completed air yards per completion: how far the ball travelled in the air on catches."),
    ("Pressured / Pressure%", "Dropbacks where the rush got home before the throw (sacks, hits, hurries). "
     "For a pass rusher, Pressures counts how often he was the one who got there."),
    ("Target share", "Share of the team's targets that went to this player."),
    ("YAC/Rec", "Yards after the catch per reception."),
    ("Coverage: Tgt / Cmp / Rating allowed", "Throws at the receiver a defender was covering, completions "
     "allowed and the passer rating on those throws. Lower is better."),
    ("1st Dn", "Plays that gained a first down or a touchdown."),
    ("Snaps / Snap %", "Plays a player was on the field for. Snap % compares him with the team's busiest player "
     "on that side of the ball."),
    ("Stops", "Tackles that ended a play as a failure for the offense (negative EPA)."),
    ("Missed tackles", "Charged to a defender who whiffed on a play that went for a big gain."),
]

GAMEDAY_DESC = [
    ("Fatigue", "Every snap costs energy — linemen and pass rushers burn it fastest, quarterbacks barely at all. "
     "The huddle gives a little back, the sideline a lot, halftime most of it. A tired player loses speed, "
     "strength and technique and is more likely to get hurt. Stamina decides how fast he tires. Heat and "
     "no-huddle offenses (which stop the defense substituting) wear players down faster."),
    ("Rotation", "On every snap the staff compares each starter's ability, discounted by how tired he is, "
     "with the fresher backups, and the better option plays. Defensive linemen rotate the most, offensive "
     "linemen and quarterbacks almost never. Set each group's rotation on the Depth Chart. In a blowout "
     "late in the game the backups take over."),
    ("Game plan", "Before each game the defensive coordinator scouts the opponent and adjusts: more pressure "
     "against a shaky quarterback, a spy against a runner, a safety rolled toward a star receiver, a loaded "
     "box against a run-first team. Good coordinators read it right; poor ones over- or under-react. Set your "
     "own choices on the Game Plan screen."),
    ("Halftime adjustments", "At quarter breaks, and above all at halftime, both coordinators look at what is "
     "working — runs or passes, short or deep — and lean against it (defense) or into it (offense)."),
]

PLAYBOOK_DESC = [
    ("Offensive systems", "Each coach runs a system: Air Raid, West Coast, Run and Shoot, Spread Option, "
     "Pistol, Pro Style, Air Coryell, Power Run, Zone Run, Wing-T or Flexbone. The system decides which "
     "formations, pass concepts and run schemes get called most (see Tactics → Playbook)."),
    ("Option football", "On zone read, inverted veer, midline, speed and triple option the quarterback reads an "
     "unblocked defender and gives, keeps or pitches. Smart quarterbacks make the right read more often; "
     "a wrong read is usually a short gain or a loss."),
    ("Coverages", "Cover 0/1 are man coverage with zero or one deep safety; Cover 2/Tampa 2/Cover 4/Cover 6 "
     "keep two safeties deep; Cover 3 plays three deep. Every coverage has routes that beat it — corner routes "
     "against Cover 2, seams and flats against Cover 3, crossers against man, hitches against quarters."),
    ("Pressures and line games", "Fire zones and blitzes send five or six; they get home faster but leave "
     "hot throws and screens open. Stunts (TEX, ET, Twist, Pirate) and simulated pressures (Creeper) "
     "confuse a line without giving up coverage."),
    ("Fronts", "Over/Under/Wide 9/Bear for four-man lines, Odd/Tite for three-man lines. Bear and Tite fronts "
     "clog inside runs but are softer on the edge; a Wide 9 rushes the passer but opens inside lanes."),
    ("Special teams", "Kickoffs (deep, directional, squib, pooch, onside), returns (middle, sideline wall, wedge, "
     "reverse), punts (spread, directional, rugby, pooch) and the receiving side's calls (return, wall, "
     "block, safe/fake-watch). Better core special-teams players and coaches win the hidden yardage."),
]

LINE_DESC = [
    ("Pass protection", "On every pass each rusher is matched against the blocker assigned to him: tackles take "
     "the edge rushers, guards the tackles, and spare linemen slide toward the most dangerous rusher (a double "
     "team). Tight ends and backs chip the edge or pick up blitzers. Power rushers test a blocker's strength, "
     "speed rushers his feet. The first rusher to win before the ball is out causes the pressure, and the "
     "blocker he beat is charged with it."),
    ("Pass-rush win rate", "How often a rusher beats his block, whether or not he reaches the quarterback "
     "in time. Around 20% is average; 30%+ is elite."),
    ("Pressures / sacks allowed", "Charged to the blocker who lost the rep. Unblocked rushers and coverage "
     "sacks are on nobody."),
    ("Run blocking", "Blockers at the point of attack are paired with the defenders there. Win your block and "
     "the runner has room (yards before contact); lose it and the defender wins the rep. A dominant win is a pancake."),
    ("YBC / YAC (rushing)", "Yards before contact, created by the blocking, and yards after contact, created "
     "by the runner."),
    ("Game grade (0-100)", "How well a player did his job on the snaps he played, compared with an average player "
     "at his position: blocks won and lost, pressures, coverage reps, tackles and misses, catches over expectation, "
     "EPA as a passer and so on. 90+ elite, 80-89 high quality, 70-79 above average, 60-69 average, under 50 poor. "
     "Season grades are snap-weighted. Grades feed the All-Pro team and awards."),
]

COACHING_DESC = [
    ("4th down and 2-point decisions", "Coaches compare win probability for going for it, punting and kicking "
     "(and for one or two points after a touchdown), then lean on their own temperament: aggressive coaches go "
     "for it on closer calls, cautious ones kick unless the numbers are clear. If going for it keeps working "
     "around the league, coaches get bolder over the years."),
    ("Two-minute and four-minute offense", "Trailing late, offenses hurry, get out of bounds, use timeouts "
     "when the clock is running and spike the ball when they have none left. Leading late, they run, stay in "
     "bounds and take the play clock down. Poor game managers lose seconds and waste timeouts."),
    ("Situational tendencies", "Each offensive coordinator has his own habits: early-down passing, short-yardage "
     "and red-zone calls, shot plays on 1st down, screens and draws on 3rd & long. The Game Plan screen compares "
     "your opponent's habits with the league."),
    ("Quarterback progressions", "The quarterback works his reads in order. Better processors see the "
     "coverage more clearly and get through more reads; gunslingers throw into tighter windows, careful "
     "quarterbacks take the checkdown or throw it away. Every extra read gives the pass rush more time. "
     "Against a blitz, a sharp quarterback spots it and throws hot."),
    ("Time to throw / tight window %", "Average seconds from snap to throw, and the share of throws into "
     "tight coverage (the receiver was not open)."),
]
