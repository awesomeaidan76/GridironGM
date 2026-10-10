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
    ("POT (Potential)", "The rating he reaches if his development goes well. About one young player in three "
                        "gets there or beyond, most end a few points short and some well short. It is not fixed: "
                        "each offseason (and at mid-season for young players) a year in which he grew faster than "
                        "expected raises it, a stalled year lowers it, and work ethic, coaching, playing time and "
                        "how he plays move it too, more the younger he is. Young players sit well below it (about "
                        "18 points at 21 and 7 at 24) and grow fastest from 21 to 24, about 3 points a year; "
                        "quarterbacks and kickers grow more slowly for longer. For players you haven't seen much "
                        "it is a scouted range. Past his prime a player's potential is simply his current rating."),
    ("Role ratings", "How well a player fits each role at his position (for example Power Back vs Receiving "
                     "Back). They use the same 1-99 scale but weight the attributes that role needs."),
    ("Playing out of position", "Anyone can be put at any slot on the depth chart. His rating there (Slot OVR) "
     "is that position's formula applied to his own attributes, so a receiver at running back is judged on vision, "
     "balance and breaking tackles, which receivers rarely have. Then his size and how well he knows the "
     "position count. His rating at his own position never changes, and his contract is valued at his own "
     "position, until he is moved to the new one for good."),
    ("Familiarity", "How well he knows a position, 0-100: always 100 (Natural) at the position he came up "
     "playing. Elsewhere he starts "
     "with what carries over (a tackle already knows a lot about guard, a receiver very little about corner) "
     "and learns from practice reps when he is on that slot's depth chart (starters get the most) and from "
     "game snaps there: about four weeks for a related move, a season or more for an unrelated one. "
     "Adaptable, football-smart players learn faster, and skills at a position he stops playing fade a little "
     "each offseason. Low familiarity costs his mental attributes, the techniques his own position never uses "
     "and, a little, the ones it does. Accomplished 90+, Competent 70+, Learning 45+, Awkward 20+, below that "
     "Unfamiliar."),
    ("Size fit", "Every position has a normal build. A player well outside it pays for it there: too light and "
     "he loses strength, blocking, block shedding and tackle-breaking (a 245 lb linebacker gets moved by 315 lb "
     "guards); too heavy and he loses speed and quickness; either way everything he does at that spot suffers a "
     "little. Inside the normal range there is no effect."),
    ("Slot POT", "What he could become at a slot once he has learned it: his rating there with full "
     "familiarity, plus the growth he still has in him, in proportion to how much the two positions share."),
    ("Position change", "Moving a player to a new position for good (Change Position on his profile, or "
     "right-click him on the Depth Chart). The new position becomes his listed one: his OVR, his contract value "
     "and his development follow it, and his potential is reset to what the staff expect him to reach there. "
     "He is not a natural yet: until he has learned it his OVR there carries the familiarity penalty (and the "
     "size penalty if he is the wrong build). His old position stays familiar, and moving him back makes him a "
     "natural there again."),
    ("Converting", "A player learning the position he was moved to (marked * in the depth chart). He gets "
     "practice reps there every week even as a backup, and training camp counts too. Good position coaches "
     "teach it faster. Each offseason a conditioning program moves his weight toward the position's normal "
     "build, by up to about 25 lb in all (faster for young players): bulking up costs a little speed and "
     "quickness, slimming down a little strength. He becomes a natural once he knows the position and is close "
     "to its build; a receiver who can never get big enough for tight end keeps a small size penalty."),
    ("Second position", "A training focus on his profile (Positions tab): he takes extra practice reps at a "
     "second position, so he learns it without being on its depth chart, and part of his offseason growth "
     "goes into its skills. It costs him a little development at his own position. Moving him there for good "
     "ends it."),
    ("Staff Position Report", "Your position coaches' view of where else a player could play: his rating there "
     "today, once he has learned it (and been conditioned for it), his potential there, how well he knows it "
     "and how many weeks it would take. Like every report it is their opinion: the better the position coach, "
     "the closer it is to the truth. Natural fit and Worth the work mean he should be about as good there as "
     "where he is; Could make the switch and Long project a few points worse; Emergency option and Not suited "
     "well below."),
    ("Tiers", "Elite 90+, Pro Bowl 82-89, Starter 72-81, Rotation 64-71, Backup 55-63, Fringe below 55."),
    ("Attributes (1-100)", "90+ world class, 75-89 quality, 60-74 solid starter level, 45-59 backup, below 45 poor."),
    ("Development", "Each offseason a player grows, holds or declines depending on age, potential, work ethic, "
                    "coaching, playing time, production, injuries, scheme fit, mentors and some luck. Your "
                    "staff's report on his profile explains it — better coaches read it more accurately."),
    ("Raw / Polished", "How predictable a young player's development is. Raw players (about one in six) keep a "
                       "wide potential range until they are close to their peak: their ceiling moves more from "
                       "year to year and they break out or bust more often. Polished players are easier to "
                       "project — a higher floor and a lower ceiling — and change less. Most players sit in "
                       "between and are not tagged."),
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
    ("Injuries", "Anyone in the collision can get hurt, not just the ball carrier: the runner and the man "
     "who tackles him, a receiver and his defender on a contested throw, the linemen on every snap, "
     "receivers and defensive backs pulling muscles in their routes and coverage, and the quarterback when "
     "he is sacked or hit as he throws. Linemen take a small knock every play, a ball carrier a bigger one "
     "on each touch, so (as in the NFL) a running back is about a tenth of all injuries and the trenches "
     "about a third. Durability, fatigue and the league's Injury Rate setting raise or lower every chance."),
    ("Rotation", "Your depth chart decides who plays. On every snap the staff checks how tired each starter "
     "is, and a fresher backup comes in to rest him when that is the better option at that moment. A starter "
     "is never benched just because someone listed behind him rates higher. Defensive linemen rotate the most, "
     "offensive linemen and quarterbacks almost never. Set each group's rotation on the Depth Chart. In a "
     "blowout late in the game the backups take over."),
    ("Two slots", "A player can be listed at two slots (a receiver who also plays corner, a starter who returns "
     "kicks). He plays one spot per snap: when both of his slots are on the field together he plays the first "
     "(quarterback, line, running back, tight end, receiver; on defense line, linebacker, corner, safety) and "
     "the next man on the other list steps in. Every snap he plays costs energy."),
    ("Package slots", "Extra depth chart lists for one job inside a personnel group. Offense: Third-Down Back "
     "(passing downs and the two-minute drill), Power Back (short yardage and the goal line), Slot Receivers "
     "(the inside men in three- and four-receiver sets) and Jumbo Tight End (the third tight end). Defense: "
     "Pass-Rush Ends and Tackles (obvious passing downs), Sub Linebackers (who stays on in nickel and dime), "
     "Nickel and Dime Backs (the fifth and sixth defensive backs) and Third Safety (big nickel and quarter). "
     "A package player plays its base position, so his familiarity and size there count, and he is rated by "
     "that job's role formula (a third-down back as a Receiving Back, a nickel back as a Slot Corner). Slot "
     "receivers, nickel backs, the third safety and the jumbo tight end come on beside the starters: list your "
     "best receiver first at Slot Receivers and he moves inside. Left alone, each list adds the next best man "
     "(its starters are listed last), and the third-down and power backs only take over from a lead back who "
     "is worse at the job."),
    ("Blown assignments", "A player still learning a position sometimes busts: a missed block lets a rusher in "
     "free, a blown coverage leaves a receiver wide open, a wrong gap opens a running lane, a wrong route kills "
     "a pass. Unfamiliar players are also flagged more (false starts, holding, offside). Busts are counted in "
     "his stats."),
    ("CPU depth charts", "CPU staffs list players at their own positions and cover injuries from other "
     "positions on game day. Each week they also look for a player who would be overwhelmingly better "
     "somewhere else than the man starting there, and start him there (shown in the news). Stars get the "
     "benefit of the doubt, and adaptable head coaches try it sooner."),
    ("Two-way players", "A CPU club with a Pro Bowl level star (or a big name) who would also be a good starter "
     "at a quite different position, and much better there than the backup, lists him as that slot's first "
     "backup too: a receiver who takes handoffs, a linebacker at tight end, a corner at receiver. He plays one "
     "spot per snap and fatigue counts every snap. Moves between close positions (corner and safety, edge and "
     "linebacker) are left to game-day injury cover. Adaptable coaches try it sooner."),
    ("CPU position changes", "Each offseason a CPU staff may move up to two players for good: a safety to "
     "corner, a tackle inside to guard, a big receiver to tight end, a buried backup to where he projects "
     "better. They judge him on what he should be there once he has learned it against what they lose where "
     "he was, and won't move a player they would only start back at his old spot, or one they moved in the "
     "last two seasons. Adaptable, teaching coaches and risk-taking GMs make more moves. Each move is in the "
     "news with his reaction."),
    ("Player reactions to a move", "How a player takes a position change depends on who he is: adaptable "
     "players enjoy a new challenge, ambitious ones dislike a move to a position that is paid less, stars "
     "don't like being moved off their spot, and anyone likes a move that makes him a starter. Calm players "
     "take it in their stride. A player who spends real time away from his position each week also feels it "
     "a little: adaptable players don't mind, ambitious stars do."),
    ("Film study", "Before each game both staffs watch the opponent's recent games (four at the Pro difficulty "
     "level). They count how often it passes on each down and distance, which coverages it plays and how "
     "often it blitzes, and what offenses have done against it. Early in the season, with little film, they "
     "go on what they know of the coach's system. Better coordinators read the film more accurately."),
    ("Game plan", "Before each game the defensive coordinator scouts the opponent and adjusts: more pressure "
     "against a shaky quarterback, a spy against a runner, a safety rolled toward a star receiver, a loaded "
     "box against a run-first team. Good coordinators read it right; poor ones over- or under-react. Set your "
     "own choices on the Game Plan screen."),
    ("Offensive game plan", "The offensive coordinator plans for the defense too: he features the pass concepts "
     "that beat the coverages it plays most (Smash against Cover 2, crossers against man), takes more shots "
     "against single-high safeties and works underneath against two-high, calls more screens and quick throws "
     "against a blitzing team, leans on the run or the pass depending on which of its units is weaker, looks "
     "for the receiver with the best matchup against its corners and runs behind the stronger side of the "
     "line. Adaptable head coaches lean into the plan (game-plan coaches); stubborn ones mostly run their "
     "system. The Game Plan screen shows your coordinator's plan."),
    ("Reading tendencies", "A defense that has seen on film that an offense throws more than usual on, say, "
     "1st and 2nd down plays a lighter box there, and loads it where the offense likes to run. Sharp offensive "
     "staffs know what their own film shows and break their tendencies against defenses that read them."),
    ("Halftime adjustments", "At quarter breaks, and above all at halftime, both coordinators look at what is "
     "working — runs or passes, short or deep — and lean against it (defense) or into it (offense). The "
     "defense also updates its read of the offense's tendencies with what it has shown today."),
    ("Series adjustments", "Between series both staffs look at their call sheet: concepts, runs and coverages "
     "that have worked today get called a little more, ones that have been beaten a little less, and a "
     "defense whose blitzes keep getting burned rushes four more often. Sharper, more adaptable staffs adjust "
     "faster. Your Featured and Removed plays always stay in force."),
    ("Injury adjustments", "When a starter goes down both staffs re-plan: an offense that loses its quarterback "
     "leans on the run and plays safer, the defense re-scouts the backup, and an offense goes after a backup "
     "corner who has just come in."),
    ("Tempo against a tired front", "A sharp offensive staff that sees the defensive line tiring goes no-huddle "
     "more often, so the defense can't substitute fresh linemen."),
    ("Difficulty (CPU intelligence)", "A league setting chosen when you start a career and changed any time in "
     "Settings > AI: Rookie (0.5), Pro (1.0, realistic), All-Pro (1.5) or Hall of Fame (2.0). It changes how "
     "well CPU staffs decide, never how good their players are. Higher levels study more film and read it "
     "more accurately, lean harder into their game plans, adjust faster during games, manage the clock "
     "better and trust the numbers more on 4th down and two-point tries. Their front offices judge players "
     "and potential more accurately and weigh what a trade does to their roster more fully, so lopsided "
     "trades are harder to find. Your own staff always works at the Pro level, so its quality comes from "
     "the coaches you hire."),
]

PLAYBOOK_DESC = [
    ("Offensive systems", "Each coach runs a system: Air Raid, West Coast, Run and Shoot, Spread Option, "
     "Pistol, Pro Style, Air Coryell, Power Run, Zone Run, Wide Zone, Wing-T or Flexbone. The system decides "
     "which formations, pass concepts, run schemes and kinds of motion get called most (see Tactics → "
     "Playbook). Wide Zone is the modern under-center outside zone offense: motion on almost every snap, "
     "bootlegs, play-action shots and the leak and banana routes off the run fakes."),
    ("Defensive systems", "4-3 Over, 3-4 Two Gap, Cover 3, Tampa 2, Press Man, Two-High Match, Zone Blitz, "
     "46 Blitz and Three-High. A Three-High defense keeps a third safety on the field against most "
     "personnel: three deep shells and Cover 9 rotations to take away play-action and shots, a five-man "
     "Penny front to hold up against the run, and simulated pressures (Creeper, Amoeba) on third down."),
    ("Pre-snap motion", "A player moving before the snap. Jet motion (a receiver sprinting across the "
     "formation) sets up the jet sweep and makes the backside defenders respect it on other runs; orbit "
     "motion (a loop behind the quarterback) sets up screens and misdirection; across motion moves a tight "
     "end or receiver to the other side; a shift resets two or more players. Motion shows the quarterback "
     "man or zone (a defender following the man in motion means man), so his reads are cleaner, and a man in "
     "motion can't be jammed at the line. Disguised coverages (Cover 9, Cover 2 Invert) hide the answer, and "
     "a three-high shell adjusts with its safeties so motion tells it less. A little risk too: illegal motion "
     "and illegal shift flags, more often with careless players. The Pre-Snap Motion slider sets how often."),
    ("Pass concepts", "Each pass play is a set of routes built to beat certain coverages; Tactics → "
     "Playbook lists every one with its routes. Some newer ones: Spider 2 Y Banana (play-action, the tight "
     "end arcs out behind the linebackers while the fullback runs to the flat), Leak (play-action, a tight "
     "end slips across the field behind a defense flowing with the run), Scissors (post and corner from the "
     "same side), Hoss (hitches outside, seams inside: a quarters and Cover 3 beater), Jailbreak Screen (the "
     "receiver comes back inside behind released linemen) and Pop Pass (an RPO: the tight end pops up the "
     "seam off a jet sweep fake)."),
    ("Run schemes", "Inside and outside zone (the line steps together and the back picks a lane), duo "
     "(double teams with no pullers, best against a light two-high box), split zone (a tight end or fullback "
     "comes across to kick out the backside end), power and counter (gap runs with pulling linemen), pin and "
     "pull (block down, pull around to the edge), toss and crack toss (receivers block down on the linebacker "
     "and safety), trap, lead, draw, the jet sweep (needs jet motion) and designed quarterback runs (QB "
     "counter, QB power: the back becomes a blocker, an extra hat at the point of attack). Wildcat snaps the "
     "ball straight to a running back, who keeps it or hands to the jet man: one more blocker, no pass threat."),
    ("Personnel groups", "Two digits: running backs, then tight ends; the rest of the five skill players "
     "are receivers. 11 (one back, one tight end, three receivers) is the most common in the NFL; 12 adds a "
     "second tight end, 21 a fullback, 22 both, 10 is four receivers, 13 is three tight ends (heavy "
     "play-action and short yardage), 20 is two backs and three receivers (split backs and pony sets), and "
     "23 is the goal-line jumbo package. Heavy-personnel coaches use more tight ends and fullbacks; up-tempo "
     "teams stay in 11 and 10."),
    ("Defensive packages", "The defense sends on its personnel after seeing the offense's (never the play). "
     "Base (four linemen, three linebackers, four defensive backs; 3-4 teams play three and four) against two "
     "receivers; Nickel (a fifth defensive back for a linebacker) against three; Big Nickel (a third safety "
     "instead, to stay big against tight ends: two-high coordinators with a good third safety like it); Dime "
     "(six defensive backs, one linebacker) against four or more; Quarter (seven defensive backs) for Hail Marys; "
     "Goal Line (three tackles, two ends, three linebackers) at the goal line. No-huddle offenses keep the "
     "defense in whatever it had on the field."),
    ("Option football", "On zone read, inverted veer, midline, speed and triple option the quarterback reads an "
     "unblocked defender and gives, keeps or pitches. Smart quarterbacks make the right read more often; "
     "a wrong read is usually a short gain or a loss."),
    ("Coverages", "Cover 0/1 are man coverage with zero or one deep safety; Cover 2/Tampa 2/Cover 4/Cover 6 "
     "keep two safeties deep; Cover 3 plays three deep. Every coverage has routes that beat it — corner routes "
     "against Cover 2, seams and flats against Cover 3, crossers against man, hitches against quarters. "
     "Newer shells: Palms (quarters where the corner jumps the flat), Cover 8 (Cover 6 flipped), Cover 7 "
     "(man with two defenders bracketing the best receiver), Cover 2 Invert (shows Cover 2, the corners "
     "bail deep and the safeties take the flats), Cover 9 (shows two-high, spins to three deep at the snap) "
     "and Three-High (three safeties deep: kills shots and play-action, softer against the run)."),
    ("Disguise", "How much a coverage changes from what it showed before the snap. A disguised coverage makes "
     "the quarterback's pre-snap read noisier (less so for quarterbacks with high awareness and progression "
     "reads) and takes away much of what motion would have told him."),
    ("Pressures and line games", "Fire zones and blitzes send five or six; they get home faster but leave "
     "hot throws and screens open. A corner blitz brings a cornerback off the edge with a safety rotating to "
     "his man; an edge zone blitz brings a linebacker from wide with the end dropping into the flat. Stunts "
     "(TEX, ET, Twist, Pirate) and simulated pressures confuse a line without giving up coverage: Creeper "
     "(a linebacker rushes, a lineman drops), Amoeba (nobody in a stance on third down, so the protection has "
     "to guess, hardest on a young line) and Double Mug (both linebackers in the A gaps, the center has to "
     "get the protection right). Green dog: in man coverage, a linebacker whose running back stays in to "
     "block rushes the quarterback too."),
    ("Fronts", "Over/Under/Wide 9/Bear for four-man lines, Odd/Tite/Penny for three-man lines. Bear and Tite "
     "fronts clog inside runs but are softer on the edge; a Wide 9 rushes the passer but opens inside lanes; "
     "Penny puts five on the line with one linebacker behind them so a three-safety defense can stop the run."),
    ("Special teams", "Kickoffs (deep, directional, squib, pooch, onside), returns (middle, sideline wall, wedge, "
     "reverse, return to the field side, throwback lateral), punts (spread, directional, rugby, pooch, coffin "
     "corner, and the rare third-down quick kick) and the receiving side's calls (return, wall, hold-up "
     "return that doubles both gunners, block, safe/fake-watch). Better core special-teams players and "
     "coaches win the hidden yardage."),
    ("Fakes", "Fake punts: a direct snap to the up-back, a punter pass or a punter run. Fake field goals: "
     "the holder runs or throws. Two-point tries can start from a swinging gate (the line splits out wide). "
     "A fake works when the other team isn't expecting it: a safe call or a well-coached unit usually "
     "stops it. Feature or remove each one in Tactics → Playbook."),
    ("Dynamic kickoff", "A kickoff rule the competition committee may adopt when most kickoffs end in "
     "touchbacks. Both units line up five yards apart and nobody moves until the ball lands, so returns are "
     "more like a running play than a footrace. The kick must land between the goal line and the 20: short "
     "of it the receivers get the ball at their 40, into the end zone in the air is a touchback (to the 30, "
     "or the 35 if the committee later moves it to get more kicks returned). Onside kicks must be declared, "
     "so there are no surprise onsides."),
    ("Free kicks", "After a safety the team that gave it up punts from its own 20, and it can be returned. "
     "After a fair catch, the receiving team may try a fair catch kick: a field goal kicked from the spot "
     "with no rush, used at the end of a half."),
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
     "around the league, coaches get bolder over the years. Before a two-point try the staff weighs its "
     "offense against that defense rather than a league-average chance. On higher difficulty levels CPU "
     "staffs trust the numbers more."),
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


def front_office_desc():
    """Owners, GMs, plans and coach styles (built from front_office.py so it never goes stale)."""
    import front_office as fo
    out = [("Front offices", "Every CPU club has an owner, a general manager and a head coach. The owner sets the "
            "budget and decides how long to wait; the GM has a personality and a plan for the season that drive "
            "his trades, draft board, free agency and re-signings; the coach decides who plays. See Teams → "
            "Front Offices, or the Front Office tab when you open a club."),
           ("Plans", "Each offseason, and again two weeks before the trade deadline, a GM chooses a plan from "
            "where his roster ranks, how old its core is, its quarterback, the cap and his owner's mood. Plans "
            "stick for a season or two, so a rebuild isn't abandoned after one good month. Buyers (All-In, "
            "Contend, Last Dance, Playoff Push) trade picks for veterans; sellers (Rebuild, Tank, Retool, Youth "
            "Movement, Cap Reset) do the opposite.")]
    for k, v in fo.PLANS.items():
        out.append((f"Plan: {k}", v["desc"]))
    for k, (desc, _, _) in fo.GM_ARCHETYPES.items():
        out.append((f"GM: {k}", desc))
    for k, (lo, hi, desc) in fo.TRAIT_INFO.items():
        out.append((f"GM trait: {lo} / {hi}", desc))
    out.append(("GM judgement", "Separate from his style: how accurately he sizes up players. Sharp evaluators "
                "rarely misjudge anyone; erratic ones overrate and underrate players in ways that stick for a "
                "season."))
    out.append(("Draft record and learning", "Four years after each draft, a GM's picks are compared with the "
                "players taken in the same round. He trusts positions where he has hit and is warier where he "
                "has missed. GMs also drift toward the ideas of the latest champion, and owners tend to replace "
                "a fired GM with someone unlike him, so front-office fashions come and go."))
    for k, v in fo.FOCUS_EFFECTS.items():
        out.append((f"Priority: {k}", v))
    out.append(("Trade value", "How much a club values a player in a trade, on the same scale as draft picks. It "
                "grows much faster than his rating: an average starter is worth about a third-round pick, a Pro "
                "Bowl player a high first and an elite one two firsts or more, with quarterbacks worth most. "
                "Young players add what their scouts think they can become, players past their position's "
                "prime lose value each year, and a cheap contract adds value while an expensive one takes it "
                "away."))
    out.append(("What a deal adds to the roster", "A club judges a package by what it does to its own roster. "
                "A player who would start is worth his full value, a rotation player or a prospect less, and a "
                "deep backup little. Each extra piece in a package counts for less than the one before, so "
                "several good players rarely buy a star. A club trying to win now also charges for the hole a "
                "deal leaves in this season's lineup, above all at quarterback."))
    out.append(("Scouting fog", "CPU clubs see current ratings like you do, but not potential: for other clubs' "
                "young players they have their scouts' range, read through their own scouting department, "
                "and a lean of their own inside it. They know their own players."))
    out.append(("Re-signing and extensions", "At the end of the re-signing window a CPU club works out next "
                "season's money (the deals that are ending don't count), keeps back enough for its draft picks "
                "and minimum bodies, and re-signs its players in order of how much they matter to it. It will "
                "stretch to the hard cap for a star or a cheap starter. An ambitious player on an unattractive "
                "club may turn it down and test the market. Young core players in the last year of a deal are "
                "often extended early, before a big season raises their price."))
    out.append(("Hot seat", "A GM whose last three seasons fall short of his owner's bar is on the hot seat. He "
                "trades future picks for help now and won't start a rebuild that could cost him his job."))
    out.append(("Training focus (CPU)", "Before camp every CPU staff picks a training focus for each player: young "
                "players work on the most important part of their game where they are weakest, veterans past "
                "their prime on their body to keep their speed. Good teaching staffs get it right more often. "
                "Young players with real upside get the extra playing time on a rebuilding club."))
    out.append(("Difficulty and the front office", "The Difficulty setting (CPU intelligence) also sharpens or "
                "dulls every CPU front office: a GM judges players as if his judgement were better or worse, "
                "his scouts read potential as if the department were better or worse, his plan misreads his "
                "roster less, and he weighs what a deal does to his roster more or less fully. Ratings never "
                "change."))
    for k, v in fo.OWNER_TYPES.items():
        out.append((f"Owner: {k}", v))
    for k, v in fo.POWER_TYPES.items():
        out.append((f"Power structure: {k}", v))
    out.append(("Coach styles", "A head coach's style comes from his strongest quality (Offensive or Defensive "
                "Mastermind, Teacher and Developer, Players' Coach, Game-Day Tactician, Adaptable Problem-Solver, "
                "Disciplinarian), plus his 4th-down temperament and whether he plays young players or trusts "
                "veterans. Coaches who trust youth give young players the edge on close depth-chart calls; "
                "rebuilding clubs play the kids even more."))
    return out


# ── Table columns (shown when hovering over a column header) ─────────────────

COLUMN_DESC = {
    # Players and contracts
    "OVR": "Overall: how good he is right now at his position, 1-99. 74 is an average starter, 82+ Pro Bowl, 90+ elite.",
    "POT": "Potential: the best he is likely to become (a scouted range for young players).",
    "OVR est": "Your scouts' estimate of his overall rating. More scouting narrows the error.",
    "POT est": "Your scouts' estimate of his potential. More scouting narrows the error.",
    "Overall": "Overall rating. For players 1-99 (74 = average starter); for coaches, staff and scouts, "
               "their all-round ability.",
    "Proj": "Where your scouts project him to be drafted.",
    "Scouted": "How thoroughly your scouts have seen him. Better-scouted prospects have more accurate estimates.",
    "Dev": "Development: how well this coach helps players improve.",
    "Form": "Recent form: how well he has played in the last few games compared with his ability.",
    "Morale": "Happiness, 1-100. Low morale hurts performance and makes contract talks harder.",
    "Rep": "Reputation around the league, 0-100. Famous players cost more and draw more interest.",
    "Personality": "How the staff read his character: work ethic, temperament and ambition.",
    "Archetype": "The kind of player he is at his position (for example Power Back or Slot Receiver).",
    "Arch": "The kind of player he is at his position (for example Power Back or Slot Receiver).",
    "Role": "His best role at his position and his rating in it.",
    "Best Role": "His best role at his position and his rating in it.",
    "Salary": "This season's cap hit.",
    "Yrs": "Seasons left on his contract.",
    "Market": "What he would command on the open market each season.",
    "Market Value": "What he would command on the open market each season.",
    "Value / Cost": "Market value divided by salary. Above 1.0x he is a bargain; below 0.8x he is overpaid.",
    "Asking": "What he is asking for per season.",
    "Interest": "How keen he is on your club (Keen, Open or Reluctant): whether you contend, whether he "
                "would start, your coach's reputation and your fan support.",
    "Cap Space": "Salary cap minus payroll (including dead money).",
    "Payroll": "Total cap hits this season, including dead money from released players.",
    "Age": "Age in years.",
    "40yd": "40-yard dash time at the combine (seconds; lower is faster).",
    "Bench": "Bench press reps of 225 lb at the combine.",
    "Vert": "Vertical jump at the combine (inches).",
    "Stamina": "How long he can play at full effort before he needs a rest.",
    "Slot OVR": "His rating at this depth chart slot today: the position's formula on his attributes, adjusted for "
                "his size and how well he knows the position. At his own position it is his OVR.",
    "Slot POT": "What he could become at this slot once he has learned it (a scouted range for young players).",
    "Fit": "Natural at his own position. Elsewhere (and at a position he is converting to), how well he knows "
           "the position (familiarity 0-100) and whether he is light or heavy for it.",
    "Lock": "Locked players keep their place when the depth chart is auto sorted.",
    "Busts": "Blown assignments: missed blocks, blown coverages and wrong routes by a player learning a position.",
    # Games and standings
    "GP": "Games played.",
    "GS": "Games started.",
    "W": "Wins.", "L": "Losses.", "T": "Ties.",
    "Pct": "Percentage: winning % in standings (ties count half), completion % for passers, made % for kickers.",
    "PF": "Points for.", "PA": "Points against.",
    "Diff": "Point differential: points for minus points against.",
    "Strk": "Current winning or losing streak.",
    "Div": "Division. In the standings, the record against division opponents.",
    "Conf": "Conference. In the standings, the record against conference opponents.",
    "Home": "Record at home.", "Away": "Record on the road.",
    "Pts/G": "Points per game.", "Yds/G": "Yards per game.",
    "Pass/G": "Passing yards per game.", "Rush/G": "Rushing yards per game.",
    "Y/Play": "Yards per play.",
    "TO": "Turnovers: interceptions thrown plus fumbles lost.",
    "Pen Yds": "Penalty yards.",
    "Plays": "Offensive plays run.",
    "Pass %": "Share of plays that were dropbacks (passes, sacks and scrambles).",
    "3rd %": "Third-down conversion rate.",
    "20+": "Plays that gained 20 yards or more.",
    "Win %": "Winning percentage. For pass rushers, pass-rush win rate: how often he beat his block "
             "(about 20% is average, 30%+ elite).",
    # Snaps
    "Snaps": "Plays he was on the field for.",
    "Snap %": "Share of his side's snaps he played.",
    "Off Snaps": "Offensive snaps played.", "Def Snaps": "Defensive snaps played.",
    # Passing
    "Cmp": "Completions.", "Att": "Attempts.", "Pass Att": "Pass attempts.",
    "Cmp%": "Completion percentage.", "Comp %": "Completion percentage.",
    "Yds": "Yards.", "Pass Yds": "Passing yards.", "Yards": "Yards.",
    "TD": "Touchdowns.", "Pass TD": "Passing touchdowns.",
    "Int": "Interceptions.", "INT %": "Interceptions per pass attempt.",
    "Rate": "Passer rating (the NFL formula, 0-158.3).",
    "Rating": "Passer rating (0-158.3). For a defender, the rating on throws at the receiver he covered.",
    "Y/A": "Yards per pass attempt.", "Lng": "Longest play.", "Pass Lng": "Longest completion.",
    "Sck": "Times sacked.", "Sack %": "Share of dropbacks that ended in a sack.",
    "Dropbacks": "Pass attempts plus sacks plus scrambles: every time the quarterback dropped back to pass.",
    "aDOT": "Average depth of target: how far past the line of scrimmage his passes (or targets) travel.",
    "CAY/Cmp": "Completed air yards per completion: how far the ball travelled in the air on catches.",
    "Pressured": "Dropbacks where the rush got home before the throw.",
    "Pressure %": "Share of dropbacks where he was pressured.",
    "Time to Throw": "Average seconds from snap to throw.",
    "Checkdown %": "Share of throws to the checkdown (short safety-valve) option.",
    "Tight Window %": "Share of throws into tight coverage, where the receiver was not open.",
    "Throwaways": "Passes thrown away to avoid a sack.",
    "Hot Reads": "Times he spotted a blitz before the snap and set a hot route to beat it.",
    # Rushing
    "Rush Att": "Rushing attempts.", "Rush Yds": "Rushing yards.",
    "Rushes": "Rushing attempts. For pass rushers, the number of pass-rush reps.",
    "Rush Avg": "Yards per carry.", "Rush TD": "Rushing touchdowns.", "Rush Lng": "Longest run.",
    "Y/C": "Yards per carry.",
    "YBC/Att": "Yards before contact per carry: room created by the blocking.",
    "YAC/Att": "Yards after contact per carry: what the runner created himself.",
    "Fum": "Fumbles.",
    # Receiving
    "Rec": "Receptions.", "Tgt": "Targets: passes thrown his way.",
    "Tgt Share": "Share of the team's targets that went to him.",
    "Catch%": "Receptions per target.", "Drop": "Dropped passes.",
    "Y/Tgt": "Yards per target.", "YAC": "Yards after the catch.", "YAC/Rec": "Yards after the catch per reception.",
    "1st Dn": "Plays that gained a first down or a touchdown.",
    # EPA
    "EPA": "Expected points added: how much his plays changed his team's expected points (see Glossary).",
    "Total EPA": "Expected points added over the season.",
    "EPA / play": "Average expected points added per play. Around 0 is average.",
    "EPA/Att": "Expected points added per attempt.", "EPA/DB": "Expected points added per dropback.",
    "EPA/Tgt": "Expected points added per target.", "Pass EPA/DB": "Passing EPA per dropback.",
    "Off EPA/Play": "Offensive EPA per play (higher is better).",
    "Def EPA/Play": "EPA allowed per play by the defense (lower is better).",
    "Net EPA/Play": "Offensive EPA per play minus defensive EPA per play.",
    "Success": "Share of plays with positive EPA. Good offenses are above 50%.",
    "Off Success": "Offensive success rate (share of plays with positive EPA).",
    "Def Success": "Success rate allowed by the defense (lower is better).",
    # Line play
    "Pass Pro": "Pass-blocking reps.",
    "Press. Allowed": "Pressures charged to this blocker.",
    "Pressure% Allowed": "Share of his pass-blocking reps that he lost for a pressure.",
    "Hits Allowed": "Quarterback hits charged to this blocker.", "Sacks Allowed": "Sacks charged to this blocker.",
    "Run Blocks": "Run-blocking reps at the point of attack.",
    "Run Win %": "Share of run-blocking reps he won.",
    "Pancakes": "Dominant run-block wins that put the defender on the ground.",
    "Pressures": "Times he pressured the quarterback (sacks, hits and hurries).",
    "Pressure% Made": "Share of his pass-rush reps that produced a pressure.",
    "Double-teamed": "Share of his pass-rush reps where two blockers took him.",
    "Run Stop Win %": "Share of run-defense reps where he beat his blocker.",
    "QB Hits": "Hits on the quarterback as he threw.", "QBH": "Hits on the quarterback as he threw.",
    # Defense
    "Tkl": "Total tackles.", "Solo": "Solo tackles.", "Ast": "Assisted tackles.",
    "TFL": "Tackles for loss.", "Sacks": "Sacks.", "FF": "Forced fumbles.", "FR": "Fumble recoveries.",
    "PD": "Passes defended (broken up or intercepted).",
    "Stops": "Tackles that ended a play as a failure for the offense (negative EPA).",
    "Missed": "Missed tackles (charged when a whiff let the play go for a big gain).",
    "Miss %": "Missed tackles as a share of tackle attempts (tackles plus misses).",
    "ST Tkl": "Special-teams tackles.",
    # Kicking and returns
    "FGM": "Field goals made.", "FGA": "Field goals attempted.", "FG %": "Field goal percentage.",
    "0-39": "Field goals made / attempted from under 40 yards.",
    "40-49": "Field goals made / attempted from 40-49 yards.",
    "50+": "Field goals made / attempted from 50+ yards.",
    "XPM": "Extra points made.", "XPA": "Extra points attempted.",
    "Punts": "Punts.", "Avg": "Average yards per carry, catch, punt or return.",
    "In20": "Punts downed inside the opponent's 20.", "TB": "Touchbacks.",
    "KR": "Kickoff returns.", "KR Yds": "Kickoff return yards.", "KR TD": "Kickoff return touchdowns.",
    "PR": "Punt returns.", "PR Yds": "Punt return yards.", "PR TD": "Punt return touchdowns.",
    # Grades, staff and front offices
    "Grade": "Game grade, 0-100: how well he did his job compared with an average player at his position. "
             "90+ elite, 70-79 above average, 60-69 average, under 50 poor.",
    "Teaching": "How well this coach develops players.",
    "Motivation": "How well this coach keeps players' morale and effort up.",
    "Judge Ability": "How accurately this scout or coach rates a player's current ability.",
    "Judge Potential": "How accurately this scout or coach projects a player's potential.",
    "Plan": "The club's plan for this season (All-In, Contend, Rebuild, Tank and so on).",
    "GM Style": "The general manager's personality, which shapes his trades, drafts and signings.",
    "Owner patience": "How long the owner gives the front office before firing people.",
    "Confidence": "The owner's confidence in the general manager, 0-100%.",
    "QB pipe": "Talent pipeline: how strong the incoming generation of quarterbacks is in this league.",
    "RB pipe": "Talent pipeline: how strong the incoming generation of running backs is in this league.",
    "WR pipe": "Talent pipeline: how strong the incoming generation of receivers is in this league.",
    "DB pipe": "Talent pipeline: how strong the incoming generation of defensive backs is in this league.",
}


def column_tip(label):
    """Hover text for a table column header, or '' if there is none."""
    if label in COLUMN_DESC:
        return COLUMN_DESC[label]
    from ratings import ATTRIBUTES
    hits = [(name, ATTRIBUTE_DESC.get(k, "")) for k, (name, abbr, _g) in ATTRIBUTES.items() if abbr == label]
    return "  /  ".join(f"{name}: {desc}" for name, desc in hits)


# ── Settings (shown when hovering over a setting) ─────────────────────────────

SETTING_DESC = {
    "theme": "Dark or light colours.",
    "accent": "The highlight colour used for buttons and headings.",
    "font_size": "Base text size in points.",
    "table_density": "Row height in tables.",
    "show_ca_number": "Show ratings as numbers, or as tier names (Elite, Pro Bowl, Starter...).",
    "show_pa_number": "Show your scouts' potential estimates.",
    "show_archetype": "Show each player's archetype in tables.",
    "show_hidden_stats": "Reveal hidden traits such as work rate and big-game temperament (normally only hinted at).",
    "color_attributes": "Colour attribute values from poor (red) to elite (green).",
    "highlight_player_team": "Highlight your club's rows in league tables.",
    "home_field_advantage": "Whether playing at home helps at all.",
    "home_field_strength": "How much home field helps. 1.0 is about the NFL's real edge.",
    "game_randomness": "How much the better team's edge is diluted by luck on game day.",
    "turnover_rate": "Scales interceptions and fumbles.",
    "sack_rate": "Scales how often pressure ends in a sack.",
    "big_play_rate": "Scales the chance of long runs and deep completions.",
    "penalty_rate": "Scales how often flags are thrown.",
    "fg_accuracy": "Scales every kicker's range and accuracy.",
    "pat_distance": "Where the extra point is kicked from (33 yards in the NFL since 2015).",
    "fourth_down_aggression": "How willing coaches are to go for it on fourth down. Coaches still drift with results.",
    "weather": "Wind, rain, snow, heat and cold affect passing, kicking, fumbles and fatigue.",
    "momentum": "How much big plays swing the next few plays.",
    "streakiness": "How much players run hot and cold between games.",
    "injury_rate": "Scales how often players get hurt.",
    "injury_severity": "Scales how long injuries last.",
    "pass_tendency": "Shifts every coach's pass/run balance. Above 1 means more passing.",
    "pace": "Scales the number of plays per game.",
    "completion_rate": "Scales completion percentage.",
    "run_efficiency": "Scales yards per carry.",
    "fatigue_rate": "How quickly players tire during a game.",
    "fatigue_effect": "How much tiredness hurts performance.",
    "playoff_teams": "Playoff teams from each conference.",
    "overtime_rules": "Modern: both teams get a possession, then the next score wins (10-minute period in the regular season). Sudden death: the first score wins. Full period: the whole overtime period is played.",
    "salary_cap": "The league's salary cap this season.",
    "cap_growth": "How much the salary cap rises each season.",
    "hard_cap": "Clubs can't go over the cap to sign or trade for players.",
    "roster_size": "Active roster limit in the regular season.",
    "trade_deadline_week": "No trades after this week of the regular season.",
    "practice_squad_size": "Players each club can keep on the practice squad.",
    "growth_rate": "How fast young players improve.",
    "decline_rate": "How fast veterans decline.",
    "breakout_rate": "How often players develop far faster than expected.",
    "bust_rate": "How often promising players stall.",
    "retirement_age_shift": "Players retire this many years later (positive) or earlier (negative).",
    "draft_class_strength": "Overall talent of each draft class.",
    "ai_trade_willingness": "How readily CPU clubs trade with each other and with you. Lower makes them demand more.",
    "ai_fa_aggression": "How hard CPU clubs spend in free agency.",
    "coach_hot_seat": "How quickly owners fire head coaches.",
    "gm_hot_seat": "How quickly owners fire CPU general managers.",
    "ai_personality_strength": "How different CPU front offices are. 0 makes them all alike.",
    "holdout_rate": "How often underpaid stars hold out (normally 0-3 a season).",
    "cpu_intelligence": "Difficulty. How well CPU staffs scout, game-plan, adjust during games and make 4th-down "
                        "and clock decisions, and how well CPU front offices judge players, plan and trade: "
                        "0.5 Rookie, 1.0 Pro (realistic), 1.5 All-Pro, 2.0 Hall of Fame. "
                        "Player ratings are never changed; your own staff always works at the Pro level.",
    "watch_games": "Open the live viewer for your games when you press Continue.",
    "sim_stop_injury": "Multi-week sims stop when one of your starters is hurt for 3+ weeks.",
    "sim_stop_offer": "Multi-week sims stop when a club makes you a trade offer.",
    "watch_speed": "Speed of the live game viewer.",
    "gm_can_be_fired": "Whether your owner can fire you.",
    "auto_roster_moves": "Your staff handle injured reserve and the practice squad.",
    "autosave": "Save automatically after each week.",
    "autosave_slots": "How many autosaves to keep.",
    "confirm_actions": "Ask before releasing or trading players.",
}

# Settings whose effect shows up in a league average: key -> (average, label, format, NFL reference)
SETTING_READINGS = {
    "turnover_rate": ("turnovers", "turnovers per team-game", "{:.2f}", "about 1.3"),
    "sack_rate": ("sack_rate", "% of dropbacks end in a sack", "{:.1f}", "about 6.8"),
    "penalty_rate": ("penalties", "accepted penalties per team-game", "{:.1f}", "about 6"),
    "fg_accuracy": ("fg_pct", "% of field goals made", "{:.1f}", "about 85"),
    "pass_tendency": ("pass_rate", "% of plays are dropbacks", "{:.1f}", "about 59"),
    "pace": ("plays", "plays per team-game", "{:.1f}", "about 63"),
    "completion_rate": ("comp_pct", "% completions", "{:.1f}", "about 64"),
    "run_efficiency": ("ypc", "yards per carry", "{:.2f}", "about 4.3"),
    "big_play_rate": ("ypa", "yards per pass attempt", "{:.2f}", "about 7.0"),
    "pat_distance": ("xp_pct", "% of extra points made", "{:.1f}", "about 95"),
    "home_field_strength": ("home_win", "% of games won by the home team", "{:.1f}", "about 55"),
    "injury_rate": ("injuries", "injuries per team-game", "{:.2f}", None),
    "fourth_down_aggression": ("fourth_att", "4th-down attempts per team-game", "{:.2f}", "about 1.6"),
}


def league_readings(lg):
    """League averages behind SETTING_READINGS: this regular season once 4+ weeks are played,
    otherwise last season's. Returns (averages dict, 'this season' / 'last season' / '')."""
    from eras import season_averages
    games = [g for w in sorted(lg.results) for g in lg.results[w]] if getattr(lg, "results", None) else []
    if len(games) >= 4 * max(1, len(lg.teams) // 2):
        avg = dict(season_averages(games))
        n = 2 * len(games)
        xpa = sum(line.get("xpa", 0) for g in games for line in g.player_stats.values())
        xpm = sum(line.get("xpm", 0) for g in games for line in g.player_stats.values())
        if xpa:
            avg["xp_pct"] = 100.0 * xpm / xpa
        avg["home_win"] = 100.0 * sum(1 for g in games if g.home_score > g.away_score) / len(games)
        avg["injuries"] = sum(len(g.injuries) for g in games) / n
        avg["fourth_att"] = sum(g.team_stats[a]["fourth_att"] for g in games for a in (g.home, g.away)) / n
        return avg, "this season"
    if lg.history and lg.history[-1].get("averages"):
        return dict(lg.history[-1]["averages"]), "last season"
    return {}, ""


def setting_reading(key, avgs, when):
    """One line showing how a slider's effect looks in this league, or ''."""
    spec = SETTING_READINGS.get(key)
    if not spec or spec[0] not in avgs:
        return ""
    stat, label, fmt, nfl = spec
    sep = "" if label.startswith("%") else " "
    out = f"{when.capitalize()}: {fmt.format(avgs[stat])}{sep}{label}"
    return out + (f" (NFL {nfl})" if nfl else "")
