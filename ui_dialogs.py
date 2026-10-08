"""
ui_dialogs.py — player profile, team view, contract offers, settings,
new game and load game dialogs.
"""
from collections import Counter

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFormLayout,
                             QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QScrollArea, QSlider, QSpinBox, QTabWidget, QVBoxLayout, QWidget)

import free_agency as fa
import save_manager
from contracts import market_value, asking_salary, contract_length
from player import ARCHETYPES
from ratings import (ATTRIBUTES, ATTRIBUTE_GROUPS, POSITION_DISPLAY_GROUPS, POSITIONS,
                     HIDDEN_TRAITS, POSITION_NAMES, stars_text, ca_tier, unit_ovr)
from settings import settings, SPEC, GROUPS as SETTING_GROUPS
from coach import COACH_RATINGS, COACH_RATING_LABELS
from stats import merge, summary_line
from ui_theme import T, accent, attr_color, ca_color, morale_color, ovr_color
from ui_widgets import (AttrBar, Card, Chip, DataTable, LineChart, StatTile, TeamBadge,
                        ovr_cell, cell, clear_layout, confirm, divider, h_label, info, money,
                        pot_text, personality, team_cell, trait_word, ALIGN_CENTER)
import ui_stats


def _hero_style(team):
    c1 = team.colors[0] if team else T("bg2")
    return (f"QFrame#hero {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            f"stop:0 {c1}, stop:0.65 {T('bg2')}, stop:1 {T('bg2')}); "
            f"border: 1px solid {T('border')}; border-radius: 12px; }}")


class BaseDialog(QDialog):
    def __init__(self, main, title, w=980, h=720):
        super().__init__(main if isinstance(main, QWidget) else None)
        self.main = main
        self.setWindowTitle(title)
        self.resize(w, h)
        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(18, 18, 18, 14)
        self.root.setSpacing(12)


# ── Player profile ────────────────────────────────────────────────────────────

class PlayerDialog(BaseDialog):
    def __init__(self, main, player):
        super().__init__(main, f"{player.name} — Player Profile", 1040, 760)
        self.p = player
        self.lg = main.lg
        self.build()

    @property
    def user(self):
        return self.lg.user_team

    def build(self):
        clear_layout(self.root)
        p = self.p
        lg = self.lg
        team = lg.teams.get(p.team) if p.team else None
        user = self.user
        scouting = user.scouting if user else 10

        # Hero
        hero = QFrame()
        hero.setObjectName("hero")
        hero.setStyleSheet(_hero_style(team))
        hl = QHBoxLayout(hero)
        hl.setContentsMargins(18, 14, 18, 14)
        hl.setSpacing(14)
        if team:
            hl.addWidget(TeamBadge(team, 52))
        left = QVBoxLayout()
        left.setSpacing(2)
        name = QLabel(p.name)
        name.setObjectName("h1")
        left.addWidget(name)
        arch = f" · {p.archetype}" if p.archetype and settings["show_archetype"] else ""
        left.addWidget(QLabel(f"#{p.jersey}  {POSITION_NAMES[p.position]}{arch}  ·  Age {p.age}"
                              f"  ·  {p.height_str}, {p.weight} lb"))
        where = team.full_name if team else ("Retired" if p.retired else "Free Agent")
        if p.draft:
            dr = f"Drafted {p.draft['year']} R{p.draft['round']} #{p.draft['pick']} ({p.draft['team']})"
        else:
            dr = "Undrafted"
        sub = QLabel(f"{where}  ·  {dr}  ·  {p.college}  ·  {p.hometown}")
        sub.setObjectName("sub")
        left.addWidget(sub)
        chips = QHBoxLayout()
        chips.setSpacing(6)
        chips.addWidget(Chip(personality(p)))
        chips.addWidget(Chip(p.development_stage()))
        if p.injury:
            chips.addWidget(Chip(f"Injured: {p.injury['name']} ({max(0, p.injury['weeks'])} wk)",
                                 T("bad")))
        if p.hall_of_fame:
            chips.addWidget(Chip("Hall of Fame", T("gold")))
        for yr, aw in p.awards[-3:]:
            if aw != "Champion":
                chips.addWidget(Chip(f"{yr} {aw}", T("gold")))
        chips.addStretch(1)
        left.addLayout(chips)
        hl.addLayout(left, 1)

        right = QVBoxLayout()
        right.setSpacing(0)
        cap = QLabel(f"OVERALL · {p.position}")
        cap.setObjectName("caps")
        cap.setAlignment(Qt.AlignmentFlag.AlignRight)
        right.addWidget(cap)
        show = settings["show_ca_number"]
        shown = p.scouted_ovr(scouting) if not p.team or p.team != lg.user_abbr else p.ovr
        ca = QLabel(str(shown) if show else p.tier)
        ca.setObjectName("bigvalue")
        ca.setAlignment(Qt.AlignmentFlag.AlignRight)
        ca.setStyleSheet(f"color: {ovr_color(shown)};")
        right.addWidget(ca)
        st = QLabel(f"{p.tier}")
        st.setAlignment(Qt.AlignmentFlag.AlignRight)
        st.setStyleSheet(f"color: {T('gold')};")
        right.addWidget(st)
        role, rv = p.best_role
        rl = QLabel(f"Best role: <b>{role}</b> {rv}")
        rl.setObjectName("sub")
        rl.setAlignment(Qt.AlignmentFlag.AlignRight)
        right.addWidget(rl)
        if settings["show_pa_number"]:
            pa = QLabel(f"Potential (scouted): {pot_text(p, scouting)}")
            pa.setObjectName("sub")
            pa.setAlignment(Qt.AlignmentFlag.AlignRight)
            right.addWidget(pa)
        hl.addLayout(right)
        self.root.addWidget(hero)

        # Tiles
        tiles = QHBoxLayout()
        tiles.setSpacing(10)
        t1 = StatTile("Morale", p.morale, "Happiness at the club")
        t1.set(p.morale, color=morale_color(p.morale))
        tiles.addWidget(t1)
        tiles.addWidget(StatTile("Reputation", p.reputation, "League-wide fame"))
        if p.contract:
            tiles.addWidget(StatTile("Contract", money(p.salary),
                                     f"{p.contract_years} yr left"
                                     + (" · rookie deal" if p.on_rookie_deal else "")))
        else:
            tiles.addWidget(StatTile("Asking", money(asking_salary(p, lg.salary_cap)),
                                     "Free agent" if not p.retired else "Retired"))
        tiles.addWidget(StatTile("Market Value", money(market_value(p, lg.salary_cap)),
                                 "Estimated per season"))
        best = sorted(((p.ovr_at(pos), pos) for pos in POSITIONS if pos not in ("K", "P")
                       or pos == p.position), reverse=True)[:3]
        tiles.addWidget(StatTile("Best Positions", f"{best[0][1]} {best[0][0]}",
                                 ", ".join(f"{pos} {v}" for v, pos in best[1:])))
        self.root.addLayout(tiles)

        tabs = QTabWidget()
        tabs.addTab(self._attributes_tab(), "Attributes")
        tabs.addTab(self._stats_tab(), "Career Stats")
        tabs.addTab(self._log_tab(), "Game Log")
        tabs.addTab(self._history_tab(), "Development & History")
        self.root.addWidget(tabs, 1)

        # Actions
        row = QHBoxLayout()
        row.addStretch(1)
        if p.team == lg.user_abbr and not p.retired:
            if p.contract and (p.contract_years <= 1 or p.id in lg.expiring or p.holdout):
                b = QPushButton("Extend Contract…")
                b.clicked.connect(self._extend)
                row.addWidget(b)
            b = QPushButton("Release")
            b.setObjectName("danger")
            b.clicked.connect(self._release)
            row.addWidget(b)
        elif p.team is None and not p.retired and p in lg.free_agents:
            b = QPushButton("Offer Contract…")
            b.setObjectName("primary")
            b.clicked.connect(self._offer)
            row.addWidget(b)
        elif p.team and p.team != lg.user_abbr and lg.user_abbr:
            b = QPushButton("Trade For…")
            b.clicked.connect(self._trade)
            row.addWidget(b)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        row.addWidget(close)
        self.root.addLayout(row)

    def _attributes_tab(self):
        p = self.p
        w = QWidget()
        outer = QVBoxLayout(w)
        outer.setContentsMargins(0, 8, 0, 0)
        show_all = QCheckBox("Show every attribute")
        outer.addWidget(show_all)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        grid = QGridLayout(inner)
        grid.setSpacing(10)
        grid.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(inner)
        outer.addWidget(scroll, 1)

        def fill(all_groups):
            clear_layout(grid)
            groups = list(POSITION_DISPLAY_GROUPS[p.position])
            if all_groups:
                groups += [g for g in ATTRIBUTE_GROUPS if g not in groups]
            cols = 3
            for i, g in enumerate(groups):
                card = Card(g)
                for key, (label, abbr, group) in ATTRIBUTES.items():
                    if group == g:
                        from glossary import ATTRIBUTE_DESC
                        card.add(AttrBar(label, p.attrs[key],
                                         tip=f"{label} ({abbr}) {p.attrs[key]} — {ATTRIBUTE_DESC.get(key, '')}"))
                card.body.addStretch(1)
                grid.addWidget(card, i // cols, i % cols)
            # Role ratings
            card = Card("Role Ratings")
            for role, rv in p.roles:
                desc = ""
                from player import ARCHETYPES
                spec = ARCHETYPES.get(p.position, {}).get(role)
                if spec:
                    desc = spec[2]
                card.add(AttrBar(role + ("  ◆" if role == p.archetype else ""), rv, tip=desc))
            card.body.addStretch(1)
            n0 = len(groups)
            grid.addWidget(card, n0 // cols, n0 % cols)
            groups = groups + ["_roles"]
            # Personality
            card = Card("Personality")
            for trait, desc in HIDDEN_TRAITS.items():
                v = p.hidden.get(trait, 50)
                label = trait.replace("_", " ").title()
                if settings["show_hidden_stats"]:
                    card.add(AttrBar(label, v, tip=desc))
                else:
                    lbl = QLabel(f"{label}: <b>{trait_word(v)}</b>")
                    lbl.setToolTip(desc)
                    card.add(lbl)
            card.body.addStretch(1)
            n = len(groups)
            grid.addWidget(card, n // cols, n % cols)

        show_all.toggled.connect(fill)
        fill(False)
        return w

    def _stats_tab(self):
        p = self.p
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 8, 0, 0)
        groups = ui_stats.groups_for(p)
        seasons = sorted(p.career.items())
        current = None
        if self.lg.phase in ("regular", "playoffs") and p.season_stats["gp"]:
            current = (self.lg.year, {"team": p.team or "FA", "stats": p.season_stats})
        rows_src = seasons + ([current] if current else [])
        if not groups:
            groups = []
        cols = ["Year", "Team", "GP", "GS"]
        for g in groups:
            cols += [f"{g[:4]} {c}" if c in ("Att", "Yds", "TD", "Lng", "Avg") else c
                     for c in ui_stats.columns(g)]
        table = DataTable(cols, stretch=None)
        rows = []
        total = Counter()
        for yr, s in rows_src:
            st = s["stats"]
            total = merge(total, st)
            row = [cell(yr, yr), s["team"], st["gp"], st["gs"]]
            for g in groups:
                row += ui_stats.values(g, st)
            rows.append(row)
        if rows:
            row = [cell("Career", 99999, bold=True), "", total["gp"], total["gs"]]
            for g in groups:
                row += ui_stats.values(g, total)
            rows.append(row)
        table.set_rows(rows)
        lay.addWidget(table, 1)
        po = Counter()
        for _, s in seasons:
            merge(po, s.get("playoffs", Counter()))
        if self.lg.phase == "playoffs":
            merge(po, p.playoff_stats)
        if po["gp"]:
            lbl = QLabel(f"Playoff career: {po['gp']} games — {summary_line(po, p.position)}")
            lbl.setObjectName("sub")
            lay.addWidget(lbl)
        if not rows:
            lbl = QLabel("No regular-season games played yet.")
            lbl.setObjectName("muted")
            lay.addWidget(lbl)
        return w

    def _log_tab(self):
        p = self.p
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 8, 0, 0)
        table = DataTable(["Week", "Opp", "Result", "Line"], stretch=3, sortable=False)
        rows = []
        for wk, opp, home, result, line in p.game_log:
            col = T("good") if result.startswith("W") else T("bad") if result.startswith("L") else T("warn")
            rows.append([wk, ("vs " if home else "@ ") + opp, cell(result, color=col, bold=True),
                         summary_line(line, p.position)])
        table.set_rows(rows)
        lay.addWidget(table)
        return w

    def _history_tab(self):
        p = self.p
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 8, 0, 0)
        left = Card("Ability over time")
        chart = LineChart(height=240)
        from ratings import ovr_from_ca
        pts = sorted((y, ovr_from_ca(v, p.position)) for y, v in p.ca_history.items())
        if not pts or pts[-1][0] != self.lg.year:
            pts.append((self.lg.year, p.ovr))
        chart.set_series([("OVR", accent(), [(float(x), float(y)) for x, y in pts])])
        left.add(chart)
        msg = f"Last offseason change: {p.last_change:+d}" if p.last_change else "No change recorded yet."
        lbl = QLabel(msg)
        lbl.setObjectName("muted")
        left.add(lbl)
        # Training focus (your players only)
        if p.team == self.lg.user_abbr:
            row = QHBoxLayout()
            row.addWidget(QLabel("Training focus:"))
            focus = QComboBox()
            groups = ["Balanced"] + list(POSITION_DISPLAY_GROUPS[p.position])
            for g in ("Physical", "Mental"):
                if g not in groups:
                    groups.append(g)
            for g in groups:
                focus.addItem(g, None if g == "Balanced" else g)
            cur = getattr(p, "training_focus", None)
            idx = focus.findData(cur) if cur else 0
            focus.setCurrentIndex(max(0, idx))
            focus.setToolTip("Growth goes mostly into this group of attributes; in decline it fades slower.")

            def set_focus(_i, cb=focus, player=p):
                player.training_focus = cb.currentData()
            focus.currentIndexChanged.connect(set_focus)
            row.addWidget(focus, 1)
            left.body.addLayout(row)
        lay.addWidget(left, 3)
        mid = Card("Staff Development Report")
        reps = getattr(p, "dev_reports", None) or []
        ms = getattr(p, "midseason_change", None)
        if ms and ms[0] == self.lg.year and ms[1]:
            mid.add(QLabel(f"<b>{self.lg.year} mid-season:</b> "
                           f"{'stepped forward' if ms[1] > 0 else 'regressed'} ({ms[1]:+d} ability)"))
        if not reps:
            mid.add(QLabel("No offseason report yet."))
        for r in reversed(reps[-3:]):
            head = QLabel(f"<b>{r['year']} offseason: {r['ovr_change']:+d} OVR</b>"
                          + (f"  ·  {r['note']}" if r.get("note") else ""))
            head.setTextFormat(Qt.TextFormat.RichText)
            mid.add(head)
            q = QLabel(f"<i>“{r['text']}”</i> — {r['coach']}")
            q.setTextFormat(Qt.TextFormat.RichText)
            q.setWordWrap(True)
            mid.add(q)
            for label, v in r["factors"]:
                word = ("big boost" if v >= 2.5 else "helped" if v >= 0.8 else "slight lift" if v > 0
                        else "big drag" if v <= -2.5 else "held him back" if v <= -0.8 else "slight drag")
                fl = QLabel(f"{'▲' if v > 0 else '▼'} {label}: {word} (about {v:+.0f})")
                fl.setStyleSheet(f"color: {T('good') if v > 0 else T('bad')};")
                mid.add(fl)
            acc = r.get("accuracy", 10)
            note = QLabel("Your staff's read is " + ("sharp." if acc >= 15 else "reasonable." if acc >= 10
                                                       else "rough — take it with a grain of salt."))
            note.setObjectName("muted")
            mid.add(note)
        mid.body.addStretch(1)
        lay.addWidget(mid, 3)
        right = QVBoxLayout()
        aw = Card("Awards & Honours")
        if p.awards:
            for yr, a in sorted(p.awards, reverse=True)[:14]:
                aw.add(QLabel(f"{yr}  ·  {a}"))
        if getattr(p, "potw", 0):
            aw.add(QLabel(f"Player of the Week  ×{p.potw}"))
        if not p.awards and not getattr(p, "potw", 0):
            aw.add(QLabel("None yet."))
        aw.body.addStretch(1)
        right.addWidget(aw)
        inj = Card("Injury History")
        if p.injury_history:
            for yr, nm, wk in p.injury_history[-10:][::-1]:
                inj.add(QLabel(f"{yr}  ·  {nm}  ({wk} wk)"))
        else:
            inj.add(QLabel("Clean bill of health."))
        inj.body.addStretch(1)
        right.addWidget(inj)
        lay.addLayout(right, 2)
        return w

    # Actions
    def _release(self):
        p = self.p
        if not confirm(self, "Release player", f"Release {p.name}? Part of his salary will "
                                               f"count as dead cap this season."):
            return
        fa.release(self.lg, self.user, p)
        self.main.refresh_all()
        self.accept()

    def _offer(self):
        dlg = OfferDialog(self.main, self.p)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.main.refresh_all()
            self.accept()

    def _extend(self):
        dlg = OfferDialog(self.main, self.p, resign=True)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.main.refresh_all()
            self.build()

    def _trade(self):
        self.accept()
        self.main.trade_for(self.p)


# ── Contract offers ───────────────────────────────────────────────────────────

class OfferDialog(BaseDialog):
    """Contract talks: salary, years, signing bonus and guarantees, in rounds with the agent."""

    def __init__(self, main, player, resign=False):
        super().__init__(main, ("Extend " if resign else "Negotiate with ") + player.name, 640, 600)
        import negotiation as nego
        self.p = player
        self.lg = main.lg
        self.resign = resign
        self.counter = None
        team = self.lg.user_team
        cap = self.lg.salary_cap
        self.mood = 1.0 if resign else fa.mood(self.lg)
        dem = nego.demands(self.lg, team, player, resign, self.mood)
        ag = dem["agent"]
        self.root.addWidget(h_label(player.name, "h2"))
        info_lbl = QLabel(f"{player.position} · Age {player.age} · OVR {player.ovr} · "
                          f"{personality(player)}" + ("  ·  HOLDING OUT" if player.holdout else ""))
        info_lbl.setObjectName("sub")
        self.root.addWidget(info_lbl)
        top = sorted(dem["prio"].items(), key=lambda kv: -kv[1])
        names = {"money": "getting paid", "security": "guaranteed money and years", "winning": "a contender",
                 "role": "a starting role", "loyalty": "staying with his team"}
        ag_lbl = QLabel(f"Agent: <b>{ag['name']}</b> — {ag['style']} ({ag['desc'].lower()}).<br>"
                        f"{player.name.split()[-1]} cares most about {names[top[0][0]]}, "
                        f"then {names[top[1][0]]}.")
        ag_lbl.setTextFormat(Qt.TextFormat.RichText)
        ag_lbl.setWordWrap(True)
        self.root.addWidget(ag_lbl)
        grid = QFormLayout()
        grid.addRow("He's asking for:", QLabel(
            f"<b>{money(dem['apy'])}</b> per year · {dem['years']} yr · "
            f"~{dem['guar'] * 100:.0f}% guaranteed"))
        grid.addRow("Market value:", QLabel(money(market_value(player, cap))))
        space = team.cap_space(cap) + (player.salary if resign else 0)
        grid.addRow("Your cap space:", QLabel(money(space)))
        self.salary = QDoubleSpinBox()
        self.salary.setDecimals(2)
        self.salary.setRange(round(fa.min_salary(cap) / 1e6, 2), 120.0)
        self.salary.setSingleStep(0.25)
        self.salary.setSuffix(" M / yr")
        self.salary.setValue(round(dem["apy"] * 0.9 / 1e6, 2))
        grid.addRow("Average per year (cap hit):", self.salary)
        self.years = QSpinBox()
        self.years.setRange(1, 5)
        self.years.setValue(dem["years"])
        grid.addRow("Years:", self.years)
        self.bonus = QDoubleSpinBox()
        self.bonus.setDecimals(2)
        self.bonus.setRange(0.0, 600.0)
        self.bonus.setSingleStep(0.5)
        self.bonus.setSuffix(" M total")
        grid.addRow("Signing bonus:", self.bonus)
        self.guar = QDoubleSpinBox()
        self.guar.setDecimals(2)
        self.guar.setRange(0.0, 600.0)
        self.guar.setSingleStep(0.5)
        self.guar.setSuffix(" M total")
        grid.addRow("Guaranteed (incl. bonus):", self.guar)
        tot = dem["apy"] * 0.9 * dem["years"]
        self.guar.setValue(round(tot * dem["guar"] * 0.8 / 1e6, 2))
        self.bonus.setValue(round(tot * dem["bonus"] * 0.8 / 1e6, 2))
        self.root.addLayout(grid)
        self.summary = QLabel("")
        self.summary.setObjectName("muted")
        self.summary.setWordWrap(True)
        self.root.addWidget(self.summary)
        self.hint = QLabel("Make an offer. Each lowball costs patience; the agent will counter.")
        self.hint.setWordWrap(True)
        self.root.addWidget(self.hint)
        for w in (self.salary, self.years, self.bonus, self.guar):
            w.valueChanged.connect(self._update)
        self.root.addStretch(1)
        row = QHBoxLayout()
        self.use_counter = QPushButton("Use Their Counter")
        self.use_counter.setEnabled(False)
        self.use_counter.clicked.connect(self._apply_counter)
        row.addWidget(self.use_counter)
        row.addStretch(1)
        cancel = QPushButton("Close")
        cancel.clicked.connect(self.reject)
        row.addWidget(cancel)
        ok = QPushButton("Make Offer")
        ok.setObjectName("primary")
        ok.clicked.connect(self._submit)
        row.addWidget(ok)
        self.root.addLayout(row)
        self._update()

    def _values(self):
        sal = int(self.salary.value() * 1e6)
        yrs = self.years.value()
        bonus = int(self.bonus.value() * 1e6)
        guar = max(bonus, int(self.guar.value() * 1e6))
        return sal, yrs, bonus, guar

    def _update(self, *_):
        sal, yrs, bonus, guar = self._values()
        total = sal * yrs
        dead = bonus + max(0, guar - bonus)
        self.summary.setText(f"Total value {money(total)} · {guar / max(1, total) * 100:.0f}% guaranteed · "
                             f"cap hit {money(sal)} a year · releasing him next year would leave about "
                             f"{money(int(bonus / yrs * (yrs - 1) + max(0, guar - bonus - (sal - bonus / yrs))))} "
                             f"of dead money.")

    def _apply_counter(self):
        c = self.counter
        if not c:
            return
        self.salary.setValue(round(c["apy"] / 1e6, 2))
        self.years.setValue(c["years"])
        self.bonus.setValue(round(c["bonus"] / 1e6, 2))
        self.guar.setValue(round(c["guaranteed"] / 1e6, 2))

    def _submit(self):
        import negotiation as nego
        sal, yrs, bonus, guar = self._values()
        team = self.lg.user_team
        cap = self.lg.salary_cap
        space = team.cap_space(cap) + (self.p.salary if self.resign else 0)
        if settings["hard_cap"] and sal > space:
            self.hint.setText(f"✖ Not enough cap space ({money(space)} available).")
            self.hint.setStyleSheet(f"color: {T('warn')};")
            return
        if not self.resign and fa.active_count(team) >= fa.roster_limit(self.lg):
            self.hint.setText(f"✖ Your roster is full ({fa.roster_limit(self.lg)} max). Release someone first.")
            self.hint.setStyleSheet(f"color: {T('warn')};")
            return
        result, msg, counter = nego.respond(self.lg, team, self.p, sal, yrs, bonus, guar, self.resign, self.mood)
        self.counter = counter
        self.use_counter.setEnabled(counter is not None)
        if result == "accept":
            if self.resign:
                fa.resign(self.lg, team, self.p, sal, yrs, bonus, guar)
            else:
                fa.sign(self.lg, team, self.p, sal, yrs, bonus=bonus, guaranteed=guar)
            info(self, "Deal done", msg)
            self.accept()
            return
        self.hint.setText(("✖ " if result == "walk" else "↔ ") + msg)
        self.hint.setStyleSheet(f"color: {T('bad') if result == 'walk' else T('warn')};")


# ── Team view ─────────────────────────────────────────────────────────────────

class TeamDialog(BaseDialog):
    def __init__(self, main, team):
        super().__init__(main, team.full_name, 1040, 740)
        self.team = team
        self.lg = main.lg
        lg = self.lg
        hero = QFrame()
        hero.setObjectName("hero")
        hero.setStyleSheet(_hero_style(team))
        hl = QHBoxLayout(hero)
        hl.setContentsMargins(18, 14, 18, 14)
        hl.addWidget(TeamBadge(team, 56))
        col = QVBoxLayout()
        col.addWidget(h_label(team.full_name, "h1"))
        rec = lg.standings.get(team.abbr)
        sub = QLabel(f"{team.conference} {team.division}  ·  {rec.wlt() if rec else ''}  ·  "
                     f"Coach {team.coach.name} ({team.coach.off_scheme} / {team.coach.def_scheme})")
        sub.setObjectName("sub")
        col.addWidget(sub)
        hl.addLayout(col, 1)
        u = team.unit_ratings()
        for k in ("OFF", "DEF", "OVR"):
            from ratings import unit_ovr
            v = unit_ovr(u[k], k)
            t = StatTile({"OFF": "Offense", "DEF": "Defense", "OVR": "Overall"}[k], v)
            t.set(v, color=ovr_color(v))
            hl.addWidget(t)
        self.root.addWidget(hero)

        tabs = QTabWidget()
        # Roster
        roster = DataTable(["Name", "Pos", "Age", "OVR", "POT", "Arch", "Salary", "Yrs", "Status"], stretch=0)
        rows, keys = [], []
        for p in sorted(team.roster, key=lambda x: (POSITIONS.index(x.position), -x.ca)):
            rows.append([p.name, cell(p.position, POSITIONS.index(p.position)), p.age,
                         ovr_cell(p.scouted_ovr(lg.user_team.scouting if lg.user_team else 10)
                                  if team.abbr != lg.user_abbr else p.ovr),
                         ovr_cell(p.pot if team.abbr == lg.user_abbr else
                                  p.scouted_pot_range(lg.user_team.scouting if lg.user_team else 10)[1]),
                         p.archetype or "", cell(money(p.salary), p.salary),
                         p.contract_years, p.injury["name"] if p.injury else ""])
            keys.append(p.id)
        roster.set_rows(rows, keys)
        roster.on_activate = lambda pid: main.open_player(pid)
        tabs.addTab(roster, "Roster")
        # Units
        units = QWidget()
        ul = QVBoxLayout(units)
        for k, label in (("QB", "Quarterback"), ("RB", "Running Back"), ("WR", "Receivers"),
                         ("TE", "Tight End"), ("OL", "Offensive Line"), ("DL", "Defensive Line"),
                         ("LB", "Linebackers"), ("DB", "Secondary"), ("ST", "Special Teams")):
            ul.addWidget(AttrBar(label, int(u[k]), maximum=200))
        ul.addStretch(1)
        tabs.addTab(units, "Unit Ratings")
        # Coach
        cw = QWidget()
        cl = QVBoxLayout(cw)
        c = team.coach
        cl.addWidget(h_label(f"{c.name}  ·  Age {c.age}", "h3"))
        meta = QLabel(f"Record {c.record_str} ({c.win_pct:.3f}) · {c.seasons} seasons · "
                      f"{c.titles} titles · Reputation {c.reputation}"
                      + (f" · Coaching tree: {c.mentor} ({c.tree_origin})" if c.mentor else ""))
        meta.setObjectName("sub")
        meta.setWordWrap(True)
        cl.addWidget(meta)
        for r in COACH_RATINGS:
            cl.addWidget(AttrBar(COACH_RATING_LABELS[r], c.ratings[r] * 5))
        cl.addStretch(1)
        tabs.addTab(cw, "Head Coach")
        # History
        hist = DataTable(["Year", "Record", "PF", "PA", "Result", "Coach"], stretch=5)
        hist.set_rows([[h["year"], f"{h['w']}-{h['l']}" + (f"-{h['t']}" if h['t'] else ""),
                        h["pf"], h["pa"], h["result"], h["coach"]] for h in reversed(team.history)])
        tabs.addTab(hist, "History")
        self.root.addWidget(tabs, 1)
        row = QHBoxLayout()
        honours = QLabel(f"Titles {team.titles} · Conference titles {team.conf_titles} · "
                         f"Division titles {team.division_titles} · Playoff apps {team.playoff_apps}")
        honours.setObjectName("sub")
        row.addWidget(honours)
        row.addStretch(1)
        if lg.user_abbr and team.abbr != lg.user_abbr:
            tb = QPushButton("Propose Trade…")
            tb.clicked.connect(lambda: (self.accept(), main.trade_with(team.abbr)))
            row.addWidget(tb)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        row.addWidget(close)
        self.root.addLayout(row)


# ── Settings ──────────────────────────────────────────────────────────────────

class SettingsDialog(BaseDialog):
    def __init__(self, main):
        super().__init__(main, "Settings", 760, 640)
        self.controls = {}
        self.root.addWidget(h_label("Settings", "h1"))
        note = QLabel("Match Engine, League, Development and AI settings belong to this league and are "
                      "saved with it (your other leagues keep their own). They apply from the next game "
                      "or offseason. New leagues start from the values you last saved. The realistic "
                      "baseline is 1.0 everywhere; use Reset to go back to it.")
        note.setObjectName("sub")
        note.setWordWrap(True)
        self.root.addWidget(note)
        tabs = QTabWidget()
        for group in SETTING_GROUPS:
            page = QWidget()
            form = QFormLayout(page)
            form.setContentsMargins(8, 12, 8, 8)
            form.setSpacing(10)
            for key, (default, g, label, kind, extra) in SPEC.items():
                if g != group:
                    continue
                form.addRow(label + ":", self._control(key, kind, extra))
            reset = QPushButton(f"Reset {group} to defaults")
            reset.setObjectName("ghost")
            reset.clicked.connect(lambda _c=False, grp=group: self._reset(grp))
            form.addRow("", reset)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(page)
            tabs.addTab(scroll, group)
        self.root.addWidget(tabs, 1)
        row = QHBoxLayout()
        row.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        row.addWidget(cancel)
        ok = QPushButton("Save Settings")
        ok.setObjectName("primary")
        ok.clicked.connect(self._save)
        row.addWidget(ok)
        self.root.addLayout(row)

    def _control(self, key, kind, extra):
        val = settings[key]
        if kind == "bool":
            w = QCheckBox()
            w.setChecked(bool(val))
            self.controls[key] = ("bool", w)
            return w
        if kind == "choice":
            w = QComboBox()
            for opt in extra:
                w.addItem(opt.title() if opt.islower() else opt, opt)
            w.setCurrentIndex(max(0, list(extra).index(val) if val in extra else 0))
            self.controls[key] = ("choice", w)
            return w
        lo, hi, step = extra
        if kind == "int" and (hi - lo) / step > 400:
            w = QSpinBox()
            w.setRange(int(lo), int(hi))
            w.setSingleStep(int(step))
            w.setValue(int(val))
            w.setGroupSeparatorShown(True)
            self.controls[key] = ("spin", w)
            return w
        # Slider with live value label
        box = QWidget()
        lay = QHBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        steps = int(round((hi - lo) / step))
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, steps)
        slider.setValue(int(round((val - lo) / step)))
        lab = QLabel()
        lab.setMinimumWidth(52)

        def show(pos, lo=lo, step=step, kind=kind, lab=lab):
            v = lo + pos * step
            lab.setText(f"{int(round(v))}" if kind == "int" else f"{v:.2f}")
        slider.valueChanged.connect(show)
        show(slider.value())
        lay.addWidget(slider, 1)
        lay.addWidget(lab)
        self.controls[key] = ("slider", slider, lo, step, kind)
        return box

    def _reset(self, group):
        settings.reset(group)
        self.main.apply_theme()
        self.accept()
        self.main.open_settings()

    def _save(self):
        for key, spec in self.controls.items():
            kind = spec[0]
            w = spec[1]
            if kind == "bool":
                settings.set(key, w.isChecked())
            elif kind == "choice":
                settings.set(key, w.currentData())
            elif kind == "spin":
                settings.set(key, w.value())
            else:
                _, slider, lo, step, k = spec
                v = lo + slider.value() * step
                settings.set(key, int(round(v)) if k == "int" else round(v, 4))
        settings.save()
        self.main.apply_theme()
        self.accept()


# ── New game ──────────────────────────────────────────────────────────────────

class NewGameDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gridiron GM — New Career")
        self.resize(1100, 720)
        self.league = None
        self.selected = None
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 16)
        root.setSpacing(12)
        title = QLabel("GRIDIRON GM")
        title.setObjectName("h1")
        title.setStyleSheet(f"color: {accent()}; font-size: {settings['font_size'] + 16}px;")
        root.addWidget(title)
        sub = QLabel("Build a dynasty. Every snap simulated, every era earned.")
        sub.setObjectName("sub")
        root.addWidget(sub)

        form = QHBoxLayout()
        form.setSpacing(10)
        form.addWidget(QLabel("League name:"))
        self.name_edit = QLineEdit("Gridiron Football League")
        form.addWidget(self.name_edit, 2)
        regen = QPushButton("Generate New League")
        regen.clicked.connect(self.generate)
        form.addWidget(regen)
        root.addLayout(form)
        era_note = QLabel("Every league begins from a different, era-neutral landscape. From there "
                          "the style of play evolves on its own: draft classes, coaching trees, "
                          "innovators, defensive counters and the competition committee's rule "
                          "changes decide what each era looks like.")
        era_note.setObjectName("muted")
        era_note.setWordWrap(True)
        root.addWidget(era_note)

        body = QHBoxLayout()
        body.setSpacing(12)
        self.table = DataTable(["Team", "Conf", "Div", "OVR", "OFF", "DEF", "QB", "Coach Scheme",
                                "Cap Space"], stretch=0)
        self.table.itemSelectionChanged.connect(self._selected)
        self.table.on_activate = lambda abbr: self._choose(abbr)
        body.addWidget(self.table, 3)
        self.preview = Card("Select a franchise")
        self.preview.setMinimumWidth(330)
        self.preview_text = QLabel("Pick a team from the list to see its outlook.")
        self.preview_text.setWordWrap(True)
        self.preview_text.setTextFormat(Qt.TextFormat.RichText)
        self.preview.add(self.preview_text)
        self.preview.body.addStretch(1)
        body.addWidget(self.preview, 2)
        root.addLayout(body, 1)

        row = QHBoxLayout()
        row.addStretch(1)
        cancel = QPushButton("Back")
        cancel.clicked.connect(self.reject)
        row.addWidget(cancel)
        self.start_btn = QPushButton("Start Career  ▸")
        self.start_btn.setObjectName("primary")
        self.start_btn.setEnabled(False)
        self.start_btn.clicked.connect(self._start)
        row.addWidget(self.start_btn)
        root.addLayout(row)
        self.generate()

    def generate(self, *_):
        from worldgen import new_league
        self.league = new_league(self.name_edit.text().strip() or "Gridiron Football League")
        lg = self.league
        rows, keys = [], []
        for t in lg.team_list():
            u = t.unit_ratings()
            qb = t.lineup("QB", 1)[0]
            rows.append([t.full_name, t.conference, t.division, team_cell(u["OVR"], "OVR"),
                         team_cell(u["OFF"], "OFF"), team_cell(u["DEF"], "DEF"), ovr_cell(qb.ovr),
                         t.coach.off_scheme, cell(money(t.cap_space(lg.salary_cap)),
                                                  t.cap_space(lg.salary_cap))])
            keys.append(t.abbr)
        self.table.set_rows(rows, keys)
        self.selected = None
        self.start_btn.setEnabled(False)

    def _selected(self):
        abbr = self.table.selected_key()
        if abbr:
            self._show(abbr)

    def _show(self, abbr):
        lg = self.league
        t = lg.teams[abbr]
        self.selected = abbr
        self.start_btn.setEnabled(True)
        u = t.unit_ratings()
        ranks = sorted(lg.teams.values(), key=lambda x: -x.unit_ratings()["OVR"])
        rank = ranks.index(t) + 1
        if rank <= 6:
            outlook = "Title contender — the owner expects a deep playoff run."
        elif rank <= 14:
            outlook = "Playoff hopeful — a wild card is the minimum target."
        elif rank <= 24:
            outlook = "Middle of the pack — build towards contention."
        else:
            outlook = "Rebuilding — develop youth and stockpile talent."
        stars = sorted(t.roster, key=lambda p: -p.ovr)[:5]
        star_txt = "<br>".join(f"{p.position} {p.name} — {p.ovr} OVR (age {p.age})" for p in stars)
        c = t.coach
        self.preview.title_label.setText(t.full_name)
        self.preview_text.setText(
            f"<b>League rank:</b> #{rank} of 32<br><b>Outlook:</b> {outlook}<br><br>"
            f"<b>Offense</b> {unit_ovr(u['OFF'], 'OFF')} · <b>Defense</b> {unit_ovr(u['DEF'], 'DEF')} · "
            f"<b>Special teams</b> {unit_ovr(u['ST'], 'ST')}<br><br>"
            f"<b>Head coach:</b> {c.name}<br>{c.off_scheme} offense · {c.def_scheme} defense<br><br>"
            f"<b>Best players</b><br>{star_txt}<br><br>"
            f"<b>Cap space:</b> {money(t.cap_space(lg.salary_cap))}")

    def _choose(self, abbr):
        self._show(abbr)
        self._start()

    def _start(self):
        if not self.selected:
            return
        lg = self.league
        lg.name = self.name_edit.text().strip() or lg.name
        lg.user_abbr = self.selected
        from season import default_tactics
        lg.user_team.tactics = default_tactics()
        lg.add_news("League", f"You have taken charge of the {lg.user_team.full_name}. "
                              f"Good luck, Coach.", lg.user_abbr)
        self.accept()


# ── Load game ─────────────────────────────────────────────────────────────────

class LoadDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Load Game")
        self.resize(820, 520)
        self.path = None
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 14)
        root.addWidget(h_label("Load Game", "h1"))
        self.table = DataTable(["Save", "Team", "Season", "Phase", "Record", "Saved", "Type"],
                               stretch=0)
        self.table.on_activate = self._load_key
        root.addWidget(self.table, 1)
        row = QHBoxLayout()
        self.del_btn = QPushButton("Delete")
        self.del_btn.setObjectName("danger")
        self.del_btn.clicked.connect(self._delete)
        row.addWidget(self.del_btn)
        row.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        row.addWidget(cancel)
        load = QPushButton("Load")
        load.setObjectName("primary")
        load.clicked.connect(lambda: self._load_key(self.table.selected_key()))
        row.addWidget(load)
        root.addLayout(row)
        self.refresh()

    def refresh(self):
        rows, keys = [], []
        for s in save_manager.list_saves():
            m = save_manager.read_meta(s["path"])
            rows.append([s["file"].replace(".gsav", ""), m.get("team", "?"), m.get("year", ""),
                         m.get("phase", ""), m.get("record", ""),
                         cell(m.get("saved", ""), s["modified"]), "Auto" if s["auto"] else "Manual"])
            keys.append(s["path"])
        self.table.set_rows(rows, keys)

    def _load_key(self, path):
        if path:
            self.path = path
            self.accept()

    def _delete(self):
        path = self.table.selected_key()
        if path and confirm(self, "Delete save", "Delete this save file permanently?"):
            save_manager.delete(path)
            self.refresh()


class StartDialog(QDialog):
    """First screen: new career, load, or quit."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gridiron GM")
        self.resize(520, 420)
        self.choice = None
        root = QVBoxLayout(self)
        root.setContentsMargins(36, 36, 36, 30)
        root.setSpacing(14)
        title = QLabel("GRIDIRON GM")
        title.setAlignment(ALIGN_CENTER)
        title.setStyleSheet(f"color: {accent()}; font-size: {settings['font_size'] + 22}px; "
                            f"font-weight: 800;")
        root.addWidget(title)
        sub = QLabel("American football management simulation")
        sub.setAlignment(ALIGN_CENTER)
        sub.setObjectName("sub")
        root.addWidget(sub)
        root.addSpacing(18)
        for label, key, primary in (("New Career", "new", True), ("Load Game", "load", False),
                                    ("Continue Last Save", "continue", False), ("Quit", "quit", False)):
            b = QPushButton(label)
            if primary:
                b.setObjectName("primary")
            b.setMinimumHeight(40)
            if key == "continue" and not save_manager.list_saves():
                b.setEnabled(False)
            b.clicked.connect(lambda _c=False, k=key: self._pick(k))
            root.addWidget(b)
        root.addStretch(1)

    def _pick(self, key):
        self.choice = key
        self.accept()


class JobOffersDialog(QDialog):
    """You've been fired: pick a new job (or walk away)."""

    def __init__(self, main):
        super().__init__(main)
        self.main = main
        lg = main.lg
        self.setWindowTitle("You're fired")
        self.resize(640, 420)
        lay = QVBoxLayout(self)
        lay.addWidget(h_label("Your time is up", "h1"))
        txt = QLabel((getattr(lg, "gm_review", None) or ("", False))[0] or "The owner has let you go.")
        txt.setWordWrap(True)
        lay.addWidget(txt)
        lay.addWidget(QLabel("These clubs want to interview you:"))
        self.table = DataTable(["Team", "Record", "Overall", "Owner patience"], stretch=0)
        rows, keys = [], []
        from ratings import unit_ovr
        for abbr in lg.gm.get("offers", []):
            t = lg.teams[abbr]
            rec = lg.standings.get(abbr)
            ov = unit_ovr(t.unit_ratings()["OVR"], "OVR")
            rows.append([t.full_name, rec.wlt() if rec else "", ovr_cell(ov),
                         getattr(getattr(t, "owner", None), "patience", 10)])
            keys.append(abbr)
        self.table.set_rows(rows, keys)
        lay.addWidget(self.table, 1)
        row = QHBoxLayout()
        row.addStretch(1)
        quit_btn = QPushButton("Walk Away")
        quit_btn.clicked.connect(self.reject)
        row.addWidget(quit_btn)
        take = QPushButton("Take the Job")
        take.setObjectName("primary")
        take.clicked.connect(self._take)
        row.addWidget(take)
        lay.addLayout(row)
        self.choice = None

    def _take(self):
        abbr = self.table.selected_key()
        if not abbr:
            return
        import staff as staff_mod
        staff_mod.take_job(self.main.lg, abbr)
        self.choice = abbr
        self.accept()
