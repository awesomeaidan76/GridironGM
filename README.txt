GRIDIRON GM  (version 5)
========================

HOW TO PLAY
1. Unzip into a new folder. To keep your careers, copy the "saves" folder from
   your previous version into this one (older saves load fine).
2. Double-click Play.bat. The first launch installs PyQt6 (about a minute).

NEW IN VERSION 5
 Fatigue and substitutions
   - Every player tires during a game. Linemen and pass rushers tire fastest,
     quarterbacks barely at all. The sideline and halftime bring them back.
     Tired players lose speed, strength and technique and get hurt more often.
     Stamina finally matters at every position. Heat and no-huddle offenses
     (which stop the defense substituting) wear players down faster.
   - Coaches rotate on every snap when a fresher backup is the better option.
     Typical game: starting DTs play about 65-80% of snaps, edge rushers 80-90%,
     corners and safeties nearly all of them, the lead back about 75%.
   - Depth Chart: stamina and snap % columns, and a rotation setting for each
     group (none / light / normal / heavy).
   - Blowouts: late in the 4th quarter the backups (and the backup QB) play.
   - Snap counts are tracked for every player (box scores, profiles).
 Defense
   - New Game Plan screen (My Club > Game Plan): a scouting report on this
     week's opponent, your coordinator's read, and your own calls: shadow
     corner, bracket their top target, QB spy, box count, pressure and shell.
   - AI coordinators scout every opponent the same way. Better coordinators
     read it right; poor ones over- or under-react.
   - Halftime (and quarter-break) adjustments for both coordinators, shown in
     the play-by-play.
   - Call report: EPA and success rate for each coverage, pressure, front, and
     for your own pass concepts and runs, all season.
   - New defensive stats: stops, missed tackles (League Stats > Tackling).
 Ratings
   - The bottom of the scale is softened: fringe players now read in the 40s
     instead of the 20s and 30s. Average and elite ratings are unchanged.
 Settings
   - Match Engine, League, Development and AI settings are now saved with each
     league (like ZenGM). New sliders: pass/run lean, pace of play, completion
     rate, rushing efficiency, fatigue build-up, fatigue effect, holdouts.
     1.0 is the realistic baseline.
 Contracts
   - Holdouts are rarer: 0-3 a season league-wide.

CONTROLS
   Continue = Ctrl+Space. Save = Ctrl+S. Sim menu jumps further ahead.
   Game menu: Save As, Load, Export League to JSON, Settings.

FILES
   saves\               careers, autosaves and JSON exports
   playbooks\           your custom plays (JSON) - see docs\PLAYBOOK_FORMAT.md
   settings.json        default settings for new leagues
   gridiron_errors.log  only appears if something goes wrong - send it to me
   docs\                ARCHITECTURE.md (for the Unreal/C++ port), PLAYBOOK_FORMAT.md
   tools\               calibration scripts comparing the sim with NFL numbers
