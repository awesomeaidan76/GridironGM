"""
ui_main.py — the main window: top bar, sidebar navigation, screens,
background simulation and autosave.
"""
import os
import traceback

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QKeySequence, QPalette, QShortcut
from PyQt6.QtWidgets import (QApplication, QDialog, QFrame, QHBoxLayout, QInputDialog, QLabel,
                             QMainWindow, QMenu, QMessageBox, QPushButton, QScrollArea,
                             QStackedWidget, QToolButton, QVBoxLayout, QWidget)

import free_agency as fa
import save_manager
import season as season_mod
from settings import settings
from ui_dialogs import LoadDialog, PlayerDialog, SettingsDialog, TeamDialog
from ui_live import LiveGameDialog, has_live_data
from ui_screens_club import (DepthChartScreen, FinancesScreen, HomeScreen, RosterScreen,
                             StaffScreen, TacticsScreen, GamePlanScreen)
from ui_screens_league import (GameCenterScreen, HistoryScreen, NewsScreen, PlayersScreen,
                               PlayoffsScreen, ScheduleScreen, StandingsScreen, StatsScreen,
                               TeamsScreen, GlossaryScreen)
from ui_screens_moves import DraftScreen, FreeAgencyScreen, TradeScreen, TradingBlockScreen
from ui_theme import T, accent, stylesheet, palette
from ui_widgets import TeamBadge, confirm, info

NAV = [
    ("MY CLUB", [("home", "Home"), ("roster", "Roster"), ("depth", "Depth Chart"),
                 ("tactics", "Tactics"), ("gameplan", "Game Plan"), ("staff", "Staff"),
                 ("finances", "Finances")]),
    ("LEAGUE", [("schedule", "Schedule"), ("game", "Game Center"), ("standings", "Standings"),
                ("stats", "Stats"), ("players", "Players"), ("teams", "Teams"),
                ("playoffs", "Playoffs"), ("history", "History"), ("news", "News"),
                ("glossary", "Glossary")]),
    ("TRANSACTIONS", [("draft", "Draft"), ("fa", "Free Agency"), ("trades", "Trades"),
                      ("block", "Trading Block")]),
]

SCREENS = {
    "home": HomeScreen, "roster": RosterScreen, "depth": DepthChartScreen,
    "tactics": TacticsScreen, "gameplan": GamePlanScreen, "staff": StaffScreen, "finances": FinancesScreen,
    "schedule": ScheduleScreen, "game": GameCenterScreen, "standings": StandingsScreen,
    "stats": StatsScreen, "players": PlayersScreen, "teams": TeamsScreen,
    "playoffs": PlayoffsScreen, "history": HistoryScreen, "news": NewsScreen,
    "draft": DraftScreen, "fa": FreeAgencyScreen, "trades": TradeScreen, "block": TradingBlockScreen,
    "glossary": GlossaryScreen,
}

WINDOWS = []          # keep references so windows aren't garbage collected
ERROR_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gridiron_errors.log")


def apply_palette(app):
    p = palette()
    pal = QPalette()
    for role, key in ((QPalette.ColorRole.Window, "bg0"), (QPalette.ColorRole.WindowText, "text"),
                      (QPalette.ColorRole.Base, "card"), (QPalette.ColorRole.AlternateBase, "card_alt"),
                      (QPalette.ColorRole.Text, "text"), (QPalette.ColorRole.Button, "bg2"),
                      (QPalette.ColorRole.ButtonText, "text"), (QPalette.ColorRole.ToolTipBase, "card"),
                      (QPalette.ColorRole.ToolTipText, "text"), (QPalette.ColorRole.PlaceholderText, "muted")):
        pal.setColor(role, QColor(p[key]))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(accent()))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(pal)
    app.setStyleSheet(stylesheet())


def log_error(text):
    try:
        with open(ERROR_LOG, "a", encoding="utf-8") as f:
            f.write(text + "\n" + "-" * 70 + "\n")
    except OSError:
        pass


class SimWorker(QThread):
    progress = pyqtSignal(str)
    done = pyqtSignal(str)

    def __init__(self, fn):
        super().__init__()
        self.fn = fn
        self.error = None

    def run(self):
        msg = ""
        try:
            msg = self.fn(self.progress.emit) or ""
        except Exception:
            self.error = traceback.format_exc()
        self.done.emit(msg)


class MainWindow(QMainWindow):
    # Keep Python references to every open main window (a top-level widget
    # whose wrapper is garbage-collected would vanish).
    _open = []

    def __init__(self, lg):
        super().__init__()
        MainWindow._open.append(self)
        self.lg = lg
        settings.use_league(lg)          # this league's own sim settings
        self.busy = False
        self.worker = None
        self.current = "home"
        self.setWindowTitle(f"Gridiron GM — {lg.user_team.full_name}")
        self.resize(1440, 900)
        self.setMinimumSize(1180, 720)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._topbar())
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._sidebar())
        self.stack = QStackedWidget()
        self.screens = {}
        for key, cls in SCREENS.items():
            scr = cls(self)
            self.screens[key] = scr
            self.stack.addWidget(scr)
        body.addWidget(self.stack, 1)
        root.addLayout(body, 1)
        self.status_label = QLabel("")
        self.statusBar().addWidget(self.status_label, 1)

        self._sc_continue = QShortcut(QKeySequence("Ctrl+Space"), self)
        self._sc_continue.activated.connect(self.continue_clicked)
        self._sc_save = QShortcut(QKeySequence("Ctrl+S"), self)
        self._sc_save.activated.connect(self.quick_save)
        self.goto("home")
        self.refresh_topbar()
        WINDOWS.append(self)

    # ── Chrome ───────────────────────────────────────────────────────────────

    def _topbar(self):
        bar = QFrame()
        bar.setObjectName("topbar")
        bar.setFixedHeight(60)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 8, 16, 8)
        lay.setSpacing(10)
        logo = QLabel("GRIDIRON GM")
        logo.setStyleSheet(f"color: {accent()}; font-weight: 900; font-size: {settings['font_size'] + 3}px;")
        lay.addWidget(logo)
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(f"color: {T('border')};")
        lay.addWidget(sep)
        self.badge = TeamBadge(self.lg.user_team, 36)
        lay.addWidget(self.badge)
        col = QVBoxLayout()
        col.setSpacing(0)
        self.team_label = QLabel()
        self.team_label.setObjectName("h3")
        col.addWidget(self.team_label)
        self.phase_label = QLabel()
        self.phase_label.setObjectName("muted")
        col.addWidget(self.phase_label)
        lay.addLayout(col)
        lay.addStretch(1)
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.quick_save)
        lay.addWidget(self.save_btn)
        file_btn = QToolButton()
        file_btn.setText("Game ▾")
        file_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        fm = QMenu(file_btn)
        fm.addAction("Save As…").triggered.connect(self.save_as)
        fm.addAction("Load Game…").triggered.connect(self.load_game)
        fm.addAction("Export League to JSON…").triggered.connect(self.export_json)
        fm.addSeparator()
        fm.addAction("Settings…").triggered.connect(self.open_settings)
        fm.addAction("Toggle Light / Dark").triggered.connect(self.toggle_theme)
        fm.addSeparator()
        fm.addAction("Quit").triggered.connect(self.close)
        file_btn.setMenu(fm)
        lay.addWidget(file_btn)
        self.sim_btn = QToolButton()
        self.sim_btn.setText("Sim ▾")
        self.sim_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        sm = QMenu(self.sim_btn)
        sm.addAction("Sim to end of regular season").triggered.connect(lambda: self.sim("regular"))
        sm.addAction("Sim through the playoffs").triggered.connect(lambda: self.sim("playoffs"))
        sm.addAction("Sim 4 weeks").triggered.connect(lambda: self.sim("weeks4"))
        sm.addAction("Sim to the trade deadline").triggered.connect(lambda: self.sim("deadline"))
        sm.addSeparator()
        sm.addAction("Sim to next season (auto offseason)").triggered.connect(lambda: self.sim("season"))
        sm.addAction("Sim 5 full seasons (auto)").triggered.connect(lambda: self.sim("season5"))
        sm.addSeparator()
        self.watch_act = sm.addAction("Watch my games live")
        self.watch_act.setCheckable(True)
        self.watch_act.setChecked(bool(settings["watch_games"]))
        self.watch_act.toggled.connect(self._set_watch)
        self.sim_btn.setMenu(sm)
        lay.addWidget(self.sim_btn)
        self.cont_btn = QPushButton("Continue ▸")
        self.cont_btn.setObjectName("primary")
        self.cont_btn.setToolTip("Advance the league (Ctrl+Space)")
        self.cont_btn.setMinimumWidth(200)
        self.cont_btn.clicked.connect(self.continue_clicked)
        lay.addWidget(self.cont_btn)
        return bar

    def _sidebar(self):
        side = QFrame()
        side.setObjectName("sidebar")
        side.setFixedWidth(208)
        lay = QVBoxLayout(side)
        lay.setContentsMargins(10, 14, 10, 14)
        lay.setSpacing(2)
        self.nav_buttons = {}
        for group, items in NAV:
            cap = QLabel(group)
            cap.setObjectName("caps")
            cap.setContentsMargins(8, 10, 0, 4)
            lay.addWidget(cap)
            for key, label in items:
                b = QPushButton(label)
                b.setObjectName("nav")
                b.setCheckable(True)
                b.clicked.connect(lambda _c=False, k=key: self.goto(k))
                lay.addWidget(b)
                self.nav_buttons[key] = b
        lay.addStretch(1)
        hint = QLabel("Ctrl+Space: Continue\nCtrl+S: Save")
        hint.setObjectName("muted")
        lay.addWidget(hint)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(side)
        scroll.setFixedWidth(210)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        return scroll

    def refresh_topbar(self):
        lg = self.lg
        t = lg.user_team
        rec = lg.standings.get(t.abbr)
        self.team_label.setText(f"{t.full_name}  {rec.wlt() if rec else ''}")
        self.phase_label.setText(f"{lg.year} · {season_mod.PHASE_TITLES.get(lg.phase, '')} · "
                                 f"{lg.week_label} · Cap space "
                                 f"{t.cap_space(lg.salary_cap) / 1e6:.1f}M")
        self.cont_btn.setText(season_mod.continue_label(lg) + "  ▸")
        self.cont_btn.setEnabled(not self.busy)
        self.sim_btn.setEnabled(not self.busy)
        self.save_btn.setEnabled(not self.busy)

    # ── Navigation ───────────────────────────────────────────────────────────

    def goto(self, key):
        if self.busy:
            for k, b in self.nav_buttons.items():
                b.setChecked(k == self.current)
            return
        self.current = key
        for k, b in self.nav_buttons.items():
            b.setChecked(k == key)
        scr = self.screens[key]
        self.stack.setCurrentWidget(scr)
        self._safe_refresh(scr)

    def _safe_refresh(self, scr):
        try:
            scr.refresh()
        except Exception:
            err = traceback.format_exc()
            log_error(err)
            self.status(f"Display error on this screen (details saved to {os.path.basename(ERROR_LOG)})")

    def refresh_all(self):
        self.refresh_topbar()
        self._safe_refresh(self.screens[self.current])

    def status(self, msg):
        self.status_label.setText(msg)

    def open_player(self, pid):
        p = self.lg.find_player(pid)
        if p is None:
            return
        PlayerDialog(self, p).exec()
        self.refresh_all()

    def open_team(self, abbr):
        t = self.lg.teams.get(abbr)
        if t is None:
            return
        if abbr == self.lg.user_abbr:
            self.goto("roster")
            return
        TeamDialog(self, t).exec()
        self.refresh_all()

    def open_game(self, g):
        self.screens["game"].show_game(g)
        self.goto("game")

    def trade_with(self, abbr):
        self.goto("trades")
        self.screens["trades"].set_partner(abbr)

    def trade_for(self, player):
        self.goto("trades")
        self.screens["trades"].preload(player)

    # ── Settings / theme ─────────────────────────────────────────────────────

    def apply_theme(self):
        app = QApplication.instance()
        if app is not None:
            apply_palette(app)
        self.badge.set_team(self.lg.user_team)
        self.refresh_all()

    def toggle_theme(self):
        settings.set("theme", "light" if settings["theme"] == "dark" else "dark")
        settings.save()
        self.apply_theme()

    def open_settings(self):
        if self.busy:
            return
        SettingsDialog(self).exec()

    # ── Saving ───────────────────────────────────────────────────────────────

    def _default_name(self):
        lg = self.lg
        return f"{lg.user_abbr} {lg.year} {lg.week_label}"

    def quick_save(self):
        if self.busy:
            return
        name = getattr(self.lg, "save_name", None) or f"{self.lg.user_abbr} career"
        try:
            path = save_manager.save(self.lg, name)
            self.lg.save_name = name
            self.status(f"Saved to {os.path.basename(path)}")
        except Exception as e:
            log_error(traceback.format_exc())
            info(self, "Save failed", str(e))

    def save_as(self):
        if self.busy:
            return
        name, ok = QInputDialog.getText(self, "Save As", "Save name:", text=self._default_name())
        if ok and name.strip():
            self.lg.save_name = name.strip()
            self.quick_save()

    def export_json(self):
        if self.busy:
            return
        try:
            path = save_manager.export_json(self.lg, self._default_name())
            info(self, "Exported", f"League exported to:\n{path}")
        except Exception as e:
            log_error(traceback.format_exc())
            info(self, "Export failed", str(e))

    def load_game(self):
        if self.busy:
            return
        dlg = LoadDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.path:
            try:
                lg = save_manager.load(dlg.path)
            except Exception as e:
                log_error(traceback.format_exc())
                info(self, "Load failed", f"Could not load that save:\n{e}")
                return
            self._replace_with(lg)

    def _replace_with(self, lg):
        win = MainWindow(lg)
        win.show()
        self._skip_close_prompt = True
        self.close()
        if self in MainWindow._open:
            MainWindow._open.remove(self)
        return win

    def _handle_firing(self):
        g = getattr(self.lg, "gm", None)
        if not g or not g.get("fired"):
            return
        from ui_dialogs import JobOffersDialog
        dlg = JobOffersDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.choice:
            self.setWindowTitle(f"Gridiron GM — {self.lg.user_team.full_name}")
            self.badge.set_team(self.lg.user_team)
            for scr in self.screens.values():
                if hasattr(scr, "_partners_loaded"):
                    scr._partners_loaded = False
                    scr.partner.clear()
            self.goto("home")
            return
        # Walked away: back to the start menu
        from main import choose_league
        self._skip_close_prompt = True
        lg = choose_league()
        if lg is not None:
            self._replace_with(lg)
        else:
            self.close()

    def closeEvent(self, event):
        if getattr(self, "_skip_close_prompt", False) or not settings["confirm_actions"]:
            event.accept()
            return
        btn = QMessageBox.question(self, "Quit", "Save your career before quitting?",
                                   QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard
                                   | QMessageBox.StandardButton.Cancel)
        if btn == QMessageBox.StandardButton.Cancel:
            event.ignore()
            return
        if btn == QMessageBox.StandardButton.Save:
            self.quick_save()
        event.accept()

    # ── Simulation ───────────────────────────────────────────────────────────

    def _precheck(self):
        """Warn about decisions that will be made automatically."""
        lg, team = self.lg, self.lg.user_team
        if lg.phase == "resign":
            n = [p for p in team.roster if p.id in lg.expiring]
            if n and not confirm(self, "Expiring contracts",
                                 f"{len(n)} of your players have expiring contracts and will become "
                                 f"free agents ({', '.join(p.name for p in n[:6])}"
                                 f"{'…' if len(n) > 6 else ''}). Continue?"):
                return False
        if lg.phase == "draft":
            left = [o for o in lg.draft_order[lg.draft_index:] if o[2] == lg.user_abbr]
            if left and not confirm(self, "Finish draft", f"You still have {len(left)} picks. "
                                                         f"They will be made automatically "
                                                         f"(best available). Continue?"):
                return False
        if lg.phase == "preseason":
            over = fa.active_count(team) - settings["roster_size"]
            if over > 0 and not confirm(self, "Roster cuts",
                                        f"You are {over} players over the limit. The lowest-value "
                                        f"players will be released automatically. Continue?"):
                return False
        return True

    def _user_games(self):
        lg = self.lg
        return [g for g in lg.all_results(include_playoffs=True) if lg.user_abbr in (g.home, g.away)]

    def continue_clicked(self):
        if self.busy or not self._precheck():
            return
        lg = self.lg
        self._watch_from = len(self._user_games()) if settings["watch_games"] else None

        def work(emit):
            emit(f"Simulating: {season_mod.continue_label(lg)}…")
            return season_mod.advance(lg)
        self._run(work)

    def sim(self, target):
        if self.busy:
            return
        lg = self.lg
        if target in ("season", "season5"):
            n = 5 if target == "season5" else 1
            if not confirm(self, "Auto offseason", f"Simulate {'5 seasons' if n == 5 else 'to the next season'}? "
                                                   "Re-signings, draft picks and roster cuts will be "
                                                   "handled automatically for your team."):
                return

        def step():
            """One week; returns a stop message if something needs the user."""
            snap = season_mod.sim_snapshot(lg)
            season_mod.advance(lg)
            return season_mod.sim_stop_reason(lg, snap)

        def work(emit):
            if target == "regular":
                while lg.phase == "regular":
                    emit(f"Simulating week {lg.week + 1}…")
                    why = step()
                    if why and lg.phase == "regular":
                        return why
                return "Regular season complete."
            if target == "deadline":
                deadline = settings["trade_deadline_week"]
                while lg.phase == "regular" and lg.week + 1 < deadline:
                    emit(f"Simulating week {lg.week + 1}…")
                    why = step()
                    if why:
                        return why
                return f"Trade deadline week: {lg.week_label}."
            if target == "weeks4":
                for _ in range(4):
                    if lg.phase != "regular":
                        break
                    emit(f"Simulating week {lg.week + 1}…")
                    why = step()
                    if why:
                        return why
                return f"Simulated to {lg.week_label}."
            if target == "playoffs":
                while lg.phase in ("regular", "playoffs"):
                    emit(f"Simulating {lg.week_label}…")
                    why = step()
                    if why and lg.phase in ("regular", "playoffs"):
                        return why
                return f"{lg.year} season complete. Champion: {lg.teams[lg.champion].full_name}."
            seasons = 5 if target == "season5" else 1
            for i in range(seasons):
                start = lg.year
                guard = 0
                while guard < 80:
                    guard += 1
                    if lg.phase == "resign":
                        self._auto_resign()
                    emit(f"Season {i + 1}/{seasons}: {lg.year} {lg.week_label}…")
                    season_mod.advance(lg)
                    if getattr(lg, "gm", {}).get("fired"):
                        return "You have been fired."
                    if lg.phase == "regular" and lg.week == 0 and lg.year > start:
                        break
            return f"Now in the {lg.year} season."
        self._run(work)

    def _auto_resign(self):
        """When auto-simming, keep the most valuable expiring players if affordable."""
        lg, team = self.lg, self.lg.user_team
        exp = [p for p in team.roster if p.id in lg.expiring]
        exp.sort(key=lambda p: -fa.player_value(p))
        for p in exp:
            from contracts import asking_salary, contract_length
            ask = asking_salary(p, lg.salary_cap, 1.0)
            if fa.player_value(p) >= 115 and p.age <= 31 and \
                    ask <= team.cap_space(lg.salary_cap) + p.salary:
                fa.resign(lg, team, p, ask, contract_length(p))

    def _set_watch(self, on):
        settings.set("watch_games", bool(on))
        settings.save()

    def watch_game(self, res):
        if self.busy:
            return
        if not has_live_data(res):
            info(self, "Watch game", "This game was played before live data was recorded, so it "
                                     "can only be viewed in the box score.")
            return
        LiveGameDialog(self, res).exec()

    def _run(self, fn):
        self.busy = True
        self.stack.setEnabled(False)
        self.refresh_topbar()
        self.worker = SimWorker(fn)
        self.worker.progress.connect(self.status)
        self.worker.done.connect(self._done)
        self.worker.start()

    def _done(self, msg):
        worker = self.worker
        self.busy = False
        self.stack.setEnabled(True)
        if worker is not None and worker.error:
            log_error(worker.error)
            info(self, "Simulation error", "Something went wrong during the simulation. Details "
                                           f"were saved to {ERROR_LOG}.\n\n{worker.error[-600:]}")
        watch_from = getattr(self, "_watch_from", None)
        self._watch_from = None
        if watch_from is not None and (worker is None or not worker.error):
            mine = self._user_games()
            if len(mine) == watch_from + 1 and has_live_data(mine[-1]):
                try:
                    LiveGameDialog(self, mine[-1]).exec()
                except Exception:
                    log_error(traceback.format_exc())
        summary = self._user_result_line()
        self.status(" · ".join(x for x in (msg, summary) if x))
        if settings["autosave"]:
            try:
                save_manager.autosave(self.lg, keep=settings["autosave_slots"])
            except Exception:
                log_error(traceback.format_exc())
        self.refresh_all()
        self._handle_firing()

    def _user_result_line(self):
        lg = self.lg
        games = lg.team_results(lg.user_abbr)
        if not games:
            return ""
        g = games[-1]
        me = lg.user_abbr
        ms, ts = g.score_of(me), g.score_of(g.opponent(me))
        r = "W" if ms > ts else "L" if ms < ts else "T"
        return f"Last game: {r} {ms}-{ts} vs {g.opponent(me)}"
