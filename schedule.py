"""
schedule.py — NFL-style 17-game, 18-week schedule.

Each team plays:
  6  division games (home and away vs. each rival)
  4  vs. a rotating division in its own conference
  4  vs. a rotating division in the other conference
  2  vs. same-place finishers from the other two divisions in its conference
  1  vs. a same-place finisher from another division in the other conference
Week 18 is all divisional games and every team gets one bye (weeks 5-14).
"""
import random


def build_matchups(structure, year, ranks):
    """
    structure: {conf: {div: [abbr, ...]}}  (2 conferences x 4 divisions x 4)
    ranks:     {abbr: finishing place in division last season, 0-3}
    Returns a list of (team_a, team_b, is_division) pairs (home not set).
    """
    confs = list(structure.keys())
    divs = {c: list(structure[c].keys()) for c in confs}
    by_rank = {}
    for c in confs:
        for d in divs[c]:
            teams = sorted(structure[c][d], key=lambda a: ranks.get(a, 0))
            for r, a in enumerate(teams):
                by_rank[(c, d, r)] = a

    games = []
    # Division: home and away
    for c in confs:
        for d in divs[c]:
            t = structure[c][d]
            for i in range(4):
                for j in range(i + 1, 4):
                    games.append((t[i], t[j], True))
                    games.append((t[j], t[i], True))

    intra_pairs = [[(0, 1), (2, 3)], [(0, 2), (1, 3)], [(0, 3), (1, 2)]][year % 3]
    for c in confs:
        for a, b in intra_pairs:
            for x in structure[c][divs[c][a]]:
                for y in structure[c][divs[c][b]]:
                    games.append((x, y, False))
        # Same-place games vs the two unpaired divisions
        for a, b in [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]:
            if (a, b) in intra_pairs:
                continue
            for r in range(4):
                games.append((by_rank[(c, divs[c][a], r)], by_rank[(c, divs[c][b], r)], False))

    c0, c1 = confs
    shift = year % 4
    for d in range(4):
        e = (d + shift) % 4
        for x in structure[c0][divs[c0][d]]:
            for y in structure[c1][divs[c1][e]]:
                games.append((x, y, False))
        # 17th game: same-place vs another division
        f = (d + shift + 2) % 4
        for r in range(4):
            games.append((by_rank[(c0, divs[c0][d], r)], by_rank[(c1, divs[c1][f], r)], False))
    return games


def assign_home(games, year):
    """Division games already have home/away; balance the rest."""
    home_count = {}
    out = []
    for a, b, div in games:
        if div:
            out.append((a, b, True))
            home_count[a] = home_count.get(a, 0) + 1
    rest = [g for g in games if not g[2]]
    random.shuffle(rest)
    for a, b, _ in rest:
        ha, hb = home_count.get(a, 0), home_count.get(b, 0)
        if ha < hb or (ha == hb and random.random() < 0.5):
            home, away = a, b
        else:
            home, away = b, a
        home_count[home] = home_count.get(home, 0) + 1
        out.append((home, away, False))
    # Repair pass: flip games until every team has 8 or 9 home games
    for _ in range(2000):
        hi = [t for t, n in home_count.items() if n > 9]
        lo = [t for t, n in home_count.items() if n < 8]
        if not hi and not lo:
            break
        flipped = False
        for i, (h, a, div) in enumerate(out):
            if div:
                continue
            if (h in hi and home_count[a] < 9) or (a in lo and home_count[h] > 8):
                out[i] = (a, h, False)
                home_count[h] -= 1
                home_count[a] = home_count.get(a, 0) + 1
                flipped = True
                break
        if not flipped:
            break
    return out


def _matching(teams, edges_by_team, rng, max_steps=4000):
    """Find a perfect matching of `teams` using remaining games (backtracking)."""
    steps = [0]

    def solve(unmatched, chosen):
        if not unmatched:
            return list(chosen)
        steps[0] += 1
        if steps[0] > max_steps:
            return None
        # Team with the fewest options first
        best = None
        best_opts = None
        for t in unmatched:
            opts = [g for g in edges_by_team[t]
                    if (g[0] == t and g[1] in unmatched) or (g[1] == t and g[0] in unmatched)]
            if best is None or len(opts) < len(best_opts):
                best, best_opts = t, opts
                if len(opts) <= 1:
                    break
        if not best_opts:
            return None
        rng.shuffle(best_opts)
        for g in best_opts:
            other = g[1] if g[0] == best else g[0]
            nxt = unmatched - {best, other}
            chosen.append(g)
            res = solve(nxt, chosen)
            if res is not None:
                return res
            chosen.pop()
        return None

    return solve(frozenset(teams), [])


def build_schedule(structure, year, ranks, weeks=18, attempts=200):
    teams = [a for c in structure.values() for d in c.values() for a in d]
    games = assign_home(build_matchups(structure, year, ranks), year)
    rng = random.Random(year * 7919 + len(teams))

    for _ in range(attempts):
        remaining = list(games)
        sched = [None] * weeks
        # Week 18: division games only
        div_games = [g for g in remaining if g[2]]
        by_team = {t: [g for g in div_games if t in g[:2]] for t in teams}
        last = _matching(teams, by_team, rng)
        if last is None:
            continue
        for g in last:
            remaining.remove(g)
        sched[weeks - 1] = last

        # Byes: weeks 5-14, even number of teams per week
        bye_sizes = [2, 4, 4, 4, 2, 4, 4, 2, 4, 2]
        order = list(teams)
        rng.shuffle(order)
        byes = {}
        i = 0
        for w, n in zip(range(4, 14), bye_sizes):
            for t in order[i:i + n]:
                byes[t] = w
            i += n

        ok = True
        for w in range(weeks - 1):
            active = [t for t in teams if byes.get(t) != w]
            by_team = {t: [g for g in remaining if t in g[:2]] for t in active}
            m = _matching(active, by_team, rng)
            if m is None:
                ok = False
                break
            for g in m:
                remaining.remove(g)
            sched[w] = m
        if ok and not remaining:
            return [[(h, a) for h, a, _ in wk] for wk in sched]
    # Fallback (should be very rare): simple random pairings
    sched = []
    for w in range(weeks):
        order = list(teams)
        rng.shuffle(order)
        sched.append([(order[i], order[i + 1]) for i in range(0, len(order), 2)])
    return sched
