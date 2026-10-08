"""Simulate many full seasons headlessly to test stability and era drift."""
import os, sys, time, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from worldgen import new_league
from season import advance, PHASES
import draft as draft_mod
from eras import era_label

def run(seasons=3, era=None, seed=7, user="DAL", verbose=True):
    t0 = time.time()
    kw = {"user_abbr": user, "seed": seed}
    lg = new_league(**kw)
    if verbose: print(f"created in {time.time()-t0:.1f}s, year {lg.year}")
    for s in range(seasons):
        ts = time.time()
        start_year = lg.year
        while True:
            if lg.phase == "draft":
                # user auto-picks via finish_draft
                pass
            advance(lg)
            if lg.phase == "regular" and lg.week == 0:
                break
        h = lg.history[-1]
        a = h["averages"]
        n_players = sum(len(t.roster) for t in lg.teams.values())
        if verbose:
            aw = h["awards"].get("MVP") or {}
            print(f"{h['year']} {time.time()-ts:5.1f}s champ {h['champion']} MVP {aw.get('name')} ({aw.get('pos')}) "
                  f"| ppg {a['ppg']:.1f} pass% {a['pass_rate']:.1f} cmp {a['comp_pct']:.1f} ypa {a['ypa']:.2f} "
                  f"ypc {a['ypc']:.2f} int {a['int_rate']:.2f} fg {a['fg_pct']:.1f} | {h['era']} "
                  f"| rosters {n_players} FA {len(lg.free_agents)} ret {len(lg.retired)} "
                  f"| pipe QB {lg.pipeline['QB']:+.1f} RB {lg.pipeline['RB']:+.1f} WR {lg.pipeline['WR']:+.1f}")
    return lg

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    run(n, seed=seed)
