"""
ui_screens_club.py — My Club screens: Home, Roster, Depth Chart, Tactics,
Staff and Finances.
"""
from collections import Counter

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QComboBox, QDoubleSpinBox, QGridLayout, QHBoxLayout, QLabel, QListWidget,
                             QListWidgetItem, QPushButton, QScrollArea, QSlider, QSpinBox, QTabWidget,
                             QTextBrowser, QVBoxLayout, QWidget)

import capplan
import free_agency as fa
import roster_rules as rr
from coach import COACH_RATINGS, COACH_RATING_LABELS, OFFENSIVE_SCHEMES, DEFENSIVE_SCHEMES
from contracts import market_value
from ratings import (POSITIONS, POSITION_NAMES, key_attributes, attr_abbr, ROSTER_TEMPLATE)
from season import PHASE_TITLES, continue_label
from settings import settings
from stats import summary_line, total_tackles
from team import TACTIC_SLIDERS
from ui_theme import T, accent, attr_color, ca_color, morale_color, ovr_color, result_color
from ui_widgets import (AttrBar, Card, Chip, DataTable, StatTile, TeamBadge, attr_cell, ovr_cell, pot_cell,
                        cell, clear_layout, confirm, divider, filter_chips, form_cell, h_label, info, money,
                        pot_text, personality, screen_header, USER_ROLE)

POS_GROUP_FILTERS = [("ALL", "All"), ("QB", "QB"), ("RB", "RB/FB"), ("WR", "WR"), ("TE", "TE"),
                     ("OL", "OL"), ("DL", "DL"), ("LB", "LB"), ("DB", "DB"), ("ST", "K/P"),
                     ("INJ", "Injured")]
FILTER_POSITIONS = {"QB": {"QB"}, "RB": {"RB", "FB"}, "WR": {"WR"}, "TE": {"TE"},
                    "OL": {"OT", "IOL"}, "DL": {"DT", "EDGE"}, "LB": {"LB"},
                    "DB": {"CB", "S"}, "ST": {"K", "P"}}


ROSTER_FILTERS = POS_GROUP_FILTERS + [("PS", "Practice Squad"), ("IRL", "Injured Reserve")]


def pos_matches(p, f):
    if f == "ALL":
        return True
    if f == "INJ":
        return p.is_injured
    if f == "PS":
        return bool(p.ps)
    if f == "IRL":
        return bool(p.ir)
    return p.position in FILTER_POSITIONS.get(f, {f})


class Screen(QWidget):
    title = ""
    subtitle = ""

    def __init__(self, main):
        super().__init__()
        self.setObjectName("screen")
        self.main = main
        self.outer = QVBoxLayout(self)
        self.outer.setContentsMargins(22, 18, 22, 18)
        self.outer.setSpacing(12)
        self.header = screen_header(self.title, self.subtitle)
        self.outer.addWidget(self.header)

    @property
    def lg(self):
        return self.main.lg

    @property
    def user(self):
        return self.main.lg.user_team

    def set_subtitle(self, text):
        self.header.sub_label.setText(text)

    def refresh(self):
        pass


# ── Home ──────────────────────────────────────────────────────────────────────

class HomeScreen(Screen):
    title = "Home"

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
        lg, team = self.lg, self.user
        clear_layout(self.lay)
        rec = lg.standings[team.abbr]
        conf, div = lg.division_of(team.abbr)
        self.header.title_label.setText(team.full_name)
        self.set_subtitle(f"{lg.name} · {lg.year} · {PHASE_TITLES.get(lg.phase, '')} · "
                          f"{lg.week_label}")

        # Guidance banner
        banner = Card()
        banner.setStyleSheet(f"QFrame#card {{ border-left: 4px solid {accent()}; }}")
        msg = QLabel(self._guidance())
        msg.setWordWrap(True)
        msg.setTextFormat(Qt.TextFormat.RichText)
        banner.add(msg)
        self.lay.addWidget(banner)

        # Tiles
        tiles = QHBoxLayout()
        tiles.setSpacing(10)
        ds = lg.division_standings(conf, div)
        div_rank = [r.abbr for r in ds].index(team.abbr) + 1
        t = StatTile("Record", rec.wlt(), f"{_ordinal(div_rank)} in {conf} {div}")
        tiles.addWidget(t)
        g = max(1, rec.games)
        tiles.addWidget(StatTile("Points / Game", f"{rec.pf / g:.1f}" if rec.games else "—",
                                 f"Allowed {rec.pa / g:.1f}" if rec.games else "Season not started"))
        ranks = sorted(lg.teams.values(), key=lambda x: -x.overall)
        ovr_rank = ranks.index(team) + 1
        from ratings import unit_ovr
        tov = unit_ovr(team.unit_ratings()["OVR"], "OVR")
        t = StatTile("Team Overall", tov, f"#{ovr_rank} of 32")
        t.set(tov, color=ovr_color(tov))
        tiles.addWidget(t)
        space = team.cap_space(lg.salary_cap)
        t = StatTile("Cap Space", money(space), f"Payroll {money(team.payroll)}")
        t.set(money(space), color=T("good") if space > 0 else T("bad"))
        tiles.addWidget(t)
        m = int(team.team_morale)
        t = StatTile("Morale", m, _morale_word(m))
        t.set(m, color=morale_color(m))
        tiles.addWidget(t)
        g = getattr(lg, "gm", None)
        if g:
            oconf = int(g["confidence"])
            exp = (g.get("expectation") or {}).get("label", "")
            t = StatTile("Owner Confidence", f"{oconf}%", exp)
            t.set(f"{oconf}%", color=T("good") if oconf >= 60 else T("warn") if oconf >= 35 else T("bad"))
            tiles.addWidget(t)
        self.lay.addLayout(tiles)

        grid = QGridLayout()
        grid.setSpacing(12)
        grid.addWidget(self._next_game(), 0, 0)
        grid.addWidget(self._division(conf, div), 0, 1)
        grid.addWidget(self._last_game(), 1, 0)
        grid.addWidget(self._leaders(), 1, 1)
        grid.addWidget(self._news(), 2, 0)
        grid.addWidget(self._injuries(), 2, 1)
        grid.setColumnStretch(0, 3)
        grid.setColumnStretch(1, 2)
        self.lay.addLayout(grid)
        self.lay.addStretch(1)

    def _guidance(self):
        lg, team = self.lg, self.user
        ph = lg.phase
        nxt = f"Press <b>{continue_label(lg)}</b> (top right, or Ctrl+Space) when you're ready."
        if ph == "regular":
            injured = [p for p in team.roster if p.is_injured and p.ovr >= 70]
            extra = (f" {len(injured)} key players are injured — check your depth chart (players out "
                     f"4+ weeks can go on injured reserve from the Roster screen)." if injured else "")
            return (f"<b>Regular season.</b> Set your tactics and depth chart, then play.{extra} Your "
                    f"scouts are watching next spring's draft class — put prospects on your focus list "
                    f"on the <b>Draft</b> screen. {nxt}")
        if ph == "playoffs":
            alive = any(team.abbr in v for v in lg.playoff_alive.values())
            return ("<b>Playoffs.</b> " + ("You're still alive — every snap matters. " if alive
                                           else "Your season is over. Scout the draft class while you wait. ")
                    + nxt)
        if ph == "season_end":
            return (f"<b>Season review.</b> Awards are in — see History. Combine results are on the "
                    f"Draft screen, and the owner's verdict is on the Staff screen. {nxt}")
        if ph == "resign":
            n = sum(1 for p in team.roster if p.id in lg.expiring)
            return (f"<b>Re-signing window.</b> {n} of your players have expiring contracts. "
                    f"Re-sign the ones you want in <b>Finances</b> — anyone unsigned becomes a free "
                    f"agent when you continue. You may also <b>franchise-tag</b> one of them. {nxt}")
        if ph == "draft":
            mine = [(r, pk) for r, pk, a in lg.draft_order[lg.draft_index:] if a == team.abbr]
            picks = ", ".join(f"R{r} #{pk}" for r, pk in mine[:7]) or "none left"
            return (f"<b>Draft day.</b> Your remaining picks: {picks}. Make your selections on the "
                    f"<b>Draft</b> screen; continuing auto-drafts any picks you haven't used.")
        if ph == "free_agency":
            return (f"<b>Free agency.</b> Cap space: {money(team.cap_space(lg.salary_cap))}. Make "
                    f"offers on the <b>Free Agency</b> screen before rival teams sign the best "
                    f"players. {nxt}")
        if ph == "preseason":
            over = fa.active_count(team) - settings["roster_size"]
            cut = (f" You're {over} over the {settings['roster_size']}-man limit — release players "
                   f"or the lowest-value ones will be cut automatically." if over > 0 else "")
            return (f"<b>Training camp.</b> Player development happens when the new season starts. "
                    f"Young players you don't need on the 53 can go to the practice squad."
                    f"{cut} {nxt}")
        return nxt

    def _next_game(self):
        lg, team = self.lg, self.user
        card = Card("Next Game")
        game = None
        if lg.phase == "regular":
            for w in range(lg.week, len(lg.schedule)):
                for h, a in lg.schedule[w]:
                    if team.abbr in (h, a):
                        game = (w + 1, h, a)
                        break
                if game:
                    break
        if not game:
            lbl = QLabel("No game scheduled." if lg.phase != "playoffs" else
                         "Playoff matchups are on the Playoffs screen.")
            lbl.setObjectName("muted")
            card.add(lbl)
            return card
        wk, h, a = game
        opp = lg.teams[a if h == team.abbr else h]
        row = QHBoxLayout()
        row.addWidget(TeamBadge(team, 44))
        mid = QVBoxLayout()
        mid.addWidget(h_label(f"Week {wk}: {'vs' if h == team.abbr else '@'} {opp.full_name}", "h3"))
        orec = lg.standings[opp.abbr]
        sub = QLabel(f"{opp.abbr} {orec.wlt()} · OVR {opp.overall} · {opp.coach.off_scheme} / "
                     f"{opp.coach.def_scheme}")
        sub.setObjectName("sub")
        mid.addWidget(sub)
        row.addLayout(mid, 1)
        row.addWidget(TeamBadge(opp, 44))
        card.body.addLayout(row)
        mine, theirs = team.unit_ratings(), opp.unit_ratings()
        for label, a_key, b_key in (("Your offense vs their defense", "OFF", "DEF"),
                                    ("Your defense vs their offense", "DEF", "OFF"),
                                    ("Your QB vs their QB", "QB", "QB")):
            diff = mine[a_key] - theirs[b_key]
            col = T("good") if diff > 4 else T("bad") if diff < -4 else T("text2")
            l = QLabel(f"{label}: <b style='color:{col}'>{int(mine[a_key])} vs {int(theirs[b_key])}</b>")
            l.setTextFormat(Qt.TextFormat.RichText)
            card.add(l)
        return card

    def _last_game(self):
        lg, team = self.lg, self.user
        card = Card("Last Result")
        games = lg.team_results(team.abbr)
        if not games:
            lbl = QLabel("No games played yet this season.")
            lbl.setObjectName("muted")
            card.add(lbl)
            return card
        g = games[-1]
        mine, theirs = g.score_of(team.abbr), g.score_of(g.opponent(team.abbr))
        r = "W" if mine > theirs else "L" if mine < theirs else "T"
        l = QLabel(f"<span style='color:{result_color(r)}; font-weight:800'>{r}</span>  "
                   f"{g.summary()}" + (f"  ·  {g.playoff}" if g.playoff else ""))
        l.setTextFormat(Qt.TextFormat.RichText)
        l.setObjectName("h3")
        card.add(l)
        tops = []
        for pid, line in g.player_stats.items():
            name, pos, abbr, _ = g.player_meta[pid]
            if abbr == team.abbr:
                from stats import fantasy_like_value
                tops.append((fantasy_like_value(line), name, pos, line))
        tops.sort(key=lambda x: -x[0])
        for _, name, pos, line in tops[:3]:
            lbl = QLabel(f"<b>{name}</b> ({pos}) — {summary_line(line, pos)}")
            lbl.setTextFormat(Qt.TextFormat.RichText)
            card.add(lbl)
        btn = QPushButton("Open in Game Center")
        btn.setObjectName("ghost")
        btn.clicked.connect(lambda: self.main.open_game(g))
        card.add(btn)
        return card

    def _division(self, conf, div):
        lg = self.lg
        card = Card(f"{conf} {div}")
        table = DataTable(["Team", "W", "L", "T", "PF", "PA", "Strk"], stretch=0, sortable=False)
        rows, keys = [], []
        for r in lg.division_standings(conf, div):
            t = lg.teams[r.abbr]
            mine = r.abbr == lg.user_abbr
            rows.append([cell(t.full_name, bold=mine, color=accent() if mine else None),
                         r.w, r.l, r.t, r.pf, r.pa, r.streak])
            keys.append(r.abbr)
        table.set_rows(rows, keys)
        table.fit_height()
        table.on_activate = self.main.open_team
        card.add(table)
        return card

    def _leaders(self):
        team = self.user
        card = Card("Team Leaders")
        cats = [("Passing", "pass_yds", "yds"), ("Rushing", "rush_yds", "yds"),
                ("Receiving", "rec_yds", "yds"), ("Tackles", None, "tkl"),
                ("Sacks", "sacks", "sk"), ("Interceptions", "def_int", "int")]
        for label, key, unit in cats:
            if key is None:
                best = max(team.roster, key=lambda p: total_tackles(p.season_stats))
                v = total_tackles(best.season_stats)
            else:
                best = max(team.roster, key=lambda p: p.season_stats[key])
                v = best.season_stats[key]
            txt = f"<span style='color:{T('muted')}'>{label}</span>  <b>{best.name}</b> " \
                  f"({best.position}) {v:g} {unit}" if v else \
                  f"<span style='color:{T('muted')}'>{label}</span>  —"
            l = QLabel(txt)
            l.setTextFormat(Qt.TextFormat.RichText)
            card.add(l)
        return card

    def _news(self):
        lg = self.lg
        card = Card("Latest News")
        items = [n for n in reversed(lg.news) if n[4] == lg.user_abbr or n[2] in
                 ("Championship", "Awards", "League", "Hall of Fame", "Trade", "Coaching")][:10]
        box = QTextBrowser()
        box.setOpenExternalLinks(False)
        box.setMinimumHeight(240)
        box.setHtml(news_html(items))
        card.add(box)
        return card

    def _injuries(self):
        team = self.user
        card = Card("Injury Report")
        inj = sorted((p for p in team.roster if p.is_injured), key=lambda p: -p.ovr)
        if not inj:
            lbl = QLabel("No injuries. Full strength.")
            lbl.setObjectName("muted")
            card.add(lbl)
        for p in inj[:8]:
            wk = max(0, p.injury["weeks"])
            l = QLabel(f"<b>{p.name}</b> {p.position} — {p.injury['name']}, "
                       f"<span style='color:{T('bad')}'>{'season' if p.injury.get('season_ending') else f'{wk} wk'}</span>")
            l.setTextFormat(Qt.TextFormat.RichText)
            card.add(l)
        card.body.addStretch(1)
        return card


def _ordinal(n):
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(n, f"{n}th")


def _morale_word(m):
    if m >= 80:
        return "Superb"
    if m >= 65:
        return "Good"
    if m >= 50:
        return "Okay"
    if m >= 35:
        return "Poor"
    return "Very poor"


NEWS_COLORS = {"Injury": "bad", "Championship": "gold", "Awards": "gold", "Hall of Fame": "gold",
               "Trade": "info", "Signing": "info", "Release": "warn", "Coaching": "warn",
               "Draft": "info", "Performance": "good", "Development": "good", "Shortlist": "info",
               "Front Office": "warn"}


def news_html(items):
    rows = []
    for year, wk, cat, text, team in items:
        col = T(NEWS_COLORS.get(cat, "text2"))
        rows.append(f"<div style='margin:0 0 9px 0'><span style='color:{col}; font-weight:700'>"
                    f"{cat.upper()}</span> <span style='color:{T('muted')}'>· {year} {wk}"
                    f"{' · ' + team if team else ''}</span><br>"
                    f"<span style='color:{T('text')}'>{text}</span></div>")
    if not rows:
        rows.append(f"<span style='color:{T('muted')}'>Nothing yet.</span>")
    return "".join(rows)


# ── Roster ────────────────────────────────────────────────────────────────────

class RosterScreen(Screen):
    title = "Roster"

    def __init__(self, main):
        super().__init__(main)
        self.filter = "ALL"
        chips, self.get_filter = filter_chips(ROSTER_FILTERS, self._set_filter)
        self.outer.addWidget(chips)
        self.table = DataTable([], stretch=1)
        self.table.on_activate = self.main.open_player
        self.outer.addWidget(self.table, 1)
        row = QHBoxLayout()
        self.summary = QLabel("")
        self.summary.setObjectName("sub")
        row.addWidget(self.summary)
        row.addStretch(1)
        view = QPushButton("View Profile")
        view.clicked.connect(lambda: self._with_selected(self.main.open_player))
        row.addWidget(view)
        ir = QPushButton("Injured Reserve")
        ir.setToolTip("Place a player out 4+ weeks on IR, or activate a healthy player from IR")
        ir.clicked.connect(self._toggle_ir)
        row.addWidget(ir)
        ps = QPushButton("Practice Squad")
        ps.setToolTip("Move a young player to the practice squad, or promote one to the active roster")
        ps.clicked.connect(self._toggle_ps)
        row.addWidget(ps)
        rel = QPushButton("Release…")
        rel.setObjectName("danger")
        rel.clicked.connect(self._release)
        row.addWidget(rel)
        self.outer.addLayout(row)

    def _set_filter(self, f):
        self.filter = f
        self.refresh()

    def _with_selected(self, fn):
        pid = self.table.selected_key()
        if pid is not None:
            fn(pid)

    def _selected_player(self):
        pid = self.table.selected_key()
        p = self.lg.find_player(pid) if pid is not None else None
        if p is None or p.team != self.lg.user_abbr:
            return None
        return p

    def _toggle_ir(self):
        p = self._selected_player()
        if p is None:
            return
        if p.ir:
            ok, msg = rr.activate_ir(self.lg, self.user, p)
        else:
            ok, msg = rr.place_ir(self.lg, self.user, p)
        info(self, "Injured reserve", msg)
        self.main.refresh_all()

    def _toggle_ps(self):
        p = self._selected_player()
        if p is None:
            return
        if p.ps:
            ok, msg = rr.promote(self.lg, self.user, p)
        else:
            ok, why = rr.can_move_to_ps(self.lg, self.user, p)
            if not ok:
                info(self, "Practice squad", why)
                return
            if not confirm(self, "Practice squad",
                           f"Move {p.name} to the practice squad? His contract becomes a one-year "
                           f"practice-squad deal ({money(rr.ps_salary(self.lg.salary_cap))}) and other "
                           f"teams may sign him away."):
                return
            ok, msg = rr.move_to_ps(self.lg, self.user, p)
        info(self, "Practice squad", msg)
        self.main.refresh_all()

    def _release(self):
        pid = self.table.selected_key()
        p = self.lg.find_player(pid) if pid is not None else None
        if p is None or p.team != self.lg.user_abbr:
            return
        if confirm(self, "Release player", f"Release {p.name} ({p.position}, {p.ovr} OVR)? "
                                           f"Part of his {money(p.salary)} salary becomes dead cap."):
            fa.release(self.lg, self.user, p)
            self.main.refresh_all()

    def refresh(self):
        lg, team = self.lg, self.user
        scouting = team.scouting
        players = [p for p in team.roster if pos_matches(p, self.filter)]
        players.sort(key=lambda p: (POSITIONS.index(p.position), -p.ca))
        single = None
        if self.filter in FILTER_POSITIONS and len(FILTER_POSITIONS[self.filter]) == 1:
            single = next(iter(FILTER_POSITIONS[self.filter]))
        keys_attr = key_attributes(single, 6) if single else []
        cols = ["Name", "#", "Pos", "Age", "OVR", "POT", "Best Role", "Morale", "Form", "Salary",
                "Yrs", "Status"]
        cols += [attr_abbr(a) for a in keys_attr]
        cols += ["Season"]
        if self.table.columns != cols:
            self.table.columns = cols
            self.table.setColumnCount(len(cols))
            self.table.setHorizontalHeaderLabels(cols)
        rows, keys = [], []
        show_ca = settings["show_ca_number"]
        for p in players:
            status = ""
            col = None
            if p.injury:
                status = f"{p.injury['name']} ({max(0, p.injury['weeks'])}w)"
                col = T("bad")
            if p.ir:
                status = "IR" + (f" · {status}" if status else "")
                col = T("bad")
            elif p.ps:
                status, col = "Practice squad", T("muted")
            elif p.injury:
                pass
            elif p.id in lg.expiring:
                status, col = "Expiring", T("warn")
            elif p.on_rookie_deal:
                status = "Rookie deal"
            role, rv = p.best_role
            row = [cell(p.name, bold=p.ovr >= 85), p.jersey,
                   cell(p.position, POSITIONS.index(p.position)), p.age, ovr_cell(p.ovr, show_ca),
                   pot_cell(p, scouting),
                   cell(f"{role} {rv}", rv),
                   cell(p.morale, p.morale, color=morale_color(p.morale)), form_cell(p),
                   cell(money(p.salary), p.salary), p.contract_years, cell(status, color=col)]
            row += [attr_cell(p.attrs[a]) for a in keys_attr]
            row += [summary_line(p.season_stats, p.position) if p.season_stats["gp"] else ""]
            rows.append(row)
            keys.append(p.id)
        self.table.set_rows(rows, keys)
        n = len(team.roster)
        active = fa.active_count(team)
        self.set_subtitle(f"{team.full_name} · {n} players ({active} active, limit "
                          f"{fa.roster_limit(lg)}) · Double-click a player for his full profile")
        avg_age = sum(p.age for p in team.roster) / max(1, n)
        self.summary.setText(f"Average age {avg_age:.1f} · Practice squad {len(rr.practice_squad(team))}/"
                             f"{rr.ps_size()} · IR {len(rr.injured_reserve(team))} · "
                             f"Cap space {money(team.cap_space(lg.salary_cap))}")


# ── Depth chart ───────────────────────────────────────────────────────────────

DEPTH_SLOTS = POSITIONS + ["KR", "PR"]
STARTERS = {"QB": 1, "RB": 1, "FB": 1, "WR": 3, "TE": 1, "OT": 2, "IOL": 3, "DT": 2,
            "EDGE": 2, "LB": 3, "CB": 3, "S": 2, "K": 1, "P": 1, "KR": 1, "PR": 1}


class DepthChartScreen(Screen):
    title = "Depth Chart"
    subtitle = "Order players at each position. Starters are highlighted; injured players are skipped on game day."

    def __init__(self, main):
        super().__init__(main)
        body = QHBoxLayout()
        body.setSpacing(12)
        self.slots = QListWidget()
        self.slots.setMaximumWidth(190)
        for s in DEPTH_SLOTS:
            label = {"KR": "Kick Returner", "PR": "Punt Returner"}.get(s, f"{s} · {POSITION_NAMES[s]}"
                                                                           if s in POSITION_NAMES else s)
            it = QListWidgetItem(label)
            it.setData(USER_ROLE, s)
            self.slots.addItem(it)
        self.slots.currentRowChanged.connect(lambda _r: self._show_slot())
        body.addWidget(self.slots)

        mid = QVBoxLayout()
        self.slot_title = h_label("", "h2")
        mid.addWidget(self.slot_title)
        self.order = DataTable(["#", "Name", "Pos", "Age", "Rating", "Stamina", "Snap %", "Status"],
                               stretch=1, sortable=False)
        mid.addWidget(self.order, 1)
        rot = QHBoxLayout()
        rot.addWidget(QLabel("Rotation:"))
        self.rot_combo = QComboBox()
        for key, label in (("none", "Starters play every snap"), ("light", "Light rotation"),
                           ("normal", "Normal rotation"), ("heavy", "Heavy rotation (keep them fresh)")):
            self.rot_combo.addItem(label, key)
        self.rot_combo.currentIndexChanged.connect(lambda _i: self._rotation_changed())
        rot.addWidget(self.rot_combo)
        self.rot_note = QLabel("")
        self.rot_note.setObjectName("muted")
        self.rot_note.setWordWrap(True)
        rot.addWidget(self.rot_note, 1)
        mid.addLayout(rot)
        btns = QHBoxLayout()
        for label, fn in (("▲ Up", lambda: self._move(-1)), ("▼ Down", lambda: self._move(1)),
                          ("Make Starter", self._to_top), ("Reset to Auto", self._reset)):
            b = QPushButton(label)
            b.clicked.connect(fn)
            btns.addWidget(b)
        btns.addStretch(1)
        mid.addLayout(btns)
        body.addLayout(mid, 3)

        self.lineup = Card("Game-Day Lineup")
        self.lineup_text = QLabel()
        self.lineup_text.setTextFormat(Qt.TextFormat.RichText)
        self.lineup_text.setWordWrap(True)
        self.lineup.add(self.lineup_text)
        self.lineup.body.addStretch(1)
        self.lineup.setMinimumWidth(300)
        body.addWidget(self.lineup, 2)
        self.outer.addLayout(body, 1)
        self.slots.setCurrentRow(0)

    def _slot(self):
        it = self.slots.currentItem()
        return it.data(USER_ROLE) if it else "QB"

    def _candidates(self, slot):
        team = self.user
        if slot in ("KR", "PR"):
            pool = [p for p in team.roster if p.position in ("RB", "WR", "CB", "S")]
            order = team.depth_overrides.get(slot, [])
            rank = {pid: i for i, pid in enumerate(order)}
            return sorted(pool, key=lambda p: (rank.get(p.id, 999), -p.return_rating))
        return team.depth(slot, include_injured=True)

    def _rating(self, p, slot):
        return p.return_rating if slot in ("KR", "PR") else p.ovr_at(slot)

    def _show_slot(self):
        slot = self._slot()
        self.slot_title.setText({"KR": "Kick Returner", "PR": "Punt Returner"}.get(
            slot, POSITION_NAMES.get(slot, slot)))
        players = self._candidates(slot)
        rows, keys = [], []
        n_start = STARTERS.get(slot, 1)
        healthy_rank = 0
        team = self.user
        unit = "def_snaps" if slot in ("DT", "EDGE", "LB", "CB", "S") else "off_snaps"
        team_snaps = max([p.season_stats[unit] for p in team.roster] + [1])
        for i, p in enumerate(players):
            starter = False
            if not p.is_injured and not p.holdout:
                healthy_rank += 1
                starter = healthy_rank <= n_start
            share = 100.0 * p.season_stats[unit] / team_snaps
            status = (f"{p.injury['name']} ({max(0, p.injury['weeks'])}w)" if p.injury else
                      "Holding out" if p.holdout else ("Starter" if starter else ""))
            rows.append([cell(i + 1, i), cell(p.name, bold=starter, color=accent() if starter else None),
                         p.position, p.age, ovr_cell(self._rating(p, slot)),
                         cell(p.attrs.get("stamina", 0), p.attrs.get("stamina", 0)),
                         cell(f"{share:.0f}%" if p.season_stats[unit] else "—", share),
                         cell(status, color=T("bad") if (p.injury or p.holdout) else None)])
            keys.append(p.id)
        self.order.set_rows(rows, keys)
        self._show_rotation(slot)
        self._lineup()

    ROT_GROUPS = {"DT": "DL", "EDGE": "DL", "LB": "LB", "CB": "DB", "S": "DB", "WR": "WR", "TE": "TE",
                  "RB": "RB", "OT": "OL", "IOL": "OL"}

    def _show_rotation(self, slot):
        grp = self.ROT_GROUPS.get(slot)
        self.rot_combo.setEnabled(grp is not None)
        self.rot_combo.blockSignals(True)
        cur = (self.user.rotation or {}).get(grp, "normal") if grp else "normal"
        self.rot_combo.setCurrentIndex(max(0, self.rot_combo.findData(cur)))
        self.rot_combo.blockSignals(False)
        self.rot_note.setText(
            f"Applies to the whole {grp} group. Tired players lose speed, strength and technique and get "
            "hurt more; fresher backups come in when they're the better option at that moment."
            if grp else "Quarterbacks, kickers and returners don't rotate (except in blowouts).")

    def _rotation_changed(self):
        grp = self.ROT_GROUPS.get(self._slot())
        if not grp:
            return
        team = self.user
        rot = dict(team.rotation or {})
        rot[grp] = self.rot_combo.currentData()
        team.rotation = rot

    def _set_order(self, ids):
        self.user.depth_overrides[self._slot()] = ids
        self._show_slot()

    def _move(self, d):
        players = self._candidates(self._slot())
        ids = [p.id for p in players]
        pid = self.order.selected_key()
        if pid not in ids:
            return
        i = ids.index(pid)
        j = i + d
        if 0 <= j < len(ids):
            ids[i], ids[j] = ids[j], ids[i]
            self._set_order(ids)
            self.order.selectRow(j)

    def _to_top(self):
        players = self._candidates(self._slot())
        ids = [p.id for p in players]
        pid = self.order.selected_key()
        if pid in ids:
            ids.remove(pid)
            self._set_order([pid] + ids)

    def _reset(self):
        self.user.depth_overrides.pop(self._slot(), None)
        self._show_slot()

    def _lineup(self):
        team = self.user
        s = team.starters()
        kr, pr = team.returner("KR"), team.returner("PR")

        def line(pos, players):
            return f"<b>{pos}</b> " + ", ".join(
                f"{p.name} <span style='color:{ovr_color(p.ovr_at(pos))}'>{p.ovr_at(pos)}</span>"
                for p in players)
        off = [line(k, s[k]) for k in ("QB", "RB", "WR", "TE", "OT", "IOL")]
        de = [line(k, s[k]) for k in ("DT", "EDGE", "LB", "CB", "S")]
        st = [line(k, s[k]) for k in ("K", "P")]
        st.append(f"<b>KR</b> {kr.name if kr else '—'} · <b>PR</b> {pr.name if pr else '—'}")
        self.lineup_text.setText("<br>".join(["<u>Offense</u>"] + off + ["", "<u>Defense</u>"] + de
                                             + ["", "<u>Special Teams</u>"] + st))

    def refresh(self):
        self._show_slot()


# ── Tactics ───────────────────────────────────────────────────────────────────

class TacticsScreen(Screen):
    title = "Tactics"
    subtitle = ("Sliders shift your team away from the head coach's natural tendencies. "
                "50 = follow the coach.")

    def __init__(self, main):
        super().__init__(main)
        body = QHBoxLayout()
        body.setSpacing(12)
        left = Card("Game Plan")
        self.sliders = {}
        for key, (label, desc) in TACTIC_SLIDERS.items():
            lbl = QLabel(label)
            lbl.setObjectName("h3")
            left.add(lbl)
            row = QHBoxLayout()
            s = QSlider(Qt.Orientation.Horizontal)
            s.setRange(0, 100)
            s.setSingleStep(5)
            s.setPageStep(10)
            val = QLabel("50")
            val.setMinimumWidth(30)
            s.valueChanged.connect(lambda v, k=key, l=val: self._changed(k, v, l))
            row.addWidget(s, 1)
            row.addWidget(val)
            left.body.addLayout(row)
            d = QLabel(desc)
            d.setObjectName("muted")
            left.add(d)
            self.sliders[key] = (s, val)
        reset = QPushButton("Reset to Coach Defaults")
        reset.clicked.connect(self._reset)
        left.add(reset)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(left)
        body.addWidget(scroll, 3)

        right = QVBoxLayout()
        self.coach_card = Card("Coaching Philosophy")
        self.coach_text = QLabel()
        self.coach_text.setTextFormat(Qt.TextFormat.RichText)
        self.coach_text.setWordWrap(True)
        self.coach_card.add(self.coach_text)
        right.addWidget(self.coach_card)
        self.proj_card = Card("Projected Tendencies")
        self.proj_text = QLabel()
        self.proj_text.setTextFormat(Qt.TextFormat.RichText)
        self.proj_text.setWordWrap(True)
        self.proj_card.add(self.proj_text)
        right.addWidget(self.proj_card)
        self.pb_card = Card("Playbook")
        self.pb_kind = QComboBox()
        self.pb_kind.addItems(["Pass plays", "Run plays", "Defense", "Special teams"])
        self.pb_kind.currentIndexChanged.connect(lambda _i: self._refresh_playbook())
        self.pb_card.add(self.pb_kind)
        self.pb_table = DataTable(["Play", "Type", "Coach likes", "Your call"], stretch=0)
        self.pb_card.add(self.pb_table)
        self.pb_desc = QLabel("")
        self.pb_desc.setObjectName("muted")
        self.pb_desc.setWordWrap(True)
        self.pb_card.add(self.pb_desc)
        self.pb_table.itemSelectionChanged.connect(self._pb_selected)
        brow = QHBoxLayout()
        for label, val in (("Feature", 2.0), ("Normal", 1.0), ("Remove", 0.0)):
            b = QPushButton(label)
            b.clicked.connect(lambda _c=False, v=val: self._set_pref(v))
            brow.addWidget(b)
        self.pb_card.body.addLayout(brow)
        note = QLabel("Featured calls are made twice as often; removed calls are never made "
                      "(forced situations such as onside kicks still happen). "
                      "Custom plays from the playbooks folder appear under Pass plays.")
        note.setObjectName("muted")
        note.setWordWrap(True)
        self.pb_card.add(note)
        right.addWidget(self.pb_card, 1)
        body.addLayout(right, 2)
        self.outer.addLayout(body, 1)
        self._loading = False

    def _playbook_entries(self):
        """(key, name, type, coach-like weight, description) for the selected category."""
        import playbook as pb
        import defense as dlib
        import specialteams as stl
        team = self.user
        kind = self.pb_kind.currentIndex() if hasattr(self, "pb_kind") else 0
        out = []
        if kind == 0:
            likes = pb.SCHEME_CONCEPTS.get(team.coach.off_scheme, {})
            for play in pb.PASS_PLAYS:
                if play.get("cls") == "hail":
                    continue
                typ = ("RPO " if play.get("rpo") else "play-action " if play.get("pa") else "") + play["cls"]
                if play.get("forms"):
                    typ += " (" + "/".join(play["forms"]) + ")"
                routes = ", ".join(f"{s} {r}" for s, r in play["routes"].items() if r != "block")
                out.append((play["name"], play["name"], typ, likes.get(play["name"], 1.0), routes))
        elif kind == 1:
            likes = pb.SCHEME_RUNS.get(team.coach.off_scheme, {})
            for name, desc in pb.RUN_CONCEPT_INFO.items():
                out.append(("run:" + name, name.title(), "option" if "option" in desc.lower() or
                            name in ("zone read", "inverted veer", "midline") else "run",
                            1.0 + likes.get(name, 0.0), desc))
        elif kind == 2:
            likes = dlib.SCHEME_CALLS.get(team.coach.def_scheme, {})
            for name in dlib.ALL_CALLS:
                typ = ("front" if name in dlib.FRONTS else "pressure" if name in dlib.PRESSURES
                       else "line game" if name.startswith("Stunt") or name in dlib.SIM_PRESSURE
                       else "coverage")
                out.append(("def:" + name, name, typ, likes.get(name, 1.0), dlib.describe(name)))
        else:
            groups = ((stl.KICKOFFS, "kickoff"), (stl.KICK_RETURNS, "kick return"), (stl.PUNTS, "punt"),
                      (stl.PUNT_RETURNS, "punt return"), (stl.FG_DEFENSE, "field goal defence"))
            for d, typ in groups:
                for name in d:
                    out.append(("st:" + name, name, typ, 1.0, d[name]))
        return out

    def _refresh_playbook(self):
        team = self.user
        prefs = getattr(team, "play_prefs", None) or {}
        rows, keys = [], []
        self._pb_desc = {}
        for key, name, typ, like, desc in self._playbook_entries():
            v = prefs.get(key, 1.0)
            call = "Featured" if v >= 2 else "Removed" if v <= 0 else "Normal"
            rows.append([name, typ,
                         cell("Favourite" if like >= 2 else "Likes" if like > 1 else
                              "Avoids" if like < 1 else "—", like),
                         cell(call, v, color=T("good") if v >= 2 else T("bad") if v <= 0 else None)])
            keys.append(key)
            self._pb_desc[key] = f"<b>{name}</b> — {desc}" if desc else ""
        self.pb_table.set_rows(rows, keys)
        self.pb_desc.setText("")

    def _pb_selected(self):
        key = self.pb_table.selected_key()
        self.pb_desc.setText(getattr(self, "_pb_desc", {}).get(key, "") if key else "")

    def _set_pref(self, v):
        name = self.pb_table.selected_key()
        if not name:
            return
        team = self.user
        if not hasattr(team, "play_prefs") or team.play_prefs is None:
            team.play_prefs = {}
        if v == 1.0:
            team.play_prefs.pop(name, None)
        else:
            team.play_prefs[name] = v
        self._refresh_playbook()

    def _changed(self, key, v, label):
        label.setText(str(v))
        if self._loading:
            return
        team = self.user
        if team.tactics is None:
            from season import default_tactics
            team.tactics = default_tactics()
        team.tactics[key] = v
        self._projection()

    def _reset(self):
        from season import default_tactics
        self.user.tactics = default_tactics()
        self.refresh()

    def _projection(self):
        team = self.user
        plan = team.gameplan()
        pr = plan["pass_rate"]
        deep = 0.115 + 0.07 * plan["deep"]
        self.proj_text.setText(
            f"Neutral-down pass rate: <b>{pr * 100:.0f}%</b><br>"
            f"Deep shots: <b>{max(0, deep) * 100:.0f}%</b> of passes · Screens: "
            f"<b>{(0.025 + 0.09 * plan['screen']) * 100:.0f}%</b><br>"
            f"Outside runs: <b>{plan['outside'] * 75:.0f}%</b> · Designed QB runs: "
            f"<b>{plan['qb_run'] * 16:.0f}%</b> of runs<br>"
            f"Tempo: <b>{_word(plan['tempo'], ('Methodical', 'Steady', 'Up-tempo', 'Hurry-up'))}</b> · "
            f"4th-down aggression: <b>{_word(plan['aggression'], ('Very cautious', 'Cautious', 'Bold', 'Very bold'))}</b><br>"
            f"Blitz rate: <b>{plan['blitz'] * 55:.0f}%</b> of dropbacks · Zone: <b>{plan['zone'] * 100:.0f}%</b> · "
            f"Two-high shells: <b>{plan['two_high'] * 100:.0f}%</b><br>"
            f"Backfield: <b>{_word(1 - plan['committee'], ('Full committee', 'Rotation', 'Lead back', 'Bell-cow'))}</b>"
            f"{self._backfield_note(team)}")

    def _backfield_note(self, team):
        rbs = team.lineup("RB", 2)
        if not rbs:
            return ""
        return f" · lead back <b>{rbs[0].name}</b> (stamina {rbs[0].a('stamina')})"

    def refresh(self):
        team = self.user
        c = team.coach
        t = c.tendencies
        self._refresh_playbook()
        self.coach_text.setText(
            f"<b>{c.name}</b> runs a <b>{c.off_scheme}</b> offense and a <b>{c.def_scheme}</b> "
            f"defense.<br>Natural pass lean {t['pass_lean']:+.2f} · deep {t['deep']:+.2f} · "
            f"blitz {t['blitz']:.2f} · zone {t['zone']:.2f}<br>"
            f"Adaptability {c.ratings['adaptability']}/20 — adaptable coaches lean further into "
            f"your roster's strengths.")
        self._loading = True
        tac = team.tactics or {}
        for key, (s, val) in self.sliders.items():
            v = int(tac.get(key, 50))
            s.setValue(v)
            val.setText(str(v))
        self._loading = False
        self._projection()


def _word(v, words):
    return words[min(len(words) - 1, int(v * len(words)))]


# ── Staff ─────────────────────────────────────────────────────────────────────

class StaffScreen(Screen):
    title = "Staff"
    subtitle = ("Coordinators call the plays, position coaches develop players, scouts learn the "
                "draft class and the owner judges you.")

    def __init__(self, main):
        super().__init__(main)
        self.tabs = QTabWidget()
        self.outer.addWidget(self.tabs, 1)

        # Head coach
        hc = QWidget()
        body = QHBoxLayout(hc)
        body.setContentsMargins(0, 8, 0, 0)
        body.setSpacing(12)
        self.coach_card = Card("Head Coach")
        self.coach_box = QVBoxLayout()
        self.coach_card.body.addLayout(self.coach_box)
        self.coach_card.body.addStretch(1)
        self.coach_card.setMinimumWidth(380)
        body.addWidget(self.coach_card, 2)
        right = QVBoxLayout()
        pool_card = Card("Available Head Coaches")
        self.pool = DataTable(["Name", "Age", "Overall", "Offense", "Defense", "Dev", "Record",
                               "Scheme"], stretch=0)
        pool_card.add(self.pool)
        hire = QPushButton("Hire Selected Coach")
        hire.setObjectName("primary")
        hire.clicked.connect(self._hire)
        pool_card.add(hire)
        right.addWidget(pool_card, 1)
        self.club_card = Card("Club Facilities")
        self.club_text = QLabel()
        self.club_text.setTextFormat(Qt.TextFormat.RichText)
        self.club_text.setWordWrap(True)
        self.club_card.add(self.club_text)
        right.addWidget(self.club_card)
        body.addLayout(right, 3)
        self.tabs.addTab(hc, "Head Coach")

        # Assistants
        asst = QWidget()
        al = QHBoxLayout(asst)
        al.setContentsMargins(0, 8, 0, 0)
        al.setSpacing(12)
        mine = Card("Your Coaching Staff")
        self.staff_table = DataTable(["Role", "Name", "Age", "Overall", "Teaching", "Tactics",
                                      "Motivation", "Seasons"], stretch=1, sortable=False)
        self.staff_table.itemSelectionChanged.connect(self._staff_selected)
        mine.add(self.staff_table)
        note = QLabel("Coordinators' tactics drive play-calling; teaching drives development at "
                      "the positions each coach looks after.")
        note.setObjectName("muted")
        note.setWordWrap(True)
        mine.add(note)
        al.addWidget(mine, 3)
        avail = Card("Available")
        self.avail_table = DataTable(["Name", "Role", "Age", "Overall", "Teaching", "Tactics",
                                      "Motivation"], stretch=0)
        avail.add(self.avail_table)
        hire_s = QPushButton("Hire for Selected Role")
        hire_s.setObjectName("primary")
        hire_s.clicked.connect(self._hire_staff)
        avail.add(hire_s)
        al.addWidget(avail, 3)
        self.tabs.addTab(asst, "Coaching Staff")

        # Scouts
        sc = QWidget()
        sl = QHBoxLayout(sc)
        sl.setContentsMargins(0, 8, 0, 0)
        sl.setSpacing(12)
        mine_s = Card("Your Scouts")
        self.scout_table = DataTable(["Name", "Age", "Region", "Judge Ability", "Judge Potential"],
                                     stretch=0, sortable=False)
        mine_s.add(self.scout_table)
        row = QHBoxLayout()
        row.addWidget(QLabel("Assign region:"))
        self.region = QComboBox()
        import staff as staff_mod
        for r in staff_mod.REGIONS:
            self.region.addItem(r, r)
        row.addWidget(self.region)
        assign = QPushButton("Assign")
        assign.clicked.connect(self._assign_region)
        row.addWidget(assign)
        fire = QPushButton("Release Scout")
        fire.clicked.connect(self._fire_scout)
        row.addWidget(fire)
        mine_s.body.addLayout(row)
        self.scout_note = QLabel()
        self.scout_note.setObjectName("muted")
        self.scout_note.setWordWrap(True)
        mine_s.add(self.scout_note)
        sl.addWidget(mine_s, 3)
        pool_s = Card("Available Scouts")
        self.scout_pool = DataTable(["Name", "Age", "Region", "Judge Ability", "Judge Potential"],
                                    stretch=0)
        pool_s.add(self.scout_pool)
        hire_sc = QPushButton("Hire Scout")
        hire_sc.setObjectName("primary")
        hire_sc.clicked.connect(self._hire_scout)
        pool_s.add(hire_sc)
        sl.addWidget(pool_s, 2)
        self.tabs.addTab(sc, "Scouting")

        # Owner
        ow = QWidget()
        ol = QVBoxLayout(ow)
        ol.setContentsMargins(0, 8, 0, 0)
        self.owner_card = Card("Owner")
        self.owner_text = QLabel()
        self.owner_text.setTextFormat(Qt.TextFormat.RichText)
        self.owner_text.setWordWrap(True)
        self.owner_card.add(self.owner_text)
        self.conf_bar = AttrBar("Owner confidence in you", 50)
        self.owner_card.add(self.conf_bar)
        ol.addWidget(self.owner_card)
        hist_card = Card("Your Record as General Manager")
        self.gm_table = DataTable(["Year", "Team", "Record", "Goal", "Met", "Confidence"],
                                  stretch=3, sortable=False)
        hist_card.add(self.gm_table)
        ol.addWidget(hist_card, 1)
        self.tabs.addTab(ow, "Owner")

    # ── Refresh ─────────────────────────────────────────────────────────────

    def refresh(self):
        import staff as staff_mod
        staff_mod.ensure_league(self.lg)
        team = self.user
        c = team.coach
        clear_layout(self.coach_box)
        self.coach_box.addWidget(h_label(f"{c.name}", "h2"))
        meta = QLabel(f"Age {c.age} · {c.record_str} career ({c.win_pct:.3f}) · {c.titles} titles · "
                      f"Reputation {c.reputation}"
                      + (f"<br>Coaching tree: learned under {c.mentor} ({c.tree_origin})" if c.mentor else ""))
        meta.setTextFormat(Qt.TextFormat.RichText)
        meta.setWordWrap(True)
        meta.setObjectName("sub")
        self.coach_box.addWidget(meta)
        self.coach_box.addWidget(QLabel(f"<b>{c.off_scheme}</b> offense · <b>{c.def_scheme}</b> defense"))
        for r in COACH_RATINGS:
            self.coach_box.addWidget(AttrBar(COACH_RATING_LABELS[r], c.ratings[r] * 5,
                                             tip=f"{c.ratings[r]}/20"))
        rows, keys = [], []
        for pc in sorted(self.lg.coach_pool, key=lambda x: -x.overall):
            rows.append([pc.name, pc.age, cell(f"{pc.overall:.1f}", pc.overall, bold=True),
                         pc.ratings["offense"], pc.ratings["defense"], pc.ratings["development"],
                         pc.record_str, f"{pc.off_scheme} / {pc.def_scheme}"])
            keys.append(id(pc))
        self.pool.set_rows(rows, keys)
        self.club_text.setText(
            f"Training facilities: <b>{team.facilities}/20</b> — speeds up player development.<br>"
            f"Scouting department: <b>{team.scouting}/20</b> — how much every scout learns each week.<br>"
            f"Fan support: <b>{team.fan_support}/100</b> — makes free agents more willing to sign.<br>"
            f"Play-calling: offense <b>{staff_mod.off_calling(team):.1f}</b>, defense "
            f"<b>{staff_mod.def_calling(team):.1f}</b> (head coach and coordinators combined).")
        # Staff
        rows, keys = [], []
        for role, (title, poss, _) in staff_mod.STAFF_ROLES.items():
            m = team.staff[role]
            rows.append([cell(title, bold=role in ("OC", "DC")), m.name, m.age,
                         cell(f"{m.overall:.1f}", m.overall, bold=True), m.r("teaching"),
                         m.r("tactics"), m.r("motivation"), m.seasons])
            keys.append(role)
        self.staff_table.set_rows(rows, keys)
        self._staff_selected()
        # Scouts
        rows, keys = [], []
        for s in team.scouts:
            rows.append([s.name, s.age, s.region, s.ability, s.potential])
            keys.append(id(s))
        self.scout_table.set_rows(rows, keys)
        covered = sorted({s.region for s in team.scouts})
        missing = [r for r in staff_mod.REGIONS if r not in covered]
        self.scout_note.setText(f"Covered: {', '.join(covered) or 'none'}. "
                                + (f"Not covered: {', '.join(missing)} — prospects there are only "
                                   f"known from film." if missing else "Every region is covered."))
        rows, keys = [], []
        for s in sorted(self.lg.scout_pool, key=lambda x: -x.overall):
            rows.append([s.name, s.age, s.region, s.ability, s.potential])
            keys.append(id(s))
        self.scout_pool.set_rows(rows, keys)
        # Owner
        g = self.lg.gm
        exp = g.get("expectation") or {}
        o = team.owner
        patience = "very patient" if o.patience >= 15 else "patient" if o.patience >= 10 else \
            "impatient" if o.patience >= 6 else "ruthless"
        import front_office as fo
        fo.owner_traits(o)
        otype = fo.owner_type(o)
        self.owner_text.setText(
            f"<b>{o.name}</b> · {patience} · ambition {o.ambition}/20 · spending {o.spending}/20 · "
            f"meddling {o.meddling}/20<br>"
            f"<b>{otype}</b>: {fo.OWNER_TYPES[otype]}<br>"
            f"Goal for {exp.get('year', self.lg.year)}: <b>{exp.get('label', '—')}</b>"
            f" (around {exp.get('wins', '?')} wins)<br>"
            f"Your reputation around the league: <b>{g['reputation']}</b>/100")
        self.conf_bar.value = int(g["confidence"])
        self.conf_bar.update()
        self.gm_table.set_rows([[h["year"], h["team"], h["record"], h["expectation"],
                                 cell("Yes" if h["met"] else "No",
                                      color=T("good") if h["met"] else T("bad")), h["confidence"]]
                                for h in reversed(g["history"])])

    def _staff_selected(self):
        role = self.staff_table.selected_key()
        pool = [m for m in self.lg.staff_pool if role is None or m.role == role]
        rows, keys = [], []
        for m in sorted(pool, key=lambda x: -x.overall):
            rows.append([m.name, m.title, m.age, cell(f"{m.overall:.1f}", m.overall, bold=True),
                         m.r("teaching"), m.r("tactics"), m.r("motivation")])
            keys.append(id(m))
        self.avail_table.set_rows(rows, keys)

    def _hire(self):
        key = self.pool.selected_key()
        pick = next((c for c in self.lg.coach_pool if id(c) == key), None)
        if pick is None:
            return
        team = self.user
        if not confirm(self, "Hire coach", f"Fire {team.coach.name} and hire {pick.name}?"):
            return
        old = team.coach
        self.lg.coach_pool.remove(pick)
        old.team_seasons = 0
        self.lg.coach_pool.append(old)
        pick.team_seasons = 0
        team.coach = pick
        self.lg.add_news("Coaching", f"{team.full_name} hire {pick.name} as head coach, replacing "
                                     f"{old.name}.", team.abbr)
        self.main.refresh_all()

    def _hire_staff(self):
        import staff as staff_mod
        key = self.avail_table.selected_key()
        m = next((x for x in self.lg.staff_pool if id(x) == key), None)
        if m is None:
            return
        old = self.user.staff[m.role]
        if not confirm(self, "Hire coach", f"Replace {old.name} with {m.name} as {m.title.lower()}?"):
            return
        staff_mod.hire_staff(self.lg, self.user, m)
        self.main.refresh_all()

    def _scout(self):
        key = self.scout_table.selected_key()
        return next((s for s in self.user.scouts if id(s) == key), None)

    def _assign_region(self):
        s = self._scout()
        if s is None:
            return
        s.region = self.region.currentData()
        self.refresh()

    def _fire_scout(self):
        s = self._scout()
        if s is None or len(self.user.scouts) <= 1:
            return
        if confirm(self, "Release scout", f"Release {s.name}?"):
            self.user.scouts.remove(s)
            self.lg.scout_pool.append(s)
            self.refresh()

    def _hire_scout(self):
        import staff as staff_mod
        key = self.scout_pool.selected_key()
        s = next((x for x in self.lg.scout_pool if id(x) == key), None)
        if s is None:
            return
        ok, msg = staff_mod.hire_scout(self.lg, self.user, s)
        info(self, "Scouting", msg)
        self.refresh()


# ── Finances ──────────────────────────────────────────────────────────────────

class FinancesScreen(Screen):
    title = "Finances & Contracts"

    def __init__(self, main):
        super().__init__(main)
        tiles = QHBoxLayout()
        tiles.setSpacing(10)
        self.t_cap = StatTile("Salary Cap")
        self.t_pay = StatTile("Payroll")
        self.t_space = StatTile("Cap Space")
        self.t_dead = StatTile("Dead Cap")
        self.t_next = StatTile("Committed Next Year")
        for t in (self.t_cap, self.t_pay, self.t_space, self.t_dead, self.t_next):
            tiles.addWidget(t)
        self.outer.addLayout(tiles)
        chips, _ = filter_chips([("all", "All Contracts"), ("expiring", "Expiring"),
                                 ("rookie", "Rookie Deals")], self._set_filter)
        self.filter = "all"
        self.outer.addWidget(chips)
        self.table = DataTable(["Name", "Pos", "Age", "OVR", "Salary", "Yrs", "Market Value",
                                "Value / Cost", "Morale", "Status"], stretch=0)
        self.table.on_activate = self.main.open_player
        self.outer.addWidget(self.table, 1)
        row = QHBoxLayout()
        self.note = QLabel("")
        self.note.setObjectName("sub")
        self.note.setWordWrap(True)
        row.addWidget(self.note, 1)
        ext = QPushButton("Re-sign / Extend…")
        ext.setObjectName("primary")
        ext.clicked.connect(self._extend)
        row.addWidget(ext)
        tag = QPushButton("Franchise Tag…")
        tag.setToolTip("Once a year, in the re-signing window: keep an expiring player for one season "
                       "at the average of the top five salaries at his position")
        tag.clicked.connect(self._tag)
        row.addWidget(tag)
        rel = QPushButton("Release…")
        rel.setObjectName("danger")
        rel.clicked.connect(self._release)
        row.addWidget(rel)
        self.outer.addLayout(row)

    def _set_filter(self, f):
        self.filter = f
        self.refresh()

    def _tag(self):
        p = self._selected()
        if p is None:
            return
        ok, why = rr.can_tag(self.lg, self.user, p)
        if not ok:
            info(self, "Franchise tag", why)
            return
        amt = rr.tag_amount(self.lg, p)
        if not confirm(self, "Franchise tag", f"Tag {p.name} for one season at {money(amt)}? "
                                              f"Players who want long-term security may be unhappy."):
            return
        ok, msg = rr.apply_tag(self.lg, self.user, p)
        info(self, "Franchise tag", msg)
        self.main.refresh_all()

    def refresh(self):
        lg, team = self.lg, self.user
        cap = lg.salary_cap
        self.t_cap.set(money(cap))
        self.t_pay.set(money(team.payroll), f"{team.payroll / cap * 100:.0f}% of cap")
        space = team.cap_space(cap)
        self.t_space.set(money(space), color=T("good") if space >= 0 else T("bad"))
        self.t_dead.set(money(team.dead_cap), "Released players this season")
        nxt = sum(p.salary for p in team.roster if p.contract and p.contract["years"] >= 2)
        self.t_next.set(money(nxt), f"{money(cap - nxt)} projected space")
        rows, keys = [], []
        for p in sorted(team.roster, key=lambda p: -p.salary):
            expiring = p.id in lg.expiring or (p.contract and p.contract["years"] <= 0)
            if self.filter == "expiring" and not expiring:
                continue
            if self.filter == "rookie" and not p.on_rookie_deal:
                continue
            mv = market_value(p, cap)
            ratio = mv / max(1, p.salary)
            status = "HOLDOUT" if p.holdout else "EXPIRING" if expiring else ("Rookie" if p.on_rookie_deal else "")
            rows.append([p.name, cell(p.position, POSITIONS.index(p.position)), p.age, ovr_cell(p.ovr),
                         cell(money(p.salary), p.salary), p.contract_years,
                         cell(money(mv), mv),
                         cell(f"{ratio:.2f}x", ratio, color=T("good") if ratio >= 1.2 else
                              T("bad") if ratio < 0.8 else None),
                         cell(p.morale, p.morale, color=morale_color(p.morale)),
                         cell(status, color=T("bad") if p.holdout else T("warn") if expiring else None)])
            keys.append(p.id)
        self.table.set_rows(rows, keys)
        n_exp = sum(1 for p in team.roster if p.id in lg.expiring)
        if lg.phase in ("season_end", "resign"):
            self.note.setText(f"{n_exp} expiring contracts. Re-sign players before continuing past "
                              f"the re-signing window, or they will test free agency.")
        else:
            self.note.setText("Players with one year left can be extended. Value / Cost compares "
                              "market value to salary — above 1.0x is a bargain.")
        self.set_subtitle(f"{team.full_name} · {len(team.roster)} contracts")

    def _selected(self):
        pid = self.table.selected_key()
        return self.lg.find_player(pid) if pid is not None else None

    def _extend(self):
        p = self._selected()
        if p is None:
            return
        if p.contract and p.contract["years"] > 1 and p.id not in self.lg.expiring and not p.holdout:
            info(self, "Not yet", f"{p.name} still has {p.contract['years']} years left. "
                                  f"Extensions open in the final year of a deal.")
            return
        from ui_dialogs import OfferDialog
        dlg = OfferDialog(self.main, p, resign=True)
        if dlg.exec():
            self.main.refresh_all()

    def _release(self):
        p = self._selected()
        if p is None:
            return
        if confirm(self, "Release player", f"Release {p.name}? Part of his salary becomes dead cap."):
            fa.release(self.lg, self.user, p)
            self.main.refresh_all()


# ── Cap planner ───────────────────────────────────────────────────────────────

PLAN_YEARS = 5


class CapPlannerScreen(Screen):
    title = "Cap Planner"
    subtitle = "Committed money, dead money and expiring deals for the next five seasons."

    def __init__(self, main):
        super().__init__(main)
        self.what_if = {}
        top = Card("Cap by Season")
        self.summary = DataTable([""] + [""] * PLAN_YEARS, stretch=None, sortable=False)
        top.add(self.summary)
        self.outer.addWidget(top)

        self.table = DataTable(["Name", "Pos", "Age", "OVR"] + [""] * PLAN_YEARS + ["Cut now"], stretch=0)
        self.table.on_activate = self.main.open_player
        self.outer.addWidget(self.table, 1)

        wi = Card("What if I extend him?")
        row = QHBoxLayout()
        row.setSpacing(8)
        self.who = QComboBox()
        self.who.setMinimumWidth(260)
        self.who.currentIndexChanged.connect(lambda _i: self._ask())
        row.addWidget(self.who)
        row.addWidget(QLabel("Years"))
        self.years = QSpinBox()
        self.years.setRange(1, 5)
        row.addWidget(self.years)
        row.addWidget(QLabel("Per year"))
        self.apy = QDoubleSpinBox()
        self.apy.setDecimals(2)
        self.apy.setRange(0.5, 120.0)
        self.apy.setSingleStep(0.25)
        self.apy.setSuffix(" M")
        row.addWidget(self.apy)
        prev = QPushButton("Preview")
        prev.setObjectName("primary")
        prev.clicked.connect(self._preview)
        row.addWidget(prev)
        clr = QPushButton("Clear Previews")
        clr.setObjectName("ghost")
        clr.clicked.connect(self._clear)
        row.addWidget(clr)
        neg = QPushButton("Negotiate…")
        neg.clicked.connect(self._negotiate)
        row.addWidget(neg)
        row.addStretch(1)
        wi.body.addLayout(row)
        self.wi_note = QLabel("")
        self.wi_note.setObjectName("muted")
        self.wi_note.setWordWrap(True)
        wi.add(self.wi_note)
        self.outer.addWidget(wi)

    def refresh(self):
        lg, team = self.lg, self.user
        self.what_if = {pid: v for pid, v in self.what_if.items()
                        if (p := lg.find_player(pid)) is not None and p.team == team.abbr}
        pl = capplan.plan(lg, team, PLAN_YEARS, self.what_if)
        seasons = [str(y) for y in pl["seasons"]]
        self.summary.columns = [""] + seasons
        self.summary.setHorizontalHeaderLabels(self.summary.columns)
        muted = T("muted")
        rows = [
            [cell("Projected cap", color=muted)] + [money(v) for v in pl["caps"]],
            [cell("Committed", color=muted)] + [money(v) for v in pl["committed"]],
            [cell("Dead money", color=muted)] + [money(v) if v else "—" for v in pl["dead"]],
            [cell("Cap space", bold=True)] + [cell(money(v), v, color=T("good") if v >= 0 else T("bad"), bold=True)
                                              for v in pl["space"]],
            [cell("Players under contract", color=muted)] + list(pl["counts"]),
            [cell("Deals ending after season", color=muted)] + [
                cell(str(len(e)), len(e), tip=", ".join(f"{p.position} {p.name}" for p in e[:12]))
                for e in pl["expiring"]],
        ]
        self.summary.set_rows(rows)
        self.summary.fit_height()

        cols = ["Name", "Pos", "Age", "OVR"] + seasons + ["Cut now"]
        self.table.columns = cols
        self.table.setHorizontalHeaderLabels(cols)
        prows, keys = [], []
        for r in pl["players"]:
            p = r["player"]
            line = [cell(p.name + ("  (preview)" if r["preview"] else ""),
                         color=accent() if r["preview"] else None),
                    cell(p.position, POSITIONS.index(p.position)), p.age, ovr_cell(p.ovr)]
            for k, h in enumerate(r["hits"]):
                final = h and k == r["last"]
                line.append(cell(money(h) if h else "", h,
                                 color=T("warn") if final else None,
                                 tip="Final year of his deal" if final else None))
            line.append(cell(f"saves {money(r['cut_saves'])}" if r["cut_saves"] > 0 else
                             f"costs {money(-r['cut_saves'])}", r["cut_saves"],
                             tip=f"Releasing him now leaves {money(r['cut_dead'])} of dead money"))
            prows.append(line)
            keys.append(p.id)
        self.table.set_rows(prows, keys)
        self._fill_who()
        self.set_subtitle(f"{team.full_name} · cap grows {settings['cap_growth'] * 100:.0f}% a season · "
                          f"amber = final year of a deal · double-click a player for his profile")

    def _fill_who(self):
        lg, team = self.lg, self.user
        cur = self.who.currentData()
        self.who.blockSignals(True)
        self.who.clear()
        cands = sorted((p for p in team.roster if p.contract and
                        (p.contract["years"] <= 2 or p.id in lg.expiring)),
                       key=lambda p: -p.ovr)
        for p in cands:
            self.who.addItem(f"{p.position} {p.name} ({p.ovr} OVR, {p.contract['years']} yr left)", p.id)
        idx = self.who.findData(cur) if cur is not None else -1
        self.who.setCurrentIndex(idx if idx >= 0 else (0 if cands else -1))
        self.who.blockSignals(False)
        if cur is None or idx < 0:
            self._ask()

    def _player(self):
        pid = self.who.currentData()
        return self.lg.find_player(pid) if pid is not None else None

    def _ask(self):
        p = self._player()
        if p is None:
            self.wi_note.setText("No one is close to the end of his deal.")
            return
        apy, years = capplan.extension_estimate(self.lg, self.user, p)
        self.years.setValue(years)
        self.apy.setValue(round(apy / 1e6, 2))
        dead = capplan.extension_dead_money(p)
        self.wi_note.setText(f"His agent's opening ask: {money(apy)} a year for {years} years. Market value "
                             f"{money(market_value(p, self.lg.salary_cap))}."
                             + (f" Extending now leaves {money(dead)} of his old bonus as dead money this "
                                f"year." if dead else ""))

    def _preview(self):
        p = self._player()
        if p is None:
            return
        self.what_if[p.id] = (int(self.apy.value() * 1e6), self.years.value())
        self.refresh()

    def _clear(self):
        self.what_if = {}
        self.refresh()

    def _negotiate(self):
        p = self._player()
        if p is None:
            return
        from ui_dialogs import OfferDialog
        if OfferDialog(self.main, p, resign=True).exec():
            self.what_if.pop(p.id, None)
            self.main.refresh_all()


# ── Game plan ─────────────────────────────────────────────────────────────────

class GamePlanScreen(Screen):
    title = "Game Plan"
    subtitle = "Scout this week's opponent, set your defensive plan, and see which calls are working."

    def __init__(self, main):
        super().__init__(main)
        import defense as dlib
        body = QHBoxLayout()
        body.setSpacing(12)
        left = QVBoxLayout()
        self.scout_card = Card("Scouting Report")
        self.scout_text = QLabel()
        self.scout_text.setTextFormat(Qt.TextFormat.RichText)
        self.scout_text.setWordWrap(True)
        self.scout_card.add(self.scout_text)
        left.addWidget(self.scout_card)
        self.plan_card = Card("Defensive Game Plan")
        self.plan_controls = {}
        grid = QGridLayout()
        for i, (key, (label, choices)) in enumerate(dlib.GAMEPLAN_OPTIONS.items()):
            lbl = QLabel(label)
            lbl.setWordWrap(True)
            grid.addWidget(lbl, i, 0)
            box = QComboBox()
            for c in choices:
                box.addItem("Coordinator decides" if c == "auto" else c.capitalize(), c)
            box.currentIndexChanged.connect(lambda _i, k=key: self._plan_changed(k))
            grid.addWidget(box, i, 1)
            self.plan_controls[key] = box
        self.plan_card.body.addLayout(grid)
        self.dc_text = QLabel()
        self.dc_text.setTextFormat(Qt.TextFormat.RichText)
        self.dc_text.setWordWrap(True)
        self.plan_card.add(self.dc_text)
        left.addWidget(self.plan_card)
        left.addStretch(1)
        body.addLayout(left, 2)

        right = QVBoxLayout()
        self.rep_card = Card("How Your Calls Are Working (this season)")
        self.rep_kind = QComboBox()
        self.rep_kind.addItems(["Defense: coverages, pressure and fronts", "Offense: plays and runs"])
        self.rep_kind.currentIndexChanged.connect(lambda _i: self._report())
        self.rep_card.add(self.rep_kind)
        self.rep_table = DataTable(["Call", "Plays", "EPA / play", "Success", "Total EPA"], stretch=0)
        self.rep_card.add(self.rep_table)
        note = QLabel("EPA per play: positive is good for the offense. On defense, look for calls with "
                      "negative EPA and low success rates — and calls the opponent keeps beating.")
        note.setObjectName("muted")
        note.setWordWrap(True)
        self.rep_card.add(note)
        right.addWidget(self.rep_card, 1)
        body.addLayout(right, 3)
        self.outer.addLayout(body, 1)
        self._loading = False

    def _next_opponent(self):
        lg, team = self.lg, self.user
        if lg.phase != "regular":
            return None, None
        for w in range(lg.week, len(lg.schedule)):
            for h, a in lg.schedule[w]:
                if team.abbr in (h, a):
                    return w + 1, lg.teams[a if h == team.abbr else h]
        return None, None

    def refresh(self):
        import defense as dlib
        import random as _r
        import staff as staff_mod
        lg, team = self.lg, self.user
        self._loading = True
        mine = getattr(team, "def_gameplan", None) or {}
        for key, box in self.plan_controls.items():
            box.setCurrentIndex(max(0, box.findData(mine.get(key, "auto"))))
        self._loading = False
        wk, opp = self._next_opponent()
        if opp is None:
            self.scout_text.setText("No regular-season opponent this week. Your plan settings carry over "
                                    "to every game, including the playoffs.")
            self.dc_text.setText("")
        else:
            oplan = opp.gameplan()
            qb = (opp.lineup("QB", 1) or [None])[0]
            rb = (opp.lineup("RB", 1) or [None])[0]
            targets = sorted(opp.lineup("WR", 3) + opp.lineup("TE", 1), key=lambda p: -p.ovr)[:3]
            games = lg.team_results(opp.abbr)
            tot = Counter()
            for g in games:
                tot.update(g.team_stats[opp.abbr])
            n = max(1, len(games))
            plays = tot["pass_att"] + tot["sacked"] + tot["rush_att"]
            lines = [f"<b>Week {wk}: {opp.full_name}</b> — {opp.coach.off_scheme} offense, "
                     f"{opp.coach.def_scheme} defense"]
            if games:
                lines.append(f"{tot['points'] / n:.1f} points a game · "
                             f"{tot['total_yds'] / max(1, plays):.1f} yards per play · "
                             f"EPA/play {tot['epa'] / max(1, tot['epa_plays']):+.2f} · "
                             f"passes on {100 * (tot['pass_att'] + tot['sacked']) / max(1, plays):.0f}% of snaps")
            else:
                lines.append(f"Expected to pass on about {oplan['pass_rate'] * 100:.0f}% of snaps")
            deep = "takes a lot of deep shots" if oplan["deep"] > 0.3 else \
                "lives on the quick game" if oplan["deep"] < -0.3 else "balanced passing depth"
            lines.append(f"Style: {deep}; runs {'outside' if oplan['outside'] > 0.55 else 'inside'}; "
                         f"tempo {'fast' if oplan['tempo'] > 0.6 else 'normal' if oplan['tempo'] > 0.35 else 'slow'}.")
            if qb:
                lines.append(f"QB {qb.name} — OVR {qb.ovr}, speed {qb.attrs.get('speed', 0)}")
            if rb:
                lines.append(f"RB {rb.name} — OVR {rb.ovr}")
            if targets:
                lines.append("Targets: " + ", ".join(f"{p.name} ({p.position} {p.ovr})" for p in targets))
            # Their play-calling by situation, against the league average
            if games:
                lg_tot = Counter()
                for wk_res in lg.all_results(include_playoffs=False):
                    for ab in (wk_res.home, wk_res.away):
                        for k, v in wk_res.team_stats[ab].items():
                            if isinstance(k, str) and k.startswith("sit|"):
                                lg_tot[k] += v
                parts = []
                for b in ("1st & 2nd down", "3rd/4th & short", "3rd/4th & medium", "3rd/4th & long", "Red zone"):
                    n_ = tot[f"sit|{b}|n"]
                    if n_ >= 8:
                        mine_p = 100.0 * tot[f"sit|{b}|p"] / n_
                        lg_p = 100.0 * lg_tot[f"sit|{b}|p"] / max(1, lg_tot[f"sit|{b}|n"])
                        diff_ = mine_p - lg_p
                        tag = "" if abs(diff_) < 5 else (" (pass-heavy)" if diff_ > 0 else " (run-heavy)")
                        parts.append(f"{b}: pass {mine_p:.0f}% vs league {lg_p:.0f}%{tag}")
                if parts:
                    lines.append("<b>Tendencies:</b> " + " · ".join(parts))
            self.scout_text.setText("<br>".join(lines))
            dc = dlib.scout(team, opp, oplan, calling=staff_mod.def_calling(team),
                            rng=_r.Random(hash((lg.year, wk, team.abbr))))
            saved = getattr(team, "def_gameplan", None)
            team.def_gameplan = None
            auto = dlib.scout(team, opp, oplan, calling=staff_mod.def_calling(team),
                              rng=_r.Random(hash((lg.year, wk, team.abbr))))
            team.def_gameplan = saved
            notes = auto["notes"] or ["No special adjustments — play our normal defense."]
            self.dc_text.setText("<b>Your coordinator's read:</b><br>• " + "<br>• ".join(notes) +
                                 f"<br><span style='color:{T('muted')}'>Plan in effect: "
                                 f"{'shadow corner, ' if dc['shadow'] else ''}"
                                 f"{'QB spy, ' if dc['spy'] else ''}"
                                 f"bracket {dc['bracket'] * 100:.0f}% of the time, "
                                 f"box {dc['box']:+.1f}, pressure {dc['blitz']:+.2f}, "
                                 f"two-high {dc['two_high']:+.2f}</span>")
        self._report()

    def _plan_changed(self, key):
        if self._loading:
            return
        team = self.user
        plan = dict(getattr(team, "def_gameplan", None) or {})
        val = self.plan_controls[key].currentData()
        if val == "auto":
            plan.pop(key, None)
        else:
            plan[key] = val
        team.def_gameplan = plan or None
        self.refresh()

    def _report(self):
        lg, team = self.lg, self.user
        prefix = "dc|" if self.rep_kind.currentIndex() == 0 else "oc|"
        tot = Counter()
        for g in lg.team_results(team.abbr):
            for k, v in g.team_stats[team.abbr].items():
                if isinstance(k, str) and k.startswith(prefix):
                    tot[k] += v
        calls = sorted({k.split("|")[1] for k in tot})
        rows = []
        for c in calls:
            n = tot[f"{prefix}{c}|n"]
            if not n:
                continue
            e = tot[f"{prefix}{c}|epa"]
            s = tot[f"{prefix}{c}|s"]
            good = (e / n) if prefix == "oc|" else -(e / n)
            rows.append([c, n, cell(f"{e / n:+.2f}", e / n, color=T("good") if good > 0.05 else
                                    T("bad") if good < -0.05 else None, bold=True),
                         cell(f"{100 * s / n:.0f}%", s / n), cell(f"{e:+.1f}", e)])
        rows.sort(key=lambda r: -r[1])
        self.rep_table.set_rows(rows)
