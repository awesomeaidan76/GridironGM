"""
ui_screens_league.py — League screens: Schedule, Game Center, Standings,
Stats, Players, Teams, Playoffs, History and News.
"""
from collections import Counter

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QScrollArea, QSpinBox, QTabWidget, QTextBrowser,
                             QVBoxLayout, QWidget)

import eras
import records
import ui_stats
import weather
from ui_live import has_live_data
from eras import TREND_KEYS
from ratings import POSITIONS
from season import playoff_round_name
from settings import settings
from stats import fantasy_like_value, summary_line, total_tackles
from ui_screens_club import Screen, news_html, NEWS_COLORS
from ui_theme import T, accent, ca_color, ovr_color, result_color
from ui_widgets import (Card, DataTable, LineChart, StatTile, TeamBadge, ovr_cell, pot_cell, team_cell, cell,
                        clear_layout, filter_chips, h_label, money, pot_text, personality,
                        )


# ── Schedule ──────────────────────────────────────────────────────────────────

class ScheduleScreen(Screen):
    title = "Schedule & Results"

    def __init__(self, main):
        super().__init__(main)
        top = QHBoxLayout()
        top.addWidget(QLabel("Week:"))
        self.week = QComboBox()
        self.week.setMinimumWidth(160)
        self.week.currentIndexChanged.connect(lambda _i: self._fill_week())
        top.addWidget(self.week)
        top.addStretch(1)
        self.outer.addLayout(top)
        body = QHBoxLayout()
        body.setSpacing(12)
        wk_card = Card("Games")
        self.games = DataTable(["Away", "", "Home", "", "Status", "Notes"], stretch=5, sortable=False)
        self.games.on_activate = self._open
        wk_card.add(self.games)
        body.addWidget(wk_card, 3)
        my_card = Card("Your Season")
        self.mine = DataTable(["Wk", "Opponent", "Result", "Record"], stretch=1, sortable=False)
        self.mine.on_activate = self._open
        my_card.add(self.mine)
        body.addWidget(my_card, 2)
        self.outer.addLayout(body, 1)
        self._game_index = {}

    def refresh(self):
        lg = self.lg
        self.week.blockSignals(True)
        self.week.clear()
        for i in range(len(lg.schedule)):
            self.week.addItem(f"Week {i + 1}", ("W", i))
        for rnd in lg.playoff_results:
            self.week.addItem(rnd, ("P", rnd))
        if lg.phase == "regular":
            target = max(0, min(lg.week - 1, len(lg.schedule) - 1))
        else:
            target = self.week.count() - 1
        self.week.setCurrentIndex(max(0, target))
        self.week.blockSignals(False)
        self._fill_week()
        self._fill_mine()
        self.set_subtitle(f"{lg.year} season · double-click a played game to open the Game Center")

    def _fill_week(self):
        lg = self.lg
        data = self.week.currentData()
        if data is None:
            self.games.set_rows([])
            return
        kind, key = data
        rows, keys = [], []
        if kind == "W":
            results = {(g.home, g.away): g for g in lg.results.get(key, [])}
            for h, a in lg.schedule[key]:
                g = results.get((h, a))
                mine = lg.user_abbr in (h, a)
                if g:
                    self._game_index[id(g)] = g
                    w = g.winner
                    rows.append([cell(lg.teams[a].full_name, bold=w == a, color=accent() if mine else None),
                                 cell(g.away_score, g.away_score, bold=w == a),
                                 cell(lg.teams[h].full_name, bold=w == h, color=accent() if mine else None),
                                 cell(g.home_score, g.home_score, bold=w == h),
                                 "Final" + (" (OT)" if g.overtime else ""), _game_note(g)])
                    keys.append(id(g))
                else:
                    rows.append([cell(lg.teams[a].full_name, color=accent() if mine else None), "",
                                 cell(lg.teams[h].full_name, color=accent() if mine else None), "",
                                 "Scheduled", f"OVR {lg.teams[a].overall} @ {lg.teams[h].overall}"])
                    keys.append(None)
            playing = {t for pair in lg.schedule[key] for t in pair}
            byes = [t for t in lg.teams if t not in playing]
            if byes:
                rows.append([cell("Bye: " + ", ".join(sorted(byes)), color=T("muted")), "", "", "", "", ""])
                keys.append(None)
        else:
            for g in lg.playoff_results.get(key, []):
                self._game_index[id(g)] = g
                w = g.winner
                rows.append([cell(lg.teams[g.away].full_name, bold=w == g.away),
                             cell(g.away_score, bold=w == g.away),
                             cell(lg.teams[g.home].full_name, bold=w == g.home),
                             cell(g.home_score, bold=w == g.home), "Final" + (" (OT)" if g.overtime else ""),
                             _game_note(g)])
                keys.append(id(g))
        self.games.set_rows(rows, keys)

    def _fill_mine(self):
        lg = self.lg
        me = lg.user_abbr
        rows, keys = [], []
        w = l = t = 0
        for i, wk in enumerate(lg.schedule):
            game = next(((h, a) for h, a in wk if me in (h, a)), None)
            if game is None:
                rows.append([i + 1, cell("BYE", color=T("muted")), "", ""])
                keys.append(None)
                continue
            h, a = game
            opp = a if h == me else h
            res = next((g for g in lg.results.get(i, []) if g.home == h and g.away == a), None)
            label = ("vs " if h == me else "@ ") + lg.teams[opp].full_name
            if res:
                ms, ts = res.score_of(me), res.score_of(opp)
                r = "W" if ms > ts else "L" if ms < ts else "T"
                w += r == "W"
                l += r == "L"
                t += r == "T"
                self._game_index[id(res)] = res
                rows.append([i + 1, label, cell(f"{r} {ms}-{ts}", color=result_color(r), bold=True),
                             f"{w}-{l}" + (f"-{t}" if t else "")])
                keys.append(id(res))
            else:
                rows.append([i + 1, label, "", ""])
                keys.append(None)
        for rnd, games in lg.playoff_results.items():
            for g in games:
                if me in (g.home, g.away):
                    ms, ts = g.score_of(me), g.score_of(g.opponent(me))
                    r = "W" if ms > ts else "L"
                    self._game_index[id(g)] = g
                    rows.append([rnd.split()[0], ("vs " if g.home == me else "@ ") +
                                 lg.teams[g.opponent(me)].full_name,
                                 cell(f"{r} {ms}-{ts}", color=result_color(r), bold=True), "Playoffs"])
                    keys.append(id(g))
        self.mine.set_rows(rows, keys)

    def _open(self, key):
        g = self._game_index.get(key)
        if g is not None:
            self.main.open_game(g)


def _game_note(g):
    best = None
    for pid, line in g.player_stats.items():
        v = fantasy_like_value(line)
        if best is None or v > best[0]:
            best = (v, pid, line)
    if not best:
        return ""
    name, pos, team, _ = g.player_meta[best[1]]
    return f"{name} ({team}): {summary_line(best[2], pos)}"


# ── Game Center ───────────────────────────────────────────────────────────────

BOX_GROUPS = [("Passing", "pass_att"), ("Rushing", "rush_att"), ("Receiving", "targets"),
              ("Defense", None), ("Kicking", "xpa"), ("Punting", "punts"), ("Returns", None),
              ("Snaps", None), ("Grades", None)]


class GameCenterScreen(Screen):
    title = "Game Center"

    def __init__(self, main):
        super().__init__(main)
        top = QHBoxLayout()
        top.addWidget(QLabel("Game:"))
        self.picker = QComboBox()
        self.picker.setMinimumWidth(420)
        self.picker.currentIndexChanged.connect(lambda _i: self._show())
        top.addWidget(self.picker)
        self.only_mine = QCheckBox("Only my games")
        self.only_mine.setChecked(True)
        self.only_mine.toggled.connect(lambda _c: self.refresh())
        top.addWidget(self.only_mine)
        top.addStretch(1)
        self.outer.addLayout(top)
        self.board = QVBoxLayout()
        self.outer.addLayout(self.board)
        self.tabs = QTabWidget()
        self.outer.addWidget(self.tabs, 1)
        self.games = []
        self.pending = None

    def show_game(self, g):
        self.pending = g

    def refresh(self):
        lg = self.lg
        games = lg.all_results(include_playoffs=True)
        if self.only_mine.isChecked() and lg.user_abbr:
            mine = [g for g in games if lg.user_abbr in (g.home, g.away)]
            if self.pending is None or self.pending in mine:
                games = mine
        self.games = list(reversed(games))
        self.picker.blockSignals(True)
        self.picker.clear()
        for g in self.games:
            label = (g.playoff or f"Week {g.week}") + f":  {g.summary()}"
            self.picker.addItem(label)
        idx = 0
        if self.pending is not None and self.pending in self.games:
            idx = self.games.index(self.pending)
        self.pending = None
        if self.games:
            self.picker.setCurrentIndex(idx)
        self.picker.blockSignals(False)
        self._show()

    def _show(self):
        clear_layout(self.board)
        self.tabs.clear()
        i = self.picker.currentIndex()
        if not (0 <= i < len(self.games)):
            lbl = QLabel("No games have been played yet.")
            lbl.setObjectName("muted")
            self.board.addWidget(lbl)
            self.set_subtitle("")
            return
        g = self.games[i]
        lg = self.lg
        self.set_subtitle(f"{g.season} · {g.playoff or 'Week ' + str(g.week)}")
        self.board.addWidget(self._scoreboard(g))
        self.tabs.addTab(self._box(g), "Box Score")
        self.tabs.addTab(self._team_stats(g), "Team Stats")
        self.tabs.addTab(self._scoring(g), "Scoring")
        self.tabs.addTab(self._drives(g), "Drives")
        self.tabs.addTab(self._pbp(g), "Play-by-Play")
        self.tabs.addTab(self._highlights(g), "Highlights")

    def _scoreboard(self, g):
        lg = self.lg
        card = Card()
        row = QHBoxLayout()
        row.setSpacing(16)
        for abbr, score, side in ((g.away, g.away_score, "away"), (g.home, g.home_score, "home")):
            t = lg.teams[abbr]
            box = QHBoxLayout()
            if side == "away":
                box.addWidget(TeamBadge(t, 48))
            col = QVBoxLayout()
            name = h_label(t.full_name, "h3")
            col.addWidget(name)
            rec = QLabel(lg.standings[abbr].wlt() if abbr in lg.standings else "")
            rec.setObjectName("muted")
            col.addWidget(rec)
            box.addLayout(col)
            sc = QLabel(str(score))
            sc.setObjectName("bigvalue")
            if g.winner == abbr:
                sc.setStyleSheet(f"color: {accent()};")
            box.addWidget(sc)
            if side == "home":
                box.addWidget(TeamBadge(t, 48))
            row.addLayout(box, 1)
            if side == "away":
                mid = QLabel("FINAL" + (" / OT" if g.overtime else ""))
                mid.setObjectName("caps")
                row.addWidget(mid)
        card.body.addLayout(row)
        n = max(len(g.quarters[g.home]), len(g.quarters[g.away]))
        cols = ["Team"] + [str(q + 1) if q < 4 else "OT" for q in range(n)] + ["T"]
        qt = DataTable(cols, stretch=0, sortable=False)
        rows = []
        for abbr in (g.away, g.home):
            q = g.quarters[abbr] + [0] * (n - len(g.quarters[abbr]))
            rows.append([abbr] + q + [cell(g.score_of(abbr), bold=True)])
        qt.set_rows(rows)
        qt.fit_height()
        card.add(qt)
        foot = QHBoxLayout()
        w = getattr(g, "weather", None)
        wl = QLabel(f"{lg.teams[g.home].city} · {weather.describe(w)}" if w else lg.teams[g.home].city)
        wl.setObjectName("muted")
        foot.addWidget(wl)
        foot.addStretch(1)
        if has_live_data(g):
            watch = QPushButton("▶  Watch replay")
            watch.clicked.connect(lambda _c=False, game=g: self.main.watch_game(game))
            foot.addWidget(watch)
        card.body.addLayout(foot)
        return card

    def _box(self, g):
        lg = self.lg
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 8, 0, 0)
        for abbr in (g.away, g.home):
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            inner = QWidget()
            col = QVBoxLayout(inner)
            col.setContentsMargins(0, 0, 6, 0)
            col.addWidget(h_label(lg.teams[abbr].full_name, "h3"))
            lines = [(pid, line) for pid, line in g.player_stats.items() if g.player_meta[pid][2] == abbr]
            for group, key in BOX_GROUPS:
                if group == "Defense":
                    sel = [(pid, l) for pid, l in lines if total_tackles(l) + l["sacks"] + l["def_int"] + l["pd"] > 0]
                    sel.sort(key=lambda x: -(total_tackles(x[1]) + x[1]["sacks"] * 3 + x[1]["def_int"] * 4))
                elif group == "Returns":
                    sel = [(pid, l) for pid, l in lines if l["kr"] + l["pr"] > 0]
                elif group == "Grades":
                    sel = [(pid, l) for pid, l in lines if l["grade_n"]]
                    sel.sort(key=lambda x: -(x[1]["grade_pts"] / x[1]["grade_n"]))
                elif group == "Snaps":
                    sel = [(pid, l) for pid, l in lines if l["off_snaps"] + l["def_snaps"] > 0]
                    sel.sort(key=lambda x: (POSITIONS.index(g.player_meta[x[0]][1]),
                                            -(x[1]["off_snaps"] + x[1]["def_snaps"])))
                else:
                    sel = [(pid, l) for pid, l in lines if l[key] > 0]
                    sk = {"Passing": "pass_att", "Rushing": "rush_yds", "Receiving": "rec_yds"}.get(group, key)
                    sel.sort(key=lambda x: -x[1][sk])
                if not sel:
                    continue
                lbl = QLabel(group.upper())
                lbl.setObjectName("caps")
                col.addWidget(lbl)
                table = DataTable(["Player"] + ui_stats.columns(group), stretch=0)
                rows, keys = [], []
                for pid, l in sel:
                    name, pos, _, num = g.player_meta[pid]
                    rows.append([f"{name} ({pos})"] + ui_stats.values(group, l))
                    keys.append(pid)
                table.set_rows(rows, keys)
                table.fit_height()
                table.on_activate = self.main.open_player
                col.addWidget(table)
            col.addStretch(1)
            scroll.setWidget(inner)
            lay.addWidget(scroll, 1)
        return w

    def _team_stats(self, g):
        a, h = g.team_stats[g.away], g.team_stats[g.home]
        table = DataTable(["", g.away, g.home], stretch=0, sortable=False)

        def pct(n, d):
            return f"{n}/{d}" + (f" ({100 * n / d:.0f}%)" if d else "")

        def top(s):
            v = int(s["top"])
            return f"{v // 60}:{v % 60:02d}"
        rows = [
            ["First downs", a["first_downs"], h["first_downs"]],
            ["Total yards", a["total_yds"], h["total_yds"]],
            ["Passing yards (net)", a["pass_yds"] - a["sack_yds"], h["pass_yds"] - h["sack_yds"]],
            ["Comp / Att", f"{a['pass_cmp']}/{a['pass_att']}", f"{h['pass_cmp']}/{h['pass_att']}"],
            ["Sacks – yards", f"{a['sacked']}-{a['sack_yds']}", f"{h['sacked']}-{h['sack_yds']}"],
            ["Rushing yards", a["rush_yds"], h["rush_yds"]],
            ["Rushing attempts", a["rush_att"], h["rush_att"]],
            ["Yards per play", f"{a['total_yds'] / max(1, a['pass_att'] + a['sacked'] + a['rush_att']):.1f}",
             f"{h['total_yds'] / max(1, h['pass_att'] + h['sacked'] + h['rush_att']):.1f}"],
            ["3rd down", pct(a["third_conv"], a["third_att"]), pct(h["third_conv"], h["third_att"])],
            ["4th down", pct(a["fourth_conv"], a["fourth_att"]), pct(h["fourth_conv"], h["fourth_att"])],
            ["Red zone TD", pct(a["rz_td"], a["rz_trips"]), pct(h["rz_td"], h["rz_trips"])],
            ["Turnovers", a["turnovers"], h["turnovers"]],
            ["Penalties – yards", f"{a['penalties']}-{a['pen_yds']}", f"{h['penalties']}-{h['pen_yds']}"],
            ["Punts", a["punts"], h["punts"]],
            ["Time of possession", top(a), top(h)],
        ]
        if a["epa_plays"] and h["epa_plays"]:
            rows[9:9] = [
                ["EPA per play", f"{a['epa'] / a['epa_plays']:+.2f}", f"{h['epa'] / h['epa_plays']:+.2f}"],
                ["Success rate", pct(a["succ"], a["epa_plays"]), pct(h["succ"], h["epa_plays"])],
                ["Pressured dropbacks", pct(a["pressured"], a["dropbacks"]), pct(h["pressured"], h["dropbacks"])],
            ]
        table.set_rows(rows)
        return table

    def _scoring(self, g):
        table = DataTable(["Qtr", "Time", "Team", "Play", g.away, g.home], stretch=3, sortable=False)
        table.set_rows([[q, clk, team, text, aw, hm] for q, clk, team, text, hm, aw in g.scoring])
        return table

    def _drives(self, g):
        table = DataTable(["Team", "Qtr", "Start", "Plays", "Yards", "Result"], stretch=5)
        rows = []
        for abbr in (g.away, g.home):
            for d in g.drives[abbr]:
                start = d["start"]
                rows.append([abbr, cell(f"Q{d['quarter']}" if d["quarter"] <= 4 else "OT", d["quarter"]),
                             cell(f"Own {start}" if start <= 50 else f"Opp {100 - start}", start),
                             d["plays"], d["yards"],
                             cell(d["result"], color=T("good") if d["result"] in ("Touchdown", "Field goal")
                                  else T("bad") if d["result"] in ("Interception", "Fumble", "Downs",
                                                                  "Turnover TD") else None)])
        table.set_rows(rows)
        return table

    def _pbp(self, g):
        table = DataTable(["Qtr", "Clock", "Team", "Situation", "Play"], stretch=4, sortable=False)
        rows = []
        for q, clk, team, sit, text, kind in g.plays:
            col = None
            up = text.upper()
            if kind == "score":
                col = accent()
            elif "INTERCEPTED" in up or "FUMBLE" in up:
                col = T("bad")
            elif "INJURY" in up:
                col = T("warn")
            elif kind == "note":
                col = T("muted")
            rows.append([q, clk, team, sit, cell(text, color=col, bold=kind == "score")])
        if not rows:
            rows.append(["", "", "", "", "Play-by-play was not recorded for this game."])
        table.set_rows(rows)
        return table

    def _highlights(self, g):
        lg = self.lg
        box = QTextBrowser()
        parts = []
        winner = g.winner
        if winner:
            loser = g.loser
            margin = abs(g.home_score - g.away_score)
            verb = "edged" if margin <= 3 else "beat" if margin <= 14 else "routed"
            parts.append(f"<h3>{lg.teams[winner].full_name} {verb} the {lg.teams[loser].full_name}, "
                         f"{max(g.home_score, g.away_score)}-{min(g.home_score, g.away_score)}"
                         f"{' in overtime' if g.overtime else ''}.</h3>")
        else:
            parts.append(f"<h3>{g.summary()} — a tie.</h3>")
        perf = sorted(((fantasy_like_value(l), pid, l) for pid, l in g.player_stats.items()),
                      key=lambda x: -x[0])[:6]
        parts.append("<b>Top performers</b><ul>")
        for _, pid, l in perf:
            name, pos, team, _ = g.player_meta[pid]
            parts.append(f"<li><b>{name}</b> ({pos}, {team}) — {summary_line(l, pos)}</li>")
        parts.append("</ul>")
        big = [p for p in g.plays if p[5] == "play" and any(
            k in p[4] for k in ("TOUCHDOWN", "INTERCEPTED", "FUMBLE", "BLOCKED"))]
        long_plays = []
        for p in g.plays:
            if p[5] != "play" or " for " not in p[4]:
                continue
            try:
                yds = int(p[4].split(" for ")[-1].split(" ")[0])
            except ValueError:
                continue
            if yds >= 30:
                long_plays.append(p)
        key_plays = (big + long_plays)[:12]
        if key_plays:
            parts.append("<b>Key plays</b><ul>")
            for q, clk, team, sit, text, _ in key_plays:
                parts.append(f"<li>{q} {clk} · {team}: {text}</li>")
            parts.append("</ul>")
        if g.injuries:
            parts.append("<b>Injuries</b><ul>")
            for pid, name, team, inj, wk in g.injuries:
                parts.append(f"<li>{name} ({team}) — {inj}, {wk} wk</li>")
            parts.append("</ul>")
        box.setHtml("".join(parts))
        return box


# ── Standings ─────────────────────────────────────────────────────────────────

class StandingsScreen(Screen):
    title = "Standings"

    def __init__(self, main):
        super().__init__(main)
        chips, get = filter_chips([("division", "Divisions"), ("conference", "Conference / Seeds"),
                                   ("league", "League")], self._set_mode, state_key="standings")
        self.mode = get()
        self.outer.addWidget(chips)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.inner = QWidget()
        self.inner.setObjectName("screen")
        self.grid = QGridLayout(self.inner)
        self.grid.setSpacing(12)
        self.grid.setContentsMargins(0, 0, 4, 0)
        scroll.setWidget(self.inner)
        self.outer.addWidget(scroll, 1)

    def _set_mode(self, m):
        self.mode = m
        self.refresh()

    COLS = ["Team", "W", "L", "T", "Pct", "PF", "PA", "Diff", "Div", "Conf", "Home", "Away", "Strk"]

    def _row(self, r, seed=None):
        lg = self.lg
        t = lg.teams[r.abbr]
        mine = r.abbr == lg.user_abbr
        name = (f"{seed}. " if seed else "") + t.full_name
        return [cell(name, bold=mine, color=accent() if mine else None), r.w, r.l, r.t,
                cell(f"{r.pct:.3f}", r.pct), r.pf, r.pa,
                cell(f"{r.diff:+d}", r.diff, color=T("good") if r.diff > 0 else T("bad") if r.diff < 0 else None),
                f"{r.div_w}-{r.div_l}" + (f"-{r.div_t}" if r.div_t else ""),
                f"{r.conf_w}-{r.conf_l}" + (f"-{r.conf_t}" if r.conf_t else ""),
                f"{r.home_w}-{r.home_l}", f"{r.away_w}-{r.away_l}", r.streak]

    def refresh(self):
        lg = self.lg
        clear_layout(self.grid)
        self.set_subtitle(f"{lg.year} · {lg.week_label}")
        if self.mode == "division":
            i = 0
            for conf, divs in lg.structure.items():
                for div in divs:
                    card = Card(f"{conf} {div}")
                    t = DataTable(self.COLS, stretch=0, sortable=False)
                    recs = lg.division_standings(conf, div)
                    t.set_rows([self._row(r) for r in recs], [r.abbr for r in recs])
                    t.fit_height()
                    t.on_activate = self.main.open_team
                    card.add(t)
                    self.grid.addWidget(card, i // 2, i % 2)
                    i += 1
        elif self.mode == "conference":
            n = settings["playoff_teams"]
            for ci, conf in enumerate(lg.structure):
                card = Card(f"{conf} — playoff seeds ({n} teams)")
                seeds = lg.playoff_seeds.get(conf) or lg.conference_seeds(conf, n)
                rest = sorted((r for r in (lg.standings[a] for divs in lg.structure[conf].values()
                                           for a in divs) if r.abbr not in seeds),
                              key=lambda r: r.sort_key(), reverse=True)
                rows = [self._row(lg.standings[a], i + 1) for i, a in enumerate(seeds)]
                rows += [self._row(r) for r in rest]
                keys = list(seeds) + [r.abbr for r in rest]
                t = DataTable(self.COLS, stretch=0, sortable=False)
                t.set_rows(rows, keys)
                t.fit_height()
                t.on_activate = self.main.open_team
                card.add(t)
                self.grid.addWidget(card, ci, 0)
        else:
            card = Card("League")
            recs = sorted(lg.standings.values(), key=lambda r: r.sort_key(), reverse=True)
            t = DataTable(self.COLS, stretch=0)
            t.set_rows([self._row(r, i + 1) for i, r in enumerate(recs)], [r.abbr for r in recs])
            t.fit_height()
            t.on_activate = self.main.open_team
            card.add(t)
            self.grid.addWidget(card, 0, 0)


# ── Stats ─────────────────────────────────────────────────────────────────────

STAT_TABS = [("Passing", "Passing"), ("Rushing", "Rushing"), ("Receiving", "Receiving"),
             ("Defense", "Defense"), ("Kicking", "Kicking"), ("Punting", "Punting"),
             ("Returns", "Returns"), ("AdvPass", "Adv. Passing"), ("AdvRush", "Adv. Rushing"),
             ("AdvRec", "Adv. Receiving"), ("QBDecisions", "QB Decisions"), ("Grades", "Grades"), ("Blocking", "Blocking"), ("PassRush", "Pass Rush"),
             ("RunDef", "Tackling"), ("Coverage", "Coverage"),
             ("TeamOff", "Team Offense"), ("TeamDef", "Team Defense"), ("TeamAdv", "Team Advanced")]


class StatsScreen(Screen):
    title = "League Stats"

    def __init__(self, main):
        super().__init__(main)
        chips, get = filter_chips(STAT_TABS, self._set_group, "Passing", state_key="stats")
        self.group = get()
        self.outer.addWidget(chips)
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Season:"))
        self.season = QComboBox()
        self.season.currentIndexChanged.connect(lambda _i: self._fill())
        bar.addWidget(self.season)
        bar.addWidget(QLabel("Team:"))
        self.team = QComboBox()
        self.team.currentIndexChanged.connect(lambda _i: self._fill())
        bar.addWidget(self.team)
        bar.addWidget(QLabel("Position:"))
        self.pos = QComboBox()
        self.pos.addItem("All", None)
        for p in POSITIONS:
            self.pos.addItem(p, p)
        self.pos.currentIndexChanged.connect(lambda _i: self._fill())
        bar.addWidget(self.pos)
        self.qualified = QCheckBox("Qualified only")
        self.qualified.setChecked(True)
        self.qualified.toggled.connect(lambda _c: self._fill())
        bar.addWidget(self.qualified)
        self.playoffs = QCheckBox("Playoffs")
        self.playoffs.toggled.connect(lambda _c: self._fill())
        bar.addWidget(self.playoffs)
        bar.addStretch(1)
        self.outer.addLayout(bar)
        self.table = DataTable(["Player"], stretch=0)
        self.table.on_activate = self._activate
        self.outer.addWidget(self.table, 1)
        self._loading = False

    def _set_group(self, g):
        self.group = g
        self._fill()

    def _activate(self, key):
        if isinstance(key, str):
            self.main.open_team(key)
        else:
            self.main.open_player(key)

    def refresh(self):
        lg = self.lg
        self._loading = True
        cur = self.season.currentData()
        self.season.clear()
        years = []
        if lg.phase in ("regular", "playoffs"):
            years.append(lg.year)
        years += sorted({h["year"] for h in lg.history}, reverse=True)
        for y in years:
            self.season.addItem(str(y), y)
        if cur in years:
            self.season.setCurrentIndex(years.index(cur))
        tcur = self.team.currentData()
        self.team.clear()
        self.team.addItem("All teams", None)
        for t in lg.team_list():
            self.team.addItem(t.full_name, t.abbr)
        if tcur:
            self.team.setCurrentIndex(max(0, self.team.findData(tcur)))
        self._loading = False
        self._fill()

    def _season_lines(self, year, playoffs):
        """[(player, team_abbr, statline)] for a season."""
        lg = self.lg
        out = []
        current = year == lg.year and lg.phase in ("regular", "playoffs")
        seen = set()
        for p in lg.all_players(include_fa=True) + lg.retired:
            if p.id in seen:
                continue
            seen.add(p.id)
            if current:
                s = p.playoff_stats if playoffs else p.season_stats
                if s["gp"]:
                    out.append((p, p.team or "FA", s))
            else:
                c = p.career.get(year)
                if c:
                    s = c.get("playoffs", Counter()) if playoffs else c["stats"]
                    if s["gp"]:
                        out.append((p, c["team"], s))
        return out

    def _fill(self):
        if self._loading:
            return
        lg = self.lg
        year = self.season.currentData()
        if year is None:
            self.table.set_rows([])
            return
        playoffs = self.playoffs.isChecked()
        if self.group in ("TeamOff", "TeamDef", "TeamAdv"):
            self._fill_teams(year)
            return
        title, qual, sort_col = ui_stats.LEADERBOARDS[self.group]
        cols = ["Player", "Team", "Pos", "Age", "GP"] + ui_stats.columns(self.group)
        self.table.columns = cols
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        team_f = self.team.currentData()
        pos_f = self.pos.currentData()
        lines = self._season_lines(year, playoffs)
        rows, keys = [], []
        team_games = max(1, max((s["gp"] for _, _, s in lines), default=1))
        team_tgt = Counter()
        for _, abbr, s in lines:
            team_tgt[abbr] += s["targets"]
        for p, abbr, s in lines:
            if team_f and abbr != team_f:
                continue
            if pos_f and p.position != pos_f:
                continue
            if self.qualified.isChecked() and not qual(s, team_games if not playoffs else 0):
                continue
            if not qual(s, 0):
                continue
            age = p.age - (lg.year - year)
            mine = abbr == lg.user_abbr
            rows.append([cell(p.name, color=accent() if mine and settings["highlight_player_team"] else None,
                              bold=mine), abbr, cell(p.position, POSITIONS.index(p.position)), age,
                         s["gp"]] + ui_stats.values(self.group, s, {"team_tgt": team_tgt[abbr]}))
            keys.append(p.id)
        # Default ordering by the group's headline stat
        idx = cols.index(sort_col)

        def sk(r):
            v = r[idx]
            return v["sort"] if isinstance(v, dict) and v["sort"] is not None else (v if isinstance(v, (int, float)) else 0)
        order = sorted(range(len(rows)), key=lambda i: -sk(rows[i]))
        self.table.set_rows([rows[i] for i in order], [keys[i] for i in order])
        self.set_subtitle(f"{year} {'playoffs' if playoffs else 'regular season'} · "
                          f"{len(rows)} players · click a column header to sort")

    def _fill_teams(self, year):
        lg = self.lg
        if self.group == "TeamAdv":
            return self._fill_team_adv(year)
        defense = self.group == "TeamDef"
        cols = ["Team", "GP", "Pts/G", "Yds/G", "Pass/G", "Rush/G", "Y/Play", "1st Dn", "3rd %",
                "TO", "Sacks", "Pen Yds"]
        self.table.columns = cols
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        if year == lg.year and lg.phase in ("regular", "playoffs"):
            games = lg.all_results(include_playoffs=False)
        else:
            games = []
        tot = {a: Counter() for a in lg.teams}
        gp = Counter()
        for g in games:
            for abbr in (g.home, g.away):
                src = g.team_stats[g.opponent(abbr)] if defense else g.team_stats[abbr]
                tot[abbr].update(src)
                gp[abbr] += 1
        rows, keys = [], []
        if not games:
            hist = next((h for h in lg.history if h["year"] == year), None)
            for a, t in lg.teams.items():
                if hist and a in hist["standings"]:
                    w, l, ti, pf, pa = hist["standings"][a]
                    n = max(1, w + l + ti)
                    rows.append([t.full_name, n, cell(f"{(pa if defense else pf) / n:.1f}",
                                                      (pa if defense else pf) / n)] + [""] * 9)
                    keys.append(a)
        else:
            for a, s in tot.items():
                n = max(1, gp[a])
                plays = s["pass_att"] + s["sacked"] + s["rush_att"]
                rows.append([lg.teams[a].full_name, gp[a],
                             cell(f"{s['points'] / n:.1f}", s["points"] / n),
                             cell(f"{s['total_yds'] / n:.1f}", s["total_yds"] / n),
                             cell(f"{(s['pass_yds'] - s['sack_yds']) / n:.1f}", (s['pass_yds'] - s['sack_yds']) / n),
                             cell(f"{s['rush_yds'] / n:.1f}", s["rush_yds"] / n),
                             cell(f"{s['total_yds'] / max(1, plays):.2f}", s["total_yds"] / max(1, plays)),
                             s["first_downs"],
                             cell(f"{100 * s['third_conv'] / max(1, s['third_att']):.1f}",
                                  s["third_conv"] / max(1, s["third_att"])),
                             s["turnovers"], s["sacked"], s["pen_yds"]])
                keys.append(a)
        rows_keys = sorted(zip(rows, keys), key=lambda rk: rk[0][2]["sort"] if isinstance(rk[0][2], dict) else 0,
                           reverse=not defense)
        self.table.set_rows([r for r, _ in rows_keys], [k for _, k in rows_keys])
        self.set_subtitle(f"{year} · team {'defense (opponent stats allowed)' if defense else 'offense'}")

    def _fill_team_adv(self, year):
        import advanced as adv
        lg = self.lg
        cols = ["Team", "GP", "Off EPA/Play", "Off Success", "Def EPA/Play", "Def Success",
                "Pass EPA/DB", "Pressure% Allowed", "Pressure% Made", "aDOT", "Net EPA/Play"]
        self.table.columns = cols
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        if not (year == lg.year and lg.phase in ("regular", "playoffs")):
            self.table.set_rows([])
            self.set_subtitle(f"{year} · advanced team stats are kept for the current season only")
            return
        off = {a: Counter() for a in lg.teams}
        dfn = {a: Counter() for a in lg.teams}
        gp = Counter()
        for g in lg.all_results(include_playoffs=False):
            for abbr in (g.home, g.away):
                off[abbr].update(g.team_stats[abbr])
                dfn[abbr].update(g.team_stats[g.opponent(abbr)])
                gp[abbr] += 1
        pass_epa = Counter()
        for p in lg.all_players():
            if p.team and p.season_stats["dropbacks"]:
                pass_epa[p.team] += p.season_stats["pass_epa"]
        rows, keys = [], []
        for a, o in off.items():
            d = dfn[a]
            oe, de_ = adv.team_epa_per_play(o), adv.team_epa_per_play(d)
            pdb = pass_epa[a] / o["dropbacks"] if o["dropbacks"] else 0.0
            pa = 100.0 * o["pressured"] / o["dropbacks"] if o["dropbacks"] else 0.0
            pm = 100.0 * d["pressured"] / d["dropbacks"] if d["dropbacks"] else 0.0
            ad = o["iay"] / o["pass_att"] if o["pass_att"] else 0.0
            rows.append([lg.teams[a].full_name, gp[a],
                         cell(f"{oe:+.3f}", oe, bold=True), cell(f"{adv.team_success(o):.1f}%", adv.team_success(o)),
                         cell(f"{de_:+.3f}", -de_, bold=True), cell(f"{adv.team_success(d):.1f}%", -adv.team_success(d)),
                         cell(f"{pdb:+.3f}", pdb), cell(f"{pa:.1f}%", -pa), cell(f"{pm:.1f}%", pm),
                         cell(f"{ad:.1f}", ad), cell(f"{oe - de_:+.3f}", oe - de_, bold=True)])
            keys.append(a)
        order = sorted(range(len(rows)), key=lambda i: -rows[i][10]["sort"])
        self.table.set_rows([rows[i] for i in order], [keys[i] for i in order])
        self.set_subtitle(f"{year} · EPA = expected points added per play (see the Glossary). "
                          "Defense columns: lower is better")


# ── Players search ────────────────────────────────────────────────────────────

class PlayersScreen(Screen):
    title = "Player Search"
    subtitle = "Every player in the league, including free agents."

    def __init__(self, main):
        super().__init__(main)
        bar = QHBoxLayout()
        self.name = QLineEdit()
        self.name.setPlaceholderText("Search by name…")
        self.name.textChanged.connect(lambda _t: self.refresh())
        bar.addWidget(self.name, 2)
        self.pos = QComboBox()
        self.pos.addItem("All positions", None)
        for p in POSITIONS:
            self.pos.addItem(p, p)
        self.pos.currentIndexChanged.connect(lambda _i: self.refresh())
        bar.addWidget(self.pos)
        self.team = QComboBox()
        self.team.currentIndexChanged.connect(lambda _i: self.refresh())
        bar.addWidget(self.team)
        bar.addWidget(QLabel("Age ≤"))
        self.age = QSpinBox()
        self.age.setRange(20, 45)
        self.age.setValue(45)
        self.age.valueChanged.connect(lambda _v: self.refresh())
        bar.addWidget(self.age)
        bar.addWidget(QLabel("OVR ≥"))
        self.min_ca = QSpinBox()
        self.min_ca.setRange(0, 99)
        self.min_ca.setValue(55)
        self.min_ca.valueChanged.connect(lambda _v: self.refresh())
        bar.addWidget(self.min_ca)
        self.outer.addLayout(bar)
        self.table = DataTable(["Name", "Pos", "Team", "Age", "OVR", "POT", "Best Role",
                                "Personality", "Salary", "Yrs", "Rep"], stretch=0)
        self.table.on_activate = self.main.open_player
        self.outer.addWidget(self.table, 1)
        self._teams_loaded = False

    def refresh(self):
        lg = self.lg
        if not self._teams_loaded:
            self.team.blockSignals(True)
            self.team.addItem("All teams", None)
            self.team.addItem("Free agents", "FA")
            self.team.addItem("My shortlist", "SHORT")
            for t in lg.team_list():
                self.team.addItem(t.full_name, t.abbr)
            self.team.blockSignals(False)
            self._teams_loaded = True
        q = self.name.text().strip().lower()
        pos = self.pos.currentData()
        tf = self.team.currentData()
        scouting = lg.user_team.scouting if lg.user_team else 10
        rows, keys = [], []
        for p in lg.all_players(include_fa=True):
            if q and q not in p.name.lower():
                continue
            if pos and p.position != pos:
                continue
            if tf == "FA" and p.team is not None:
                continue
            if tf == "SHORT" and p.id not in (getattr(lg, "shortlist", None) or []):
                continue
            if tf and tf not in ("FA", "SHORT") and p.team != tf:
                continue
            ovr = p.scouted_ovr(scouting)
            if p.age > self.age.value() or ovr < self.min_ca.value():
                continue
            rows.append([p.name, cell(p.position, POSITIONS.index(p.position)), p.team or "FA", p.age,
                         ovr_cell(ovr, settings["show_ca_number"]),
                         pot_cell(p, scouting),
                         cell("{} {}".format(*p.best_role), p.best_role[1]),
                         personality(p), cell(money(p.salary) if p.contract else "—", p.salary),
                         p.contract_years, p.reputation])
            keys.append(p.id)
            if len(rows) >= 1500:
                break
        order = sorted(range(len(rows)), key=lambda i: -rows[i][4]["sort"])
        self.table.set_rows([rows[i] for i in order], [keys[i] for i in order])
        self.set_subtitle(f"{len(rows)} players match · double-click for the full profile")


# ── Teams ─────────────────────────────────────────────────────────────────────

class TeamsScreen(Screen):
    title = "Teams"
    subtitle = "Double-click a team for its roster, coach and history."

    def __init__(self, main):
        super().__init__(main)
        self.tabs = QTabWidget()
        self.table = DataTable(["Team", "Conf", "Div", "Record", "OVR", "OFF", "DEF", "QB",
                                "Head Coach", "Offense", "Defense", "Payroll", "Titles"], stretch=0)
        self.table.on_activate = self.main.open_team
        self.tabs.addTab(self.table, "Teams")
        fo_w = QWidget()
        fl = QVBoxLayout(fo_w)
        fl.setContentsMargins(0, 8, 0, 0)
        self.fo_note = QLabel()
        self.fo_note.setObjectName("sub")
        self.fo_note.setWordWrap(True)
        fl.addWidget(self.fo_note)
        self.fo_table = DataTable(["Team", "Plan", "Priorities", "General Manager", "GM Style", "GM Traits",
                                   "GM Record", "Owner", "Power", "Coach Style"], stretch=5)
        self.fo_table.on_activate = self.main.open_team
        fl.addWidget(self.fo_table, 1)
        self.tabs.addTab(fo_w, "Front Offices")
        self.outer.addWidget(self.tabs, 1)

    def refresh(self):
        lg = self.lg
        rows, keys = [], []
        for t in lg.team_list():
            u = t.unit_ratings()
            r = lg.standings[t.abbr]
            mine = t.abbr == lg.user_abbr
            rows.append([cell(t.full_name, bold=mine, color=accent() if mine else None), t.conference,
                         t.division, cell(r.wlt(), r.pct), team_cell(u["OVR"], "OVR"), team_cell(u["OFF"], "OFF"),
                         team_cell(u["DEF"], "DEF"), team_cell(u["QB"], "QB"), t.coach.name, t.coach.off_scheme,
                         t.coach.def_scheme, cell(money(t.payroll), t.payroll), t.titles])
            keys.append(t.abbr)
        self.table.set_rows(rows, keys)
        self._front_offices()

    def _front_offices(self):
        import front_office as fo
        lg = self.lg
        fo.ensure(lg)
        rows, keys = [], []
        for t in lg.team_list():
            g = fo.gm_of(t)
            o = fo.owner_traits(t.owner)
            mine = t.abbr == lg.user_abbr
            plan = t.plan or {}
            rows.append([cell(t.full_name, bold=mine, color=accent() if mine else None),
                         "—" if mine else fo.plan_of(t), ", ".join(plan.get("focus") or []) if not mine else "",
                         "You" if g is None else g.name, "" if g is None else g.archetype,
                         "" if g is None else ", ".join(g.trait_words(3)),
                         "" if g is None else cell(g.record_str, g.win_pct),
                         fo.owner_type(o), t.power or "GM-led", fo.coach_style(t.coach)])
            keys.append(t.abbr)
        self.fo_table.set_rows(rows, keys)
        counts = fo.plan_summary(lg)
        buyers = sum(v for k, v in counts.items() if k in fo.BUYERS)
        sellers = sum(v for k, v in counts.items() if k in fo.SELLERS)
        self.fo_note.setText("Every CPU club has an owner, a general manager with his own personality and a "
                             "plan for the season. Plans: " + ", ".join(f"{k} {v}" for k, v in
                                                                        sorted(counts.items(), key=lambda kv: -kv[1]))
                             + f". {buyers} clubs are buying, {sellers} selling. Double-click a club for "
                               f"its full front-office profile.")


# ── Playoffs ──────────────────────────────────────────────────────────────────

class PlayoffsScreen(Screen):
    title = "Playoffs"

    def __init__(self, main):
        super().__init__(main)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.inner = QWidget()
        self.inner.setObjectName("screen")
        self.lay = QVBoxLayout(self.inner)
        self.lay.setContentsMargins(0, 0, 4, 0)
        self.lay.setSpacing(12)
        scroll.setWidget(self.inner)
        self.outer.addWidget(scroll, 1)

    def refresh(self):
        lg = self.lg
        clear_layout(self.lay)
        n = settings["playoff_teams"]
        if lg.champion:
            champ = lg.teams[lg.champion]
            card = Card()
            card.setStyleSheet(f"QFrame#card {{ border: 2px solid {T('gold')}; }}")
            row = QHBoxLayout()
            row.addWidget(TeamBadge(champ, 56))
            row.addWidget(h_label(f"🏆  {lg.year} Champions: {champ.full_name}", "h1"), 1)
            card.body.addLayout(row)
            self.lay.addWidget(card)
        projected = not lg.playoff_seeds
        self.set_subtitle(("Projected field if the season ended today" if projected else
                           f"{lg.year} playoffs") + f" · {n} teams per conference")
        cols = QHBoxLayout()
        cols.setSpacing(12)
        for conf in lg.structure:
            seeds = lg.playoff_seeds.get(conf) or lg.conference_seeds(conf, n)
            card = Card(f"{conf} Bracket")
            for i, a in enumerate(seeds):
                t = lg.teams[a]
                alive = a in lg.playoff_alive.get(conf, seeds) if not projected else True
                exit_r = lg.playoff_exit.get(a, -1)
                status = "" if projected else ("alive" if alive and not lg.champion else
                                               "Champions" if exit_r == 9 else
                                               "Runner-up" if exit_r == 8 else "eliminated")
                col = T("muted") if status == "eliminated" else (accent() if a == lg.user_abbr else T("text"))
                lbl = QLabel(f"<span style='color:{T('muted')}'>{i + 1}.</span> "
                             f"<b style='color:{col}'>{t.full_name}</b> "
                             f"<span style='color:{T('muted')}'>{lg.standings[a].wlt()} {status}</span>")
                lbl.setTextFormat(Qt.TextFormat.RichText)
                card.add(lbl)
            card.body.addStretch(1)
            cols.addWidget(card, 1)
        self.lay.addLayout(cols)
        for rnd, games in lg.playoff_results.items():
            card = Card(rnd)
            for g in games:
                w = g.winner
                lbl = QLabel(f"{lg.teams[g.away].full_name} <b>{g.away_score}</b>  @  "
                             f"{lg.teams[g.home].full_name} <b>{g.home_score}</b>"
                             f"{' (OT)' if g.overtime else ''} — <span style='color:{accent()}'>"
                             f"{lg.teams[w].name} advance</span>")
                lbl.setTextFormat(Qt.TextFormat.RichText)
                card.add(lbl)
                btn = QPushButton("Box score")
                btn.setObjectName("ghost")
                btn.clicked.connect(lambda _c=False, gg=g: self.main.open_game(gg))
                card.add(btn)
            self.lay.addWidget(card)
        if lg.phase == "playoffs" and not lg.champion:
            nxt = QLabel(f"Next up: {playoff_round_name(lg)}")
            nxt.setObjectName("h3")
            self.lay.addWidget(nxt)
        self.lay.addStretch(1)


# ── History ───────────────────────────────────────────────────────────────────

AWARD_ORDER = ["MVP", "Offensive Player of the Year", "Defensive Player of the Year",
               "Offensive Rookie of the Year", "Defensive Rookie of the Year", "Coach of the Year"]


class HistoryScreen(Screen):
    title = "League History"

    def __init__(self, main):
        super().__init__(main)
        self.tabs = QTabWidget()
        self.outer.addWidget(self.tabs, 1)
        # Seasons
        self.seasons = DataTable(["Year", "Champion", "Runner-up", "Best Record", "MVP", "Era",
                                  "Pts/G", "Pass %", "Comp %", "Y/A", "Y/C"], stretch=None)
        self.tabs.addTab(self.seasons, "Seasons")
        # Trends
        tw = QWidget()
        tl = QVBoxLayout(tw)
        tl.setContentsMargins(0, 8, 0, 0)
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Metric:"))
        self.metric = QComboBox()
        for k, label in TREND_KEYS:
            self.metric.addItem(label, k)
        self.metric.currentIndexChanged.connect(lambda _i: self._chart())
        bar.addWidget(self.metric)
        bar.addWidget(QLabel("Compare:"))
        self.metric2 = QComboBox()
        self.metric2.addItem("(none)", None)
        for k, label in TREND_KEYS:
            self.metric2.addItem(label, k)
        self.metric2.currentIndexChanged.connect(lambda _i: self._chart())
        bar.addWidget(self.metric2)
        bar.addStretch(1)
        tl.addLayout(bar)
        self.chart = LineChart(height=300)
        tl.addWidget(self.chart, 2)
        self.era_note = QLabel()
        self.era_note.setWordWrap(True)
        self.era_note.setObjectName("sub")
        tl.addWidget(self.era_note)
        self.trend_table = DataTable(["Year", "Era", "Pts/G", "Pass %", "Pass Att", "Comp %", "Y/A",
                                      "INT %", "Sack %", "Rush Att", "Y/C", "FG %", "Top scheme",
                                      "QB pipe", "RB pipe", "WR pipe", "DB pipe"], stretch=None)
        tl.addWidget(self.trend_table, 2)
        self.tabs.addTab(tw, "Eras & Trends")
        # Awards
        self.awards = DataTable(["Year"] + ["MVP", "OPOY", "DPOY", "OROY", "DROY", "Coach", "Comeback",
                                            "Special Teams"], stretch=None)
        self.tabs.addTab(self.awards, "Awards")
        # Records
        rw = QWidget()
        rl = QVBoxLayout(rw)
        rl.setContentsMargins(0, 8, 0, 0)
        rbar = QHBoxLayout()
        self.rec_kind = QComboBox()
        self.rec_kind.addItem("Single season", "season")
        self.rec_kind.addItem("Career", "career")
        self.rec_kind.addItem("Single game", "game")
        self.rec_kind.addItem("Team, single game", "team")
        self.rec_kind.currentIndexChanged.connect(lambda _i: self._rec_kind_changed())
        rbar.addWidget(self.rec_kind)
        self.rec_cat = QComboBox()
        self._rec_cats = None
        self._fill_rec_cats("season")
        self.rec_cat.currentIndexChanged.connect(lambda _i: self._records())
        rbar.addWidget(self.rec_cat)
        rbar.addStretch(1)
        rl.addLayout(rbar)
        self.rec_table = DataTable(["#", "Value", "Player", "Pos", "Team / Status", "Season / Yrs"],
                                   stretch=2, sortable=False)
        self.rec_table.on_activate = self.main.open_player
        rl.addWidget(self.rec_table, 1)
        self.tabs.addTab(rw, "Record Book")
        # Hall of fame
        self.hof = DataTable(["Inducted", "Player", "Pos", "Seasons", "Awards", "Career"], stretch=5)
        self.hof.on_activate = self.main.open_player
        self.tabs.addTab(self.hof, "Hall of Fame")
        # Franchise
        self.franchise = DataTable(["Year", "Record", "PF", "PA", "Result", "Coach"], stretch=5)
        self.tabs.addTab(self.franchise, "Your Franchise")
        # Rule changes
        self.rules = DataTable(["Year", "Competition Committee decision"], stretch=1, sortable=False)
        self.tabs.addTab(self.rules, "Rule Changes")

    def refresh(self):
        lg = self.lg
        self.set_subtitle(f"{len(lg.history)} completed seasons · league founded "
                          f"{getattr(lg, 'founded', lg.year - len(lg.history))}")
        rows = []
        for h in reversed(lg.history):
            a = h["averages"] or {}
            mvp = h["awards"].get("MVP") or {}
            br = h["best_record"]
            rows.append([h["year"], lg.teams[h["champion"]].full_name if h["champion"] else "",
                         lg.teams[h["runner_up"]].full_name if h.get("runner_up") else "",
                         f"{br[0]} {br[1]}", f"{mvp.get('name', '')} ({mvp.get('pos', '')}, {mvp.get('team', '')})"
                         if mvp else "", h["era"],
                         cell(f"{a.get('ppg', 0):.1f}", a.get("ppg", 0)),
                         cell(f"{a.get('pass_rate', 0):.1f}", a.get("pass_rate", 0)),
                         cell(f"{a.get('comp_pct', 0):.1f}", a.get("comp_pct", 0)),
                         cell(f"{a.get('ypa', 0):.2f}", a.get("ypa", 0)),
                         cell(f"{a.get('ypc', 0):.2f}", a.get("ypc", 0))])
        self.seasons.set_rows(rows)
        trows = []
        for h in reversed(lg.history):
            a = h["averages"] or {}
            sch = h.get("schemes") or {}
            top = max(sch, key=sch.get) if sch else ""
            pipe = h.get("pipeline", {})
            trows.append([h["year"], h["era"], cell(f"{a.get('ppg', 0):.1f}", a.get("ppg", 0)),
                          cell(f"{a.get('pass_rate', 0):.1f}", a.get("pass_rate", 0)),
                          cell(f"{a.get('pass_att', 0):.1f}", a.get("pass_att", 0)),
                          cell(f"{a.get('comp_pct', 0):.1f}", a.get("comp_pct", 0)),
                          cell(f"{a.get('ypa', 0):.2f}", a.get("ypa", 0)),
                          cell(f"{a.get('int_rate', 0):.2f}", a.get("int_rate", 0)),
                          cell(f"{a.get('sack_rate', 0):.2f}", a.get("sack_rate", 0)),
                          cell(f"{a.get('rush_att', 0):.1f}", a.get("rush_att", 0)),
                          cell(f"{a.get('ypc', 0):.2f}", a.get("ypc", 0)),
                          cell(f"{a.get('fg_pct', 0):.1f}", a.get("fg_pct", 0)), top,
                          cell(f"{pipe.get('QB', 0):+.1f}", pipe.get("QB", 0)),
                          cell(f"{pipe.get('RB', 0):+.1f}", pipe.get("RB", 0)),
                          cell(f"{pipe.get('WR', 0):+.1f}", pipe.get("WR", 0)),
                          cell(f"{pipe.get('DB', 0):+.1f}", pipe.get("DB", 0))])
        self.trend_table.set_rows(trows)
        self._chart()
        arows = []
        short = {"MVP": 0, "Offensive Player of the Year": 1, "Defensive Player of the Year": 2,
                 "Offensive Rookie of the Year": 3, "Defensive Rookie of the Year": 4,
                 "Coach of the Year": 5, "Comeback Player of the Year": 6,
                 "Special Teams Player of the Year": 7}
        for h in reversed(lg.history):
            row = [h["year"]] + [""] * 8
            for name, i in short.items():
                a = h["awards"].get(name)
                if a:
                    row[i + 1] = f"{a['name']} ({a['team']})"
            arows.append(row)
        self.awards.set_rows(arows)
        self._records()
        hrows, hkeys = [], []
        for yr, p in reversed(lg.hall_of_fame):
            tot = records.career_totals(p)
            aw = Counter(a for _, a in p.awards if a != "Champion")
            hrows.append([yr, p.name, p.position, len(p.career),
                          ", ".join(f"{n}× {a}" for a, n in aw.most_common(3)),
                          summary_line(tot, p.position)])
            hkeys.append(p.id)
        self.hof.set_rows(hrows, hkeys)
        team = lg.user_team
        if team:
            rh = getattr(lg, "rule_history", [])
            self.rules.set_rows([[y, text[0].upper() + text[1:]] for y, _k, _s, text in reversed(rh)]
                                or [["—", "No rule changes yet. The committee reacts when scoring "
                                           "dries up or players keep getting hurt."]])
            self.franchise.set_rows([[h["year"], f"{h['w']}-{h['l']}" + (f"-{h['t']}" if h['t'] else ""),
                                      h["pf"], h["pa"], h["result"], h["coach"]]
                                     for h in reversed(team.history)])

    def _chart(self):
        lg = self.lg
        k1 = self.metric.currentData()
        k2 = self.metric2.currentData()
        series = []
        for key, color in ((k1, accent()), (k2, T("info"))):
            if not key:
                continue
            pts = [(float(y), float(v.get(key, 0))) for y, v in sorted(lg.season_trends.items()) if v]
            label = dict(TREND_KEYS).get(key, key)
            series.append((label, color, pts))
        self.chart.set_series(series)
        if lg.history:
            labels = [h["era"] for h in lg.history]
            runs = []
            for i, h in enumerate(lg.history):
                if runs and runs[-1][0] == h["era"]:
                    runs[-1][2] = h["year"]
                else:
                    runs.append([h["era"], h["year"], h["year"]])
            text = " → ".join(f"{e} ({a}" + (f"–{b})" if b != a else ")") for e, a, b in runs[-8:])
            self.era_note.setText(f"Eras so far: {text}")
        else:
            self.era_note.setText("Complete a season to start tracking how the league evolves.")

    def _fill_rec_cats(self, kind):
        cats = {"season": records.CATEGORIES, "career": records.CATEGORIES,
                "game": records.GAME_CATEGORIES, "team": records.TEAM_GAME_CATEGORIES}[kind]
        if cats is self._rec_cats:
            return
        self._rec_cats = cats
        self.rec_cat.blockSignals(True)
        self.rec_cat.clear()
        for k, label in cats:
            self.rec_cat.addItem(label, k)
        self.rec_cat.blockSignals(False)

    def _rec_kind_changed(self):
        kind = self.rec_kind.currentData()
        if kind:
            self._fill_rec_cats(kind)
        self._records()

    def _records(self):
        lg = self.lg
        kind = self.rec_kind.currentData()
        cat = self.rec_cat.currentData()
        if kind is None or cat is None:
            return

        def fmt(v):
            return f"{v:.1f}" if isinstance(v, float) and v != int(v) else f"{v:g}"
        if kind == "season":
            data = records.season_records(lg, 25).get(cat, [])
            rows = [[i + 1, cell(fmt(v), v, bold=True), n, pos, team, yr]
                    for i, (v, n, pos, team, yr, pid) in enumerate(data)]
            keys = [d[5] for d in data]
        elif kind == "career":
            data = records.career_leaders(lg, 25).get(cat, [])
            rows = [[i + 1, cell(fmt(v), v, bold=True), n, pos, status, f"{yrs} seasons"]
                    for i, (v, n, pos, status, yrs, pid) in enumerate(data)]
            keys = [d[5] for d in data]
        else:
            data = (getattr(lg, "game_records", None) or {}).get(cat, [])
            rows = [[i + 1, cell(fmt(v), v, bold=True), n, pos or "Team", f"{team} vs {opp}" if pos else team,
                     f"{yr} {wk}"] for i, (v, n, pos, team, opp, yr, wk, pid) in enumerate(data)]
            keys = [d[7] for d in data]
        self.rec_table.set_rows(rows, keys)


# ── News ──────────────────────────────────────────────────────────────────────

class NewsScreen(Screen):
    title = "News"

    def __init__(self, main):
        super().__init__(main)
        chips, get = filter_chips([("mine", "My Club"), ("all", "Everything"), ("Injury", "Injuries"),
                                   ("Signing", "Signings"), ("Trade", "Trades"), ("Draft", "Draft"),
                                   ("Coaching", "Coaching"), ("Positions", "Positions"), ("Awards", "Awards"),
                                   ("Performance", "Performances")], self._set_cat, "mine", state_key="news")
        self.cat = get()
        self.outer.addWidget(chips)
        self.tabs = QTabWidget()
        self.feed = QTextBrowser()
        self.tabs.addTab(self.feed, "News Feed")
        self.tx = DataTable(["Season", "When", "Transaction"], stretch=2, sortable=False)
        self.tabs.addTab(self.tx, "Transactions")
        self.outer.addWidget(self.tabs, 1)

    def _set_cat(self, c):
        self.cat = c
        self.refresh()

    def refresh(self):
        lg = self.lg
        items = list(reversed(lg.news))
        if self.cat == "mine":
            items = [n for n in items if n[4] == lg.user_abbr or n[2] in ("League", "Championship")]
        elif self.cat != "all":
            items = [n for n in items if n[2] == self.cat
                     or (self.cat == "Signing" and n[2] in ("Signing", "Release", "Contract"))
                     or (self.cat == "Positions" and n[2] in ("Depth Chart", "Position Change"))]
        self.feed.setHtml(news_html(items[:250]))
        self.tx.set_rows([[y, w, t] for y, w, t in reversed(lg.transactions[-600:])])
        self.set_subtitle(f"{len(items)} stories")


# ── Glossary ──────────────────────────────────────────────────────────────────

class GlossaryScreen(Screen):
    title = "Glossary"
    subtitle = "What every rating, attribute, trait, stat and play call means."

    def __init__(self, main):
        super().__init__(main)
        from glossary import ATTRIBUTE_DESC, TRAIT_DESC, RATING_DESC
        from ratings import ATTRIBUTES, ATTRIBUTE_GROUPS, POSITION_WEIGHTS
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Search:"))
        self.search = QLineEdit()
        self.search.setPlaceholderText("e.g. vision, coverage, potential")
        self.search.textChanged.connect(lambda _t: self.refresh())
        bar.addWidget(self.search, 1)
        self.outer.addLayout(bar)
        self.text = QTextBrowser()
        self.outer.addWidget(self.text, 1)
        # Which positions lean on each attribute most
        uses = {}
        for pos, w in POSITION_WEIGHTS.items():
            tot = sum(w.values())
            for a, v in w.items():
                if v / tot >= 0.06:
                    uses.setdefault(a, []).append(pos)
        self.sections = [("Ratings", [(n, d, "") for n, d in RATING_DESC])]
        for g in ATTRIBUTE_GROUPS:
            rows = [(v[0] + f" ({v[1]})", ATTRIBUTE_DESC.get(k, ""), ", ".join(uses.get(k, [])))
                    for k, v in ATTRIBUTES.items() if v[2] == g]
            self.sections.append((g, rows))
        self.sections.append(("Hidden personality traits",
                               [(k.replace("_", " ").title(), d, "") for k, d in TRAIT_DESC.items()]))
        from glossary import STATS_DESC, PLAYBOOK_DESC, GAMEDAY_DESC
        self.sections.append(("Game day: fatigue, rotation and game plans", [(n, d, "") for n, d in GAMEDAY_DESC]))
        from glossary import LINE_DESC, COACHING_DESC
        self.sections.append(("Line play and grades", [(n, d, "") for n, d in LINE_DESC]))
        self.sections.append(("Coaching decisions and quarterback play", [(n, d, "") for n, d in COACHING_DESC]))
        from glossary import front_office_desc
        self.sections.append(("Front offices, plans and owners", [(n, d, "") for n, d in front_office_desc()]))
        self.sections.append(("Advanced stats", [(n, d, "") for n, d in STATS_DESC]))
        self.sections.append(("Playbooks and calls", [(n, d, "") for n, d in PLAYBOOK_DESC]))
        from glossary import COLUMN_DESC, SETTING_DESC
        from settings import SPEC
        self.sections.append(("Table columns (also shown when you hover over a column header)",
                              [(n, d, "") for n, d in COLUMN_DESC.items()]))
        self.sections.append(("Settings (also shown when you hover over a setting)",
                              [(SPEC[k][2], d, "") for k, d in SETTING_DESC.items() if k in SPEC]))

    def refresh(self):
        q = self.search.text().strip().lower()
        html = []
        for title, rows in self.sections:
            keep = [r for r in rows if not q or q in r[0].lower() or q in r[1].lower() or q in title.lower()]
            if not keep:
                continue
            html.append(f"<h3 style='color:{accent()}'>{title}</h3>")
            for name, desc, used in keep:
                key = f" <span style='color:{T('muted')}'>· key for {used}</span>" if used else ""
                html.append(f"<p><b>{name}</b>{key}<br>{desc}</p>")
        self.text.setHtml("".join(html) or "<p>No matches.</p>")
