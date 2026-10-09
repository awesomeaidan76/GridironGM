# Roadmap: quality-of-life and depth features

This list comes from researching what players praise, and what they ask for, in Football Manager,
Out of the Park Baseball, Front Office Football, ZenGM (Football and Basketball GM), Madden
Franchise, NBA 2K MyLeague/MyGM, Draft Day Sports, Pro Strategy Football and Motorsport Manager
(October 2026). Status: ✅ done · 🔜 next · 💡 later (most belong in the Unity port's UI).

## Done in version 7
- ✅ **Shortlist.** Star a player from his profile. The Players screen has a "My shortlist" filter, and
  you get news alerts when a shortlisted player changes team, becomes a free agent or gets hurt
  (as in OOTP and FM watch lists).
- ✅ **Player comparison.** Two players side by side: ratings, contract, season line, grade and every
  attribute his position uses (as in ZenGM's Compare Players and FM's comparison view).
- ✅ **Sim stop conditions.** Multi-week sims stop when one of your starters is hurt for 3+ weeks or a
  club makes you an offer. Both can be switched off in Settings. There is also a new "Sim to the
  trade deadline" option (as in OOTP's alert-and-stop sim and ZenGM's "until" targets).
- ✅ **Visible CPU front offices.** Every club's plan, GM, owner and coach style can be seen, with
  news that explains why moves happen. Players' most common complaint about football GM games is
  CPU rosters that don't make sense.

## Next (Python, small)
- ✅ **Actionable inbox / to-do.** A new Inbox screen (with a count in the sidebar and a
  "Needs a Decision" card on Home) groups trade offers, holdouts, expiring deals, extension
  candidates, injured-reserve candidates, positions short of healthy starters, roster and cap
  limits and draft picks apart from news, with buttons to act on each inline (as in FM27's inbox
  redesign). Logic lives in `inbox.py`.
- 🔜 **Persistent table state.** Keep sort, filters and scroll position per screen, plus back and
  forward navigation (the top complaints about FM26).
- 🔜 **Trading block.** List players and ask every club for offers, with a "what would make this
  work?" button and filters by asset type (ZenGM).
- 🔜 **Multi-year cap planner.** Committed money by year, dead money, expiring players and
  "what if I extend him" (OOTP, FOF8).
- 🔜 **Glossary hover tooltips.** Show glossary text when hovering over column headers and
  settings sliders, with the league average next to each slider (BBGM reviews).

## Later (mostly the Unity port)
- 💡 Delegation per task: let staff handle the depth chart, re-signings, the practice squad or the
  draft (OOTP, FM). Delegation has to be trustworthy, or it forces players to micromanage.
- 💡 Commissioner mode: edit players, teams, schedule and rules. Expansion, relocation and
  realignment; custom draft classes (ZenGM God Mode, Pro Strategy Football).
- 💡 League export and import as plain JSON, real-player import and historical seasons (OOTP,
  ZenGM). A JSON export already exists and is the basis for this.
- 💡 Mock drafts, a deeper combine, scout disagreement and confidence levels in scouting reports.
- 💡 Injury recovery shown as a range, and load-management choices (Madden 26's Wear & Tear).
- 💡 Emergent storylines: rivalries from close games and playoff rematches, revenge games, coaching
  trees, a weekly recap show.
- 💡 Roles beyond GM: play as head coach or coordinator; apply for jobs; coordinators leaving for
  head-coaching jobs (this already happens for the CPU).
- 💡 Achievements and scenarios ("rebuild this club in 3 years"), owner directives.
- 💡 Accessibility: remappable shortcuts, colourblind palettes, UI scaling, a density setting.
- 💡 UI patterns for the port:
  - full panels instead of pop-ups;
  - menus that land on content;
  - bookmarks;
  - context action strips;
  - right-click actions on every player name;
  - multi-row bulk actions;
  - swappable dashboard tiles;
  - desktop-first density.

## CPU front offices: further ideas
- Contract structures by GM: front-loading, back-loading, void years, and extending a star early
  before the market resets.
- Trade grudges and partners: GMs remember who fleeced them.
- An empirical draft-pick value chart fitted from the league's own draft history, which each GM
  blends with the "market" chart according to his analytics and risk traits.
- Positional value fitted from the engine itself (wins added per OVR point at each position),
  re-estimated as rules change.
- Practice-squad poaching and waiver claims driven by GM style.
