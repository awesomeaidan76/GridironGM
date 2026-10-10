"""
league.py — the League: teams, standings, schedule, history and news.

Season flow (what happens when you press Continue) lives in season.py.
"""
from collections import Counter

from settings import settings

# Fictional league (the user's original franchises)
TEAM_DATA = {
    "AFC": {
        "North": [("DET", "Detroit", "Ironclad", ("#3a4a5c", "#c0c8d0")),
                  ("MIN", "Minneapolis", "Glaciers", ("#2f6fa8", "#d8ecf8")),
                  ("PIT", "Pittsburgh", "Steelworks", ("#2b2b2b", "#f2b70f")),
                  ("CLE", "Cleveland", "Blizzard", ("#5a7d9a", "#ffffff"))],
        "South": [("HOU", "Houston", "Marshals", ("#7a1f2b", "#d9b56a")),
                  ("NOL", "New Orleans", "Bayou Kings", ("#4b2a6b", "#e0c060")),
                  ("MIA", "Miami", "Herons", ("#1aa3a3", "#f28c38")),
                  ("JAX", "Jacksonville", "Cannons", ("#1d3557", "#e63946"))],
        "East": [("PHI", "Philadelphia", "Liberty", ("#0b5d3b", "#c9a227")),
                 ("NYS", "New York", "Sentinels", ("#14213d", "#fca311")),
                 ("BOS", "Boston", "Minutemen", ("#8b1e2d", "#1f3a5f")),
                 ("WAS", "Washington", "Monuments", ("#5c4033", "#e8d8b0"))],
        "West": [("DAL", "Dallas", "Wranglers", ("#1c3f7a", "#b8c4d6")),
                 ("LVG", "Las Vegas", "Dust Devils", ("#c4702a", "#2d2d2d")),
                 ("LAC", "Los Angeles", "Condors", ("#d4a017", "#1b1b3a")),
                 ("DEN", "Denver", "Prospectors", ("#d35400", "#123a5a"))],
    },
    "NFC": {
        "North": [("CHI", "Chicago", "Voyagers", ("#16284f", "#d95d1e")),
                  ("GBY", "Green Bay", "Timberwolves", ("#2e4d2c", "#e8c547")),
                  ("MIL", "Milwaukee", "Iron Range", ("#6d6d6d", "#b5322d")),
                  ("IND", "Indianapolis", "Northmen", ("#1e4fa3", "#e6e6e6"))],
        "South": [("NAS", "Nashville", "Cavalry", ("#24305e", "#c7362f")),
                  ("ATL", "Atlanta", "Copperheads", ("#b5651d", "#1a1a1a")),
                  ("CHA", "Charlotte", "Panthers", ("#00a3d9", "#111111")),
                  ("TAM", "Tampa Bay", "Pelicans", ("#d1495b", "#00798c"))],
        "East": [("NWK", "Newark", "Giants", ("#1f3c88", "#d62828")),
                 ("BAL", "Baltimore", "Capitals", ("#3d2c8d", "#e9c46a")),
                 ("RIC", "Richmond", "Colonials", ("#264653", "#e76f51")),
                 ("BUF", "Buffalo", "Express", ("#0d47a1", "#e53935"))],
        "West": [("SFO", "San Francisco", "Redwoods", ("#7b2d26", "#d4af37")),
                 ("SEA", "Seattle", "Surge", ("#1b4965", "#62b6cb")),
                 ("PHX", "Phoenix", "Desert Hawks", ("#a63d40", "#e9b872")),
                 ("SDG", "San Diego", "Pacifica", ("#0081a7", "#fed9b7"))],
    },
}


class Record:
    def __init__(self, abbr):
        self.abbr = abbr
        self.w = self.l = self.t = 0
        self.pf = self.pa = 0
        self.div_w = self.div_l = self.div_t = 0
        self.conf_w = self.conf_l = self.conf_t = 0
        self.home_w = self.home_l = 0
        self.away_w = self.away_l = 0
        self.streak = ""          # e.g. "W3"
        self.last5 = []           # "W"/"L"/"T"
        self.h2h = Counter()      # opponent -> wins minus losses

    @property
    def games(self):
        return self.w + self.l + self.t

    @property
    def pct(self):
        g = self.games
        return (self.w + 0.5 * self.t) / g if g else 0.0

    @property
    def diff(self):
        return self.pf - self.pa

    def wlt(self):
        return f"{self.w}-{self.l}" + (f"-{self.t}" if self.t else "")

    def add(self, result, pf, pa, div, conf, home, opp):
        self.pf += pf
        self.pa += pa
        if result == "W":
            self.w += 1
            self.h2h[opp] += 1
        elif result == "L":
            self.l += 1
            self.h2h[opp] -= 1
        else:
            self.t += 1
        if div:
            self.div_w += result == "W"
            self.div_l += result == "L"
            self.div_t += result == "T"
        if conf:
            self.conf_w += result == "W"
            self.conf_l += result == "L"
            self.conf_t += result == "T"
        if result != "T":
            if home:
                self.home_w += result == "W"
                self.home_l += result == "L"
            else:
                self.away_w += result == "W"
                self.away_l += result == "L"
        self.last5 = (self.last5 + [result])[-5:]
        if self.streak and self.streak[0] == result:
            self.streak = f"{result}{int(self.streak[1:]) + 1}"
        else:
            self.streak = f"{result}1"

    def sort_key(self):
        cg = self.conf_w + self.conf_l + self.conf_t
        cpct = (self.conf_w + 0.5 * self.conf_t) / cg if cg else 0.0
        dg = self.div_w + self.div_l + self.div_t
        dpct = (self.div_w + 0.5 * self.div_t) / dg if dg else 0.0
        return (self.pct, dpct, cpct, self.diff, self.pf)


class League:
    def __init__(self, name, era):
        self.name = name
        self.era_start = era
        self.year = 2026
        self.founded = 2026
        self.teams = {}
        self.structure = {}
        self.user_abbr = None

        self.phase = "regular"     # see season.PHASES
        self.week = 0              # index of the next regular-season week
        self.schedule = []         # [[(home, away), ...] per week]
        self.results = {}          # week index -> [GameResult]
        self.playoff_results = {}  # round name -> [GameResult]
        self.playoff_seeds = {}    # conf -> [abbr]
        self.playoff_alive = {}    # conf -> [abbr] remaining
        self.playoff_round = 0
        self.champion = None
        self.standings = {}
        self.last_ranks = {}       # abbr -> division finish last season

        self.free_agents = []
        self.draft_class = []
        self.draft_order = []      # [(round, pick, abbr)]
        self.draft_index = 0
        self.draft_log = []        # [(round, pick, abbr, player_id, name, pos)]
        self.retired = []
        self.hall_of_fame = []     # [(year, player)]
        self.history = []          # season summary dicts
        self.news = []             # [(year, week_label, category, text, team)]
        self.transactions = []     # [(year, week_label, text)]
        self.coach_pool = []

        self.salary_cap = settings["salary_cap"]
        self.pipeline = {}
        self.pipeline_drift = {}
        self.pipeline_wave = {}    # slow generational talent tides by position group (eras.evolve)
        self.style_drift = {"pass": 0.0}   # the league's slowly drifting football culture
        self.prestige_history = []
        self.prestige_baseline = None
        self.ratio_ema = None
        self.meta = {}
        self.class_strength = 0.0
        self.playoff_exit = {}
        self.archetype_weights = {}
        self.season_trends = {}    # year -> league averages
        self.next_player_id = 1
        self.expiring = []         # player ids with expiring deals (re-sign window)
        self.fa_wave = 0
        self.awards_this_season = {}
        # Competition committee
        self.rules = {"coverage": 0, "qb_protection": 0, "holding": 0, "kickoff": 0, "dynamic_kickoff": 0}
        self.rule_history = []     # [(year, key, step, text)]
        self.qb_injury_history = []
        # Roster rules
        self.pick_owner = {}       # "year-round-origteam" -> owner abbr (traded picks)
        self.fa_moves = []         # (fa year, from, to, salary, name, pos) for comp picks
        self.draft_orig = []       # original team for each slot of draft_order
        self.draft_comp = set()    # overall pick numbers that are compensatory
        self.comp_awards = []
        # Record book extras
        self.game_records = {}     # key -> [(value, name, pos, team, opp, year, week, pid)]
        self.weekly_awards = []    # (year, week, award, pid, name, pos, team, line)
        self.negotiations = {}     # contract talks in progress (negotiation.py)
        self.custom_settings = None  # this league's own sim settings (settings.use_league)
        # Front offices (front_office.py)
        self.gm_pool = []          # general managers out of work
        self.fo_log = []           # (year, "offseason"/"midseason", {abbr: plan})
        self.shortlist = []        # player ids the user is watching
        self.shortlist_state = {}  # pid -> (team, injured) at the last check
        self.trade_block = []      # user's players (ids) and picks (lists) offered to the league

    def strength_order(self):
        """Team abbreviations from strongest to weakest roster (cached until something changes)."""
        token = (self.year, self.phase, self.week, getattr(self, "draft_index", 0), len(self.transactions),
                 len(self.free_agents))
        cache = getattr(self, "_strength_cache", None)
        if cache is None or cache[0] != token:
            order = sorted(self.teams, key=lambda a: -self.teams[a].overall)
            self._strength_cache = (token, order)
            cache = self._strength_cache
        return list(cache[1])

    def __getstate__(self):
        state = dict(self.__dict__)
        state.pop("_strength_cache", None)
        return state

    def __setstate__(self, state):
        """Older saves: fill in anything added since they were written."""
        fresh = League.__new__(League)
        League.__init__(fresh, state.get("name", "League"), state.get("era_start", ""))
        self.__dict__.update(fresh.__dict__)
        self.__dict__.update(state)

    # ── Lookups ──────────────────────────────────────────────────────────────

    @property
    def user_team(self):
        return self.teams.get(self.user_abbr)

    def team_list(self):
        return [self.teams[a] for c in self.structure.values()
                for d in c.values() for a in d]

    def division_of(self, abbr):
        for c, divs in self.structure.items():
            for d, abbrs in divs.items():
                if abbr in abbrs:
                    return c, d
        return None, None

    def all_players(self, include_fa=True):
        out = [p for t in self.teams.values() for p in t.roster]
        if include_fa:
            out += self.free_agents
        return out

    def find_player(self, pid):
        for t in self.teams.values():
            for p in t.roster:
                if p.id == pid:
                    return p
        for p in self.free_agents:
            if p.id == pid:
                return p
        for p in self.draft_class:
            if p.id == pid:
                return p
        for p in self.retired:
            if p.id == pid:
                return p
        return None

    @property
    def week_label(self):
        if self.phase == "regular":
            return f"Week {self.week + 1}"
        return {
            "playoffs": "Playoffs", "season_end": "Season End",
            "resign": "Re-signing", "draft": "Draft",
            "free_agency": "Free Agency", "preseason": "Preseason",
        }.get(self.phase, self.phase.title())

    def add_news(self, category, text, team=None):
        self.news.append((self.year, self.week_label, category, text, team))
        if len(self.news) > 1500:
            self.news = self.news[-1200:]

    def add_transaction(self, text):
        self.transactions.append((self.year, self.week_label, text))
        if len(self.transactions) > 2000:
            self.transactions = self.transactions[-1500:]

    # ── Standings ────────────────────────────────────────────────────────────

    def reset_standings(self):
        self.standings = {a: Record(a) for a in self.teams}

    def record_game(self, res):
        h, a = res.home, res.away
        hc, hd = self.division_of(h)
        ac, ad = self.division_of(a)
        div = hc == ac and hd == ad
        conf = hc == ac
        if res.home_score > res.away_score:
            hr, ar = "W", "L"
        elif res.home_score < res.away_score:
            hr, ar = "L", "W"
        else:
            hr = ar = "T"
        self.standings[h].add(hr, res.home_score, res.away_score, div, conf, True, a)
        self.standings[a].add(ar, res.away_score, res.home_score, div, conf, False, h)

    def division_standings(self, conf, div):
        recs = [self.standings[a] for a in self.structure[conf][div]]
        return sorted(recs, key=lambda r: r.sort_key(), reverse=True)

    def conference_seeds(self, conf, n=None):
        """Division winners first (by record), then wild cards."""
        n = n or settings["playoff_teams"]
        winners, others = [], []
        for div in self.structure[conf]:
            ds = self.division_standings(conf, div)
            winners.append(ds[0])
            others += ds[1:]
        winners.sort(key=lambda r: r.sort_key(), reverse=True)
        others.sort(key=lambda r: r.sort_key(), reverse=True)
        n_div = min(len(winners), n)
        seeds = winners[:n_div] + others[:max(0, n - n_div)]
        return [r.abbr for r in seeds]

    def league_rank(self):
        recs = sorted(self.standings.values(), key=lambda r: r.sort_key(), reverse=True)
        return [r.abbr for r in recs]

    # ── Results helpers ──────────────────────────────────────────────────────

    def all_results(self, include_playoffs=True):
        out = [g for w in sorted(self.results) for g in self.results[w]]
        if include_playoffs:
            for rnd in self.playoff_results.values():
                out += rnd
        return out

    def team_results(self, abbr):
        return [g for g in self.all_results() if abbr in (g.home, g.away)]
