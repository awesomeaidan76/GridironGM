"""Calibration harness: simulate many games between freshly generated teams and
print league averages vs NFL targets.

    python tools/calibrate.py [games] [seed]
"""
import os, sys, random, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from league import League, TEAM_DATA
from team import Team
from worldgen import build_roster, make_coach, assign_initial_contracts
from eras import archetype_weights_for, random_landscape, season_averages
from engine import simulate_game
from collections import Counter

TARGETS = {"ppg": (21, 23.5), "pass_att": (31, 35), "comp_pct": (61, 66), "pass_yds": (215, 240),
           "ypa": (6.7, 7.3), "pass_td": (1.3, 1.65), "int_rate": (2.0, 2.7), "sack_rate": (6, 7.5),
           "rush_att": (25.5, 29), "rush_yds": (110, 125), "ypc": (4.1, 4.5), "rush_td": (0.75, 0.98),
           "pass_rate": (56, 61), "fg_pct": (82, 88), "punt_avg": (44, 48), "plays": (61, 66),
           "third_pct": (37, 42), "turnovers": (1.1, 1.5)}


def make_league(seed=1):
    random.seed(seed)
    preset = random_landscape()
    lg = League("t", "calibration")
    lg.pipeline = dict(preset["pipeline"])
    lg.archetype_weights = archetype_weights_for(preset)
    teams = []
    for conf, divs in TEAM_DATA.items():
        for div, ts in divs.items():
            for abbr, city, nick, colors in ts:
                t = Team(abbr, city, nick, conf, div, colors)
                t.coach = make_coach(preset)
                build_roster(t, random.gauss(0, 6), "", lg)
                assign_initial_contracts(t, 255_000_000, 2026)
                teams.append(t)
    return teams


def run(games=400, seed=1, quiet=False):
    teams = make_league(seed)
    res = []
    t0 = time.time()
    home_w = 0; ties = 0
    for i in range(games):
        h, a = random.sample(teams, 2)
        r = simulate_game(h, a, keep_pbp=False)
        res.append(r)
        for t in (h, a):
            for p in t.roster:
                p.injury = None
            t.refresh_depth() if hasattr(t, "refresh_depth") else None
        if r.home_score > r.away_score: home_w += 1
        elif r.home_score == r.away_score: ties += 1
    dt = time.time() - t0
    avg = season_averages(res)
    if quiet:
        return avg
    tot = Counter()
    for r in res:
        for ab in (r.home, r.away):
            tot.update(r.team_stats[ab])
    n = 2 * len(res)
    inj = sum(len(r.injuries) for r in res) / n
    print(f"seed {seed}: {games} games in {dt:.1f}s ({dt/games*1000:.0f} ms/game) "
          f"home win {home_w/games:.3f} ties {ties}")
    for k, v in avg.items():
        t = TARGETS.get(k)
        flag = ""
        if t: flag = "  OK" if t[0] <= v <= t[1] else f"  <-- target {t}"
        print(f"  {k:12s} {v:8.2f}{flag}")
    print(f"  injuries/team-game {inj:.2f}  penalties {tot['penalties']/n:.1f} for {tot['pen_yds']/n:.0f}  "
          f"TO {tot['turnovers']/n:.2f}  rz {tot['rz_td']/max(1,tot['rz_trips'])*100:.0f}%  "
          f"4th att {tot['fourth_att']/n:.2f} conv {tot['fourth_conv']/max(1,tot['fourth_att'])*100:.0f}%  "
          f"punts {tot['punts']/n:.2f} drives {tot['drives']/n:.1f} top {tot['top']/n/60:.1f}m")
    return avg


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 400, int(sys.argv[2]) if len(sys.argv) > 2 else 1)
