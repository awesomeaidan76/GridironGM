"""
Headless UI test: drives every screen, button and dialog through the strict
PyQt6 fake in tests/fakeqt (added to the path automatically; it validates every
call against the real PyQt6 signatures in registry.json). Any PyQt6 API misuse or
Python error fails the run.

    python tools/ui_test.py
"""
import os
import random
import sys
import traceback

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "tests", "fakeqt"))

from PyQt6 import _core, _impls  # noqa: E402  (fake)
from PyQt6.QtWidgets import QApplication, QPushButton  # noqa: E402

import ui_main  # noqa: E402

ERRORS = []
ui_main.log_error = lambda text: ERRORS.append(text)

import settings as settings_mod  # noqa: E402
settings_mod.SETTINGS_FILE = os.path.join(HERE, "tools", "_test_settings.json")
settings_mod.settings.set("autosave", False)
import ui_state  # noqa: E402
ui_state.STATE_FILE = os.path.join(HERE, "tools", "_test_ui_state.json")
ui_state.reset()

app = QApplication([])
ui_main.apply_palette(app)

import save_manager  # noqa: E402
import ui_dialogs  # noqa: E402
from ui_main import MainWindow  # noqa: E402

STEPS = []
LIVE = []


def step(name):
    STEPS.append(name)
    if _core.STRICT_ERRORS:
        raise AssertionError(f"Strict PyQt errors after '{name}':\n" + "\n".join(_core.STRICT_ERRORS))
    if ERRORS:
        raise AssertionError(f"UI errors after '{name}':\n" + ERRORS[0])


def buttons_in(layout_owner):
    """All QPushButtons reachable through a widget's layouts."""
    out = []

    def walk_layout(lay):
        if lay is None:
            return
        for i in range(lay.count()):
            it = lay.itemAt(i)
            w = it.widget()
            if w is not None:
                walk_widget(w)
            sub = it.layout()
            if sub is not None:
                walk_layout(sub)

    def walk_widget(w):
        if isinstance(w, QPushButton):
            out.append(w)
        walk_layout(w.layout())
        inner = getattr(w, "widget", None)
        if callable(inner) and type(w).__name__ == "QScrollArea":
            iw = w.widget()
            if iw is not None:
                walk_widget(iw)
    walk_widget(layout_owner)
    return out


# ── Dialog hooks ──────────────────────────────────────────────────────────────

DIAG_SEEN = []


def select_key(table, key):
    for r in range(table.rowCount()):
        if table.key_at(r) == key:
            table.selectRow(r)
            return True
    return False


NEGOTIATIONS = []
from ui_screens_club import DEPTH_SLOTS  # noqa: E402
DEPTH_SLOT_DT = DEPTH_SLOTS.index("DT")
DEPTH_SLOT_LB = DEPTH_SLOTS.index("LB")


def on_exec(dlg):
    name = type(dlg).__name__
    if name == "OfferDialog":
        dlg._submit()                      # opening offer (usually below the ask)
        for _ in range(4):
            if dlg.result():
                break
            if dlg.counter:
                dlg._apply_counter()
            dlg._submit()
        NEGOTIATIONS.append((dlg.p.name, dlg.result(), dlg.hint.text()))
        return dlg.result()
    if name == "PlayerDialog":
        # Toggle 'show every attribute' and visit tabs by rebuilding
        return 0
    if name == "LiveGameDialog":
        LIVE.append(dlg)
        for _ in range(5):
            dlg._tick()
        dlg.toggle()
        dlg.toggle()
        dlg._speed_changed(8)
        dlg.next_drive()
        dlg.next_quarter()
        for wdg in (dlg.field, dlg.wp, dlg.mom):
            wdg.paintEvent(None)
        diags = [d for d in getattr(dlg.res, "diagrams", []) if d]
        DIAG_SEEN.append(len(diags))
        for dg in diags[:60]:
            dlg.playview.set_play(dg, dlg.home, dlg.away, animate=True)
            for _ in range(12):
                dlg.playview._frame()
                if _ % 4 == 0:
                    dlg.playview.paintEvent(None)
            dlg.playview.t = 1.0
            dlg.playview.paintEvent(None)
        if len(LIVE) % 2:
            dlg.skip()
        else:
            dlg.open_box()
        assert dlg.game_over
        return 1
    if name == "JobOffersDialog":
        dlg.table.selectRow(0)
        dlg._take()
        return dlg.result()
    if name == "SettingsDialog":
        for key, spec in dlg.controls.items():
            if spec[0] == "slider":
                spec[1].setValue(spec[1].maximum() // 2)
        dlg._save()
        return 1
    return None


_impls.CONFIG["on_exec"] = on_exec


INBOX_KINDS = set()


def exercise_inbox(win, tag):
    """Open the inbox and press every kind of button once."""
    import inbox
    from ui_screens_club import run_inbox_action
    win.goto("inbox")
    done = set()
    for _ in range(30):
        todo = [(it, a) for it in inbox.action_items(win.lg) for a, _ in it["actions"]
                if (it["kind"], a) not in done]
        if not todo:
            break
        it, a = todo[0]
        done.add((it["kind"], a))
        INBOX_KINDS.add(it["kind"])
        run_inbox_action(win, it, a)
        win.goto("inbox")
    win.goto("home")
    step(f"inbox {tag}: {sorted(k for k, _ in done)}")


def main():
    random.seed(3)
    # Start + new game dialogs
    sd = ui_dialogs.StartDialog()
    sd._pick("new")
    assert sd.choice == "new"
    step("start dialog")
    ng = ui_dialogs.NewGameDialog()
    ng.generate()
    ng.table.setCurrentCell(5, 0)
    abbr = ng.table.selected_key()
    ng._show(abbr)
    ng._start()
    lg = ng.league
    assert lg.user_abbr == abbr, (lg.user_abbr, abbr)
    step("new game dialog")

    win = MainWindow(lg)
    step("main window")
    for key in ("roster", "stats", "players"):
        win.goto(key)
    win.go_back()
    assert win.current == "stats", win.current
    win.go_back()
    assert win.current == "roster", win.current
    win.go_forward()
    assert win.current == "stats", win.current
    win.goto("home")
    assert not win.fwd_btn.isEnabled()
    win.go_forward()
    assert win.current == "home"
    step("back and forward")

    def visit_all(tag):
        for key in ui_main.SCREENS:
            win.goto(key)
            step(f"{tag}: goto {key}")

    visit_all("preseason")

    # Interactions on club screens
    scr = win.screens["roster"]
    for f, _ in __import__("ui_screens_club").POS_GROUP_FILTERS:
        scr._set_filter(f)
    scr._set_filter("ALL")
    step("roster filters")
    dc = win.screens["depth"]
    dc.slots.setCurrentRow(DEPTH_SLOT_DT)
    dc.rot_combo.setCurrentIndex(3)
    assert lg.user_team.rotation.get("DL") == "heavy", lg.user_team.rotation
    dc.slots.setCurrentRow(DEPTH_SLOT_LB)
    dc.rot_combo.setCurrentIndex(1)
    for i in range(dc.slots.count()):
        dc.slots.setCurrentRow(i)
        if dc.order.rowCount() > 1:
            dc.order.selectRow(1)
            dc._move(-1)
            dc.order.selectRow(0)
            dc._move(1)
            dc.order.selectRow(1)
            dc._to_top()
            dc._reset()
    step("depth chart")
    tac = win.screens["tactics"]
    for key, (s, _) in tac.sliders.items():
        s.setValue(80)
    tac._reset()
    tac.sliders["pass_run"][0].setValue(65)
    tac.refresh()
    tac.pb_table.selectRow(0)
    tac._set_pref(2.0)
    tac.pb_table.selectRow(1)
    tac._set_pref(0.0)
    tac.pb_table.selectRow(1)
    tac._set_pref(1.0)
    for i in range(4):
        tac.pb_kind.setCurrentIndex(i)
        assert tac.pb_table.rowCount() > 3, i
        tac.pb_table.selectRow(2)
        tac._pb_selected()
        tac._set_pref(2.0 if i != 2 else 0.0)
    assert any(k.startswith("run:") for k in tac.user.play_prefs) and any(k.startswith("def:") for k in tac.user.play_prefs)
    assert any(k.startswith("st:") for k in tac.user.play_prefs)
    tac.pb_kind.setCurrentIndex(0)
    step("tactics")
    staff = win.screens["staff"]
    win.goto("staff")
    staff.pool.selectRow(0)
    staff._hire()
    staff.staff_table.selectRow(2)
    staff._staff_selected()
    if staff.avail_table.rowCount():
        staff.avail_table.selectRow(0)
        staff._hire_staff()
    staff.scout_table.selectRow(0)
    staff.region.setCurrentIndex(3)
    staff._assign_region()
    staff.scout_pool.selectRow(0)
    staff._hire_scout()
    staff.scout_table.selectRow(0)
    staff._fire_scout()
    for i in range(staff.tabs.count()):
        staff.tabs.setCurrentIndex(i)
    staff.conf_bar.paintEvent(None)
    step("staff hire")
    # Draft board during the season: scouting focus
    win.goto("draft")
    drs = win.screens["draft"]
    for r in range(3):
        drs.table.selectRow(r)
        drs._focus()
    step("scouting focus")
    fin = win.screens["finances"]
    win.goto("finances")
    fin._set_filter("expiring")
    fin._set_filter("all")
    fin.table.selectRow(0)
    fin._extend()
    step("finances")

    # Profiles & team dialogs
    some = [lg.user_team.roster[0], lg.free_agents[0], lg.team_list()[3].roster[2]]
    for p in some:
        dlg = ui_dialogs.PlayerDialog(win, p)
        for b in buttons_in(dlg):
            if b.text() in ("Release",):
                continue
            b.click()
        step(f"player dialog {p.position}")
    td = ui_dialogs.TeamDialog(win, lg.team_list()[7])
    step("team dialog")
    ui_dialogs.TeamDialog(win, lg.user_team)
    html = ui_dialogs.front_office_html(lg, next(t for t in lg.team_list() if t.abbr != lg.user_abbr))
    assert "General Manager" in html and "Plan:" in html, html
    step("front office views")
    sdlg = ui_dialogs.SettingsDialog(win)
    on_exec(sdlg)
    step("settings dialog")

    # Free agent signing during preseason
    win.goto("fa")
    fa_scr = win.screens["fa"]
    fa_scr.table.selectRow(0)
    fa_scr._offer()
    step("fa offer")

    # Play a few weeks with Continue
    for _ in range(3):
        win.continue_clicked()
        step(f"continue {lg.week_label}")
    visit_all("week3")
    win.goto("game")
    gc = win.screens["game"]
    for i in range(min(3, gc.picker.count())):
        gc.picker.setCurrentIndex(i)
    gc.only_mine.setChecked(False)
    win.watch_game(gc.games[0])
    win.watch_act.setChecked(False)
    win.watch_act.setChecked(True)
    step("game center")
    assert len(LIVE) >= 3, len(LIVE)
    gp = win.screens["gameplan"]
    win.goto("gameplan")
    for key, box in gp.plan_controls.items():
        box.setCurrentIndex(box.count() - 1)
    assert lg.user_team.def_gameplan and len(lg.user_team.def_gameplan) == len(gp.plan_controls)
    for i in range(2):
        gp.rep_kind.setCurrentIndex(i)
        assert gp.rep_table.rowCount() > 0, i
    for key, box in gp.plan_controls.items():
        box.setCurrentIndex(0)
    assert not lg.user_team.def_gameplan
    step("game plan")
    st = win.screens["stats"]
    win.goto("stats")
    from ui_screens_league import STAT_TABS
    for g, _ in STAT_TABS:
        st._set_group(g)
        if g in ("AdvPass", "AdvRush", "AdvRec", "PassRush", "TeamAdv", "Grades", "Blocking", "QBDecisions"):
            assert st.table.rowCount() > 0, g
    st.qualified.setChecked(False)
    st.team.setCurrentIndex(2)
    st.pos.setCurrentIndex(1)
    st.playoffs.setChecked(True)
    st.playoffs.setChecked(False)
    step("stats screen")
    win.goto("standings")
    for m in ("division", "conference", "league"):
        win.screens["standings"]._set_mode(m)
    step("standings")
    win.goto("players")
    pl = win.screens["players"]
    pl.name.setText("a")
    pl.pos.setCurrentIndex(3)
    pl.team.setCurrentIndex(1)
    pl.min_ca.setValue(60)
    step("players")
    win.goto("schedule")
    sch = win.screens["schedule"]
    for i in range(sch.week.count()):
        sch.week.setCurrentIndex(i)
    step("schedule")
    win.goto("news")
    for c in ("all", "Injury", "Trade", "mine"):
        win.screens["news"]._set_cat(c)
    step("news")

    # Trades
    win.goto("trades")
    tr = win.screens["trades"]
    tr.partner.setCurrentIndex(4)
    tr.mine.selectRow(5)
    tr._add(tr.mine, tr.give)
    tr.theirs.selectRow(30)
    tr._add(tr.theirs, tr.get)
    tr._evaluate()
    tr._propose()
    tr._remove()
    step("trades")

    # Roster rules: injured reserve, practice squad, picks in trades
    import roster_rules as rr
    settings_mod.settings.set("practice_squad_size", 16)
    win.goto("roster")
    rs = win.screens["roster"]
    for f in ("PS", "IRL", "ALL"):
        rs._set_filter(f)
    team = lg.user_team
    victim = next(p for p in team.roster if not p.ps and not p.ir and p.position == "WR")
    victim.injury = {"name": "Test sprain", "weeks": 6}
    rs.refresh()
    assert select_key(rs.table, victim.id)
    rs._toggle_ir()
    assert victim.ir, "IR placement failed"
    young = next(p for p in team.roster if p.years_pro <= 2 and not p.ps and not p.ir and p.ovr < 72)
    assert select_key(rs.table, young.id)
    rs._toggle_ps()
    assert young.ps, "move to practice squad failed"
    rs.refresh()
    assert select_key(rs.table, young.id)
    rs._toggle_ps()
    assert not young.ps, "promotion failed"
    step("ir and practice squad")
    win.goto("trades")
    tr.partner.setCurrentIndex(6)
    tr._clear()
    pick_keys = [tr.mine.key_at(r) for r in range(tr.mine.rowCount()) if isinstance(tr.mine.key_at(r), str)]
    assert pick_keys, "no tradable picks listed"
    select_key(tr.mine, pick_keys[0])
    tr._add(tr.mine, tr.give)
    their = [tr.theirs.key_at(r) for r in range(tr.theirs.rowCount()) if not isinstance(tr.theirs.key_at(r), str)]
    select_key(tr.theirs, their[-1])
    tr._add(tr.theirs, tr.get)
    tr._evaluate()
    tr._propose()
    tr.mine.on_activate(pick_keys[0])
    step("pick trade")
    import market
    for _ in range(40):
        if market.maybe_offer_user(lg, chance=1.0):
            break
    tr.refresh()
    if getattr(lg, "trade_offers", []):
        tr.offers.setCurrentRow(0)
        tr._accept_offer()
    for _ in range(40):
        if market.maybe_offer_user(lg, chance=1.0):
            break
    tr.refresh()
    tr.offers.setCurrentRow(0)
    tr._decline_offer()
    step("trade offers")

    # Trading block: put a starter on the block, ask every club, haggle, accept
    win.goto("block")
    blk = win.screens["block"]
    star = max((p for p in team.roster if not p.ps and not p.ir and not p.is_injured
                and p.position not in ("QB", "K", "P")), key=lambda p: p.ovr)
    assert select_key(blk.mine, star.id)
    blk._add()
    assert star.id in lg.trade_block, lg.trade_block
    pk = next(blk.mine.key_at(r) for r in range(blk.mine.rowCount()) if isinstance(blk.mine.key_at(r), str))
    assert select_key(blk.mine, pk)
    blk._add()
    blk.block.setCurrentRow(1)
    blk._remove()
    assert len(lg.trade_block) == 1, lg.trade_block
    for kind in ("players", "picks", "any"):
        blk._set_kind(kind)
        blk._ask()
        assert blk.offers_table.rowCount() > 0, kind
    blk.offers_table.selectRow(0)
    blk._open_in_trades()
    assert tr.give.count() == 1 and tr.get.count() >= 1
    tr._make_it_work()
    win.goto("block")
    blk._ask()
    blk.offers_table.selectRow(0)
    blk._accept()
    assert star.team != team.abbr, "block trade failed"
    assert not lg.trade_block
    step("trading block")
    win.goto("trades")
    rich = max(lg.team_list()[12].roster, key=lambda p: p.ovr)
    tr.preload(rich)
    tr._make_it_work()
    if tr.give.count():
        assert tr._evaluate(), "make it work suggestion was not accepted"
    step(f"make it work ({tr.give.count()} added)")
    for _ in range(40):
        if market.maybe_offer_user(lg, chance=1.0):
            break
    offered = {r for o in lg.trade_offers for r in o["get"]}
    hurt = next(p for p in team.roster if not p.ps and not p.ir and p.position == "CB"
                and p.id not in offered)
    hurt.injury = {"name": "Test fracture", "weeks": 8}
    exercise_inbox(win, "in season")
    win.goto("glossary")
    gl = win.screens["glossary"]
    gl.search.setText("cover")
    gl.search.setText("")
    step("glossary")
    other = lg.team_list()[10].roster[0]
    win.trade_for(other)
    step("trade_for")

    # Sim to the deadline (stops on injuries / offers), then the rest without stops
    win.sim("deadline")
    step(f"sim to deadline: {lg.week_label}")
    settings_mod.settings.set("sim_stop_injury", False)
    settings_mod.settings.set("sim_stop_offer", False)
    # Sim rest of the regular season and playoffs
    win.sim("regular")
    step("sim regular")
    visit_all("end regular")
    win.sim("playoffs")
    step("sim playoffs")
    assert lg.phase == "season_end", lg.phase
    visit_all("season_end")
    win.goto("history")
    hs = win.screens["history"]
    for i in range(hs.metric.count()):
        hs.metric.setCurrentIndex(i)
    hs.metric2.setCurrentIndex(3)
    hs.chart.paintEvent(None)
    for i in range(hs.rec_cat.count()):
        hs.rec_cat.setCurrentIndex(i)
    for kind in range(hs.rec_kind.count()):
        hs.rec_kind.setCurrentIndex(kind)
        for i in range(hs.rec_cat.count()):
            hs.rec_cat.setCurrentIndex(i)
        assert hs.rec_table.rowCount() > 0, kind
    assert lg.weekly_awards and any(getattr(p, "potw", 0) for p in lg.all_players())
    hs.rec_kind.setCurrentIndex(1)
    step("history")

    # Offseason: re-sign window
    win.continue_clicked()
    assert lg.phase == "resign", lg.phase
    exercise_inbox(win, "resign")
    win.goto("finances")
    fin._set_filter("expiring")
    if fin.table.rowCount():
        fin.table.selectRow(0)
        fin._extend()
    fin._set_filter("expiring")
    if fin.table.rowCount():
        fin.table.selectRow(0)
        fin._tag()
    step("resign")
    win.continue_clicked()
    assert lg.phase == "draft", lg.phase
    exercise_inbox(win, "draft")
    win.goto("draft")
    dr = win.screens["draft"]
    dr._sim()
    dr.table.selectRow(0)
    dr._pick()
    dr._sim()
    dr._auto()
    dr._set_filter("QB")
    step("draft")
    win.continue_clicked()
    assert lg.phase == "free_agency", lg.phase
    win.goto("fa")
    fa_scr._set_filter("WR")
    fa_scr.table.selectRow(0)
    fa_scr._offer()
    fa_scr._wave()
    step("free agency")
    win.continue_clicked()
    assert lg.phase == "preseason", lg.phase
    visit_all("preseason2")
    exercise_inbox(win, "preseason")
    win.continue_clicked()
    assert lg.phase == "regular" and lg.week == 0, (lg.phase, lg.week)
    step("new season")

    # Getting fired and taking a new job
    import staff as staff_mod
    old_abbr = lg.user_abbr
    lg.gm["fired"] = True
    lg.gm["offers"] = staff_mod.job_offers(lg)
    win._handle_firing()
    assert lg.user_abbr != old_abbr and not lg.gm["fired"], "job change failed"
    visit_all("new job")
    step("fired and rehired")

    # Auto-sim a full season
    win.sim("season")
    step("sim season")
    visit_all("after auto season")

    # Theme + save/load
    win.toggle_theme()
    visit_all("light theme")
    win.toggle_theme()
    # Table sort and filter chips are remembered for the next window / session
    win.goto("roster")
    from PyQt6.QtCore import Qt
    hdr = win.screens["roster"].table.horizontalHeader()
    hdr.setSortIndicator(3, Qt.SortOrder.DescendingOrder)
    hdr.sortIndicatorChanged.emit(3, Qt.SortOrder.DescendingOrder)     # what a header click does
    win.goto("news")
    lay = win.screens["news"].outer
    next(lay.itemAt(i).widget() for i in range(lay.count())
         if hasattr(lay.itemAt(i).widget(), "pick")).pick("Trade")
    assert win.screens["news"].cat == "Trade"
    path = save_manager.save(lg, "ui test")
    lg2 = save_manager.load(path)
    win2 = MainWindow(lg2)
    assert win2.screens["news"].cat == "Trade", win2.screens["news"].cat
    win2.goto("roster")
    rt = win2.screens["roster"].table
    assert rt._user_sorted and rt._pending_sort is None, (rt._user_sorted, rt._pending_sort)
    step("table and filter memory")
    for key in ui_main.SCREENS:
        win2.goto(key)
    save_manager.delete(path)
    if os.path.exists(ui_state.STATE_FILE):
        os.remove(ui_state.STATE_FILE)
    step("save/load")
    assert any(DIAG_SEEN), "no play diagrams were drawn"
    assert {"offer", "ir", "expiring", "draft"} <= INBOX_KINDS, INBOX_KINDS
    print("negotiations:", [(n, r) for n, r, _ in NEGOTIATIONS][:8])
    assert any(r for _, r, _ in NEGOTIATIONS), NEGOTIATIONS
    print(f"UI test passed: {len(STEPS)} steps, league now {lg.year} {lg.week_label}, "
          f"{len(lg.history)} seasons in history")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        print("LAST STEP:", STEPS[-1] if STEPS else None)
        sys.exit(1)
