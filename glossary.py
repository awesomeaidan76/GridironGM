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
