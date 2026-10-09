"""
season.py — the flow of a league year.

Phases, in order:
  regular      18 weeks (17 games + bye)
  playoffs     one round per Continue
  season_end   awards are out; retirements are announced on Continue
  resign       re-sign your expiring players (AI teams decide on Continue)
  draft        pick when you're on the clock
  free_agency  sign free agents; AI teams sign in waves on Continue
  preseason    training camp & development; Continue starts the new season
"""
import math
import random
from collections import Counter

import awards as awards_mod
import records as records_mod
import negotiation as nego
import draft as draft_mod
import committee
import staff as staff_mod
import roster_rules as rr
import eras
import front_office as fo
import free_agency as fa
from coach import hire_from_tree, generate_coach
from development import develop, retirement_chance
from engine import simulate_game
from injuries import apply_lasting_damage
from schedule import build_schedule
from settings import settings
from stats import merge, fantasy_like_value, summary_line
from team import TACTIC_SLIDERS
from trades import ai_trade_market

PHASES = ["regular", "playoffs", "season_end", "resign", "draft", "free_agency", "preseason"]

PHASE_TITLES = {
    "regular": "Regular Season", "playoffs": "Playoffs", "season_end": "Season Review",
    "resign": "Re-signing Period", "draft": "Draft", "free_agency": "Free Agency",
    "preseason": "Training Camp",
}


def continue_label(lg):
    ph = lg.phase
    if ph == "regular":
        return f"Play Week {lg.week + 1}"
    if ph == "playoffs":
        return f"Play {playoff_round_name(lg)}"
    return {
        "season_end": "Continue to Re-signing",
        "resign": "Continue to the Draft",
        "draft": "Finish the Draft",
        "free_agency": "Continue to Training Camp",
        "preseason": f"Start the {lg.year + 1} Season",
    }[ph]


# ── New season ────────────────────────────────────────────────────────────────

def default_tactics():
    return {k: 50 for k in TACTIC_SLIDERS}


def start_new_season(lg, first=False):
    if not first:
        last = lg.year
        lg.year += 1
        lg.salary_cap = int(lg.salary_cap * (1.0 + settings["cap_growth"]))
        drafted_now = lambda p: p.draft and p.draft.get("year") == last and p.years_pro == 0
        for team in lg.teams.values():
            for p in team.roster:
                if not drafted_now(p):
                    p.age += 1
                    old, new, note = develop(p, team, last_season=last)
                    _development_news(lg, p, team, old, new, note)
                _offseason_heal(p)
        for p in lg.free_agents:
            p.age += 1
            develop(p, None, last_season=last)
            _offseason_heal(p)
        for c in [t.coach for t in lg.teams.values()] + lg.coach_pool:
            c.age += 1
        # AI rosters must be legal
        for team in lg.teams.values():
            if team.abbr == lg.user_abbr:
                continue
            fa.ai_cutdown(lg, team, settings["roster_size"])
            fa.ai_fill_minimums(lg, team)
        user = lg.user_team
        if user is not None:
            over = fa.active_count(user) - settings["roster_size"]
            if over > 0:
                before = {p.id for p in user.roster}
                fa.ai_cutdown(lg, user, settings["roster_size"])
                cut = [p for p in lg.free_agents if p.id in before]
                lg.add_news("Roster", f"Final cuts: released {', '.join(p.name for p in cut)} "
                                      f"to get down to {settings['roster_size']}.", user.abbr)
            fa.ai_fill_minimums(lg, user)
        for team in lg.teams.values():
            if team.abbr != lg.user_abbr or settings["auto_roster_moves"]:
                rr.ai_build_practice_squad(lg, team)
        fa.trim_free_agent_pool(lg)

    for team in lg.teams.values():
        rr.clear_ir(team)
        team.dead_cap = 0
        for p in team.roster:
            p.season_stats = Counter()
            p.playoff_stats = Counter()
            p.game_log = []
            p.morale = int(p.morale * 0.6 + 65 * 0.4)
    for p in lg.free_agents:
        p.season_stats = Counter()
        p.playoff_stats = Counter()
        p.game_log = []

    lg.reset_standings()
    lg.results = {}
    lg.playoff_results = {}
    lg.playoff_seeds = {}
    lg.playoff_alive = {}
    lg.playoff_round = 0
    lg.playoff_exit = {}
    lg.champion = None
    lg.awards_this_season = {}
    ranks = lg.last_ranks or {a: i % 4 for i, a in enumerate(lg.teams)}
    lg.schedule = build_schedule(lg.structure, lg.year, ranks)
    lg.week = 0
    lg.phase = "regular"
    lg.fa_wave = 0
    lg.expiring = []
    user = lg.user_team
    if user is not None and user.tactics is None:
        user.tactics = default_tactics()
    staff_mod.ensure_league(lg)
    fo.ensure(lg)
    staff_mod.set_expectation(lg)
    # Next spring's draft class plays its college season now; scouts watch it all year
    draft_mod.generate_class(lg)
    lg.add_news("League", f"The {lg.year} season is underway.")
    exp = lg.gm.get("expectation") if user is not None else None
    if exp:
        lg.add_news("Front Office", f"Owner {user.owner.name}'s goal for {lg.year}: "
                                    f"{exp['label'].lower()}.", user.abbr)


def _offseason_heal(p):
    if p.injury:
        p.injury["weeks"] = p.injury.get("weeks", 0) - 26
        if p.injury["weeks"] <= 0:
            p.injury = None


def _development_news(lg, p, team, old, new, note):
    from ratings import ovr_from_ca
    if team.abbr != lg.user_abbr and new < 155:
        return
    o_old, o_new = ovr_from_ca(old, p.position), ovr_from_ca(new, p.position)
    if note == "breakout":
        lg.add_news("Development", f"{p.name} ({p.position}, {team.abbr}) had a breakout "
                                   f"offseason: {o_old} → {o_new} OVR", team.abbr)
    elif note == "bust" and team.abbr == lg.user_abbr:
        lg.add_news("Development", f"Scouts are worried {p.name} ({p.position}) has hit "
                                   f"his ceiling.", team.abbr)
    elif team.abbr == lg.user_abbr and abs(new - old) >= 8:
        verb = "improved" if new > old else "declined"
        lg.add_news("Development", f"{p.name} ({p.position}) {verb} in camp: "
                                   f"{o_old} → {o_new} OVR", team.abbr)


# ── Regular season ────────────────────────────────────────────────────────────

def play_week(lg):
    if lg.phase != "regular" or lg.week >= len(lg.schedule):
        return []
    results = []
    for home, away in lg.schedule[lg.week]:
        res = simulate_game(lg.teams[home], lg.teams[away], week=lg.week + 1, season=lg.year,
                            rules=lg.rules, diagrams=lg.user_abbr in (home, away))
        lg.record_game(res)
        _apply_game(lg, res, playoff=False)
        results.append(res)
    lg.results[lg.week] = results
    _post_week(lg, results)
    lg.week += 1
    if lg.week >= len(lg.schedule):
        begin_playoffs(lg)
    return results


def _apply_game(lg, res, playoff):
    for text in records_mod.update_game_records(lg, res)[:2]:
        lg.add_news("Performance", text, None)
    lookup = {}
    for abbr in (res.home, res.away):
        for p in lg.teams[abbr].roster:
            lookup[p.id] = p
    for abbr in (res.home, res.away):
        opp = res.opponent(abbr)
        mine, theirs = res.score_of(abbr), res.score_of(opp)
        outcome = "W" if mine > theirs else "L" if mine < theirs else "T"
        result = f"{outcome} {mine}-{theirs}" + (" OT" if res.overtime else "")
        wk = res.playoff or f"Wk {res.week}"
        for p in lg.teams[abbr].roster:
            line = res.player_stats.get(p.id)
            if line is None:
                continue
            merge(p.playoff_stats if playoff else p.season_stats, line)
            p.game_log.append((wk, opp, abbr == res.home, result, Counter(line)))
    for pid, name, abbr, inj_name, weeks in res.injuries:
        p = lookup.get(pid)
        if p is None or p.injury is None:
            continue
        p.injury["new"] = True
        p.injury_history.append((lg.year, inj_name, weeks))
        changes = apply_lasting_damage(p, p.injury)
        if weeks >= 1 and (abbr == lg.user_abbr or p.ca >= 150):
            out = "out for the season" if p.injury.get("season_ending") or weeks > 17 \
                else f"out {weeks} week{'s' if weeks != 1 else ''}"
            lg.add_news("Injury", f"{p.name} ({p.position}, {abbr}) — {inj_name}, {out}", abbr)
        if changes and abbr == lg.user_abbr:
            lg.add_news("Injury", f"The medical staff fear {p.name}'s {inj_name.lower()} "
                                  f"will cost him some athleticism.", abbr)


def _post_week(lg, results):
    # Injury clock
    for team in lg.teams.values():
        for p in team.roster:
            inj = p.injury
            if not inj:
                continue
            if inj.pop("new", False):
                if inj["weeks"] <= 0:
                    p.injury = None
                continue
            inj["weeks"] -= 1
            if inj["weeks"] <= 0:
                p.injury = None
                if team.abbr == lg.user_abbr and p.ca >= 110:
                    lg.add_news("Injury", f"{p.name} ({p.position}) has been cleared to play.",
                                team.abbr)

    # Morale
    for res in results:
        for abbr in (res.home, res.away):
            won = res.winner == abbr
            lost = res.winner is not None and not won
            team = lg.teams[abbr]
            starters = res.starters
            for p in team.roster:
                d = (2 if won else -2 if lost else 0)
                if p.id in starters:
                    d += 1
                elif p.ca >= 130 and not p.is_injured:
                    d -= 2          # good player not playing
                temper = p.hidden.get("temperament", 50)
                d *= 1.3 - temper / 100.0 * 0.6
                p.morale = int(max(1, min(100, p.morale + d + (65 - p.morale) * 0.05)))

    _performance_news(lg, results)
    nego.weekly_holdouts(lg)
    for yr, wk, award, pid, name, pos, abbr, text in awards_mod.player_of_the_week(lg, results):
        if abbr == lg.user_abbr or award.startswith("Offensive"):
            lg.add_news("Awards", f"{award} (week {wk + 1}): {name} ({pos}, {abbr}) — {text}", abbr)
    if lg.week + 1 == 9:
        _midseason_development(lg)
    staff_mod.weekly_scouting(lg)
    if lg.user_abbr:
        mine = next((r for r in results if lg.user_abbr in (r.home, r.away)), None)
        staff_mod.weekly_confidence(lg, mine)
    fa.in_season_moves(lg)
    import market
    market.weekly(lg)
    for team in lg.teams.values():
        if team.abbr == lg.user_abbr:
            continue
        if fa.active_count(team) > settings["roster_size"]:
            fa.ai_cutdown(lg, team, settings["roster_size"])
        elif fa.active_count(team) < settings["roster_size"]:
            rr.fill_active_roster(lg, team)


def _performance_news(lg, results):
    items = []
    for res in results:
        for pid, line in res.player_stats.items():
            name, pos, abbr, _ = res.player_meta[pid]
            score = 0
            text = None
            if line["pass_yds"] >= 360 or line["pass_td"] >= 4:
                score = line["pass_yds"] / 4 + line["pass_td"] * 25
                text = f"{name} threw for {line['pass_yds']} yards and {line['pass_td']} TD"
            elif line["rush_yds"] >= 150:
                score = line["rush_yds"]
                text = f"{name} ran for {line['rush_yds']} yards"
            elif line["rec_yds"] >= 150:
                score = line["rec_yds"]
                text = f"{name} caught {line['rec']} passes for {line['rec_yds']} yards"
            elif line["sacks"] >= 3:
                score = line["sacks"] * 50
                text = f"{name} recorded {line['sacks']:g} sacks"
            elif line["def_int"] >= 2:
                score = line["def_int"] * 70
                text = f"{name} intercepted {line['def_int']} passes"
            if text:
                opp = res.opponent(abbr)
                items.append((score + (500 if abbr == lg.user_abbr else 0),
                              f"{text} ({abbr} vs {opp}, {res.summary()})", abbr))
    items.sort(reverse=True)
    for _, text, abbr in items[:4]:
        lg.add_news("Performance", text, abbr)


# ── Playoffs ──────────────────────────────────────────────────────────────────

def begin_playoffs(lg):
    n = settings["playoff_teams"]
    lg.phase = "playoffs"
    lg.playoff_round = 0
    lg.playoff_exit = {a: -1 for a in lg.teams}
    lg.playoff_seeds = {}
    lg.playoff_alive = {}
    for conf in lg.structure:
        seeds = lg.conference_seeds(conf, n)
        lg.playoff_seeds[conf] = seeds
        lg.playoff_alive[conf] = list(seeds)
        for a in seeds:
            lg.playoff_exit[a] = 0
            lg.teams[a].playoff_apps += 1
    user = lg.user_abbr
    if user:
        made = any(user in s for s in lg.playoff_seeds.values())
        seed = next((s.index(user) + 1 for s in lg.playoff_seeds.values() if user in s), None)
        lg.add_news("League", f"The playoff field is set." + (
            f" {lg.teams[user].full_name} are the #{seed} seed." if made else
            f" {lg.teams[user].full_name} missed the playoffs."), user)


def playoff_round_name(lg):
    alive = [len(v) for v in lg.playoff_alive.values()]
    if all(a <= 1 for a in alive):
        return "Championship Game"
    remaining = max(1, math.ceil(math.log2(max(alive))))
    names = {1: "Conference Championship", 2: "Divisional Round", 3: "Wild Card Round"}
    return names.get(remaining, "Wild Card Round")


def _seed_index(lg, abbr):
    for conf, seeds in lg.playoff_seeds.items():
        if abbr in seeds:
            return seeds.index(abbr)
    return 99


def play_playoff_round(lg):
    if lg.phase != "playoffs":
        return []
    name = playoff_round_name(lg)
    results = []
    if name == "Championship Game":
        finalists = [v[0] for v in lg.playoff_alive.values() if v]
        a, b = finalists[0], finalists[1]
        home, away = (a, b) if lg.standings[a].sort_key() >= lg.standings[b].sort_key() else (b, a)
        res = simulate_game(lg.teams[home], lg.teams[away], week=99, season=lg.year,
                            playoff=name, neutral=True, rules=lg.rules,
                            diagrams=lg.user_abbr in (home, away))
        _apply_game(lg, res, playoff=True)
        results.append(res)
        lg.playoff_results[name] = results
        champ = res.winner
        runner = res.loser
        lg.champion = champ
        lg.playoff_exit[champ] = 9
        lg.playoff_exit[runner] = 8
        lg.teams[champ].titles += 1
        lg.teams[champ].coach.titles += 1
        lg.add_news("Championship", f"The {lg.teams[champ].full_name} are {lg.year} champions! "
                                    f"({res.summary()})", champ)
        for p in lg.teams[champ].roster:
            p.awards.append((lg.year, "Champion"))
            p.reputation = min(100, p.reputation + 3)
        end_season(lg)
        return results

    lg.playoff_round += 1
    for conf, alive in lg.playoff_alive.items():
        alive.sort(key=lambda a: _seed_index(lg, a))
        count = len(alive)
        if count <= 1:
            continue
        pow2 = 1 << (count.bit_length() - 1)
        playing = alive if count == pow2 else alive[count - 2 * (count - pow2):]
        pairs = [(playing[i], playing[-1 - i]) for i in range(len(playing) // 2)]
        for hi, lo in pairs:
            res = simulate_game(lg.teams[hi], lg.teams[lo], week=90 + lg.playoff_round,
                                season=lg.year, playoff=name, rules=lg.rules,
                                diagrams=lg.user_abbr in (hi, lo))
            _apply_game(lg, res, playoff=True)
            results.append(res)
            loser = res.loser
            alive.remove(loser)
            lg.playoff_exit[loser] = lg.playoff_round
            if name == "Conference Championship":
                lg.teams[res.winner].conf_titles += 1
        _post_playoff_injuries(lg)
    lg.playoff_results[name] = results
    if lg.user_abbr:
        for res in results:
            if lg.user_abbr in (res.home, res.away):
                won = res.winner == lg.user_abbr
                lg.add_news("Playoffs", f"{name}: {res.summary()} — "
                                        f"{'advance!' if won else 'season over.'}", lg.user_abbr)
    return results


def _post_playoff_injuries(lg):
    for team in lg.teams.values():
        for p in team.roster:
            if p.injury:
                if p.injury.pop("new", False):
                    if p.injury["weeks"] <= 0:
                        p.injury = None
                    continue
                p.injury["weeks"] -= 1
                if p.injury["weeks"] <= 0:
                    p.injury = None


# ── End of season ─────────────────────────────────────────────────────────────

def end_season(lg):
    year = lg.year
    regular = [g for w in sorted(lg.results) for g in lg.results[w]]
    avgs = eras.season_averages(regular)
    lg.season_trends[year] = avgs

    aw = awards_mod.compute(lg)
    awards_mod.apply(lg, aw)
    lg.awards_this_season = aw

    # Division titles & last-season ranks (for next year's schedule)
    for conf, divs in lg.structure.items():
        for div in divs:
            ds = lg.division_standings(conf, div)
            lg.teams[ds[0].abbr].division_titles += 1
            for i, r in enumerate(ds):
                lg.last_ranks[r.abbr] = i

    # League leaders for the history book
    leaders = {}
    players = [(p, t) for t in lg.teams.values() for p in t.roster]
    for key, label in [("pass_yds", "Passing Yards"), ("pass_td", "Passing TD"),
                       ("rush_yds", "Rushing Yards"), ("rush_td", "Rushing TD"),
                       ("rec", "Receptions"), ("rec_yds", "Receiving Yards"),
                       ("rec_td", "Receiving TD"), ("sacks", "Sacks"),
                       ("def_int", "Interceptions")]:
        if players:
            p, t = max(players, key=lambda pt: pt[0].season_stats[key])
            leaders[label] = (p.name, t.abbr, p.season_stats[key], p.id)

    best = max(lg.standings.values(), key=lambda r: r.sort_key())
    runner = next((a for a, v in lg.playoff_exit.items() if v == 8), None)
    entry = {
        "year": year,
        "champion": lg.champion,
        "runner_up": runner,
        "best_record": (best.abbr, best.wlt()),
        "awards": aw,
        "averages": avgs,
        "era": eras.era_label(avgs),
        "leaders": leaders,
        "standings": {a: (r.w, r.l, r.t, r.pf, r.pa) for a, r in lg.standings.items()},
        "pipeline": dict(lg.pipeline),
        "schemes": Counter(t.coach.off_scheme for t in lg.teams.values()),
    }
    lg.history.append(entry)

    # Team & coach histories
    for team in lg.teams.values():
        rec = lg.standings[team.abbr]
        ex = lg.playoff_exit.get(team.abbr, -1)
        result = {-1: "Missed playoffs", 0: "Lost Wild Card", 1: "Lost Wild Card",
                  2: "Lost Divisional", 3: "Lost Conference", 8: "Lost Championship",
                  9: "Champions"}.get(ex, "Playoffs")
        if ex in (1, 2, 3):
            n_rounds = lg.playoff_round
            result = {n_rounds - 2: "Lost Wild Card", n_rounds - 1: "Lost Divisional",
                      n_rounds: "Lost Conference"}.get(ex, "Playoffs")
        team.history.append({"year": year, "w": rec.w, "l": rec.l, "t": rec.t,
                             "pf": rec.pf, "pa": rec.pa, "result": result,
                             "coach": team.coach.name, "exit": ex})
        c = team.coach
        c.career_wins += rec.w
        c.career_losses += rec.l
        c.career_ties += rec.t
        c.seasons += 1
        c.team_seasons += 1
        c.history.append((year, team.abbr, rec.w, rec.l, rec.t, result))
        c.reputation = int(max(1, min(100, c.reputation + (rec.pct - 0.5) * 12
                                      + (6 if ex >= 2 else 0) + (10 if ex == 9 else 0))))

    # Archive player seasons
    for team in lg.teams.values():
        for p in team.roster:
            _archive(lg, p, team.abbr)
    for p in lg.free_agents:
        if p.season_stats["gp"] or p.playoff_stats["gp"]:
            _archive(lg, p, "FA")
        p.last_season_gp = p.season_stats["gp"]
        p.last_season_gs = p.season_stats["gs"]

    _update_reputations(lg)
    fo.season_end(lg)
    _coaching_carousel(lg)

    _season_evaluations(lg)

    # Contracts tick down
    lg.expiring = []
    for team in lg.teams.values():
        for p in team.roster:
            if p.contract:
                nego.tick(p.contract)
                p.contract["years"] -= 1
                if p.contract["years"] <= 0:
                    lg.expiring.append(p.id)
                    p.contract_year = lg.year

    rr.season_end_ps(lg)
    for team in lg.teams.values():
        rr.clear_ir(team)
    rr.prune_old(lg)
    fo.update_plans(lg)
    eras.evolve(lg)
    committee.record_season_injuries(lg, regular)
    committee.review(lg)
    if not lg.draft_class:
        draft_mod.generate_class(lg)
    staff_mod.combine_bump(lg)
    draft_mod.compute_order(lg)
    staff_mod.staff_offseason(lg)
    lg.gm_review = staff_mod.season_review(lg)
    lg.phase = "season_end"


def _season_evaluations(lg):
    """
    How well each player produced relative to his ability this season, as
    percentiles within his position. Feeds development (outplaying your
    rating builds confidence and earns reps; underperforming does the opposite).
    """
    from awards import off_score, def_score, position_score
    from stats import total_tackles  # noqa: F401  (kept for clarity of def_score inputs)
    team_ol = {}
    for t in lg.teams.values():
        ts = [g.team_stats[t.abbr] for g in lg.team_results(t.abbr)]
        att = sum(x["rush_att"] for x in ts) or 1
        drop = sum(x["pass_att"] + x["sacked"] for x in ts) or 1
        team_ol[t.abbr] = sum(x["rush_yds"] for x in ts) / att * 10 - sum(x["sacked"] for x in ts) / drop * 120
    groups = {}
    for t in lg.teams.values():
        for p in t.roster:
            s = p.season_stats
            if s["gp"] < 4:
                continue
            if p.position in ("OT", "IOL", "FB"):
                prod = team_ol[t.abbr] * (0.4 + 0.6 * min(1.0, s["gs"] / 12.0))
            elif p.position in ("K", "P"):
                prod = position_score(p, lg) - p.ca * 0.2
            elif p.position in ("DT", "EDGE", "LB", "CB", "S"):
                prod = def_score(s)
            else:
                prod = off_score(s, p.position)
            groups.setdefault(p.position, []).append((p, prod))
    for pos, items in groups.items():
        n = len(items)
        if n < 3:
            continue
        by_prod = sorted(items, key=lambda x: x[1])
        by_ca = sorted(items, key=lambda x: x[0].ca)
        rank_p = {id(x[0]): i / (n - 1) for i, x in enumerate(by_prod)}
        rank_c = {id(x[0]): i / (n - 1) for i, x in enumerate(by_ca)}
        for p, _ in items:
            p.season_eval = {"year": lg.year, "prod_pct": rank_p[id(p)], "ca_pct": rank_c[id(p)]}


def _midseason_development(lg):
    from development import midseason
    for team in lg.teams.values():
        for p in team.roster:
            d = midseason(p, team, lg.year)
            if d and team.abbr == lg.user_abbr and abs(d) >= 3:
                from ratings import ovr_from_ca
                verb = "has taken a step forward" if d > 0 else "has regressed"
                lg.add_news("Development", f"{p.name} ({p.position}) {verb} at mid-season "
                                           f"(now {p.ovr} OVR).", team.abbr)


def _archive(lg, p, abbr):
    s = p.season_stats
    p.career[lg.year] = {"team": abbr, "stats": Counter(s), "playoffs": Counter(p.playoff_stats),
                         "ca": p.ca, "age": p.age}
    p.ca_history[lg.year] = p.ca
    p.last_season_gp = s["gp"]
    p.last_season_gs = s["gs"]
    p.years_pro += 1


def _update_reputations(lg):
    by_pos = {}
    for t in lg.teams.values():
        for p in t.roster:
            by_pos.setdefault(p.position, []).append(p)
    for pos, group in by_pos.items():
        scored = sorted(group, key=lambda p: awards_mod.position_score(p, lg), reverse=True)
        n = len(scored)
        for i, p in enumerate(scored):
            pct = 1.0 - i / max(1, n - 1)
            delta = (pct - 0.55) * 10
            if p.season_stats["gp"] < 4:
                delta -= 3
            p.reputation = int(max(1, min(100, p.reputation * 0.93 + delta + p.ca * 0.035)))
    for p in lg.free_agents:
        p.reputation = int(max(1, p.reputation * 0.85))


def _coaching_carousel(lg):
    hot = settings["coach_hot_seat"]
    # Recent success leaders: their trees supply new coaches
    def recent_pct(t):
        h = t.history[-3:]
        g = sum(x["w"] + x["l"] + x["t"] for x in h)
        return sum(x["w"] + 0.5 * x["t"] for x in h) / g if g else 0.5
    elite = sorted(lg.teams.values(), key=lambda t: -(recent_pct(t) + t.titles * 0.02))[:8]

    for team in lg.teams.values():
        if team.abbr == lg.user_abbr:
            continue
        c = team.coach
        rec = lg.standings[team.abbr]
        recent_playoffs = sum(1 for h in team.history[-3:] if h["exit"] >= 0)
        p_fire = 0.0
        if rec.pct < 0.30 and c.team_seasons >= 2:
            p_fire = 0.65
        elif rec.pct < 0.42 and c.team_seasons >= 3 and recent_playoffs == 0:
            p_fire = 0.45
        elif rec.pct < 0.50 and c.team_seasons >= 5 and recent_playoffs == 0:
            p_fire = 0.30
        p_fire *= hot * fo.owner_coach_patience(team)
        g = fo.gm_of(team)
        new_gm = g is not None and g.seasons == 0 and c.team_seasons >= 1 and random.random() < 0.30 * hot
        if new_gm:
            p_fire = 1.0                 # the new general manager brings in his own coach
        retiring = c.age >= 68 or (c.age >= 63 and random.random() < 0.3)
        if not retiring and random.random() >= p_fire:
            continue
        if retiring:
            lg.add_news("Coaching", f"{team.full_name} head coach {c.name} retires "
                                    f"({c.record_str} career).", team.abbr)
        else:
            why = f" New GM {g.name} wants his own man." if new_gm else ""
            lg.add_news("Coaching", f"{team.full_name} fire head coach {c.name} after a "
                                    f"{rec.wlt()} season.{why}", team.abbr)
            c.team_seasons = 0
            if c.age < 64:
                lg.coach_pool.append(c)
        team.coach = hire_coach(lg, team, elite)

    lg.coach_pool = sorted(lg.coach_pool, key=lambda c: -c.overall)[:20]


def innovator_coach(lg):
    """
    A coach whose ideas counter whatever the league is doing. When everyone
    throws, defenses go two-high and light boxes invite the run game back;
    when everyone runs, offenses that spread it out find space.
    """
    from coach import OFFENSIVE_SCHEMES, DEFENSIVE_SCHEMES
    coaches = [t.coach for t in lg.teams.values()]
    two_high = sum(c.tendencies.get("two_high", 0.5) for c in coaches) / len(coaches)
    last = lg.history[-1]["averages"] if lg.history and lg.history[-1].get("averages") else {}
    pass_rate = last.get("pass_rate", 57.0)
    off_w = {k: 1.0 for k in OFFENSIVE_SCHEMES}
    off_w.update({"Wing-T": 0.3, "Flexbone": 0.2})
    if two_high > 0.55:
        for k in ("Zone Run", "Power Run", "Pistol"):
            off_w[k] = 3.0
        off_w["Wing-T"], off_w["Flexbone"] = 0.8, 0.5
    elif two_high < 0.42:
        for k in ("Air Coryell", "Run and Shoot", "Air Raid"):
            off_w[k] = 2.5
    def_w = {k: 1.0 for k in DEFENSIVE_SCHEMES}
    if pass_rate > 59.5:
        for k in ("Two-High Match", "Tampa 2", "Cover 3"):
            def_w[k] = 3.0
    elif pass_rate < 53:
        for k in ("46 Blitz", "4-3 Over", "Press Man"):
            def_w[k] = 3.0
    c = generate_coach(quality=random.uniform(10, 15))
    c.age = random.randint(34, 48)
    c.off_scheme = random.choices(list(off_w), weights=list(off_w.values()))[0]
    c.def_scheme = random.choices(list(def_w), weights=list(def_w.values()))[0]
    c.set_tendencies()
    return c


def hire_coach(lg, team, elite=None):
    """
    The club interviews a slate of candidates - an up-and-coming innovator, a
    disciple of a winning coach (or a hot coordinator), a retread from the
    pool, a first-timer - and the GM picks the one who best fits his plan and
    philosophy (a rebuild wants a teacher who plays young players, a contender
    a proven game-day coach, an analytics GM an aggressive 4th-down caller).
    """
    if elite is None:
        elite = sorted(lg.teams.values(), key=lambda t: -lg.standings[t.abbr].pct)[:8]
    slate = []                       # (coach, how, prior, kind, extra)
    slate.append((innovator_coach(lg), "an up-and-coming innovator", 0.25, "innovator", None))
    src = random.choice([t for t in elite if t is not team] or elite)
    tree = hire_from_tree(src.coach, src.abbr)
    tree.tendencies["aggression"] = max(0.0, min(1.0, src.coach.tendencies.get(
        "aggression", 0.5) + random.gauss(0, 0.1)))
    slate.append((tree, f"from the {src.coach.name} coaching tree ({src.abbr}, {src.coach.off_scheme})",
                  0.22, "tree", None))
    if random.random() < 0.5:
        promo = staff_mod.peek_coordinator(lg, team)
        if promo is not None:
            psrc, m = promo
            pc = hire_from_tree(psrc.coach, psrc.abbr)
            pc.name, pc.age = m.name, m.age
            side = "offense" if m.role == "OC" else "defense"
            pc.ratings[side] = max(pc.ratings[side], m.r("tactics"))
            pc.ratings["development"] = m.r("teaching")
            pc.ratings["motivation"] = m.r("motivation")
            slate.append((pc, f"promoted from {psrc.abbr} {m.title.lower()} ({psrc.coach.off_scheme} tree)",
                          0.22, "promo", promo))
    if lg.coach_pool:
        best = max(lg.coach_pool, key=lambda c: c.overall + c.reputation / 10 + random.uniform(0, 3))
        slate.append((best, f"(previously {best.record_str})", 0.10, "pool", None))
    first = generate_coach(quality=random.uniform(8, 14))
    first.age = random.randint(35, 52)
    slate.append((first, "a first-time head coach", 0.12, "first", None))

    def score(entry):
        coach, _, prior, _, _ = entry
        return fo.coach_fit(lg, team, coach) + prior * 10 + random.gauss(0, 1.6)
    new, how, _, kind, extra = max(slate, key=score)
    if kind == "pool":
        lg.coach_pool.remove(new)
    elif kind == "promo":
        staff_mod.take_coordinator(lg, *extra)
    new.team_seasons = 0
    fo.coach_youth_trust(new)
    lg.add_news("Coaching", f"{team.full_name} hire {new.name} as head coach — {how}. "
                            f"Scheme: {new.off_scheme} / {new.def_scheme}. {fo.coach_style(new)}.", team.abbr)
    return new


# ── Offseason ─────────────────────────────────────────────────────────────────

def process_retirements(lg):
    retired_now = []
    for team in lg.teams.values():
        for p in list(team.roster):
            if p.id in lg.expiring and p.age >= 30:
                chance = retirement_chance(p) * 1.15
            else:
                chance = retirement_chance(p)
            if random.random() < chance:
                team.remove_player(p)
                _retire(lg, p, team.abbr)
                retired_now.append((p, team.abbr))
    for p in list(lg.free_agents):
        if random.random() < retirement_chance(p, unsigned=True):
            lg.free_agents.remove(p)
            _retire(lg, p, None)
            retired_now.append((p, None))
    lg.expiring = [pid for pid in lg.expiring if lg.find_player(pid) and
                   not lg.find_player(pid).retired]
    return retired_now


def hof_score(p):
    score = 0.0
    for yr, award in p.awards:
        score += {"MVP": 25, "Offensive Player of the Year": 12,
                  "Defensive Player of the Year": 12, "All-Pro": 8,
                  "Offensive Rookie of the Year": 3, "Defensive Rookie of the Year": 3,
                  "Champion": 2}.get(award, 0)
    tot = Counter()
    for season in p.career.values():
        tot.update(season["stats"])
    score += tot["pass_yds"] / 1000 * 1.0 + tot["pass_td"] * 0.15
    score += tot["rush_yds"] / 1000 * 3.0 + tot["rush_td"] * 0.3
    score += tot["rec_yds"] / 1000 * 2.6 + tot["rec_td"] * 0.3
    score += tot["sacks"] * 0.45 + tot["def_int"] * 0.8 + tot["ff"] * 0.4
    score += tot["fgm"] * 0.06
    return score


def _retire(lg, p, abbr):
    p.retired = True
    p.retired_year = lg.year
    p.contract = None
    p.team = None
    p.game_log = []
    p.injury = None
    games = sum(s["stats"]["gp"] for s in p.career.values())
    hof = hof_score(p)
    if hof >= 62:
        p.hall_of_fame = True
        lg.hall_of_fame.append((lg.year, p))
        lg.add_news("Hall of Fame", f"{p.name} ({p.position}) retires as a Hall of Famer "
                                    f"after {len(p.career)} seasons.", abbr)
    if games >= 24 or p.awards or p.hall_of_fame:
        lg.retired.append(p)
        if p.reputation >= 55 or abbr == lg.user_abbr:
            if not p.hall_of_fame:
                lg.add_news("Retirement", f"{p.name} ({p.position}{', ' + abbr if abbr else ''}) "
                                          f"retires after {len(p.career)} seasons.", abbr)
    if len(lg.retired) > 4000:
        lg.retired.sort(key=lambda x: -(hof_score(x) + len(x.career)))
        lg.retired = lg.retired[:3000]


def finalize_resign(lg):
    """End of the re-signing window: AI teams decide; unsigned players hit the market."""
    rr.ai_tags(lg)
    for team in lg.teams.values():
        if team.abbr == lg.user_abbr:
            for p in list(team.roster):
                if p.contract and p.contract["years"] <= 0:
                    team.remove_player(p)
                    p.contract = None
                    p.fa_origin = (team.abbr, lg.year)
                    lg.free_agents.append(p)
                    lg.add_transaction(f"{p.position} {p.name} left {team.abbr} in free agency")
        else:
            fa.ai_resign(lg, team)
    lg.expiring = []


def fa_next_wave(lg):
    if lg.phase != "free_agency":
        return 0
    lg.fa_wave += 1
    import market
    market.offseason(lg, "free_agency")
    return fa.ai_free_agency_wave(lg, max_signings={1: 5, 2: 4}.get(lg.fa_wave, 3))


# ── The Continue button ───────────────────────────────────────────────────────

def advance(lg):
    """Move the league forward one step. Returns a short description."""
    msg = _advance(lg)
    shortlist_alerts(lg)
    return msg


def _advance(lg):
    ph = lg.phase
    if ph == "regular":
        wk = lg.week + 1
        play_week(lg)
        return f"Week {wk} complete."
    if ph == "playoffs":
        name = playoff_round_name(lg)
        play_playoff_round(lg)
        return f"{name} complete."
    if ph == "season_end":
        retired = process_retirements(lg)
        lg.phase = "resign"
        import market
        market.offseason(lg, "resign")
        return f"{len(retired)} players retired. Re-signing window is open."
    if ph == "resign":
        finalize_resign(lg)
        lg.phase = "draft"
        import market
        market.offseason(lg, "draft")
        lg.add_news("Draft", f"The {lg.year + 1} draft is about to begin.")
        return "Re-signing window closed. Draft day!"
    if ph == "draft":
        draft_mod.finish_draft(lg)
        lg.phase = "free_agency"
        lg.fa_wave = 0
        fa_next_wave(lg)
        return "Draft complete. Free agency is open."
    if ph == "free_agency":
        while lg.fa_wave < 4:
            fa_next_wave(lg)
        for team in lg.teams.values():
            if team.abbr != lg.user_abbr:
                fa.ai_fill_minimums(lg, team)
        lg.phase = "preseason"
        lg.negotiations = {}
        held = nego.start_holdouts(lg)
        mine = [p for t, p in held if t.abbr == lg.user_abbr]
        if mine:
            return ("Free agency winds down. Training camp opens — " +
                    ", ".join(p.name for p in mine) + " is holding out for a new contract.")
        return "Free agency winds down. Training camp opens."
    if ph == "preseason":
        start_new_season(lg)
        return f"The {lg.year} season begins."
    return ""


# ── Quality of life: shortlist alerts and sim stop conditions ────────────────

def shortlist_alerts(lg):
    """News for the user when a shortlisted player changes team, hits free agency or gets hurt."""
    ids = getattr(lg, "shortlist", None) or []
    if not ids:
        return
    state = getattr(lg, "shortlist_state", None) or {}
    by_id = {p.id: p for p in lg.all_players(include_fa=True)}
    user = lg.user_abbr
    for pid in list(ids):
        p = by_id.get(pid)
        if p is None:
            ids.remove(pid)
            state.pop(pid, None)
            continue
        now = (p.team, bool(p.injury and p.injury.get("weeks", 0) >= 2))
        before = state.get(pid)
        if before is not None and before != now:
            if before[0] != now[0]:
                if now[0] is None:
                    lg.add_news("Shortlist", f"{p.position} {p.name} (OVR {p.ovr}) is now a free agent.", user)
                elif now[0] == user:
                    pass
                else:
                    lg.add_news("Shortlist", f"{p.position} {p.name} has moved to {lg.teams[now[0]].full_name}.",
                                user)
            elif now[1] and not before[1]:
                lg.add_news("Shortlist", f"{p.position} {p.name} is injured ({p.injury['name']}, "
                                         f"{p.injury['weeks']} weeks).", user)
        state[pid] = now
    lg.shortlist_state = state


def toggle_shortlist(lg, pid):
    ids = getattr(lg, "shortlist", None)
    if ids is None:
        ids = lg.shortlist = []
    if pid in ids:
        ids.remove(pid)
        return False
    ids.append(pid)
    shortlist_alerts(lg)
    return True


def sim_snapshot(lg):
    """What a multi-week sim watches so it can stop when something needs the user."""
    team = lg.user_team
    hurt = set()
    if team is not None:
        for pos, players in team.starters().items():
            hurt.update(p.id for p in players)
    return {"offers": len(getattr(lg, "trade_offers", []) or []), "starters": hurt}


def sim_stop_reason(lg, snap):
    """Text explaining why a multi-week sim should stop now, or None."""
    team = lg.user_team
    if team is None:
        return None
    if settings["sim_stop_offer"] and len(getattr(lg, "trade_offers", []) or []) > snap["offers"]:
        o = lg.trade_offers[-1]
        return f"Stopped: {lg.teams[o['from']].full_name} have made you a trade offer (see Trades)."
    if settings["sim_stop_injury"]:
        for p in team.roster:
            if p.id in snap["starters"] and p.injury and p.injury.get("weeks", 0) >= 3:
                return f"Stopped: starter {p.position} {p.name} is out ({p.injury['name']}, {p.injury['weeks']} weeks)."
    return None


def sim_to(lg, target, callback=None):
    """
    target: 'week:N', 'end_regular', 'end_playoffs', 'draft', 'next_season'
    """
    guard = 0
    while guard < 200:
        guard += 1
        ph = lg.phase
        if target.startswith("week:") and ph == "regular" and lg.week >= int(target[5:]) - 1:
            break
        if target == "end_regular" and ph != "regular":
            break
        if target == "end_playoffs" and ph not in ("regular", "playoffs"):
            break
        if target == "draft" and ph == "draft":
            break
        if target == "next_season" and ph == "regular" and lg.week == 0 and guard > 1:
            break
        if ph == "draft" and target != "next_season":
            break
        advance(lg)
        if callback:
            callback(lg)
